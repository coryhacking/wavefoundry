# Project Overview — Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-07-20

## What Wavefoundry Is

Wavefoundry is the agent harness for the repositories it is installed in — the persistent operating layer that wraps AI coding agents with feedforward guidance (seed prompts), feedback sensors (computational and inferential reviewer lanes), and structural lifecycle enforcement. It ships as a local MCP server and a set of plain-file documents that survive context loss.

As a project, Wavefoundry is the canonical repository for the Wave Framework and its local MCP server. It owns the seed prompts, framework scripts, packaging logic, migration helpers, the optional local dashboard surface, and the MCP tool surface that makes framework-aware work searchable, auditable, and operable across target repositories.

**Wavefoundry is a harness and tooling repository, not a target product repository.** It does not ship a networked product application. Its deliverables are:

1. **The Wave Framework seed pack** — numbered seed prompts (001–214+) and reference docs packaged into dated `.zip` distributions and installed into target repositories.
2. **Framework scripts** — CLI tools for lifecycle ID generation, docs linting, docs gardening, platform surface rendering, packaging, test running, index building, and local dashboard serving.
3. **Local MCP server** — a local-only stdio server exposing structured tools for wave lifecycle management, semantic search, code navigation, secrets scanning, audit, and feedback harness operation.
4. **Local dashboard surface** — a loopback-only operational dashboard served from `.wavefoundry/framework/dashboard/` by `.wavefoundry/framework/scripts/dashboard_server.py`.

For a full conceptual overview see `docs/references/wavefoundry-overview.md`.

## Supported Platforms

Wavefoundry is local-only and runs wherever a supported Python and AI host run. The single source of truth for platform support:

| Platform | Status | Notes |
| --- | --- | --- |
| **macOS** (Apple Silicon + Intel) | **Supported** | Primary dev platform. Apple Silicon gets CoreML/GPU embedding acceleration; Intel runs CPU. |
| **Linux** (x86_64 / arm64) | **Supported** | Continuously exercised (dev/CI). CPU embedding by default; NVIDIA CUDA used when present. |
| **Windows via WSL2** | **Supported** | WSL2 **is** Linux — it runs the identical POSIX code path (`os.name == 'posix'`, `bin/python`, `fcntl`, `os.kill`, shebang launchers) with no separate install and no special flags. CUDA works via WSL2 GPU passthrough; CoreML/DirectML do not apply (CPU otherwise). See the WSL2 gotchas below. |
| **Native Windows** (Terminal / PowerShell / cmd) | **Supported** | Requires `python3` 3.11 or higher on PATH — verify with `python3 --version` before install. Windows may ship `python` but not `python3`; if so, install a distribution that provides `python3` (e.g. from python.org) and ensure it is on PATH. See `docs/references/native-windows-support.md` for setup notes. |

**WSL2 gotchas** (the few that matter — all are environment setup, not framework config):

1. **Keep the repo on the Linux filesystem** (`~/projects/...`), **not** a Windows drive mount (`/mnt/c/...`). DrvFs cross-OS I/O is dramatically slower and will make index builds and file-watching crawl.
2. **The tool venv lives inside the WSL2 distro** at `~/.wavefoundry/venv` — not under the Windows `%USERPROFILE%`. Run setup from inside WSL2.
3. **GPU:** NVIDIA CUDA works via WSL2 GPU passthrough (`nvidia_gpu_present` detects it); CoreML (macOS) and DirectML (native Windows) do not apply under WSL2.

**Validation status:** the Linux/POSIX path is exercised continuously (the framework is POSIX; dev and CI run on macOS/Linux), and WSL2 runs that same path. A dedicated WSL2 smoke pass is published as a reproducible runbook at `docs/reports/wsl2-smoke-checklist.md` — a real WSL2 user (or a WSL2 box) can run it to confirm the blessed-target claim end to end.

## Orient with the codebase map first

Before grep-thrashing or opening files, read `docs/references/codebase-map.md` — a generated, graceful-scaling map of this project's own codebase (built offline from the persisted graph + community-cluster artifacts and refreshed with the index build). It is the **index to the index**: it shows the bounded set of top-level areas, each with its responsibility, key files, and entry-point symbols, plus a drill-in handle. To go deeper, pass an area's stable `hub_node_id` to `code_graph_community`, or open its key files with `code_outline`. The map is read-only and regenerates on index build (or on demand via `wf codebase-map --root .`).

**Before working in an area, consult that area's `AGENTS.md` if one is present** — vendor-neutral per-area context (local conventions, gotchas, intent) for major areas only. The map links each area to its `AGENTS.md` when one exists; scaffold empty stubs with `wf codebase-map --scaffold-area-contexts` (humans author the content). The only `@import` is the root `CLAUDE.md` → `AGENTS.md` bridge; there are no per-folder `CLAUDE.md` bridge files.

## Repository Structure

