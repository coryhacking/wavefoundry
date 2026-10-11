# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20b3b upgrade-resilience`
Title: Upgrade Resilience

## Objective

Stop an upgrade from failing late or hanging on known field conditions: detect a customized legacy review-plan prompt before framework/operating-document/checkpoint mutation, resume rather than re-run the full upgrade at the index guard, disable and bound the xet model download, and keep a store permission error from poisoning context-efficiency accounting.

## Changes

Change ID: `20b35-bug review-plan-prompt-migration-preflight`
Change Status: `implemented`

Change ID: `20b36-bug index-guard-handoff-resume-not-full-upgrade`
Change Status: `implemented`

Change ID: `20b37-bug hf-xet-download-hang-and-unbounded-downloads`
Change Status: `implemented`

Change ID: `20b38-bug context-efficiency-flush-permission-poisons-store`
Change Status: `implemented`

## Participants

- Coordinator: council-chair
- Write-owning roles: implementer (the only write-owning lane; every reviewer lane is read-only)
- Requested review lanes: security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-10

## Wave Summary

Wave `20b3b` (Upgrade Resilience) delivered 4 changes: Review-Plan Prompt Migration Is Detected In Preflight, Not After Mutation, Index-Guard Handoff Resumes The Upgrade Instead Of Re-Running It, Embedding Model Downloads Cannot Hang: Disable Xet By Default And Bound Every Download Path, and Context-Efficiency Flush Defers Its Transfer Instead Of Poisoning The Store. Notable adjustments during implementation: Review-Plan Prompt Migration Is Detected In Preflight, Not After Mutation: Readiness repair: old-code-window question settled in favor of the incoming-pack extension seam; scope extended to the pre-profile refusals.; Review-Plan Prompt Migration Is Detected In Preflight, Not After Mutation: Confirming-round repair: the hook is a self-contained standard-library-only checker (the renderer cannot be loaded from the zip); lock release made a required wrapper; dry-run-style return dropped; limits stated; module registration and architecture docs made mandatory. Product Intent: waived (bug fix, no product scope).; Index-Guard Handoff Resumes The Upgrade Instead Of Re-Running It: Readiness repair: the full path is verified to re-render after `_tree_already_at`; mapping table, rebuild fallback and single decision point added.

**Changes delivered:**

- **Review-Plan Prompt Migration Is Detected In Preflight, Not After Mutation** (`20b35-bug review-plan-prompt-migration-preflight`) — 10 ACs completed. Key decisions: Divergent pre-plan. Approach A: factor a read-only check in the installed renderer and call it from preflight with `getattr` tolerance. Approach B: load the incoming pack's renderer and run its check before extraction. Approach C: only improve the Phase 1 message and docs. Approach D: a self-contained standard-library-only checker module shared with the migration and run from the incoming `post_preflight` hook. SELECTED D, with A kept as the new-runner path only.
- **Index-Guard Handoff Resumes The Upgrade Instead Of Re-Running It** (`20b36-bug index-guard-handoff-resume-not-full-upgrade`) — 14 ACs completed. Key decisions: Divergent pre-plan. Approach A: select a resume flag from recorded state at the guard's call site. Approach B: keep the full form but make the full path skip rendering and the docs gate when the tree is already at target. Approach C: only document the manual resume. Selected A, deciding at `upgrade_extensions.py:851` by consuming the `20b34` resume helper.; Delete the `--resume-after-gate` row.
- **Embedding Model Downloads Cannot Hang: Disable Xet By Default And Bound Every Download Path** (`20b37-bug hf-xet-download-hang-and-unbounded-downloads`) — 10 ACs completed. Key decisions: Divergent pre-plan. Approach A: default-disable xet and add deadlines to the unbounded helpers. Approach B: deadlines only, leave xet enabled. Approach C: pre-download the model in a separate bounded step before long index phases. Selected A, delivered by both an early environment default and a scoped constant patch, wrapping only the online branch of all three routes.; Operator selected the same deadline for all three online routes, including direct CPU/indexer; require worker-owned in-flight suppression and deadline propagation.
- **Context-Efficiency Flush Defers Its Transfer Instead Of Poisoning The Store** (`20b38-bug context-efficiency-flush-permission-poisons-store`) — 12 ACs completed. Key decisions: Divergent pre-plan. Approach A: classify retryable errors in `flush` and defer the transfer without a marker. Approach B: stop upgrade and reload from blocking on a gap marker. Approach C: add an MCP tool to clear the gap. Approach D (rejected during readiness): give `flush` the spool fallback of `_commit_event`. Selected A.; Widen `_with_busy_retry` with an optional classification parameter (default unchanged) rather than adding a second retry loop, and keep two classification paths deliberately.
## Watchpoints

