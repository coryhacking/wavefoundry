# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21uny mcp-lifecycle-reliability`
Title: MCP Lifecycle Reliability

## Objective

Make MCP reload identity and cleanup outcomes explicit for operators, and verify owned-resource shutdown through real stdio tests. Host session lifetime and Tensorwell daemon lifetime remain independently owned.

## Changes

Change ID: `21ttt-enh mcp-lifecycle-reliability`
Change Status: `implemented`

## Participants

- Coordinator: Codex coordinator
- Write-owning roles: implementer (coordinator)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-27

## Wave Summary

Wave `21uny` (MCP Lifecycle Reliability) delivered one change: MCP Lifecycle Reliability. Notable adjustments during implementation: MCP Lifecycle Reliability: Planning: host restart removed old MCP PIDs; isolated EOF probes exited in 0.074s and 0.126s without forced termination. Baseline only, not universal shutdown proof.

Intent outcome: achieved for the admitted lifecycle contract. The final 12,281-test canonical run and independent delivery checks establish process diagnostics, current-handler shutdown, reversible monitor preparation, refusal without disposal when preparation fails, and successful reload after callbacks drain. Operator restarted the host; live MCP PID 73407 is owned by new daemon 72745, loaded runner and implementation match disk, both monitors are alive, and previous daemon 39568/MCP 40330 are absent. Native Windows/Linux/WSL execution, arbitrary foreground/native quiescence and rollback after destructive cleanup remain outside the verified claim. All seven ACs and all tasks are complete; no intentional AC deferrals.

**Changes delivered:**

- **MCP Lifecycle Reliability** (`21ttt-enh mcp-lifecycle-reliability`) — 7 ACs completed. Key decisions: Add diagnostics and bounded cleanup using existing ownership
## Watchpoints

- Watchpoint: serialize source writes and freeze the tree during independent review. Preserve shared Tensorwell services and existing healthy reload.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 21uny-qa-lifecycle-fixture-prefix | do_now | no | completed | code-reviewer, qa-reviewer, council-delivery |

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

- Operator explicitly authorized closure on 2026-10-27; typed operator-signoff recorded.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-10-27: Two-phase extension delivered and independently approved against all seven ACs. Full five-stance primer; isolated architecture/security/QA/reality fixed seats (remaining seats parallel), rotating docs-contract alternative and separate code lane. Anonymous-first synthesis unanimous, no new findings; red-team closing held. All required specialist/council approvals refreshed; operator signoff remains pending. Controlled intent establishes resource preservation/resumed scheduling on preparation refusal and callback exclusion through successful cleanup. Canonical qualification: 12,281 tests / 214 files / 12 skips / 555.492s; receipt ok. Framework gate closed; no commit, closure or host restart authorized by this implementation task.

Final extension Git blobs: server.py 66c8f426fb185bc2162eaa9a520624ff3b3069e6; server_impl.py f1786eeffc00351d7ffe148ac3d769b83f138ca5; test_mcp_lifecycle.py a97753a34b7ac3fad017c7a580c3c5f3c7d3a5a5; test_index_source_guard.py fb7cbf82965ecdf157327ca7893c74a7d75089e4; test_setup_readiness_integration.py ce111071a36cc115ed7203c0c4d5fc96f7522ad9; test_server_context_efficiency.py c5959e1c697afe955ecc8d5e19de5925f69332d2; MCP spec d1837d2ada9088b0ec9647971fddabdda56aa42b; architecture 631e0c38e5c0125f7eff40a8bb7f2fd11467747e. The unique staggered-callback probe recipe is preserved in the change Progress Log. Routine logs remain in the disposable work area. No new memory candidate needed beyond maintained tests, contracts and typed evidence.

2026-10-27: Amended readiness passed on receipt 28fd8c11b4c159422f33. Isolated standard primer, fixed architecture/security/QA/reality and rotating docs-contract plus independent code lane; no findings, unanimous anonymous-first synthesis, red-team closing held. All four lanes and council recorded. QA actual registered baseline held either callback, observed destructive refusal at 1.004/1.006s with both stop events set and resource cleanup; this falsifies AC6 before the fix. Shared callback gate preferred over partial-lock acquisition or restarting disposed workers.

2026-10-27: Operator authorized reversible reload preparation, extending the existing change with AC-6/7. Re-Prepare and fresh review are required before edits. Coordinator owns tightly coupled source/tests; independent council uses fresh gpt-6.1-sol/high contexts for concurrency judgment (requested settings, runtime identity unverified). Work stays in `.wavefoundry/work/21uny/`. No commit, close, live reload, host restart or native Windows qualification is inferred.

2026-10-27: Delivery complete; all specialist and council approvals current, required finding repaired and independently reverified, no unresolved reviewer block. Standard council's final intent verdict establishes the controlled lifecycle outcome. Fresh repaired-tree code review: 8 tests / 11.195s; QA: 8 / 11.409s; chair stdio replay: 3 / 6.077s, all zero skips. Each independently restored old invalid fixture names and caught first-reload failure. Architecture/docs acknowledge test-only repair with unchanged product contracts; no full-council trigger or remaining dissent. Final canonical run passed 12,278 tests / 214 files / 12 skips / 547.348s, green receipt. No native Windows, arbitrary native interruption, SIGKILL cleanup, host-session termination or universal absence-of-leaks claim. Operator signoff remains pending; no closure or commit authorized.

