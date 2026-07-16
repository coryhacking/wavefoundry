# Security

Owner: Engineering
Status: active
Last verified: 2026-07-15

## Security Posture

Wavefoundry is local developer tooling with no network exposure in current scripts. Security posture is low-risk for the current implementation.

Wavefoundry runs with the **operator's own authority**. The repository filesystem is trusted, target roots are operator-approved, and network surfaces are loopback-only. A defect the operator (or a same-user local process) could trigger using capabilities the operator already has is a **required-contract / correctness** issue, not an authority escalation.

- **Trusted:** the operator; operator-owned repository contents (read as data); same-user local processes.
- **Untrusted:** genuinely external callers or content explicitly accepted from third parties — untrusted archives, webhook payloads, third-party/forked repositories, forked-PR CI, plugins, imported configuration, and shared-workspace users when a less-trusted actor controls them.
- **Out of scope (today):** malicious same-user concurrent processes and privilege-separated attackers on the local host.

### Credible-Threat Gate

Security severity, blocking, and approval freshness are driven **only** by grounded findings. A credible security threat requires ALL five factors present (a conjunctive gate, not an additive score): (1) a named less-trusted actor in the threat model, (2) a surface that actor controls, (3) a supported product path that accepts it, (4) an authority or asset delta beyond what the actor already has, and (5) a concrete confidentiality/integrity/availability/privilege impact. Reviewers may report security candidates freely; only findings that pass the gate affect severity. See `docs/architecture/threat-model.md` for the actor classes and promotion triggers.

**Promotion triggers** (any one flips the posture): remote / non-loopback MCP or network binding, multi-user service operation, untrusted-repository analysis, CI on untrusted/forked pull requests, or execution under credentials unavailable to the caller.

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