- Watchpoint, precondition on every change: `20b3a upgrade-failure-surfacing` must be implemented, fully delivery-reviewed and PAUSED under the operator-approved sequence before this wave is re-Prepared or implemented. No closure or commit is required/authorized. Re-derive all symbol/line anchors and consume the actual `20b34` helper contract against that source.
- Prepare-time checklist completed: the predecessor is delivery-reviewed and paused, and the amended plans passed refreshed typed readiness before activation. Historical readiness records remain below for context; current authority is receipt `review-policy-b56498e4f09f1ab21906`.
- Implementation boundaries: preserve the existing outer transaction cleanup instead of double-exiting; strict retained-pack ownership uses a bounded wrapper; the telemetry projection owner is `_flush_context_efficiency`, with actual carrier errors wrapped by `RuntimeFileLock.acquire` covered by tests.
- Hard code dependencies on `20b3a`: `20b35`'s early refusal is written to the upgrade log by the early log open of `20b33` (on rebase the log open must precede the `post_preflight` hook), and `20b36` consumes the CLI resume command helper that `20b34` introduces and adds nothing to `restart_command` (its second caller is `sqlite_storage_migration.py:900`).
- Dependency independence is not activation authority: all four changes still follow the operator sequence and root Stage Gate. Canonical framework source/test edits require applicable framework-edit authorization; protected seeds/templates remain read-only.
- Serialize `upgrade_wavefoundry.py` and `upgrade_extensions.py` after the predecessor, then `20b35` before `20b36`. The latter owns only one durable verified recovery slot and bounded resolver/cleanup changes. `20b37` precedes any required `20b38` delegating boundary hunk in `server_impl.py`; real instrumentation failure handling stays unchanged.
- `20b35` writes no `docs/prompts/` files; recovery prose goes in the Windows reference and CHANGELOG. Its checker is read-only, while authorized early diagnostics/runtime locks/staging are excluded from invariance. Register/ship its stdlib module without adding it to the mandatory old-runner protocol census. Security review is required for the guard/trust changes.
- The `20b35` refusal runs while the lifecycle publication transaction is held; preserve the predecessor's outer `main` release and test subprocess/in-process failures without double-exiting. The old runner in the field window relies on process exit.
- `20b35` limits, stated in the change: an old-runner `--dry-run` does not report the blocker, and runners older than the verified v1.15.4 tag get no early detection.
- Block on a stale `migration` module: `20b36` falls back to the full form whenever the `20b34` helper or argument is unavailable.
- Approved operator choices: `20b36` retains one contained ignored verified pack until terminal cleanup, keeping paused/failed authority; `20b37` applies the same configured deadline to the three identified online routes, including direct CPU/indexer, with worker-owned in-flight suppression. Read-only preflight found a fourth existing route in optional MCP background warm-up; the coordinator includes the same safeguard under the stated coverage assumption after the optional preference question received no answer. This adds no download pass or query-time network access and is not an additional operator decision.
- `20b38` classifies actual wrapped own-lease carrier errors without changing global runtime-lock semantics, and adds a non-fatal pending `deferred` result to actual transfer callers and the public MCP spec. Request docs-contract review alongside the existing required code/QA/architecture/release lanes; both additional specialists and the full fixed-seat Council are required at refreshed readiness/delivery.
- The Windows failures behind `20b37` and `20b38` were not reproduced off Windows; their root causes are inferred and recorded as such.
- Whether telemetry may block lifecycle operations at all (`20b38` rejected alternative B) is an operator decision, not part of this wave.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 20b36-retained-pack-terminal-cleanup-retry | do_now | no | completed | architecture-reviewer, code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer, council-readiness |
| QA-NUMERIC-DEADLINE | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, council-delivery |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
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

- operator-signoff: <approved when operator confirms closure>

## Review checkpoints

### Refreshed readiness allocation — 2026-10-10

Predecessor20b3a is fully implemented, delivery-reviewed and PAUSED; its12,196-test receipt matches the current framework tree. Prepare published receipt `review-policy-81b627da5e0f30881353` (digest `662c3250830071c0ffe46ffeb006b9af02109e987b2c93d6c859c670a261c99b`), with all six specialist approvals and Council pending on the amended plans. Gardening and full docs lint pass. This receipt does not yet authorize activation.

