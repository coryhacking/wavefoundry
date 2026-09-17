# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0h1 tool-registry-dispatch`
Title: Tool Registry Dispatch

## Objective

When this wave closes, the MCP server has an enumerable runtime registry of tool specifications and one explicit, ordered middleware chain, with no handler moved and the public tool surface byte-identical to the golden fixture.

## Changes

Change ID: `1y0be-ref tool-registry-and-wrapper-chain`
Change Status: `planned`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

## Wave Summary

Maintainer-facing refactor from the modularity RFC, scoped to what preserves the existing hot-reload and packaging model: a flat `mcp_tool_registry.py` sibling module populated by a post-registration pass over FastMCP's own tool table cross-referenced with the roster (operator decision 2026-09-16; the 90 registration sites are untouched), the three wrapper passes as one applied chain with an inspectable order, and a registry-based roster parity test. No aliases, no `server/` package, no fail-fast roster check at startup.

## Watchpoints

- Requires `1y0do` closed; AC-1 is defined against the golden fixture.
- The actual wrapper order is cost innermost, lifecycle lock middle, upgrade-publication guard outermost. The RFC and kickoff state it differently; the existing guard-is-outermost test is the authority.
- The runtime roster check stays warning-only by recorded decision; do not reverse it.
- `repo_root`, `subprocess_util`, `venv_bootstrap`, and now (as of `1y3og`, verified 2026-09-17) `setup_readiness` and `runtime_advisory` are outside the reload purge list and stay stale across `wf_reload_mcp`; out of scope here, worth its own small change, and growing.
- This wave does not unblock Waveforge; do not sequence it ahead of `1y0gz` or `1y0h0`.
- Follow-up for `1y0h2 handler-module-split` (docs-contract seat, 2026-09-16): its Requirement 2 has relocated modules hand-author `TOOLS: list[ToolSpec]`, but under the introspection design `ToolSpec` is derived from FastMCP's tool table after registration, so hand-authored specs would never be introspected. Before `1y0h2` opens, its change doc must state either that relocated handlers keep `@mcp.tool` registration through a call from `register_mcp_surface`, or that composition loops `mcp.tool()(fn)` over each `TOOLS` entry so introspection still finds them. Editing that doc rotates its readiness receipt; do it as its own re-ready step.

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

- `1y0do tool-surface-snapshot` must close before implementation.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| credit_history_unavailable | 0 | 0 |

<!-- wave:context-efficiency-state {"generation":43,"measurement_status":"credit_history_unavailable","pending":false,"schema_version":1,"stages":{"plan":{"calls":42,"content_source_credit":1226740,"derived_artifact_credit":1250,"direct_net":1165719,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3094,"response_debit":61468,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2291},"review":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-1553,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10,"response_debit":1543,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":43,"content_source_credit":1226740,"derived_artifact_credit":1250,"direct_net":1164166,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3104,"response_debit":63011,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2291},"wave_id":"1y0h1 tool-registry-dispatch"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a 90-site decorator conversion may be avoidable by introspecting FastMCP's own tool table; strongest-alternative: recorded as an open decision for the operator, not applied).
- **Prepare-phase Wave Council [prepare-council] — 2026-09-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: red-team claimed the module purge list Requirement 4 depends on does not exist, refuted by the `sys.modules` eviction block at the top of `server_impl.py`; strongest-alternative: AC-1 restated as an AST-digest test and Requirement 2 gains the `RUNNER_TOOLS` timing invariant, both applied in-session; `1y0h2` composition mismatch recorded as a watchpoint for that wave's own re-ready).
