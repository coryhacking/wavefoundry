# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `242yp extension-loader-and-guru-refresh`
Title: Extension Loader And Guru Refresh

## Objective

Distributions can declare an upgrade journal hook module that uses `@dataclass` with postponed annotations, and the upgrade imports it instead of reporting it as unimportable. A render refreshes the managed Guru subagent description after any vocabulary profile change, while a description customized outside its shortcut names is still kept. A distribution can declare in its active test profile that wall-clock timing-budget tests are skipped, with a visible reason, while the default upstream run keeps them. All three come from Waveforge field feedback.

## Changes

Change ID: `241l1-bug journal-hook-dataclass-import`
Change Status: `implemented`

Change ID: `241l2-bug guru-description-refresh-misses-departing-profile`
Change Status: `implemented`

Change ID: `242yq-enh distribution-timing-budget-bypass`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-11-22

## Wave Summary

Wave `242yp` (Extension Loader And Guru Refresh) delivered 3 changes: Journal hook modules that use dataclasses fail to import during upgrade, Guru description refresh misses a departing vocabulary profile, and Distribution timing-budget bypass.

**Changes delivered:**

- **Journal hook modules that use dataclasses fail to import during upgrade** (`241l1-bug journal-hook-dataclass-import`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Fix upstream under ordinary review; Register the module under its private name only while `exec_module` runs, then restore the prior state, in the shared helper.
- **Guru description refresh misses a departing vocabulary profile** (`241l2-bug guru-description-refresh-misses-departing-profile`) — AC-1, AC-2, AC-3, AC-4, AC-5 and AC-6 completed. Key decisions: Match managed descriptions by form with any text in the shortcut slots; Drop the hand-filled shortcut entries and slot the short form's `Implement wave` and `Close wave`.
- **Distribution timing-budget bypass** (`242yq-enh distribution-timing-budget-bypass`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6 and AC-7 completed. Key decisions: Keep the budget test unchanged in the default run and let a distribution disable timing-budget tests; Declare the bypass in the distribution's active profile asset.

## Watchpoints

- Watchpoint: open `framework_edit_allowed` around framework edits and close it after.
- Watchpoint: the extension loader runs inside the older runner's process during upgrade; the module must never be left registered after the load.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 242yp-cr-guru-slot-excludes-legal-shortcut-chars | do_now | no | completed | — |
| 242yq-CR-R3-1-duplicate-subtest-skip-identity | do_now | no | completed | code-reviewer |
| 242yq-bypass-skip-identity-collision | do_now | no | completed | — |
| 242yq-qa-r3-per-bound-skip-oracle | do_now | no | completed | qa-reviewer |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 92 | 4,416,680 |
| implement | 104 | 17,934 |
| review | 39 | 172,459 |
| **Total** | **235** | **4,607,073** |

<!-- wave:context-efficiency-state {"generation":216,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":104,"content_source_credit":40828,"derived_artifact_credit":1346,"direct_net":17934,"estimated_tokens_saved":17934,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4359,"response_debit":28638,"source_credit_count":3,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8757},"plan":{"calls":92,"content_source_credit":4683651,"derived_artifact_credit":5240,"direct_net":4416680,"estimated_tokens_saved":4416680,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":45072,"response_debit":246928,"source_credit_count":175,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":19789},"review":{"calls":39,"content_source_credit":274159,"derived_artifact_credit":2889,"direct_net":172459,"estimated_tokens_saved":172459,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5673,"response_debit":105694,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":235,"content_source_credit":4998638,"derived_artifact_credit":9475,"direct_net":4607073,"estimated_tokens_saved":4607073,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":55104,"response_debit":381260,"source_credit_count":200,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":35324},"wave_id":"242yp extension-loader-and-guru-refresh"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 648,903 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":648903,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
