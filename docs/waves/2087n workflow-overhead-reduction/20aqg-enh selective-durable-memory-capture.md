# Select useful memories before creating files

Change ID: `20aqg-enh selective-durable-memory-capture`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: `2087n workflow-overhead-reduction`

## Rationale

Closing2071p required a generic repaired-docstring draft whose target was temporary tooling, then a permanent rejection record to unblock close. A repaired finding is history, not automatically a new actionable memory. Filter real targets and review usefulness before creating candidates.

Evidence: the recent-ten-wave audit and final cleanup are summarized in `docs/waves/2071p bounded-reconciliation-reporting/wave.md` and `docs/waves/2071n profile-skip-qualification/wave.md`. Existing unique proof and ledger citations remain available. This plan does not claim future implementation tests passed.

## Requirements

1. Automatic draft targets must identify existing contained repository files, not absolute/temporary paths normalized into nonexistent repository anchors, linked escapes or generic verification harnesses. Keep valid repaired-surface and decision targets; omitted sources remain visible in bounded proposal diagnostics.
2. Keep a dry-run proposal view and add explicit source-event selection for creating eligible candidates. The server derives candidate bodies and source identities from the real wave; unknown/ineligible selections fail before writes, retries preserve source dispositions and existing duplicate safeguards. Existing unselected proposals create no files.
3. The coordinator assesses concrete future action and canonical overlap before selecting candidates. It records the retrospective and no-new-memory rationale inline in wave.md when nothing warrants retention. Do not add a semantic model, new closure sidecar or per-finding negative record merely to represent ordinary repair history.
4. Closure still requires validation of actual selected pending candidates and preserves rejected/superseded history, but does not demand a physical candidate or rejection file for every automatically proposed repair. Preserve typed review authority and operator closure permission. A selected candidate whose target later disappears or falls outside automatic drafting still remains pending and blocks; filtering proposals must not hide actual unvalidated records linked to this wave.
5. Do not delete or reclassify existing decisions/preferences/fragile-file records, run broad memory maintenance, or force a new historical backfill on ordinary upgrades. Existing validated useful memories and their source-event replay remain stable.

## Scope

**Problem statement:** Closing2071p required a generic repaired-docstring draft whose target was temporary tooling, then a permanent rejection record to unblock close. A repaired finding is history, not automatically a new actionable memory. Filter real targets and review usefulness before creating candidates.

**In scope:** the named behavior, its existing module owners, finite contract regressions and affected documentation. Canonical seeds are edited first; generated lifecycle/role surfaces are regenerated from those seeds, not patched as a substitute.

Expose selection as an additive memory_propose argument carrying source-event IDs. Existing dry-run proposals remain compatible. A create request without explicit selection creates nothing and explains the needed selection; this intentional write-path change must be documented in the tool schema and close prompt. Explicit empty selection is an idempotent no-op. Close reads all actual wave-linked pending candidates, including those no longer draft-eligible, and never treats a no-new-memory note as validation of an existing candidate. Targets are checked at proposal and immediately before creation. A routine repair is not automatically a future instruction.

**Out of scope:** graph-query provenance wave2071o, unrelated scanner repairs, mandatory-lane removal, weakening full lifecycle gates, rewriting ledger history, release/tag/publish, new broad maintenance during consumer upgrades and product-wide refactoring. No implementation is authorized by this planning pass.

## Acceptance Criteria

- [x] AC-1: Temporary, missing and escaping targets do not produce automatic repository-anchored drafts; a genuine contained repaired target still does. Oracle: proposal public path with invalid and useful target controls.
- [x] AC-2: Selecting a useful source creates only that candidate with stable derived source identity; empty selection writes nothing, invalid selection writes nothing, duplicate/rejected replay stays idempotent. Oracle: real proposal/create/retry matrix.
- [x] AC-3: Close accepts an honest no-new-memory retrospective without manufacturing rejection files, while an actual pending selected candidate still blocks until validated. Oracle: declared-wave close-gate controls with paired pending/validated/no-candidate states.
- [x] AC-4: Useful decisions and existing source dispositions remain unchanged, and ordinary upgrade does not trigger broad recuration or a new historical backfill. Oracle: byte/state comparisons and a finite upgrade/backfill control.

## Tasks

