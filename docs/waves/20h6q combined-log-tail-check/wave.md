# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20h6q combined-log-tail-check`
Title: 1.29.0 Release Follow-ups

## Objective

Address the two release qualification follow-ups and the reported upgrade usability defects: deterministic combined log-tail testing, quiet completed guide migrations, pending-upgrade guidance before pack selection, and a bounded later timing reassessment. Preserve project ownership, retained-run authority and existing validation gates.

## Changes

Change ID: `20gz6-bug deterministic-combined-log-tail-check`
Change Status: `implemented`

Change ID: `20h6r-bug quiet-completed-guide-migration`
Change Status: `implemented`

Change ID: `20h8g-bug pending-upgrade-before-pack-selection`
Change Status: `implemented`

Change ID: `20h8h-task reassess-warm-estimator-budget`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (after readiness)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-12

## Wave Summary

Closed after independent delivery approvals, explicit operator approval and a matching green qualification receipt: 12,416 tests across 185 files, 12 skips.

- 20h8g: default upgrades explain retained pending work before pack discovery; explicit verified recovery remains available.
- 20h6r: completed project-owned guide migrations stop emitting the permanent unconfirmed notice; destination presence grants no rewrite authority.
- 20gz6: regression fixtures establish stream ordering and process readiness before assertions; production log caps and real deadlines remain unchanged.
- 20h8h: timing disposition is inconclusive/deferred under concurrent reviews. Later reassessment is bounded to one baseline and one corroborating run; no threshold change or causal conclusion.

All ACs/tasks are reconciled; no intentionally deferred checkbox remains. The timing task's explicit inability disposition is complete, while the measurement itself remains a future action. Retrospective: establish process readiness before testing pipe deadlines, preserve project ownership and retained-pack authority, and keep completion narration in Progress Log rather than replacing reviewed plan text. These lessons already live in canonical tests/guidance and this record; the proposed fixture-memory draft was not selected because it adds no durable action. Retention is limited to the four admitted change docs, wave.md and authoritative events.jsonl; no routine evidence folder was created.

Local testing artifact: 1.30.0+pw8f, wavefoundry-1.30.0.pw8f.zip, 10,510,910 bytes, SHA256 565fba68ffd6f0f4591a4806e6019b9ccab57a94dc583dac32094beef31aa941. The operator renewed the build request after disclosure of red/incomplete packaging qualification; the exception applies only to this local artifact. Default/second/declared reports remain unchanged; no public release or later-build qualification is claimed.

## Watchpoints

- Preserve the 1 MiB cap and 64 KiB combined suffix; do not introduce per-stream file retention.
- Use bounded synchronization for asserted marker ordering and preserve real deadline controls.
- Operator approved the 1.29.0 release with this follow-up and timing analysis deferred.
- No performance conclusions while other reviews run on the host; no permanent routine evidence folder.
- A new-only unmanaged guide never grants link-rewrite authority. No new managed region, receipt or dismissal file.
- A no-argument upgrade reports pending work; it must not silently switch packs, validate memories, publish indexes or erase retained state.
- Serialize shared runner tests, seed 160, rendered upgrade guidance and changelog writes. The changes have no hard dependency on one another.
- Use targeted verification per change and the normal wave-level qualification once source edits settle; bookkeeping alone does not justify repeated qualification.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 20h6q-deadline-fixture-precondition | do_now | no | completed | qa-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- Operator closure approval is recorded in the typed ledger.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 360 | 3,692,167 |
| implement | 474 | 1,912,231 |
| review | 115 | 835,534 |
| **Total** | **949** | **6,439,932** |

