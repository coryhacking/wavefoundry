# Threat Model

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Trust Boundaries

| Boundary | Trust Level | Notes |
|----------|------------|-------|
| Local filesystem (repo root) | Fully trusted | All scripts operate on local files only |
| Target repository roots (future MCP) | Operator-configured explicit trust | Must never read or write outside `allowed_roots` |
| MCP client connection (future) | Localhost only; no authentication required for MVP | Loopback-only binding expected |
| Distribution zip archives | Trusted (produced by Wavefoundry scripts) | Operators verify before unpacking into target repos |

## Current Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Seed protection bypass | Framework seed edits without guard approval could corrupt seed prompts | Pre-edit hook checks `.wavefoundry/guard-overrides.json`; seeds require explicit approval |
| Framework plan gate bypass | Broad docs/prompts/ edits without plan review | Pre-edit hook enforces `framework_edit_allowed` flag |
| MCP server allowed-roots escape (future) | Tool reads/writes outside operator-configured roots | Explicit allowed-roots validation before every tool operation |
| Sensitive data in journals | Journal entries must not contain secrets, credentials, PII | Memory governance rules in seed-130; `.gitignore` covers guard-overrides only |

## Security Sensitivity

- No secrets, credentials, tokens, or PII in framework scripts or seed prompts.
- Guard-overrides file (`.wavefoundry/guard-overrides.json`) is gitignored to prevent accidental commit of approval flags.
- Distribution zips are gitignored; they are local transport artifacts only.

## Future Considerations

- MCP server authentication: for MVP, localhost-only binding; no auth required.
- If MCP server is ever exposed beyond localhost, an auth layer must be designed and threat model updated.
