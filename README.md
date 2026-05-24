# Wavefoundry

Wavefoundry is an agent operating framework for software repositories. It gives AI coding agents a structured, auditable way to plan, execute, review, and close work — and ships as a local MCP server that agents connect to directly.

Current version: **2026-05-06g**

---

## What It Does

When an AI agent works on a software project, it typically operates with no memory of prior decisions, no enforcement of process, no structured handoff between sessions, and no way to verify that what it did matches what was intended. The result is drift: half-finished work, bypassed reviews, documentation that diverges from code, and coordination that only works when the same context is still in the conversation window.

Wavefoundry addresses this by giving agents a persistent operating surface: a set of documents, tools, and conventions that let agents plan work, admit it into tracked delivery units called *waves*, gate implementation behind readiness checks, record reviews, and seal closure with structured evidence. Agents interact with this surface through a local MCP server — a set of tools that run in the same process as the agent's host and operate on the repository's own files.

---

## Core Concepts

### Waves

A *wave* is the delivery unit. Work is never planned directly into production — it is first authored as a change document, admitted into a wave, and then implemented through the wave lifecycle. This keeps scope explicit, makes handoffs durable, and gives every closed wave a permanent record of what was decided and why.

```
Plan feature → Create wave → Add change → Prepare wave → Implement → Review → Close wave
```

Each step has a gate. `Prepare wave` runs a readiness check before any code is touched. `Review wave` enforces required reviewer lanes — including project-declared inferential sensor lanes that run LLM-based security, performance, and architecture reviewers. `Close wave` blocks until operator signoff and all required lanes are recorded.

### Seeds

Seeds are numbered prompt documents (001–214 and growing) that define how agents should behave at each lifecycle step. They live in `.wavefoundry/framework/seeds/` and cover everything from installing the framework to reviewing architecture to triaging sensor findings by severity. Seeds are the framework's long-term memory — they encode hard-won operational lessons in a form agents can retrieve and apply.

### The MCP Server

The local MCP server (`server.py`) exposes 47 tools across four surfaces:

- **Wave lifecycle** — `wave_current`, `wave_prepare`, `wave_review`, `wave_close`, `wave_run_sensors`, and the full creation and mutation surface
- **Docs and code search** — `docs_search` (semantic + lexical fallback), `code_search`, `code_read`, `code_definition`, `code_references`, `code_ask`
- **Audit and health** — `wave_audit`, `wave_validate`, `wave_garden`, `wave_index_health`, `wave_index_build`
- **Framework navigation** — `seed_get`, `wave_help`, `wave_map`, `wave_get_prompt`

The server runs locally over stdio — no hosted service, no network dependency, no data leaving the machine.

### The Feedback Harness

Beyond process gates, Wavefoundry ships a three-dimension feedback harness based on Böckeler's harness engineering model:

- **Maintainability** — computational sensors: project-registered shell commands run via `wave_run_sensors` before reviewer lanes; pass/fail determined by exit code
- **Architecture** — inferential sensor lane: `architecture-reviewer` (seed 214) reads project architecture docs and assesses layer violations, boundary crossings, and decision conflicts
- **Behaviour** — inferential sensor lanes: `security-reviewer` (seed 213) and `performance-reviewer` (seed 212) assess their respective dimensions

Projects declare which lanes are required in `docs/workflow-config.json`. `wave_review` enforces them structurally — a missing declared lane blocks `wave_close` the same way a missing operator signoff does.

Sensor findings carry a severity (`critical`, `high`, `medium`, `low`, `none`). `wave_review` aggregates severity across all recorded signoffs and emits a `high_severity_finding` advisory when the worst finding is `critical` or `high`.

### The Semantic Index

The framework ships a local semantic search index built on `fastembed` and `BAAI/bge-base-en-v1.5`. It indexes project docs and code separately, runs entirely offline, and supports incremental updates driven by post-edit hooks. `docs_search` falls back to lexical search when the index is unavailable, so MCP tools always return something useful.

---

## Repository Layout

```
wavefoundry/
  .wavefoundry/framework/
    seeds/        Numbered seed prompts (001–214+)
    scripts/      Framework tooling: server, indexer, chunker, lint, gardener,
                  lifecycle ID, packaging, platform surface rendering
    index/        Packaged framework semantic index (ships in the distribution zip)
    VERSION       Current distribution version
    MANIFEST      File manifest for pack-aware upgrade pruning
  docs/           Wavefoundry's self-hosted operating surface
    waves/        Closed and active wave records
    agents/       Role docs, journals, personas, session handoff
    architecture/ Architecture docs (current-state, layering rules, domain map, etc.)
    contributing/ Build, verification, workflow, review-and-evals docs
    prompts/      Public command catalog and agent-oriented prompt bodies
    references/   Project overview, context memory, tech debt tracker
    workflow-config.json  Lifecycle epoch, review policies, sensor config, index roots
  AGENTS.md       Root agent entry map with shortcuts, stage gate, git policy
  README.md       This file
```