<!-- wave:context-efficiency-state {"generation":664,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":474,"content_source_credit":3065337,"derived_artifact_credit":0,"direct_net":1912231,"estimated_tokens_saved":1912231,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17412,"response_debit":1296822,"source_credit_count":98,"source_credit_drop_count":0,"structural_source_credit":156392,"workflow_prompt_credit":4736},"plan":{"calls":360,"content_source_credit":4373029,"derived_artifact_credit":7234,"direct_net":3692167,"estimated_tokens_saved":3692167,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20994,"response_debit":670907,"source_credit_count":156,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":115,"content_source_credit":1135147,"derived_artifact_credit":330,"direct_net":835534,"estimated_tokens_saved":835534,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28912,"response_debit":273962,"source_credit_count":71,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":949,"content_source_credit":8573513,"derived_artifact_credit":7564,"direct_net":6439932,"estimated_tokens_saved":6439932,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":67318,"response_debit":2241691,"source_credit_count":325,"source_credit_drop_count":0,"structural_source_credit":156392,"workflow_prompt_credit":11472},"wave_id":"20h6q combined-log-tail-check"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 29 | 0 | 18 | 17,710,626 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":18,"estimated_exploration_avoided":17710626,"surfaced_events":29} -->
<!-- wave:exploration-avoided end -->
## Planning Decisions

