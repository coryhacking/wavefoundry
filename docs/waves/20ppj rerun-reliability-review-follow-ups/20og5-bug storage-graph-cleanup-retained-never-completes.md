# Retired graph cleanup: retain and complete instead of refusing forever

Change ID: `20og5-bug storage-graph-cleanup-retained-never-completes`
Change Status: `implemented`
Owner: Engineering
Status: implementing
Last verified: 2026-10-15
Wave: `20ppj rerun-reliability-review-follow-ups`

## Rationale

Change `20qvm` (commit `43621e07`) added identity-bound cleanup of the retired `.wavefoundry/index/graph/` folder inside `cleanup_legacy`. Its requirement said that older receipts without graph evidence, and hosts that cannot delete safely, "preserve and report the directory". The implementation turns both into a permanent refusal: `cleanup_legacy` raises `MigrationRequired`, leaves the receipt at `cleanup_pending`, and every later `--cleanup` raises the same error. Cleanup never reaches `complete` for three populations:

- Native Windows hosts: `_apply_retired_graph_directory` checks `os.supports_dir_fd` and `O_NOFOLLOW` in the APPLY section, after the legacy artifacts, the source database and staging have already been deleted. The earlier `_remove_retired_component` path had a revalidated no-follow fallback for exactly this host class.
- Receipts written before this field existed: `_plan_captured_graph` treats a missing `retired_graph_ownership` as unproven and raises `storage_graph_cleanup_retained` on every run. Before `43621e07` a non-kind receipt skipped graph cleanup entirely and completed.
- A graph folder removed between `_inventory_retired_graph_directory` and the following `lstat()` in `_capture_retired_graph` raises `FileNotFoundError` out of `_new_receipt`, so no receipt is written at all, although the inventory function already maps the same race to `absent`.

"Preserve" must mean the folder stays and cleanup finishes with the retention recorded. It must not mean the upgrade can never finalize.

## Requirements

1. The host capability check (`os.unlink in os.supports_dir_fd` and `os.O_NOFOLLOW`) moves into the PLAN section of `cleanup_legacy`. When the host cannot delete through an identity-checked directory descriptor, the graph plan is classified as retained with a reason naming the missing capability. No deletion of any other component happens before this classification. This preserves the Windows behaviour of refusing fd-less graph deletion while keeping cleanup terminal. The POSIX fd-anchored path on macOS, Linux and WSL2 is unchanged.
2. A graph plan classified as retained (unowned contents, missing or changed ownership evidence, or missing host capability) does not raise. `cleanup_legacy` proceeds through the APPLY section, records `graph_directory_cleanup` with `state`, `path`, `entries` and `reason`, and ends at `state == "complete"`. The receipt keeps the retained reason so an operator can delete the folder by hand or rebuild.
3. A receipt that predates `retired_graph_ownership` (field absent) is retained under requirement 2 with a reason saying the receipt predates ownership capture. The folder is never adopted by name alone: the only evidence that grants deletion is a captured identity set, exactly as `20qvm` decided.
4. `_capture_retired_graph` handles `FileNotFoundError` from its `lstat()` and from iterating children by returning `{"state": "absent"}`, matching what `_inventory_retired_graph_directory` already reports for the same race.
5. Existing retained reasons keep their current wording where tests assert on it; the new capability reason and the predates-capture reason are new strings. The `storage_graph_cleanup_descriptor_unavailable` error no longer exists as a raised exception; the tests that currently assert it move to asserting the retained-and-complete outcome.
6. Windows, macOS, Linux and WSL2 behaviour: on POSIX hosts with `dir_fd` support, a captured and unchanged folder is deleted as today. On native Windows the folder is always retained and cleanup completes. A receipt from before ownership capture is retained and completes on every platform.

## Scope

**Problem statement:** retained-graph outcomes are implemented as permanent refusals, and one of them fires after irreversible deletions have begun.

**In scope:**

- `_plan_captured_graph`, `_apply_retired_graph_directory`, `_capture_retired_graph` and the PLAN/APPLY ordering in `cleanup_legacy` in `sqlite_storage_migration.py`
- The three existing tests that assert `descriptor_unavailable`, plus new regressions for each retained population
- The upgrade seed and rendered guidance sentence that describes retained graph cleanup, if its wording claims a refusal

**Out of scope:**

- Adopting a graph folder by name for old receipts (deliberately refused by `20qvm`)
- Changing any other `cleanup_legacy` component (artifacts, source retirement, staging)
- A Windows fd-less deletion path for the graph folder

## Acceptance Criteria

