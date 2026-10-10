# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `204mp waveforge-follow-up`
Title: Waveforge Follow Up

## Objective

Resolve Waveforge public follow-up C1–C5 against d11da852: portable framework test oracles, declarable legacy council actors, and repaired links after role-document moves. C6 is implemented and reviewed under its original change ID in wave 206is.

## Changes

Change ID: `204ml-bug distribution-test-oracles`
Change Status: `implemented`

Change ID: `204mm-enh declarable-legacy-council-actors`
Change Status: `implemented`
Depends On: `204ml-bug distribution-test-oracles`

Change ID: `204mn-bug moved-role-document-links`
Change Status: `implemented`
Depends On: `204ml-bug distribution-test-oracles`

## Participants

- Coordinator: Engineering coordinator
- Write-owning roles: Implementer and technical writer; assignments confirmed at Prepare
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-09

## Wave Summary

Delivered Waveforge C1–C5: portable independent test oracles, declarable legacy council actors and exact supported role-link migration with preview and retry. C6 is delivered in wave 206is. Unknown hook-tool names and packaging skip parity remain separate follow-ups.

- All admitted changes are implemented and every AC and task is completed; there are no intentionally unmet checkboxes.
- All required specialist delivery approvals and council-readiness are current; findings are terminal. Council-delivery is not selected by the current Prepare receipt. Docs-contract review was performed where required.
- Operator closure approval was explicitly given and recorded as typed evidence on 2026-10-09. Completed chronology is recorded above.
- Closure proved the current green framework receipt: 11995 tests, hash 83a742059996ef0eedc2fd3c637d5ef8864dedfbdacbf8c8c88f29d226f86092. No framework code or seed changed during closure.
- Cleanup retains authoritative events, unique reports, reproducible probes, receipts and historical fingerprints in their existing evidence locations. The later authorized2026-10-10 cleanup removes verified redundant working copies; see Evidence Retention below.
- Retrospective: Portable tests require independent expectations and explicit upstream ownership; link migrations rewrite only controlled destinations. The reviewed contracts and regression owners already capture this lesson; no additional durable memory is warranted.
- Memory checkpoint: memory_propose(create) was run; no pending candidate remains. The proposal produced zero new candidates.
- The session handoff records all six closures. Closure did not commit, push or publish a new pack.

## Watchpoints

- C3 oracle selected: frozen test-local historical payload encoder plus independent golden cross-checks; upstream ownership inventory includes zero-hit files and fixtures.
- C6 decision and implementation are tracked separately in 206is; its original primer observations remain preserved here.
- Serialize shared tests, profile modules, renderers and upgrade contracts.
- Pack204mk, Rust206og, phase207lx and graph207t4 are paused and technically ready for operator closure. Public204mp is finishing final bookkeeping before pause.
- Preparation must review alias authority boundaries and role-link retry behavior.
- C1–C5 implementation and full independent delivery review are complete. No release, commit or push is included.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DOC-204MP-01 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer |
| ARCH-DOC-204MP-02 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer |
| ARCH-DOC-204MP-03 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer, code-reviewer, qa-reviewer |
| ARCH-DOC-204MP-04 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer, code-reviewer, qa-reviewer |
| ARCH-DOC-204MP-05 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer, code-reviewer, qa-reviewer |
| ARCH-DOC-204MP-06 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer, code-reviewer, qa-reviewer |
| ARCH-DOC-204MP-07 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer, code-reviewer, qa-reviewer |
| ARCH-DOC-204MP-08 | do_now | no | completed | docs-contract-reviewer |
| ARCH-DOC-204MP-09 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer, code-reviewer, qa-reviewer |
| ARCH-DOC-204MP-10 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer, code-reviewer, qa-reviewer |
| ARCH-DOC-204MP-11 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer, code-reviewer, qa-reviewer |
| ARCH-DOC-204MP-12 | do_now | no | completed | docs-contract-reviewer, code-reviewer, qa-reviewer |
| ARCH-DOC-204MP-13 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer |
| ARCH-DOC-204MP-14 | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer |

*Machine review state — 14 findings; current: do_now 14, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Base implementation includes the completed fixture repairs in paused wave204mk. Public204mp holds the OPEN slot until its final pause; intra-wave dependencies are declared above.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 136 | 1,803,418 |
| implement | 251 | 4,141,989 |
| review | 1,047 | 10,061,079 |
| **Total** | **1,434** | **16,006,486** |

<!-- wave:context-efficiency-state {"generation":1404,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":251,"content_source_credit":1556854,"derived_artifact_credit":0,"direct_net":4141989,"estimated_tokens_saved":4141989,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9149,"response_debit":483900,"source_credit_count":160,"source_credit_drop_count":0,"structural_source_credit":3075603,"workflow_prompt_credit":2581},"plan":{"calls":136,"content_source_credit":2181057,"derived_artifact_credit":1545,"direct_net":1803418,"estimated_tokens_saved":1803418,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":24848,"response_debit":358141,"source_credit_count":103,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":1047,"content_source_credit":14316399,"derived_artifact_credit":2334,"direct_net":10061079,"estimated_tokens_saved":10061079,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":195674,"response_debit":4064364,"source_credit_count":389,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1434,"content_source_credit":18054310,"derived_artifact_credit":3879,"direct_net":16006486,"estimated_tokens_saved":16006486,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":229671,"response_debit":4906405,"source_credit_count":652,"source_credit_drop_count":0,"structural_source_credit":3075603,"workflow_prompt_credit":8770},"wave_id":"204mp waveforge-follow-up"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 161 | 0 | 35 | 78,124,124 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":35,"estimated_exploration_avoided":78124124,"surfaced_events":161} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

