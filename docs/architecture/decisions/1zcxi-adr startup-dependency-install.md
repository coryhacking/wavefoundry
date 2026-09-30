# 1zcxi-adr — MCP startup installs missing declared dependencies

Owner: Engineering
Status: accepted
Last verified: 2026-09-29

## Context

A repository reaches a framework version with new or re-pinned requirements in two ways. `wf upgrade` / `wf_upgrade` installed packages only as a side effect of its Phase 4 index child, reported an install failure as an index publication failure, and never surfaced `wf setup` in its summary or next step. A `git pull` of a teammate's committed upgrade runs no upgrade code at all: the next MCP start assessed `dependencies_missing`, exited because startup was blocked, and printed the `wf setup` guidance only to stderr, so the host showed a failed MCP server and only Claude Code's session-start hook told the agent why.

Wave `1zc7n` made `psutil` a required dependency, which turns this gap into a guaranteed event for every consumer. Until now the setup-readiness design (wave `1yzcz`) was report-only everywhere: checks, the session-start hook and `index_health` report and ask, and nothing installs by itself. That rule lived in seed 050, `AGENTS.md` and the MCP spec; no ADR recorded it.

The operator decided (2026-09-29) that both paths must end with the declared dependencies installed or a clear `wf setup` recommendation, and that the MCP server installs them itself at startup. Readiness review of wave `1zfd9` then shaped how: host MCP startup timeouts can be seconds, the tool environment is shared by every repository on the machine, `pip` has no package-age guard, and a running server cannot replace a package it already imported.

## Decision

MCP startup installs the missing or version-incompatible declared dependencies when they are the only reason startup is blocked: exactly the specs the assessment reports, into the existing tool environment, through uv with its `--exclude-newer` guard only, with repository uv configuration excluded, under one OS lock that owns every change to the tool environment, with nothing written to stdout. Packages the server runs without install in the background after the transport starts, and `process_info` does not import them until the install finishes; anything else installs before the server starts. There is no opt-out. The upgrade installs dependencies as its own step before Phase 4 and reports setup readiness in its cleanup summary and next step. Everything else stays report-only.

## Consequences

**Positive:**

- A pull that adds or re-pins a requirement no longer leaves the MCP server unable to start on any host; the agent sees the install in `wf_server_info` and the setup notice.
- A background install keeps the server inside short host startup timeouts when the missing package is deferrable (`psutil` is).
- An upgrade whose dependency install fails says so, names `wf setup`, and does not claim an index publication failure it never attempted.
- uv's 21-day age guard applies to every unattended install; the pip fallback stays available only to operator-run `wf setup`.

**Negative:**

- The tool environment is shared by every repository on the machine. Two repositories on framework versions with different pins for the same package re-pin it on each host start. The operator accepted this; each startup install is visible in `wf_server_info`, and on Windows a package in use by another host, an index build or the dashboard cannot be replaced, so the install fails with guidance naming what to stop.
- Startup now uses the network when a requirement changed. In locked-down environments the install fails within `setup.dep_install_timeout_seconds` and the server reports `wf setup`.
- A host that kills the server mid-install on Windows releases the lock while the installer may still run (on POSIX every installer child, including venv creation and the uv bootstrap, inherits the lock). The next start reassesses.
- A lock that cannot be taken fails closed: `wf setup`, the upgrade and startup install nothing rather than race another installer or a venv recreation. A check that finds nothing to install and no environment to create takes no lock, so it never fails on the lock; the lock is opened at the resolved tool-environment base, so a relocated, linked `~/.wavefoundry` works.
- The upgrade's separate dependency step changes what Phase 4 does, so on the default path of `wf upgrade` and `wf_upgrade()` it takes effect from the upgrade after the one that installs it; the `wf_upgrade` next step, computed by the running server, applies after a reload or restart.

## Trust model

The installed specs come from `setup_requirements.py` in the checkout, the same code the host already runs automatically after a pull, so an automatic install adds no new code-execution boundary. The package index follows the operator's uv configuration: uv environment variables, and the operator's user- or system-level `uv.toml`, which the startup install passes explicitly with `--config-file` (or `--no-config` when there is none). An explicit configuration file stops uv discovering configuration from the working directory and its parents, so a repository's `uv.toml` or `[tool.uv]` never applies to the startup install, even when the tool environment lives inside a checkout; `wf setup` keeps uv's normal discovery. When both a user- and a system-level file exist, only the user file is used (uv would merge them). An operator-set `UV_CONFIG_FILE`, or a truthy `UV_NO_CONFIG`, is left to uv. Repository configuration can only change the install timeout.

## Alternatives Considered

- **Start degraded and recommend `wf setup`.** Keeps report-only, but a pull adding a package the server imports still leaves it unable to start. Rejected by the operator.
- **Always install before starting.** Simpler, but a short host timeout kills the server mid-install on every start. Replaced by background installs for deferrable packages.
- **Install absent packages only.** Avoids re-pinning the shared environment, but a pull that re-pins a package would not self-heal. Rejected by the operator.
- **Reuse `ensure_deps` at startup.** It can recreate the shared environment, plans GPU packages from hardware probes, and falls back to pip. Rejected in readiness review.
- **An operator opt-out variable.** Rejected by the operator.

## Related

- Change `1zcm3-enh setup-after-upgrade-and-pull` (wave `1zfd9`)
- ADR `1z9df-adr psutil-process-info`
- ADR `1u49j-adr fresh-code-summary-producer-contract` (flat summary fields)
