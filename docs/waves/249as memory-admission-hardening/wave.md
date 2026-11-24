# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-23
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `249as memory-admission-hardening`
Title: Memory Admission Hardening

## Objective

Agents that validate memory candidates get a mechanical floor under their judgment: refs and targets must resolve in the current checkout, credentials and model-control tokens are refused by reason, evidence from URLs or dependency trees is flagged, and a rewrite keeps a resolving target. A briefing for files no record targets is empty and normal. Existing records, the query set, ranking and indexing are unchanged.

## Changes

Change ID: `249aq-enh memory-admission-hardening`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-11-24

## Wave Summary

Wave `249as` (Memory Admission Hardening) delivered one change: Memory admission checks refs, content and anchors before a record is written.

**Changes delivered:**

- **Memory admission checks refs, content and anchors before a record is written** (`249aq-enh memory-admission-hardening`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11 and AC-12 completed. Key decisions: Put the primitive in `memory_records.py` as `resolve_memory_refs` plus `memory_ref_tree`, with this change owning it; Resolve against the working tree, not `git HEAD`.

## Watchpoints

- Watchpoint: run the AC-11 evidence script once before the first code edit and once after the last; the frozen-set control is expected to be unchanged.
- Watchpoint: seed 240 and seed 190 edits need `seed_edit_allowed`; the install template copies need `framework_edit_allowed`.
- Watchpoint: wave `249ar` waits on the primitive contract recorded under AC-10.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 249as-rt-path-form-unspecified | do_now | no | completed | — |
| arch-249as-path-form-truncates-spaced-paths | do_now | no | completed | — |
| cr-249as-evidence-path-form-undefined | do_now | no | completed | — |
| cr-249as-rewrite-pending-refs-contradiction | do_now | no | completed | — |
| qa-249as-rewrite-gone-target-unreachable | do_now | no | completed | — |
| qa-249as-unnamed-test-breakage | do_now | no | completed | — |

*Machine review state — 6 findings; current: do_now 6, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking); known-bad control not applicable: Inspected the docs-contract surface (state vocabulary, 249ar agreement, test list count, Serialization Points, arc rows, docs lint); no defect in this lane, so no known-bad to detect. | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 99 | 1,071,632 |
| implement | 36 | 108,423 |
| review | 83 | 220,856 |
| **Total** | **218** | **1,400,911** |

<!-- wave:context-efficiency-state {"generation":205,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":36,"content_source_credit":118685,"derived_artifact_credit":0,"direct_net":108423,"estimated_tokens_saved":108423,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1317,"response_debit":20043,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11098},"plan":{"calls":99,"content_source_credit":1374431,"derived_artifact_credit":2400,"direct_net":1071632,"estimated_tokens_saved":1071632,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":43241,"response_debit":268256,"source_credit_count":79,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"review":{"calls":83,"content_source_credit":376953,"derived_artifact_credit":1888,"direct_net":220856,"estimated_tokens_saved":220856,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9749,"response_debit":155104,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6868}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":218,"content_source_credit":1870069,"derived_artifact_credit":4288,"direct_net":1400911,"estimated_tokens_saved":1400911,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":54307,"response_debit":443403,"source_credit_count":112,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":24264},"wave_id":"249as memory-admission-hardening"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 2 | 162,905 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":162905,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
