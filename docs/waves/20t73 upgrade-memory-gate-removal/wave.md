# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-16
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20t73 upgrade-memory-gate-removal`
Title: Upgrade Memory Gate Removal

## Objective

Remove the historical-memory gate and its receipt-owned index publication from upgrade and setup, leaving one advisory report line and the on-demand `memory_backfill` and `memory_validate` path. Now, because the gate pauses upgrades unpredictably and since 1.29.0 tells agents to run an external hosts-stopped command that the MCP resume never needed.

## Changes

Change ID: `20smo-enh remove-upgrade-historical-memory-gate`
Change Status: `implemented`

## Participants

- Coordinator: planning session
- Write-owning roles: one implementer (runner, setup, memory core, handlers, seeds, docs)
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-16

## Wave Summary

Wave `20t73` (Upgrade Memory Gate Removal) delivered one change: Remove the historical-memory gate from upgrade and setup. Notable adjustments during implementation: Remove the historical-memory gate from upgrade and setup: Core implementation in progress: removed parent staging/memory authority from index-store finalize, added cross-run source/wave queries and full-key advisory compatibility responses. Single writer is now replacing runner/setup gates and checking lifecycle inventory reuse. No AC or qualification is claimed before focused execution.; Remove the historical-memory gate from upgrade and setup: Pre-edit old-code census: published latest release is v1.31.0 (GitHub non-draft, published2026-10-15). AST checks of local tags v1.24.0 through v1.31.0 all call the same eleven memory names: ACTION_REQUIRED_EXIT, MAX_CANDIDATES_PER_CALL, ensure_run, sync_inventory, reconcile_index_publication, run_summary, validation_worklist, run_state, index_publication_scope, complete_index_publication, mark_indexed. Protocol1 v1.22 fixture is the subset without run_state. Summary keys follow Req4; candidates_drafted is get-read, eligible_waves belongs to setup. Exact-token source census finds the parent-finalize environment variable set only in phase_index_update_parent_owned, never a production storage-migration path; other setters are tests, and setup_reconciliation only strips it. Gapfill: historical Git-tag AST inspection uses git show because current-file MCP reads do not address historical revisions.; Remove the historical-memory gate from upgrade and setup: Operator accepted the final source-grounded clarification and requested implementation. Owning Requirement2/Decision Log now promise one existing inventory pass with no extra report scan, not a fixed resource bound. Task6 now follows AC-3 newest-released-runner selection rather than stale1.32 wording. Focused readiness delta only; no new scope, timer, model, policy or full critique. Existing20st8 is closed and pushed7221d9a1, freeing its serialized files.

**Changes delivered:**

- **Remove the historical-memory gate from upgrade and setup** (`20smo-enh remove-upgrade-historical-memory-gate`) — 7 ACs completed. Key decisions: Remove the gate and receipt entirely; keep backfill on demand with a report line; Tie deletion of the compatibility layer and aliases to runner protocol 2 leaving `SUPPORTED_RUNNER_PROTOCOLS` or a proven runner handoff, not to one elapsed release
## Watchpoints

- Watchpoint, old-runner window: the carrying upgrade executes a supported older runner against the extracted modules; confirm its memory call list from source before editing `memory_backfill.py` (change task 1, AC-3).
- Seed edits run only under `seed_edit_allowed`; hand-reconcile project-authored install/upgrade prompts as required by the admitted change.
- Follow-up: mint a tech-debt change at close whose deletion precondition is the supported-runner/handoff boundary in Requirement4.
- Subagent model split for review seats: Fable or Opus for red-team, security, architecture, code and QA; Sonnet for docs-contract and release.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-LIVE-GUIDANCE | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
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

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 193 | 2,321,416 |
| implement | 294 | 4,726,639 |
| review | 417 | 3,515,259 |
| **Total** | **904** | **10,563,314** |

<!-- wave:context-efficiency-state {"generation":846,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":294,"content_source_credit":5320386,"derived_artifact_credit":1303,"direct_net":4726639,"estimated_tokens_saved":4726639,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16853,"response_debit":583549,"source_credit_count":141,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5352},"plan":{"calls":193,"content_source_credit":2726612,"derived_artifact_credit":8223,"direct_net":2321416,"estimated_tokens_saved":2321416,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":22770,"response_debit":403947,"source_credit_count":131,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13298},"review":{"calls":417,"content_source_credit":4677829,"derived_artifact_credit":1821,"direct_net":3515259,"estimated_tokens_saved":3515259,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":45548,"response_debit":1121897,"source_credit_count":300,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3054}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":904,"content_source_credit":12724827,"derived_artifact_credit":11347,"direct_net":10563314,"estimated_tokens_saved":10563314,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":85171,"response_debit":2109393,"source_credit_count":572,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":21704},"wave_id":"20t73 upgrade-memory-gate-removal"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 82 | 0 | 38 | 40,489,812 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":38,"estimated_exploration_avoided":40489812,"surfaced_events":82} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Final delivery: all six required lanes and council approved against unchanged65-path fingerprint f3c0d32c7a45bff0b6de5b88a6f65804372a2502191dcbd53decab210dfc777a after terminal cycle2 and derived convergence. Canonical default:11,853tests/200files/12existing skips/655.087s, exit0; receipt inputs_hash ca8454af981b232d8cc6b5b5ced16d60f6ecbcdf3a8e16b89aad527d6ba7aa51. No waiver or repeated qualification for bookkeeping. Operator approval and the explicitly close-time compatibility-debt task remain for operator-authorized closure.
- Durable evidence index under `.wavefoundry/framework/scripts/tests/`: `test_memory_backfill.py` covers advisory/manual errors, once-per-lifecycle and cross-run work; `test_old_parent_publication.py` covers archived-main/ordinary child publication; `fixtures/upgrade_old_runner/upgrade_runner_v1_31_0.py.txt` preserves the published old-runner input; `test_index_state_store.py` covers retired-variable authorization refusal and grant/CAS; `test_upgrade_wavefoundry.py`, `test_upgrade_recovery_guidance.py`, `test_sqlite_storage_migration.py` and `test_storage_upgrade_resume.py` cover ordinary upgrade and retained recovery. Guidance regressions are `test_setup_wavefoundry.py`, `test_compact_review_artifacts.py`, `test_vocabulary_prompt_names.py` and `test_review_policy.py`. Reproduce full qualification with `python3 .wavefoundry/framework/scripts/run_tests.py`; temporary probe scripts/logs are supplemental, not the only durable proof. Preserve the original/current source and immutable ledger; no repository evidence folder was added.
- Limits: real child grant/refusal composition was executed independently; expensive indexing/model payload, extraction/storage and guard-handoff fixture substitutions are disclosed. No native Windows or complete downstream installation qualification. Code/QA shared one original delivery context, architecture/release another; docs, security and chair were separate. Both guidance repair cycles had distinct fresh reviewers. Canonical qualification was coordinator-executed; lane and chair evidence does not claim they each ran it. Initial failing suite and the focused guard-rejected run remain historical failures, superseded by the settled-source green runs.

- Cycle 2 is terminal with a derived convergence checkpoint. Fresh code/QA passed 40 focused tests, no skips, and actual old-producer/deleted-clause controls; fresh docs/release independently passed both public render shapes and caught the old producer. Shared remits are disclosed; neither context implemented the repair. Chair confirmed the two-file guidance/oracle delta leaves runtime authority unchanged. The first focused run's assertions passed but a coordinator handoff edit tripped its guard; the clean two-file repeat exited 0. Final source remains the65-path f3c0d32c7a45bff0b6de5b88a6f65804372a2502191dcbd53decab210dfc777a packet. Only repaired-tree full qualification remains.

- 2026-10-16: First canonical default run completed 11,853 tests / 200 files / 12 existing skips / 785.784s, with three assertions failing in two files. Same-root cycle 2 repairs the canonical upgrade-policy text producer and stale compact-evidence oracle; no runtime authority changes. Self-hosted surface sync now writes nothing and lint passes. Fresh focused code/QA and docs/release reverification and repaired-tree canonical qualification remain pending. No failure waived. Final 65-path fingerprint f3c0d32c7a45bff0b6de5b88a6f65804372a2502191dcbd53decab210dfc777a.

- 2026-10-16: Delivery source review used an isolated standard red-team primer (adversarial, constructive and simplicity stances; live-guidance fidelity and old-runner publication composition questions), then separate fixed architecture, security, QA and reality contexts; rotating docs-contract ran after the fixed assessments and proposed plain option forwarding plus on-demand curation while retaining supported-window aliases. Code shared QA's context; release shared architecture's context. Every fixed seat explicitly weighed the rotating alternative. Chair first weighed anonymized outputs, then reattached identities. Initial agreement unanimous, maximum severity medium for false live guidance; no challenge round. Independent probes joined archived v1.31 main and incoming hooks to actual ordinary epoch publication/refusal, including real non-owner children and an unmocked archived phase; expensive index/model, storage/extraction and guard-handoff substitutions remain explicit. No native Windows or live-target qualification is claimed.
- Same-root finding DEL-LIVE-GUIDANCE stayed in one open repair cycle until all residual help, seed/prompt and architecture claims were corrected. Fresh code/QA cleared only setup help/forwarding with old-help and flag-stripping assertion controls; fresh docs/release withheld incomplete repairs, then passed the consolidated guidance against current hook/store behavior and known-bad prose restoration. All four affected lanes independently cleared; finding is terminal. Two obsolete descriptive nouns were subsequently removed inline, with whole-runner AST equality verified; no behavior changed. Final frozen source fingerprint:1b9f2369742840117c4ea98ab4db397b0a57e9d6d5e11d1479bea1d418e07080 across63 paths. Canonical qualification and final approvals follow; ordinary bookkeeping does not require repeated qualification.

- 2026-10-16: Operator accepted final inventory wording clarification and authorized implementation. Focused amendment only on receipt review-policy-c72c98dece4f011d6019: isolated standard red-team primer, separate fixed architecture/security/QA/reality contexts, rotating docs-contract, fresh chair synthesis of anonymized outputs. Code/QA shared remit context; architecture/release shared another; other seats separate. All six required readiness approvals and council current; successful Prepare then Implement. Unanimous/no blocker. Source-only reality/primer notes are not future runtime evidence. Available inherited models used; prior Opus/Sonnet identities were not asserted. Existing once-per-lifecycle requirement must be pinned across real archived main plus incoming hook. No full critique or new timer.
