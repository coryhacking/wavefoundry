# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-19
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2134s distribution-vocabulary-portability`
Title: Distribution Vocabulary Portability

## Objective

Renamed distributions such as Waveforge resolve prompt shortcuts by their own names, run our lifecycle prompt tests green on their own vocabulary and template wording, and see their own tier nouns in skill descriptions, while Wavefoundry's own rendered output and test coverage stay unchanged.

## Changes

Change ID: `2134p-enh profile-shortcut-lookup`
Change Status: `implemented`

Change ID: `2134q-enh profile-portable-prompt-tests`
Change Status: `implemented`
Depends On: `2134r-enh profile-skill-description-nouns`

Change ID: `2134r-enh profile-skill-description-nouns`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-10-19

## Wave Summary

Wave `2134s` (Distribution Vocabulary Portability) delivered 3 changes: Resolve prompt shortcuts through the vocabulary profile, Make lifecycle prompt tests hold on any declared vocabulary, and Derive tier nouns in skill descriptions from the vocabulary profile. Notable adjustments during implementation: Resolve prompt shortcuts through the vocabulary profile: Implementation note (deviation from Requirement 1's wording, recorded here because the change doc is past readiness): with no `prompt_names` record the lookup uses the shipped slugs, as `vocabulary_profile.applied_prompt_slugs(None)` and the renderer read an absent record (prompts not yet migrated), not the profile's slug that Requirement 1 states; the profile's slug is used only for an invalid record (Requirement 5). Using the profile's slug for an absent record would send a renamed "Close wave" (the item close) to the unmigrated container-close file `close-wave.prompt.md`. Found by the 2134q implementer; docstring and comment corrected.; Resolve prompt shortcuts through the vocabulary profile: Delivery repair (code-reviewer): `test_malformed_manifest_resolves_through_the_profile` ran only under the default profile, so it could not tell the profile slug from the shipped one (mutant M2 survived). Added `test_malformed_manifest_uses_the_profile_slug_not_the_shipped_one` under a Set/Wave swap; M2 now fails. Red-team note applied: the docstring says a hand-edited record that disagrees with the files misroutes exactly as the renderer would.; Make lifecycle prompt tests hold on any declared vocabulary: Implemented (implementer subagent; coordinator reviewed). Census: candidate grep found mapped prompt paths in 21 test files, shortcut phrases in 8, template reads in 12; the authoritative census was the Set/Wave scratch run of 25 candidate files (about 110 failures), of which 13 files hold Requirement 1 assertions, all converted: test_render_agent_surfaces (+151/-85), test_setup_wavefoundry (+16/-14), test_reconcile_scan (+16/-12), test_review_policy (+15/-10), test_declared_extension_skills (+13/-6), test_compact_review_artifacts (+12/-2), test_memory_records (+11/-4), test_render_platform_surfaces (+10/-2), test_install_resume_integration (+6/-2), test_upgrade_wavefoundry (+5/-1), test_readiness_convergence (+2/-2), test_server_context_efficiency (+2/-2), test_server_tools_lifecycle (one test); new support module `tests/prompt_vocabulary_support.py`. Wording clauses use `{wave}`/`{change}`/`{doc[key]}`/`{shortcut[key]}` placeholders: seeds compared exactly with shipped nouns, templates and rendered prompts case-insensitively with `tier_noun` nouns. Narrowed under renamed profiles only, with inline reasons (Requirement 5): seed-to-template body byte equality in `BriefingLoopCarrierTests`, and containment of the implement-wave Completion section in this repository's rendered prompt; both still apply under shipped names and the clause checks run on every profile. Left literal: seed text, template asset file names, the untiered review-plan prompt, `DefaultNamePinTests`, `ProfileConsumerTests`, and no-record manifest fixtures. Outside Requirement 1 and not changed: test_docs_lint (about 60 failures on the Set/Wave tree, because the static `DOCS_LINT_FIXTURE` carries shipped prompt names and lint asks for migration) and test_wf_cli (a census of this repository's own live docs); a distribution suite run still sees those, recorded as a follow-up. AC-1: 13 scratch mutants (missing template or rendered clause, prompt at the wrong path) killed on both the default and the Set/Wave tree, unmutated controls pass (`scratchpad/2134q/mutants.py`). AC-2: `scratchpad/2134q/setup_setwave.py` (Set/Wave tier names, all 11 prompt overrides, migrated prompts, reworded templates and rendered prompts, marker regions untouched, a re-render writes nothing): the 13 changed files ran 2387 tests OK, 8 skips (4 shared with the default run, 4 existing `default_profile_only`). Existing gap noted, not changed: `LifecyclePromptTextTests._text` skips rather than fails when the file is missing.

**Changes delivered:**

- **Resolve prompt shortcuts through the vocabulary profile** (`2134p-enh profile-shortcut-lookup`) — 4 ACs completed. Key decisions: Resolve declared shortcuts first, then keep the existing fallbacks.
- **Make lifecycle prompt tests hold on any declared vocabulary** (`2134q-enh profile-portable-prompt-tests`) — 3 ACs completed. Key decisions: Derive names through the profile and compare wording against the shipped template.
- **Derive tier nouns in skill descriptions from the vocabulary profile** (`2134r-enh profile-skill-description-nouns`) — 4 ACs completed. Key decisions: Explicit helper calls per tier noun, with declared article constants.
## Watchpoints

- Watchpoint: implement `2134r` before `2134q`; `2134q`'s clause assertions use `2134r`'s tier-noun helpers.
- Watchpoint: reply to Waveforge with the declined asks and the reasons once the wave closes.

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
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 16 | 2,335 |
| implement | 55 | 0 |
| review | 9 | 37,196 |
| **Total** | **80** | **39,531** |

<!-- wave:context-efficiency-state {"generation":80,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":55,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-7527,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1699,"response_debit":9990,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4162},"plan":{"calls":16,"content_source_credit":17253,"derived_artifact_credit":1282,"direct_net":2335,"estimated_tokens_saved":2335,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2371,"response_debit":18257,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4428},"review":{"calls":9,"content_source_credit":52886,"derived_artifact_credit":1634,"direct_net":37196,"estimated_tokens_saved":37196,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2768,"response_debit":17770,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":80,"content_source_credit":70139,"derived_artifact_credit":2916,"direct_net":32004,"estimated_tokens_saved":39531,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6838,"response_debit":46017,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11804},"wave_id":"2134s distribution-vocabulary-portability"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
