# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-10-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20tpp tensorwell-workload-aware-client`
Title: Tensorwell Workload Aware Client

## Objective

Bring the Wavefoundry Tensorwell client up to the workload-aware and client-aware service contract Tensorwell is shipping now: negotiated capabilities, explicit interactive and batch workloads, per-request deadlines up to 300 s, a stable per-process session hint, distinct failure causes with bounded retry and concurrency, and capacity reporting. When this wave closes the client has been exercised against a deployed candidate service. No backward compatibility with the pre-capabilities service is kept, by operator decision.

## Changes

Change ID: `20tpq-enh tensorwell-capability-negotiation-and-request-contract`
Change Status: `implementing`

Change ID: `20tpr-enh tensorwell-failure-causes-backpressure-and-reporting`
Change Status: `implementing`
Depends On: `20tpq-enh tensorwell-capability-negotiation-and-request-contract`

## Participants

- Coordinator: Coordinator
- Write-owning roles: One implementer owns `tensorwell_client.py` across both changes; coordinator owns lifecycle records
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer, architecture-reviewer, performance-reviewer, docs-contract-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

## Wave Summary

Two changes: `20tpq` negotiates capabilities and sends workload, deadline, session and timing fields; `20tpr` classifies failure causes, bounds retries and concurrency, and reports capacity, then runs the live acceptance checklist against the deployed candidate.

## Watchpoints

- Watchpoint: the adaptive API is deployed locally. Its nested schema_version 2 capabilities, nested response timing and schema_version 3 stats are the contract for the revised plans; prior flat fixtures are provisional and must be replaced before live acceptance.
- Watchpoint: `20tpr` lands after `20tpq`; both edit `tensorwell_client.py` under one write owner. Workload is derived inside the adapters from the entry point; call sites and the `20qvt` extension adapter contract stay untouched.
- Follow-up: complete live acceptance before closure; the candidate is available, but the client contract reconciliation must land first. Keep the wave paused meanwhile and record results in the Live Acceptance section.
- Watchpoint: operator decision, no legacy service compatibility. Selection stays macOS arm64; Windows, Linux and WSL2 keep local inference.
- Watchpoint: session hint and credentials never enter logs, status or diagnostics.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 20tpp-delivery-deadline-validation | do_now | no | completed | qa-reviewer, code-reviewer, council-delivery |
| 20tpp-delivery-handler-digest | do_now | no | completed | qa-reviewer, release-reviewer |

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
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | withheld | repaired findings require fresh approval: 20tpp-delivery-deadline-validation, 20tpp-delivery-handler-digest | record a fresh independent approval for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 61 | 493,034 |
| implement | 224 | 1,078,312 |
| review | 460 | 4,291,950 |
| **Total** | **745** | **5,863,296** |

<!-- wave:context-efficiency-state {"generation":675,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":224,"content_source_credit":1408143,"derived_artifact_credit":0,"direct_net":1078312,"estimated_tokens_saved":1078312,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9798,"response_debit":331553,"source_credit_count":49,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11520},"plan":{"calls":61,"content_source_credit":612709,"derived_artifact_credit":5851,"direct_net":493034,"estimated_tokens_saved":493034,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":24056,"response_debit":108748,"source_credit_count":46,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7278},"review":{"calls":460,"content_source_credit":5408814,"derived_artifact_credit":1324,"direct_net":4291950,"estimated_tokens_saved":4291950,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":57545,"response_debit":1060643,"source_credit_count":311,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":745,"content_source_credit":7429666,"derived_artifact_credit":7175,"direct_net":5863296,"estimated_tokens_saved":5863296,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":91399,"response_debit":1500944,"source_credit_count":406,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":18798},"wave_id":"20tpp tensorwell-workload-aware-client"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 15 | 0 | 10 | 13,786,379 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":10,"estimated_exploration_avoided":13786379,"surfaced_events":15} -->
<!-- wave:exploration-avoided end -->
## Readiness outcome