Risk-selected primer depth: full, for retained-pack authority, migration preflight, download-worker ownership and telemetry transfer semantics. Run an isolated five-stance adversarial primer, four independent fixed seats (architecture, security, QA, reality), then a rotating docs-contract seat and independent chair synthesis. Code shares architecture's context; release shares docs-contract's context, with correlated role judgments stated honestly. Request Astra/high for chair, primer and state/trust judgments; task-fit model selection for each seat follows seed180. Observed runtime identity is unknown. Review uses bounded feasibility controls and current live source reads; it does not repeat canonical qualification or claim future implementation. After one bounded plan repair and focused verification, any remaining blocker returns to the operator under the readiness workflow.

### Initial readiness synthesis and bounded repair — 2026-10-10

Full isolated five-stance primer, four fixed seats, rotating docs-contract/release review, anonymous merit synthesis, targeted factual challenge and red-team closing found one deduplicated blocker: `20b36-retained-pack-terminal-cleanup-retry`. Architecture, code, QA and docs-contract retain blocking authority. Seven bounded feasibility controls and 359 observed source/plan identities were unchanged; readiness reviews made no delivery or native-Windows claims. The typed readiness finding and implementer repair-start were recorded before the plan edit.

The single bounded repair changes Requirements 8/10 and AC-13: checkpoint-owned terminal cleanup state allows only finalization after deliberate archive removal, with nonzero checkpoint-deletion failure and fresh-process retry/interruption tests. Ordinary resume, malformed state and foreign/replaced files remain refused. Re-publish Prepare, then one focused verification covering original findings, exact repair diff and directly affected unchanged contracts; every required lane and Council must approve the current receipt. Any remaining blocker returns to the operator without another automatic readiness round.

Implementation notes from the unchanged download plan: the worker owns the constants scope and restores it in its `finally` after work exits, including after the parent reports timeout. Use the existing reload-retained canonical `setup_index` owner for the in-flight registry; pin public reload and same-model retry without inventing a new cache service or global isolation claim. The immediate-parent-restoration candidate was withdrawn after a concrete placement probe; it is not a second finding.

### Readied and activated — 2026-10-10

The single focused round cleared all four blocking lanes of the readiness finding. All six specialists and Council approved receipt `review-policy-b56498e4f09f1ab21906`; Prepare then passed and Implement Wave activated this wave. These are plan-readiness approvals, not delivery proof. Generic implementer lanes own two independent families: upgrade preflight/resume (`20b35` then `20b36`) and download/accounting (`20b37` then `20b38`); framework cross-cutting work fits this lane. Requested model is GPT-6.1-Sol/high for both implementations; actual runtime identity is unknown. Source baselines stay in temporary storage. Coordinator owns shared CHANGELOG, architecture data/control-flow integration and final qualification; no worker closes, commits, pushes or builds a pack.

### Implementation qualification boundary — 2026-10-10

All four changes are implemented and their source is frozen for qualification. Upgrade-family focused integration passed 191 tests with one existing native-runtime skip; two pinned MCP storage/index-guard fixtures also passed. Download/accounting final isolated checks passed 13 download, 98 transfer, 112 server-transfer and 75 registry/lifecycle tests; the 200-test setup and 407-test indexer suites passed. Twenty-nine named negative controls failed as intended and were restored. These focused results do not substitute for the canonical full suite or independent delivery approval. AC-12 of `20b38` and its combined docs-contract review task remain pending until that lane verifies the public contract. Working evidence stays in temporary storage; durable outcomes remain here and in the change documents.

Full docs lint passed with no errors or warnings before qualification. The isolated snapshot matches framework hash `5315b98da0040780c0160a089c80889a19c3b8b8cad6e81738e2f8cfe96b51e9`, with37 frozen review paths and185 test files. An initial diagnostic run used an absent temporary tool-venv override and failed test-process startup; it was interrupted and wrote no green receipt. Corrected launch checks use the existing installed interpreter and leave source unchanged. This incomplete run is not delivery evidence and grants no waiver.

