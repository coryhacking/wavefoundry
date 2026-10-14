# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20nju optional-tensorwell-inference`
Title: Optional Tensorwell Inference

## Objective

Prefer an installed, compatible Tensorwell service for the pinned embedding and reranking models, and start the configured service in the background when MCP starts and it is stopped. Keep MCP responsive and retain local inference when the service is unavailable or incompatible, without changing model identity or index compatibility.

## Changes

Change ID: `20njt-enh optional-tensorwell-inference`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (after readiness)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-10-14

## Wave Summary

Wave `20nju` (Optional Tensorwell Inference) delivered one change: Optional Tensorwell inference with bounded service startup.

**Changes delivered:**

- **Optional Tensorwell inference with bounded service startup** (`20njt-enh optional-tensorwell-inference`) — 8 ACs completed. Key decisions: Optional service with background startup and local fallback; Narrow qualified immutable-identity table
## Watchpoints

- Implementation and required reviews are complete; the wave awaits operator-owned closure. The installed service was reused for synthetic native parity without starting, restarting or stopping it. Both edit gates are closed.
- Same pinned manifest is necessary but insufficient: qualify full profile identities and numerical behavior before admitting a backend. Query prefixes must be applied exactly once.
- Auto-start is background and bounded, macOS managed service first; never install, configure, replace or stop a shared service. Verify client cancellation cannot trigger destructive management cleanup.
- Keep CPU/provider overrides, recorded index precision and local fallback; unknown identities remain local. No Tensorwell code edits are admitted.
- Timing assessment remains deferred while other work runs. Keep durable conclusions here and in tests/docs; no permanent evidence folder.

## Current assumptions

- Optional automatic selection and automatic start implement the operator's request; an explicit opt-out covers operators who prefer local inference.
- First version requires both supported model capabilities. Partial profiles, unsupported platforms and unknown runtime identities retain local behavior.
- Full identity qualification and exact numerical tolerances are implementation tasks, not claims made by the initial matching-manifest observation.

## Outputs produced or expected

- Optional client/adapters, bounded serving-startup integration, cached status diagnostics, canonical regression tests, reusable native parity oracle and operator/architecture documentation. All eight required ACs and six tasks are complete; none is deferred.

## Review checkpoints

- Readiness PASS on receipt `review-policy-0dc2f577b64430357fa5`: full isolated red-team primer; architecture, security, QA and reality-checker fixed seats; performance rotating seat; supplemental code and docs-contract reviews. One controller-lifetime finding was repaired by specifying exact owned-child cancellation/reaping and qualified controller eligibility. Fresh focused performance/security verification cleared it; all required lanes reviewed the narrow delta and the chair recorded unanimous approval. Native inference and delivered code were not claimed by readiness.
- Current readiness receipt `review-policy-d1e9a7e01117aff3aba9` preserves that plan after an effects-only refresh for the canonical handoff pointer. No requirement, authority, AC or review-target change was introduced by the bookkeeping repair.
- Initial delivery council: full isolated primer; architecture, security, QA and reality fixed seats, performance rotating seat. Architecture also served the code remit in the same actual context; reality also served docs-contract in the same context. The chair weighed anonymized findings before restoring identities. Unanimous needs-revision, maximum severity medium: reload state, float32 representability, builtin registration, timeout inventory and two fixture prerequisites. All six had typed repair starts before the single repair batch. The batch-local sizing alternative remained advisory: no production stall or measured benefit justified changing failure ordering. No security authority delta or timing diagnosis was claimed.
- Repair qualification: 381 focused tests across seven files, both reranker fixture cases, final 20 client tests and 14 named guard mutants passed/detected. Fresh code/architecture, QA and docs/security contexts independently cleared the six findings; combined remits are disclosed as shared contexts, not separate reviewers. Code/architecture executed 16 baseline checks and 17 detected controls; QA executed 17 baseline checks and 17 detected controls; docs/security executed six baseline checks and three detected controls. The final focused council/performance effects check used one additional fresh independent context, three passing checks and a detected stale-generation control; it consumed the original council and fresh repair evidence without inventing another fixed-seat vote.
- Final qualification PASS: 12,499 tests across 187 files, 12 reported skips, exit 0. Green receipt `3eb074fae2e3949e83124ea7d50b89dcdb1ea01e83d432b3c82ae819141655ff`; all 29 reviewed Git blobs match `c54a85bb62e75375a2ad672f2a85e00a8a5de03008a48da0e7b76c30f0192131`. All seven required delivery approvals are recorded and every finding is terminal. The two earlier TechDocs failures passed unchanged; no causal timing conclusion or threshold change is claimed. Temporary review/test artifacts are outside the repository; durable outcomes and named regressions remain here, in the admitted change and canonical tests.
- Native synthetic qualification reused the running matching service: minimum embedding cosine `0.999840498` against the predeclared `0.999` floor; maximum raw-logit delta `0.008549214` below `0.05`; top-1 and all 63 comparisons with reference margins above `0.10` preserved. Repeated and singleton/batch controls passed. The checked-in parity oracle and canonical regression tests retain the proof mechanism; temporary captures stay outside the repository. Native service lifecycle, physical GPU execution, speed and other platform profiles were not qualified.
- Prepare wave and independent readiness council before source edits.
- Delivery reviews focus on compatibility, query roles, shared-service ownership, bounded failure and index publication integrity.
- Product-owner acknowledgment: the operator approved proceeding with this planned optional integration through “prepare, review, and implement”; compatibility and non-disruptive service ownership remain the acceptance boundary.
- Work allocation: one implementer owns source and tests; the coordinator owns docs, native qualification and integration checks. Independent chairs and isolated reviewers use requested gpt-6.1-sol/high, with a frontier/high initial security seat for trust/process boundaries. A separate discovery worker independently derived model identities. Requested settings are known; worker runtime identity is not exposed. Reports stay temporary; only outcomes belong here.

