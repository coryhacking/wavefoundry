# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0h2 handler-module-split`
Title: Handler Module Split

## Objective

When this wave closes, the code-navigation and graph-query handler families live in `codenav_handlers.py` and `graph_handlers.py` with their own `TOOLS` lists, are unit-tested without the transport, stay fresh across `wf_reload_mcp`, and the public tool surface is unchanged.

## Changes

Change ID: `1y0bf-ref codenav-graph-handler-modules`
Change Status: `planned`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

## Wave Summary

First handler extraction on top of the registry: the two largest self-contained families move out of `server_impl.py`, the AST roster census is retired in favor of the registry parity test, and packaging is confirmed to pick the modules up automatically. Search, lifecycle, memory, context-efficiency, and techdocs follow in later changes once this pattern holds.

## Watchpoints

- Watchpoint: blocked until `1y0h1` closes; the `TOOLS` lists use the registry types.
- Neither module may import `server_impl` at top level; shared helpers stay in the composition root behind the existing lazy indirection.
- Both modules must be added to the reload purge list; a stale handler after an upgrade would be a silent regression.
- Defer pacing decision to the operator; it is maintainer value only and carries the most merge surface for downstream patches.

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
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- `1y0h1 tool-registry-dispatch` must close before implementation.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 7 | 0 |
| **Total** | **7** | **0** |

<!-- wave:context-efficiency-state {"generation":7,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":7,"content_source_credit":3309,"derived_artifact_credit":273,"direct_net":-1801,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1383,"response_debit":7607,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3607}},"store_instance_id":"33652402c1924592b478c511b0100138","totals":{"calls":7,"content_source_credit":3309,"derived_artifact_credit":273,"direct_net":-1801,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1383,"response_debit":7607,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3607},"wave_id":"1y0h2 handler-module-split"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->

## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: whether relocating handler bodies could let a tool's permission tier silently drift; strongest-alternative: none needed, tier travels with the registry-composed ToolSpec, not file location).
