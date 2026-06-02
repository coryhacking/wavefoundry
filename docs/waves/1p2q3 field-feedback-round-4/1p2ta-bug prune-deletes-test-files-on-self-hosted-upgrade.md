# Prune Deletes Test Files on Self-Hosted Upgrade

Change ID: `1p2ta-bug prune-deletes-test-files-on-self-hosted-upgrade`
Change Status: `implemented`
Owner: Engineering
Status: in-progress
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

`upgrade-wavefoundry --cleanup` deletes `.wavefoundry/framework/scripts/tests/` and `scripts/run_tests.py` on every self-hosted upgrade. This wave alone has lost 30+ tests to the prune twice, both times immediately after `build_pack.py` shipped a new pack. The framework's own regression coverage is being wiped out by the framework's own upgrade workflow.

Trace of the failure path:

1. `build_pack.py` writes a `MANIFEST` file into the zip, then deletes it from the source tree (line 478: "packaging artifact — delete after").
2. `upgrade-wavefoundry` looks for `.wavefoundry/framework/MANIFEST` to copy aside as `OLD_MANIFEST_TMP` before extracting the new pack. The file doesn't exist (build_pack just deleted it), so the save is skipped silently.
3. Phase 2 calls `prune_framework.py` without `--old-manifest`, which falls through to the legacy-fallback branch at lines 137–151.
4. The legacy branch unconditionally deletes every entry in `_LEGACY_REMOVALS` — a list intended for cleaning up paths that shipped in pre-MANIFEST packs (2026-04-29a through 2026-05-02d). The list includes `scripts/tests/` and `scripts/run_tests.py`.

The legacy list was never the right home for these entries:

- The wavefoundry repo's `tests/` directory is the canonical source of regression coverage; it's git-tracked under `.wavefoundry/framework/scripts/tests/` and never shipped in any modern pack.
- Even operators upgrading from the historical pre-MANIFEST packs (now over a month old) would not be harmed by stale test files persisting — old test scripts in an unused directory do not break anything.
- The other entries in `_LEGACY_REMOVALS` (`render_hooks.py`, `build_zip.py`, `docs-lint.py`, `docs-gardener.py`, `docs_lint_lib/`) were real shipped framework artifacts that warranted cleanup. Tests and the test runner are different in kind — they are development workflow files.

Operator-facing impact: silent data loss on every self-hosted release cycle, requiring a manual `git checkout` and re-add of any session test work that wasn't committed before the build. The workaround ("commit tests before building") is not discoverable from the upgrade command output.

## Requirements

1. `prune_framework.py` must not delete `.wavefoundry/framework/scripts/tests/` or `scripts/run_tests.py` under any code path — legacy fallback or manifest-diff.
2. The legacy fallback branch must remain available for operators upgrading from genuinely pre-MANIFEST packs, but its scope is reduced to the entries that were actually packaged in those releases.
3. Decision: per operator direction during 1p2q3 close-out, `_LEGACY_REMOVALS` is removed entirely. Pre-MANIFEST packs are over a month old; operators on that vintage can clean up the obsolete `render_hooks.py` / `build_zip.py` / `docs-lint.py` / `docs-gardener.py` / `docs_lint_lib/` paths manually. The risk of an automated legacy prune deleting current development files outweighs the convenience.
4. When no `--old-manifest` is supplied, prune must emit a clear log line so operators can tell at a glance that the diff-based prune was skipped and no automated cleanup occurred.
5. Regression test asserts that prune called without `--old-manifest` does NOT delete `scripts/tests/` or `scripts/run_tests.py` even when they exist on disk.

## Scope

**Problem statement:** The framework's prune phase silently deletes the framework's own test files on every self-hosted upgrade because `build_pack.py` deletes the MANIFEST before `upgrade-wavefoundry` can save it, and the legacy fallback path treats `tests/` and `run_tests.py` as deletion candidates.

**In scope:**

- `.wavefoundry/framework/scripts/prune_framework.py` — delete `_LEGACY_REMOVALS` and `_prune_legacy()`; surface a no-op log line when `--old-manifest` is absent
- `.wavefoundry/framework/scripts/tests/test_prune_framework.py` — regression test for the "no manifest, no deletion" behavior

**Out of scope:**

- Changing `build_pack.py`'s MANIFEST-deletion behavior. That deletion is intentional for downstream consumers (MANIFEST is a packaging artifact, not source). The fix is at the prune layer.
- Adding a commit-before-build warning to `build_pack.py`. The right fix is to make the prune safe by design rather than rely on operator discipline.

## Acceptance Criteria

- [x] AC-1: `_LEGACY_REMOVALS` and `_prune_legacy()` are removed from `prune_framework.py`.
- [x] AC-2: When `prune` is invoked without `--old-manifest`, it emits a structured log message ("info: no old MANIFEST provided — skipping prune") and returns without deleting any files.
- [x] AC-3: When `prune` is invoked with a valid `--old-manifest`, the diff-based deletion path continues to work — files in `old_manifest - new_manifest` are deleted as before.
- [x] AC-4: Regression test: `prune` called against a framework dir containing `scripts/tests/` and `scripts/run_tests.py`, with no `--old-manifest`, does NOT delete either path. Covered by `test_no_old_manifest_is_noop_does_not_delete_tests_dir`.
- [x] AC-5: Regression test: `prune` called with `--old-manifest` referencing an old manifest containing `scripts/foo.py` (not in the new manifest), DOES delete `scripts/foo.py` — confirms the diff path is unaffected. Covered by `test_diff_path_still_deletes_when_old_manifest_supplied`.
- [x] AC-6: All existing 2,200 framework tests pass without modification.

## Tasks

- [x] Open `framework_edit_allowed` gate (already open from earlier 1p2q3 work; verify)
- [x] Delete `_LEGACY_REMOVALS` constant and `_prune_legacy()` function from `prune_framework.py`
- [x] Update the no-manifest branch in `prune()` to emit the new log message and return `[]`
- [x] Update `prune_framework.py` module docstring to reflect that legacy fallback is no longer supported
- [x] Replace legacy tests in `test_prune_framework.py` with regression coverage for AC-4 and AC-5
- [x] Run framework tests
- [ ] Update wave handoff to note the prune-safety fix shipped in this round

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| prune-fix | Engineering | — | Single-file edit in `prune_framework.py` |
| prune-tests | Engineering | prune-fix | New test file |

## Serialization Points

- N/A — single-module change with no integration gates.

## Affected Architecture Docs

N/A — bug fix confined to the prune script; no boundary, flow, or verification-architecture change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the data-loss vector at its source |
| AC-2 | required | Operator must see the no-op state clearly; silent skip would mask future regressions |
| AC-3 | required | Diff-based prune is the only correct deletion mode; must continue to work for downstream operators |
| AC-4 | required | The specific regression that motivated this change |
| AC-5 | required | Confirms the fix is scoped to the legacy fallback path |
| AC-6 | required | No baseline regression |

## Related Work

- Direct follow-on to the wave 1p2q3 close-out audit. Test loss was observed twice in this session alone (Threads 1/3/4/5/6/A/B coverage erased on the 1.3.5 build; coverage from this session erased on the 1.3.6 build).
- Pairs with the `MANIFEST` deletion in `build_pack.py` (line 478) — that behavior is intentional for downstream consumers but interacts badly with the legacy fallback. This fix decouples the two.
