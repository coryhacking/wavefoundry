# The Read-Only Archive Root Is Never Rewritten or Reported as Live

Change ID: `1zim7-bug archive-root-left-untouched`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zim5 profile-portable-test-suite

## Rationale

Wave 1z827 made `record_paths.ARCHIVE_ROOT` a read-only root for older records kept under their old vocabulary. Running the framework suite under the second profile (1zim5, `run_tests.py --profile second`, where the archive root is `docs/waves`) found two paths that still treat it as live:

- `memory_records.migrate_memory_ids_to_lifecycle_naming` gathers reference-repair candidates from `docs/**`, the plans root and the waves root. Only paths under the live waves root get the closed-wave filter, so a record under an archive root inside `docs/` is rewritten (`mem-alpha-lesson` became `3btr5-mem alpha-lesson` in `docs/waves/1arc archived/wave.md`).
- `review_policy_reconcile._live_markdown_excluded_prefixes` adds the live waves root to the static exclusions but not the archive root, so the review-policy upgrade preflight reports an archived record as "retired lifecycle prose outside a registered carrier" and tells the operator to rewrite it by hand.

Both are reachable in a distribution that configures an archive root under `docs/`; neither is reachable with the shipped defaults (no archive root).

## Requirements

1. **Memory id migration.** The reference-repair pass in `migrate_memory_ids_to_lifecycle_naming` never reads or writes a file under the configured archive root (resolved through `record_paths.load_record_roots`, so the same root the reader uses), wherever the unioned candidate set reaches it (record-layout validation keeps the archive out of the plans and waves roots, so in practice through the `docs/**` walk). The `memory_backfill_sources` repair is index state, not an archived record, and keeps repairing rows for archived sources. The memory-root branch is decided before the archive exclusion, so live memory records are never skipped. Archived records keep their text byte for byte.
2. **Review-policy preflight.** `_live_markdown_excluded_prefixes` excludes the configured archive root as well as the live waves root, so archived records are neither reported nor rewritten.
3. **No archive, no change.** With no archive root configured, both functions behave exactly as today.
4. **Platforms.** Windows, macOS, Linux and WSL2 behave the same (prefix comparison on repository-relative POSIX paths, as the existing waves-root exclusion does).
5. **Transition.** Bug fix; CHANGELOG under `### Fixed` in `## [Unreleased]`.

## Scope

**Problem statement:** two maintenance paths treat records under the read-only archive root as live documents.

**In scope:**

- `memory_records.migrate_memory_ids_to_lifecycle_naming` (reference pass), `review_policy_reconcile._live_markdown_excluded_prefixes`; regression tests; CHANGELOG.

**Out of scope:**

- How retrieval, drift and the graph treat archived records (demotion weights, `compute_doc_drift`, graph doc-scan exclusions, retrieval-eval carrier classes). Wave 1z827 left archived documents indexed as documents; whether they should be demoted or treated as historical is a separate decision for the operator.
- Walks limited to `docs/agents/**` (`upgrade_extensions` role-field backfill, `agent_surface_integrity`): an archive root under `docs/agents/` is not addressed here.

## Acceptance Criteria

