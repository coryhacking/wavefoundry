# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `24c3o review-comprehension-isolation-and-contract-drift`
Title: Catch ambiguous plans and verify review and contract evidence

## Objective

Reviewers predict observable behavior and challenge apparent tradeoffs before implementation. When a proposed readiness repair would undo a previous one, the operator sees both outcomes and their evidence before choosing the next step. Maintainers can check what context a reviewer received on a tested host and where a standing behavior contract disagrees with the system it describes.

## Changes

Spec ID: `24c3p-enh predict-observable-behavior-at-readiness`
Spec Status: `implemented`

Spec ID: `24c3q-enh challenge-false-tradeoffs-in-plan-review`
Spec Status: `implemented`

Spec ID: `24c3r-enh qualify-native-reviewer-context-isolation`
Spec Status: `implemented`

Spec ID: `24c3s-enh inspect-behavior-contract-drift`
Spec Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer and technical writer
- Requested review lanes: qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-25

## Wave Summary

Wave `24c3o` (Catch ambiguous plans and verify review and contract evidence) delivered 4 changes: Predict observable behavior during readiness review, Challenge apparent tradeoffs in plan review, Qualify reviewer context isolation on native hosts, and Inspect behavior contract drift without editing.

Intent outcome: the ordered prediction exposed a stage-boundary mismatch, the focused handoff distinguished removing a warning from removing a duplicate footer, and the read-only contract walkthrough separated contradiction, insufficient evidence and observable omissions. Both native CLI controls detected deliberate disclosure. Those observations cover fresh CLI processes only. The five-wave adoption follow-up remains outstanding.

**Changes delivered:**

- **Predict observable behavior during readiness review** (`24c3p-enh predict-observable-behavior-at-readiness`) — AC-1, AC-2 and AC-3 completed. Key decisions: Use an assigned reviewer.
- **Challenge apparent tradeoffs in plan review** (`24c3q-enh challenge-false-tradeoffs-in-plan-review`) — AC-1, AC-2 and AC-3 completed. Key decisions: Extend optional plan review.
- **Qualify reviewer context isolation on native hosts** (`24c3r-enh qualify-native-reviewer-context-isolation`) — AC-1, AC-2 and AC-3 completed. Key decisions: Qualify host configurations outside lifecycle review.
- **Inspect behavior contract drift without editing** (`24c3s-enh inspect-behavior-contract-drift`) — AC-1, AC-2 and AC-3 completed. Key decisions: Add inspection to wf-contract.

## Watchpoints

- Coordinate 24c3p and 24c3q edits to the shared council-chair guidance and Prepare wave prompts. Verify both the independent prediction at readiness and the repair-reversal handoff after focused verification.
- At the five-wave follow-up, use existing records from qualifying waves to compare late intent repairs and review rounds with recent comparable waves. Note missing evidence and differences in scope. These observations alone cannot establish causation.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 24c3q-adr-handoff | do_now | no | completed | docs-contract-reviewer |
| 24c3s-retained-authoring-route | do_now | no | completed | code-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
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
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-25: Intent outcome: the ordered prediction exposed a stage-boundary mismatch, the focused handoff distinguished removing a warning from removing a duplicate footer, and the read-only contract walkthrough separated contradiction, insufficient evidence and observable omissions. Both native CLI controls detected deliberate disclosure. Those observations cover fresh CLI processes only. The five-wave adoption follow-up remains outstanding.

Independent QA intent outcome: the warning, fixed-record and footer-only controls discriminated actual losses from harmless rewrites. QA reproduced the contract fixture digest and removed a return value that its existing test never checked. Both host qualification rows support only fresh CLI process observations. Code and docs reviewers identified a retained-writer routing gap and a missing offer of architectural decision evaluation; see the delivery ledger for their repairs and current verification.


Readiness uses a standard-depth primer for the host context and contract inspection boundaries. The ordinary council reviews the four specs together. Specialist approvals cover the shared packet.

The red-team primer identified an answer-bearing council brief as a counterexample to an independent prediction. Spec 24c3p now collects the prediction first, then resumes normal primer engagement. At delivery, follow the public Prepare, agent Prepare and Council review instructions through both exchanges, including seed 100 and seed 237 pointers. The code reviewer exercised the real skill renderer, QA replayed the missing-warning example, and docs-contract checked the original primer order against the revised requirement. These checks establish readiness only.

Prepare wave readiness verdict: the council chair approved all four specs and the wave objective (intent fit: establishes). Architecture, security and reality-checker seats confirmed the evidence boundaries. Delivery verifies rendered entry points, actual host controls and read-only inspection.


2026-11-25: Delivery review complete. The repaired 22-path tree passed independent code and docs-contract reverification. QA approved all four outcomes. The canonical framework suite ran 13,621 tests across 261 files, with 13 skips, in 852.554 seconds and wrote a green receipt. The earlier Tensorwell client failures passed in the final suite. The five-wave follow-up remains scheduled.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 23 | 34,969 |
| implement | 42 | 188,938 |
| review | 61 | 325,415 |
| **Total** | **126** | **549,322** |

<!-- wave:context-efficiency-state {"generation":130,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":42,"content_source_credit":204308,"derived_artifact_credit":0,"direct_net":188938,"estimated_tokens_saved":188938,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1128,"response_debit":18387,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4145},"plan":{"calls":23,"content_source_credit":53749,"derived_artifact_credit":6696,"direct_net":34969,"estimated_tokens_saved":34969,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1618,"response_debit":30156,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"review":{"calls":61,"content_source_credit":445350,"derived_artifact_credit":1187,"direct_net":325415,"estimated_tokens_saved":325415,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9475,"response_debit":118576,"source_credit_count":45,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6929}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":126,"content_source_credit":703407,"derived_artifact_credit":7883,"direct_net":549322,"estimated_tokens_saved":549322,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12221,"response_debit":167119,"source_credit_count":65,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":17372},"wave_id":"24c3o review-comprehension-isolation-and-contract-drift"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 4 | 10,642,110 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":10642110,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
