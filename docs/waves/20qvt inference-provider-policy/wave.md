# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20qvt inference-provider-policy`
Title: Framework Inference Provider Selection and Adapters

## Objective

Keep Tensorwell automatic by default and let downstream distributions disable or replace it through a framework declaration and a narrow enterprise inference adapter contract. Preserve lazy local model loading and reuse compatibility and provider reporting.

## Changes

Change ID: `20qvu-enh repository-inference-policy`
Change Status: `implemented`

## Participants

- Coordinator: Coordinator
- Write-owning roles: Implementer after readiness; coordinator owns lifecycle records
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-15

## Wave Summary

Wave `20qvt` (Framework Inference Provider Selection and Adapters) delivered one change: Declare framework inference providers and downstream API adapters.

**Changes delivered:**

- **Declare framework inference providers and downstream API adapters** (`20qvu-enh repository-inference-policy`) — 5 ACs completed. Key decisions: Keep Tensorwell automatic by default; declare selection at framework/distribution level; Add a narrow adapter seam for downstream enterprise APIs
## Watchpoints

- Implementation source and focused qualification complete; aggregate suite and independent delivery review pending. Preserve publication/recovery guards and private intake boundaries. Timing investigation stays deferred.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QVT-RD1 | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, council-readiness |

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
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: pending

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 95 | 1,611,477 |
| implement | 15 | 439 |
| review | 190 | 3,694,188 |
| **Total** | **300** | **5,306,104** |

<!-- wave:context-efficiency-state {"generation":315,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":15,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":439,"estimated_tokens_saved":439,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":533,"response_debit":2220,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3192},"plan":{"calls":95,"content_source_credit":1771066,"derived_artifact_credit":2830,"direct_net":1611477,"estimated_tokens_saved":1611477,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":23195,"response_debit":143029,"source_credit_count":66,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":190,"content_source_credit":4208592,"derived_artifact_credit":0,"direct_net":3694188,"estimated_tokens_saved":3694188,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6614,"response_debit":510857,"source_credit_count":131,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3067}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":300,"content_source_credit":5979658,"derived_artifact_credit":2830,"direct_net":5306104,"estimated_tokens_saved":5306104,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":30342,"response_debit":656106,"source_credit_count":197,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10064},"wave_id":"20qvt inference-provider-policy"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 29 | 0 | 25 | 11,810,665 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":25,"estimated_exploration_avoided":11810665,"surfaced_events":29} -->
<!-- wave:exploration-avoided end -->
## Current assumptions

Four cohesive waves avoid a single large approval boundary and the overhead of one wave per small item. Shared framework files are implemented serially; planning does not open an implementation slot.

## Outputs produced or expected

Admitted change plans, focused regression coverage, updated canonical guidance and a concise durable result in this wave record. No permanent raw probe/evidence folders are planned.

## Review checkpoints

Delivery council: full-depth isolated adversarial primer, fixed architecture/security/QA/reality seats, rotating combined code/docs seat and independent chair; merit comparison favored the admitted trusted-adapter facade over a new external-process cancellation layer. Verdict unanimous, no findings within the synthetic-provider scope. Code and docs lanes share a disclosed context; each seat reviewed both current waves. All required delivery approvals are recorded. Root's aggregate suite is separate and currently not green.

Executed controls include registered reload, CPU/full index publication and INT8 refusal, raw query roles, raw reranker logits and memory cutoff, malformed responses, deadline overrun, generation/cache invalidation, and no explicit-provider fallback. Independent response-descriptor, sigmoid-score, generation and deadline mutants failed expected assertions. Durable tests: `.wavefoundry/framework/scripts/tests/test_inference_provider.py` (`ProviderTests`, `RegisteredProviderTests`). All 52 reviewed source-path hashes stayed unchanged during the round. No live enterprise service/model/hardware qualification or exhaustive consumer census is claimed. One additional held-adapter custom fixture hit disk exhaustion; separate generation rejection and registered reload controls passed, and selected registered-preview coverage was completed by another seat. Raw output remains outside the repository.

