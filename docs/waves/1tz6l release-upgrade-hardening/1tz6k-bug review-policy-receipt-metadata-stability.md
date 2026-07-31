# Stabilize Review-Policy Receipts Against Gardener Metadata

Change ID: `1tz6k-bug review-policy-receipt-metadata-stability`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-07-30
Wave: `1tz6l release-upgrade-hardening`

## Rationale

Review-policy receipts are intended to become stale when policy, requested or project-required
lanes, or the substantive contents of an admitted change change. Today the digest hashes the raw
bytes of every admitted change document. `wf_close_wave(mode="create")` runs docs-gardener before
evaluating the receipt, and docs-gardener updates `Last verified` on Git-modified Markdown. A close
that crossed midnight therefore changed an admitted change's date from `2026-07-29` to
`2026-07-30`, invalidated an otherwise current receipt, and required a new readiness receipt and
approval even though no policy or implementation scope changed.

The reproduced `1tskc` digests isolate the defect: the current bytes produce
`2f58cfac…`, while changing only that date back in memory reproduces the prior persisted
`c0375117…` digest exactly. Gardener-owned verification metadata is not an input to lane selection
and must not create review-policy churn.

## Requirements

1. Replace raw admitted-change hashing with one canonical review-policy input representation that
   normalizes only the top-level `Last verified: YYYY-MM-DD` metadata value to a stable sentinel
   before hashing. Keep every other byte—including status, requirements, ACs, tasks, progress,
   decisions, risks, and target references—load-bearing.
2. Keep the existing digest inputs for normalized `wave_review`, project-required lanes,
   `review_policies`, admitted change identity/kind, and requested lanes unchanged. `VERSION`,
   README, prompt-surface manifest, wave projection, and other unrelated repository files remain
   outside the digest.
3. Make Prepare, Review, Implement, and Close consume the same canonical digest function. Do not add
   a lifecycle-specific exception or silently refresh an approval at Close.
4. Version the changed evaluator semantics explicitly. Existing non-closed waves may require one
   deterministic re-Prepare after upgrade; closed wave Markdown and ledgers remain immutable.
5. Preserve fail-closed behavior for malformed or ambiguous change metadata. A missing
   `Last verified` line remains hashable as-is; multiple matching top-level lines must not be broadly
   stripped or used to hide substantive content.
6. Add a public-path regression that prepares a wave on one date, advances only gardener-owned
   verification dates, then closes on the next date without `review_policy_receipt_stale`. The same
   fixture must prove a one-byte substantive change still produces the stale diagnostic.
7. Document the semantic digest boundary and the one-time evaluator-version transition in the MCP
   tool-surface specification and review-policy data/control-flow documentation.
8. Reuse or extract the existing canonical leading-frontmatter rule currently embodied by
   `index_state_store._strip_gardener_field`; do not introduce a second independently maintained
   `Last verified` parser. The review-policy representation may replace the value with a sentinel
   instead of deleting the line, but both consumers must share the same field-recognition boundary.

## Scope

**Problem statement:** An automatic `Last verified` update changes the raw admitted-change bytes and
invalidates a review-policy receipt even though the evaluator's policy inputs are semantically
unchanged.

**In scope:**

- Canonical admitted-change normalization for review-policy hashing.
- Evaluator-version migration behavior for non-closed waves.
- Cross-lifecycle receipt validation and date-rollover regressions.
- Review-policy contract documentation.

**Out of scope:**

- Removing docs-gardener from Close or changing its Git-modified-doc selection policy.
- Ignoring change status, AC/task state, Progress Log, Decision Log, or any other substantive text.
- Automatically carrying approvals across substantive change-document edits.
- Changing receipt chaining, signoff chronology, repair independence, or closed-wave immutability.

## Acceptance Criteria

- [x] AC-1: Two otherwise identical admitted changes whose only difference is the top-level
  `Last verified` date produce the same `policy_input_digest`.
- [x] AC-2: Mutating any non-`Last verified` byte in the same fixture changes the digest and causes
  the public lifecycle path to return `review_policy_receipt_stale`.
- [x] AC-3: A prepared non-closed wave survives a simulated midnight Close garden pass without a
  receipt refresh, lane reset, or approval churn.
- [x] AC-4: The canonical normalizer handles zero or one valid metadata line narrowly and cannot
  erase duplicate, embedded, malformed, or body-level lookalikes.
