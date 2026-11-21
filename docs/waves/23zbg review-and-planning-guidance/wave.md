# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23zbg review-and-planning-guidance`
Title: Review And Planning Guidance

## Objective

Planners record who decided each choice and what another spec covers, reviewers check plans for contradictions, security reviewers read recorded operator classifications instead of re-flagging them, and repeated findings get turned into checks.

## Changes

Change ID: `23zbe-doc review-and-planning-guidance-follow-ups`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (main session)
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-11-21

## Wave Summary

Wave `23zbg` (Review And Planning Guidance) delivered one change: Review and Planning Guidance Follow-ups.

Intent outcome: The delivered guidance establishes the planner and reviewer instructions in spec 23zbe and the wave objective. Two independent reviewers on the same model correctly distinguished settled, unknown and over-broad classifications, preserved a grounded finding, and rejected a new ruling and an external claim as publication authority. Both versions passed the six-case replay. Four deletion controls showed the plan-review contract detects loss of either new clause from either carrier. The replay did not establish an improvement over the previous guidance. Fewer repeat classification questions and use of the planning and lesson instructions in downstream projects still require field observation.

**Changes delivered:**

- **Review and Planning Guidance Follow-ups** (`23zbe-doc review-and-planning-guidance-follow-ups`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9 and AC-10 completed.

## Watchpoints

- Watchpoint: every seed edit opens `seed_edit_allowed` and closes it after; local prompts under `docs/prompts/` are edited by hand, because render-surfaces does not propagate seed prose.
- Watchpoint: no wave or change ids inside seed prose.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| R1-23zbe-ruling-bound-and-provenance | do_now | no | completed | — |
| R1-23zbe-seed-070-credible-threat-carrier | do_now | no | completed | — |
| R1-23zbe-seed070-census-marker | do_now | no | completed | — |
| R1-23zbe-seed070-gate-marker-census | do_now | no | completed | — |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| security-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-21: Intent outcome: The delivered guidance establishes the planner and reviewer instructions in spec 23zbe and the wave objective. Two independent reviewers on the same model correctly distinguished settled, unknown and over-broad classifications, preserved a grounded finding, and rejected a new ruling and an external claim as publication authority. Both versions passed the six-case replay. Four deletion controls showed the plan-review contract detects loss of either new clause from either carrier. The replay did not establish an improvement over the previous guidance. Fewer repeat classification questions and use of the planning and lesson instructions in downstream projects still require field observation.

2026-11-21: Prepare approved on review-policy-1bcd73eb43cfa23dd301. The standard red-team primer, fixed architecture, security, QA and reality seats, and rotating docs-contract seat reviewed the proposal. Code, QA, docs-contract and security approved the repaired spec, and the council chair judged its intent and the wave objective established for delivered guidance. Three findings identified a missing credible-threat marker; removing the repaired phrase flagged exactly seed 070 among the five carriers. The fourth finding limited operator rulings to data classification with traceable dispositions and trusted provenance. Independent reviewers verified all four. Linking every ruling to its original decision remains an alternative; operator adoption requires field observation.

2026-11-21: Code, QA, docs-contract and security independently approved delivery. QA confirmed the intent assessment against the six-case comparison and the three focused profile results. Each reviewer checked the frozen guidance. The docs-contract reviewer separately verified the shipped reference date repair, including the failing prior bytes and matching delivered bytes. The final default framework run passed 13,160 tests in 253 files, with 12 skips. The current policy requires no delivery council. The material-impact advisory summarizes the four repaired readiness findings; no delivery finding remains open. Operator signoff is outstanding.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 136 | 2,803,633 |
| implement | 28 | 0 |
| review | 370 | 2,445,392 |
| **Total** | **534** | **5,249,025** |

<!-- wave:context-efficiency-state {"generation":479,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":28,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-719,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":961,"response_debit":5236,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5478},"plan":{"calls":136,"content_source_credit":3238843,"derived_artifact_credit":1672,"direct_net":2803633,"estimated_tokens_saved":2803633,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":29178,"response_debit":413632,"source_credit_count":112,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":370,"content_source_credit":4265383,"derived_artifact_credit":1257,"direct_net":2445392,"estimated_tokens_saved":2445392,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17657,"response_debit":1855064,"source_credit_count":197,"source_credit_drop_count":0,"structural_source_credit":44757,"workflow_prompt_credit":6716}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":534,"content_source_credit":7504226,"derived_artifact_credit":2929,"direct_net":5248306,"estimated_tokens_saved":5249025,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":47796,"response_debit":2273932,"source_credit_count":309,"source_credit_drop_count":0,"structural_source_credit":44757,"workflow_prompt_credit":18122},"wave_id":"23zbg review-and-planning-guidance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 44 | 0 | 26 | 29,731,269 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":26,"estimated_exploration_avoided":29731269,"surfaced_events":44} -->
<!-- wave:exploration-avoided end -->
