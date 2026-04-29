# Project Overview — Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-04-28

## What Wavefoundry Is

Wavefoundry is the canonical repository for the Wave Framework and its future local MCP server. It owns the seed prompts, framework scripts, packaging logic, migration helpers, and the planned tool surface that makes framework-aware work searchable, auditable, and operable across target repositories.

**Wavefoundry is a framework and tooling repository, not a target product repository.** It does not ship a user-facing application. Its deliverables are:

1. **The Wave Framework seed pack** — prompts and reference docs packaged into dated `.zip` distributions and installed into target repositories.
2. **Framework scripts** — CLI tools for lifecycle ID generation, docs linting, docs gardening, platform surface rendering, packaging, and test running.
3. **Future local MCP server** — a local-only stdio server exposing structured tools for framework-aware inspection, validation, seed resolution, code search, and (eventually) mutation operations on target repositories.

## Repository Structure

```
wavefoundry/
  framework/seeds/         Canonical seed prompts (001–250 numbered)
  framework/scripts/       Framework tooling (lint, gardener, lifecycle ID, packaging, rendering)
  framework/README.md      Canonical prompt map, public commands, factor model
  framework/VERSION        Current distribution version (2026-04-28a)
  .wavefoundry/framework/  Symlink → ../framework (self-hosting mode)
  docs/                    Wavefoundry self-hosted Wave Framework operating surface (this tree)
  AGENTS.md                Root agent entry map with shortcuts, stage gate, git commits policy
  README.md                Product README for Wavefoundry
```

## Self-Hosting Boundary

Wavefoundry uses the Wave Framework to develop itself:

- `framework/` is the **canonical framework product source**. Edits here change the framework for all target repositories.
- `docs/` is **Wavefoundry's self-hosted project operating surface**. Plans, waves, architecture notes, agent roles, and journals live here.
- When `docs/` guidance conflicts with `framework/seeds/` on generic framework behavior, the seed source wins.
- When project-specific policy under `docs/` conflicts with generic framework defaults, the local policy governs Wavefoundry until a wave changes the framework default.

## Workflow Overview

Wavefoundry uses the Wave Framework lifecycle for its own development:

1. **Plan feature** — author a consolidated change doc at `docs/plans/`.
2. **Create wave / Add change to wave** — admit the change into `docs/waves/<wave-id>/`.
3. **Prepare wave** — relocate admitted change docs into the wave folder; confirm readiness.
4. **Implement wave / Implement feature** — execute the admitted changes.
5. **Review wave** — code review, QA, architecture review as required by the change type.
6. **Close wave / Finalize feature** — record closure, distill journals, promote memory, clear handoff.

See `AGENTS.md` for the shortcut phrase table and stage gate. See `docs/prompts/index.md` for the full public command catalog.

## Generic Agent Roles

Wavefoundry uses the standard Wave Framework generic roles:

| Role | Primary Responsibility |
|------|------------------------|
| `planner` | Authors change docs; performs discovery; plans waves |
| `wave-coordinator` | Admits work into waves; manages execution order; declares closure |
| `implementer` | Executes code changes per admitted change doc |
| `code-reviewer` | Reviews implementation correctness and pattern compliance |
| `architecture-reviewer` | Reviews boundary and layering impact |
| `qa-reviewer` | Reviews verification coverage and defect risk |
| `security-reviewer` | Reviews trust and safety boundaries |
| `docs-contract-reviewer` | Reviews behavioral spec consistency |
| `performance-reviewer` | Reviews performance and reliability impact |

Role docs live under `docs/agents/`. Factor-review agents for applicable factors live under `.claude/agents/`.

## Project Personas

Wavefoundry has two active persona agents representing people who use or operate the system:

- **framework-operator** (`docs/agents/personas/framework-operator.md`) — developers who install and upgrade the Wave Framework in their own repositories, run lifecycle commands, and review diffs.
- **wave-coordinator** (`docs/agents/personas/wave-coordinator.md`) — operators who run wave lifecycle commands in target repositories: plan, prepare, review, and close waves.

## Key Configuration

| File | Purpose |
|------|---------|
| `docs/workflow-config.json` | Lifecycle epoch, wave settings, review policies, persona and factor policies |
| `docs/repo-profile.json` | Project archetypes, traits, factor-review applicability |
| `docs/prompts/prompt-surface-manifest.json` | Machine-readable prompt surface catalog; includes `framework_revision` |
| `.wavefoundry/guard-overrides.json` | Temporary approval flags for seed/framework edits (gitignored) |

## How to Start

1. Read `AGENTS.md` → **Start Here** section to understand the shortcut phrase table, stage gate, and git commits policy.
2. Consult `docs/prompts/index.md` for the full public command surface.
3. For architecture context, start with `docs/ARCHITECTURE.md`.
4. For workflow details, see `docs/contributing/change-workflow.md` and `docs/contributing/feature-wave-lifecycle-overview.md`.
