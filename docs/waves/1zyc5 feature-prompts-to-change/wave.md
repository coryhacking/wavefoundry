# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zyc5 feature-prompts-to-change`
Title: Feature Prompts To Change

## Objective

Remove "feature" and "finalize" from the lifecycle vocabulary: Plan feature and Implement feature become Plan change and Implement change, Finalize feature is retired in favor of a Close change prompt backed by `wf_close_change` (Close wave stays the only wave close), with no aliases and an upgrade migration for existing targets. In Waveforge a feature sits above a wave set, so the old names conflict.

## Changes

Change ID: `1zyc4-enh rename-feature-prompts-to-change`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-06

## Wave Summary

Wave `1zyc5` (Feature Prompts To Change) delivered one change: Rename the Feature Lifecycle Prompts to Change and Replace Finalize Feature with Close Change. Notable adjustments during implementation: Rename the Feature Lifecycle Prompts to Change and Replace Finalize Feature with Close Change: Seeds renamed with `git mv`; `wf render-surfaces` run in this repo moved the four prompts byte-for-byte, rewrote the manifest (Finalize entry replaced by Close change), removed `wf-plan-feature` in three hosts, rendered `wf-plan-change` and `wf-close-change`, materialized `close-change.prompt.md`; a second render wrote nothing (scratch). Guru description hand-edited.; Rename the Feature Lifecycle Prompts to Change and Replace Finalize Feature with Close Change: Census A to E rerun: matches only in `model_swap_v2_result.json` (3), `reconcile_scan.py` (15, retired-name table), `render_agent_surfaces.py` (10, STALE_SKILL_PATHS and migration pairs), tests of those (`test_reconcile_scan` 38, `test_render_agent_surfaces` 23, `test_docs_lint` 10, `test_upgrade_wavefoundry` 8, `test_declared_extension_skills` 2, `test_server_tools_lifecycle` 2), seed 160 (1, the seed-only sentence), `CHANGELOG.md` (3: the 1zli8 line and this entry), the two out-of-scope plans (1 and 5). Row G returns 0 lines. Row F (non-Python) returns only the kept technical uses listed in Requirement 8 plus the seed 160 seed-only line.; Rename the Feature Lifecycle Prompts to Change and Replace Finalize Feature with Close Change: Tests added: scan (`RetiredFeaturePromptNameTests`, 6), render (`ChangePromptRenameMigrationTests` 7, `ChangePromptSkillAndContractTests` 3), lookup (`ChangePromptLookupTests` 2), help goal, declared retired skill, docs-lint AC-8, upgrade-path AC-15. Handler digests: only `seed_get`, `wf_get_prompt`, `wf_help` changed and were updated. `wf_validate_docs` passed (one advisory warning on AC-13 wording).

**Changes delivered:**

- **Rename the Feature Lifecycle Prompts to Change and Replace Finalize Feature with Close Change** (`1zyc4-enh rename-feature-prompts-to-change`) — 19 ACs completed. Key decisions: Implementation-time amendment: treat `model_swap_docs_queries.json` as historical (not edited) and update the five `1us4q` plan references in this change.; No legacy aliases for the old phrases, files, skill or help goal (operator decision).
## Watchpoints

- Seed edits need `seed_edit_allowed`; script and template edits need `framework_edit_allowed`.
- No retired token may remain in any `docs/prompts/**/*.md` file (prompt lookup content fallback).
- Follow-up, out of scope: the remaining feature-named docs (seed 001, `feature-workflow.md`, `feature-wave-lifecycle-overview.md`).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | pending | — |
| DEL-2 | do_now | no | pending | — |
| DEL-3 | do_now | no | pending | — |
| DEL-4 | do_now | no | pending | — |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
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
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 17 | 48,881 |
| implement | 10 | 0 |
| review | 20 | 127,140 |
| **Total** | **47** | **176,021** |

<!-- wave:context-efficiency-state {"generation":45,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":10,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-11833,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":119,"response_debit":12024,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":310},"plan":{"calls":17,"content_source_credit":68803,"derived_artifact_credit":2522,"direct_net":48881,"estimated_tokens_saved":48881,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1833,"response_debit":24420,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":20,"content_source_credit":158385,"derived_artifact_credit":2841,"direct_net":127140,"estimated_tokens_saved":127140,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5301,"response_debit":31174,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2389}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":47,"content_source_credit":227188,"derived_artifact_credit":5363,"direct_net":164188,"estimated_tokens_saved":176021,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7253,"response_debit":67618,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6508},"wave_id":"1zyc5 feature-prompts-to-change"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
