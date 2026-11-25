# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-23
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `249ar memory-maintenance-by-signal`
Title: Memory Maintenance By Signal

## Objective

Maintainers who run Review memories see records whose targets no longer resolve at HEAD, or have churned since their last recorded check, at the front of the audit batch, with the reason shown. Confidence and `Updated:` change only when a check is recorded. The wave builds the tooling and measures it read-only; it does not rewrite this repository's memory records.

## Changes

Change ID: `246to-enh memory-revalidation-by-signal`
Change Status: `implemented`

Change ID: `24885-bug memory-withhold-and-markup-case`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-24

## Wave Summary

Wave `249ar` (Memory Maintenance By Signal) delivered two changes: Queue memory records for revalidation by signal and Memory validation withholds every stored field, and markup matching ignores case.

**Changes delivered:**

- **Queue memory records for revalidation by signal** (`246to-enh memory-revalidation-by-signal`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13 and AC-14 completed. Key decisions: Derive the flag on each read; persist nothing; Remove churn attenuation for every kind, and surface flagged records with their flag.
- **Memory validation withholds every stored field, and markup matching ignores case** (`24885-bug memory-withhold-and-markup-case`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: A separate change in wave `249ar`, not new requirements in `246to`; Withhold a matching `memory_id` in the view rather than refuse the call.

## Watchpoints

- Watchpoint: seed 240 edits need the `seed_edit_allowed` gate; other edits under `.wavefoundry/framework/` need `framework_edit_allowed`.
- No test may write under this repository's `docs/agents/memory/` or `docs/evals/`.
- Follow-up after close, with operator authorization: a Review memories pass over the `uncoverable_records` batch, then the versioned freeze of query set version 2 with an operator spot-check (coordinator decision, 2026-11-24).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 24885-rewrite-copies-source-event | do_now | no | completed | qa-reviewer |
| 24885-source-event-exemption | do_now | no | completed | qa-reviewer |
| 249ar-rt-bare-target-churn-blind | do_now | no | completed | — |
| blocking-contract-mismatch | do_now | no | completed | — |
| cr-24885-source-event-lint-exemption-and-rewrite-inherit | do_now | no | completed | — |
| cr-249ar-blocking-semantics-contradiction | do_now | no | completed | — |
| qa-249ar-eval-ids-break-aggregate-only | do_now | no | completed | — |
| qa-249ar-keep-note-breaks-candidate-paths | do_now | no | completed | — |
| rt-24885-rewrite-propagates-stored-source-event | do_now | no | completed | — |
| rt-24885-rewrite-residual-stored-echo | do_now | no | completed | — |

*Machine review state — 10 findings; current: do_now 10, maybe_later 0, dont_do_later 0, not_issue 0*
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
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Depends on wave `249as memory-admission-hardening` (track 3 of arc `244cm-arc memory-quality`, change `249aq-enh memory-admission-hardening`), which delivers `memory_records.resolve_memory_refs` and `memory_ref_tree`. This wave reads each target ref's `state`, not the admission `blocking` list (coordinator decision, 2026-11-24). This wave must not activate before they are delivered; if `249as` slips, this wave waits (coordinator decision, 2026-11-24).

## Review Checkpoints

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 104 | 837,224 |
| implement | 48 | 0 |
| review | 97 | 1,085,066 |
| **Total** | **249** | **1,922,290** |

<!-- wave:context-efficiency-state {"generation":242,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":48,"content_source_credit":5470,"derived_artifact_credit":0,"direct_net":-1295,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1907,"response_debit":15362,"source_credit_count":3,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10504},"plan":{"calls":104,"content_source_credit":1296626,"derived_artifact_credit":5374,"direct_net":837224,"estimated_tokens_saved":837224,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":62837,"response_debit":417231,"source_credit_count":101,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15292},"review":{"calls":97,"content_source_credit":1274462,"derived_artifact_credit":3345,"direct_net":1085066,"estimated_tokens_saved":1085066,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8863,"response_debit":190797,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6919}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":249,"content_source_credit":2576558,"derived_artifact_credit":8719,"direct_net":1920995,"estimated_tokens_saved":1922290,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":73607,"response_debit":623390,"source_credit_count":160,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":32715},"wave_id":"249ar memory-maintenance-by-signal"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 2 | 2,636,098 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":2636098,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