- [x] AC-5: Prepare, Review, Implement, and Close agree on receipt currency for the same repository
  state, with existing stale-receipt recovery unchanged for substantive edits.
- [x] AC-6: The evaluator-version transition is explicit and tested; existing closed ledgers remain
  byte-identical and non-closed legacy receipts converge through one re-Prepare.
- [x] AC-7: Review-policy specification and architecture documentation name the normalized metadata
  boundary and preserve all existing authority and chronology guarantees.
- [x] AC-8: Gardener drift detection and review-policy hashing share one canonical recognition rule,
  with a regression proving their accepted and rejected lookalike classes cannot diverge.

## Tasks

- [x] Extract or reuse the existing narrow gardener-frontmatter recognizer and consume it from
  `policy_input_digest` without creating a parallel regex contract.
- [x] Bump the review-policy evaluator version and reconcile receipt compatibility tests.
- [x] Add unit polarity tests for metadata-only versus substantive mutations.
- [x] Add a real gardener-to-Close date-rollover regression through the public lifecycle surface.
- [x] Run receipt, lifecycle, docs-gardener, and close-focused tests plus docs lint.
- [x] Update the MCP tool-surface spec and `docs/architecture/data-and-control-flow.md`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Digest boundary | implementer | — | Canonicalize one owned metadata field only. |
| Lifecycle regression | qa-reviewer | Digest boundary | Exercise gardener and public Close ordering. |
| Contract reconciliation | docs-contract-reviewer | Digest boundary | Keep spec and architecture aligned. |
| Independent verification | code-reviewer | All implementation work | Mutation-check both polarities. |

## Serialization Points

- `review_policy.py` owns the canonical digest contract and must land before lifecycle fixtures are
  updated.
- Evaluator-version and receipt-compatibility expectations must change atomically.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — clarify the semantic admitted-change digest.
- `docs/specs/mcp-tool-surface.md` — document stale-receipt boundaries and recovery.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Defines the repaired metadata-stability contract. |
| AC-2 | required | Prevents normalization from weakening substantive invalidation. |
| AC-3 | required | Reproduces the operator-visible defect through the real ordering. |
| AC-4 | required | Prevents an overbroad stripping bypass. |
| AC-5 | required | Receipt authority must remain consistent across lifecycle gates. |
| AC-6 | required | Versioned evaluator semantics and closed-wave compatibility are load-bearing. |
| AC-7 | important | Keeps the public contract discoverable. |
| AC-8 | required | Prevents two metadata recognizers from drifting into different authority boundaries. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-30 | Reproduced the false staleness and isolated it to one gardener-owned date line. | Current digest `2f58cfac…`; in-memory date-only reversal reproduces persisted digest `c0375117…`. |
| 2026-07-30 | Implemented a shared fail-closed gardener-frontmatter recognizer and evaluator v2 digest normalization. | `test_review_policy.py`: 22/22 OK; metadata-only and substantive polarities plus duplicate/body/malformed lookalikes executed. |
| 2026-07-30 | Proved the normalized receipt through all public lifecycle consumers and repaired the drift parser's remaining private-regex reference. | `TypedExclusiveGateDerivationTests`: midnight date-only rollover leaves Prepare, Review, Implement, and Close current; `test_doc_drift.py`: 91/91; full suite: 6,509/6,509. |
| 2026-07-30 | Closed delivery-review evidence gaps for the evaluator transition and public contract. | Evaluator version is pinned to `2`; public Prepare proves one v1-to-v2 receipt rollover followed by idempotence; closed Markdown and ledger bytes are pinned; the MCP specification now names the exact normalization and compatibility boundary. Full suite: 6,518/6,518. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-30 | Normalize only the top-level `Last verified` value. | It is gardener-owned, irrelevant to policy selection, and the exact reproduced trigger. | Removing Close gardening was rejected because it weakens a separate docs invariant; ignoring broader headers or sections was rejected as an authority bypass. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Normalization hides substantive edits. | Match exactly one top-level metadata field and mutation-test every adjacent byte class. |
| Digest algorithm changes without migration clarity. | Bump the evaluator version and pin one-time non-closed-wave convergence. |
| Different lifecycle tools compute different currency. | Route all gates through the same canonical digest and public-path cross-surface tests. |
| Receipt hashing and drift detection recognize different gardener fields. | Share one canonical frontmatter recognizer and mutation-check the same lookalike corpus through both consumers. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
