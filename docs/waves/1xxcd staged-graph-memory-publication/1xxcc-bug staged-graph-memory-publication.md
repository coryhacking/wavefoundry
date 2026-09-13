# Isolate staged graph builds from live memory publication

Change ID: `1xxcc-bug staged-graph-memory-publication`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-13
Wave: `1xxcd staged-graph-memory-publication`

## Rationale

Unblock the 1.23-to-1.24 upgrade with active memory backfill. The graph candidate inherits live publication environment but resolves the run in an empty staging memory store. Candidate completion must remain separate from authoritative memory publication. The blocked ppol project needs forward recovery without changing its receipt or archive identity.

## Requirements

1. Complete the receipt-owned schema-8 graph candidate without opening historical-backfill authority in staging, advancing live memory, or overwriting the parent receipt. The existing disposable memory-cache fence may remain staging output; it contains no backfill runs and is never published.
2. Bind isolation to the exact validated candidate directory and identity; restore on exceptions, preserve live guards, and never mutate global environment.
3. Retry retained staged receipts from their source with unchanged package/source ownership, then use ordinary live publication, fresh verification and cleanup.
4. Supply a narrowly hash-pinned ppol repair with check-before-apply and a tested continuation that does not re-extract over the fix. Refuse mismatched files, receipt state/kind, roots and package identity. Do not edit recovery data.

## Scope

In scope: candidate context, epoch finalizer, native tests, local repair kit, focused recovery/architecture documentation and tight changelog entry.

Out of scope: memory relocation, storage strategy changes, graph semantics, version-constant bumps, target-project mutation without an identified target, commit, closure and release.

## Acceptance Criteria

- [x] AC-1: Real schema-7-to-8 migration under active memory and parent-finalize context completes the candidate without creating historical-backfill tables in staging or prematurely changing live runs/receipts.
- [x] AC-2: Isolation refuses other/live or replaced directories, restores after failures, and leaves normal unknown/pending-memory and stale-attempt refusals intact.
- [x] AC-3: Retained staged retry preserves source/package identity and completes live parent publication with matching memory/index identity; source cleanup occurs only after fresh verification.
- [x] AC-4: The pinned ppol repair checks before writing, refuses incompatible inputs, retains backups and recovery data, and has an exercised CLI continuation.
- [x] AC-5: Edited docs distinguish candidate completion from live publication and describe recovery without copying memory or substituting packages.

## Tasks

- [x] Reproduce combined migration and memory failure with negative controls.
- [x] Implement exact-candidate isolation and restoration.
- [x] Verify staged retry, live publication, fresh verification and cleanup.
- [x] Build and test pinned ppol repair and continuation.
- [x] Update docs/changelog, run tests and independent delivery reviews.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Candidate isolation | implementer | readiness | Migration and finalizer |
| Recovery kit | implementer | Candidate isolation | Same canonical fix |
| Verification/review | qa-reviewer | implementation | Independent lanes |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/sqlite_storage_migration.py`
- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/tests/test_sqlite_storage_migration.py`
- `.wavefoundry/framework/scripts/tests/test_storage_upgrade_resume.py`
- `.wavefoundry/framework/scripts/tests/test_index_state_store.py`
- `.wavefoundry/framework/scripts/repair_ppol_memory_staging.py`
- `.wavefoundry/framework/scripts/tests/test_repair_ppol_memory_staging.py`
- `docs/architecture/data-and-control-flow.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`

