# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zimb expected-test-profile`
Title: Expected Test Profile

## Objective

Profile guards check the loaded constants against the profile the tree is meant to be (named by the run mode, or by an asset marked active, or the shipped defaults), so a tree left on the wrong profile fails; the second profile mirrors the Set/Wave rename distributions use.

## Changes

Change ID: `1zima-debt profile-assets-name-the-expected-profile`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-10-01

## Wave Summary

Wave `1zimb` (Expected Test Profile) delivered one change: Profile Assets Name the Expected Profile, and the Second Profile Matches Set and Wave.

**Changes delivered:**

- **Profile Assets Name the Expected Profile, and the Second Profile Matches Set and Wave** (`1zima-debt profile-assets-name-the-expected-profile`) — 6 ACs completed. Key decisions: Mark the active asset with a field inside it; Run mode names its profile through the copy's runner environment
## Watchpoints

- Watchpoint: the default run of this repository must not change (no asset is active here); run the whole suite under `--profile second` and `--profile declared` before delivery review.

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
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: an expected profile that replaces the active asset with the run-mode profile fails every run mode in a distribution, because `apply_profile` overlays the copied tree that already carries the distribution's profile; resolved by making the expected profile a layering (active asset, then run-mode profile) and refusing a receipt-writing run while `WAVEFOUNDRY_TEST_PROFILE` is set; strongest-alternative: reset the copy to shipped before applying, rejected because run mode would then stop testing the distribution's own profile)
- Prepare council seat evidence (2026-10-01): one independent Opus reviewer ran both seats and the code, qa and architecture lanes against the code: the Set/Wave asset passes `vocabulary_profile.validation_errors`; a scratch whole-suite `--profile second` run with Set/Wave and the literal fixes passed 149/149 files, 10,335 tests; it found the replace-not-layer defect, the stray-variable receipt risk, an unmeetable AC-2 and three unlisted tests that would break. Its plan edits (Requirements 2-7 and 10, AC-2, AC-3 (f)(g), AC-4, the Risk row) were applied verbatim.
- **Delivery Wave Council [delivery-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the active base is self-declared, so a distribution that drifts its constants and edits its own active asset in the same commit still passes; accepted as inherent to a self-declared profile; strongest-alternative: pin the active asset's digest outside the fixtures directory, rejected because the Decision Log keeps the asset and its activation in one file)
- Delivery seat evidence (2026-10-01): one independent Opus reviewer ran both seats and the code, qa and architecture lanes in a scratch copy: layering equals what `apply_profile` loads (executed with an active asset plus each run mode); `WAVEFOUNDRY_TEST_PROFILE` read only in `run_mode_profile_name`; profile names checked against `_PROFILE_NAME_RE` before any path join; seven mutants (resolver ignores active, replace instead of layer, two fallbacks, refusal disabled or removed, run-mode env dropped) all failed tests. Three maybe_later items (run-mode layer missing from two-active error, `--schedule-control` exemption undocumented, refusal ordering unpinned) were fixed and reverified by the same reviewer with two further mutants caught. Full suite 10354 OK; `--profile second` and `--profile declared` 149/149 files.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 16 | 6,934 |
| implement | 19 | 0 |
| review | 9 | 24,965 |
| **Total** | **44** | **31,899** |

<!-- wave:context-efficiency-state {"generation":44,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":19,"content_source_credit":4341,"derived_artifact_credit":0,"direct_net":-197,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":688,"response_debit":4830,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":980},"plan":{"calls":16,"content_source_credit":17886,"derived_artifact_credit":2226,"direct_net":6934,"estimated_tokens_saved":6934,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2418,"response_debit":14569,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":9,"content_source_credit":38932,"derived_artifact_credit":1305,"direct_net":24965,"estimated_tokens_saved":24965,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1856,"response_debit":15732,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":44,"content_source_credit":61159,"derived_artifact_credit":3531,"direct_net":31702,"estimated_tokens_saved":31899,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4962,"response_debit":35131,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7105},"wave_id":"1zimb expected-test-profile"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
