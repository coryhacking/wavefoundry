# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21luh wave-work-and-focused-rereview`
Title: Wave Work And Focused Rereview

## Objective

Agents share one gitignored, disposable work area per wave, and readiness reviewers can inspect every material change since their own prior approval without reconstructing uncommitted history. Successful close safely cleans only owned scratch after durable evidence is preserved. Existing approval authority, receipt identity and deferral rules remain unchanged; missing snapshots retain normal full review.

## Changes

Change ID: `21luf-enh wave-work-area-and-safe-close-cleanup`
Change Status: `implemented`

Change ID: `21lug-enh receipt-section-attribution-and-focused-rereview`
Change Status: `implemented`
Depends On: `21luf-enh wave-work-area-and-safe-close-cleanup`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer; coordinator owns plan and wave records; shared server/seed edits serialized
- Requested review lanes: security-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-25

## Wave Summary

Wave `21luh` (Wave Work And Focused Rereview) delivered two changes: Wave work area and safe close cleanup and Receipt section attribution and focused re-review.

Intent outcome: achieved for both admitted changes and the wave Objective. Independent bounded review and final qualification (12,195 tests across 211 files, 12 skips, 592.190s) establish shared owned wave work, contained lifecycle cleanup and complete per-lane cumulative reviewed-text reconstruction with explicit full-review fallback, while preserving receipt identity and approval authority. QA independently confirmed this assessment; Council reused it. Durable proof must still be preserved before scratch cleanup. Native Windows safe-I/O qualification, universal agent adoption and real-world reviewer-effort reduction are not claimed; the first three later waves requiring renewed readiness will provide the specified prospective observations.

**Changes delivered:**

- **Wave work area and safe close cleanup** (`21luf-enh wave-work-area-and-safe-close-cleanup`) — 5 ACs completed. Key decisions: Managed local work area with plain files and lazy subdirectories; Cleanup after committed closure, best effort
- **Receipt section attribution and focused re-review** (`21lug-enh receipt-section-attribution-and-focused-rereview`) — 6 ACs completed. Key decisions: Section metadata plus disposable text snapshots; Compare to each lane's approved receipt
## Watchpoints

- Work path is `.wavefoundry/work/<wave-id>/`, keyed by the unique lifecycle prefix, with no waves subdirectory. Git ignore is an implementation requirement, not already shipped.
- Implement 21luf before 21lug; serialize shared lifecycle, seed and guidance writes.
- Cleanup is destructive but narrowly limited to owned disposable scratch after successful closure; retain uncertain ownership and report failure.
- No new approval gate, automatic approval transfer, selective invalidation or post-implementation deferral exemption.
- Receipt snapshots are optional aids and not durable evidence authority.
- 21lue test-receipt acceptance and later intent-fit experiments remain separate.
- Baseline: 12 receipts, 11 transitions and 34 readiness approvals in 21j63; per-round effort unavailable after existing telemetry compaction.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 21LUH-READ-IGNORE-CARRIER | not_issue | no | not_required | release-reviewer |

*Machine review state — 1 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 1*
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

- No external wave dependency; follows closed 21j63. Intra-wave ordering is declared in the 21lug change block.

## Review Checkpoints

- 2026-10-25: Close retrospective: compare cumulatively from each lane's last approval; immutable scratch snapshots remain optional aids, and safe cleanup requires preserving unique proof first. These lessons are already carried in canonical review/cleanup guidance, the maintained regular-parent regression and the durable baseline/measurement record; no duplicate memory is warranted. memory_propose dry-run returned zero candidates (decision rows lacked a current contained source anchor); no candidates were created. Retain wave.md, admitted plans, events.jsonl and evidence/readiness-baseline-21j63.md. Routine external task captures are not auto-deleted. The operator explicitly instructed closure after reviewing the achieved intent and current green qualification.

- 2026-10-25: Final delivery Council: full-depth red-team primer; independent fixed architecture, security, QA and reality-checker seats; rotating docs-contract as best-alternative seat; separate required code and release specialists. Chair weighed anonymized Seat 1–5 evidence before restoring identities. Aggregate unanimous / max severity none; no material disagreement or unresolved production finding. Primer challenged optional cache authority, proof preservation and effort overclaims; registered lifecycle/publication tests, cumulative reconstruction controls and explicit fallback answered those challenges. Strongest alternative, full-plan-only review, is simpler but loses verified cumulative uncommitted history; keep the optional aid and existing first-three-wave observation table, without adding a gate or permanent archive. Overlapping test counts are not independent additive samples. Parent-anchor removal survived older tests; independent regular-parent substitution detected it and is now maintained as WaveWorkTests.test_regular_parent_substitution_before_unlink_preserves_moved_work. Security replay passed and the isolated mutant failed its preservation assertion. No production repair was required. All 48 reviewed source fingerprints remained unchanged throughout final qualification; final receipt inputs_hash db4065ce546931c670d6378ed45f79af78c256fe64aec17cfda145e214335a87. Both changes remain implemented; operator closure is not authorized.

