# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-19

wave-id: `12qmg dashboard-ux`
Title: Dashboard UX

## Objective

Improve dashboard ergonomics for MCP users: add a dedicated `wave_dashboard_open` tool that opens the browser to a running dashboard (or starts and opens if not running), and surface a `next_tools` hint from `wave_dashboard_start` when the server is already up.

## Changes

Change ID: `12qme-enh dashboard-open-browser`
Change Status: `implemented`

Change ID: `12qmp-bug lance-null-language-column-type-mismatch`
Change Status: `implemented`

Completed At: 2026-05-19

## Wave Summary

Single-change wave delivering `wave_dashboard_open` — a new MCP tool that always opens the browser to the dashboard, whether the server is already running or needs to be started. Complements `wave_dashboard_start` with a `next_tools` hint when the dashboard is already running.

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required for all edits to `server.py` — open before editing, close immediately after.

## Review Evidence

- wave-council-readiness: approved — single low-risk ergonomic tool addition; pattern follows existing dashboard tools; no boundary or schema changes. 2026-05-18.
- wave-council-delivery: approved — both admitted changes implemented; objective delivered (wave_dashboard_open tool + wave_dashboard_start next_tools hint + Lance null-language column type fix); wave_dashboard_open confirmed in registered-tool assertion and has dedicated tests; no deferred changes; delivery matches readiness scope. 2026-05-19.
- operator-signoff: approved — operator confirmed closure. 2026-05-19.

## Dependencies

- No external wave dependencies.
