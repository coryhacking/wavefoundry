# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z8tr timed-helper-tree-kills`
Title: Timed Helper Tree Kills

## Objective

Timed helpers that start child processes (setup installs, the upgrade runner's hooks and child steps, the techdocs audit worker and the test runner's per-file workers) end their whole process tree on timeout, so a timeout can no longer leave descendants running or hang on Windows.

## Changes

Change ID: `1z8qm-bug timed-helpers-leave-process-trees`
Change Status: `complete`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-09-27

## Wave Summary

Wave `1z8tr` (Timed Helper Tree Kills) delivered one change: Timed Helpers That Start Children Leave Process Trees. Notable adjustments during implementation: Timed Helpers That Start Children Leave Process Trees: Readiness review requested changes; adopted. F1: a 1.27.0 runner imports the new `setup_index` with its old `subprocess_util`, so `setup_index` falls back to `isolated_run` (Requirement 5, AC-5). F2: `run_tests.py` moved out of scope (worker-thread waits cannot see Ctrl-C). F3: the helper waits in slices so an interrupt is seen on Windows too (Requirement 4). F4 test repointing, F5 (stdin; corrected at recheck: the sites already use `DEVNULL`), F6 hard kill, F7 out-of-scope labels, F8 the check's key.

**Changes delivered:**

- **Timed Helpers That Start Children Leave Process Trees** (`1z8qm-bug timed-helpers-leave-process-trees`) — 6 ACs completed. Key decisions: Keep `run_tests.py` out of scope; Route only helpers that start children or run long; leave single-program probes
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

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
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 15 | 33,143 |
| implement | 8 | 1,088,495 |
| review | 8 | 22,993 |
| **Total** | **31** | **1,144,631** |

<!-- wave:context-efficiency-state {"generation":31,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":8,"content_source_credit":1102395,"derived_artifact_credit":0,"direct_net":1088495,"estimated_tokens_saved":1088495,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":162,"response_debit":13738,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":15,"content_source_credit":44846,"derived_artifact_credit":1079,"direct_net":33143,"estimated_tokens_saved":33143,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1651,"response_debit":17642,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":8,"content_source_credit":35187,"derived_artifact_credit":1294,"direct_net":22993,"estimated_tokens_saved":22993,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1852,"response_debit":13952,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":31,"content_source_credit":1182428,"derived_artifact_credit":2373,"direct_net":1144631,"estimated_tokens_saved":1144631,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3665,"response_debit":45332,"source_credit_count":64,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8827},"wave_id":"1z8tr timed-helper-tree-kills"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
