# Upgrade Memory Hook Uses Stale Modules When an Older Server Drives the Upgrade

Change ID: `1zesi-bug memory-hook-stale-modules`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zeyo upgrade-field-fixes

## Rationale

Field report: a 1.27.0 → 1.28.0+ptgj upgrade started with `wf_upgrade()` from a running 1.27 MCP server extracted, rendered and passed the docs gate, then failed with `ERROR: Extension hook 'post_docs_gate' raised: 'RecordRoots' object has no attribute 'archive'`. After a full host restart, rerunning the same pack succeeded, and `wf memory-backfill --mode dry_run --entry-path upgrade` from a fresh process ran cleanly.

Cause, verified in code: `upgrade_extensions.post_docs_gate` ("Bootstrap the memory pause under both old and new upgrade runners") loads the newly extracted `memory_backfill` through `_installed_memory_backfill`, which reloads only the `memory_backfill` module. Its dependencies stay as the old runner loaded them in `sys.modules`: the 1.28 `memory_backfill` (wave `1z8tt`) calls `record_paths.discover_archive_dirs` and `load_record_roots(...).archive`, but the process still holds the 1.27 `record_paths`, whose `RecordRoots` has no `archive` field. `upgrade_extensions` is loaded from the new pack, so a fix here reaches 1.27 → 1.28 upgrades.

Goal: the memory bootstrap runs on consistent, newly extracted code whatever runner drives it. Consumer: every repository upgrading from an older version through MCP. Success: a 1.27-driven `wf_upgrade` to the fixed pack passes the memory step without a restart.

## Requirements

1. **Consistent code for the memory bootstrap, in this process.** Before `post_docs_gate` runs `ensure_run` and `sync_inventory`, it refreshes in place, leaf-first, every framework module those calls and `reconcile_index_publication` reach at runtime (derived from their imports; today `vocabulary_profile`, `record_paths`, `path_containment`, `repo_root`, `memory_records`, then `memory_backfill`), so the old runner's own post-hook `import memory_backfill` (v1.27.0 `upgrade_wavefoundry.main`) also runs consistent code. Modules that hold process state (locks, context variables, open transactions: `runtime_lock`, `lifecycle_lock`, `upgrade_lib`, `index_state_store`, `sqlite_storage_migration`, `review_evidence`) are never reloaded; each excluded module is listed with its reason. A subprocess alone is rejected because it leaves the parent's stale modules for the runner's post-hook import.
2. **Other cross-extraction loaders are checked.** Every loader in `upgrade_extensions.py` that reuses a module from the old runner's `sys.modules` is audited for the same dependency staleness; any found is fixed the same way or recorded with a reason it is safe.
3. **No behaviour change on a fresh process.** When the runner already has the new code (a restarted server or the CLI), the bootstrap's results are unchanged.
4. **Platforms.** Same on Windows, macOS, Linux and WSL2 (in-process module reload; no subprocess).
5. **Transition.** The fix is in `upgrade_extensions.py`, which the running upgrade loads from the new pack, so it applies to the upgrade that installs it, including 1.27 → 1.28 (verified: v1.27.0 `_load_extension_module` reads `upgrade_extensions.py` from the pack and executes it). The CHANGELOG entry goes under `### Fixed` in the open `## [1.28.0]` section.

## Scope

**Problem statement:** the upgrade's memory bootstrap mixes newly extracted and stale modules when an older server drives it, and crashes.

**In scope:**

- `upgrade_extensions.post_docs_gate`, `_installed_memory_backfill` and any other stale-dependency loaders found under Requirement 2; tests; CHANGELOG.

**Out of scope:**

- The failure labelling and recovery after a hook crash (change `1zeyn-bug post-docs-gate-failure-recovery`).
- Memory backfill behaviour itself.

## Acceptance Criteria

- [x] AC-1: with the v1.27.0 `record_paths` source already in `sys.modules` (no `vocabulary_profile`, which did not exist in 1.27; a `RecordRoots` without `archive`), `post_docs_gate` against a newly extracted tree completes the bootstrap and records the memory run in the upgrade lock.
- [x] AC-1b: after `post_docs_gate` returns with the v1.27.0 `record_paths` source preloaded in `sys.modules`, a fresh `import memory_backfill` plus `ensure_run`, `sync_inventory` and `reconcile_index_publication` in the same process succeeds (mirrors the v1.27.0 runner after the hook).
- [x] AC-2: on a fresh process the bootstrap produces the same run and summary as before.
- [x] AC-3: every cross-extraction loader in `upgrade_extensions.py` is listed in the Progress Log with its dependency-staleness verdict.
- [x] AC-4: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Derive the runtime closure of `ensure_run`, `sync_inventory` and `reconcile_index_publication`; reload it leaf-first in place; list the excluded stateful modules with reasons.
- [x] Audit the other loaders in `upgrade_extensions.py`.
- [x] Tests for AC-1, AC-1b and AC-2 using the real v1.27.0 `record_paths` source in `sys.modules`; CHANGELOG entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Loader fix and audit | implementer | readiness | |
| Review | code-reviewer, qa-reviewer, release-reviewer | Loader fix and audit | Upgrade old-code window |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- CHANGELOG.md

