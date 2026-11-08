# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-07
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22sft fixture-profile-default-test`
Title: Fixture Profile Default Test

## Objective

A distribution that fills in the fork-editable container fixture profile runs the fixture-helper tests unchanged, keeping the merge checks, while upstream still proves its shipped default adds nothing. Test-only; no shipped behavior changes.

## Changes

Change ID: `22rmf-bug fixture-profile-default-test-downstream`
Change Status: `implemented`

## Participants

- Coordinator: root agent
- Write-owning roles: implementer (coordinator)
- Requested review lanes: code-reviewer, qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-11-07

## Wave Summary

Wave `22sft` (Fixture Profile Default Test) delivered one change: Fixture profile default test fails downstream. Notable adjustments during implementation: Fixture profile default test fails downstream: Known-bad in a scratch copy of the scripts: with the profile returning Waveforge-style arguments (`feature`, `kind`, `scope`), the HEAD test fails, the new pass-through test passes and the shipped-default test fails (default vocabulary; it skips under a renamed profile). With `close_container` dropping its keyword arguments, the pass-through test fails. Gapfill: shell edits and probes on a single known test file.

Intent outcome: partially. A renamed distribution such as Waveforge now runs the fixture-helper tests unchanged with the merge checks kept, and upstream still proves its shipped default adds nothing. A distribution that keeps the default vocabulary but fills in the fixture profile still fails the shipped-default test, a risk the plan accepted. Evidence: default suite 12,591 tests / 231 files / 12 skips green; code and QA delivery approvals with QA mutants; council-delivery `ev-approval-council-delivery`. macOS only.

**Changes delivered:**

- **Fixture profile default test fails downstream** (`22rmf-bug fixture-profile-default-test-downstream`) — 2 ACs completed. Key decisions: Patch the profile inside the pass-through test and keep a separate default-only check.
## Watchpoints

- Watchpoint: rerun the full suite and the second and declared profile qualifications after this change, before the 1.40.0 release dry run.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-07: Intent outcome: partially. A renamed distribution such as Waveforge now runs the fixture-helper tests unchanged with the merge checks kept, and upstream still proves its shipped default adds nothing. A distribution that keeps the default vocabulary but fills in the fixture profile still fails the shipped-default test, a risk the plan accepted. Evidence: default suite 12,591 tests / 231 files / 12 skips green; code and QA delivery approvals with QA mutants; council-delivery `ev-approval-council-delivery`. macOS only.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 14 | 0 |
| implement | 13 | 0 |
| review | 15 | 2,607 |
| **Total** | **42** | **2,607** |

<!-- wave:context-efficiency-state {"generation":41,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":13,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2275,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":441,"response_debit":2240,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":406},"plan":{"calls":14,"content_source_credit":12760,"derived_artifact_credit":2074,"direct_net":-5097,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4159,"response_debit":21274,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5502},"review":{"calls":15,"content_source_credit":33379,"derived_artifact_credit":1032,"direct_net":2607,"estimated_tokens_saved":2607,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4348,"response_debit":31232,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":42,"content_source_credit":46139,"derived_artifact_credit":3106,"direct_net":-4765,"estimated_tokens_saved":2607,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8948,"response_debit":54746,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9684},"wave_id":"22sft fixture-profile-default-test"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
