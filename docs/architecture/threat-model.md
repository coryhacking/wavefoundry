# Threat Model

Owner: Engineering
Status: active
Last verified: 2026-07-15

## Trust Boundaries

| Boundary | Trust Level | Notes |
|----------|------------|-------|
| Local filesystem (repo root) | Fully trusted | All scripts operate on local files only |
| Target repository roots (future MCP) | Operator-configured explicit trust | Must never read or write outside `allowed_roots` |
| MCP client connection (future) | Localhost only; no authentication required for MVP | Loopback-only binding expected |
| Dashboard browser connection | Loopback only; no authentication by default | `dashboard_server.py` must bind only to configured local host (default `127.0.0.1`) |
| Distribution zip archives | Trusted (produced by Wavefoundry scripts) | Operators verify before unpacking into target repos |

## Threat Actors and Trust Classification

Wavefoundry runs with the **operator's own authority** — not a more privileged identity, and not a network-facing service. A defect the operator (or a same-user local process) could trigger using capabilities the operator already has is **not an authority escalation**. Security classification depends on *who controls the input or state*, so the actor set is explicit:

| Class | Actors / inputs | Rationale |
|-------|-----------------|-----------|
| **Trusted** | The operator; operator-owned repository contents (read as data); same-user local processes and the operator's own filesystem, shell, and credentials | These already hold the authority Wavefoundry runs under. Nothing Wavefoundry does grants them a capability they lack. |
| **Untrusted** | Genuinely external callers or content explicitly accepted from third parties — untrusted archives, webhook payloads, third-party/forked repositories, forked-PR CI, plugins, imported configuration, and shared-workspace users **when a less-trusted actor controls them** | A less-trusted actor controls the input, so a supported path that accepts it can cross an authority or asset boundary. |
| **Out of scope (today)** | Malicious same-user concurrent processes; privilege-separated attackers on the local host | Defending against a same-user process that already shares the operator's authority buys nothing under the current single-user, loopback-only posture. Revisit if a promotion trigger fires. |

"External" means a less-trusted actor controls the path — not merely that data originated elsewhere and the operator chose to import it.

### Credible-Threat Gate

A finding is a **credible security threat** only when ALL five factors are grounded (a conjunctive gate, not an additive risk score). Severity is assessed **only after** the gate passes:

1. **Actor** — a named, less-trusted actor present in this threat model (not the operator, not trusted repo content).
2. **Controlled surface** — an input, file, request, repository, or state that actor actually controls.
3. **Supported path** — a real product path that accepts that surface.
4. **Authority/asset delta** — something the program can then do or access that the actor could **not already** do with their own authority.
5. **Concrete impact** — a specific confidentiality, integrity, availability, or privilege consequence.

If any factor is absent — most commonly a trusted actor as the only controller (factor 1) or no delta beyond the operator's existing authority (factor 4) — the finding may still be a real **required-contract / correctness** issue worth fixing, but it is **not** a demonstrated security vulnerability and does not drive security severity, blocking, or approval freshness.

### Promotion Triggers

Any one of these flips the posture and re-scopes the actor classes above; when a trigger fires, re-run the credible-threat gate against the newly untrusted surface:

- Remote / non-loopback MCP or network binding (any listener beyond `127.0.0.1`).
- Multi-user service operation (Wavefoundry serving identities other than the invoking operator).
- Untrusted-repository analysis (running against repository content a less-trusted actor controls).
- CI on untrusted or forked pull requests.
- Execution under credentials or authority unavailable to the caller (privilege separation).

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
