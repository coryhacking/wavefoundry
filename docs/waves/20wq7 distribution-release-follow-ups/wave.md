# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20wq7 distribution-release-follow-ups`
Title: Distribution Release Follow Ups

## Objective

Answer the bounded items of a downstream distribution's report before the next release: a release gate on profile qualification with named exceptions, build provenance and published checksums in every release, a declared list of distribution profile assets, one test that no longer assumes the shipped declaration, and threat-model wording that matches the executable lookup.

## Changes

Change ID: `20wq6-enh distribution-qualification-assets-and-test-declarations`
Change Status: `implemented`

Change ID: `20qvs-enh release-provenance-verification`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator (agent)
- Write-owning roles: implementer
- Requested review lanes: security-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-17

## Wave Summary

Wave `20wq7` (Distribution Release Follow Ups) delivered two changes: Distribution qualification assets, test declarations and lookup wording and Make release verification and qualification provenance explicit. Notable adjustments during implementation: Distribution qualification assets, test declarations and lookup wording: Qualification on the final tree, one run at a time: canonical default `--no-cache` 11,890 tests / 200 files / 12 skips, receipt inputs_hash `fc8af1b262ad8b54c413e8155d3c62f8d9f8d23f7a4ed8e02b234f4351a49da7`; `--qualify-profile second` 11,882 / 200 / 28 skips; `--qualify-profile declared` 11,890 / 200 / 12 skips; both scopes `full fallback: coverage unproven`. `qualification_report.py --compare` passes for both (second: 16 default-only skips; declared: equal). The new gate, called read-only on the real tree, lists all three as passed with no exception. A first attempt was invalid: a reviewer's concurrent focused run held the runner lock and raced the live-tree build's generated files during a profile copy, and the declared run exposed two wave-caused census failures (a timed git call outside the tree-kill routing census, and a patched loader not asserted), both fixed and confirmed by code and security before the rerun.; Distribution qualification assets, test declarations and lookup wording: Implemented. `qualification_scope` accepts the optional distribution-owned list through `_distribution_profile_assets`; two new `CompatibilityCoverageTests`; `RetainedUpgradePreviewTests.setUp` calls `apply_base_declaration`; threat-model Tensorwell sentence and build-and-verification inventory paragraph corrected. Focused: `test_profile_support` 82/82; `test_server_tools_lifecycle` 640 with 2 pre-existing skips under default and declared on a repaired clone, identical to HEAD (an earlier two-file run reported 639 and 5 skips across both files, not reproduced). AC-2 control (scratch clone, profile `closeover` overriding `wf_close_wave`): repaired 640 OK; unrepaired fails exactly `test_registered_actual_lint_previews_are_read_only_for_default_and_positional_modes` and `test_close_reports_new_unpublished_secrets_in_same_lint_pass` with `read_only_preview` absent. Mutants: digest and repeat-inventory guards killed; widening the path pattern is equivalent for scope outcome because the asset-set equality already refuses non-direct children (the pattern only keeps the digest read inside the profiles folder); the 64-hex and name rules are likewise redundant with digest equality and the inventory listing. Delivery finding DEL-2 (QA): the oversized control was invalid JSON, so it passed without the size bound; repaired to a valid list padded past 1 MiB, size-bound mutant now killed. Gapfill: shell reads and Python edit scripts were used because the targets and anchors were fixed by readiness.; Distribution qualification assets, test declarations and lookup wording: Readiness corrections folded in before approval: contract-binding check limited to inventory assets; declared assets described as bound by the report source hash; inventory refresh dropped (four digests already stale, 188 of 200 classified); threat-model wording limited to the Tensorwell lookup; build-and-verification text added; AC-1 and AC-2 controls made specific.

**Changes delivered:**

- **Distribution qualification assets, test declarations and lookup wording** (`20wq6-enh distribution-qualification-assets-and-test-declarations`) — 4 ACs completed. Key decisions: A separate distribution-owned list, not edits to the upstream inventory.; Declared assets stay out of the scope dictionary.
- **Make release verification and qualification provenance explicit** (`20qvs-enh release-provenance-verification`) — 5 ACs completed. Key decisions: Choose artifact provenance tied to source and explicit release qualification.; Narrow to the gate, provenance file and published checksums; defer signing.
## Watchpoints

- Watchpoint: whole-suite runs and profile qualifications run one at a time, never concurrently.
- Follow-up: report items K3, K4, G13 and G14 are out of scope; the operator plans them separately.
- Open the seed gate only for the two seed edits and close it immediately after.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer, security-reviewer, release-reviewer |
| DEL-2 | do_now | no | completed | qa-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- 2026-10-17: Readiness: six lanes and the red-team and docs-contract seats passed after one correction round; the red-team confirmation round caught an exception rule no profile run could satisfy, fixed before approval. Delivery: DEL-1 (an exception excused a runner or repository guard failure; the first repair missed the case with a coincident skip difference, caught by a fresh code reviewer) and DEL-2 (vacuous oversized control) repaired and reverified by fresh code and QA contexts; all six lanes and council-delivery approved. Shared contexts disclosed: code with architecture on the first pass, docs-contract with release. Qualification green on the final tree (default 11,890, second 11,882, declared 11,890; comparisons equal; the new gate accepts the real reports). Follow-ups: two pre-existing release-main rejection tests never reach preflight; the coverage inventory is stale (188 of 200 classified, four pins stale), so profile runs fall back to full; report items K3, K4, G13 and G14 and release signing remain for separate planning. Not a release: the operator cuts 1.32.0.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 20 | 511,117 |
| implement | 58 | 0 |
| review | 20 | 178,551 |
| **Total** | **98** | **689,668** |

<!-- wave:context-efficiency-state {"generation":98,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":58,"content_source_credit":1913,"derived_artifact_credit":0,"direct_net":-6476,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1976,"response_debit":11939,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5526},"plan":{"calls":20,"content_source_credit":570889,"derived_artifact_credit":3301,"direct_net":511117,"estimated_tokens_saved":511117,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3416,"response_debit":63925,"source_credit_count":37,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4268},"review":{"calls":20,"content_source_credit":232924,"derived_artifact_credit":2114,"direct_net":178551,"estimated_tokens_saved":178551,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8049,"response_debit":51492,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3054}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":98,"content_source_credit":805726,"derived_artifact_credit":5415,"direct_net":683192,"estimated_tokens_saved":689668,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13441,"response_debit":127356,"source_credit_count":70,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12848},"wave_id":"20wq7 distribution-release-follow-ups"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
