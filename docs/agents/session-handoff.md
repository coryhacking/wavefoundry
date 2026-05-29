# Session Handoff

Owner: wave-coordinator
Status: active
Last verified: 2026-05-29

## Active Wave

**Wave:** `12sg7 implementation-governance-upgrades`  
**Status:** active — all 6 changes complete; ready for `Review wave`  
**Changes (all complete):**
- `12sf9-enh senior-builder-roles` — seeds 222/223/224, design-system governance, `wave_gate_open`/`close`/`status` rename, `design_system_edit_allowed` gate
- `12sfb-enh mcp-code-navigation-defaults` — MCP-first navigation defaults in seeds 180/050/100/211
- `12sfj-enh ac-task-linked-tracking` — checkbox AC template, truth-hierarchy review contracts, lint validator, dashboard review-badge
- `12sg4-enh pre-implementation-review-gate` — pre-implementation gate in seeds 180/100/001, local prompts, council surfaces
- `12s5r-enh dashboard-dialog-wider-ac-id-column` — wider dialogs (1000px), AC-ID column, no-wrap table cells, newest-first pending waves
- `12sh5-enh formal-red-team-role` — seed-225 red-team role, routing tables, council config, specialist taxonomy

**Key governance notes:**
- Gate tool family renamed: `wave_gate_open` / `wave_gate_close` / `wave_gate_status` (was `wave_open_gate` / `wave_close_gate`)
- New `design_system_edit_allowed` gate; enforced only when `workflow-config.json` `design_system_policy.governance` is `"read-only"` or `"review-governed"`
- MCP server must be reloaded (client reconnect) for renamed gate tools to appear under their new names

**Next:** `Review wave` — required lanes: `architecture-reviewer` (12sf9, 12sfb, 12sg4, 12sh5), `code-reviewer` (12sf9, 12sfj, 12sg4, 12s5r), `qa-reviewer` (all), `docs-contract-reviewer` (12sf9, 12sfb, 12sfj, 12sg4, 12sh5), `security-reviewer` (12sf9, 12sg4, 12sh5). Wave Council delivery pass required (`council-moderator` + fixed seats + rotating `docs-contract-reviewer`).

## Last Closed Wave

**Wave:** `12rnv agent-prompt-harness` — implementation complete 2026-05-21 (closure pending review)  
**Shipped:** Harness core seed-209, specialists 217–219, inferential reviewers 212/214/221, bootstrap updates 007/050/100/020/180/215, AGENTS.md implementation principles, role-metadata lint, Factor dashboard group, category-driven grouping, dashboard visualization.

## Open Questions / Deferred Decisions

- `wave_gate_*` new names are in server_impl.py but MCP server has not been reloaded — existing sessions see old `wave_open_gate`/`wave_close_gate` names until client reconnect.
- `close_warnings` path in `perform_mcp_reload` (when `ImplHandler.close()` raises) is not tested — advisory only.

## Current Session

**Active wave:** *(none)*

**Stage-gate waiver (operator-approved, 2026-05-29):** Operator explicitly authorized a direct framework-code change (no wave) to centralize project include-prefix config reading inside `indexer.py`. Scope: `indexer.py` now self-reads `docs/workflow-config.json` (content-scoped, plus legacy `include_framework_code_for_code_search` boolean) with CLI `--project-include-prefix` as an override; redundant config-read+forward removed from the post-edit hook (live + render template), `dashboard_server.py`, and `server_impl.py` (run_index_build, staleness dry-run, background refresh). `setup_index.py` left unchanged as the explicit orchestrator. Verified via the framework test suite.
