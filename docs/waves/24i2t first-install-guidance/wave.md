# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `24i2t first-install-guidance`
Title: First Install Guidance

## Objective

A person installing Wavefoundry for the first time learns which Python to use and why, is told when setup runs under a different interpreter than the agent host will launch, and is not shown a factor-review warning the next install step resolves. No change to the Python floor, what blocks setup, or which review lanes run.

## Changes

Spec ID: `24fw1-enh first-install-python-and-factor-guidance`
Spec Status: `complete`

## Participants

- Coordinator: main session
- Write-owning roles: implementer
- Requested review lanes: qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-27

## Wave Summary

Wave `24i2t` (First Install Guidance) delivered one change: Clear Python and factor-review guidance on first install.

Intent outcome: partial. Delivered and verified: the advisory recommends 3.14, covers 3.11 to 3.13 with the python.org installer limit, and warns that every project shares one tool environment (AC-1); setup names a PATH `python3` that differs from the setup interpreter and gives the platform's rerun-setup remedy (AC-2); stale recommendations removed by census (AC-3); the install audit carries the fresh-install factor warning as pending until the seed-050 row (AC-4); plain wording with both options and the `partial` instruction for factors left off (AC-5); final full suite 13654 tests OK on fingerprint `06c63d3cf3db9222`, second profile on touched files OK (AC-6). The measure of success (no factor warning between install rows 2.3 and 2.5, no agent-invented factor decision, an operator settling on one interpreter from the notice) can be read only from the next Waveforge first-install report. Accepted limitations recorded as findings INTENT-1-host-path (setup sees its own PATH, not the host's) and INTENT-2-native-windows (no native Windows run). qa-reviewer independently agreed with partial; council-delivery intent_fit partially.

**Changes delivered:**

- **Clear Python and factor-review guidance on first install** (`24fw1-enh first-install-python-and-factor-guidance`) — AC-1, AC-2, AC-3, AC-4, AC-5 and AC-6 completed. Key decisions: Recommend 3.14 and advise on 3.11 to 3.13; Factor fix: audit carries the warning as pending while the seed-050 row is pending.

## Watchpoints

- Watchpoint: seed edits (011, 160) need `seed_edit_allowed`; framework scripts need `framework_edit_allowed`.
- Watchpoint: run the second profile per touched test file only (`--file`); the full second-profile run is release-only.
- Follow-up: the Waveforge reply carries these verdicts after delivery.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| INTENT-1-host-path | dont_do_later | no | not_required | — |
| INTENT-2-native-windows | dont_do_later | no | not_required | — |

*Machine review state — 2 findings; current: do_now 0, maybe_later 0, dont_do_later 2, not_issue 0*
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

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-27: Intent outcome: partial. Delivered and verified: the advisory recommends 3.14, covers 3.11 to 3.13 with the python.org installer limit, and warns that every project shares one tool environment (AC-1); setup names a PATH `python3` that differs from the setup interpreter and gives the platform's rerun-setup remedy (AC-2); stale recommendations removed by census (AC-3); the install audit carries the fresh-install factor warning as pending until the seed-050 row (AC-4); plain wording with both options and the `partial` instruction for factors left off (AC-5); final full suite 13654 tests OK on fingerprint `06c63d3cf3db9222`, second profile on touched files OK (AC-6). The measure of success (no factor warning between install rows 2.3 and 2.5, no agent-invented factor decision, an operator settling on one interpreter from the notice) can be read only from the next Waveforge first-install report. Accepted limitations recorded as findings INTENT-1-host-path (setup sees its own PATH, not the host's) and INTENT-2-native-windows (no native Windows run). qa-reviewer independently agreed with partial; council-delivery intent_fit partially.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 19 | 55,723 |
| implement | 49 | 139,296 |
| review | 21 | 721,919 |
| **Total** | **89** | **916,938** |

<!-- wave:context-efficiency-state {"generation":87,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":49,"content_source_credit":149209,"derived_artifact_credit":0,"direct_net":139296,"estimated_tokens_saved":139296,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":926,"response_debit":9941,"source_credit_count":7,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":954},"plan":{"calls":19,"content_source_credit":85736,"derived_artifact_credit":2478,"direct_net":55723,"estimated_tokens_saved":55723,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4854,"response_debit":34116,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6479},"review":{"calls":21,"content_source_credit":770501,"derived_artifact_credit":1825,"direct_net":721919,"estimated_tokens_saved":721919,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7896,"response_debit":49440,"source_credit_count":33,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6929}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":89,"content_source_credit":1005446,"derived_artifact_credit":4303,"direct_net":916938,"estimated_tokens_saved":916938,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13676,"response_debit":93497,"source_credit_count":68,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14362},"wave_id":"24i2t first-install-guidance"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
