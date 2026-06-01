# Framework Pack and Framework Index Leak Transient Artifact Files

Change ID: `130o2-bug framework-pack-leaks-lock-files`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130et framework-bin-mcp-server-launcher

## Rationale

Operator report 2026-05-31 (Solaris, downstream user) after upgrading to 1.1.0+30ny: the project-layer staleness bug (130nf) is fixed, but the framework layer now reports `test-run.lock` as a stale path. Audit of `wavefoundry-1.1.0.30ny.zip` revealed multiple transient artifact categories that ship in the pack:

```
.wavefoundry/framework/test-run.lock                   5 B   (run_tests.py mutex)
.wavefoundry/framework/index/index-build.lock         46 B   (indexer rebuild mutex)
.wavefoundry/framework/index/index-build.log         296 B   (indexer log output, per-machine timestamps)
.wavefoundry/framework/index/index-build-docs.log    296 B   (indexer log output, per-machine timestamps)
```

`test-run.lock` is created by `run_tests.py:50` (`_LOCK_FILE = _FRAMEWORK_DIR / "test-run.lock"`) — a transient flock target for the test-runner mutex. `index-build.lock` is created by the indexer during `build_index` to serialize concurrent rebuilds. The two `index-build*.log` files are stdout/stderr captures from index rebuilds — they contain per-machine timestamps and run-specific paths.

Two filters both miss them:

1. **`build_pack.should_exclude` (`build_pack.py:70-84`)** excludes `.DS_Store`, `__pycache__`/`.pytest_cache`/`.wavefoundry` dirs, specific rel-paths (`scripts/tests`, `scripts/run_tests.py`, `scripts/benchmarks`, `test-cache.json`), and `*.pyc`. **No transient-artifact extension rules.** So the lock and log files travel into the shipped zip's MANIFEST and onto downstream disks.
2. **`indexer._filter_framework_pack_artifacts` (`indexer.py:658-680`)** excludes `MANIFEST`/`VERSION` basenames, `MANIFEST.pre-*` prefix, framework test paths, dev-only prefixes (`scripts/benchmarks/`), and dev-only exact paths (`scripts/run_tests.py`, `test-cache.json`). **No transient-artifact extension rules.** So when `wave_index_build` runs the framework layer locally, lock and log files are included in `file_meta`. Across machines (transient artifacts created by test/build runs on one machine, absent or recreated with different content on another) the framework layer's `meta.json` and the local walk disagree → permanent `stale` flag for transient bytes.

Symptom in operator's `wave_index_health` output (1.1.0+30ny):

```
framework | stale | 1 (test-run.lock) | Transient lock file — trivial
```

The same shape of report would surface for the log files on any machine where the local indexer logs diverge from the packed snapshot — the user just hasn't tripped that yet because the build logs were stable across their machine and ours.

## Requirements

1. The shipped pack must not contain any file whose basename matches transient-artifact extensions: `.lock`, `.log`, `.bak`, `.swp`, `.tmp`, `.orig`, `.rej`. Today this fixes leaks of `test-run.lock`, `index-build.lock`, `index-build.log`, `index-build-docs.log`; the editor-artifact extensions (`.bak`, `.swp`, `.tmp`, `.orig`, `.rej`) are defensive — none currently exist but they're standard transient categories that should never ship if someone accidentally leaves one behind.
2. `wave_index_build` for the framework layer must skip the same set of extensions in both the walk that hashes (`_layer_current_hashes("framework")` through `_filter_framework_pack_artifacts`) and the walk that populates the framework `file_meta`. The two walks must agree, so the framework layer never reports transient files as `added`/`modified`/`removed`.
3. The fix must be a generic extension rule, not an exact-path list — so we never re-introduce the bug when a new transient artifact appears under any name.
4. The existing exclusions (`.DS_Store`, `__pycache__`, `scripts/tests`, etc.) must remain unchanged. No regression to the project-layer build (transient artifacts are not currently captured there either, but if they were, the same extension rule applies).

## Scope

**Problem statement:** Two transient `*.lock` files leak into the shipped framework pack and into the framework layer's index meta. Downstream operators see a permanently `stale` framework layer for noise.

**In scope:**

- `.wavefoundry/framework/scripts/build_pack.py` — extend `should_exclude` to skip any file whose basename ends in one of the transient-artifact extensions (`.lock`, `.log`, `.bak`, `.swp`, `.tmp`, `.orig`, `.rej`). Define the set as a module-level constant so the indexer can reuse it.
- `.wavefoundry/framework/scripts/indexer.py` — extend `_filter_framework_pack_artifacts` to skip the same extensions. (Project-layer indexing already excludes them implicitly via gitignore patterns when present, but the framework-layer walk uses `respect_ignore=False` per `run_index_rebuild`, so the filter must be explicit.)
- `.wavefoundry/framework/scripts/tests/test_build_pack.py` — regression test asserting a tree with `framework/test-run.lock`, `framework/index/index-build.lock`, `framework/index/index-build.log`, and a representative editor artifact produces a pack that contains none of them.
- `.wavefoundry/framework/scripts/tests/test_indexer.py` — regression test asserting `_filter_framework_pack_artifacts` strips the same set of extensions.