---

## Getting Started

### Installing in a target repository

Drop the distribution zip at the root of the target repository and run:

- `wavefoundry-YYYY-MM-DDx.zip` for the one-time `0.9.0` bridge release
- `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` for `1.0.0` and later

```
Install Wavefoundry
```

The agent unpacks the zip, bootstraps the full operating surface, registers the MCP server with the host, and hands off a summary. After install, restart the MCP server and run:

```
wave_index_build(content="docs", mode="update")
```

### Upgrading an existing install

```
Upgrade Wavefoundry
```

The agent detects drift, reconciles prompts and hook surfaces, runs the docs gate, restarts MCP, and updates the index. If `CHUNKER_VERSION` changed in the new pack, a full rebuild is required — `wave_index_health` will report `chunker_version_mismatch`.

### Working on Wavefoundry itself

Wavefoundry uses the Wave Framework to develop itself. The self-hosting boundary:

- `.wavefoundry/framework/` — canonical framework source; edits here change the framework for all downstream repositories
- `docs/` — Wavefoundry's own project operating surface

Before editing seeds, open the `seed_edit_allowed` gate. Before broad framework edits, open `framework_edit_allowed`. Both gates are checked by pre-edit hooks and closed automatically at wave close.

Supported operator environments for Wavefoundry itself:

- macOS: supported natively
- Linux: supported natively
- Windows: supported through WSL2 for now; native Windows operator workflows are not yet a public support target because some launchers and upgrade steps still assume a POSIX shell
- **Python ≥ 3.11 required.** `setup_wavefoundry.py` is the preferred bootstrap entrypoint. It creates and manages a shared tool environment at `~/.wavefoundry/venv` (override with `$WAVEFOUNDRY_TOOL_VENV`) and then runs the index setup flow. `setup_index.py` remains supported as the underlying compatibility entrypoint; neither modifies system Python.

**Distribution directories:** Built zips land in `~/.wavefoundry/dist/` by default. For semver-era upgrades, the upgrader searches the project root, `~/.wavefoundry/`, and `~/.wavefoundry/dist/`, then picks the highest semver zip automatically.

**Versioning:** Releases use `MAJOR.MINOR.PATCH` semver. Build artifacts carry the rightmost 4 characters of the lifecycle prefix as build metadata (`1.0.0+2tm5` in `VERSION`; `wavefoundry-1.0.0.2tm5.zip` as the filename). See `docs/architecture/decisions/12tm5-adr semver-versioning-contract.md` for the version bump policy.

```bash
# Package a new distribution (version required)
python3 .wavefoundry/framework/scripts/build_pack.py --version 1.0.0

# Run framework tests
python3 .wavefoundry/framework/scripts/run_tests.py

# Docs gate
wave_garden() then wave_validate()
```

---

## Design Principles

**Local-first.** The server runs as a subprocess in the agent's host process. No hosted service, no accounts, no data leaving the machine. The semantic index is built and queried offline.

**File-based state.** All wave state, change records, review evidence, and configuration live in ordinary Markdown and JSON files in the repository. Nothing is hidden in a database. Agents and humans can read, edit, and version-control everything.

**Structural enforcement over convention.** Gates are enforced by the server, not by agent instruction. `wave_close` will not succeed without operator signoff and all required lane signoffs recorded in the wave file. The harness dimensions are declared in config and enforced the same way.

**Feedforward and feedback together.** Seeds (feedforward) guide agents through correct behavior. Sensors and reviewers (feedback) catch what the feedforward missed. Both are necessary; neither alone is sufficient.

**Framework as a deployable artifact.** Wavefoundry ships as a dated zip that any repository can install or upgrade. The framework evolves in Wavefoundry's own wave process, gets packaged, and propagates to downstream projects through a standard upgrade flow.

---

## Non-Goals

- Not specific to any one target repository or language
- Not a hosted service — no network dependency for install, upgrade, validation, indexing, or packaging
- Not a replacement for human review — the harness directs attention, it does not eliminate judgment
- Not a code generator — Wavefoundry structures how agents work, not what they produce