Final reviewed Git blob fingerprints: server.py f41abb1c22f6d195e6328a277cb1eb10efc3fd97; server_impl.py b000e61c7df342ac466bdc0c9451f7e7d487b066; test_mcp_lifecycle.py 0a05f73a26325480fe5079888f76ac4acce73ce7; MCP spec b27c829d352ae08956cf0e5cb004c48229522491; data/control architecture fb1d6960a0a51c17caeb5bd3104eb5b695742280. The unique composed-monitor probe recipe is preserved in the change Progress Log; routine scratch logs remain disposable.

2026-10-27: Initial delivery collection completed on frozen tree: one low-impact required verification defect from QA (invalid fixture names plus after-third-only health check), no production regression. Code/architecture/security/reality/docs otherwise passed their remits. Standard council anonymous-first synthesis retained QA blocking authority; no full-council trigger. Recorded cycle-1 focused test-only repair and exact old-prefix mutant detection; refreshed code/QA checks and council repair-effects replay required.

2026-10-27: Intent outcome: achieved in controlled lifecycle execution: public process identity and same-process reload are explicit; current-handler teardown and named timeout/refusal/retry pass new tests, with four known-bad mutants detected. Actual stdio EOF is verified for idle and entered finite work. Host-held session lifetime and arbitrary blocking/native interruption remain outside the claim. QA is assigned the independent intent check. Canonical qualification retry and independent delivery review remain pending.

- 2026-10-27: Readiness approved on receipt 11674a20e7268e7df8c7. Standard red-team primer, fixed architecture/security/QA/reality seats and rotating docs-contract seat all ran with no findings; required code/QA/architecture/docs lanes approved independently. Anonymous-first synthesis unanimous; red-team closing held empty findings. Strongest challenge: preserve timeout retry ownership before module reload. Diagnostics-only alternative leaves cleanup gaps. Intent fit establishes.

- 2026-10-27: Operator requested planning, prepare, review and implementation of the proposed lifecycle improvements; product-owner acknowledgment is the explicit instruction. No closure or commit authorized.
- Work allocation: coordinator implements the narrow coupled runner/handler change. Fresh independent council and reviewer contexts use gpt-6.1-sol at high reasoning for concurrency/cleanup and protocol judgment; requested settings are recorded, runtime identity unverified. Disposable work: `.wavefoundry/work/21uny/`.

2026-10-27: Intent outcome: achieved for the admitted lifecycle contract. The final 12,281-test canonical run and independent delivery checks establish process diagnostics, current-handler shutdown, reversible monitor preparation, refusal without disposal when preparation fails, and successful reload after callbacks drain. Operator restarted the host; live MCP PID 73407 is owned by new daemon 72745, loaded runner and implementation match disk, both monitors are alive, and previous daemon 39568/MCP 40330 are absent. Native Windows/Linux/WSL execution, arbitrary foreground/native quiescence and rollback after destructive cleanup remain outside the verified claim. All seven ACs and all tasks are complete; no intentional AC deferrals.

2026-10-27: Closure retrospective: keep the monitor admission pause separate from destructive resource cleanup, and assert service health after every reload in lifecycle fixtures. These lessons already live in maintained tests, the MCP contract and architecture documentation; no additional memory is warranted. memory_propose dry-run returned zero candidates. Unique probe recipes and reviewed fingerprints are retained in the change/wave records and typed ledger; routine work-area logs and controls are disposable and eligible for the close tool's owned cleanup. Gapfill: direct Markdown editing used only for closure narration; no code investigation or source edit.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 130 | 1,741,118 |
| implement | 91 | 1,518,326 |
| review | 583 | 1,804,457 |
| **Total** | **804** | **5,063,901** |

<!-- wave:context-efficiency-state {"generation":674,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":91,"content_source_credit":1677750,"derived_artifact_credit":0,"direct_net":1518326,"estimated_tokens_saved":1518326,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2843,"response_debit":163393,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6812},"plan":{"calls":130,"content_source_credit":2110695,"derived_artifact_credit":2627,"direct_net":1741118,"estimated_tokens_saved":1741118,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7711,"response_debit":376812,"source_credit_count":72,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12319},"review":{"calls":583,"content_source_credit":3679161,"derived_artifact_credit":7364,"direct_net":1804457,"estimated_tokens_saved":1804457,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":39290,"response_debit":1846467,"source_credit_count":161,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":804,"content_source_credit":7467606,"derived_artifact_credit":9991,"direct_net":5063901,"estimated_tokens_saved":5063901,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":49844,"response_debit":2386672,"source_credit_count":258,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":22820},"wave_id":"21uny mcp-lifecycle-reliability"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 32 | 0 | 9 | 25,265,276 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":25265276,"surfaced_events":32} -->
<!-- wave:exploration-avoided end -->
