# Wavefoundry

[![Version](https://img.shields.io/badge/version-1.9.3-purple)](https://github.com/coryhacking/wavefoundry/releases)
[![MCP](https://img.shields.io/badge/MCP-local_server-0a7ea4)](https://modelcontextprotocol.io)
[![Hosts](https://img.shields.io/badge/hosts-Claude_Code_%C2%B7_Codex_%C2%B7_Antigravity_%C2%B7_Cursor-blue)](https://github.com/coryhacking/wavefoundry)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.11-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Your AI coding agent forgets what it did last session, skips review steps you told it to follow, and ships work that drifts from the plan. Wavefoundry is a local harness for all three. It runs on your machine. No service, no account, no telemetry.

## Who this is for

- Teams or solo engineers **shipping production work with an AI coding agent**.
- Codebases where review discipline, traceability, and "what was decided?" matter.
- Teams **without much engineering process yet** but with code that's going to live for a while: Wavefoundry adds the structure you'd otherwise have to invent, and the MCP intelligence is useful from day one even before the lifecycle gates kick in.

Anything that's going to live for a while can benefit.

---

## What you get

**A structured delivery lifecycle** — plan change(s) → prepare wave → implement → review → close. Two phases are enforced gates. `Prepare wave` refuses to advance an incomplete change doc. `Close wave` refuses without operator signoff.

**A local MCP server with working knowledge of your codebase.** The same server that runs the lifecycle indexes your code and docs locally and exposes them as agent tools:

- **Semantic search over code and docs** — the agent searches by intent rather than grep pattern, with reranked results across your code and your `docs/` tree.
- **Code-graph queries** — call hierarchies, impact analysis, references, dependency walks, community clustering.

All exposed as MCP tools — `docs_search`, `code_search`, `code_ask`, `code_callhierarchy`, `code_impact`, `code_references`, `code_graph_community`, `wave_graph_report`, and others. They work before any wave runs. The agent stops inventing functions that don't exist and starts answering "where do we handle X?" from your actual code.

**Built-in secrets detection.** The framework scans your project for hardcoded credentials, API keys, and tokens on every wave using a [Gitleaks](https://github.com/gitleaks/gitleaks)-based TOML ruleset (MIT licensed, community maintained). Findings land in `docs/scan-findings.json` with a lifecycle — `pending` → `false-positive` (requires multi-reviewer confirmation) or `confirmed-secret` (requires per-wave operator acknowledgment). `Close wave` refuses until every finding is resolved. Call `wave_scan_secrets` for an on-demand scan at any time; incremental mode automatically escalates to a full scan when the ruleset changes.

---

## Design principles

- **Local-first.** Operational state lives on disk in your repo and your home directory. No service, no account, no telemetry.
- **Structural enforcement over policy.** Gates fire in the framework, not in seed-prompt language. An agent cannot talk its way past `wave_close`.
- **Framework as a deployable artifact.** Wavefoundry ships as a zip that any repository can install or upgrade. The framework evolves in Wavefoundry's own wave process, gets packaged, and propagates to downstream projects.
- **Honest about scope.** What's required is required; what's optional is clearly labeled.

---

## Prerequisites

Three hard prerequisites. Do not run any install command until all three resolve.

1. **Python 3.11 or higher.** Check with:

   ```bash
   python3 --version
   # expected: Python 3.11.x (or higher)
   ```

   *Do not proceed past this block until `python3 --version` reports 3.11 or higher.* Install via your package manager (`brew install python@3.11`, `apt install python3.11`) or [`pyenv`](https://github.com/pyenv/pyenv).

2. **A supported host OS** — **macOS** (Apple Silicon or Intel), **Linux** (x86_64/arm64), or **Windows via WSL2**. WSL2 is Linux: it runs the identical POSIX code path as native Linux, so there is no separate install. Native Windows (Terminal/PowerShell/cmd) is **not yet supported** — it is on the roadmap; see [Native Windows support](docs/references/native-windows-support.md).

3. **An MCP-aware agent host.** **Claude Code** or **Codex CLI** is recommended for first install — both auto-load MCP from on-disk config (`.mcp.json` / `.codex/config.toml`), so the install flow runs with no manual UI step. **Cursor**, **Junie**, and **Antigravity** also auto-load MCP from a rendered config; **GitHub Copilot**, **Windsurf**, **Air**, and **Warp** attach by pasting the stdio entry into the host's own MCP settings — see [Host support](#host-support).

---

## Quick start

Two operator steps, one MCP restart, ~3 minutes if Python is ready. **The agent drives the install** — you drop the zip in your repo and say `Install Wavefoundry`; the agent does the rest.

> **Do not extract the zip yourself.** The agent unpacks it as the first step of the install. Dropping the still-zipped file at your repo root is correct.

### Install walkthrough

The install runs in **two phases** with an MCP host restart between them. Both phases are agent-driven — the only operator actions are dropping the zip, typing the install phrase, and restarting your host when the agent asks.

**(a) Drop the release zip at your repo root**

Go to [Releases](https://github.com/coryhacking/wavefoundry/releases) and download the asset attached to the **latest release**. Drop the zip — still zipped, do not extract — at the root of your target repository.

**(b) Type this shortcut phrase as a chat message to your AI agent:**

```
Install Wavefoundry
```

This is a **chat message** to your AI agent, not a shell command. The agent must already be open in your repository (the repo set as the working directory) and connected to a supported AI host:

- **Recommended for first install:** **Claude Code** or **Codex CLI** — both auto-load MCP from on-disk config, so the install runs with no manual UI step.
- **Also supported:** **Cursor**, **Junie**, **GitHub Copilot**, **Windsurf**, **Air**, **Warp**, **Antigravity** — see [Host support](#host-support) for the per-host attachment.

---

#### Phase 1 — Bootstrap the harness (no MCP yet)

The Wavefoundry MCP server is what Phase 1 installs, so this phase runs from your agent's general capabilities alone — no `wave_*` MCP tools are called yet. The agent:

- **Unpacks the release zip.** Signal: `.wavefoundry/`, `docs/`, and `.mcp.json` appear at your repo root.
- **Sets the lifecycle epoch** in `docs/workflow-config.json` (defaults to your project's first git commit date).
- **Runs `wf setup`** — the orchestrator that creates the shared tool venv at `~/.wavefoundry/venv/`, installs dependencies, builds the framework + project semantic indexes, writes `.wavefoundry/bin/` launchers and your host's MCP config, and dry-runs the MCP server to catch startup failures before you restart. Signal: setup exits 0; final summary line reports index-ready.
- **Stops and tells you to restart your MCP host.** This is the explicit Phase 1 → Phase 2 hand-off; don't try to continue in the current agent session.

> **Note on dependency install.** `wf setup` uses [`uv`](https://github.com/astral-sh/uv) when available with a **21-day package-age guard** (`--exclude-newer`) — a supply-chain safeguard that rejects packages published in the last 21 days. If `uv` is not present it is bootstrapped automatically; if that fails, `pip` is used with a warning.

---

#### → Restart your MCP host, then resume

Quit and relaunch your agent, or use your host's MCP reload command. After restart, the `wavefoundry` MCP server appears in your host's MCP server list and the agent can call `wave_*` tools.

**To resume, type `Install Wavefoundry` again.** The install shortcut is state-aware: when `.wavefoundry/install-log.md` already exists, the agent continues from the first unchecked row (which is Phase 2 row 2.1, `wave_install_audit(phase=1)`). No separate "start Phase 2" phrase is needed.

---

#### Phase 2 — Project discovery (MCP-driven)

With the MCP server reachable, the agent walks through `.wavefoundry/install-log.md` row-by-row, calling `wave_install_audit` between rows to enforce lint-as-you-go (lint errors and missing artifacts block advancement). Phase 2 bootstraps project-specific artifacts tailored to your repo — this is where Wavefoundry stops looking like a generic install and starts looking like *your* repo's framework. The agent:

- **Audits Phase 1 artifacts** (`wave_install_audit(phase=1)`) — recovers if any are missing.
- **Profiles your repo** — `docs/repo-profile.json` (archetype, traits, applicable factors), `docs/repo-index.md`.
- **Bootstraps the canonical `docs/` structure** — `architecture/`, `contributing/`, `plans/`, `references/`, `prompts/`, `waves/`, `agents/`.
- **Generates per-role agent docs** — `docs/agents/<role>.md` per enabled role, including the three council specialists (`wave-council`, `red-team`, `archetype-council`) loaded from their authoritative seeds.
- **Maps your architecture** — `docs/ARCHITECTURE.md` plus `current-state.md`, `domain-map.md`, `layering-rules.md`, `cross-cutting-concerns.md`, `data-and-control-flow.md`, `testing-architecture.md`.
- **Establishes posture** — `QUALITY_SCORE.md`, `RELIABILITY.md`, `SECURITY.md`, `PERFORMANCE.md` (when applicable).
- **Wires the docs gate**, **generates the prompt surface**, **bootstraps wave artifacts**, **synthesizes personas**, **bootstraps per-role journals**, and **registers drift expectations**.
- **Confirms complete.** Final `wave_install_audit()` returns `{status: "complete"}`. The agent delivers an operator summary covering what was seeded, the workflow, commands, roles, and the docs gate.

---

## What is installed

After `Install Wavefoundry` finishes, your repository has the following shape. It's durable — across upgrades, the same paths appear in the same places.

### In your repository

```
.wavefoundry/
  framework/         Framework code, seeds, dashboard assets
  bin/               Repo-local CLI shims
  index/             Local semantic + graph indexes (LanceDB)      *
  logs/              Build, upgrade, dashboard logs                *
docs/
  prompts/           Public command catalog
  waves/             Wave records — your delivery history
  plans/             Change docs being authored
  architecture/      Architecture docs
  agents/            Agent role docs, journals, session handoff
  references/        Long-form project references
AGENTS.md            Agent-facing entry surface
CLAUDE.md            Claude Code-specific entry surface
.mcp.json            MCP server stdio entry
```

\* `.wavefoundry/index/` and `.wavefoundry/logs/` are gitignored — per-machine and regenerable. A few host-local runtime artifacts are also gitignored: `.wavefoundry/guard-overrides.json`, `.wavefoundry/dashboard-server.json`, `.wavefoundry/*.lock`, `.wavefoundry/framework/test-cache.json`.

Wavefoundry writes only to the paths above. The framework itself is committed so everyone on the team has the same version locked in the repo. If you run a host-specific renderer (Claude Code, Cursor, Codex, Junie, GitHub hooks), those write to `.claude/`, `.cursor/hooks.json`, `.codex/config.toml`, `.junie/`, and/or `.github/hooks/` — all committed.

What each `docs/` subdirectory carries — the agent reads these to ground its work:

- **`docs/prompts/`** — the catalog the agent looks up to route shortcut phrases (`Plan feature`, `Create wave`, and the rest).
- **`docs/waves/`** — your delivery history. Each closed wave is a committed record of who decided what, who reviewed, and what shipped.
- **`docs/plans/`** — staging area for change docs being authored before admission into a wave.
- **`docs/architecture/`** — domain map, layering rules, current-state snapshots, data/control flow, ADRs. The agent reads this before drafting plans so it doesn't violate boundaries.
- **`docs/agents/`** — role docs (wave-coordinator, planner, reviewer specialists), persona definitions, journals, and the session handoff file. The agent reads its own role description and any active watchpoints before each step.
- **`docs/references/`** — durable project context: memory, known pitfalls, project overview.

### On your user home directory

| Path | What it is |
|---|---|
| `~/.wavefoundry/venv/` | Shared tool venv (dependencies — LanceDB, ONNX, etc.) |
| `~/.wavefoundry/cache/fastembed/` | Embedding + reranker model weights (FastEmbed-quantized ONNX), fetched from Hugging Face on first index build, cached thereafter |

### Network footprint

**Zero at runtime to Wavefoundry-controlled endpoints.** Embedding model weights are fetched from Hugging Face on the first index build and cached locally thereafter. Dependencies are installed via `uv` (or `pip` fallback) during `wf setup` and during framework upgrades. No service, no account, no telemetry.

---

## Your first wave

Three turns of conversation, end to end. Step 3 includes a structural refusal you can't talk past — that's the point of the framework.

### 1. Plan a change

```
> Plan feature: add /healthz endpoint to the API server

[agent reads docs/architecture/, drafts the change doc]

Agent: I've drafted docs/plans/12abc-feat add-healthz-endpoint.md
with Rationale, Requirements, Acceptance Criteria, Tasks, and Risks.
Want me to admit it into a new wave?

> yes, create a wave for it
```

The agent created a *change doc* (the planning artifact for one unit of work) and is ready to roll it into a *wave* (the delivery unit that admits one or more changes).

### 2. Create wave, admit, prepare

```
> Create wave: api-healthz

Agent: Created docs/waves/12abd api-healthz/wave.md. Admitting 12abc...
       Wave status: planned, 1 admitted change.

> Prepare wave

Agent: Running readiness checks…
       - Change docs complete: ✓
       - AC priority recorded: ✓
       - Required review lanes selected: code-review, qa-review: ✓
       - Wave Council readiness review: PASS
       Wave status: active. Pre-implementation review gate next.
```

`Prepare wave` is a real gate. Docs-lint must pass. Every admitted change doc must be complete. AC priority must be recorded. When configured, a structured council review must record `wave-council-readiness`. Only then is the wave **readied** — it stays `planned`; a separate, single-OPEN-gated step (`Implement wave`) opens it to `active`/`implementing`. Any number of waves can be planned and readied in parallel; only one may be OPEN at a time.

### 3. Implement, review, close

```
> Implement wave

[agent edits api/server.py, adds tests, runs them]

Agent: Implementation complete. Tests pass. Review lanes:
       code-review: approved
       qa-review: approved
       Ready to close?

> Close wave

Agent: wave_close returned an error.
       Diagnostic: operator_signoff_missing
       Recovery: operator must record `operator-signoff: approved`
       in ## Review Evidence on wave.md before close can succeed.

> approved, go ahead and close

Agent: Recorded operator-signoff. Running wave_close again…
       Wave closed. 1 change implemented. Session handoff updated.
```

That first-attempt refusal is the point. `wave_close` blocks structurally — the agent could not have talked its way past it. The gate is the framework, not the prompt.

> *Want to see this visually? Run `Start dashboard` to open a local web UI showing wave state, AC and task progress, and review evidence at a glance.*

---

## Core concepts

### Lifecycle

A change doc enters the pipeline by being admitted into a wave. The wave moves through five phases — **plan change(s)**, **prepare wave**, **implement**, **review**, **close** — and two of those phases are *enforced gates*:

- **`Prepare wave`** blocks until docs lint passes. AC priority must be recorded on every admitted change. When configured, a structured council readiness review must be recorded.
- **`Close wave`** blocks until every required reviewer lane has recorded a signoff and the operator has confirmed closure.

The agent cannot route around either gate. The transcript above shows what the refusal looks like when one of the prerequisites is missing.

### Waves

A *wave* is the delivery unit. Work is admitted into a wave as one or more *change docs*, gated through `Prepare wave`, implemented through `Implement wave`, reconciled through `Review wave`, and sealed by `Close wave`.

**Closest analogue:** a feature branch combined with a release notes draft. **Key difference:** the wave's lifecycle has *enforced gates* — the framework refuses to close when prerequisites aren't met, rather than relying on soft conventions.

### Change docs

A *change doc* is the structured planning artifact for one unit of work: Rationale, Requirements, Acceptance Criteria, Tasks, Risks, Decision Log.

**Closest analogue:** a GitHub Issue plus a design doc plus an internal RFC. **Key difference:** the change doc lives next to the code in your repo (`docs/plans/` during planning, `docs/waves/<wave-id>/` after admission) and is what the agent reads, edits, and the framework lints.

### Seeds

*Seeds* are numbered prompt bodies — currently `001` through `250+` — that define how agents should behave at each lifecycle step. They live in `.wavefoundry/framework/seeds/` and cover everything from installing the framework to running adversarial council reviews.

**Closest analogue:** a style guide combined with operational runbooks. **Key difference:** the seeds are indexed and retrievable by the MCP server (`seed_get`, `docs_search`), so the agent reaches for them inline rather than re-reading them on every interaction.

### Feedback sensors

Two kinds: **computational sensors** (linters, validators, gate scripts that block when checks fail) and **inferential sensor lanes** (LLM-based code-review, architecture-review, security-review, qa-review, etc., recorded as structured evidence on the wave). Secrets detection is a built-in computational sensor — it scans for hardcoded credentials on every wave and blocks close until every finding is classified.

**Closest analogue:** CI pipelines combined with PR review assignments. **Key difference:** sensors record their findings as structured evidence on the wave doc itself, and `wave_close` blocks until required-lane signoffs are present.

### MCP server

A local MCP server (`wavefoundry`) exposes tools that operate on your repository's own files. It runs alongside your agent's host. No service, no account, no telemetry.

**Closest analogue:** a CLI you'd invoke yourself with structured I/O. **Key difference:** the agent calls the tools directly during conversation, so the lifecycle gates fire mid-conversation rather than only when you remember to run a check.

---

## Host support

Any MCP-aware host can attach to the local Wavefoundry server. For some hosts, `wf render-surfaces` writes the config for you; for the others, you paste the stdio entry into the host's MCP settings yourself.

| Host | What to do |
|---|---|
| **Claude Code** | `wf render-surfaces --platform claude` |
| **Codex CLI** | The committed `.codex/config.toml` loads on project trust |
| **Cursor** | `wf render-surfaces --platform cursor` |
| **Junie** | `wf render-surfaces --platform junie` |
| **GitHub Copilot · Windsurf · Air · Warp** | Paste the stdio entry from [`docs/prompts/install-wavefoundry.prompt.md`](docs/prompts/install-wavefoundry.prompt.md) into your host's MCP settings |
| **Antigravity** | `wf render-surfaces --platform antigravity` |

---

## Day-to-day phrases

You'll use about six phrases day-to-day; the rest of the surface is there when you need it.

- `Plan feature` — author a change doc
- `Create wave` — open a delivery unit
- `Add change to wave` — admit a change to the active wave
- `Prepare wave` — readiness gate before implementation
- `Implement wave` — coordinator-managed implementation loop with review lanes
- `Close wave` — structured closure with operator signoff

The [full tool surface](docs/prompts/index.md) covers wave admin, code search, graph queries, dashboard control, gate management, and adversarial review. The catalog is searchable from inside the agent (`docs_search`, `code_ask`).

---

## For enterprise forks

If you fork Wavefoundry for internal distribution, the upstream GitHub URLs above (`github.com/coryhacking/wavefoundry/releases`, the version badge's **link target**, and the link inside the bundled `install/install-block.md`) need to point at your fork. The version badge **image** is now a static shields badge whose value `build_pack.py --release` stamps automatically, so it's fork-stable — only its link target needs redirecting. The shortcut phrase, the install flow, and the in-zip surfaces are fork-stable; only the download/release-page links need redirecting.

Specific places to update when you fork:

- This `README.md` — the version badge's **link target** (line ~3; the badge image is static and its version is auto-stamped by `build_pack --release`) and the Releases download link in **Quick start → (a)**.
- `.wavefoundry/framework/install/install-block.md` — the README link near the bottom. This block is auto-prepended to every release's notes by `build_pack.py --release`, so the link follows your fork's release pages.
- Any internal docs or onboarding decks that quote the install steps verbatim.

The framework intentionally does not auto-detect "what fork is this" — the GitHub remote URL is the source of truth, but the install surfaces are static so that an air-gapped operator can still read them. Forks own the redirection step.

## For teams

Three questions a team evaluating Wavefoundry typically asks.

### Adoption cost

Install, drive a small wave end-to-end, and decide whether the discipline fits your codebase. The framework provisions per-repo and lives entirely in your repo plus `~/.wavefoundry/`. No infrastructure to operate, no shared service to run.

### Lock-in 

All planning artifacts (change docs, wave records) are Markdown in your `docs/` tree. They're readable, grep-able, and survive Wavefoundry being deleted. The semantic index in `.wavefoundry/index/` is regenerable from source. Removing Wavefoundry is `rm -rf .wavefoundry/` plus `rm .mcp.json AGENTS.md CLAUDE.md` if you don't want the host shims — your `docs/` directory still tells the story of what was shipped.

### Security 

Local-only operation. No network calls at runtime to Wavefoundry-controlled endpoints. No service, no account, no telemetry. Embedding model weights fetched from Hugging Face on first index build, cached locally. Dependencies installed via `uv` with a supply-chain age guard during install and upgrade. Audited file-write surface — Wavefoundry never edits files outside the paths shown in [What got installed](#what-got-installed).

Credential scanning is built in: the framework checks every project file against a community Gitleaks ruleset and blocks wave closure until findings are classified. Your `docs/scan-rules.toml` extends or overrides the framework defaults for project-specific needs.

---

## Upgrading

```
Upgrade wave framework
```

The agent detects framework drift, reconciles prompts and hook surfaces, runs the docs gate, restarts the MCP server, and updates the semantic index. The upgrader searches the project root, `~/.wavefoundry/`, and `~/.wavefoundry/dist/` for the highest semver zip available.

---

## Contributing

Wavefoundry uses the Wave Framework to develop itself. The maintainers use the same MCP tools — semantic search, code-graph queries, lifecycle gates — that ship to downstream projects. The wave directory in this repository is the worked evidence.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute.

## Security

See [SECURITY.md](SECURITY.md) — local-first means no service to attack, but the supply-chain surface (`uv`, dependency install) is still real. Wavefoundry also scans your project files for hardcoded credentials using a built-in Gitleaks-based ruleset; findings are tracked in `docs/scan-findings.json` and must be resolved before a wave can close.

## License

Apache 2.0 — see [LICENSE](LICENSE).
