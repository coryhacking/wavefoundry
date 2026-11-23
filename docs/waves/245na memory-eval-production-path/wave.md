# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-11-23
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `245na memory-eval-production-path`
Title: Memory Eval Production Path

## Objective

Maintainers and agents get a memory evaluation that scores independently authored situation-language queries, including null and stale cases, against no-memory, grep, BM25-only, dense-only, hybrid, production and full-context baselines, with intervals and memory index signals. Measurement only: production ranking and indexing do not change.

## Changes

Change ID: `245sp-enh memory-eval-situation-queries-and-baselines`
Change Status: `planned`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

## Wave Summary

First wave of arc `244cm-arc memory-quality` (track 1, evaluation). It makes the later indexing, admission and maintenance waves measurable, and its retrieval-stack gate decides whether retrieval investment stays paused. Spec `243hz-bug memory-eval-measures-production-path` was removed on 2026-11-23 with disposition `superseded` by `245sp-enh memory-eval-situation-queries-and-baselines`, which carries its production-path row and bounded experimental row; the superseded spec is kept, withdrawn, at `docs/plans/`.

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
| 245na-qa-bootstrap-untested | do_now | no | completed | — |
| 245na-rt-gate-rewards-abstention | do_now | no | completed | — |
| 245na-rt-split-and-resample-unit-is-case | do_now | no | completed | — |

*Machine review state — 7 findings; current: do_now 7, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | pending | no current executed approval | record approval evidence for council-delivery |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | withheld | repaired findings require fresh approval: 245na-cr-grep-null-gate, 245na-cr-arm-corpus-and-signals | record a fresh independent approval for code-reviewer |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | pending | no current executed approval | record approval evidence for architecture-reviewer |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking); known-bad control not applicable: Docs-only lane: inspected the spec, arc, withdrawn 243hz header and planned CHANGELOG and tool-reference lines; no code surface in this lane is affected, so no known-bad control was run. | none |
| docs-contract-reviewer | delivery | pending | no current executed approval | record approval evidence for docs-contract-reviewer |
| operator-signoff | delivery | withheld | repaired findings require fresh approval: 245na-rt-gate-rewards-abstention, 245na-rt-split-and-resample-unit-is-case, 245na-cr-grep-null-gate, 245na-cr-arm-corpus-and-signals, 245na-qa-bootstrap-untested, 245na-arch-dense-stream-unspecified, 245na-qa-ac18-vacuous-live-check | record a fresh independent approval for operator-signoff |
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
| review | 9 | 0 |
| **Total** | **107** | **1,831,239** |

<!-- wave:context-efficiency-state {"generation":102,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":98,"content_source_credit":2137979,"derived_artifact_credit":4330,"direct_net":1831239,"estimated_tokens_saved":1831239,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":51960,"response_debit":265408,"source_credit_count":89,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"review":{"calls":9,"content_source_credit":27654,"derived_artifact_credit":0,"direct_net":-14565,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":153,"response_debit":42066,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":107,"content_source_credit":2165633,"derived_artifact_credit":4330,"direct_net":1816674,"estimated_tokens_saved":1831239,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":52113,"response_debit":307474,"source_credit_count":90,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"wave_id":"245na memory-eval-production-path"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
