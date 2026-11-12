# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `237ee language-aware-builder-and-reviewer-guidance`
Title: Language Aware Builder And Reviewer Guidance

## Objective

Projects in any language receive builder, reviewer and planning guidance that treats compiler and type-checker errors as design feedback, and a performance reviewer that checks their own hot paths instead of Wavefoundry's. Rules that hold in every language are generic; language blocks carry only their own constructs, with Rust added. Guidance only: no lint, sensor, gate or approval is added.

## Changes

Change ID: `2362b-bug performance-reviewer-seed-ships-wavefoundry-internals`
Change Status: `implemented`

Change ID: `2362c-enh design-over-diagnostic-guidance-and-rust-stack`
Change Status: `implemented`
Depends On: `2362b-bug performance-reviewer-seed-ships-wavefoundry-internals`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (serial ownership of shared seeds)
- Requested review lanes: docs-contract-reviewer, qa-reviewer, code-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-11

## Wave Summary

Wave `237ee` (Language Aware Builder And Reviewer Guidance) delivered two changes: Performance reviewer seed ships Wavefoundry internals and Design-over-diagnostic guidance and a Rust stack block.

Intent outcome: achieved for delivered guidance in both changes and the wave Objective. Eight new contract tests exercise conditional language guidance, upgrade reconciliation and the real missing-role renderer; the existing changed-carrier pin and all eight focused second-profile tests pass. Original seed snapshots and two deletion/contamination controls reject missing or leaked guidance. These establish instruction delivery, not better agent behavior or measured port speed; the reporter’s next upgrade and port remain the field check. QA independently checks this assessment.

**Changes delivered:**

- **Performance reviewer seed ships Wavefoundry internals** (`2362b-bug performance-reviewer-seed-ships-wavefoundry-internals`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Readiness primer repair: deliver through seed 160's changed-carrier rule; CODE-RDY-1 repair: review-time language sections instead of a generation-time hook.
- **Design-over-diagnostic guidance and a Rust stack block** (`2362c-enh design-over-diagnostic-guidance-and-rust-stack`) — AC-1, AC-2, AC-3, AC-4, AC-5 and AC-6 completed. Key decisions: Deliver guidance in the builder, reviewer, implement and plan seeds; no sensor or gate; Operator direction: make guidance generic where it applies beyond Rust.

## Watchpoints

- Watchpoint: The operator authorized bounded readiness repair and implementation. Pause wave 231kh before activation; preserve its delivered work and unrelated local build metadata. Seed edits need `seed_edit_allowed`. Closure, commit, push and release remain held.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |
| CODE-RDY-1 | do_now | no | completed | code-reviewer |
| INTEGRATION-DEL-1 | do_now | no | completed | code-reviewer, docs-contract-reviewer |
| QA-RDY2-1 | do_now | no | completed | qa-reviewer |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-11: Final integration is complete. Canonical suite passes 12,822 tests / 249 files / 12 reported skips in 604.553 seconds. INTEGRATION-DEL-1 (Readback carrier boundary) was repaired by moving the new paragraph before the existing block; existing tests were preserved and fresh code/docs verification confirmed both original-placement mutants fail. All required technical approvals are current; no delivery council is required. Wave remains OPEN, with no closure, commit, push or release performed.

2026-11-11: Required code, QA and docs-contract delivery reviews approve. One shared test-oracle defect (CODE-DEL-1) was repaired and independently reverified by both affected lanes; all finding heads are terminal. QA confirms all ten ACs and the guidance-delivery intent, with field effectiveness unproven. Targeted delivery policy requires no additional council. Final canonical suite is next; no closure authority is asserted.

2026-11-11: Intent outcome: achieved for delivered guidance in both changes and the wave Objective. Eight new contract tests exercise conditional language guidance, upgrade reconciliation and the real missing-role renderer; the existing changed-carrier pin and all eight focused second-profile tests pass. Original seed snapshots and two deletion/contamination controls reject missing or leaked guidance. These establish instruction delivery, not better agent behavior or measured port speed; the reporter’s next upgrade and port remain the field check. QA independently checks this assessment.

- 2026-11-11: Operator authorized one further bounded readiness repair and focused verification after the external review stopped at QA-RDY2-1. Independent plan review confirmed that issue and qualified overbroad cost/workaround wording, preserved existing language expertise and clarified opt-in lint authority. Current receipt publishes those amended Requirements and ACs; independent QA/code/docs review refreshes only that delta.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 29 | 1,778,439 |
| implement | 36 | 131,806 |
| review | 152 | 854,446 |
| **Total** | **217** | **2,764,691** |

<!-- wave:context-efficiency-state {"generation":224,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":36,"content_source_credit":142743,"derived_artifact_credit":0,"direct_net":131806,"estimated_tokens_saved":131806,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1122,"response_debit":14412,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4597},"plan":{"calls":29,"content_source_credit":1863369,"derived_artifact_credit":1489,"direct_net":1778439,"estimated_tokens_saved":1778439,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8108,"response_debit":83813,"source_credit_count":55,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5502},"review":{"calls":152,"content_source_credit":1119375,"derived_artifact_credit":1755,"direct_net":854446,"estimated_tokens_saved":854446,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11294,"response_debit":259166,"source_credit_count":96,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":217,"content_source_credit":3125487,"derived_artifact_credit":3244,"direct_net":2764691,"estimated_tokens_saved":2764691,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20524,"response_debit":357391,"source_credit_count":162,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13875},"wave_id":"237ee language-aware-builder-and-reviewer-guidance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 14 | 0 | 9 | 12,375,982 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":12375982,"surfaced_events":14} -->
<!-- wave:exploration-avoided end -->
