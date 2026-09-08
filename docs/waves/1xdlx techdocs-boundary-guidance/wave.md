# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-07
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xdlx techdocs-boundary-guidance`
Title: Techdocs Boundary Guidance

## Objective

Make Refresh TechDocs remediation guidance accurately distinguish navigation, publication, and repository-link behavior, carry the correction through upgrades, and verify that post-1.21.0 changes have valid upgrade convergence paths.

## Changes

Change ID: `1w3bt-doc techdocs-boundary-remediation-guidance`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: technical-writer, implementer
- Requested review lanes: docs-contract-reviewer, qa-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-09-07

## Wave Summary

Wave `1xdlx techdocs-boundary-guidance` (Techdocs Boundary Guidance) delivered one change: Clarify TechDocs Publication-Boundary Repairs and Upgrade Propagation. Notable adjustments during implementation: Clarify TechDocs Publication-Boundary Repairs and Upgrade Propagation: Thought: validate the complete docs surface, inspect the scoped diff, and run the full framework suite last.; Clarify TechDocs Publication-Boundary Repairs and Upgrade Propagation: Reflect: operator review exposed an upgrade propagation gap and brought the adjacent internal wording inconsistency into scope.; Clarify TechDocs Publication-Boundary Repairs and Upgrade Propagation: Reflect: expanded-scope readiness review rejected an underspecified merge and an open-ended wave census.

**Changes delivered:**

- **Clarify TechDocs Publication-Boundary Repairs and Upgrade Propagation** (`1w3bt-doc techdocs-boundary-remediation-guidance`) — 8 ACs completed. Key decisions: Correct guidance and add one polarity regression; do not alter the audit.; Record the change under Unreleased rather than the stale `1.19.0` section named during planning.
## Watchpoints

- Watchpoint: preserve the audit algorithm and result schema while tests pin its current semantics.
- Edit canonical seed 178 before synchronizing the self-hosted prompt.
- Keep the audit algorithm and result schema unchanged.
- Do not infer a repository remote or branch when describing explicit repository URLs.
- Preserve target-project additions while reconciling the Refresh TechDocs prompt from a changed seed 178.
- Add no migration when packaged replacement, an existing version gate, or safe optional-state evolution already converges the target.
- Retain the pre-apply seed diff so a changed seed 178 is observable after extraction, and stop on ambiguous project-owned prompt clauses rather than replacing the file.

## Review Checkpoints

- **Framework-operator acknowledgment — 2026-09-07: ACKNOWLEDGED** (the operator explicitly directed this wave to repair the internal inconsistency, add upgrade instructions, and evaluate every completed wave since the last upgrade.)
- **Review plan — 2026-09-07: COMPLETE** (self-answered: the current changelog target is Unreleased; canonical seed 178 is edited first and the self-hosted authored prompt is synchronized manually; no operator questions remain; stop condition reached after narrowing `exclude_docs` wording to its two-tier precedence semantics.)
- **Prepare-phase Wave Council [prepare-council] — 2026-09-07: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a universal later-negation claim was false because direct-file matches outrank ancestor-directory matches; strongest-alternative: state the two-tier rule and test exact-file exclusion plus exact-file re-inclusion. The plan was corrected before approval, both seats accepted the correction, and three existing boundary/link regressions passed.)
- **Delivery-phase Wave Council [delivery-council] — 2026-09-07: PASS** (moderator: wave-council; primer-depth: standard; fingerprint: `d76e06b96d4201464fe8609321b28cc665fc483d`; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; seat agreement: pass with one adjacent finding; material disagreement: the primer questioned whether the stale internal audit-module overview invalidated delivery, while the rotating seat classified it outside the declared public carrier scope; resolution: record `DEL-1` as pre-existing adjacent internal documentation and reject scope expansion for this wave. The strongest alternative was a remediation matrix, retained as optional because the delivered paragraph is concise and fully pinned. Code, QA, and docs-contract lanes approved the frozen diff; 14 mutation classes were killed, docs validation passed, and the current framework receipt covers 8,526 tests.)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | code-reviewer, docs-contract-reviewer |
| QA-RDY-1 | not_issue | no | not_required | qa-reviewer |
| RED-RDY-CLOSE-1 | do_now | no | completed | wave-council-readiness |

*Machine review state — 3 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 1*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 156 | 744,899 |
| implement | 41 | 0 |
| review | 666 | 10,522,946 |
| **Total** | **863** | **11,267,845** |

<!-- wave:context-efficiency-state {"generation":773,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":41,"content_source_credit":4830,"derived_artifact_credit":0,"direct_net":-3876,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1595,"response_debit":10260,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3149},"plan":{"calls":156,"content_source_credit":1075289,"derived_artifact_credit":993,"direct_net":744899,"estimated_tokens_saved":744899,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8129,"response_debit":335520,"source_credit_count":74,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12266},"review":{"calls":666,"content_source_credit":12342940,"derived_artifact_credit":6520,"direct_net":10522946,"estimated_tokens_saved":10522946,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":57364,"response_debit":1771039,"source_credit_count":465,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":863,"content_source_credit":13423059,"derived_artifact_credit":7513,"direct_net":11263969,"estimated_tokens_saved":11267845,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":67088,"response_debit":2116819,"source_credit_count":540,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":17304},"wave_id":"1xdlx techdocs-boundary-guidance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 81 | 0 | 25 | 71,488,077 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":25,"estimated_exploration_avoided":71488077,"surfaced_events":81} -->
<!-- wave:exploration-avoided end -->
