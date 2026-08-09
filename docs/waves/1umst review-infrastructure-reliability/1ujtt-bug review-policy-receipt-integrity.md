# Review Policy Receipt Integrity

Change ID: `1ujtt-bug review-policy-receipt-integrity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-06
Wave: 1umst review-infrastructure-reliability

## Rationale

Solaris found three receipt-integrity failures in ordinary prepare and delivery review. The lane evaluator scores an undeclared change document with raw substring membership, so a Progress Log mention of `events.jsonl` recruits the JavaScript-triggered code lane. Meanwhile the digest deliberately excludes the Progress Log, yielding a stable digest for a changed roster. Normal lifecycle metadata (`Status:` and `Last verified:`) is also hashed as if it were a behavioral contract change, lapping approvals during the workflow's own status transitions. Finally, a rotating council seat changes `council_seats`, which is treated as receipt-semantic even when the digest and required lane roster have not changed.

These faults make the receipt disagree with the policy it is meant to bind: non-policy prose can create work, policy-significant changes can go unbound, and incidental metadata can invalidate completed review.

## Requirements

1. Lane selection and `policy_input_digest` must operate over one identical canonical representation of each admitted change document.
2. The undeclared-document fallback must match only path-shaped trigger occurrences with the same boundary semantics as declared serialization points; arbitrary prose substrings, including framework filenames such as `events.jsonl`, must not recruit a lane.
3. Each fallback reason must identify the matched token and an unambiguous document location or excerpt sufficient to diagnose why it selected a lane.
4. Canonical policy input must normalize lifecycle-managed change-doc metadata that does not describe scope or behavior, including the `Status:` and `Last verified:` header lines, while preserving substantive metadata and all contract text.
5. A receipt must supersede only when a binding policy dimension changes. A rotating council-seat selection with unchanged canonical digest, required lanes, delivery mode, and other coverage fields must not lapse approvals.
6. The council-seat snapshot recorded with a receipt, any generated council brief, and readiness validation must share one canonical source for that receipt; no response may report conflicting seats.
7. The policy evaluator version and regression coverage must prove both direct evaluator behavior and public lifecycle convergence from a prior receipt.

## Scope

**Problem statement:** The review-policy evaluator has mismatched selection, hashing, and receipt-supersession inputs, so it can silently over-recruit lanes, fail to supersede when coverage changes, and supersede when coverage does not.

**In scope:**

- Canonical policy-body normalization and fallback-token matching.
- Receipt semantic comparison, council-seat snapshot/brief alignment, diagnostic reasons, and evaluator-version transition behavior.
- Unit and public lifecycle regressions for the reported cases.

**Out of scope:**

- Replacing the legacy fallback for waves that predate Serialization Points; it remains supported with corrected matching.
- Changing the configured lane taxonomy, risk triggers, or council-selection policy.
- Retroactively rewriting closed ledgers.

## Acceptance Criteria

- [x] AC-1: An undeclared document that mentions `events.jsonl`, `.js`, or a trigger token in explanatory prose does not recruit a path-triggered lane; a real path-shaped occurrence still does.
- [x] AC-2: Every fallback-selected lane receipt reason names its exact trigger and source location/excerpt.
- [x] AC-3: Adding or removing a Progress Log row cannot change required lanes without also changing `policy_input_digest`; non-Progress Log policy text that changes lane selection changes the digest.
- [x] AC-4: Updating only `Status:` or `Last verified:` leaves the digest and current receipt valid, while a substantive header/body change still supersedes it.
- [x] AC-5: Repeated dry runs with a changed rotating-seat candidate, but identical binding policy fields, do not append a receipt or lapse otherwise-current approvals.
- [x] AC-6: The generated council brief, persisted receipt, and council-seat validator agree on the same recorded seat roster.
- [x] AC-7: Direct policy tests plus a public prior-evaluator receipt convergence test pass, including a test that observes exactly one required append for a real policy change.

## Tasks

- [x] Define and test one canonical change-text carrier used by both scoring and digesting.
- [x] Replace raw fallback substring membership with boundary-aware, location-carrying matching.
- [x] Normalize lifecycle-only metadata in the canonical carrier and add negative controls for substantive text.
- [x] Separate receipt-binding fields from rotating-seat operational metadata and align the brief/validator source.
- [x] Bump the evaluator version and add direct, lifecycle, and regression tests.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| canonical policy input | implementer | none | Shared scoring/digest carrier |
| receipt semantics | implementer | canonical policy input | Seat snapshot and supersession |
| regression coverage | qa-reviewer | both | Direct and public-lifecycle convergence |

## Serialization Points

- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/gardener_metadata.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` must document the receipt/reason contract if its response shape changes. No broader architecture change is expected: this corrects consistency inside the existing policy-evaluation boundary.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevents phantom required lanes. |
| AC-2 | important | Makes selection diagnosable. |
| AC-3 | required | Restores digest/roster soundness. |
| AC-4 | required | Prevents lifecycle bookkeeping from invalidating review. |
| AC-5 | required | Prevents approval churn without coverage change. |
| AC-6 | required | Removes contradictory authority. |
| AC-7 | required | Pins the evaluator upgrade path. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-06 | Filed from Solaris 1.15.4+ph68 field report; source reads confirmed raw fallback substring matching, separate digest normalization, and seat-inclusive receipt comparison. | `review_policy.py:460-588,625-685`; `gardener_metadata.py:140-159` |
| 2026-08-06 | Implemented canonical fallback scoring, receipt-bound council roster handling, and evaluator v5 convergence coverage. | `test_review_policy.py`; `test_server_tools.py` focused lifecycle regression |
| 2026-08-06 | **P1 repaired: the canonicalization covered only one of two receipt-semantic readers.** `extract_full_council_triggers` and `_select_prepare_council_rotating_seat` still consumed raw change text, so a mandated Progress Log row carrying a trigger word could flip `delivery_council_required`, supersede the receipt and lapse approvals while `policy_input_digest` stayed byte-identical, leaving no diagnostic able to explain it. Both now read the same canonical carrier as lane scoring. | `server_impl.py:7109-7131` |
| 2026-08-06 | **P1 repaired: the council brief advertised two rosters at once.** Receipt binding overwrote `rotating_seat`/`council_seats` but left `instructions` and `verdict_format` built from superseded wave text, so an agent copying the template recorded a seat the alignment check then rejected against the same response's roster. Instructions are now a seat-keyed helper and the binding rebuilds both strings. Proven: wave-text seat `security-reviewer` bound to receipt seat `code-reviewer` now yields `code-reviewer` in all three fields. | `server_impl.py` `_prepare_council_instructions`, `_bind_prepare_council_brief_to_receipt` |
| 2026-08-06 | **P2 repaired: the fallback reason named a line that exists in no document.** The offset was computed over the joined, canonicalized, lowercased corpus, so line 22 of one doc reported as "line 15" and with two docs it became a cross-document offset. The reason now names the token and a normalized excerpt and reports no line, because an exact mapping is not recoverable once canonicalization collapses the Progress Log. Spec claim corrected to match. | `review_policy.py` `_legacy_match_reason`; `mcp-tool-surface.md:637` |
| 2026-08-06 | **Test defect repaired: `action_required_inputs` existed only in the test.** `review_action_input_schema()` never emitted the response-level per-action map that 1ullt Requirement 4 requires and that `test_review_evidence.py:4237` asserts, so that test errored. The schema now emits it. | `review_evidence.py` `review_action_input_schema` |
| 2026-08-06 | **Undisclosed governance change found by independent delivery review and now made deliberate.** `normalize_review_tracking_status` made `Change Status` digest-neutral, which reversed a rule two tests pinned on purpose: advancing a change to `complete` previously superseded the receipt and lapsed the readiness roster. The reversal shipped with no disclosure and both tests red, while three ACs claimed the suites pass. Operator decision recorded below: keep the new behavior. Tests rewritten to pin it, not deleted, plus a new test naming the rule directly with a Scope-edit negative control. | `gardener_metadata.py:57-83`; `test_server_tools.py` `test_advancing_change_status_is_progress_not_a_contract_change`, `TypedExclusiveGateDerivationTests` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-06 | Use one canonical body for both lane scoring and digesting. | A shared carrier makes a roster change cryptographically visible and removes mismatched exclusions. | Maintain two normalizers and synchronize their exceptions; high drift risk. |
| 2026-08-06 | Retain corrected legacy fallback rather than remove it. | Pre-Serialization-Points waves need coverage; boundary-aware matching fixes the false-positive class without zeroing their roster. | Remove fallback and lose review coverage on historical plans. |
| 2026-08-06 | Treat rotating-seat selection as non-superseding operational metadata while retaining a receipt-bound canonical snapshot. | Coverage and input digest, not a new seat draw, determine whether existing approvals remain valid. | Supersede every rotation; repeatedly lapses valid approvals. |
| 2026-08-06 | **Advancing `Change Status` is progress, not a contract change, and stays digest-neutral.** Operator decision after independent review surfaced that the wave had reversed the prior rule without disclosure. | Consistent with the principle 1uhcb and 1ug66 already set: the Progress Log is excluded and AC completion and task marks are progress-only, while an AC `[~]` stays reviewable because it changes the contract. Readiness reviews the plan, and a status advance edits no Requirement, Scope, AC, or AC-Priority text, so re-recording would attest to byte-identical text. Verification of the work still sits behind the delivery gate, which is untouched: `wf_close_wave` demands delivery lane approvals and operator signoff regardless of any status value. | Restore the lapse by excluding `Change Status` from normalization while keeping the `Last verified` and Progress Log exclusions; rejected as ceremony that re-approves unchanged text. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Boundary rules miss a valid legacy path reference | Table-driven positives for extensions, directories, and bare path segments. |
| Metadata normalization hides a real policy edit | Explicit negative controls for requested lanes and substantive headers. |
| Evaluator bump leaves a stale public path | Prior-version receipt convergence test through prepare. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