**Out of scope:**

- Changing how `run_tests.py` or the indexer create their lock/log files. They're correct as-is — small, short-lived; the bug is purely in what we pack/index.
- Adding `.gitignore` rules for these artifacts. Already covered at the repo level; the bug is the pack/index filter.
- Adding individual transient files to `FRAMEWORK_DEV_ONLY_EXACT_PATHS`. A generic extension rule is more durable.
- Excluding any directories (e.g. `logs/`). The filter operates on file basenames only — any directory structure (including a hypothetical `framework/logs/`) is preserved; only `*.log` files inside it would be skipped. Per operator direction 2026-05-31: "we can keep the log folder, just not any log files."
- Reissuing previously-shipped packs. 1.1.0+30ny will heal on the next pack/upgrade cycle (this change) — no recall needed; the operator's `wave_index_health` will go green automatically.

## Acceptance Criteria

- [x] AC-1: `build_pack.should_exclude` returns `True` for any file whose basename ends in one of `.lock`, `.log`, `.bak`, `.swp`, `.tmp`, `.orig`, `.rej`.
- [x] AC-2: `indexer._filter_framework_pack_artifacts` strips files matching the same extension set.
- [x] AC-3: Re-running `build_pack.py --version 1.1.0` after this change produces a zip that contains zero entries matching `*.lock` or `*.log` (verified by `unzip -l | grep -E "\\.(lock|log)$"`).
- [x] AC-4: After re-rendering and reinstalling the pack, `wave_index_health` for the framework layer reports `stale_paths_count: 0` for the lock/log set (no transient artifact in either side of the diff).
- [x] AC-5: New regression test in `tests/test_build_pack.py` covers AC-1 (synthesized tree with one file per transient extension → none in the pack).
- [x] AC-6: New regression test in `tests/test_indexer.py` covers AC-2 (`_filter_framework_pack_artifacts` strips the full extension set).
- [x] AC-7: All existing tests continue to pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Patch `build_pack.should_exclude` to skip `*.lock` basenames
- [x] Patch `indexer._filter_framework_pack_artifacts` to skip `*.lock` basenames
- [x] Add regression tests to `tests/test_build_pack.py` and `tests/test_indexer.py`
- [x] Run framework tests
- [x] Rebuild pack and verify no `*.lock` entries in the zip
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline pack-exclusion fix |
| AC-2 | required | Without it the local framework meta still picks up lock files and reports them stale |
| AC-3 | required | End-to-end pack verification proves the pack-side fix landed |
| AC-4 | required | End-to-end health verification proves the index-side fix landed |
| AC-5 | required | Regression coverage so the pack filter doesn't re-leak on future refactor |
| AC-6 | required | Regression coverage for the indexer filter |
| AC-7 | required | No existing tests regress |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Generic `*.lock` extension rule | Two lock files exist today (`test-run.lock`, `index-build.lock`); future framework scripts may add more. An extension rule prevents re-leaking when a new lock is added | Add both files to `FRAMEWORK_DEV_ONLY_EXACT_PATHS` (rejected — adds maintenance burden every time a new lock is introduced) |
| 2026-05-31 | Patch both `build_pack` AND `_filter_framework_pack_artifacts` | They serve different surfaces (the pack and the local framework index respectively), and both surfaces report the bug. Patching only one leaves the other reporting `stale` | Patch only `build_pack` (rejected — local `wave_index_build` would still flag the lock as stale because `respect_ignore=False`). Patch only the indexer filter (rejected — the zip would still ship the noise) |
| 2026-05-31 | Add to existing wave 130et | Operator preference for this session's framework-provisioning hot-fix bucket; the wave is in `implementing` status; trivial change with a single LOC change per file | Open a new wave (rejected per operator direction in this session) |

## Risks

| Risk | Mitigation |
|---|---|
| A legitimate framework file ending in `.lock` might be excluded by accident | None exist today; lock files are by convention transient state, not source. AC-5/AC-6 regression tests pin the behavior |
| Existing 1.1.0+30ny installations contain the lock file in their framework meta; downgrade or skipped upgrades will leave the stale state | Self-heals on next pack install and `wave_index_build` cycle — meta is rewritten from the new walk that excludes lock files; the entries get evicted as `removed_broad` exactly like the 130nf self-heal |

## Related Work

- Fourth change in wave 130et alongside `130eu` (mcp-server launcher), `130f9` (wave-gate rearchitecture), `130nf` (project-meta layer scoping). All four are framework-provisioning hot-fixes from operator reports in the same session.
- 130nf and 130o2 share the same self-heal property: existing meta with stale entries gets rewritten on next incremental build.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