The corrected launch exposed one new fixture missing its adjacent reasoned component classification. Repair added only that explanation; the complete test AST, literals, assertions, census and production bytes are unchanged. Fourteen focused tests pass, and the exact original fixture remains a failing known-bad control. The incomplete failed qualification is excluded. Final qualification runs on re-frozen hash `49b7e994e8726c59ad236633afd9f9c5019d9ce5dc2ba7bd42eddb47bfb5b2b7`, with the same37 review paths/185 files and no waiver. No source edit is permitted during this run or delivery review.

Qualification diagnostic — 2026-10-10: the complete default run on `49b7e994e8726c59ad236633afd9f9c5019d9ce5dc2ba7bd42eddb47bfb5b2b7` executed 12,257 tests across all 185 files in 1221.282 seconds, exit 1, with the exact 12 baseline skip IDs/reasons. Seven files failed: legacy telemetry metadata access; moved ONNX scope expectation; profile fixture literals; record/vocabulary message-owner classifications; the optional background helper's root-aware test double; and a retired prompt filename in recovery prose. This red report is temporary diagnostic evidence and produces no green receipt. One bounded implementation repair addresses those exact causes; assertions, census detection, deadline behavior, skip reasons and real accounting-gap barriers remain enforced. Independent delivery review has not started.

The combined repair passes 80 focused tests in 13.954 seconds, with no skips, and full docs validation passes without errors or warnings. Eleven additional scratch variants are rejected by named assertions and restored, including new/unlisted literals, the moved message owners, retired recovery reference, absent telemetry metadata, deleted ONNX disabling, dropped background root and stopped model continuation. Record/vocabulary census functions and assertions, the CLI guard, the memory test and all production download paths are unchanged by this pass. Re-freeze the integrated source and run fresh canonical qualification; focused results do not authorize delivery approval.

### Green qualification and delivery allocation — 2026-10-10

Fresh canonical default qualification passes 12,259 tests across all 185 files in 1212.835 seconds, exit 0, with the exact 12 baseline skip IDs/reasons. Framework hash `a72f719c84440c5513e64e9ad004e6e9630095edee888529a49497aea4f24a0b` and all 41 reviewed source/document identities match between the isolated checkout and this tree. Genuine receipt `2026-10-11T01:34:43.845316+00:00` was transferred byte-identically; SHA256 `27173fde8cba238cf5bc85e426fab8e172828d9ff917ce90d19b8e6026c90061`. Complete ignored execution report `.wavefoundry/cache/qualification/20b3b-default.json` SHA256 `e9ec9332a43f5cdff2bd8673edcdc52c99a3051a1f18274004e9901d8ccdc200`. No manually minted receipt, new skip or waiver. This is default qualification; native Windows and a new distribution archive are not claimed.

Full delivery review now uses a fresh read-only council-chair, isolated full five-stance primer, four fixed contexts (architecture/code, security, QA, reality), then rotating docs-contract/release and anonymous merit synthesis. Requested Astra/high for the chair's cross-boundary recovery/data judgment; each seat chooses task-fit settings per seed180, with actual runtime identity unknown unless exposed. Code/architecture and docs/release judgments share their respective contexts and are explicitly correlated. Each seat has a 900-second budget, targeted mutants and whole-file expansion only for survivors/new failures. No repeated canonical/profile/pack run; sources remain frozen. AC-12 of20b38 awaits actual docs-contract verification; operator signoff and closure remain reserved. Working reports stay in temporary storage, with final outcomes consolidated here.

### Initial delivery synthesis and numeric repair — 2026-10-10

The full delivery council completed all isolated seats, rotating docs-contract/release, independent alternative weighing, anonymous merit synthesis and closing red-team review. All 41 reviewed identities and the genuine qualification receipt/report matched. One merged finding, `QA-NUMERIC-DEADLINE`, is required by QA and docs-contract: a valid finite `1e20` model-timeout setting starts online work, then escapes as a platform wait overflow. Default and normal-timeout controls pass. Security and the scoped release-source inclusion check are approved; code, QA, architecture, docs-contract and Council await the repair. AC-12 of `20b38` and its combined docs-contract task are now verified and checked.

The typed initial delivery finding and implementer cycle-2 repair-start precede source edits. The selected bounded repair preserves finite configured durations with OS-representable wait slices sharing one original elapsed-time budget; nonfinite durations follow the existing invalid-value default before ownership or worker launch. Focused independent reverification and one fresh quiet canonical qualification will follow. No new scheduler, cancellation guarantee, permanent evidence folder or repeated profile/archive qualification is introduced. Operator signoff and closure remain reserved.

### Final delivery qualification — 2026-10-10