2026-10-15: readied after one bounded repair round. Seats: isolated red-team (fixed), isolated security-reviewer (rotating), code and QA in one disclosed shared context, architecture and performance in one disclosed shared context, docs-contract and release in one disclosed shared context; council-chair synthesis. Round 1 found two blocking plan defects (a setup "call site" that never reaches the adapter; a mandatory caller `workload` keyword that would break the `20qvt` extension-adapter contract and its committed fixture) and about thirty medium and low wording gaps. Adopted alternatives: workload derived inside the adapters from the entry point (no call-site or contract edits) and one wall-clock operation deadline per adapter call instead of retry counters. Every seat re-verified in its original context and passed; four low residuals from re-verification were corrected before approval. Model allocation: all seats ran on the inherited Fable 5.1 model (observed runtime identity unknown); the operator confirmed the future split of Fable or Opus for red-team, security, architecture, code and QA and Sonnet for docs-contract and release. This approves plan feasibility and testability at commit `57f7cecc`, not implemented behaviour, Tensorwell's final field names or any live qualification.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Implementation opened from current typed readiness. One delegated implementer owns tensorwell_client.py and its client tests across both changes; coordinator owns facade, integration/reporting and documentation, then integration checks. Same inherited frontier model/effort selected for coupled protocol/deadline reasoning; actual worker runtime identity is not independently observed. No new readiness review. Live acceptance remains pending the deployed candidate. | wf_implement_wave create; approved execution graph |
| 2026-10-15 | Initial delivery QA and code independently proved the same pre-existing final-validation deadline gap through embed, embed_query and rerank. The typed initial-delivery finding is 20tpp-delivery-deadline-validation, blocking QA/code/council approval until repair. All 134 completed files in the interrupted canonical attempt had passed; that attempt was stopped deliberately (exit 143), is not qualification, and wrote no receipt. Its verified owned runner and descendants are gone. The remaining review seats continue read-only on the frozen source before one repair batch. | Deterministic on-time/late controls; historical HEAD confirmation; authoritative events.jsonl; /private/tmp/20tpp-full-suite.log |
| 2026-10-15 | Initial review round released with one required-AC finding. Typed repair_start cycle 1 recorded before reopening the framework gate. The implementer owns only the shared client guard and its existing regression file; all other reviewed source/docs remain unchanged. Original scenario and adjacent public entry points share one validation/acceptance path. Fresh QA/code verify the repair; no second full council or readiness round is warranted for an unchanged contract. | 20tpp-delivery-deadline-validation; events.jsonl; actual delivery chair synthesis |
| 2026-10-15 | Cycle-1 repair checks the deadline after vector/timing validation and before success accounting. Late validation reports deadline_exceeded / response_validation, retains the qualified pair and releases admission slots. New regression covers 18 deterministic entry/seam/boundary combinations; deleted/loosened guards cause 12/6 assertion failures, zero errors. Fresh separate QA/code contexts cleared the exact issue; code independently checked 27 cases including status-lock admission. Corrected canonical focused group passes 84 tests / 3 files / 0 skips in 13.074s. All other nine reviewed paths are unchanged; framework gate closed. The final canonical suite follows on this frozen tree, and full QA/council authority remains withheld for live acceptance. | Existing test_tensorwell_client.py regression; /private/tmp/20tpp-deadline-repair-cycle-1.json; /private/tmp/20tpp-repaired-focused.log; repaired aggregate 81330376a7eda42ed72fdfda5480885b6a71bd34a97efdcb685c3ffac291e3ad |
| 2026-10-16 | Second canonical attempt was stopped deliberately (exit 143) after the registry module exposed the obsolete wf_server_info description pin; it is not qualification and wrote no receipt. Fresh separate QA/release contexts confirmed exactly one mismatch among 90 handler digests and unchanged executable AST. Typed repair_start cycle 2 preceded updating only that supporting fixture entry. Registry module now passes 27 tests / 0 skips; every prior reviewed path is unchanged. Fresh focused QA/release verify the pin and description-mutation control before qualification resumes. | test_mcp_tool_registry.py HandlerDigestTests; events.jsonl; frozen 12-path aggregate 114a298125bac63a3fe7758a4906e5099a1becd6df6ac2abefa6528460e639b2 |
| 2026-10-16 | Final canonical default qualification passed 11,862 tests / 200 files / 12 existing skips in 740.812s. Green receipt matches current framework inputs, and all 12 reviewed paths remain unchanged. D1 and D2 are independently reverified and terminal; six implemented-scope approvals are recorded. AC-7 is complete in both changes. Wave paused with 20tpr AC-6/live task and full QA/council approval still pending the deliberately selected deployed candidate; no close/commit/push/package. | inputs_hash 5cec243a19aa224dc3934a6a0dc5ebe4f9bf73d79a8a00bc860935ccd0ada239; /private/tmp/20tpp-qualified-suite.log; events.jsonl |
| 2026-10-16 | Operator requested plan adjustment to use the deployed API. Updated existing 20tpq/20tpr instead of creating another wave: nested capabilities/session declaration, metadata.timing, model.load_count and nullable stats labels. Reopened only affected ACs/tasks; retained unrelated completed work and prior review/test history. Wave stays paused. Next is readiness/review of the changed contract before source edits, followed by implementation, affected-lane verification and live acceptance. No new approval, code edit or test qualification is claimed by this planning pass. | Local GETs all HTTP 200; actual client capabilities_unsupported; Tensorwell API/OpenAPI and response builders; revised admitted change docs |
| 2026-10-16 | Planning validation caught a section-boundary error in this wave edit. Restored authored coordination/history from the previously read record and unchanged change Progress Logs, and regenerated review/context projections using canonical renderers from their existing authoritative stores. The review ledger is byte-identical; no approval or finding was added by recovery. | Restored exact section boundaries; events.jsonl SHA-256 checked before/after |

