# Focused readiness delta — code and QA

Owner: Engineering
Status: active
Last verified: 2026-09-22

Verdict: approve the two operator-selected plan clarifications for readiness against receipt `review-policy-d33fe310355179ea758d`. This is not delivery approval or approval of partially implemented source. No lifecycle events or source edits were performed.

Scope: `1yoy2-bug review-ledger-tool-gaps.md`, Requirements 1, 3 and 5 and its operator decision row; original readiness evidence and tool inventory read. Code-reviewer and qa-reviewer judgments share this one context and evidence: they are correlated, not two independent reviews. The reviewer did not implement the code or write the amended plan. Requested runtime: inherited host default; observed model identity unknown.

## Red-team primer

Strongest challenge: selecting the latest approval globally clears too early, while inspecting any historical approval never clears. Selection must be append-order latest per lane AND readiness phase before comparing receipts. Delivery reapproval must not clear stale readiness. The amended plan explicitly preserves old ledger rows and clears after all lanes reapprove.

Strongest alternative: reuse the existing structured review authority's per-lane selection rather than add a second approval-currentness implementation in the server. `_approval_rows` and `review_authority_projection` already select phase-separated latest approvals (`review_evidence.py:1154-1171`, `1404-1447`). The advisory is informational and must not become a new readiness gate.

The second clarification is consistent with the stated path-token grammar: a bare test name does not establish a durable path. A temporary path plus a repository evidence path suppresses the advisory; a temporary path plus a bare test ID does not. This is a citation heuristic, not verification that a cited artifact exists.

## Evidence and controls

MCP `code_outline` and targeted `code_read` verified selection and receipt-binding anchors. `code_ask` returned `index_not_ready`; no semantic-search result was relied upon, and source reads supplied the fallback. No index rebuild was attempted.

Executed with `python3 -B`: `test_review_evidence.RepairReverificationIndependenceTests.test_readiness_receipt_rotation_preserves_retained_audit_verdict` and `test_approval_phases_have_independent_supersession`. Expected two passes without skips; observed two passes, zero skips. These existing canonical event-builder/validator controls demonstrate readiness/delivery separation and receipt-bound readiness behavior; they do not exercise the new advisory endpoints.

A bounded in-memory control invoked `_approval_rows` with old code/QA readiness approvals, a new code readiness approval, and a new QA delivery approval. Expected stale readiness; observed stale. Adding new QA readiness approval cleared the derived predicate while retaining all five history rows. The deliberately wrong historical-scan predicate still warned and was detected by disagreement with the required cleared state. This exercises the existing selection seam, not a shipped supersession advisory.

QA judgment: the amended requirement adds the missing all-lanes-reapproved control and explicitly states the bare-ID boundary. Add a partial-lane reapproval negative control when implementing the named fixture family; include a delivery-only reapproval to prove phase separation. These are bounded realizations of the specified behavior, not additional scope or a readiness blocker.

## Approval facts for coordinator

- Proposition: the clarified latest-per-lane and lexical path rules are implementable at existing seams with finite, meaningful controls and preserve receipt/approval authority.
- Counterexample: historical scans never clear; global latest selection or delivery-only approval clears too early; counting a bare test ID as a durable path suppresses the temporary-only warning.
- Execution status: executed, readiness-safe in-memory/library controls only.
- Public path: existing canonical review event builder and validator through the two named tests; no registered MCP advisory endpoint was exercised.
- Artifact: `docs/waves/1ypxw review-prompt-efficiency/evidence/ready-delta-code-qa.md`.
- Expected / observed: two baseline controls green; partial readiness remains stale; complete readiness clears without deleting history; historical-scan known-bad distinguished. All observed as expected.
- Integrity: `test_ran_without_unintended_skip=true`, `public_path_reached=true` for the stated library event-builder/validator boundary only, `boundary_values_realistic=true`, `assertions_non_vacuous=true`, `known_bad_detected=true`. Detection method: bounded historical-scan negative comparator plus existing retained-context and phase-separation negative cases.
- Safety: local read-only/in-memory probes; no repository ledger write, external request, credentials, or destructive operation; no unexecuted unsafe remainder.
- Limitations: no delivery review, full suite, new advisory endpoint execution, cross-platform path probe, or artifact-existence guarantee. No universal claim. Both specialist judgments share one reviewer context; coordinator must preserve that correlation in any synthesized evidence.