## Affected Architecture Docs

N/A: the fix refreshes modules in place inside the existing upgrade hook; no new process, boundary or flow.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The field crash |
| AC-1b | required | The old runner's own post-hook import, the headline 1.27 case |
| AC-2 | required | No regression on the normal path |
| AC-3 | important | Same class elsewhere |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Post-approval review (DEL-1ZEYO-R2): the in-place reload broke exception class identity. `importlib.reload` updates the module namespace, so an old function imported by name (`wave_lint_lib/helpers.py`: `from record_paths import RecordLayoutInvalid, load_record_roots`) raised the NEW `RecordLayoutInvalid` that the holder's `except` did not name. The red-team refutation (old function and old class stay together) was wrong. Fix: `_reload_in_place` rebinds every exception class that survives the reload to its original object (the classes in the reload set are byte-identical to v1.27.0); used by `_installed_memory_backfill` and `_refresh_record_layout_modules`. Test: a from-imported `load_record_roots` still raises the from-imported class after `post_docs_gate`. Mutant (no rebind) caught | 153 focused tests OK |
| 2026-09-30 | Implemented. `upgrade_extensions`: `_MEMORY_BOOTSTRAP_MODULES` (`vocabulary_profile`, `path_containment`, `repo_root`, `record_paths`, `memory_records`, `memory_backfill`, reloaded leaf-first in place by `_installed_memory_backfill`) and `_MEMORY_BOOTSTRAP_EXCLUDED` (`index_state_store`: holds build-state locks and context variables, bootstrap uses only `read_build_state`, unchanged since v1.27.0; `lifecycle_id`: activates the tool venv on import, `memory_records` uses only `build_prefix` and `load_lifecycle_policy`, unchanged since v1.27.0). Compatibility for the old runner: every `record_paths` function v1.27.0 framework code calls exists in HEAD with a compatible signature (only `walk_wave_candidates` gained keyword-only parameters); the only from-imports of reloaded modules in 1.27 are `core_validators` and a lint helper, which bind old functions and the old exception class together, so they stay consistent. Loader audit (AC-3): `_stop_dashboard` imports (pre-extraction, old tree intended: safe); `storage_identity` archive-member exec (digest-checked, independent: safe); `upgrade_lib` (stateful lock writer, never reloaded: 1.27 API used); `_installed_upgrade_module` and `_installed_storage_migration` (fresh `spec_from_file_location` modules: safe); `_reload_cached_review_evidence`, the `review_policy` reload and `_fresh_installed_module` (depend on `record_paths`/`vocabulary_profile`: now call `_refresh_record_layout_modules` first). Tests (`HistoricalMemoryUpgradeExtensionBootstrapTests`): a fixture of the real v1.27.0 `record_paths` source (`tests/fixtures/upgrade_old_runner/record_paths_v1_27_0.py.txt`) preloaded; the hook completes (AC-1); the old runner's own post-hook import runs `ensure_run`, `sync_inventory` and `reconcile_index_publication` (AC-1b); current-module run unchanged (AC-2); review reload refreshes `record_paths`; the reload set is derived by AST scan (every framework import is reloaded or excluded). Mutants: old single-module loader, `record_paths` dropped, `memory_records` dropped; all caught. Gapfill: none for retrieval (MCP `code_read`/`code_keyword`); the 1.27 API comparison used a git-show script | 582 upgrade tests OK |
| 2026-09-30 | Readiness review: B1 adopted (reproduced in scratch: the v1.27.0 runner re-imports `memory_backfill` after the hook, so a hook-only subprocess leaves the crash; an in-place reload of `record_paths` made the post-hook import succeed). Requirement 1, AC-1 fixture and new AC-1b per the reviewer; `memory_supply` is not in the closure. D2: CHANGELOG under `## [1.28.0]` | readiness review |
| 2026-09-30 | Planned from a 1.27 → 1.28.0+ptgj field upgrade. Verified: `_installed_memory_backfill` reloads only `memory_backfill`; `post_docs_gate` calls `ensure_run` and `sync_inventory`; `memory_backfill` and `memory_supply` read `record_paths.load_record_roots(...).archive` | code reading |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Refresh the pure runtime closure in place, leaf-first; never reload stateful modules | Readiness B1: a subprocess leaves the old runner's stale `record_paths` for its own post-hook `import memory_backfill`; reloading the full static closure would reach modules holding the runner's locks, transactions and ContextVars | Subprocess (moves the crash one step later); full static-closure reload (unsafe) |
| 2026-09-30 | Fix in `upgrade_extensions.py` (new-pack code) rather than tolerate a missing `archive` attribute in `memory_backfill` | Removes the whole class (any new field or function in a dependency), and runs on the installing upgrade | `getattr(roots, "archive", None)` in the readers (fixes only this attribute; the next new dependency field fails the same way) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Reloading shared modules changes objects other old-runner code still holds | Only pure modules (attribute access, no process state) are reloaded; stateful modules are excluded by name with reasons; AC-2 pins the fresh-process result |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
