# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xxc9 monotonic-index-version-protection`
Title: Monotonic Index Version Protection

## Objective

Prevent stale processes from downgrading graph, semantic, lexical and chunker/walker index state after an upgrade. Preserve newer published data and return actionable restart guidance, including safe handling of already-loaded older hosts on the first protected release.

## Changes

Change ID: `1xwi1-bug prevent-stale-index-writer-downgrades`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (after readiness)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-09-12

## Wave Summary

Wave `1xxc9` (Monotonic Index Version Protection) delivered one change: Prevent stale processes from downgrading project indexes.

**Changes delivered:**

- **Prevent stale processes from downgrading project indexes** (`1xwi1-bug prevent-stale-index-writer-downgrades`) — 7 ACs completed. Key decisions: Select shared preflight plus transaction-bound compatibility fencing, with entrypoint diagnostics and upgrade handoff.; Keep first-hop old-host handling explicit.
## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-12: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer). Fresh current-plan/caller census approval supersedes the stale policy binding; re-Prepare passed.
- **Delivery council — 2026-09-12: PASS.** Same receipt-selected targeted roster. The strongest challenge was final commit ownership after preparation and preservation of first-hop host obligations on retries. Executed publication/upgrade probes resolved both. The single-publication-subprocess alternative adds orchestration and cannot retrofit old hosts; shared transaction fencing is proportionate. No material disagreement or blocking finding remained.
- Seven required specialist lanes approved: code, QA, architecture, docs-contract, release, performance and security. Paired/grouped lenses disclose shared actual fresh context; they are independent of implementation, not falsely counted as independent agents within each group. Exact evidence is in the typed ledger and consolidated report.
- Docs-contract review performed: canonical seed, local upgrade prompt, architecture, reliability and MCP recovery contracts align with executed behavior. QA verified every required AC; there are no `[~]` items.

## Closure reconciliation

1. All admitted changes are complete.
2. All seven required specialist delivery lanes are approved.
3. Current readiness and delivery council approvals are recorded through typed evidence.
4. Docs-contract review is performed and approved.
5. Change chronology is reconciled; the close tool owns the final wave status/date checkpoint.
6. Memory proposal completed: zero candidates, none pending validation.
7. Durable guidance already lives in canonical upgrade/architecture/reliability docs; no duplicate memory promoted.
8. Retrospective: final-owner checks matter after preparation; old hosts cannot learn newly installed guards; manual module registration exposes partial initialization. These lessons are retained in canonical guidance, regression tests and review evidence.
9. Session handoff records the closed-wave summary and preserves paused 1xtnr plus release follow-through.
10. Every AC and task is checked; no silent unchecked or deferred item remains.

## Watchpoints

- Watchpoint: do not treat opaque model or tokenizer identities as ordered numbers. Recheck compatibility inside publication, and do not claim new guards protect pre-existing loaded code.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Planning and readiness may proceed while 1xtnr is open. Activation requires its closure or an explicit pause; preserve its pending local-test work.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 84 | 1,052,106 |
| implement | 171 | 4,593,195 |
| review | 73 | 1,956,185 |
| **Total** | **328** | **7,601,486** |

<!-- wave:context-efficiency-state {"generation":254,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":171,"content_source_credit":4960674,"derived_artifact_credit":0,"direct_net":4593195,"estimated_tokens_saved":4593195,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5068,"response_debit":364580,"source_credit_count":82,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2169},"plan":{"calls":84,"content_source_credit":1238895,"derived_artifact_credit":2074,"direct_net":1052106,"estimated_tokens_saved":1052106,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6515,"response_debit":188044,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":73,"content_source_credit":2104705,"derived_artifact_credit":1917,"direct_net":1956185,"estimated_tokens_saved":1956185,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14922,"response_debit":137404,"source_credit_count":52,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":328,"content_source_credit":8304274,"derived_artifact_credit":3991,"direct_net":7601486,"estimated_tokens_saved":7601486,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":26505,"response_debit":690028,"source_credit_count":172,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9754},"wave_id":"1xxc9 monotonic-index-version-protection"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 19 | 0 | 12 | 9,858,833 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":12,"estimated_exploration_avoided":9858833,"surfaced_events":19} -->
<!-- wave:exploration-avoided end -->
## Current Assumptions

One project-local database and existing publication ownership remain the architecture. First-hop old-host coordination may require the established restart handoff; no new bridge release.

## Outputs Expected

One consolidated change doc, compatibility matrix within that doc, bounded implementation and consolidated delivery evidence.

## Review Checkpoints

Readiness approved by fresh targeted council (red-team primer, rotating docs-contract, independent synthesis); report readiness-review.json. Seven specialist delivery lanes remain pending. Builder allocation: implementer for shared contracts and server integration; senior-data-engineer scope for transaction verification; separate implementer for upgrade checkpoint. Operator requested this bug behavior and implementation.

## Completion Criteria

All admitted ACs/tasks reconciled, required independent reviews passed, and operator closure approval obtained.

## Handoff

Readiness approved and implementation authorized. Core writer fences, public diagnostics and first-hop upgrade handoff are implemented; focused verification is underway before the full suite. Wave 1xtnr is paused. No package, commit or closure is authorized.