Also edit root CHANGELOG.md. The implementer owns writes; reviewers are read-only. Framework/seed gates apply. Generate the local repair outside shipped framework assets with tested instructions.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: candidate completion versus authoritative memory publication. Reconcile canonical seed 160 and local upgrade prompt for recovery guidance.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reported blocker |
| AC-2 | required | Preserve live authority |
| AC-3 | required | Recover existing retained state |
| AC-4 | required | Pending receipt cannot switch packages |
| AC-5 | required | Safe operator instructions |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-13 | Context-local scope bound to validated candidate path and identity | No live authority or global environment mutation | Env stripping can affect concurrent writers; redirecting memory root prematurely advances live memory; a generic bypass flag broadens caller authority. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Isolation leaks into live writes | Exact path/identity and restoration/concurrency tests |
| Archive overwrites repair | Exercise retained CLI continuation |
| Recovery manipulates authority | Hash/state/root checks, no receipt rewriting |
| Cross-platform overclaim | Native macOS plus portable tests; no native Windows/Linux claim |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-13 | Confirmed nested graph build inherits live parent memory context. | _migrate_schema8; finalize_build_epoch |
| 2026-09-13 | Readback: the owned graph candidate will complete its own epoch without consuming live memory authorization; ordinary parent publication remains the only authority for the live run. Before: unknown run in staging. After: candidate completes, then live publication gates memory normally. | AC-1 through AC-5; migration/finalizer and native test seams |
| 2026-09-13 | Thought: reproduce first, implement bound isolation, then verify retained recovery and build a pinned repair before delivery review. | Ordered implementation sequence |
| 2026-09-13 | Reflect: the real memory-document CLI fixture creates the pre-existing disposable memory cache, as _staging_allowlist documents. Corrected the overbroad no-file assertion to no staged historical-backfill authority. No memory-invalidation bypass is needed or added; re-Prepare this clarified criterion. | indexer.memory_invalidate; sqlite_storage_migration._staging_allowlist |
| 2026-09-13 | Observe/Reflect: first canonical suite ran 9004 tests with one new fixture failure. Reproduced only with CPU provider: hard-coded full-precision provenance caused a legitimate model-change rebuild. The unchanged-embedding fixture now records the selected provider precision; CPU regression passes. Runtime and distributed repair bytes are unchanged. | /tmp/1xxcd-full-tests.log; /tmp/1xxcd-cpu-retry.log; /tmp/1xxcd-cpu-retry-fixed.log |

| 2026-09-13 | Core isolation implemented. Real schema8 graph reproducer failed before the fix with unknown memory backfill run, then passed. Native parent retry preserves a nonempty vector payload and keeps memory ready until live all/graph publication and fresh-process verification. Exact-path, replaced-directory/file, changed receipt, stale CAS, other-store unknown/pending run, thread and exception checks pass. Migration/state suites: 212 tests, one existing Windows-only skip, 33.265s; `/tmp/1xxcd-core-tests.log`. Package-bound CLI replay and deletion controls remain in progress. | AC-1, AC-2; partial AC-3 |

- Thought / Readback: Repair AC-4 in scope: accept the exact pinned outer or inner ppol checkpoint archive, preserve recovery files, and exercise both retained forms. Existing feature-only validation incorrectly rejected an authentic outer archive. Change only the kit validator and its tests; reissue the kit after verification.

- Observe: AC-4 correction passes 17 kit tests; restoring the feature-only predicate fails the outer archive regression. Exact installed ppol replays pass both outer and feature retained archives (old unknown-run failure, repaired resume exit 0, receipt verified, memory indexed). Kit r2 retains all source/receipt/host checks and never edits checkpoint/package bytes. Evidence: implementation-evidence.json outer_archive_repair_followup.

- Reflect / Observe: Whole suite ran 9006 tests,12 skips; sandbox dashboard probes and loaded TechDocs timing failed. Seven focused environmental rechecks pass outside sandbox/no concurrent suite load. Full-suite receipt remains stale; no closure claim. Independent code/security/release outer-locator review approved. Corrected kit r2 published locally; no target recovery state modified.

- Thought / Readback: Final release adjustments authorized: extend existing native CLI regression to fresh conversion and interrupted outer/feature archive retries through verified cleanup; keep standard upgrade guidance and build local1.24.0 after a current green canonical suite. No new recovery platform or target mutation.

- Observe / Reflect: Final three-case native regression and independent QA/docs review pass. Unsandboxed full suite ran9008 tests with12 skips; only unchanged TechDocs150ms wall-clock assertion failed at244ms under six-worker load. Repeat complete canonical suite with Python runtime PYTHON_CPU_COUNT=2 to reduce concurrency; no test edits or threshold waiver.

- Observe: Complete canonical suite green with two workers:9008 tests,12 skips,673.768s. Receipt inputs_hash04c0bafdcdd744e7c07def5394ba35da6b6bd63593d98e5ebb8894d93473e469 independently matches. No assertion/skip/timeout changes. Packaging local1.24.0 through normal build command; no commit/publish/close.

- Thought / Readback: Operator approved source-host-only packaging cleanup. Exclude the one-off ppol repair utility from archive and generated MANIFEST, retaining source/tests here. This enforces the existing local-repair/non-distribution boundary; test the production build_zip path and a removed-exclusion mutant. No new package, consumer edits or closure requested.

- Observe: Repair utility excluded from future ZIP and MANIFEST;115 packaging tests and independent code/release review pass, removed-exclusion mutant fails. Complete9008-test suite passed (12 skips,682.427s,two workers). Receipt initial hash differs from current tree despite unchanged reviewed file hashes; not overridden or claimed closure-current. No new package, target changes, commit or closure.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
