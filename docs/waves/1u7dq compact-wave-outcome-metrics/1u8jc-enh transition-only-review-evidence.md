# Transition-only review evidence

Change ID: `1u8jc-enh transition-only-review-evidence`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-02
Wave: 1u7dq compact-wave-outcome-metrics

## Rationale

The typed ledger is already the authoritative review state, but it persists
`review_run` and finding-synthesis records and renders several narrative
projections to represent a review process. Record only state-changing review
facts, and render one compact current-state view from those facts.

## Requirements

1. Keep the typed records that the current repair/reverification state machine
   needs for ordering and independent verification. Reduce human-facing review
   projections to current findings and signoffs; do not present run/checkpoint
   bookkeeping as an operator-facing summary.
2. Keep the existing evidence integrity fields, policy receipt validation, and
   approval freshness/independence rules. Do not replace typed evidence with
   free-form prose.
3. Treat `events.jsonl` as the sole current-state authority for declared
   waves. Generate one compact signoff/finding summary from it; no gate,
   dashboard, or tool may parse rendered review prose as authority.
4. Remove stale placeholder/narrative projection blocks that are no longer
   generated. Retain a clearly labeled legacy read path only where existing
   legacy waves require it.
5. Existing declared ledgers containing historical run/synthesis records remain
   readable; the change must not require a broad rewrite or create historical
   duplicate events.

## Scope

**Problem statement:** Review bookkeeping stores and projects process narration
in addition to the transitions needed to explain current review state.

**In scope:**

- Transition-only declared-ledger writing and validation in
  `review_evidence.py`.
- Lifecycle tool paths and compact review projection consumers.
- Focused migration-compatibility, integrity, and no-prose-authority tests.
- Relevant review/evidence prompt and tool-contract documentation.

**Out of scope:**

- Removal of evidence integrity, repair-before-reverification, or
  approval-independence checks.
- Rewriting closed or historical ledgers.
- A new ledger, database, or narrative tracking surface.

## Acceptance Criteria

- [x] AC-1: A new declared-wave review sequence retains the typed records
  required for repair ordering and independent reverification, while its
  operator-facing projection shows only current findings and signoffs.
- [x] AC-2: The compact current-state projection and all lifecycle gates derive
  solely from the declared ledger; modifying rendered prose cannot alter a
  declared wave's signoff or finding state.
- [x] AC-3: Routine review-run/checkpoint bookkeeping is omitted from the
  operator-facing summary, and obsolete placeholder/narrative prose is absent.
- [x] AC-4: A historical declared ledger containing the retired record forms
  remains readable and produces the same current state without mutation.
- [x] AC-5: Finding → repair → fresh independent reverification → approval
  still rejects invalid order, same-context, and same-actor controls.

## Tasks

- [x] Retain the ordering and independent-verification records required by the
  state machine while preserving policy receipt and legacy-read compatibility.
- [x] Replace redundant generated narrative blocks with one compact,
  ledger-derived summary and remove stale placeholders.
- [~] Update lifecycle consumers, tests, and documentation; run the framework
  suite and docs validation. *(Focused evidence/dashboard/docs-lint coverage and docs validation passed; the full suite exits at the host ONNX/CoreML embedding regression before a test result.)*

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Ledger reduction | implementer | — | Keep event authority and integrity rules. |
| Compatibility and contract proof | qa-reviewer / docs-contract-reviewer | Ledger reduction | Exercise new and historical ledgers. |


## Serialization Points

- `review_evidence.py` owns declared-ledger validation, state derivation, and
  the generated current-state projection; all consumers must use it.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`,
`docs/architecture/cross-cutting-concerns.md`, and
`docs/specs/mcp-tool-surface.md` — the review ledger/projection contract and
typed-event vocabulary change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Delivers transition-only evidence. |
| AC-2 | required | Keeps the existing sole-authority safety property. |
| AC-3 | required | Removes repetitive tracking and stale prose. |
| AC-4 | required | Keeps history readable without a migration project. |
| AC-5 | required | Preserves the evidence protocol's load-bearing controls. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-02 | Change drafted from the review-overhead assessment. | `review_evidence.py` currently stores review-run and synthesis records; declared-state reads already fail closed from the ledger. |
| 2026-08-02 | Scope narrowed during implementation: retain ordering records, simplify projection only. | Operator chose the lower-risk path after confirming runs/syntheses are state-machine inputs, not redundant narration. |
| 2026-08-02 | Replaced the projection header with current findings/dispositions and accepted its legacy equivalent for immutable archives. | `test_review_evidence.py`, `test_dashboard_server.py`, `test_docs_lint.py`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-02 | Keep one typed ledger and reduce its operator-facing projection to current state. | It removes repeated process narration without weakening repair ordering or independent reverification. | Rewrite run/synthesis persistence — rejected by operator as a larger lifecycle-state redesign. Replace typed data with Markdown — rejected: reintroduces a parallel authority. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Historical ledgers become unreadable. | Preserve read compatibility and use fixtures containing the retired record forms. |
| Simplification weakens review integrity. | Pin invalid sequencing and independence controls as required tests. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
