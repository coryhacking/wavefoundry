# Active-memory budget and consolidation

Change ID: `1u7uy-enh active-memory-budget-and-consolidation`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-02
Wave: 1u7dq compact-wave-outcome-metrics

## Rationale

The active memory corpus has grown past the point where every record improves
action-time guidance. It already has safe archival and duplicate detection, but
no active-budget decision or file-specific consolidation workflow. Add one
small, explicit curation path rather than more automatic memory behavior.

## Requirements

1. Set an active-memory budget of 50 active records. Candidate, stale,
   superseded, rejected, and archived records do not consume it.
2. Surface budget state and a deterministic curation list through the existing
   memory-reconciliation path; do not automatically archive, delete, or merge
   records merely because the cap is exceeded.
3. When active `fragile_file` records target the same canonical file, offer a
   file-specific consolidation candidate that preserves the source records via
   explicit supersession links and a single actionable playbook.
4. Use the existing retention review and archive flow for superseded/rejected
   records. Protected kinds still require current evidence and explicit
   eligibility confirmation before archival.
5. Keep default action-time advisories bounded to the active corpus and retain
   historical retrieval only through the existing explicit history paths.

## Scope

**Problem statement:** Memory growth is visible but not bounded, and related
fragile-file lessons remain fragmented even when they target the same file.

**In scope:**

- Active-budget calculation and reconciliation output in the existing memory
  record/tool path.
- Deterministic file-target grouping and explicit consolidation proposal for
  active `fragile_file` records.
- Docs, lifecycle guidance, and focused tests for cap, non-destructive review,
  supersession, and archival eligibility.

**Out of scope:**

- Automatic deletion, automatic archival, or automatic rewrite of a memory.
- A new memory store, vector index, scheduler, or per-record telemetry.
- Changing existing decay/confidence scoring beyond excluding non-active
  history from the 50-record cap.

## Acceptance Criteria

- [x] AC-1: The memory view reports active count, cap 50, remaining capacity,
  and a deterministic curation list only when the cap is reached or exceeded.
- [x] AC-2: Candidate, stale, superseded, rejected, archived, and pointer
  records do not consume the active-memory budget or surface as normal active
  advisories.
- [x] AC-3: Multiple active `fragile_file` records with the same canonical
  file target produce one consolidation proposal/playbook input; distinct
  targets do not merge.
- [x] AC-4: Consolidation requires an explicit review action and leaves source
  records intact until they are explicitly superseded and, where appropriate,
  archived through the current eligibility path.
- [x] AC-5: Protected-kind retention checks, history retrieval, and current
  duplicate detection remain valid after the budget is introduced.

## Tasks

- [x] Add the fixed-cap calculation and bounded curation response to the
  existing memory reconciliation/read path.
- [x] Add deterministic fragile-file grouping and an explicit consolidation
  proposal that uses existing supersession/archival operations.
- [x] Update memory documentation and close/reconciliation guidance.
- [~] Run focused tests, framework tests, and documentation validation. *(Focused memory coverage and docs validation passed; the full suite exits at the host ONNX/CoreML embedding regression before a test result.)*

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Budget and grouping | implementer | — | Reuse the record parser and reconciliation seam. |
| Retention verification | qa-reviewer / docs-contract-reviewer | Budget and grouping | Prove curation is explicit and history remains safe. |


## Serialization Points

- `memory_records.py` owns record status, duplicate comparison, and archival
  eligibility; the existing `memory_reconcile` tool remains the mutation seam.

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` and
`docs/architecture/testing-architecture.md` — document the bounded active
corpus and its non-destructive retention test matrix. Update the memory README
and MCP tool specification for the curation result.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Makes the active budget visible and actionable. |
| AC-2 | required | Keeps history from inflating normal guidance. |
| AC-3 | required | Reduces fragile-file fragmentation. |
| AC-4 | required | Preserves explicit human judgment and history. |
| AC-5 | required | Guards the existing retention safety contract. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-02 | Change drafted from the memory-aging assessment. | Existing code excludes retired records from default advisories and supports explicit archival, but has no active cap or consolidation proposal. |
| 2026-08-02 | Added the active-50 budget and read-only same-file curation candidates to `memory_brief`. | `test_memory_records.py`; memory contracts and architecture docs. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-02 | Use a fixed 50-record active cap with explicit curation and file-target grouping. | It bounds working memory without automatic data loss. | Automatic eviction — rejected: unsafe for fragile-file knowledge. A configurable scoring system — rejected: overengineered for the current objective. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Cap creates hidden loss of useful knowledge. | Exceeding the cap only surfaces a curation list; it makes no automatic mutation. |
| Consolidation merges unrelated lessons. | Require exact canonical file-target equality and explicit human supersession. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