- [x] AC-1: with an archive root configured inside `docs/`, `migrate_memory_ids_to_lifecycle_naming` leaves an archived record holding a legacy memory reference byte-identical while still repairing the same reference in a live document; the existing test `test_memory_records.LifecycleMemoryIdTests.test_migration_rewrites_live_docs_and_preserves_archives` passes under the default and second profiles. A default-profile unit test patches `record_paths.ARCHIVE_ROOT` to a root inside `docs/` and asserts the same byte-identity; the second-profile run is corroboration, not delivery evidence.
- [x] AC-2: with an archive root configured, the review-policy preflight does not report an archived record holding retired lifecycle prose, and still reports the same prose in a live document; `test_review_policy.ReviewPolicyReconcilerTests.test_live_markdown_outside_registered_carriers_is_reported_not_rewritten` passes under both profiles. A default-profile unit test patches `record_paths.ARCHIVE_ROOT` and asserts the archived path is absent from, and the live path present in, the preflight message.
- [x] AC-3: with no archive root, both functions' results are unchanged (existing tests pass unmodified).
- [x] AC-4: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Exclude the archive root in the memory id migration's reference pass.
- [x] Exclude the archive root in the review-policy preflight.
- [x] Regression tests under a configured archive root (default-profile unit tests, plus the two existing tests under the second profile).
- [x] CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Archive exclusions | implementer | readiness | two small production edits |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/memory_records.py`, `.wavefoundry/framework/scripts/review_policy_reconcile.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`, `.wavefoundry/framework/scripts/tests/test_review_policy.py`

## Affected Architecture Docs

N/A: two exclusion-list fixes inside existing modules; no boundary, flow or verification change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Archived records must never be rewritten |
| AC-2 | required | The preflight must not direct the operator at read-only records |
| AC-3 | required | No behaviour change without an archive |
| AC-4 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Implemented. `migrate_memory_ids_to_lifecycle_naming` skips any candidate under `load_record_roots(root).archive` in a branch placed after the memory-root branch and before the waves-root branch, so archived files are never read or written and live memory records are never skipped; `memory_backfill_sources` repair is unchanged. `_live_markdown_excluded_prefixes` appends `archive_rel + "/"` when an archive root is configured. No shared `record_paths` predicate was added (two one-line checks did not justify it). Platforms: the memory pass compares `Path.is_relative_to` on root-joined, unresolved paths exactly like the existing waves-root check, and the preflight compares repository-relative POSIX prefixes exactly like the existing waves-root exclusion, so Windows, macOS, Linux and WSL2 behave the same. New default-profile tests patch the `record_paths` module the production code reads (`ARCHIVE_ROOT` = `docs/archive-records`, and `docs/agents` to contain the memory root); each failed before the fix (archived record rewritten to the new id; archive prefix missing and archived path reported), and the ordering test also fails when the archive branch is moved before the memory-root branch. Also (1zim6 Requirement 3 follow-up) the closed record in `test_sqlite_storage_migration.test_candidate_scope_is_exact_thread_local_and_exception_safe` is now built in the live waves root and vocabulary. All three files pass under the default and second profiles. Gapfill: MCP code navigation returned `index_runtime_stale` (server needs a restart), so navigation fell back to grep and direct reads | `test_memory_records.LifecycleMemoryIdTests.test_migration_leaves_configured_archive_root_byte_identical`, `test_migration_repairs_live_memory_records_inside_an_archive_root`, `test_migration_rewrites_live_docs_and_preserves_archives`; `test_review_policy.ReviewPolicyReconcilerTests.test_configured_archive_root_is_excluded_from_live_markdown_preflight`, `test_live_markdown_outside_registered_carriers_is_reported_not_rewritten`; `run_tests.py --file` and `--profile second --file` OK for `test_memory_records.py` (230), `test_review_policy.py` (105), `test_sqlite_storage_migration.py` (116) |
| 2026-10-01 | Planned from the 1zim6 migration: both defects reproduced under `run_tests.py --profile second` by assertions that write a record under the archive root when one is configured; code read confirms the reference pass walks `docs/**` with the closed-wave filter only under the live waves root, and the preflight's exclusions add only the live waves root | `memory_records.migrate_memory_ids_to_lifecycle_naming`; `review_policy_reconcile._live_markdown_excluded_prefixes` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Fix inside wave 1zim5 rather than leave the two tests failing | 1zim6 AC-1 needs the second-profile run to pass, and the defects are small and well located | Plan separately and mark the tests (rejected: marking would hide a real defect) |
| 2026-10-01 | Leave retrieval treatment of archived records out of scope | A design decision 1z827 deliberately left open, not a defect shown by a failing test | Demote archived records in this change |

## Risks

| Risk | Mitigation |
| --- | --- |
| An archive root outside `docs/` is reached by another walk | Exclude by the resolved archive prefix wherever the pass gathers candidates, not only under `docs/` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