Prepare verifies decisions and exact affected surfaces before implementation. Delivery checks registered behavior, negative controls and compatibility. Reuse valid framework qualification; consolidate a necessary suite run after code changes settle rather than repeating it for bookkeeping.

## Completion criteria

Every admitted AC and task is reconciled with evidence, required delivery lanes approve, documentation validates and the operator authorizes closure.

## Handoff or next-wave notes

Readied and implemented; aggregate full-suite qualification and independent delivery review remain pending. Coordinator may pause this wave before opening the next admitted wave. No closure, commit or release is authorized.

## Scope decision — 2026-10-15

Provider selection belongs to the framework/distribution, not target repositories. Tensorwell remains automatic by default. Downstream can disable it or implement its own enterprise API adapter. No particular enterprise service or live network integration is included; a synthetic adapter proves the extension contract. Wave 20qvq owns compatibility; this wave owns selection, dispatch, startup and reporting.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Implemented AC-1–5: distribution profile/facade, all existing inference consumers, CPU/full publication compatibility, bounded safe adapter contract, cached selection, provider telemetry, exact-source routing reload and declared helper provenance. Nine synthetic adapter tests pass; Tensorwell integration 23, extension inventory 229, reload closure 15, setup readiness 49, readiness integration 20 and package seams 31 pass. Full suite and independent delivery review remain coordinator-owned and pending. | test_inference_provider.py; /private/tmp/qvt-provider-final.log, qvt-tensorwell-final.log, qvt-extensions.log, qvt-structure-final.log, qvt-readiness.log, qvt-readiness-integration.log, qvt-package-seams.log |
| 2026-10-15 | Guard mutation evidence: eight isolated source mutants each caused a named test failure, not an incidental import error. Response descriptor, cardinality, vector dimension, finite-number and completion-deadline guards: test_response_guards_and_timeout_are_safe_no_retry. Stored-precision guard: test_explicit_selection_never_falls_back_for_partial_or_incompatible. Helper-declaration and stale-generation guards: test_selection_cache_and_generation_invalidation. | /private/tmp/qvt-mutants.log; mutants run on temporary copies only |
| 2026-10-15 | Qualification limits: synthetic transports only; no live enterprise/Tensorwell endpoint, native model/hardware, credentials, model downloads or performance qualification. Trusted adapters must enforce transport deadlines; Python code is not sandboxed. Model pins stay bound to the loaded index runtime; profile/facade reload executes exact bytes and refreshes only matching pre/post source hashes. No close, commit, push or package build. | Registered pre/post index_health stale-code check and profile/helper reload fixture; required delivery task remains open |
| 2026-10-15 | Operator authorized Prepare, review and implementation; closure/commit/release remain unrequested. Coordinator integrates serial source changes; independent role contexts review. Inherited capable model chosen for cross-module reasoning; actual runtime model/effort not exposed. | Current task; canonical lifecycle prompts |

Memory retrospective: proposal preview found no eligible durable draft; provider decisions and controls remain in this wave and its change document.

## Final qualification

2026-10-15: canonical `run_tests.py` passed 11,731 tests across 189 files, with 12 skips, in 796.576 seconds. Fresh green receipt recorded after all source repairs and review-record writes settled; no repository writes during the run. Earlier census failures are repaired, and previously failing or timed-out files passed. Full docs validation passed before qualification. Required delivery reviews approve; wave remains paused for operator closure. No close, commit, push, package or release performed. Timing investigation remains deferred; no threshold or waiver changed.

Closure reconciliation (2026-10-15): operator authorized closure, commit and push; close verified current green qualification and required review authority. No package or release requested. Only wave.md, admitted change documents and authoritative events.jsonl are retained in this wave folder; no disposable evidence artifacts were present. Prior paused/pending notes above describe earlier checkpoints.
