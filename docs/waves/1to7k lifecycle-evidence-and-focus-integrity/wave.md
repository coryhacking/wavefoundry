# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-26
review-evidence-source: events.jsonl

wave-id: `1to7k lifecycle-evidence-and-focus-integrity`
Title: Lifecycle Evidence And Focus Integrity

## Objective

Make two lifecycle integrity contracts explicit and enforceable: a repair cannot
silently self-reverify through internally contradictory ledger identity, and a
lifecycle response cannot silently leave context-efficiency focus on an unrelated
wave. Preserve honest limits—actor identity remains declarative and failed calls
still do not move focus.

## Changes

Change ID: `1tmb2-bug repair-reverification-independence-unenforced`
Change Status: `planned`

Change ID: `1tmb3-bug failed-lifecycle-call-leaves-focus-stale-and-silent`
Change Status: `planned`

## Wave Summary

The wave hardens two adjacent control surfaces without conflating them. It first
adds chain-aware repair/reverification checks at append and close boundaries,
then aligns lifecycle outcome classification, focus, projection, and diagnostics
for failed and council-ready calls.

## Participants

- Coordinator/moderator: primary Codex coordinator / wave-council
- Required lanes: red-team, architecture-reviewer, security-reviewer,
  qa-reviewer, reality-checker, docs-contract-reviewer
- Implementation owners: implementer for 1tmb2, independent reverifier for
  1tmb2, then implementer for 1tmb3

## Watchpoints

- Blocking: implement 1tmb2 alone first and independently reverify it before
  editing 1tmb3. The two changes share lifecycle evidence/response tests even
  though their production seams differ.
- Blocking: do not claim authenticated reviewer identity. The enforceable
  boundary is ledger-internal actor/context contradiction plus honest remaining
  declaration limits.
- Blocking: genuinely failed lifecycle calls remain non-focusing. The
  `ready_for_council_review` outcome is deliberately target-engaged: preserve its
  projection and move focus to that wave, without imposing a false global
  equivalence between publication and future focus.
- Follow-up boundary: do not add credit re-attribution or a general set-focus
  capability in this wave.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 2 records; 1 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-26: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the proposed enforcement could falsely present role strings as authenticated independence while lifecycle reporting could equate raw focus with effective attribution even though sealed focus and the unique-OPEN fallback route credits elsewhere; resolved by defining same-actor rejection as forward protocol policy, preserving closed archives with a legal reopened recovery cycle, and using one telemetry-owned effective-attribution resolver for commit and lifecycle reporting; strongest-alternative: retain prose-only independence and patch focus messages independently at each lifecycle tool, rejected because the observed failures came from unenforced declarations and duplicated per-path behavior; material repairs folded before approval: phase-correct repair grammar, corrected 35-chain/two-contradiction corpus census, deterministic rejection precedence, install/upgrade/reload contracts, `clear_focus` pause semantics, sealed-focus and no-focus/unique-OPEN controls, and executable next-cycle recovery; tests deliberately not run during prepare by operator direction because other repository work is active.)

## Dependencies

- Readiness may proceed in parallel with other work. Activation and edits wait
  for the current OPEN wave to release the slot and for any concurrent editor of
  `server_impl.py`, `review_evidence.py`, or their shared tests to finish.
- Within this wave, 1tmb2 is implemented and independently reverified before
  1tmb3 begins.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 21 | 1,022,442 |
| review | 1 | 0 |
| **Total** | **22** | **1,022,442** |

<!-- wave:context-efficiency-state {"generation":22,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":21,"content_source_credit":1049823,"derived_artifact_credit":287,"direct_net":1022442,"estimated_tokens_saved":1022442,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":979,"response_debit":29880,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"review":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-72,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10,"response_debit":62,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":22,"content_source_credit":1049823,"derived_artifact_credit":287,"direct_net":1022370,"estimated_tokens_saved":1022442,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":989,"response_debit":29942,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"wave_id":"1to7k lifecycle-evidence-and-focus-integrity"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
