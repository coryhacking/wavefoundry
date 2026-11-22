# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `24237 optional-dependency-diagrams`
Title: Optional Dependency Diagrams

## Objective

Operators reading a wave or spec in the offline dashboard see where dependent work branches and rejoins. Authors keep simple plans linear.

## Changes

Change ID: `24236-enh display-optional-dependency-diagrams`
Change Status: `implemented`

## Participants

- Coordinator: delivery coordinator
- Write-owning roles: frontend builder and technical writer
- Requested review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-11-21

## Wave Summary

Wave `24237 optional-dependency-diagrams` (Optional Dependency Diagrams) delivered one change: Show dependency diagrams in the local dashboard.

Intent outcome: achieved. Independent QA opened both dashboard dialogs in Chrome at a 390 px viewport. All eight arrows and text relationships in the seven-node pilot joined the intended nodes, including the four checks before reassessment. The wave example showed its two prerequisites, and the browser made zero external requests. Unsupported input retained the complete source. The planning guidance preserves lists for simple work and existing dependency records. This review measured neither screen-reader usability nor engineering throughput.

**Changes delivered:**

- **Show dependency diagrams in the local dashboard** (`24236-enh display-optional-dependency-diagrams`) — AC-1, AC-2 and AC-3 completed. Key decisions: Render a small dependency syntax with the existing offline layout capability.

## Watchpoints

- Watchpoint: preserve source fallback, existing dependency fields and review authority.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| D1-DIAGRAM-GRAMMAR | do_now | no | completed | docs-contract-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
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

2026-11-21: Intent outcome: achieved. Independent QA opened both dashboard dialogs in Chrome at a 390 px viewport. All eight arrows and text relationships in the seven-node pilot joined the intended nodes, including the four checks before reassessment. The wave example showed its two prerequisites, and the browser made zero external requests. Unsupported input retained the complete source. The planning guidance preserves lists for simple work and existing dependency records. This review measured neither screen-reader usability nor engineering throughput.

2026-11-21: At readiness the standard red-team primer challenged partial parsing that could hide a prerequisite. Architecture/code, security, QA, docs-contract and the reality-checker agreed that the eight directed endpoints and complete-source fallback were testable. The lower-cost table supported the same pilot decisions but omitted the requested visual view. The council judged the plan establishes the objective. Delivery used the four specialists selected by the targeted review policy.

2026-11-21: Docs-contract found the author guidance admitted a reserved ID and unsupported label text. The seed and local prompt now describe the accepted syntax. A fresh verifier rendered their identical example and checked complete-source fallback for each excluded case. Code and QA also verified the stronger direct fallback assertion against an isolated mutation that skipped an invalid line. All four specialist delivery approvals are current.

**Closure retrospective.** Reversing every arrow preserved the pilot’s seven nodes and eight edges. Checking the ordered endpoints caught the error. The shipped regression preserves that lesson. The memory preview proposed no additional records. The single syntax-guidance finding was repaired and independently verified.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 62 | 1,760,282 |
| implement | 81 | 454,539 |
| review | 71 | 334,393 |
| **Total** | **214** | **2,549,214** |

<!-- wave:context-efficiency-state {"generation":153,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":81,"content_source_credit":539619,"derived_artifact_credit":1347,"direct_net":454539,"estimated_tokens_saved":454539,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2282,"response_debit":87479,"source_credit_count":37,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3334},"plan":{"calls":62,"content_source_credit":1855670,"derived_artifact_credit":3741,"direct_net":1760282,"estimated_tokens_saved":1760282,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5855,"response_debit":99202,"source_credit_count":54,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5928},"review":{"calls":71,"content_source_credit":467401,"derived_artifact_credit":1518,"direct_net":334393,"estimated_tokens_saved":334393,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11879,"response_debit":129363,"source_credit_count":47,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6716}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":214,"content_source_credit":2862690,"derived_artifact_credit":6606,"direct_net":2549214,"estimated_tokens_saved":2549214,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20016,"response_debit":316044,"source_credit_count":138,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15978},"wave_id":"24237 optional-dependency-diagrams"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 3 | 2,749,416 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":2749416,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
