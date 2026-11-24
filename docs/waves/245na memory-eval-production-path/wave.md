# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-23
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `245na memory-eval-production-path`
Title: Memory Eval Production Path

## Objective

Maintainers and agents get a memory evaluation that scores independently authored situation-language queries, including null and stale cases, against no-memory, grep, BM25-only, dense-only, hybrid, production and full-context baselines, with intervals and memory index signals. Measurement only: production ranking and indexing do not change.

## Changes

Change ID: `245sp-enh memory-eval-situation-queries-and-baselines`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-11-23

## Wave Summary

Wave `245na` (Memory Eval Production Path) delivered one change: Memory eval scores situation-language queries against baselines.

**Changes delivered:**

- **Memory eval scores situation-language queries against baselines** (`245sp-enh memory-eval-situation-queries-and-baselines`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12 and AC-14 completed. AC-13 deferred: Status: Met except two parts, by operator decision 2026-11-23: 4 active records (1t78a, 1vo1a, 1ydvk, 21rnt) have fewer than 2 answerable cases because their lessons state no retrievable situation, and go to arc track 4 for rewrite or retirement and a versioned re-freeze; the production measurement is the CLI run (0 of 606 fallbacks), because `wf_memory_eval` through the MCP server lost 7 to 15 probes to a transient lexical fallback during docs index publishes, recorded as arc track 2 evidence. Key decisions: Hash the parsed JSON, not the file bytes; Run the cosine filter only at freeze; run the sequence filter at every run.

## Watchpoints

- Watchpoint: the query set must be frozen before any arm is scored; only the `dev` split may guide tuning.
- Follow-up: none required for the slug. It predates the supersession and is kept, because no lifecycle tool renames a wave.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 245na-arch-dense-stream-unspecified | do_now | no | completed | — |
| 245na-cr-arm-corpus-and-signals | do_now | no | completed | code-reviewer |
| 245na-cr-grep-null-gate | do_now | no | completed | code-reviewer |
| 245na-qa-ac18-vacuous-live-check | do_now | no | completed | — |
| 245na-qa-bootstrap-pooling-untested | do_now | no | completed | — |
| 245na-qa-bootstrap-untested | do_now | no | completed | — |
| 245na-qa-curated-bound-wiring-untested | do_now | no | completed | — |
| 245na-rt-gate-rewards-abstention | do_now | no | completed | — |
| 245na-rt-split-and-resample-unit-is-case | do_now | no | completed | — |

*Machine review state — 9 findings; current: do_now 9, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking); known-bad control not applicable: Docs-only lane: inspected the spec, arc, withdrawn 243hz header and planned CHANGELOG and tool-reference lines; no code surface in this lane is affected, so no known-bad control was run. | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 98 | 1,831,239 |
| implement | 68 | 0 |
| review | 64 | 518,594 |
| **Total** | **230** | **2,349,833** |

<!-- wave:context-efficiency-state {"generation":224,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":68,"content_source_credit":1874,"derived_artifact_credit":0,"direct_net":-11635,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3562,"response_debit":19101,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9154},"plan":{"calls":98,"content_source_credit":2137979,"derived_artifact_credit":4330,"direct_net":1831239,"estimated_tokens_saved":1831239,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":51960,"response_debit":265408,"source_credit_count":89,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"review":{"calls":64,"content_source_credit":666541,"derived_artifact_credit":1734,"direct_net":518594,"estimated_tokens_saved":518594,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19458,"response_debit":137001,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":230,"content_source_credit":2806394,"derived_artifact_credit":6064,"direct_net":2338198,"estimated_tokens_saved":2349833,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":74980,"response_debit":421510,"source_credit_count":119,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":22230},"wave_id":"245na memory-eval-production-path"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
