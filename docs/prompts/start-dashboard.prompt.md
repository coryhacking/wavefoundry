# Start Dashboard

Owner: Engineering
Status: active
Last verified: 2026-05-08

Shortcut: **`Start dashboard`**

## Purpose

Start the local Wavefoundry dashboard for the current repository. This is a loopback-only, read-only operational view over wave state, changes, review evidence, and local project health.

## Default Operator Path

Open the dashboard in the default browser and always print the final URL:

```bash
python3 .wavefoundry/framework/scripts/dashboard_server.py --root . --open
```

## Low-Level Script Path

Start the server without auto-opening the browser:

```bash
python3 .wavefoundry/framework/scripts/dashboard_server.py --root .
```

Both paths always print the final bound URL, including host and port.

## Runtime Contract

- The browser talks to a local Python HTTP server on loopback (`127.0.0.1` by default).
- The dashboard is **MCP-informed, not MCP-transported**: it reuses shared Python readers rather than making the browser speak stdio MCP directly.
- UI state lives in the browser.
- Repository data is read live from docs/config/state files on demand.
- Any `.wavefoundry/` dashboard metadata file is only for host-local endpoint discovery, not as the canonical dashboard data source.

## Port Behavior

The server reads `docs/workflow-config.json` `dashboard` settings:

- `preferred_port`
- `port_range_start`
- `port_range_end`
- `host`
- `poll_interval_ms`

Startup tries the preferred or recorded host-local port first, then scans the configured fallback range until it finds a free port.

## Guardrails

- Local-only by default; no remote exposure or auth layer.
- Read-only; the dashboard does not mutate repository state.
- The dashboard is an operational surface, not a replacement for `wave.md`, change docs, or MCP tools as the canonical source of truth.
