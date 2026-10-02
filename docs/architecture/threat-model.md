# Threat Model

Owner: Engineering
Status: active
Last verified: 2026-10-02

## Trust Boundaries

| Boundary | Trust Level | Notes |
|----------|------------|-------|
| Local filesystem (repo root) | Fully trusted | All scripts operate on local files only |
| Target repository roots (future MCP) | Operator-configured explicit trust | Must never read or write outside `allowed_roots` |
| MCP client connection (future) | Localhost only; no authentication required for MVP | Loopback-only binding expected |
| Dashboard browser connection | Loopback only; no authentication by default | `dashboard_server.py` must bind only to configured local host (default `127.0.0.1`). Since wave `1zim2` it answers only requests whose `Host` names `localhost`, `127.0.0.1` or `::1` (any port), or the host the operator explicitly bound, and refuses the rest with 421, as it does a request with more than one `Host` header or an absolute-form request target; a wildcard bind (`0.0.0.0`) admits loopback names only and records a `127.0.0.1` URL. Every response carries a same-origin Content-Security-Policy and `X-Content-Type-Options: nosniff`, and the page loads only scripts vendored under `dashboard/vendor/` from its own origin |
| Distribution zip archives | Trusted (produced by Wavefoundry scripts) | Operators verify before unpacking into target repos |
| Declared extension tool modules (`mcp_tool_extensions`, wave `1yv9l`) | Trusted as distribution code | Loaded only when declared, only as flat `.py` files directly in the framework scripts directory, never from a target repository; run with the server's authority. Anything able to write the scripts directory already holds that authority. `wf_server_info` reports the declaration and each module's executed-bytes SHA-256. Since wave `1z8oz` an alias, and the `alias_for_core` that keeps a replaced core behaviour reachable, is a copy of the tool as wrapped (the core behaviour is wrapped in its own pass keyed on the core name), so both keep the lifecycle lock and the upgrade publication guard. A replacement keeps its core name's lock and guard, which are keyed by name; a declared tier replaces only the roster tier and never lowers a `write` tool to `read` (wave `1zicq`), and `write` adds the upgrade checkpoint on a core name that is not a registered publisher. Runner tools cannot be aliased, hidden or replaced; the edit-gate tools `wf_open_gate` and `wf_close_gate` cannot be overridden, replaced or hidden (wave `1zicq`). Since wave `1zim3` a parameter-mapped alias (`EXTENSION_TOOL_PARAMETERS`) is a translator into the canonical tool's wrapped callable, captured at install: it keeps the canonical lifecycle lock, publication guard and cost accounting, keyed on the canonical name and applied once, and it refuses any argument outside the alias's parameters with `unknown_arguments` and never forwards one, so a caller cannot reach a renamed-away parameter or override a pinned value. An override that delegates through `core_handler(name)` receives the unwrapped core handler, so its own name-keyed wrappers apply once. Since wave `1zimf` a new extension tool that writes wave lifecycle records must be declared in `EXTENSION_LIFECYCLE_TOOLS`, which gives it exactly the core lifecycle lock wrapper (strict root resolution, the process-hold registry, `lifecycle_mutation_locked` on contention or re-entry), and `EXTENSION_ARTIFACT_PATH_FIELDS` credits the paths it names under the core derived-artifact contract (contained existing files only, floored per artifact); both accept only new `write`-tier extension tools, never core names, aliases, runner or edit-gate tools, and the credit is the distribution's assertion that the tool wrote those files. These declaration checks catch careless declarations, not hostile module code, which already runs with the server's authority. Any install failure leaves only runner tools served. A replacement is trusted distribution code like any extension module. |

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
| Edit gates do not see shell writes (wave 1z8ot) | A file written through a shell command bypasses every pre-write gate on every host | Known limit; listed in seed `050-agent-entry-surface-bootstrap.prompt.md`, "Known limits of the edit gates" |
| File-writing MCP tools are not gated on Claude (wave 1z8ot) | Writes through the Wavefoundry server or a third-party MCP server never reach the pre-edit hook, whose matcher names only built-in edit tools | Known limit; see seed 050's known limits |
| Check-then-use window in edit hooks (wave 1z8ot) | The hook classifies the path before the host writes it, so the path can be retargeted in between; this needs an actor who can already write the repository | Known limit; see seed 050's known limits |
| Check-then-use window in Windows lock paths (wave 1z8ot) | On native Windows each lock directory under `.wavefoundry` is checked with `lstat` for a symlink or junction before it is created or opened, so the path can be retargeted between the check and its use; this needs an actor who can already write the repository | Known limit; POSIX walks with directory handles and `O_NOFOLLOW`, so it has no window (`runtime_lock._open_lock_carrier`, `upgrade_bridge_bootstrap._open_strict_carrier`) |
| A missing `python3` fails open on Claude and Windsurf (wave 1z8ot) | The shell returns 127, not 2, and those hosts allow any exit other than 2 | Known limit; see seed 050's known limits. Copilot denies any non-zero pre-tool-use exit |
| MCP server allowed-roots escape (future) | Tool reads/writes outside operator-configured roots | Explicit allowed-roots validation before every tool operation |
| Dashboard accidental non-loopback exposure | Local operational data could be exposed on the network if bound too broadly | Default host is `127.0.0.1`; config-driven host is explicit; security review lane required for trust-boundary changes to dashboard server |
| Dashboard reached under another host name (wave 1zim2) | A web page in the operator's browser could address the loopback server under a non-loopback name and read project content | `DashboardHandler.do_GET` refuses, as its first statement, any request whose `Host` is missing, repeated, or not a loopback name or the explicitly bound host, or whose request target is absolute-form rather than a path (421 Misdirected Request) |
| Dashboard third-party scripts (wave 1zim2) | Scripts fetched from a CDN at page load could change without notice and need the network | React, ReactDOM and elkjs are vendored under `.wavefoundry/framework/dashboard/vendor/` (pinned versions, licences and SHA-256 in its `README.md`, which since wave 1zimd also records each package's npm tarball URL and registry `dist.integrity` and the commands that reproduce and check each file) and served from the dashboard's own origin; the Content-Security-Policy (`default-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`) blocks any other script source |
| uv bootstrap (wave 1zimd) | When no uv exists, setup installs one from the package index; an index or mirror serving other bytes for the pinned version would put an unreviewed binary in the tool environment, outside uv's own package-age guard | `setup_index._bootstrap_uv` installs only the pinned `UV_BOOTSTRAP_REQUIREMENT`, as a wheel, with `pip --require-hashes --no-deps` against `UV_BOOTSTRAP_WHEEL_SHA256` (every published wheel's SHA-256, replaced with the version at release); other bytes are refused and no unverified uv is installed. Known limits: an existing uv in the tool environment or on `PATH` is used whatever its version and is not checked against the hashes; a failed bootstrap (refused hash, network failure, no wheel for the platform) is reported and setup installs nothing and stops, since dependencies install only through uv with its package-age guard (wave 1zls6) |
| Dashboard state drift via persisted snapshots | Operator could see stale fabricated state if the dashboard relied on generated JSON files | Browser state stays in memory; the server reads live repo state; `.wavefoundry/locks/dashboard-server.lock` carries endpoint metadata, not a dashboard snapshot |
| Sensitive data in journals | Journal entries must not contain secrets, credentials, PII | Memory governance rules in seed-130; `.gitignore` covers guard-overrides only |
| Indexed ignore files name excluded paths (wave 1seaw, walker 16) | `.aiignore`/`.gitignore` content (path names and patterns, never file contents) is retrievable and can be cited onward by an agent host | Same-user threat model; the index stays local and gitignored; the secrets scan covers the walked file list; the low-information prior keeps unnamed ignore files below implementation evidence |

## Security Sensitivity

- No secrets, credentials, tokens, or PII in framework scripts or seed prompts.
- Guard-overrides file (`.wavefoundry/guard-overrides.json`) is gitignored to prevent accidental commit of approval flags.
- Dashboard endpoint metadata carrier (`.wavefoundry/locks/dashboard-server.lock`, the lifetime lock file) must stay untracked/host-local.
- Distribution zips are gitignored; they are local transport artifacts only.

## Future Considerations

- MCP server authentication: for MVP, localhost-only binding; no auth required.
- Dashboard server authentication: for MVP, localhost-only binding; no auth required.
- If either local server is ever exposed beyond localhost, an auth layer must be designed and threat model updated.