- [x] Implement the scoped requirements in the existing owning modules and canonical instructions.
- [x] Execute the finite positive and known-bad controls named in the ACs through actual public/registered paths; record observations and limits in wave.md.
- [x] Update affected architecture and operator contracts; regenerate affected local surfaces from canonical seeds.
- [x] Run required independent delivery review and fresh framework qualification after source edits; consolidate useful long-run evidence and current handoff without routine per-seat files.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| implementation | implementer | readied wave and later operator activation | Existing module owners; no code edit during readiness. |
| focused verification | qa-reviewer | implementation | AC-scoped real controls; preserve independent judgment. |
| delivery lanes | required specialists | verified implementation | Existing selected authority, no new roster. |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/memory_supply.py`
- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/seeds/190-close-wave.prompt.md`
- `.wavefoundry/framework/seeds/240-memory-review.prompt.md`

One implementer owns shared server_impl.py, seed190, build-and-verification and generated outputs. Qualification, memory and advisory changes settle their APIs before the compact-workflow instructions describe them. Index work may be isolated; final integration and canonical receipt run are serialized after all framework edits. Reviewer contexts do not edit source or plans.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/cross-cutting-concerns.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | All four ACs are required to protect useful capture, source identity, pending-candidate enforcement and preserved history while eliminating mandatory rejection files. |
| AC-2 | required | All four ACs are required to protect useful capture, source identity, pending-candidate enforcement and preserved history while eliminating mandatory rejection files. |
| AC-3 | required | All four ACs are required to protect useful capture, source identity, pending-candidate enforcement and preserved history while eliminating mandatory rejection files. |
| AC-4 | required | All four ACs are required to protect useful capture, source identity, pending-candidate enforcement and preserved history while eliminating mandatory rejection files. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | Consolidated plan; implementation and delivery ACs remain unmet. | Current requirements and named AC oracles; operator requested create/prepare/review. |

| 2026-10-09 | Readback: Review and explicitly select useful contained source events before memory files are created; all actual pending wave-linked candidates still block close (AC-1–4). Update memory_supply, memory_handlers, server_impl wrappers/gate, seeds190/240 and tests. Before: every repair requires a candidate or rejection; after: selected useful memories plus inline no-new-memory rationale. | Operator implementation request; admitted ACs unchanged. |

| 2026-10-09 | Implemented current contained target filtering, explicit source-event selection, independent pending-record close census and source disposition replay. | 233 memory-record tests and 56 historical/setup backfill tests passed; temporary captures only. |

| 2026-10-09 | Guard mutants in a complete temporary framework tree were detected: bypass selection gate, bypass contained-target filter, and suppress actual pending-wave match. The first incomplete temporary copy lacked an install asset and was discarded, then each corrected baseline passed before mutation. | Named controls: test_selection_required_empty_invalid_and_single_source; test_current_target_filter_and_omission_diagnostics. Public response and pending gate changed for the targeted reason (rc0 to rc1). Added post-draft target-movement refusal. |

| 2026-10-09 | memory_propose additive source_events is an intentional served-schema contract change, including declared-profile golden. | Explicit selection requirement documented in tool and MCP spec; regenerate goldens after the source freeze and verify without update flag. |

| 2026-10-09 | Target preflight guard deleted in complete temporary framework: green named baseline became intended status assertion failure (ok versus required error); production source unchanged. | MemoryProposeTests.test_target_movement_after_drafting_refuses_before_writes; baseline 1 passed, mutant 1 failure. Default/declared tool golden update changed exactly source_events; 25 worker tests passed, expected outer fixture-write guard. Final verification without update flag follows. |

| 2026-10-10 | Implementation complete; all tasks and ACs met. Required independent delivery lanes approved and current canonical qualification passed. | wave.md retains consolidated proof and limits; events.jsonl holds typed authority. Fresh source receipt bfdf8d1ecb910925f9633f3ff215385ca38110310d77faf1bc9f74114695f7af; 12,108 tests/181 files/13 skips; no closure or commit authorized. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-09 | Adopt the scoped approach above for readiness review. | Concrete ten-wave waste and current source owners support a bounded repair; retain quality and authority boundaries. | Selected pre-creation human usefulness review, contained target validation and explicit source selection. Rejected generic automatic memory creation for every repair because it duplicates history and creates rejection chores. Rejected disabling memory capture because useful future actions and existing validated history still matter. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Saving work conceals missing proof or stale authority. | Required negative controls, exact input identities, retained unique evidence and unchanged full gates. |
| Cross-change source ownership causes conflicting edits. | Shared-file serialization; canonical seeds first; focused independent integration review. |
| Upgrade performs unrelated maintenance. | Consumer upgrade trace and explicit no-source-suite/no-extra-evidence boundary in every applicable contract. |

## Session Handoff

Planned for readiness review only. See `docs/agents/session-handoff.md`; no code edited under this wave, no AC marked complete and no OPEN slot taken.
