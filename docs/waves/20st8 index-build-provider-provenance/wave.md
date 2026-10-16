# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-16
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20st8 index-build-provider-provenance`
Title: Index Build Provider Provenance

## Objective

Make index builds report the embedding provider and accepted work from their own child processes, and avoid local model probes when qualified service inference covers the workload. Operators should be able to distinguish service availability, selection, execution and successful publication without daemon-global counter comparisons or unnecessary local model construction.

## Changes

Change ID: `20st9-bug skip-local-probes-for-service-indexing`
Change Status: `complete`

Change ID: `20tt3-enh index-build-execution-reporting`
Change Status: `complete`
Depends On: `20st9-bug skip-local-probes-for-service-indexing`

## Participants

- Coordinator: Coordinator
- Write-owning roles: implementer after successful Prepare
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-10-16

## Wave Summary

Delivered workload-aware setup that skips unused local embedding probes for service-covered models, plus child-owned provider/input/logical-request summaries in existing build logs and status. Standalone background passes establish their own scope rather than inheriting prior MCP job statistics. Explicit provider policy, model/precision identity, 32-item batching and publication authority are unchanged.

Both changes are complete: 20st9 satisfies four ACs and 20tt3 satisfies five. All tasks are complete with no intentional deferrals. Six delivery approvals and operator signoff are current; all four repair findings are independently reverified. Final canonical qualification passed 11,892 tests across 200 files with 12 existing skips and wrote a matching green receipt. Closed on 2026-10-16.

Useful outcomes and verification are consolidated here. Only the two change docs and authoritative ledger accompany this record; no repository evidence folder or new memory file was needed. The future-action rules are already captured in the updated architecture/spec and existing server playbooks. Timing investigation and separate release-profile qualification remain outside this wave.

## Watchpoints

- Preserve framework-level provider selection, local fallback, model/precision compatibility, publication and recovery authority. A local probe failure for uncovered work must not itself disable covered service work.
- Existing 32-item batching and 128-item negotiated ceiling remain unchanged. Field totals corroborate routing; they do not establish inefficiency or exactly-once execution.
- Counts belong to the child attempt/layer, not the MCP lifetime or daemon totals. Shared adapters, no-op builds, invalid output, failures and legacy logs need truthful attribution.
- Reuse existing last-build storage; no per-chunk telemetry, new evidence folders, extra status probes, model downloads or upgrade scans. Keep useful final verification in this record.
- Perform one canonical qualification after both changes settle; reuse it for unchanged review bookkeeping. Official-release compatibility qualification remains a separate gate; wave 20st7 and its failed/incomplete reports are not waived by this plan. Timing investigation stays deferred.
- Preserve uncommitted local-build VERSION/manifest stamps, the existing handoff and other wave records. Wave 20tpp remains paused awaiting operator closure.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-BACKGROUND-CONTENT | do_now | no | completed | code-reviewer, qa-reviewer |
| DEL-OBSERVATION-SCOPE | do_now | no | completed | code-reviewer, qa-reviewer |
| DEL-PACKAGE-IMPORT | do_now | no | completed | code-reviewer, qa-reviewer |
| DEL-TEST-MODULE-IDENTITY | do_now | no | completed | code-reviewer, qa-reviewer |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependency. Implement 20st9 before 20tt3 because both touch selection/reporting boundaries and shared tests. Neither requires closing or reopening 20tpp.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 115 | 971,906 |
| implement | 147 | 3,470,409 |
| review | 241 | 4,662,492 |
| **Total** | **503** | **9,104,807** |

<!-- wave:context-efficiency-state {"generation":457,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":147,"content_source_credit":3695738,"derived_artifact_credit":0,"direct_net":3470409,"estimated_tokens_saved":3470409,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5181,"response_debit":224238,"source_credit_count":64,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4090},"plan":{"calls":115,"content_source_credit":1180818,"derived_artifact_credit":4223,"direct_net":971906,"estimated_tokens_saved":971906,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8911,"response_debit":208492,"source_credit_count":43,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4268},"review":{"calls":241,"content_source_credit":5350675,"derived_artifact_credit":3324,"direct_net":4662492,"estimated_tokens_saved":4662492,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":37815,"response_debit":656759,"source_credit_count":114,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3067}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":503,"content_source_credit":10227231,"derived_artifact_credit":7547,"direct_net":9104807,"estimated_tokens_saved":9104807,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":51907,"response_debit":1089489,"source_credit_count":221,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11425},"wave_id":"20st8 index-build-provider-provenance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 37 | 0 | 19 | 24,207,821 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":19,"estimated_exploration_avoided":24207821,"surfaced_events":37} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- 2026-10-16: Focused cycle2 review cleared DEL-BACKGROUND-CONTENT in fresh independent context 20st8-background-repair-2-independent-code-qa-20261016 (shared code/QA, separate from root implementer). Actual public status controls and two independent mutants passed; three reviewed path hashes match. Affected approvals restored after reverification; no broader council or repeat of unchanged lanes. Current canonical qualification remains pending and no green receipt or operator closure approval is claimed.

- 2026-10-16: Delivery approved by code/QA in one independent context and architecture/security/docs-contract/performance in a second independent shared context; both were separate from implementers. All three cycle-1 findings are independently reverified and terminal. Focused actual-child, consumer and repair checks plus known-bad mutations support all required ACs. No delivery council is required by this receipt. Final independent hash checks matched all 15 paths. All 200 canonical test files passed; only concurrent 20t73 planning-record changes failed the repository guard, so reviewers approved engineering delivery without claiming formal qualification or authorizing closure. Native daemon/device performance and existing whole-log reader bounds remain unqualified. Runtime model identities unknown.

- 2026-10-16: Readiness approved on review-policy-7554fda61d41a64cdb7d. Standard isolated red-team primer first; architecture/security/QA/reality fixed seats and rotating docs-contract, then chair synthesis. Code/performance judgments shared the independent chair context; other lane contexts were separate. Architecture/QA/chair executed bounded source/parser controls; static seats did not claim runtime tests. No blocker or plan repair; added performance lane changed allocation only. Runtime model identities unknown. Current inherited model/effort chosen for cross-process policy and provenance reasoning; no alternate runtime identity asserted. Successful second Prepare readied the wave, then Implement activated it.
- 2026-10-16: Planning/admission only. No readiness, delivery or operator closure approval is asserted. Normal Prepare and recorded council-readiness must precede code edits.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-16 | Final settled-tree canonical run passed11,892 tests across200 files with12 existing skips in730.325s, exit0. Green receipt inputs_hash e15f413d49512c757729966b83227cd84b8c9075976c900addb3e77a84d81f59 matches current framework source. All ACs/tasks and change statuses reconciled; operator authorized closure, commit and push. No further source edit, repeated review, timing waiver or extra evidence folder. | /private/tmp/20st8-close-canonical-suite.log; automatic framework test receipt. |
| 2026-10-16 | Operator authorized closure, commit and push after independent review. Retrospective: distinguish available/selected providers from accepted child execution, and bind persisted metadata only to its owning job; these rules now live in embedding/pipeline architecture, MCP spec and regression tests. Existing server playbooks cover paired-consumer and exact-state checks. memory_propose dry-run offered one generic repaired-finding draft anchored only to the test file; it adds no actionable knowledge beyond these canonical sources, so no source was selected and no new memory file was created. Cleanup: only wave.md, two admitted change docs and authoritative events.jsonl are retained; unique proof remains in cited temporary artifacts, with durable outcomes consolidated here. No deferred ACs or disposable repository evidence folders. | memory_propose dry_run records_proposed1/records_written0; six approvals and terminal finding chains; close authorization in current request. |
| 2026-10-16 | Cycle2 DEL-BACKGROUND-CONTENT is independently reverified and terminal. Code/QA ran all13 reporting tests without errors/skips and independently detected both restored standalone binding and removed MCP completeness binding. All3 focused hashes matched; affected delivery approvals restored and automatic convergence checkpoint recorded. Other four approvals remain current. Paused with edit gate closed; quiet-window coordination is pending before the canonical run. No operator signoff, close, commit or receipt waiver. | Existing test_server_tools.IndexEmbeddingExecutionTests; /private/tmp/20st8-background-repair-2-independent-code-qa.log; typed cycle2 evidence. |
| 2026-10-16 | External independent review found a valid standalone code background pass misclassified against persisted all-job stats. Root reproduced the exact stale102/current12 counterexample, recorded DEL-BACKGROUND-CONTENT and cycle2 repair_start, then repaired only the parser and existing server-tools regressions.13 targeted tests and3 known-bad controls pass. Fresh code/QA review is running; formal canonical receipt remains pending a quiet checkout. | test_server_tools.IndexEmbeddingExecutionTests; typed finding; /private/tmp/20st8-background-repair-packet.json. |
| 2026-10-16 | Final repaired canonical execution passed all 11,889 tests across 200 files with 12 existing skips in 768.837s. Runner exited 1 solely because three concurrent planning paths under wave 20t73 changed; no current green receipt was written. Both independent review contexts confirmed all 15 hashes unchanged and approved all six delivery lanes. Full docs validation passed. Formal qualification task stays open; no failure waiver, manual receipt or third suite. | /private/tmp/20st8-canonical-repaired-suite.log; existing test files and typed approvals. |
| 2026-10-16 | Paused after implementation/review and closed the framework edit gate. ACs are verified; the remaining task is a valid canonical qualification receipt after concurrent material edits settle. Operator closure, commit, push and build are not authorized here. Gapfill: final documentation bookkeeping was a bulk mechanical edit of known wave/handoff sections, without source investigation or code edits. | Wave status paused; six typed delivery approvals; framework_edit_allowed false. |
| 2026-10-16 | Independent cycle1 verification cleared all three findings in code and QA:14 targeted tests passed with zero skips/errors. Architecture/security/docs/performance confirmed the narrow repair effects with two targeted tests and an unscoped-validation mutant. Actual-build validation, provider counts and publication semantics remain intact. All15 repaired fingerprints match; a pipeline date refresh was metadata-only. Final approvals remain conditional on the running corrected qualification. | Existing tests; /private/tmp/20st8-repair-1-independent-code-qa.log and /private/tmp/20st8-contracts-repair-1.json. |
| 2026-10-16 | First canonical qualification completed 11,889 tests/200 files/12 skips in 757.755s, red on three wave-owned issues: new test import convention, new validation affecting an unobserved helper fixture, and a new fixture's shared-module identity side effect. The concurrent planning wave20t73 also changed during the run. No failure or guard was waived and no green receipt was written. | /private/tmp/20st8-canonical-suite.log; DEL-PACKAGE-IMPORT, DEL-OBSERVATION-SCOPE and DEL-TEST-MODULE-IDENTITY. |
| 2026-10-16 | Recorded repair_start for all three findings before one bounded repair pass. Canonical test import spelling restored, validation remains at observed build acceptance only, and the integration fixture executes the actual pure parser without reloading unrelated modules. All22 focused repair/adjacent tests passed; five indexer mutants reverified. No requirement/priority/authority change or new readiness cycle. Second canonical qualification runs only because these code/test verification inputs changed, not because ledger/progress was recorded. | /private/tmp/20st8-repair-1-focused.log; updated /private/tmp/20st8-delivery-packet.json. |
| 2026-10-16 | Reporting implementation and documentation settled before canonical qualification. New indexer7/status10 checks passed; current-source output reaches the actual parser and real controlled child launch reaches build status. Five indexer mutants and four consumer mutants are detected. Independent code/QA and architecture/security/docs/performance contexts found no blocker; final approvals await the matching canonical receipt. No native Tensorwell/device qualification is claimed. | /private/tmp/20st8-delivery-packet.json; /private/tmp/20tt3-indexer-mutations.json; /private/tmp/20tt3-server-mutations.json; existing source tests. |
| 2026-10-16 | 20st9 selection repair is implemented: main skips unused local probes, mixed work probes an uncovered model and automatic CPU selection no longer disables covered service work. Focused integration31/setup203/client52/provider11 tests passed. The new main-path test failed pre-fix, and restoring the automatic-CPU veto was detected by the mixed-work regression. No native model, download or project-index mutation. | Existing tests and /private/tmp/20st9-{before,policy-mutant,integration,setup-host,client-host,provider}.log. |
| 2026-10-16 | Planned both agreed follow-ups in one wave; evaluated alternatives before drafting and recorded selections in each change's Decision Log. | Admitted 20st9 and 20tt3. |
| 2026-10-16 | Full documentation validation passed with no errors or warnings. Framework source is unchanged; no framework suite was repeated for planning. | `wf_validate_docs`: passed, docs-lint ok. |
| 2026-10-16 | Current-source checks identify setup's unconditional local-provider probe, inherited CPU policy effects, silent successful service selection in the indexer, and existing log/stat storage suitable for additive reporting. | `setup_index.main`, `report_embedding_provider_decision`, `tensorwell_client._policy_reason`, `indexer._get_embedder_inner`, `server_impl._parse_finished_build_stats_from_log`. |
| 2026-10-16 | Prior bounded probes used simulated service/probe boundaries: actual service embedding could succeed without indexer provider output; a failed local CoreML probe could disqualify previously qualified service selection. No native model or project-index mutation was performed. | Temporary diagnostic: /private/tmp/tensorwell-indexer-provenance-diagnostic.json. Durable mechanism and limitations are captured in the change docs. |