### Final bounded delivery review — 2026-10-09

All fourteen cycle-1 findings have independent lane reverifications recorded, with no unresolved required lanes. All five required delivery approvals are current. QA independently verified the new green11977-test canonical receipt and recomputed its matching inputs hash. The code/QA and architecture/docs reviewers each disclosed their dual-role context; neither implemented the repairs. No council-delivery approval is required by this receipt. The source remains frozen at the final24-path packet, and phase207lx/graph207t4 own paths remain unchanged.

Actual independent evidence includes code/QA25 incoming cases,57 current and28 renamed checks without skips; architecture/docs56 incoming cases,26 default,16 selected renamed and10 boundary controls without skips; security32 controls without skips. Saved pre-autolink source reproduces four failures and two earlier-code controls. Source-removal mutants detect URI/email and title-metadata regressions; prior narrower HTML first-line mutant survival remains disclosed, without an isolated-guard coverage claim. The root full upgrade owner passes711 tests with two existing native Windows skips. This is finite contract verification, not whole-CommonMark, native Windows, downstream, private follow-up or setup-readiness certification. Durable reports and probe artifacts are in evidence/delivery-20261009-04 and evidence/delivery-20261009-autolink-repair.

Review memory curation found no candidate targeting the repaired renderer. Existing active memories and unrelated Rust drafts remain unchanged; broad consolidation or purging is outside this repair. Full docs validation passes with zero errors or warnings. No operator approval, close, commit, push or new pack has been recorded.

- Readiness preparation in progress. Source-grounded choices for C1–C5 are recorded; C6 moved intact to 206is pending its source-location decision. No readiness verdict is claimed yet.
- Actual planned review lanes: code, QA, architecture, docs-contract and security. Current Prepare dry-run selects standard primer with red-team and docs-contract council seats; final receipt and depth must reflect the settled packet.
- Allocation: readiness coordinator owns plan amendments; independent reviewers own evidence only. Runtime model identity is not exposed. No implementation source edited.

- Removal disposition: `204mo-enh version-independent-journal-hook` moved to `206is journal-hook-follow-up` to allow independent C1–C5 progress while preserving all C6 requirements.

- Actual readiness primer depth: full (five stances, three questions), justified by actor authority and project-document write boundaries; original isolated primer retained in readiness-primer.md. The generated receipt's primer_depth remains standard because lifecycle_gate_support hardcodes that metadata; no override exists. This discrepancy is disclosed, not hand-edited or used to reduce review. Actual configured council seats remain red-team and docs-contract-reviewer; five specialist lanes separately cover code, QA, architecture, docs-contract and security.
- Current C1–C5 review receipt: review-policy-5de6f84316a3a4bf9e13. Fresh independent specialist review started against the three admitted documents after the canonical C6 split; final council must come from an independent chair, not the plan-authoring readiness coordinator.
- Product-owner acknowledgment: the user explicitly requested implementation and full review of these Waveforge changes. Splitting the unresolved journal location into 206is preserves all requested scope and allows independent progress.

- Delivery checkpoint: 204ml/204mm are implemented; 204mn is review with AC-2 reopened after fresh recursive-container failures (ARCH-DOC-204MP-01); unified repair is queued after the readiness-phase fix. The frozen implementation packet is implementation-evidence.md with evidence/implementation-tree.json (23 SHA-256-bound paths). All five specialist reviews executed; security approved with notes, architecture/docs-contract await bounded repair, code approval is held for recheck, and final QA is withheld for the separate canonical graph publication failure. No closure, commit, push or publication.

### Block/inline repair checkpoint

Recorded ARCH-DOC-204MP-02 cycle-1 repair start preceded source edits. The actual C5 owner passes17/0 skips with35 install/reinstall preservation cases; four inline/block mutants and six recursive mutants are detected. AC-2 is complete on implementation evidence only; both typed findings remain open pending independent reverification. C1 inventory maintenance includes the new admitted graph test owner and verifies524 upstream files; default distribution owners107/0. Full upgrade and canonical qualification remain pending.

### Further independent C5 findings pending synthesis

Fresh code/QA and architecture/docs reviewers independently reproduced ordinary container-reference, HTML-block preservation, invalid backtick-fence info and escaped-inline-link failures through actual installing/reinstall fixtures. Architecture/docs also reproduced an existing native-role directory rename pair moving its file without repairing an ordinary link to it. Required AC-2 is reopened; no terminal original finding or public approval is claimed. Source remains frozen until every lane reports; root will record and deduplicate the complete round before a bounded repair.

## Evidence Retention

Authorized cleanup on 2026-10-10 removed 37 redundant working files (913,748 bytes); 39 evidence files remain. Keep the original shared final qualification receipt/log, immutable-ledger citations, exact-byte migration probes, source baselines, failing controls and historical source identities. C1–C5 outcomes, fourteen cleared findings and final approval/qualification remain in this record and events.jsonl; redundant review packets and green logs add no distinct long-term proof. All ledger-cited paths and bytes stay unchanged.
