# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-20

wave-id: `1seax lifecycle-ops-hardening`
Title: Lifecycle Ops Hardening

## Objective

Land the right-sized remainder of the 2026-07-12 external code review: (1) lifecycle-mutation concurrency and interruption safety — an advisory per-root mutation lock, a write-ordering audit guaranteeing forward-recoverability, and idempotent-retry fixtures — deliberately NOT the review's proposed transaction-journal/rollback layer, which was assessed as disproportionate for git-versioned markdown with zero field incidents; (2) selective subprocess bounds (timeouts + bounded capture) for the short MCP-reachable ops (gardener, surface render), with upgrade/setup explicitly exempt as long-running-by-design; (3) the materially stale operational contracts (RELIABILITY.md, performance-budget.md) rewritten from measured evidence, plus a declarative docs-vs-code-constants lint check so documented facts fail the docs gate when they drift instead of waiting for the next external review to notice.

## Changes

Change ID: `1seat-debt lifecycle-mutation-lock-and-subprocess-bounds`
Change Status: `planned`

Change ID: `1seau-doc ops-docs-refresh-and-constants-lint`
Change Status: `planned`

Change ID: `1t3zv-debt contention-safe-performance-test-budgets`
Change Status: `planned`

## Wave Summary

P2-priority hardening pair from the external review, both right-sized during validation: lifecycle mutation lock + forward-recoverability + selective subprocess bounds (transaction-journal machinery explicitly rejected), and evidence-based ops-docs refresh with a drift-preventing constants lint.

## Delivery Sequence

Implement in this order to protect release-critical operation first while
preserving the wave's deliberately narrow boundary:

1. `1seat`: lifecycle-mutation lock, forward-recoverability audit/retry
   fixtures, and prepare-council seat alignment.
2. `1seau`: canonical public-contract constants, then the narrow docs-lint
   rules that consume them (including admitted-change and signoff wording
   integrity).
3. `1seau`: evidence-based refresh of `RELIABILITY.md` and the performance
   budget after the constants contract is settled.
4. `1seat`: gardener and surface-render subprocess bounds, with generous,
   configuration-tunable limits that remain safe on slower computers.

All four steps are release scope. Existing subprocess isolation remains in
place; the new bounds must provide a clear timeout diagnostic and recovery
path, while upgrade/setup/index builds remain exempt because they are
legitimately long-running. Do not expand this sequence into a transaction
journal or blanket subprocess deadlines.

## Journal Watchpoints

