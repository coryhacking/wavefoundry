# Security

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Security Posture

Wavefoundry is local developer tooling with no network exposure in current scripts. Security posture is low-risk for the current implementation.

## Current Security Controls

| Control | Mechanism |
|---------|----------|
| Seed protection | Pre-edit hook checks `.wavefoundry/guard-overrides.json`; blocks edits to seed prompts without explicit approval |
| Framework plan gate | Pre-edit hook requires `framework_edit_allowed` flag for broad framework-maintenance edits |
| Guard-overrides file gitignored | `.wavefoundry/guard-overrides.json` is never committed; approval state stays local |
| Distribution zip gitignored | `wavefoundry-framework-*.zip` is never committed; distribution is local-only |
| No secrets in seeds or scripts | Framework scripts and seed prompts contain no credentials, API keys, or PII |

## Future Security Concerns (MCP Server)

| Concern | Mitigation Plan |
|---------|----------------|
| Allowed-roots escape | Explicit path validation before every file read/write in MCP tools |
| Mutation without approval | Mutation tools must show diff + require explicit confirmation |
| Localhost-only binding | No external network exposure for MVP; auth layer required before any remote binding |

## Threat Model Reference

See `docs/architecture/threat-model.md` for trust boundaries and detailed risk analysis.