| 2026-10-16 | Focused API-contract readiness approved on current receipt. Actual targeted council: isolated standard red-team primer and isolated rotating security; separate shared code/QA context; architecture/performance/docs/release shared chair context. All required lanes reviewed their changed remit. One bounded clarification made live/isolated verification explicit and dropped root-global policy labels. No remaining readiness blocker. Prepared/opened/implementing; client owner edits client/test only, coordinator owns integration/docs/lifecycle. Inherited model chosen for coupled protocol reasoning, actual runtime identity unobserved. | events.jsonl; /private/tmp/20tpp-api-readiness.json; review-policy-dfb1deaa01d9735b47f5 |

| 2026-10-16 | Revised API implementation passes producer-grounded controls: client 52/52 green, zero skips; nine guard mutants detected. Consumer/provider focus 37/37 green. Added healthy checkpoint-recovery leg after preserved failed epoch; integration 26/26 green with elapsed-backoff fixture and no local model factories. Real selected-candidate positives passed eight HTTP inference requests, nested timing/stats, prefix/session/privacy and batch-size comparison; results and limits are in wave.md Live Acceptance. Source frozen for fresh delivery review; full canonical suite follows once review settles. | Existing named client/integration tests; /private/tmp/20tpp-api-client-implementation.json; /private/tmp/20tpp-api-live-acceptance.json; /private/tmp/20tpp-api-recovery-integration.log; aggregate c5ed1347ca471a9076e8055bc7482c6e8baec6d13507aac7a3bd14e1cf77fde8 |

| 2026-10-16 | Revised API delivery complete: all required ACs/tasks verified, fresh focused review found no new actionable findings, all seven lane and council delivery approvals current. Canonical default passed 11,867 tests / 200 files / 12 existing skips in 756.863s; receipt matches current framework inputs and all twelve frozen hashes. Full docs validation passes. Wave paused for operator closure; no close/commit/push/package performed. API nominal checks are live; controlled faults/recovery are isolated as recorded. MCP reload succeeded, while setup assessment separately requests host restart; no setup/index rebuild was run. | inputs_hash 818020c3e26c974fbc93ff4c28c1b33645c808481522ac76ae98b8ad61f0479d; aggregate c5ed1347ca471a9076e8055bc7482c6e8baec6d13507aac7a3bd14e1cf77fde8; events.jsonl; /private/tmp/20tpp-api-canonical-suite.log |

## Review checkpoints

Readiness was consumed as approved without another plan-review round. Delivery used a full isolated red-team primer, then isolated fixed security, QA, architecture and reality-checker seats, followed by a distinct rotating performance seat. Code ran separately; docs-contract and release shared one disclosed context. Every seat received the primer. The inherited model was selected for protocol/trust reasoning; actual runtime identity was not independently observed.

The source stayed frozen through the initial round. All seven required lanes and all five council seats completed executable verification. An anonymized merit synthesis returned unanimous HOLD, maximum severity medium, for the sole finding 20tpp-delivery-deadline-validation; no challenge round was needed. QA and code independently reproduced late validation success at all three adapter entry points; a historical HEAD probe confirms the class predates this wave. Security, architecture, reality, performance and docs/release found no additional blocker.

The strongest alternative was an explicit operation record binding deadline, attempts and instance identity. The existing design already binds these values; a focused guard and regression repair is sufficient. The coordinator recorded initial delivery and repair_start cycle 1 before code edits. Fresh independent QA/code reverification is required for the repaired boundary; unaffected lane evidence is retained by reference. Final authority remains pending corrected-tree qualification, and the live acceptance AC/task remains unmet and unwaived. Subsequent test and review outcomes belong in Progress Log and typed evidence, without repeating this authored summary during qualification.

A subsequent canonical test run exposed fixture-maintenance finding 20tpp-delivery-handler-digest: the required registered description changed but its digest pin did not. Fresh QA/release confirmed one mismatch among 90 entries and unchanged executable AST. Cycle 2 changed only that fixture entry; fresh QA/release reverified the pin and mutation guard. Both recorded findings are terminal; the later planning revision requires review of the changed wire contract, not reuse of earlier fixture acceptance as live proof.