- Watchpoint (right-sizing holds): the rejected alternatives (transaction journal, blanket subprocess deadlines, correlation IDs) are recorded with rationale in the change docs — reviewers should challenge the fixes' sufficiency, not silently re-expand toward the rejected machinery.
- Watchpoint (exemption pins): upgrade/setup/index-build spawns must be PINNED as timeout-exempt — a deadline there converts slow-network success into failure.
- Watchpoint (happy-path invariance): the mutation lock must be invisible uncontended; existing lifecycle tests pass unmodified except for additive envelope fields.
- Watchpoint (measured, not aspirational): the performance-budget rewrite cites the recorded measurements (1sc7c hook costs, heal timing, FTS rebuild duration) — no unquantified claims.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-12: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, architecture-reviewer; rotating-seat: red-team emphasis; strongest-challenge: the right-sizing itself — is an advisory lock plus retry fixtures ENOUGH, or does rejecting the review's transaction layer under-protect as multi-agent use grows? Resolved on evidence: the failure base rate is zero across the framework's entire wave history, every mutation's artifacts are git-versioned human-readable markdown (git IS the recovery journal), forward-recoverability converts any interruption into \"re-run the same call\", and the lock closes the one genuinely growing risk (concurrent sessions interleaving writes) using the OS-lock pattern the index-build lock has proven in the field — the journal/rollback machinery would add failure modes to defend against failures git already makes visible; strongest-alternative: the review's full transaction layer — kept ON RECORD in the change doc's Decision Log as the escalation path if multi-agent incidents ever materialize)
- Council seat notes: reality-checker — orderings verified against `2952df8f` (`_move_change_doc` ~6048 before `wave_md.write_text` ~6067; close's wave.md-then-handoff two-step); the zero-incident base rate is drawn from the full `docs/waves/` history; the stale-docs claims verified by direct read (performance-budget's \"None currently; all operations are local file I/O with small data volumes\" against a system with GPU embedding sessions and 100MB indexes); the measured inputs for the rewrite exist (1sc7c hook costs, 38s heal, 3.4s FTS rebuild). red-team — pressed lock-leak-on-crash (kernel releases OS locks on exit — the proven index-lock pattern, not a PID file); pressed the timeout exemption inversion (an exempt op that hangs forever): upgrade/setup already write persistent progress logs and the operator-facing status tools report liveness — observability, not deadlines, is the correct control there; pressed constants-lint brittleness (a renamed constant breaking lint): the check fails loudly naming the missing constant — self-announcing drift is the feature, not a bug. qa-reviewer — interruption fixtures are enumerated per mutation (admission, removal, close) at the specific inter-step seams, plus the contended-lock fixture and the drift-seeded lint fixture; happy-path invariance is an explicit AC. architecture-reviewer — the mutation lock joins the documented locking inventory (cross-cutting-concerns) beside the index-build and table locks with distinct scope; the constants-lint reuses the declarative check pattern (`check_deprecated_role_references` shape) rather than inventing a framework; the docs rewrite is evidence-cited by requirement. seat_agreement: unanimous.
- AC priority: confirmed at prepare as proposed (`1seat` AC-3 important, all else required). Product-owner acknowledgment: operator-directed 2026-07-12 ("build these waves now"); opportunistic scheduling.

- **Prepare-council amendment [prepare-council-amendment] — 2026-07-12:** external plan review caught that the recorded council lacked the brief's required rotating seat (`docs-contract-reviewer`); the seat was run post-hoc. **docs-contract-reviewer** — `1seau`'s deliverables ARE documentation contracts (RELIABILITY, performance-budget) with the evidence-citation requirement pinned; `1seat` names the cross-cutting-concerns locking-inventory entry. Seat findings (folded into scope by this amendment): the plan-review round exposed three VALIDATOR gaps that belong in this wave — (1) docs-lint must reject unbracketed pre-approval signoff phrasing (the placeholder convention is load-bearing for the close gate); (2) docs-lint must reject `Wave: TBD`/mismatched wave references on admitted change docs; (3) `wave_prepare` should compare recorded council seats against the generated brief instead of validating structure only. (1)+(2) added to `1seau`; (3) plus close-gate signoff-token hardening added to `1seat`. Verdict unchanged: READY.

## Review Evidence

- wave-council-readiness: approved 2026-07-12 — prepare council synthesis verdict READY: the deliberate severity downgrade from the review's P0 is evidence-based and recorded with the escalation path preserved; fixtures target the known seams instead of a fault-injection framework; the docs half is measurement-cited with a drift-preventing lint. Seats unanimous; full synthesis in Review Checkpoints.
- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Opportunistic scheduling after `1seav`/`1seaw`; the docs change can land any time.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 9 | 403,809 |
| review | 14 | 847,495 |
| **Total** | **23** | **1,251,304** |

<!-- wave:context-efficiency-state {"generation":23,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":9,"content_source_credit":412922,"derived_artifact_credit":0,"direct_net":403809,"estimated_tokens_saved":403809,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":224,"response_debit":12662,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3773},"review":{"calls":14,"content_source_credit":874181,"derived_artifact_credit":0,"direct_net":847495,"estimated_tokens_saved":847495,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":662,"response_debit":26024,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":23,"content_source_credit":1287103,"derived_artifact_credit":0,"direct_net":1251304,"estimated_tokens_saved":1251304,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":886,"response_debit":38686,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3773},"wave_id":"1seax lifecycle-ops-hardening"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
