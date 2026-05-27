# Wavefoundry

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.11-blue)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-1.0.1-purple)](CHANGELOG.md)

Wavefoundry is an agent harness for software repositories. It wraps AI coding agents with feedforward guidance — numbered seed prompts for every lifecycle step — and feedback sensors — computational sensors and inferential reviewer lanes — that enforce structured, auditable delivery. It ships as a local MCP server that agents connect to directly.

**Status:** 1.0.1 — actively developed, single maintainer. The framework is self-hosted: Wavefoundry uses the Wave Framework to develop itself.

---

## The problem

When an AI agent works on a software project, it typically operates with no memory of prior decisions, no enforcement of process, no structured handoff between sessions, and no way to verify that what it did matches what was intended. The result is drift: half-finished work, bypassed reviews, documentation that diverges from code, and coordination that only works when the same context is still in the conversation window.

## What Wavefoundry does about it

Wavefoundry gives agents a persistent operating surface: a set of documents, tools, and conventions that let agents plan work, admit it into tracked delivery units called *waves*, gate implementation behind readiness checks, record reviews, and seal closure with structured evidence. Agents interact with this surface through a local MCP server — a set of tools that run in the same process as the agent's host and operate on the repository's own files.

No hosted service. No accounts. No data leaving the machine.

---

## Quick start

### Requirements

- **Python 3.11+**
- **macOS** or **Linux** (Windows via WSL2)
- An **MCP-aware agent host**: Claude Code, Cursor, Codex, GitHub Copilot, Junie, Windsurf, Air, or Warp

### Option A: Install into an existing repository

