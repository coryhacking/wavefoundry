# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22qky distribution-scan-delivery-followup`
Title: Report recovery, partial delivery and scan completion accurately

## Objective

Operators and downstream distributions receive executable recovery advice for the selected repository, visible partial skill delivery, and scanner results that distinguish completed coverage from failed work. Upgrades expose incompatible project rules before publication; concise documentation explains rescan noise, synthetic fixtures and retained provenance. Ordinary Git changes do not automatically require setup, unrelated skills remain available, and no upstream release is a prerequisite.

## Changes

Change ID: `22q2u-bug selected-root-health-recovery`
Change Status: `implemented`

Change ID: `22q2v-bug structured-partial-skill-delivery`
Change Status: `implemented`

Change ID: `22q2w-bug scan-completion-upgrade-compatibility`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer; coordinator owns shared documentation and integration.
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-11-06

## Wave Summary

Wave `22qky` (Report recovery, partial delivery and scan completion accurately) delivered 3 changes: Keep health recovery on the selected repository, Report partial skill delivery to structured callers, and Report incomplete secret scans and incompatible upgrades. Notable adjustments during implementation: Report partial skill delivery to structured callers: Implemented structured manifests, sync advisory and upgrade checkpoint/summary propagation. Real child rendering with console output erased still exposes the collision; renamed declarations clear it and failed rerenders reset stale observations. Bounded MCP test retains the flag for 2,000 collision records and reports omitted counts. Legacy/malformed manifests remain unknown.; Report partial skill delivery to structured callers: Known-bad control removed partial_skill_delivery from the actual child manifest; the public sync assertion failed as expected. No source mutation or test skip was used.; Report incomplete secret scans and incompatible upgrades: Delivery repair cycle 1: both cache producers evict prior rows for failed or unpublished attempts and retry persisted incomplete paths before cache filtering and the indexer no-work shortcut. Current exclusions and removals remain scanner-owned; no new ledger or automatic full scan was added.

Intent outcome: achieved in the focused controls for all three changes and the wave Objective. Public recovery identifies the selected root without automatic setup; actual rendering and persisted upgrade reporting retain partial skill delivery; eligible scanner failures persist and incoming-profile validation refuses incompatible publication. Equivalent example patterns preserve detection controls while removing literal key shapes. After two repair cycles, the full default suite (12,516 tests) and the renamed and declared profiles pass, and independent code, QA, architecture, security, docs-contract, release and Council delivery reviews approve; Council intent fit is partially, for the Objective's downstream and native-platform limits. External GitHub/Wiz/Veracode alert reduction, native Windows execution and old-runner retroactive protection are not established.

**Changes delivered:**

- **Keep health recovery on the selected repository** (`22q2u-bug selected-root-health-recovery`) — 4 ACs completed. Key decisions: Reuse `setup_recovery` at context-owning response boundaries; lower-level errors without a root stay prose-only.; Preserve current readiness input policy, including source-only same-VERSION limitation.
- **Report partial skill delivery to structured callers** (`22q2v-bug structured-partial-skill-delivery`) — 4 ACs completed. Key decisions: Extend the existing result and summary contracts additively; retain successful partial rendering.
- **Report incomplete secret scans and incompatible upgrades** (`22q2w-bug scan-completion-upgrade-compatibility`) — 6 ACs completed. Key decisions: Extend existing per-file outcomes and skip authority into explicit completion enforcement.; Validate incoming merged configuration before publication; refuse unsupported semantics with instructions.
## Watchpoints

- Watchpoint: preserve existing unrelated edits to VERSION, README.md, docs/index.md, the prompt manifest and the overview. No blanket fixture/evidence exclusions or silent legacy-filter conversion.
- Serialize shared writes to upgrade_wavefoundry.py, wf_server/docs_handlers.py and shared tests; merge through the coordinator. Temporary probes and reviewer packets belong in `.wavefoundry/work/22qky/`.
- Work allocation: separate bounded recovery, skill-reporting and scanner planning/implementation assignments; shared documentation and integration stay with the coordinator. Inherited model settings are used for these closely grounded tasks; actual runtime identity is unverified. Independent required review uses fresh role contexts, not implementer self-review.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 22qky-qa-stale-clean-cache-blocks-retry | do_now | no | completed | qa-reviewer |
| 22qky-scanner-upgrade-bytecode-bootstrap | do_now | no | completed | code-reviewer, architecture-reviewer |
| 22qky-security-malformed-rule-id-disclosure | do_now | no | completed | security-reviewer |
| 22qky-suite-contract-fixtures | do_now | no | completed | qa-reviewer |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
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

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-06: Intent outcome: achieved in the focused controls for all three changes and the wave Objective. Public recovery identifies the selected root without automatic setup; actual rendering and persisted upgrade reporting retain partial skill delivery; eligible scanner failures persist and incoming-profile validation refuses incompatible publication. Equivalent example patterns preserve detection controls while removing literal key shapes. After two repair cycles, the full default suite (12,516 tests) and the renamed and declared profiles pass, and independent code, QA, architecture, security, docs-contract, release and Council delivery reviews approve; Council intent fit is partially, for the Objective's downstream and native-platform limits. External GitHub/Wiz/Veracode alert reduction, native Windows execution and old-runner retroactive protection are not established.

