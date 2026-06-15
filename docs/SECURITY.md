# Security

Owner: Engineering
Status: active
Last verified: 2026-06-15

## Security Posture

Wavefoundry is local developer tooling with no network exposure in current scripts. Security posture is low-risk for the current implementation.

## Current Security Controls


| Control                         | Mechanism                                                                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Seed protection                 | Pre-edit hook checks `.wavefoundry/guard-overrides.json`; blocks edits to seed prompts without explicit approval |
| Framework plan gate             | Pre-edit hook requires `framework_edit_allowed` flag for broad framework-maintenance edits                       |
| Guard-overrides file gitignored | `.wavefoundry/guard-overrides.json` is never committed; approval state stays local                               |
| Distribution zip gitignored     | `wavefoundry-*.zip` is never committed; distribution is local-only                                               |
| No secrets in seeds or scripts  | Framework scripts and seed prompts contain no credentials, API keys, or PII                                      |
| Hardcoded secrets detection     | `wave_scan_secrets` MCP tool and `docs-lint` check scans project files against a merged Gitleaks-based TOML ruleset (`.wavefoundry/scan-rules.toml` + `docs/scan-rules.toml`). Findings land in `docs/scan-findings.json` with a pending → false-positive / confirmed-secret lifecycle requiring multi-user confirmation. False-positive confirmations are time-bounded (`confirmation_valid_days`, default 365 days; per-confirmation clock) and must be re-verified with a fresh dated entry once expired. `wave_close` hard-blocks on `pending` and `suspected-secret` entries (unresolved — must be classified); `confirmed-secret` entries do **not** block but surface a non-blocking standing reminder on every close (wave 1p5pz). See `docs/references/scan-findings-format.md`. |


## Future Security Concerns (MCP Server)


| Concern                   | Mitigation Plan                                                                     |
| ------------------------- | ----------------------------------------------------------------------------------- |
| Allowed-roots escape      | Explicit path validation before every file read/write in MCP tools                  |
| Mutation without approval | Mutation tools must show diff + require explicit confirmation                       |
| Localhost-only binding    | No external network exposure for MVP; auth layer required before any remote binding |


## Threat Model Reference

See `docs/architecture/threat-model.md` for trust boundaries and detailed risk analysis.