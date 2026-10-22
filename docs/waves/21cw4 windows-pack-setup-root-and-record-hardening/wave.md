# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21cw4 windows-pack-setup-root-and-record-hardening`
Title: Windows Pack Setup Root And Record Hardening

## Objective

Operators on native Windows can upgrade without a false verified-pack refusal, setup refuses a folder that is not a Wavefoundry repository before writing anything and, without `--root`, targets the repository that holds the setup script, and renders and close-change refuse inputs they cannot read safely. Agents can search seeds with Grep and Glob, and a source-rebranded distribution can run the profile shortcut tests unchanged. Boundaries: no proof-shape, parser or close-wave changes; valid roots, links and records behave as today.

## Changes

Change ID: `21alh-bug verified-pack-identity-mixes-fstat-and-lstat`
Change Status: `implemented`

Change ID: `21ayv-bug pre-edit-hook-gates-read-only-search-tools`
Change Status: `implemented`

Change ID: `21ayw-bug setup-refuses-root-without-framework`
Change Status: `implemented`

Change ID: `21ayx-bug baseline-destination-symlink-is-followed`
Change Status: `implemented`

Change ID: `21cw2-bug close-change-dependency-gate-reads-last-status`
Change Status: `implemented`

Change ID: `21cw3-task rebrand-stable-profile-shortcut-test-names`
Change Status: `implemented`

Change ID: `21cw5-enh setup-default-root-is-script-repository`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (Claude Code primary)
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-21

## Wave Summary

Wave `21cw4` (Windows Pack Setup Root And Record Hardening) delivered 7 changes: Compare Pack File Identities Taken by Different Stat Calls Without ctime, Let the Claude Pre-Edit Hook Pass Read-Only Grep and Glob, Setup Refuses a Root Without the Framework Copy, Refuse a Carrier Destination That Is a Dangling Link, Close Change Refuses Ambiguous Wave Records, Rebrand-Stable Names in the Profile Shortcut Tests, and Setup Defaults to the Repository That Holds the Script. Notable adjustments during implementation: Close Change Refuses Ambiguous Wave Records: Implemented: `_close_change_ambiguity_messages` and a `wave_record_ambiguous` refusal at the top of `wf_close_change_response`, before every gate and planned write (duplicate record, multiple status lines incl. unreadable count, fenced record line with line number); parser and close-wave unchanged. Gate text added to `docs/prompts/close-change.prompt.md`, its install baseline `install/lifecycle-prompts/close-change.prompt.md`, seed-190 Close change gates and seed-100 close-change bullet (seed gate opened/closed around the seed edit).; Rebrand-Stable Names in the Profile Shortcut Tests: Implemented: `ProfileShortcutLookupTests._names()` derives the colliding slug, shortcut and `Finish <noun>` alias from `DEFAULT_PROMPT_NAMES["close-wave"]` and the old phrase from `DEFAULT_PROMPT_NAMES["close-change"]`; second rename is `close-unit` / "Close unit"; the two `Prepare wave` tests read the phrase and declared path from the profile; the collision test asserts the renamed shortcut equals another key's default. AC-1 scratch: the substitution applied to only the two named files does not import (other modules call `prompt_doc("close-change")` at import), so it was applied to every `.py` under a scratch copy of `.wavefoundry/framework/scripts`.; Rebrand-Stable Names in the Profile Shortcut Tests: Clarification of the AC-1 note: the implementer's first scratch rebrand did not rewrite the `prepare-wave` slug; the coordinator's rerun added it. Both runs gave the same result: the two close-name tests fail before and pass after, and the two Prepare-wave tests pass before and after.

**Changes delivered:**

- **Compare Pack File Identities Taken by Different Stat Calls Without ctime** (`21alh-bug verified-pack-identity-mixes-fstat-and-lstat`) — 5 ACs completed. Key decisions: Ignore ctime only in comparisons that mix handle and path snapshots
- **Let the Claude Pre-Edit Hook Pass Read-Only Grep and Glob** (`21ayv-bug pre-edit-hook-gates-read-only-search-tools`) — 4 ACs completed. Key decisions: Name Grep and Glob as non-edit tools
- **Setup Refuses a Root Without the Framework Copy** (`21ayw-bug setup-refuses-root-without-framework`) — 4 ACs completed. Key decisions: Refuse in `main` before reconciliation
- **Refuse a Carrier Destination That Is a Dangling Link** (`21ayx-bug baseline-destination-symlink-is-followed`) — 5 ACs completed. Key decisions: Refuse dangling links and `.git` targets in the shared helper
- **Close Change Refuses Ambiguous Wave Records** (`21cw2-bug close-change-dependency-gate-reads-last-status`) — 6 ACs completed. Key decisions: One ambiguity rule in close-change: duplicate records, more than one status value, or a fenced id line
- **Rebrand-Stable Names in the Profile Shortcut Tests** (`21cw3-task rebrand-stable-profile-shortcut-test-names`) — 2 ACs completed. Key decisions: Derive the collision from the default table
- **Setup Defaults to the Repository That Holds the Script** (`21cw5-enh setup-default-root-is-script-repository`) — 5 ACs completed. Key decisions: Default only in the `__main__` entry, by changing into the script's repository
## Watchpoints

- Watchpoint: 21ayw came from a private report: keep its CHANGELOG entry and commit message free of exploit detail.
- Follow-up: 21alh cannot protect its own install: the reply tells the distribution to keep its local patch until the fixed release is installed.
- Open `framework_edit_allowed` before framework edits and close it after; run the framework suite last before close.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 21cw4-git-casefold-platform-keyed | do_now | no | completed | code-reviewer, security-reviewer |
| 21cw4-guard-real-change-tests | do_now | no | completed | code-reviewer |
| 21cw4-memory-backfill-setup-fixture | do_now | no | completed | qa-reviewer |
| 21cw4-staging-validation-ctime-binding | do_now | no | completed | security-reviewer, code-reviewer |
| 21cw4-upgrade-skipped-carrier-warning-swallowed | do_now | no | pending | — |

*Machine review state — 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 48 | 36,247 |
| implement | 105 | 0 |
| review | 57 | 666,092 |
| **Total** | **210** | **702,339** |

<!-- wave:context-efficiency-state {"generation":199,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":105,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-22593,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4225,"response_debit":25628,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7260},"plan":{"calls":48,"content_source_credit":75697,"derived_artifact_credit":9339,"direct_net":36247,"estimated_tokens_saved":36247,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3958,"response_debit":49259,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":57,"content_source_credit":783912,"derived_artifact_credit":6901,"direct_net":666092,"estimated_tokens_saved":666092,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17152,"response_debit":110783,"source_credit_count":71,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":210,"content_source_credit":859609,"derived_artifact_credit":16240,"direct_net":679746,"estimated_tokens_saved":702339,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25335,"response_debit":185670,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14902},"wave_id":"21cw4 windows-pack-setup-root-and-record-hardening"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
