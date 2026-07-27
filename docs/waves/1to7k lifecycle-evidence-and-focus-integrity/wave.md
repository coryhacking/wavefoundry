# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-27
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
Change Status: `implemented`

Change ID: `1tmb3-bug failed-lifecycle-call-leaves-focus-stale-and-silent`
Change Status: `implemented`

Completed At: 2026-07-27

## Wave Summary

Wave `1to7k` (Lifecycle Evidence And Focus Integrity) delivered two changes: Repair And Reverification Independence Is Documented But Unenforced and A Failed Lifecycle Call Leaves Context-Efficiency Focus Stale And Says Nothing. Notable adjustments during implementation: Repair And Reverification Independence Is Documented But Unenforced: Repair (cycle 1) of finding `same-actor-nonfresh-rejection-untested`: added `RepairReverificationIndependenceTests.test_same_actor_nonfresh_nonclearing_reverification_is_rejected` pinning the council's P8 probe shape — a same-actor, fresh_context=false, non-clearing reverification (blocking_required_lanes unchanged) is rejected with `reverification_actor_not_distinct` and appends nothing. Passed on current code unmodified; M5 mutation kill proven: narrowing the actor rejection in `_reverification_independence_defect` to fire only when fresh_context is true made the test FAIL (rows appended), byte-identical revert verified by sha256 (`8bf5e380…d1157` before and after; mutated `94dad70c…4cf07`), test and full module green after revert. No production code changed.; Repair And Reverification Independence Is Documented But Unenforced: Repair (cycle 2) of finding `same-actor-same-context-nonfresh-reverification-accepted`: the same-context/non-fresh early return in `_reverification_independence_defect` (review_evidence.py:1740-1743) bypassed the actor policy, so a same-actor, same-context, fresh_context=false reverification appended 3 rows. Red test `test_same_actor_same_context_nonfresh_reverification_is_rejected` observed RED on exactly that probe shape, then the precedence was fixed: actor equality is evaluated whenever the fresh-context contradiction did not fire. Quadrant controls added (same-actor/same-context/fresh=true returns only `reverification_context_not_fresh`; distinct-actor/same-context/non-fresh still passes policy and cannot clear). Mutation kill: restoring the early return made the red test FAIL (rows appended); byte-identical revert verified by sha256 (`83e2cd94…d69b4` before and after). No existing test modified.; A Failed Lifecycle Call Leaves Context-Efficiency Focus Stale And Says Nothing: Scope widened after observing a stronger case: `wf_prepare_wave(1tj0l, mode="ready")` returned `ready_for_council_review`, an outcome class the focus condition does not model. The same call published `1tj0l`'s checkpoint (1 call / 981 to 46 calls / 661,367) while leaving focus on `1tmb1`, which then climbed 58 to 72 calls during the council review of `1tj0l`. This is a design inconsistency, not only a missing diagnostic, so AC-8 and AC-9 were added.

**Changes delivered:**

- **Repair And Reverification Independence Is Documented But Unenforced** (`1tmb2-bug repair-reverification-independence-unenforced`) — 8 ACs completed. Key decisions: Scope the change to contradiction detection and same-actor detection, explicitly NOT to caller authentication.; Reject same-context and same-actor attempts before append; audit only older non-closed/reopened ledgers at close; preserve closed history until reopened.
- **A Failed Lifecycle Call Leaves Context-Efficiency Focus Stale And Says Nothing** (`1tmb3-bug failed-lifecycle-call-leaves-focus-stale-and-silent`) — 10 ACs completed. Key decisions: For genuinely failed calls, report the stale focus rather than moving it.; Treat `ready_for_council_review` as target-engaged: preserve its existing durable publication and move focus to that wave. Keep publication and future-focus policies distinct for other outcomes. **This narrows the preceding row**, which predates the observed council-ready case.
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
| open-wave-fallback-stage-mismatch-suppressed | do_now | no | completed | — |
| same-actor-nonfresh-rejection-untested | do_now | no | completed | — |
| same-actor-same-context-nonfresh-reverification-accepted | do_now | no | completed | — |
| sealed-close-focus-clear-failure-is-silent | do_now | no | completed | — |

*Machine review evidence — 48 records; 15 runs; 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
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
| plan | 30 | 1,660,221 |
| implement | 101 | 3,691,405 |
| review | 293 | 3,758,363 |
| **Total** | **424** | **9,109,989** |

<!-- wave:context-efficiency-state {"generation":413,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":101,"content_source_credit":3899205,"derived_artifact_credit":0,"direct_net":3691405,"estimated_tokens_saved":3691405,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3103,"response_debit":204697,"source_credit_count":70,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":30,"content_source_credit":1728072,"derived_artifact_credit":407,"direct_net":1660221,"estimated_tokens_saved":1660221,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3007,"response_debit":70516,"source_credit_count":68,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5265},"review":{"calls":293,"content_source_credit":4772709,"derived_artifact_credit":1107,"direct_net":3758363,"estimated_tokens_saved":3758363,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35757,"response_debit":980908,"source_credit_count":162,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1212}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":424,"content_source_credit":10399986,"derived_artifact_credit":1514,"direct_net":9109989,"estimated_tokens_saved":9109989,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":41867,"response_debit":1256121,"source_credit_count":300,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6477},"wave_id":"1to7k lifecycle-evidence-and-focus-integrity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 959357 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":959357,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