## Completion criteria

- Admitted change ACs/tasks reconciled with change-local evidence, required reviews complete and normal qualification gates satisfied.
- Closure remains operator-owned.

## Handoff or next-wave notes

Implementation, independent required reviews and canonical qualification are complete. Operator authorized closure and commit on 2026-10-14. No external Tensorwell change is required; unsupported contracts fall back locally. Coordinate separately before any disruptive live-service test.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 20nju-qa-env-json-lifespan | do_now | no | completed | qa-reviewer, code-reviewer |
| 20nju-qa-reranker-optout-fixtures | do_now | no | completed | qa-reviewer, code-reviewer |
| PERF-STARTUP-CONTROLLER | do_now | no | completed | performance-reviewer, security-reviewer, architecture-reviewer, code-reviewer, qa-reviewer, docs-contract-reviewer, council-readiness |
| TENSORWELL-BUILTIN-REGISTRY | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, council-delivery |
| TENSORWELL-CLI-TIMEOUT-INVENTORY | do_now | no | completed | code-reviewer, qa-reviewer, council-delivery |
| TENSORWELL-FLOAT32-FINITE | do_now | no | completed | code-reviewer, qa-reviewer, council-delivery, docs-contract-reviewer |
| TENSORWELL-RELOAD-CLOSURE | do_now | no | completed | architecture-reviewer, code-reviewer, qa-reviewer, council-delivery |

*Machine review state — 7 findings; current: do_now 7, maybe_later 0, dont_do_later 0, not_issue 0*
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
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: explicit closure and commit instruction received 2026-10-14.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

- Closure reconciliation: all eight ACs and six tasks complete; no intentionally deferred ACs. Docs-contract review was performed and approved for the changed MCP spec. Operator authorized closure and commit on 2026-10-14.
- Retrospective/memory: full model identity and numerical parity, exact owned-controller cancellation, and reload-state preservation are retained in canonical architecture/threat-model docs and named regression tests. The dry-run proposed no eligible memory; no additional record is needed.
- Cleanup: only wave.md, the admitted change and authoritative events.jsonl are retained. Raw qualification and reviewer output stays temporary; no disposable wave-folder evidence exists.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 216 | 3,875,840 |
| implement | 48 | 288,389 |
| review | 623 | 5,288,696 |
| **Total** | **887** | **9,452,925** |

<!-- wave:context-efficiency-state {"generation":724,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":48,"content_source_credit":315074,"derived_artifact_credit":0,"direct_net":288389,"estimated_tokens_saved":288389,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1411,"response_debit":29172,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3898},"plan":{"calls":216,"content_source_credit":4549695,"derived_artifact_credit":2553,"direct_net":3875840,"estimated_tokens_saved":3875840,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16800,"response_debit":666111,"source_credit_count":153,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6503},"review":{"calls":623,"content_source_credit":6779546,"derived_artifact_credit":2721,"direct_net":5288696,"estimated_tokens_saved":5288696,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":98201,"response_debit":1398301,"source_credit_count":244,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":887,"content_source_credit":11644315,"derived_artifact_credit":5274,"direct_net":9452925,"estimated_tokens_saved":9452925,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":116412,"response_debit":2093584,"source_credit_count":413,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13332},"wave_id":"20nju optional-tensorwell-inference"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 51 | 0 | 32 | 23,290,951 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":32,"estimated_exploration_avoided":23290951,"surfaced_events":51} -->
<!-- wave:exploration-avoided end -->
