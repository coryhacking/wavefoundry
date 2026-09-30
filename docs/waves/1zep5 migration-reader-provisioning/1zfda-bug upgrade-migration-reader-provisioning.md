# Upgrade Reports Migration-Reader Provisioning Failures Like the Dependency Step

Change ID: `1zfda-bug upgrade-migration-reader-provisioning`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-30
Wave: 1zep5 migration-reader-provisioning

## Rationale

Wave `1zfd9` gave the upgrade its own dependency step (`upgrade_wavefoundry._provision_upgrade_dependencies`): a failed install is reported as `dependency_provisioning_failed` naming `wf setup`, and the index update is skipped rather than reported as a failed publication. Its final review found one path the step does not cover. When a storage migration is required, `phase_index_update` calls `setup_index.ensure_deps` and, for a legacy Lance store, `setup_index.ensure_migration_deps` to install the pinned `lancedb` reader. Both raise `SystemExit` when an install fails or the install lock is unavailable.

- The default Phase 4 path catches the `SystemExit`, but records a generic `failed_phase=index_update` with no `dependency_provisioning_failed` flag and no `wf setup` remedy, and the `wf_upgrade` handler labels exit 2 as a surface-rendering failure.
- The resume-after-memory path catches only `Exception`, so the `SystemExit` escapes its failure handling: no `failed_phase` is stamped and its transaction exit is skipped.

The branch's `ensure_deps` call is not redundant: the dependency step's metadata precheck cannot see a tool venv that needs rebuilding (a partial venv, or on Windows a venv built for another Python minor version, which shares `Lib/site-packages`), and `ensure_deps` repairs that before `migrate_legacy` runs in-process. It stays.

Goal: a provisioning failure in the migration branch is reported exactly like a dependency-step failure on every upgrade path, and the migration keeps its receipt and legacy sources. Consumer: operators and agents reading `wf upgrade` output and the `wf_upgrade` response. Success: the upgrade output and the `wf_upgrade` response name `wf setup` instead of a generic index failure, a surface-rendering label or an uncaught exit.

## Requirements

1. **One classification.** The dependency step's failure handling is shared: the exception set it catches (`SystemExit`, `RuntimeError`, `OSError`, `subprocess.CalledProcessError`, exactly, not broadened to `Exception`), its `Dependency provisioning FAILED ... run \`wf setup\`` output line and its `dependency_provisioning_failed` lock write. Both provisioning calls in `phase_index_update`'s migration-required branch (`setup_index.ensure_deps` and `setup_index.ensure_migration_deps`) go through it.
2. **Always raise in the migration branch.** In the migration-required branch, `phase_index_update` raises the existing migration-pending `RuntimeError` ("dependency provisioning failed; storage migration retains its receipt and legacy sources; run `wf setup`, then retry") on a provisioning failure whether or not a migration receipt is pending (`migration_required` can be set with no receipt); it never returns False from that branch. The raise happens before `migrate_legacy` and before any publication begins, so the migration receipt and legacy sources are not modified.
3. **Every caller reports it.** For every caller of `phase_index_update` (the set is every call site in `upgrade_wavefoundry.py`; today the default Phase 4 path, `phase_index_update_parent_owned`, `--update-index`, and the resume-after-memory branch), a provisioning failure in the migration branch produces the same outcome a dependency-step failure produces on that path during a pending migration, and no `SystemExit` from provisioning escapes the caller's failure handling. On `--update-index`, which has no `except` block, that means the `RuntimeError` propagating out of `main` with the output line present. When the upgrade exits 1, `wf_upgrade`'s failure envelope carries the `dependency_provisioning_failed` diagnostic.
4. **`wf setup` is unchanged.** `setup_index.ensure_deps` and `ensure_migration_deps` keep their `SystemExit` behaviour; `setup_reconciliation` (reached only through `wf setup`) keeps its current behaviour; the 1zfd9 dependency step's metadata precheck is unchanged.
5. **Platforms.** The routing is the same on Windows, macOS, Linux and WSL2. Keeping `ensure_deps` in the branch preserves its venv repair on every platform, including the Windows case of a venv built for another Python minor version.
6. **Transition disclosure.** Like the 1zfd9 dependency step, this runs in the Phase 4 orchestrator, so on the default `wf upgrade` and `wf_upgrade()` paths it takes effect from the upgrade after the one that installs it; `--update-index` and resume run as new-code subprocesses. The unreleased 1zfd9 CHANGELOG entry is amended: the dependency failure handling also covers the legacy storage-migration reader, and with a migration required the index phase fails with the receipt and legacy sources retained, naming `wf setup`.

