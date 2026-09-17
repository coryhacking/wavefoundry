# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0h0 typed-phase-gates`
Title: Typed Phase Gates

## Objective

When this wave closes, the prepare, review, and close checks are named gate units in ordered per-phase lists, and a target repository can require additional named sensors and review lanes per phase through a typed `phase_gates` configuration block, with no repository code loaded by the server. This is the second wave that unblocks Waveforge's adoption.

## Changes

Change ID: `1y044-ref extract-lifecycle-gate-units`
Change Status: `planned`

Change ID: `1y0bd-enh config-declared-phase-gates`
Change Status: `planned`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

## Wave Summary

Extract the existing lifecycle checks one to one into `lifecycle_gates.py` with no behavior change, then append config-declared gate units that reuse the shipped `sensors` execution path and the required-lanes selection. Operator decision on 2026-09-14: config-declared typed gates, not convention-discovered policy modules.

## Watchpoints

- `1y044` must land before `1y0bd`; the configured gates append to the phase tuples the refactor creates.
- Evidence authority stays `events.jsonl` through `read_review_event_ledger`; the facade-only test in `1y044` is the guard.
- The `review_policies` config key is digested but never parsed; do not give it semantics here. `phase_gates` is a separate key.
- Sensors run repository-declared shell commands under the server's privileges; this wave adds no new discovery or implicit execution, but the security lane should review the fail-closed and provenance requirements.
- Documenting `phase_gates` in seeds and rendered `AGENTS.md` for target repositories is a seed-gated follow-up.
- Golden tool-surface fixture from `1y0do` must remain unchanged.

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
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| docs-contract-reviewer | pending | no current executed approval | record approval evidence for docs-contract-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- `1y0do tool-surface-snapshot` should close first.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 7 | 0 |
| **Total** | **7** | **0** |

<!-- wave:context-efficiency-state {"generation":7,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":7,"content_source_credit":3548,"derived_artifact_credit":271,"direct_net":-1847,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1361,"response_debit":7912,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3607}},"store_instance_id":"33652402c1924592b478c511b0100138","totals":{"calls":7,"content_source_credit":3548,"derived_artifact_credit":271,"direct_net":-1847,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1361,"response_debit":7912,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3607},"wave_id":"1y0h0 typed-phase-gates"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->

## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the sensor-execution reuse path was an unnamed, unfalsifiable proposition; strongest-alternative: name the function and its shared-module home directly in the requirement, applied in-session).
