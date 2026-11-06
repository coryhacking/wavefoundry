# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22nu3 reported-caller-recovery-corrections`
Title: Reported Caller Recovery Corrections

## Objective

Downstream maintainers can drop the reported SQLite snapshot patch, and operators receive setup recovery commands for the repository they selected. Verify the exact affected callers while preserving runtime SQLite policy, failure semantics and operator control.

## Changes

Change ID: `22nu2-bug reported-caller-sqlite-and-setup-recovery`
Change Status: `implemented`

## Participants

- Coordinator: root
- Write-owning roles: coordinator implementation after readiness
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-11-05

## Wave Summary

Closed after delivering the exact SQLite snapshot consumer repair, selected-root model failure guidance and the identified MCP recovery commands. All three ACs and all tasks are complete; no admitted work is deferred. All required specialist and Council approvals are current, and the operator authorized closure. The matching green framework receipt covers 12,374 tests with 12 skips. Unique proof is retained in delivery-evidence.json and events.jsonl; owned disposable work was removed by the close tool. Native Windows and downstream patch removal remain unqualified.

Intent outcome: achieved for the named consumers. The original snapshot caller preserves every original entry/byte and committed WAL rows across five states and two databases; ordinary/prewarm-only setup preserves the selected target in failure guidance; identified MCP consumers preserve correctly quoted commands, failure semantics and pending-install continuation. Independent QA confirmed all three ACs and the change/wave intent, and all twelve semantic bad variants were assertion-detected. The frozen-tree canonical suite passes 12,374 tests/217 files/12 skips in 544.962s with a matching green receipt. Native Windows execution and downstream patch removal are not established.

**Changes delivered:**

- **Finish the reported SQLite and setup recovery fixes** (`22nu2-bug reported-caller-sqlite-and-setup-recovery`) — 3 ACs completed. Key decisions: Repair the named callers using isolated test copies and the existing launcher owner.
## Watchpoints

- Watchpoint: test the original callers, not only new helpers. Preserve committed WAL rows and original directory bytes.
- Carry explicit roots across both ordinary and prewarm-only setup and preserve pending-install messaging.
- Native Windows remains unqualified. Do not alter or commit the unrelated :memory:.ses artifact. No close, commit, push or package authority in this request.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| model-oracle-platform-format | do_now | no | completed | qa-reviewer, code-reviewer |

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
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-05: Closure reconciliation: the delivered scope triggers the same code, QA, architecture and docs-contract lanes selected at readiness; all typed approvals and Council verdicts are current, with no unresolved finding or deferred checkbox. Retrospective: invoke the exact reported consumer and preserve independent path/byte oracles; keep standalone evidence files frozen during qualification. These lessons are encoded in the consumer regressions and existing qualification discipline, so no duplicate memory was created. memory_propose dry-run produced no eligible candidates and wrote nothing. Unique controls, original-oracle source and all reviewer conclusions are retained in delivery-evidence.json before owned disposable-work cleanup; events.jsonl remains approval authority. The operator explicitly authorized close, commit and push; the unrelated :memory:.ses remains excluded.

2026-11-05: Delivery Council PASS, standard primer, unanimous with no unresolved finding; intent_fit establishes across 22nu2 and the Objective. Fixed architecture/code (/root/nu3_codearch, shared context), QA (/root/nu3_delivery_qa), security (/root/nu3_delivery_security) and reality (/root/nu3_delivery_reality) weighed the rotating docs-contract alternative (/root/nu3_delivery_docs). Independent chair (/root/nu3_chair) saved anonymous merit weighting before identity reveal and directly confirmed the final green receipt. No challenge round or waiver. Prior-readiness context reuse, shared mutation harness and primer chronology are disclosed in delivery-evidence.json. Model guidance preserves the explicit input-root selection through its absolute launcher; MCP messages additionally emit --root. Conditional immutable reads and low-level process-info root ownership were considered; current quiescent copies/response owner remain simpler. All required typed delivery approvals are current; operator signoff is pending.

2026-11-05: Intent outcome: achieved for the named consumers. The original snapshot caller preserves every original entry/byte and committed WAL rows across five states and two databases; ordinary/prewarm-only setup preserves the selected target in failure guidance; identified MCP consumers preserve correctly quoted commands, failure semantics and pending-install continuation. Independent QA confirmed all three ACs and the change/wave intent, and all twelve semantic bad variants were assertion-detected. The frozen-tree canonical suite passes 12,374 tests/217 files/12 skips in 544.962s with a matching green receipt. Native Windows execution and downstream patch removal are not established.

2026-11-05: Readiness Council PASS at standard primer depth, all required lanes current on receipt 0f7d72c7308d38425eae. Fixed architecture/code (shared context), QA, security and isolated reality weighed the rotating docs alternative; independent chair weighed anonymous merits before restoring identities. Unanimous, maximum severity none, intent_fit establishes. No readiness repair or challenge round.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 190 | 3,984,328 |
| implement | 30 | 661,941 |
| review | 68 | 1,659,979 |
| **Total** | **288** | **6,306,248** |

<!-- wave:context-efficiency-state {"generation":147,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":30,"content_source_credit":676994,"derived_artifact_credit":0,"direct_net":661941,"estimated_tokens_saved":661941,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1142,"response_debit":17017,"source_credit_count":7,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3106},"plan":{"calls":190,"content_source_credit":4362727,"derived_artifact_credit":2692,"direct_net":3984328,"estimated_tokens_saved":3984328,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10356,"response_debit":376243,"source_credit_count":103,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5508},"review":{"calls":68,"content_source_credit":1786757,"derived_artifact_credit":1542,"direct_net":1659979,"estimated_tokens_saved":1659979,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13073,"response_debit":119025,"source_credit_count":48,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":288,"content_source_credit":6826478,"derived_artifact_credit":4234,"direct_net":6306248,"estimated_tokens_saved":6306248,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":24571,"response_debit":512285,"source_credit_count":158,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12392},"wave_id":"22nu3 reported-caller-recovery-corrections"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 11 | 0 | 5 | 2,494,208 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":2494208,"surfaced_events":11} -->
<!-- wave:exploration-avoided end -->