Download the latest release zip from [Releases](https://github.com/coryhacking/wavefoundry/releases), drop it at the root of your target repository, and tell your agent:

```
Install Wavefoundry
```

The agent unpacks the zip, bootstraps the full operating surface, registers the MCP server, and hands off a summary. Then run the semantic index setup:

```bash
python3 .wavefoundry/framework/scripts/setup_wavefoundry.py
```

This creates a shared tool environment at `~/.wavefoundry/venv` (override with `$WAVEFOUNDRY_TOOL_VENV`), installs all framework dependencies, and builds the local semantic index. It does not modify your system or project Python.

Dependencies are installed via `uv` with a **21-day package age guard** (`--exclude-newer`), which rejects packages published in the last 21 days as a supply-chain safeguard. If `uv` is not present it is bootstrapped automatically; if that fails, `pip` is used with a warning.

### Option B: Build from source

```bash
git clone https://github.com/coryhacking/wavefoundry.git
cd wavefoundry

# Bootstrap the tool venv and semantic index
python3 .wavefoundry/framework/scripts/setup_wavefoundry.py

# Package a distribution zip (lands in ~/.wavefoundry/dist/)
python3 .wavefoundry/framework/scripts/build_pack.py --version 1.0.1
```

### Register the MCP server

After install, register the MCP server with your agent host:

| Host | How |
|---|---|
| **Claude Code** | Run `render_platform_surfaces --platform claude`. Claude Code discovers `.mcp.json` automatically. |
| **Cursor** | Run `render_platform_surfaces --platform cursor`. Enable under Cursor > Settings > MCP. |
| **Codex** | Project-local `.codex/config.toml` is committed — Codex loads the `wavefoundry` server automatically. Trust the project when prompted on first clone. |
| **Junie** | Run `render_platform_surfaces --platform junie`. |
| **Copilot / Windsurf / Air / Warp** | Add the stdio entry via your host's MCP settings. See [`docs/prompts/install-wavefoundry.prompt.md`](docs/prompts/install-wavefoundry.prompt.md). |

### Verify the install

After registering, restart the MCP server in your host and run:

```
wave_index_health()
wave_audit()
```

---

## Core concepts

### Waves

A *wave* is the delivery unit. Work is never planned directly into production — it is first authored as a change document, admitted into a wave, and then implemented through the wave lifecycle:

```
Plan feature > Create wave > Add change > Prepare wave > Implement > Review > Close wave
```

Each step has a gate. `Prepare wave` runs a readiness check before any code is touched. `Review wave` enforces required reviewer lanes — including inferential sensor lanes that run LLM-based security, performance, and architecture reviewers. `Close wave` blocks until operator signoff and all required lanes are recorded.

### Seeds

Seeds are numbered prompt documents (001-214 and growing) that define how agents should behave at each lifecycle step. They live in `.wavefoundry/framework/seeds/` and cover everything from installing the framework to reviewing architecture to triaging sensor findings by severity. Seeds are the framework's long-term memory — they encode hard-won operational lessons in a form agents can retrieve and apply.

### The MCP server

The local MCP server exposes 47 tools across four surfaces:

- **Wave lifecycle** — `wave_current`, `wave_prepare`, `wave_review`, `wave_close`, `wave_run_sensors`, and the full creation and mutation surface
- **Docs and code search** — `docs_search` (semantic + lexical fallback), `code_search`, `code_read`, `code_definition`, `code_references`, `code_ask`
- **Audit and health** — `wave_audit`, `wave_validate`, `wave_garden`, `wave_index_health`, `wave_index_build`
- **Framework navigation** — `seed_get`, `wave_help`, `wave_map`, `wave_get_prompt`

The server runs locally over stdio — no hosted service, no network dependency.

### The feedback harness

Wavefoundry ships a three-dimension feedback harness based on Bockeler's harness engineering model:

- **Maintainability** — computational sensors: project-registered shell commands run via `wave_run_sensors` before reviewer lanes; pass/fail determined by exit code
- **Architecture** — inferential sensor lane: `architecture-reviewer` reads project architecture docs and assesses layer violations, boundary crossings, and decision conflicts
- **Behaviour** — inferential sensor lanes: `security-reviewer` and `performance-reviewer` assess their respective dimensions

Projects declare which lanes are required in `docs/workflow-config.json`. `wave_review` enforces them structurally — a missing declared lane blocks `wave_close`.

### The semantic index

The framework ships a local semantic search index built on `fastembed` and `BAAI/bge-base-en-v1.5`. It indexes project docs and code separately, runs entirely offline, and supports incremental updates driven by post-edit hooks. `docs_search` falls back to lexical search when the index is unavailable.

---

## Repository layout

```
wavefoundry/
  .wavefoundry/framework/
    seeds/        Numbered seed prompts (001-214+)
    scripts/      Framework tooling: server, indexer, chunker, lint, gardener,
                  lifecycle ID, packaging, platform surface rendering
    VERSION       Current distribution version
  docs/           Project operating surface
    waves/        Closed and active wave records
    agents/       Role docs, journals, personas, session handoff
    architecture/ Architecture docs, ADRs, threat model
    contributing/ Build, verification, workflow, review-and-evals docs
    prompts/      Public command catalog and agent-oriented prompt bodies
    references/   Project overview, context memory, tech debt tracker
    workflow-config.json  Lifecycle epoch, review policies, sensor config
  AGENTS.md       Root agent entry map
  CLAUDE.md       Claude Code thin pointer to AGENTS.md
  README.md       This file
```

---

## Upgrading

Tell your agent:

```
Upgrade Wavefoundry
```

The agent detects drift, reconciles prompts and hook surfaces, runs the docs gate, restarts MCP, and updates the index. The upgrader searches the project root, `~/.wavefoundry/`, and `~/.wavefoundry/dist/` for the highest semver zip automatically.

---

## Design principles

**Local-first.** The server runs as a subprocess in the agent's host process. No hosted service, no accounts, no data leaving the machine. The semantic index is built and queried offline.

**File-based state.** All wave state, change records, review evidence, and configuration live in ordinary Markdown and JSON files in the repository. Nothing is hidden in a database. Agents and humans can read, edit, and version-control everything.

**Structural enforcement over convention.** Gates are enforced by the server, not by agent instruction. `wave_close` will not succeed without operator signoff and all required lane signoffs recorded in the wave file.

**Feedforward and feedback together.** Seeds (feedforward) guide agents through correct behavior. Sensors and reviewers (feedback) catch what the feedforward missed. Both are necessary; neither alone is sufficient.

**Framework as a deployable artifact.** Wavefoundry ships as a zip that any repository can install or upgrade. The framework evolves in Wavefoundry's own wave process, gets packaged, and propagates to downstream projects through a standard upgrade flow.

---

## Non-goals

- Not specific to any one target repository or language
- Not a hosted service — no network dependency for any operation
- Not a replacement for human review — the harness directs attention, it does not eliminate judgment
- Not a code generator — Wavefoundry structures how agents work, not what they produce

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, wave workflow expectations, and pull request guidelines.

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

## Security

To report a vulnerability, see [`SECURITY.md`](SECURITY.md). Do not open a public issue.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).

```
Copyright 2026 Cory Hacking
```