2026-10-25: Intent outcome: achieved for both admitted changes and the wave Objective. Independent bounded review and final qualification (12,195 tests across 211 files, 12 skips, 592.190s) establish shared owned wave work, contained lifecycle cleanup and complete per-lane cumulative reviewed-text reconstruction with explicit full-review fallback, while preserving receipt identity and approval authority. QA independently confirmed this assessment; Council reused it. Durable proof must still be preserved before scratch cleanup. Native Windows safe-I/O qualification, universal agent adoption and real-world reviewer-effort reduction are not claimed; the first three later waves requiring renewed readiness will provide the specified prospective observations.

- 2026-10-25: First canonical qualification completed red: 12,192 tests / 211 files / 12 skips / 613.310s. Before repair: route helper record filename through vocabulary profile; make optional contained-read import lazy to preserve packaged minimal import; update profile-aware test fixtures and workspace-specific golden/relocated-root/compact-artifact contracts; regenerate only affected pre-edit hook source fingerprint. Seven failing files, no source changed during run. This records the bounded implementation repair before mutation; independent delivery review has not yet begun.

- 2026-10-25: Pre-qualification integration corrections: projection-only receipt publication accepts no-receipt state; configured root aliases normalize only the root prefix and preserve no-follow internal checks. Four old attribution assertions now expect the named changed section, while legacy fallback remains pinned. Twelve golden work-area fields are stable; seven affected regression tests pass, zero skips. Helper total now 32. Both changes implemented; independent-review tasks intentionally remain unchecked until required lanes finish.

- 2026-10-25: Implementation controls: 31 work/snapshot helper tests, 10 registered workspace lifecycle tests and six registered receipt/re-review tests passed. Guard mutants detected ownership/directory/parent/generation substitutions, omitted creation/cleanup, paused-generation rotation, raw/canonical hash and receipt/normalizer mismatch, overwrite, Prepare-only snapshot publication, live-text reread and latest-pair-only baseline errors. Canonical ignore/index/reconcile/source-observation mutants also fail their named tests. The source-module census suite passed 232 tests. These are local fixture results, not native Windows or transport qualification; unsupported safe work I/O preserves files. Durable reconstruction result and limits are in evidence/readiness-baseline-21j63.md; maintained test IDs reproduce the controls. Independent delivery review and canonical qualification are still pending.

- 2026-10-25: Readiness completed on review-policy-68602cf56165446f870e after one bounded repair of seed-050/domain-map source targets. Six required lanes and independent chair approved; fixed architecture/security/QA/reality, rotating docs-contract, red-team full primer and closing reconciliation. Intent fit establishes prospectively; observed savings remain unproven. Implementation allocation: isolated helper and exclusion/guidance work, coordinator owns shared server integration; reviewer contexts remain separate.

2026-10-25: Prepare allocation: coordinator owns integration and lifecycle records; fresh independent readiness workers review the plans and actual source with MCP-first retrieval. Full-depth red-team primer first (owned deletion and snapshot/publication boundaries), then isolated architecture, security, QA, reality-checker and rotating docs-contract seats; code and release specialists cover their required remits. Use the current capable model for safety/architecture judgment, with runtime identity unverified where not exposed. No implementation edits before current readiness approvals.

2026-10-25: Planned and admitted at the operator's request; neither readied nor opened. Product-owner admission scope was explicitly selected in conversation: gitignored wave work with safe post-close cleanup and receipt-backed focused re-review; no formal specialist or Council approval is claimed. Read-only code grounding and the Git ignore probe informed the plans. Security and architecture lanes are requested for destructive cleanup, snapshot trust and publication boundaries.

2026-10-25: Baseline and measurement limits: [21j63 readiness baseline](evidence/readiness-baseline-21j63.md). Counts derive from the typed ledger; sealed telemetry retains aggregate proxies but zero raw per-call rows. Future comparisons must capture per-round observations before closure and distinguish changes in workload from improved review efficiency.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 394 | 2,698,138 |
| implement | 52 | 960,751 |
| review | 422 | 6,710,329 |
| **Total** | **868** | **10,369,218** |

<!-- wave:context-efficiency-state {"generation":571,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":52,"content_source_credit":1012511,"derived_artifact_credit":0,"direct_net":960751,"estimated_tokens_saved":960751,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1788,"response_debit":54102,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4130},"plan":{"calls":394,"content_source_credit":3647221,"derived_artifact_credit":4640,"direct_net":2698138,"estimated_tokens_saved":2698138,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17820,"response_debit":943865,"source_credit_count":154,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7962},"review":{"calls":422,"content_source_credit":7516980,"derived_artifact_credit":4526,"direct_net":6710329,"estimated_tokens_saved":6710329,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":22698,"response_debit":792168,"source_credit_count":234,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":868,"content_source_credit":12176712,"derived_artifact_credit":9166,"direct_net":10369218,"estimated_tokens_saved":10369218,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":42306,"response_debit":1790135,"source_credit_count":393,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15781},"wave_id":"21luh wave-work-and-focused-rereview"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 72 | 0 | 35 | 21,916,701 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":35,"estimated_exploration_avoided":21916701,"surfaced_events":72} -->
<!-- wave:exploration-avoided end -->