Focused revised-contract delivery review: actual targeted council roster was an isolated standard red-team primer followed by isolated rotating security; code/QA used one fresh shared independent context, and architecture/performance/docs/release used the fresh chair context. All required lanes inspected their changed remit. Independent security passed ten controls and detected the removed fixed-header guard; code/QA verified healthy recovery and detected a no-op third-build retry at the publication assertion; chair passed the registered no-HTTP/workload tests and producer-contract metamorphic controls. All twelve source/document hashes matched before and after. Primer questions about fixture fidelity and validated timing versus successful output were resolved without a new defect. No actionable findings remain in this round; final typed delivery approval awaits fresh canonical default qualification. Prior unrelated review is retained by reference. Actual model identities were not observed. No operator closure approval is inferred.

## Live Acceptance

2026-10-16 selected-candidate nominal checks passed through the current Wavefoundry client against the authenticated local adaptive service. HTTP instance SHA-256: `b5bebc3f0a1380b053464804d746b8872760e29ec23e09b40168453de3cd9e97` (full observed ID retained only in the local diagnostic packet). Instance identity remained pinned across responses; both advertised profile descriptors matched existing client pins. Capabilities schema_version 2 and stats schema_version 3/dedicated-adaptive were observed.

- Eight real inference HTTP requests succeeded: 258 synthetic embedding inputs and one 40-document rerank. Query embedding returned 384 finite components and exactly matched the document-role explicit-prefix control (maximum absolute difference 0), supporting the prefix-once contract for that input. Rerank produced 40 finite scores in the validated index order.
- The same 128 synthetic documents took four 32-item batch requests in 1.021s (125.35 items/s) and one 128-item request in 1.367s (93.62 items/s). Both returned all 128 valid vectors with 300000ms batch deadlines; interactive requests used 30000ms. This is one observational comparison under current host/service load, not a throughput guarantee or grounds for changing the planned 32-item bound.
- All inference requests used one stable UUID-shaped private session hint. Cached status exposed no hint, bearer token or synthetic query text. The probe process reported no local embedding or reranking model loaded. This does not establish other processes' memory state or evict earlier models elsewhere.
- Nested response timing normalized into existing per-role fields. Cached schema-3 stats preserved nested model.load_count as per-profile counts, omitted null optional labels, dropped root policy fields, and left the qualified pair intact. Both profiles reported one ready resident session at observation time.
- Installed controller metadata separately reported version 0.2.0, managed protocol 2, generation 000000000000000018df0a2160c0757800009728000000000000000000000000. Installed CLI SHA-256: da6fa9b7df8823ee8daa7aac1b1022128e31eb887d78adbd656f6a50f7276a22. These installed-file facts are not attestation of the running daemon; HTTP health exposes instance/status, not a build version.

Isolated controls remain distinct: client suite 52/52 passed with zero skips, covering schema/session rejection, 429/504/503/401/400 and transport distinctions, bounded retries/admission and local cancellation. The producer-shaped regression failed before the repair (3 named tests, 4 assertion failures, zero errors), then passed; nine selected guard mutants were assertion-detected. Consumer/provider focus passed 37 tests. The extended integration module passed 26 tests after adding a healthy retry that publishes changed vectors/meta after a refused partial batch, with the documented backoff modeled as elapsed and both local model factories forbidden. This is recovery in scratch storage, not a project-index rebuild. Independent delivery review will verify these boundaries before final approval.

Evidence: existing client tests (test_producer_nested_capabilities_normalize_schema_one_and_two, test_producer_schema_session_headers_stable_across_retry_and_roles, test_producer_nested_timing_normalizes_without_flat_wire_alias, test_producer_stats_nested_counts_and_nullable_labels, test_retry_table_attempt_caps_and_deadlines, test_transport_same_instance_only_one_rediscovery_and_cancelled); existing integration tests (test_registered_capacity_and_timing_snapshot_is_allowlisted_and_no_http, test_failed_incremental_build_preserves_published_vectors_and_file_meta). Temporary packets: /private/tmp/20tpp-api-live-acceptance.json, /private/tmp/20tpp-api-client-implementation.json and /private/tmp/20tpp-api-recovery-integration.log. No evidence folder was added to the repository.

Limits: no shared-daemon fault, credential rotation, shutdown, model download, remote-cancellation guarantee, physical-GPU attestation or native Windows/Linux/WSL2 qualification. MCP implementation reload succeeded with runner/implementation matching disk; the setup assessment still reports loaded_code_stale/setup_inputs_changed and recommends a host restart. No setup, rebuild or host restart was run. Fresh-process API qualification is separate from that assessment. Final canonical qualification passed and all seven lane/council delivery approvals are recorded in the latest Progress Log; operator closure remains pending.
