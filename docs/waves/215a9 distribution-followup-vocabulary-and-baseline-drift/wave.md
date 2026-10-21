# Wave Record

Owner: Engineering
Status: implementing
Last verified: 2026-10-20
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `215a9 distribution-followup-vocabulary-and-baseline-drift`
Title: Distribution Followup Vocabulary And Baseline Drift

## Objective

Distributions receive profile-aware bridge/scaffold wording and explicit operator-instruction gates on close-change and package skills. Upgrades report lifecycle and plan-template differences using pre-extraction evidence that survives resume, while preserving project-owned destination files. No new tool-name mapping, host-specific controls, closure-status gate or automatic template refresh is introduced.

## Changes

Change ID: `21511-enh profile-vocabulary-and-operator-gate-text`
Change Status: `implemented`

Change ID: `21512-enh lifecycle-baseline-drift-report`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (Codex primary)
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

## Wave Summary

Both changes are implemented with every AC/task checked. Six specialist lanes and delivery council approved after three integration findings were repaired and independently reverified. Final canonical suite passed 12,005 tests across 203 files (12 existing skips); edit gates are closed. Wave remains open for operator review and closure.

## Watchpoints

- Watchpoint: serialize writes to render_agent_surfaces.py; integrate both changes before final qualification.
- Upgrade findings are advisory and persisted before extraction; resume must not infer previous evidence from replaced templates.
- The older framework template is not necessarily the template that produced the local document.
- Current index freshness is ready; setup separately reports setup_inputs_changed. No setup repair is included.
- Neither change closes a wave, commits code or publishes a release.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 215a9-baseline-checkpoint-fixture-prerequisite | do_now | no | completed | code-reviewer, qa-reviewer, release-reviewer, council-delivery |
| 215a9-rejected-pack-mutates-baseline-checkpoint | do_now | no | completed | code-reviewer, qa-reviewer, security-reviewer, release-reviewer, council-delivery |
| 215a9-timed-call-census-owner-stale | do_now | no | completed | code-reviewer, qa-reviewer, council-delivery |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
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
| operator-signoff | withheld | repaired findings require fresh approval: 215a9-baseline-checkpoint-fixture-prerequisite, 215a9-rejected-pack-mutates-baseline-checkpoint, 215a9-timed-call-census-owner-stale | record a fresh independent approval for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- Delivery complete: full red-team primer followed isolated architecture, security, QA and reality seats, rotating docs-contract, and one disclosed shared code/release context. First synthesis was anonymized; red-team closing held the candidate set. Required verification then found three bounded integration defects: checkpoint prerequisite missing from isolated fixtures, capture before retained-pack refusal, and stale timed-call census owner. Cycle 1 repaired all three. A fresh independent focused context reverified QA clearance and affected code/security/release/council approvals; architecture and docs-contract authority was retained with explicit unchanged-boundary validation. No full-council trigger changed. No unresolved disagreement or blocker remains.
- Final verification: `env -u PYTHONPYCACHEPREFIX python3 .wavefoundry/framework/scripts/run_tests.py` passed 12,005 tests / 203 files / 12 existing skips in 714.645 seconds. The earlier failed run is retained as diagnostic history; no skip, threshold or assertion was weakened. Detailed final log: `/private/tmp/215a9-framework-tests-repaired.log`. No native Windows, archived-runner end-to-end, downstream installation or release qualification is claimed.
- Durable evidence anchors: `.wavefoundry/framework/scripts/tests/test_lifecycle_baseline_drift.py` (`BaselineDriftTests`); `tests/test_index_upgrade_guard.py` (`IndexUpgradeGuardTests.test_changed_archive_never_executes_incoming_identity_helper`); `tests/test_archive_ownership_portability.py` (`IncomingManifestMetadataTests`); `tests/test_upgrade_wavefoundry.py` (`RootBootstrapUpgradeTests`); `tests/test_tree_kill_routing.py` (`ClassificationTests`); `tests/test_vocabulary_tier_nouns.py` (`SkillProseTests`); `tests/test_server_tools_lifecycle.py` (`WaveCreateScaffoldAlignmentTests`); `tests/test_render_agent_surfaces.py` (`SkillRegistryTests`). All abbreviated test paths are relative to `.wavefoundry/framework/scripts/`. These repository test sources and this wave's typed ledger preserve the verification contract when temporary probe logs expire.
- Report compatibility: older installed-runner dry runs expose text findings; new-runner dry runs and real delegated/cleanup summaries expose the structured field. Documentation states this boundary explicitly.

- Focused readiness recheck approved naming `upgrade_lib.py` as the existing checkpoint carrier under unchanged Requirements 6/7; all six lanes and council approved receipt `review-policy-b51e39b4d54362c2998e` before its edit. Same target version and pack digest must bind replay, including empty captures. No new delivery claim was made.

- Readiness passed against receipt review-policy-41834d0717da84eb79d5. Full isolated red-team primer, independent architecture/security/QA/reality fixed seats, rotating docs-contract best-alternative seat, and code/release in one disclosed shared independent context found no blockers. Independent controls covered omitted scaffold/preview census, contained reads, current skill defects, and invalid approval actor. Strongest counterargument: old installed runner lacks the report; existing incoming preview/pre-extract hooks make first-adoption output feasible. Preserve captured facts through summary/resume/cleanup; no delivery behavior is yet attested. Detailed temporary synthesis: /private/tmp/215a9-review/synthesis.json.

- Operator acknowledged Product Intent and authorized prepare, review and implementation of both changes in this wave on 2026-10-20.
- Readiness primer tier: full, because cross-process upgrade state, template reads and shared renderer contracts are in scope. Council fixed seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating seat: docs-contract-reviewer; code-reviewer separately required.
- Work allocation: use fresh independent review contexts and a bounded implementation worker for upgrade state; coordinator owns integration and wording change. Requested gpt-6.1-sol/high for bounded review and implementation, with higher-effort judgment available if uncertainty warrants it; actual runtime identity is unobserved. Reviewers do not edit source or ledger; coordinator records their supplied evidence.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 285 | 3,366,993 |
| implement | 165 | 1,398,734 |
| review | 119 | 1,481,485 |
| **Total** | **569** | **6,247,212** |

<!-- wave:context-efficiency-state {"generation":397,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":165,"content_source_credit":1798737,"derived_artifact_credit":1884,"direct_net":1398734,"estimated_tokens_saved":1398734,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14887,"response_debit":391622,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4622},"plan":{"calls":285,"content_source_credit":4075306,"derived_artifact_credit":4235,"direct_net":3366993,"estimated_tokens_saved":3366993,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16105,"response_debit":703981,"source_credit_count":122,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7538},"review":{"calls":119,"content_source_credit":1790737,"derived_artifact_credit":1160,"direct_net":1481485,"estimated_tokens_saved":1481485,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":37150,"response_debit":273262,"source_credit_count":72,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":569,"content_source_credit":7664780,"derived_artifact_credit":7279,"direct_net":6247212,"estimated_tokens_saved":6247212,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":68142,"response_debit":1368865,"source_credit_count":250,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12160},"wave_id":"215a9 distribution-followup-vocabulary-and-baseline-drift"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 34 | 0 | 20 | 20,073,338 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":20,"estimated_exploration_avoided":20073338,"surfaced_events":34} -->
<!-- wave:exploration-avoided end -->
