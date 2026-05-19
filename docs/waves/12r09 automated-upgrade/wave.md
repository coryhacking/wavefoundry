# Wave Record

Owner: Engineering
Status: active
Last verified: 2026-05-19

wave-id: `12r09 automated-upgrade`
Title: Automated Upgrade

## Changes

Change ID: `12r08-feat automated-upgrade-script`
Change Status: `implemented`

Change ID: `12r0b-feat wave-upgrade-mcp-tool`
Change Status: `implemented`

## Objective

Replace the manual "Upgrade wave framework" agent conversation with a scripted upgrade path: `upgrade-wavefoundry` handles zip adoption, surface rendering, pruning, docs gate, index rebuild, and dashboard coordination while the agent retains ownership of drift detection, journal reconciliation, and spec gap remediation.

## Wave Summary

Single-feature wave delivering `upgrade-wavefoundry` (bin + Python implementation), `check_version.py`, `upgrade_lib.py` (shared lock utilities), dashboard upgrade-awareness (R2), `wave_upgrade_status` MCP tool (R5), and `wave_dashboard_restart` upgrade guard (R7). Requested by Aceiss (Teton project operator).

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required for all edits to `dashboard_server.py`, `server.py`, and any new framework scripts — open before editing, close immediately after.
- **Watchpoint:** `upgrade_lib.py` must be written and committed before `dashboard_server.py` and `server.py` patches — it is imported by both.
- **Watchpoint:** `wave_upgrade_status` must be added to the registered-tool assertion in `test_server_tools.py`.
- **Watchpoint:** Dashboard startup path changes (R2) must not affect existing auto-index behavior when no lock file is present — verify with existing IndexBuilder tests.

## Review Evidence

- wave-council-readiness: approved — well-scoped mechanical feature; agent-owned phases remain agent-owned; lock file pattern is safe (pid-tracked, stale detection); dashboard patch is additive to existing watch loop; no schema changes. 2026-05-19.
- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.
