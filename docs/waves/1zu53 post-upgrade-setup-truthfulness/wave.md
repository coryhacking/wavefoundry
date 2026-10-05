# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-04
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zu53 post-upgrade-setup-truthfulness`
Title: Post Upgrade Setup Truthfulness

## Objective

Make post-upgrade and setup output tell the truth before 1.29.0 ships: the upgrade summary reports the setup state later checks will see, and terminal `wf setup` stops losing GPU acceleration to a probe that never activates the tool venv.

## Changes

Change ID: `1zu51-bug upgrade-summary-setup-ready-without-baseline`
Change Status: `implemented`

Change ID: `1zu52-bug coreml-probe-child-skips-tool-venv`
Change Status: `implemented`

## Participants

- Coordinator: wave-council
- Write-owning roles: implementer
- Requested review lanes: release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-10-04

## Wave Summary

Wave `1zu53` (Post Upgrade Setup Truthfulness) delivered two changes: Upgrade Summary Reports Setup Ready When No Setup Baseline Was Recorded and The Isolated CoreML Probe Child Never Activates The Tool Venv.

**Changes delivered:**

- **Upgrade Summary Reports Setup Ready When No Setup Baseline Was Recorded** (`1zu51-bug upgrade-summary-setup-ready-without-baseline`) — 5 ACs completed. Key decisions: Report the stamp-aware assessment instead of inventing a `setup_baseline_not_recorded` reason
- **The Isolated CoreML Probe Child Never Activates The Tool Venv** (`1zu52-bug coreml-probe-child-skips-tool-venv`) — 5 ACs completed. Key decisions: Activate inside the child rather than launching it with `tool_venv_python()`
## Watchpoints

- Watchpoint: framework edits need `framework_edit_allowed`; the seed 160 edit needs `seed_edit_allowed`.
- Watchpoint: full suites run in scratch copies; the receipt run is last, in the repo.
- Follow-up: the other items from the same field report (`.gitattributes` drift, `--check` transient after setup, first-install closing text) are triaged after this wave.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 25 | 770,387 |
| implement | 7 | 0 |
| review | 12 | 45,257 |
| **Total** | **44** | **815,644** |

<!-- wave:context-efficiency-state {"generation":34,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":7,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-515,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":57,"response_debit":458,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":25,"content_source_credit":797982,"derived_artifact_credit":3915,"direct_net":770387,"estimated_tokens_saved":770387,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2481,"response_debit":32838,"source_credit_count":37,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":12,"content_source_credit":70710,"derived_artifact_credit":1308,"direct_net":45257,"estimated_tokens_saved":45257,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3947,"response_debit":25130,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":44,"content_source_credit":868692,"derived_artifact_credit":5223,"direct_net":815129,"estimated_tokens_saved":815644,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6485,"response_debit":58426,"source_credit_count":55,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6125},"wave_id":"1zu53 post-upgrade-setup-truthfulness"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