## Scope

**Problem statement:** a failed provisioning step in the upgrade's storage-migration branch is reported as a generic index failure, or escapes the resume path's failure handling, instead of as a dependency failure naming `wf setup`.

**In scope:**

- A shared dependency-failure handler used by the dependency step and by both provisioning calls in the migration-required branch of `phase_index_update`.
- Tests for each caller named in Requirement 3.
- The 1zfd9 CHANGELOG entry.

**Out of scope:**

- `setup_index.ensure_deps` / `ensure_migration_deps` exit behaviour (`wf setup`'s contract).
- The 1zfd9 dependency step's metadata precheck, including its blindness to a venv that needs rebuilding (noted as a possible later change).
- `setup_reconciliation` and `setup_wavefoundry`.
- Storage migration itself (`sqlite_storage_migration`).

## Acceptance Criteria

- [x] AC-1: with a migration required and a legacy Lance store, a failing `ensure_migration_deps` on the default Phase 4 path records `dependency_provisioning_failed=True` and `failed_phase=index_update` in the upgrade lock, the upgrade output carries the `Dependency provisioning FAILED` line naming `wf setup`, the process exits non-zero, `wf_upgrade`'s failure envelope carries the `dependency_provisioning_failed` diagnostic, and the migration receipt and legacy sources are unchanged (`migrate_legacy` and `begin_upgrade_publication` are not called).
- [x] AC-2: the same failure on the resume-after-memory path is handled by that path's `except` (no escaping `SystemExit`, `failed_phase=index_update` stamped), and on `--update-index` it surfaces as the `RuntimeError` with the output line present.
- [x] AC-3: a failing `ensure_deps` in the migration branch is classified the same way as a failing `ensure_migration_deps`; with both succeeding, the migration proceeds as before.
- [x] AC-4: `wf setup` behaviour is unchanged: `ensure_migration_deps` still raises `SystemExit` when its install fails.
- [x] AC-5: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Extract the dependency step's failure handling into a shared helper; use it for both migration-branch calls; raise the migration-pending `RuntimeError` on failure.
- [x] Tests for the default path (with receipt and legacy sources unchanged), resume-after-memory, `--update-index`, an `ensure_deps` failure, a success case, and a `wf setup` `SystemExit` pin.
- [x] Amend the 1zfd9 CHANGELOG entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Routing and tests | implementer | readiness | Single module plus tests |
| Review | code-reviewer, qa-reviewer, release-reviewer | Routing and tests | Upgrade paths |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_startup_install.py`, `.wavefoundry/framework/scripts/tests/test_sqlite_storage_migration.py`
- CHANGELOG.md

## Affected Architecture Docs

N/A: the change reroutes exceptions inside one module (`upgrade_wavefoundry.py`) along the dependency-failure path that 1zfd9 already documented (`docs/architecture/data-and-control-flow.md` Path 7a); no boundary, flow or verification seam changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect on the default path |
| AC-2 | required | The escaping `SystemExit` on the resume path |
| AC-3 | required | Both branch calls share the classification; the success path is unchanged |
| AC-4 | required | `wf setup`'s exit contract must not move |
| AC-5 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Delivery review: code, release and council approve; QA blocked on DEL-AC1-ENVELOPE-UNTESTED (the `wf_upgrade` handler's output-line match had no test; mutant H1 survived). Repaired: `test_server_tools.WaveUpgradeMcpToolTests.test_migration_dependency_failure_carries_the_dependency_diagnostic` (exit 1 with this change's stderr on `preflight_to_docs_gate`, `update_index` and `resume_after_memory`; asserts the `dependency_provisioning_failed` diagnostic and the `wf setup` reason; H1 now fails all three subtests). AC-1's default-path lock and exit clauses are evidenced by composition: the phase raises the `RuntimeError` after the helper writes the flag (`test_startup_install.UpgradeDependencyStepTests`), `main`'s `except BaseException` finalizes `failed_phase=index_update` and re-raises (exit 1), and `test_default_path_failure_keeps_the_dependency_flag_beside_the_failed_phase` shows both lock fields survive on a real lock. Resume test pinned to exit 1. Advisories: wave summary and Risks row corrected | 951 tests across three files OK |
| 2026-09-30 | Implemented. `upgrade_wavefoundry`: `_DEPENDENCY_INSTALL_FAILURES` (exact set), `_MIGRATION_DEPENDENCY_FAILURE`, and `_run_dependency_install(root, install)` extracted from `_provision_upgrade_dependencies` (which now uses it); `phase_index_update`'s migration branch runs `ensure_deps` and, for a legacy Lance store, `ensure_migration_deps` through it and always raises the migration-pending `RuntimeError` on failure, before `migrate_legacy`. Tests: `test_startup_install.UpgradeDependencyStepTests` (reader failure with no receipt, `ensure_deps` failure, success proceeds, unrelated `ValueError` not relabelled) and `test_upgrade_wavefoundry.HistoricalMemoryUpgradeGateTests.test_resume_handles_a_migration_reader_failure_as_a_dependency_failure` (real lock: `failed_phase=index_update`, `dependency_provisioning_failed=True`). `--update-index` has no `except`: covered by the phase-level `RuntimeError`. AC-4 pinned by existing `test_setup_index` and `test_startup_install` exit tests. Mutants (scratch mut-1zep5): old unclassified calls, caught set broadened to `Exception`, return False without a receipt, `ensure_deps` dropped; all caught; the old code makes the resume test error on the escaping `SystemExit`. CHANGELOG 1zfd9 entry amended. Gapfill: none for retrieval (MCP `code_read`/`code_keyword`); edits by Edit tool | 882 tests across the four affected files OK |
| 2026-09-30 | Readiness review (code, QA, release lanes; council red-team and security). B1 adopted via the council alternative: `ensure_deps` is not redundant (the metadata precheck cannot see a venv that needs rebuilding), so it stays and both branch calls share the dependency step's classification; former AC-3 (remove `ensure_deps`) replaced. B2 adopted: AC-1 now names the lock fields, output line, exit and `wf_upgrade` envelope, since no structured summary is produced on this failure. Advisories adopted: raise regardless of receipt state (Requirement 2), `SystemExit` behaviour wording (Requirement 4), `--update-index` and exit-1 scoping (Requirement 3), exact exception set, `test_sqlite_storage_migration.py` added, CHANGELOG amendment detail | readiness review |
| 2026-09-30 | Planned as the follow-up recorded at the close of wave `1zfd9` (reviewer context `1zfd9-reverify-r3`). Traced: `phase_index_update` is the only site calling `ensure_migration_deps` in the upgrade; `phase_index_rebuild` has no migration branch; `setup_reconciliation` is reached only via `setup_wavefoundry` (`wf setup`) | code reading |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Keep the branch's `ensure_deps` and route both branch calls through a helper extracted from the dependency step | Closes the reporting gap without changing 1zfd9's precheck, and keeps `ensure_deps`' venv repair before an in-process migration (readiness B1) | (a) Remove `ensure_deps` and make the precheck also check `_venv_needs_bootstrap`: changes 1zfd9's precheck for a small saving. (b) A local try/except in the branch: duplicates the exception set and message. (c) Make `setup_index` raise a typed exception: changes `wf setup`'s exit contract |

## Risks

| Risk | Mitigation |
| --- | --- |
| The helper broadens the caught set | Requirement 1 fixes the set; `test_an_unrelated_error_is_not_relabelled_a_dependency_failure` fails if it is broadened to `Exception` |
| A caller is missed | Requirement 3 derives the set from every call site; AC-2 tests the paths with distinct failure handling |
| Narrow value: a repo still on Lance runs its old orchestrator for Phase 4 on the default path | Disclosed in Requirement 6; the fix applies to retries, `--update-index` and resume at once |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
