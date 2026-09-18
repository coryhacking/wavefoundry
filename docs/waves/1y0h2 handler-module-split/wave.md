# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0h2 handler-module-split`
Title: Handler Module Split

## Objective

When this wave closes, the code-navigation and graph-query handler families live in `codenav_handlers.py` and `graph_handlers.py` with invocation-time delegation from the existing decorated closures in `server_impl.py`, are unit-tested without the transport, stay fresh across `wf_reload_mcp`, and the public tool surface is unchanged.

## Changes

Change ID: `1y0bf-ref codenav-graph-handler-modules`
Change Status: `planned`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

## Wave Summary

First handler extraction on top of the registry: the response functions of the two largest self-contained families move out of `server_impl.py`, the AST roster census and registry parity test both remain, and packaging is confirmed to pick the modules up automatically. Search, lifecycle, memory, context-efficiency, and techdocs follow in later changes once this pattern holds.

## Watchpoints

- Watchpoint: blocked until `1y0h1` closes; the introspection registry must be available before moving response families.
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
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- `1y0h1 tool-registry-dispatch` must close before implementation.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| credit_history_unavailable | 0 | 0 |

<!-- wave:context-efficiency-state {"generation":4,"measurement_status":"credit_history_unavailable","pending":false,"schema_version":1,"stages":{"plan":{"calls":4,"content_source_credit":2991,"derived_artifact_credit":241,"direct_net":-224,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":406,"response_debit":5341,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2291}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":4,"content_source_credit":2991,"derived_artifact_credit":241,"direct_net":-224,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":406,"response_debit":5341,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2291},"wave_id":"1y0h2 handler-module-split"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: whether relocating handler bodies could let a tool's permission tier silently drift; strongest-alternative: none needed, tier travels with the registry-composed ToolSpec, not file location).