- Keep stable wave ID/path 20h6q and expand its title/objective; separate change documents preserve each repair's acceptance boundary.
- Prefer suppression of the false unmanaged-target notice over new migration state or changed ownership.
- Prefer an actionable pending-upgrade response over automatic resume or discovery followed by a low-level rejection.
- Treat the timing exception as a bounded diagnostic task, not a presumed regression or permission to weaken a threshold.
- Durable outcomes belong in wave.md, admitted change docs and the authoritative review ledger; retain no routine evidence directory.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Closed with current approvals and matching green wave receipt, then built local 1.30.0+pw8f once under the disclosed packaging exception. CRC, unique safe paths, all 248 corresponding framework files, VERSION/manifest/changelog, nested payload hashes and nested-feature parity verified. Internal bridge files are absent from dist. No code, thresholds, commit, push or public release changed during packaging. | Artifact and SHA256 in Wave Summary; docs gate passed; original incomplete qualification reports retained |
| 2026-10-12 | Operator authorized closure and renewed the local 1.30.0 build after the incomplete packaging reports were disclosed. This one local artifact uses the matching green wave qualification with the disclosed default/second/declared exception; original red reports remain unchanged. Restored the exact handoff text independently retained from delivery reads, keeping current completion narration in Progress Log to preserve reviewed plan identity. | Current operator request; existing 12,416-test receipt; packaging reports retained |
| 2026-10-12 | Local 1.30.0 packaging was requested after the wave completed. Its three concurrent qualification runs are red/incomplete (default 9 failing files, second 9, declared 8), including five per-file 600-second timeouts each. Five named non-budget functional assertions pass in one subsequent diagnostic; no cause, regression or full-profile pass is inferred. Reviewed framework inputs and the earlier 12,416-test green receipt are unchanged. Exact comparisons refuse incomplete reports. Await an explicit exception for this one local pack or later complete qualification; no ZIP, version stamp, code/threshold repair, public release or extra suite retry. | Ignored qualification/package-1.30.0-{default,second,declared}.json; ReloadDownloadOwnershipTests.test_registered_public_reload_preserves_canonical_owner; ExplorationAvoidedTests.test_concurrent_distinct_origins_are_lossless; DashboardManagedIdentityTests.test_mcp_start_confirms_serving_own_child; TechdocsAuditDegradeTests file/subdirectory escape controls; uv 0.12.17/18 hashes and three npm libraries verified |
| 2026-10-12 | Final canonical qualification PASS: 12,416 tests across 185 files, 12 skips, with a matching green receipt. All required delivery approvals are current and the single finding is terminal after fresh QA/code repair review. Paused without closing; edit gates closed. No new memory candidates are needed: durable lessons are captured in the canonical fixture and wave record. Operator requested a local 1.30.0 pack next. | run_tests.py exit 0; receipt inputs_hash 09d227d9329a4a10d69dc710f20bacdcb76981695c5675104ba70439325b08c5; typed review ledger; full docs validation |
| 2026-10-12 | Delivery review PASS: standard red-team primer and closing reconciliation; architecture, security, QA and reality fixed seats; rotating docs-contract; required code/release lanes; council-chair synthesis. Framework Operator assessment approved the two operator-facing fixes; test/diagnostic persona review is N/A. One real, pre-existing required-AC fixture finding was repaired in cycle 1 and cleared by fresh QA, with focused code reassessment; unaffected approvals were retained. Strongest alternative, a shared retained-state query API, was considered and rejected as unnecessary expansion. All ACs/tasks are complete; full docs validation passes. Canonical qualification remains pending. Timing remains explicitly inconclusive/deferred, with no threshold or production-logger changes. | Current typed six-lane/council approvals and terminal finding; PendingUpgradeTests and UpgradeManifestRecoveryTests reject changed archives before restoration; BoundedDocumentRepairTests rejects unmanaged authority; ChildTeeTests detects missing finalization, missing setup and loosened pipe deadlines; source base 7a4b1e91, final child-test blob a1363556931c98605dc954f5a03fa2056e3088e3 |
| 2026-10-12 | Corrected qualification completed 12,416 tests across 185 files with 12 skips. All files except the existing held-pipe deadline control passed, including all 765 upgrade tests. QA independently reproduced its missing parent-exit setup and recorded a required-AC finding; cause of the original delay remains unknown. Recorded cycle-1 repair adds bounded parent/descendant readiness before the unchanged real 0.2-second deadline. Focused child tests and deliberately delayed startup pass; fresh QA/code reverification and canonical qualification are pending. | Typed finding 20h6q-deadline-fixture-precondition; test_child_tee.ChildTeeTests.test_explicit_timeout_includes_withheld_descendant_pipes_and_closes_readers; source-only fixture repair |
| 2026-10-12 | First canonical run completed 12,413 tests across 185 files with 12 skips and six failing files. Five failures are environment restrictions (local binds, ps and bootstrap/cache paths); four manifest-recovery assertions in the sixth file require compatibility reconciliation in the admitted upgrade scope. No green receipt claimed. Delivery seats have not started; repair is within the existing implementation loop. | run_tests complete result; UpgradeManifestRecoveryTests four failures; process-info passes in the tool environment outside sandbox |
| 2026-10-12 | Upgrade repair passes 99 focused checks: 25 failure-surfacing, 70 recovery/preview seams and four storage process tests. Default CLI/MCP reports retained work before discovery/restoration; explicit original and relocated pack resumes remain supported. Three deleted-check mutants fail at their intended boundaries. Seed/prompt, tool contract, architecture and Unreleased notes agree. Source is frozen for canonical qualification and delivery review. Exact field checkpoint, live upgrades and native Windows remain unverified. | PendingUpgradeTests; storage process continuations; memory/docs/cleanup seam classes; real incoming preview |
| 2026-10-12 | Renderer and child-log focused verification passed: 24 and 20 default tests, plus the same 44 tests under each second and declared profile, with no skips. These are functional checks, not timing diagnosis or a full qualification receipt. The broken-finalization control fails both forced reader orders. Production logger bytes remain unchanged. | test_lifecycle_document_names; test_child_tee; two bounded profile runs; in-memory finalizer mutation |
| 2026-10-12 | Readiness PASS: standard red-team primer; architecture, security, QA and reality fixed seats; rotating docs-contract; required code/release lanes; council-chair synthesis. Unanimous with no findings. Strongest alternative retained: one early read-only pending decision using existing recovery guidance. Allocation: scoped upgrade implementer requested gpt-6.1-sol/high for multi-entry recovery logic (runtime unverified); coordinator handles renderer, fixture and shared docs. Existing wave order is a preference, not a dependency; disjoint writes proceed together, shared runner tests/docs stay serialized. | Typed current-receipt approvals; successful Prepare and Implement; original-pack continuation and no-rewrite boundaries |
| 2026-10-12 | Operator confirmed that concurrent reviews are still running and timing must remain deferred. No targeted timing measurements will run in this effort. The original release-time failure remains inconclusive; reassess with the admitted two-run limit when suitable conditions are available. | Operator reply; 20h8h diagnostic boundary |
| 2026-10-12 | Preparation technical checks passed; current typed lane/council approvals are pending. Coordinator retains implementation ownership for the small renderer and fixture edits; upgrade routing may be delegated after readiness to a scoped implementer. Independent readiness chair and seats requested gpt-6.1-sol/high for bounded code-grounded contract review; actual runtime identity is unavailable. Required independent delivery review remains separate. | wf_prepare_wave receipt review-policy-7527d88095ada8ffae22; admitted four-change packet |