All 46 ACs and tasks are met. Both finding heads have completed repairs and no open blocking lanes; cycle 2 converged after independent QA and docs-contract reverification. All six specialist delivery approvals and Council delivery are current. Code and architecture share one explicitly correlated context; QA and docs-contract use separate fresh contexts. Operator signoff remains reserved. Operator signoff is now recorded; closure is authorized and the OPEN slot is released.

Fresh canonical default qualification passes 12,266 tests across 185 complete successful workers in 1207.635 seconds, exit 0, with the exact 12 unchanged baseline skip IDs and reasons. Both checkouts match framework hash `1b296ff8983a72a297a04f22e9f4b35dd68ccdeadfd392cc8f3dff32136b0640` and all 41 reviewed SHA256/Git-blob identities. The genuine runner receipt at `.wavefoundry/framework/test-cache.json`, dated `2026-10-11T02:29:32.596839+00:00`, was transferred byte-identically (SHA256 `9a7bcbbf36b40fec136b7a48c57016fc84be77b938cf54eb7ae8c528474af9ba`). The complete ignored report `.wavefoundry/cache/qualification/20b3b-default.json` has SHA256 `f277c8e7d0953eda49e9c7054ebc681a60f4cdf66fdddd0c714f9b9655bf6154`. This supersedes the earlier qualification checkpoints; no waiver or manually minted receipt was used.

The numeric repair passes 20 focused tests without skips. Independent QA, docs-contract and correlated code/architecture checks pass 14, 11 and 12 selected invocations respectively; these overlapping selections are not added to the canonical total. Original-source finite-timeout failures, overflowing wait slices and renewed-budget variants fail the intended assertions. Durable regression references are `.wavefoundry/framework/scripts/tests/test_model_download_deadline.py`, especially `test_accepted_finite_timeout_public_indexer_never_leaks_join_overflow`, `test_nonfinite_json_uses_default_before_ownership_and_worker`, `test_prewarm_models_preserves_actual_finite_default_and_normal_config`, `test_wait_slices_preserve_one_original_deadline` and `test_legacy_wait_slices_preserve_original_budget_and_timeout_object`. Council's own five selected controls and budget-reset negative control also pass after restoration. Final currency review verified the existing evidence and current receipt without rerunning tests or the full council.

Limits: default-profile source qualification only; native Windows incidents, physical reboot, actual network/model downloads, live index publication and a new release archive were not qualified. Native work cannot be cancelled; shared same-model ownership persists until worker exit. Legacy prewarm retains its earlier outer-scope restoration on timeout. No different-model global isolation or atomic final identity-check/unlink claim is made. Temporary review reports are not permanent repository evidence; durable results stay here, with typed events as authority. Framework gate is closed. No close, commit, push or new package was performed.

## Dependencies

- External wave dependency: wave `20b3a upgrade-failure-surfacing` is implemented, fully delivery-reviewed and PAUSED first (shared edits to `upgrade_wavefoundry.py` and `upgrade_extensions.py`; `20b36` reuses the helper `20b34` introduces; `20b35`'s refusal relies on `20b33`'s early log). Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 346 | 2,210,231 |
| implement | 170 | 654,027 |
| review | 877 | 4,836,170 |
| **Total** | **1,393** | **7,700,428** |

<!-- wave:context-efficiency-state {"generation":1078,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":170,"content_source_credit":762111,"derived_artifact_credit":0,"direct_net":654027,"estimated_tokens_saved":654027,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6910,"response_debit":113246,"source_credit_count":31,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12072},"plan":{"calls":346,"content_source_credit":3206321,"derived_artifact_credit":1804,"direct_net":2210231,"estimated_tokens_saved":2210231,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":52198,"response_debit":952199,"source_credit_count":141,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6503},"review":{"calls":877,"content_source_credit":7255401,"derived_artifact_credit":408,"direct_net":4836170,"estimated_tokens_saved":4836170,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":62202,"response_debit":2360293,"source_credit_count":269,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1393,"content_source_credit":11223833,"derived_artifact_credit":2212,"direct_net":7700428,"estimated_tokens_saved":7700428,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":121310,"response_debit":3425738,"source_credit_count":441,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":21431},"wave_id":"20b3b upgrade-resilience"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 62 | 0 | 34 | 25,583,633 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":34,"estimated_exploration_avoided":25583633,"surfaced_events":62} -->
<!-- wave:exploration-avoided end -->