```
wavefoundry/
  .wavefoundry/framework/seeds/    Canonical seed prompts (001–250 numbered)
  .wavefoundry/framework/scripts/  Framework tooling (lint, gardener, lifecycle ID, packaging, rendering, dashboard server)
  .wavefoundry/framework/dashboard/ Browser assets for the optional local dashboard
  .wavefoundry/framework/README.md Canonical prompt map, public commands, factor model
  .wavefoundry/framework/VERSION   Current distribution version — semver tracked at `.wavefoundry/framework/VERSION`; the README badge auto-syncs from the latest GitHub Release tag.
  docs/                            Wavefoundry self-hosted Wave Framework operating surface (this tree)
  AGENTS.md                        Root agent entry map with shortcuts, stage gate, git commits policy
  README.md                        Product README for Wavefoundry
```

## Self-Hosting Boundary

Wavefoundry uses the Wave Framework to develop itself:

- `.wavefoundry/framework/` is the **canonical framework directory**. Edits here change the framework for all target repositories. `build_pack.py` packages this directory into dated zip distributions for operators.
- `docs/` is **Wavefoundry's self-hosted project operating surface**. Plans, waves, architecture notes, agent roles, and journals live here.
- When `docs/` guidance conflicts with `.wavefoundry/framework/seeds/` on generic framework behavior, the seed source wins.
- When project-specific policy under `docs/` conflicts with generic framework defaults, the local policy governs Wavefoundry until a wave changes the framework default.

## Workflow Overview

Wavefoundry uses the Wave Framework lifecycle for its own development:

1. **Plan feature** — author a consolidated change doc at `docs/plans/`.
2. **Create wave / Add change to wave** — admit the change and make it wave-owned under `docs/waves/<wave-id>/`.
3. **Prepare wave** — confirm readiness (docs, AC priority, council verdict) and repair any admitted-doc placement drift. This **readies** the wave (it stays `planned`); `wf_prepare_wave(mode='ready')` readies without opening, so any number of waves can be readied in parallel.
4. **Implement wave / Implement feature** — **open** a readied wave (the single-OPEN activation step) and execute the admitted changes. Only one wave may be OPEN (`active`/`implementing`) at a time; the guard fires here, not at readiness.
5. **Review wave** — code review, QA, architecture review, and Wave Council delivery synthesis as required by policy and change type.
6. **Close wave / Finalize feature** — record closure, distill journals, promote memory, clear handoff.

See `AGENTS.md` for the shortcut phrase table and stage gate. See `docs/prompts/index.md` for the full public command catalog.

## Generic Agent Roles

Wavefoundry uses the standard Wave Framework generic roles:

| Role | Primary Responsibility |
|------|------------------------|
| `planner` | Authors change docs; performs discovery; plans waves |
| `wave-coordinator` | Admits work into waves; manages execution order; declares closure |
| `wave-council` | Synthesizes Wave Council readiness and delivery verdicts |
| `implementer` | Executes code changes per admitted change doc |
| `code-reviewer` | Reviews implementation correctness and pattern compliance |
| `architecture-reviewer` | Reviews boundary and layering impact |
| `qa-reviewer` | Reviews verification coverage and defect risk |
| `security-reviewer` | Reviews trust and safety boundaries |
| `docs-contract-reviewer` | Reviews behavioral spec consistency |
| `performance-reviewer` | Reviews performance and reliability impact |

Role docs live under `docs/agents/`. Factor-review agents for applicable factors live under `.claude/agents/`.

The framework ships `wave_review.enabled: true` by default so the Wave Council surface is available out of the box. When the operator opts into enforcement via `required_for_all_waves: true`, every wave also requires a universal two-phase Wave Council pass: one readiness pass before implementation and one delivery pass before closure. The wave-council owns those verdicts; the wave-coordinator still owns lifecycle routing.

## Project Personas

Wavefoundry has two active persona agents representing people who use or operate the system:

- **framework-operator** (`docs/agents/personas/framework-operator.md`) — developers who install and upgrade the Wave Framework in their own repositories, run lifecycle commands, and review diffs.
- **wave-coordinator** (`docs/agents/personas/wave-coordinator.md`) — operators who run wave lifecycle commands in target repositories: plan, prepare, review, and close waves.

## Key Configuration

| File | Purpose |
|------|---------|
| `docs/workflow-config.json` | Lifecycle epoch, wave settings, review policies, persona and factor policies, dashboard host/port preferences |
| `docs/repo-profile.json` | Project archetypes, traits, factor-review applicability, runtime-surface and design-sensitivity evidence |
| `docs/prompts/prompt-surface-manifest.json` | Machine-readable prompt surface catalog; includes `framework_revision` |
| `.wavefoundry/guard-overrides.json` | Temporary approval flags for seed/framework edits (gitignored) |

## How to Start

1. Read `AGENTS.md` → **Start Here** section to understand the shortcut phrase table, stage gate, and git commits policy.
2. Consult `docs/prompts/index.md` for the full public command surface.
3. For architecture context, start with `docs/ARCHITECTURE.md`.
4. For workflow details, see `docs/contributing/change-workflow.md` and `docs/contributing/feature-wave-lifecycle-overview.md`.
