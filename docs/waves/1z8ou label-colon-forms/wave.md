# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-28
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z8ou label-colon-forms`
Title: Label Colon Forms

## Objective

A downstream vocabulary can use Wave, Wave ID and Wave Status as labels, because every reader matches the colon-terminated label and the validator compares those forms.

## Changes

Change ID: `1z8os-enh label-prefix-rule-uses-colon-forms`
Change Status: `complete`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-09-28

## Wave Summary

Wave `1z8ou` (Label Colon Forms) delivered one change: Label Prefix Rule Compares Colon Forms. Notable adjustments during implementation: Label Prefix Rule Compares Colon Forms: Mutation control (AC-2 d), run in scratch copies under the session scratchpad, not in the repository: unanchoring `server_impl._CHANGE_STATUS_PATTERN` fails `test_member_ids_and_statuses` (list_waves reads the `Previous Wave Status` line); making the dashboard `_WAVE_RE` match the bare label fails `test_dashboard_reads_the_back_reference` (reads `planned` from the `Wave Status` line). Reverting the four `ID_KEY` tests or `_change_block_pattern` to the unanchored form does NOT fail the driver: the `ID_KEY` tests are also gated by the member heading and closed status (lines 1134/1171) or iterate only the record file (2227/2363), and the block pattern matches an exact change id, so the unanchored forms produce no observable error on this fixture. The census fails on all four mutated trees, naming each line. Focused suites green: test_vocabulary_profile (32), test_vocabulary_second_profile (11), test_label_reader_census (5), test_vocabulary_census (5), test_docs_lint (1115), test_server_tools_lifecycle (552), test_vocabulary_writers, test_archive_root, test_record_layout_lifecycle, test_record_layout_nested, test_record_layout_census, test_lifecycle_mutation_lock, test_review_policy; Label Prefix Rule Compares Colon Forms: Implemented Requirements 1 to 5. Census predicate: every non-test `.py` line under `scripts/` except `vocabulary_profile.py` naming `ID_KEY`, `MEMBER_ID_LABEL`, `MEMBER_STATUS_LABEL`, `PREVIOUS_STATUS_LABEL` or `BACKREF_LABEL` (optionally `_RE`) as a word; each reference must sit in a `^`-anchored colon-terminated regex field, a `re.fullmatch` of the colon form, or `startswith(f"{label}:")` on a `splitlines()` line, else inside an allowlisted snippet (message, writer, exact_key, newline_anchored, variable). Result: 63 reference lines outside tests and the profile module (matching the review's figure of about 63); the six colon-terminated unanchored readers were exactly those the plan named (four `f"{_vocab.ID_KEY}:" in text` tests in `wave_validators`, `_change_block_pattern`, the template fill in `server_impl.new_change`); no bare-label reader; no difference from the review census. Anchored with `(?m)^` (`\n?^` for the block pattern), then relaxed `validation_errors` to casefolded duplicate refusal with a casefolded fixed-label prefix loop. `test_labels_must_not_prefix_each_other` is inverted and renamed `test_labels_may_prefix_each_other`. New `tests/test_label_reader_census.py`; `PrefixLabelProfileTests` in the second-profile driver. Gapfill: `code_pattern` with a `scripts/**/*.py` glob skipped top-level modules and `server_impl.py` (over 1 MB), so the reference census was re-run with `grep -rnE`.

**Changes delivered:**

- **Label Prefix Rule Compares Colon Forms** (`1z8os-enh label-prefix-rule-uses-colon-forms`) — 5 ACs completed. Key decisions: Refuse only exact (casefolded) duplicate labels; keep the heading prefix rule; casefold the fixed-label prefix rule; Anchor the six unanchored readers and enforce anchoring with a census
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-F1 | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 70 | 3,868,276 |
| implement | 19 | 329,280 |
| review | 29 | 303,365 |
| **Total** | **118** | **4,500,921** |

<!-- wave:context-efficiency-state {"generation":118,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":19,"content_source_credit":343827,"derived_artifact_credit":1039,"direct_net":329280,"estimated_tokens_saved":329280,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1774,"response_debit":16394,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2582},"plan":{"calls":70,"content_source_credit":4002506,"derived_artifact_credit":3425,"direct_net":3868276,"estimated_tokens_saved":3868276,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3632,"response_debit":143236,"source_credit_count":121,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9213},"review":{"calls":29,"content_source_credit":360552,"derived_artifact_credit":1010,"direct_net":303365,"estimated_tokens_saved":303365,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3688,"response_debit":56825,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":118,"content_source_credit":4706885,"derived_artifact_credit":5474,"direct_net":4500921,"estimated_tokens_saved":4500921,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9094,"response_debit":216455,"source_credit_count":161,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14111},"wave_id":"1z8ou label-colon-forms"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
