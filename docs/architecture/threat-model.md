# Threat Model

Owner: Engineering
Status: active
Last verified: 2026-05-08

## Trust Boundaries

| Boundary | Trust Level | Notes |
|----------|------------|-------|
| Local filesystem (repo root) | Fully trusted | All scripts operate on local files only |
| Target repository roots (future MCP) | Operator-configured explicit trust | Must never read or write outside `allowed_roots` |
| MCP client connection (future) | Localhost only; no authentication required for MVP | Loopback-only binding expected |
| Dashboard browser connection | Loopback only; no authentication by default | `dashboard_server.py` must bind only to configured local host (default `127.0.0.1`) |
| Distribution zip archives | Trusted (produced by Wavefoundry scripts) | Operators verify before unpacking into target repos |

## Current Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Seed protection bypass | Framework seed edits without guard approval could corrupt seed prompts | Pre-edit hook checks `.wavefoundry/guard-overrides.json`; seeds require explicit approval |
| Framework plan gate bypass | Broad docs/prompts/ edits without plan review | Pre-edit hook enforces `framework_edit_allowed` flag |
| MCP server allowed-roots escape (future) | Tool reads/writes outside operator-configured roots | Explicit allowed-roots validation before every tool operation |
| Dashboard accidental non-loopback exposure | Local operational data could be exposed on the network if bound too broadly | Default host is `127.0.0.1`; config-driven host is explicit; security review lane required for trust-boundary changes to dashboard server |
| Dashboard state drift via persisted snapshots | Operator could see stale fabricated state if the dashboard relied on generated JSON files | Browser state stays in memory; the server reads live repo state; `.wavefoundry/dashboard-server.json` is endpoint metadata only |
| Sensitive data in journals | Journal entries must not contain secrets, credentials, PII | Memory governance rules in seed-130; `.gitignore` covers guard-overrides only |

## Security Sensitivity

- No secrets, credentials, tokens, or PII in framework scripts or seed prompts.
- Guard-overrides file (`.wavefoundry/guard-overrides.json`) is gitignored to prevent accidental commit of approval flags.
- Dashboard endpoint metadata file (`.wavefoundry/dashboard-server.json`) must stay untracked/host-local.
- Distribution zips are gitignored; they are local transport artifacts only.

## Future Considerations

- MCP server authentication: for MVP, localhost-only binding; no auth required.
- Dashboard server authentication: for MVP, localhost-only binding; no auth required.
- If either local server is ever exposed beyond localhost, an auth layer must be designed and threat model updated.
