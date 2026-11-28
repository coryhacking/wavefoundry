# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `24jwg cheaper-verification-and-council-triggers`
Title: Cheaper Verification And Council Triggers

## Objective

Agents in every project that installs Wavefoundry find cheap verification failures in seconds and run the full verification once before close, and a spec that names platforms without changing platform behaviour can declare so and skip the delivery Council. The close gate, receipt scope and other Council triggers are unchanged.

## Changes

Spec ID: `24jwe-enh verification-order-and-guard-run`
Spec Status: `complete`

Spec ID: `24jwf-enh platform-statement-council-trigger`
Spec Status: `complete`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-11-27

## Wave Summary

Wave `24jwg` (Cheaper Verification And Council Triggers) delivered two changes: Order verification by cost, with a guard run and An explicit declaration can rule out the cross-platform Council trigger.

Intent outcome: partial. Delivered and verified: `run_tests.py --guards` (9 files, 136 tests, about 5 s) and guard-first full runs (24jwe AC-1, AC-2, AC-6; the final suite log shows the guard files completing in the first nine slots); project-neutral cost-ordering guidance in seeds 180 and 209 (AC-3); docs (AC-4); the per-text, line-anchored `cross_platform_changed: false` override with evaluator v9, small-lane two-text coverage and docs (24jwf AC-1 to AC-4); final full suite 13673 tests OK on fingerprint `8a666880e73ca96f`, second profile on every touched test file OK (AC-5). In-wave evidence: the guard run caught a real defect in about 5 s, where 24i2t lost a full run to the same class. Post-release outcomes are recorded as accepted findings INTENT-1-full-runs-per-wave (fewer full runs per wave, read from later work logs) and INTENT-2-declaration-adoption (the Council saving depends on authors adding the declaration). qa-reviewer independently agreed with partial; council-delivery intent_fit partially.

**Changes delivered:**

- **Order verification by cost, with a guard run** (`24jwe-enh verification-order-and-guard-run`) — AC-1, AC-2, AC-3, AC-6, AC-4 and AC-5 completed. Key decisions: Both a named `--guards` run and guard-first ordering in full runs; Decline the per-file receipt for test-only edits.
- **An explicit declaration can rule out the cross-platform Council trigger** (`24jwf-enh platform-statement-council-trigger`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: An explicit `cross_platform_changed: false` overrides bare OS names; Decline deriving `primer_depth`.

## Watchpoints

- Watchpoint: 24jwf bumps the review-policy evaluator version, so this wave's own receipt goes stale after that edit; re-Prepare before delivery review.
- Watchpoint: apply the new practice here: touched-file tests plus guards after each edit, batched delivery repairs, one full suite before close.
- Watchpoint: seed edits (170, 180, 209) need `seed_edit_allowed`; scripts need `framework_edit_allowed`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-RDY-1-false-override-leak | do_now | no | completed | — |
| CODE-RDY-2-scope-contradiction | do_now | no | completed | — |
| INTENT-1-full-runs-per-wave | dont_do_later | no | not_required | — |
| INTENT-2-declaration-adoption | dont_do_later | no | not_required | — |
| QA-RDY-1-false-override-leak | do_now | no | completed | — |

*Machine review state — 5 findings; current: do_now 3, maybe_later 0, dont_do_later 2, not_issue 0*
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
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-27: Intent outcome: partial. Delivered and verified: `run_tests.py --guards` (9 files, 136 tests, about 5 s) and guard-first full runs (24jwe AC-1, AC-2, AC-6; the final suite log shows the guard files completing in the first nine slots); project-neutral cost-ordering guidance in seeds 180 and 209 (AC-3); docs (AC-4); the per-text, line-anchored `cross_platform_changed: false` override with evaluator v9, small-lane two-text coverage and docs (24jwf AC-1 to AC-4); final full suite 13673 tests OK on fingerprint `8a666880e73ca96f`, second profile on every touched test file OK (AC-5). In-wave evidence: the guard run caught a real defect in about 5 s, where 24i2t lost a full run to the same class. Post-release outcomes are recorded as accepted findings INTENT-1-full-runs-per-wave (fewer full runs per wave, read from later work logs) and INTENT-2-declaration-adoption (the Council saving depends on authors adding the declaration). qa-reviewer independently agreed with partial; council-delivery intent_fit partially.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 36 | 130,426 |
| implement | 17 | 0 |
| review | 54 | 319,701 |
| **Total** | **107** | **450,127** |

<!-- wave:context-efficiency-state {"generation":106,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":17,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-1010,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":338,"response_debit":2068,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1396},"plan":{"calls":36,"content_source_credit":246111,"derived_artifact_credit":4412,"direct_net":130426,"estimated_tokens_saved":130426,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17481,"response_debit":109095,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6479},"review":{"calls":54,"content_source_credit":448285,"derived_artifact_credit":2958,"direct_net":319701,"estimated_tokens_saved":319701,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7353,"response_debit":131118,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6929}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":107,"content_source_credit":694396,"derived_artifact_credit":7370,"direct_net":449117,"estimated_tokens_saved":450127,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25172,"response_debit":242281,"source_credit_count":64,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14804},"wave_id":"24jwg cheaper-verification-and-council-triggers"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