### Readiness — 2026-11-06

Council verdict: ready; intent fit **establishes** for all three changes and the wave Objective, prospectively. Current receipt: `review-policy-63d387d4eb5b7dcc4bfe`. No readiness findings or repair round were required. Agreement was unanimous; maximum finding severity was none. This approves the plans, not the unimplemented behavior.

The chair declared full primer depth because scan enforcement and upgrade publication cross trust boundaries. An isolated red-team primer applied all five stances. Fixed seats formed artifact-only reads before receiving it. Architecture and code shared one disclosed context; QA, security, reality-checker, rotating docs-contract and the additional release lane used separate contexts. Runtime model identities were unverified; separate contexts do not establish model diversity.

| Seat | Independent read, primer effect and result |
| --- | --- |
| Architecture and code | Existing response, rendering and coverage owners fit the work. The primer sharpened incomplete-without-skip persistence; actual scanner/persistence controls reproduced the admitted defect. No findings in either lane. |
| QA | Required ACs cover intended outcomes; helper-only assertions would be insufficient. The primer extended that concern to legacy missing fields. A real platform-render invocation preserved unrelated delivery but omitted structured partial status, which the proposed assertion rejected. No findings. |
| Security | Bounded diagnostics and incoming validation must preserve authority. The primer extended the empty/absent-state cases. Actual worker-backed parsing distinguished legacy acceptance from incoming rejection without leaking a private sentinel or changing policy bytes. No findings. |
| Reality-checker | Persistent outcomes and publication ordering are the consequential assumptions. The primer sharpened a source-confirmed empty-outcome loss. Every required AC has a feasible observable contract; no intent gap or finding. |
| Docs-contract, rotating | The contracts distinguish recovery from authorization, partial delivery from failure, and incomplete scanning from exclusions. Actual TOML/Expr/CEL/regex controls preserved all 48 original-example cases and a non-allowlisted positive; an overbroad allowlist mutant failed all three controls. No findings. |
| Release | Supported publication routes, older-runner limits and retained notices are explicit. Actual merged-rule loading accepted absent/allowlist-only policy and rejected an incompatible global filter without writes. No findings. |

The first synthesis weighed anonymized outputs in the order release, reality, QA, docs, architecture/code, security before restoring identities. Shared-primer concerns were treated as correlated, not independent confirmation. No verbatim pre-primer contamination was identified. Red-team closing reconciliation found no missing-scope or intent defect in the sealed empty finding set.

| Recommendation | Decision and reason |
| --- | --- |
| Make a skill collision fatal or atomic | Declined after every fixed seat weighed it: simpler binary consumers would come at the cost of unrelated skill delivery. Keep explicit partial state through persistence and bounded responses. |
| Run a full scan on every close | Declined: repeated work does not remove the need to distinguish incomplete scanning. Preserve incremental operation and unresolved failure history. |
| Verify consumers and state transitions | Retained implementation note: exercise cleanup/resume, truncation, incoming-versus-installed validation, retained publication, and incomplete results with no skip rows. No new plan requirement. |

The measures remain observable after delivery: selected-root response fields (22q2u AC-1–3), manifest/sync/upgrade partial state and reset (22q2v AC-1–4), and completion, enforcement, preflight refusal and migration controls (22q2w AC-1–6). External alert reduction is not an outcome claimed by AC-5. Existing eligible guard failures must remain visible until proven complete, removed or explicitly excluded under current policy; no blanket vendor/evidence exemption was approved.

### Falsification Check

Ready remains the verdict. The strongest contrary argument is that correct sampled producers can still lose state at consumer/publication boundaries; the plans expressly require those delivery checks. Readiness probes establish feasibility only, not exhaustive coverage, native Windows behavior, external-scanner effectiveness or a passing full suite. Typed approvals in `events.jsonl` carry the actual bounded observations and limits.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 246 | 3,690,244 |
| implement | 478 | 4,018,200 |
| review | 156 | 1,538,892 |
| **Total** | **880** | **9,247,336** |

<!-- wave:context-efficiency-state {"generation":695,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":478,"content_source_credit":5023300,"derived_artifact_credit":0,"direct_net":4018200,"estimated_tokens_saved":4018200,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19809,"response_debit":991177,"source_credit_count":185,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5886},"plan":{"calls":246,"content_source_credit":4231032,"derived_artifact_credit":5426,"direct_net":3690244,"estimated_tokens_saved":3690244,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11039,"response_debit":540683,"source_credit_count":145,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5508},"review":{"calls":156,"content_source_credit":1951599,"derived_artifact_credit":9912,"direct_net":1538892,"estimated_tokens_saved":1538892,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":49419,"response_debit":376978,"source_credit_count":94,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":880,"content_source_credit":11205931,"derived_artifact_credit":15338,"direct_net":9247336,"estimated_tokens_saved":9247336,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":80267,"response_debit":1908838,"source_credit_count":424,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15172},"wave_id":"22qky distribution-scan-delivery-followup"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 47 | 0 | 29 | 21,136,280 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":29,"estimated_exploration_avoided":21136280,"surfaced_events":47} -->
<!-- wave:exploration-avoided end -->