- [x] AC-1: With `os.supports_dir_fd` patched to exclude `os.unlink`, `cleanup_legacy` on a receipt whose graph inventory is removable completes with `state == "complete"`, the graph folder still present, `graph_directory_cleanup.state == "retained_unowned_contents"` and a reason naming the missing capability, and no artifact, source or staging deletion observed before the classification (asserted through ordering of filesystem mutations or a plan-section probe).
- [x] AC-2: A receipt in `verified` or `cleanup_pending` state without the `retired_graph_ownership` field completes cleanup with the graph folder retained and a reason recorded; a second `cleanup_legacy` call returns the complete receipt without raising.
- [x] AC-3: A captured receipt whose folder identities still match deletes the folder on a POSIX host, proving requirement 1 and 2 did not weaken the existing deletion path.
- [x] AC-4: `_capture_retired_graph` returns `{"state": "absent"}` when the folder disappears after inventory (patched `lstat` raising `FileNotFoundError`), and `_new_receipt` writes a receipt in that case.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Reproduce each of the three populations through `cleanup_legacy` with a bounded fixture before editing.
- [x] Move the capability check into the PLAN section and classify as retained; stop raising on retained plans; record `graph_directory_cleanup` and finish at `complete`.
- [x] Return `absent` from `_capture_retired_graph` on the inventory-to-lstat race.
- [x] Rewrite the three `descriptor_unavailable` tests and add regressions for AC-1 to AC-4.
- [x] Check the upgrade seed and rendered guidance for wording that promises a refusal; correct the seed first and regenerate.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Migration fix and tests | Implementer | Readiness | Single write owner |
| Seed and guidance wording | Implementer | Migration fix | Seed first, then regenerate |
| Delivery review | QA and required reviewers | Both | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/sqlite_storage_migration.py`
- `.wavefoundry/framework/scripts/tests/test_sqlite_storage_migration.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_rerun_reliability.py`
- `.wavefoundry/framework/seeds/`

## Affected Architecture Docs

N/A. The change keeps the PLAN-then-APPLY structure of `cleanup_legacy` and only reclassifies outcomes inside one module. `docs/architecture/data-and-control-flow.md` already describes the retained-receipt flow from `20qvm`; update its sentence only if it states that retained graph cleanup refuses.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Windows upgrade cannot finalize today |
| AC-2 | required | Every pre-existing pending receipt is blocked today |
| AC-3 | required | Guards against weakening the deletion path |
| AC-4 | important | Race is narrow but loses the receipt entirely |
| AC-5 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Readback: retention currently raises before APPLY; unavailable descriptors raise after other cleanup; post-inventory capture disappearance escapes. Smallest fix: classify capabilities in the graph planner, retain and complete without adopting old evidence, catch capture disappearance, and keep fd identity checks unchanged. Verify bounded cleanup populations, real native deletion, disappearance receipt creation, and named guard mutants. | Implementer; actual runtime model identity unknown. MCP code_outline/code_read/code_keyword confirmed callable; root AGENTS.md applies; profile code_patterns has insufficient_history. Coordinator owns shared rerun tests and seed/guidance inspection; full suite and docs gate remain pending. |
| 2026-10-15 | Planned from the code review of `43621e07` | Review findings 1, 2 and 8 |
| 2026-10-15 | Reconciliation note: on hosts without descriptor-anchored deletion this change retains the graph folder permanently, while `20qrr` (wave `20qrv`) adds a bounded by-path fallback for the embedded archive. The asymmetry is deliberate: the graph folder is a few bounded files and `20qvm` chose descriptor-anchored deletion only, whereas the archive can reach the pack byte ceiling. | Cross-wave plan review; no requirement or AC changed |
| 2026-10-15 | Scope held to the reviewed receipt: the post-readiness addendum (zero-`st_ino` volumes as a fifth retained population; a `phase_cleanup` handler for refusals that escape `cleanup_legacy`) was withdrawn rather than re-readied. Zero-identity volumes already complete under requirement 2 because capture records no ownership and the plan reports retained; add that case as one regression under AC-1/AC-2 at implementation, no new code. The `phase_cleanup` handler addresses pre-existing tamper refusals (artifact identity, staging), not a regression of `43621e07`; plan it separately if a field report shows the traceback. | Ledger shows no readiness record mentioning the addendum; operator rule: favor reduced work while maintaining quality |

| 2026-10-15 | Implemented retain-and-complete, capability classification before all deletion, old-receipt non-adoption and capture disappearance handling. AC-1–AC-4 and implementation tasks complete; AC-5 remains open for final docs and combined framework gates. | Before source edit: capability ordering failed, old/changed/zero evidence and unsupported host raised, and directory-lstat/iterdir/child-lstat disappearance each lost receipt. After fix: graph subset 12 tests green; full migration module 133 tests / 1 skip green in 28.705 s. Native schema-8 deletion control passed on this POSIX host; descriptor absence and zero evidence are synthetic controls, not native Windows qualification. |
| 2026-10-15 | Four named source guard mutants were detected without skips. Shared descriptor test and guidance census completed by coordinator; seed 160 contains no retired-graph refusal promise, so no seed edit/render was needed. | `late-capability-classification` → `test_graph_descriptor_capability_is_classified_before_any_cleanup` (1 failure); `old-receipt-name-adoption` → `test_old_graph_receipts_complete_without_adopting_ownership` (1 failure, 1 error); `retention-permanent-refusal` → `test_changed_and_zero_graph_identities_retain_and_complete` (3 errors); `capture-disappearance-escapes` → `test_graph_disappearance_during_capture_still_writes_receipt` (3 errors). Mutations compiled in memory; shipped source was never replaced. Coordinator confirmed shared rerun branch now asserts retained plan/zero APPLY and completed guidance audit. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Retain and complete: retained graph plans record a reason and let cleanup finish | Matches the `20qvm` intent ("preserve and report") and makes the upgrade terminal on every host | (a) Refuse in PLAN before any deletion, keeping the receipt pending: still never terminal on Windows or for old receipts, operator must delete by hand to finish. (b) Add a Windows no-follow fallback for the graph folder: new deletion mechanism on the platform least covered by tests, and `20qvm` chose fd-anchored deletion only. |
| 2026-10-15 | Old receipts stay retained rather than lazily capturing ownership | A capture at cleanup time would adopt whatever is in the folder by name, which `20qvm` explicitly refused | Lazy capture at plan time (rejected: name-based adoption) |

## Risks

| Risk | Mitigation |
| --- | --- |
| A retained folder on Windows accumulates across upgrades | Receipt records the reason; guidance tells the operator how to remove it by hand |
| Tests that assert the old refusal string hide a silent weakening of deletion | AC-3 keeps a positive deletion test on POSIX |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
