# Agent Guide — Wavefoundry

## Start Here

Read in this order at the start of every session:

1. `docs/references/project-overview.md` — project orientation, workflow, roles
2. `docs/prompts/index.md` — shortcut phrase catalog (public command surface)
3. `docs/ARCHITECTURE.md` — architecture hub and child doc index
4. `docs/agents/session-handoff.md` — current session state (if work is in progress)

Before editing any repository code or framework seeds, read the **Stage Gate (repository code)** and **Framework Script Hygiene** sections below.

## Purpose

Wavefoundry is the repository for the Wave Framework and its local MCP server.

It owns the canonical framework source and provides local tooling for framework-aware work across target repositories. The MCP tool surface covers semantic search, wave inspection, change creation, and framework operations (lint, garden, sync surfaces).

Each target repository still owns its rendered local operating surface: `AGENTS.md`, `docs/prompts/`, `docs/agents/`, `docs/waves/`, `docs/plans/`, project specs, architecture docs, and workflow config.

The goal is not to hide the framework inside MCP. The goal is to make the canonical framework installable, upgradable, searchable, auditable, and operable while preserving explicit project-local instructions that agents can read without secret context.

## Product Boundary

This project is a framework and tooling repository, not a target product repository.

Wavefoundry should work against any explicitly configured target repository with Wave Framework state. Target examples in docs and tests must stay generic unless a fixture intentionally names a sample repository.

## Self-Hosting Boundary

Wavefoundry uses the Wave Framework to develop the Wave Framework.

This is intentional bootstrapping, not a source-of-truth collapse:

- `.wavefoundry/framework/` is the canonical framework product source: seed prompts, reference material, scripts, renderers, validators, packaging logic, and upgrade logic.
- `docs/` is Wavefoundry's self-hosted project operating surface: plans, waves, local prompt surfaces, agent roles, handoff, journals, MCP design docs, and project-specific decision records.
- Changes to framework behavior should be planned, reviewed, and closed through Wavefoundry's local `docs/` wave process.
- When `.wavefoundry/framework/seeds/` conflicts with rendered local prompt surfaces under `docs/prompts/`, treat `.wavefoundry/framework/seeds/` as source of truth for framework behavior.
- When project-specific process policy under `docs/` conflicts with generic framework defaults, treat the project-specific `docs/` policy as the local operating rule for Wavefoundry, then decide whether the framework default should be changed through an explicit wave.
- Install and upgrade tools should support a self-hosting mode where Wavefoundry is both the framework source repository and a target repository consuming rendered framework surfaces.
- Do not edit generated self-hosted surfaces as a substitute for fixing canonical framework seeds. If a rendered file is wrong because a seed is wrong, update the seed and regenerate or document the drift.

## Shortcut Phrases

Public Wave Framework commands for Wavefoundry's self-hosted surface. Full details in `docs/prompts/index.md`.

| Phrase | Purpose | Doc |
|--------|---------|-----|
| **Init wave framework** | Initialize Wave Framework in a target repo | `docs/prompts/install-wavefoundry.md` |
| **Upgrade wave framework** | Upgrade Wave Framework in a target repo | `docs/prompts/upgrade-wavefoundry.md` |
| **Plan feature** | Author a consolidated change doc | `docs/prompts/plan-feature.md` |
| **Create wave** | Create a wave record | `docs/prompts/create-wave.md` |
| **Add change to wave** | Admit a change doc into the active wave | `docs/prompts/add-change-to-wave.md` |
| **Remove change from wave** | Remove an admitted change | `docs/prompts/remove-change-from-wave.md` |
| **Prepare wave** / **Ready wave** | Confirm readiness before implementation | `docs/prompts/prepare-wave.md` |
| **Implement wave** | Coordinator-managed multi-change implementation | `docs/prompts/implement-wave.md` |
| **Implement feature** | Single-change docs-first implementation | `docs/prompts/implement-feature.md` |
| **Pause wave** | Park session state in handoff artifact | `docs/prompts/pause-wave.md` |
| **Review wave** | Run required review lanes | `docs/prompts/review-wave.md` |
| **Close wave** | Finalize and archive the wave | `docs/prompts/close-wave.md` |
| **Finalize feature** | Single-change closure path | `docs/prompts/finalize-feature.md` |
| **Interrogate this plan** | Stress-test a change doc before admission | `docs/prompts/interrogate-plan.md` |
| **Package Wavefoundry** | Build framework zip distribution | `.wavefoundry/framework/seeds/240-package-wavefoundry.prompt.md` |
| **Migrate to Wavefoundry** | Migrate a target repo from legacy layout | `.wavefoundry/framework/seeds/250-migrate-existing-wave-project.prompt.md` |

Legacy aliases: `Init wave context`, `Upgrade wave context`, `Package wave framework`, `Package wave context` — identical behavior; accept from operators and older docs.

## Stage Gate (repository code)

Applies to all repository code: framework scripts, seed prompts, test files, build manifests, and any checked-in code or config that affects shipped or verified behavior.

**Before the first code edit in a given effort, all three of the following must be true:**

1. A consolidated change document exists at `docs/plans/<change-id>.md` or `docs/waves/<wave-id>/<change-id>.md`.
2. The change is admitted into a wave via **Create wave** / **Add change to wave**.
3. The wave has a successful **Prepare wave** / **Ready wave** pass as the immediately preceding lifecycle step.

If any step is missing, stop and route back to **Plan feature**, **Create wave**, **Add change to wave**, or **Prepare wave**.

**Out of scope for this gate:**
- Documentation-only edits under `docs/` with no behavioral impact
- Prompt/framework docs edits that don't change repository code
- Operator-approved explicit waivers for a named scope (record in change doc or `docs/agents/session-handoff.md`)

## Implementation Guard (product code)

No product implementation source exists in this repository yet. When `src/wavefoundry/` or other implementation directories appear, add a full Implementation guard section at that time requiring a consolidated change document and clean **Prepare wave** before the first edit to those paths.

## Framework Script Hygiene

Run framework tests without writing bytecode:

```bash
python3 .wavefoundry/framework/scripts/run_tests.py
```

Or: `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests`

If `__pycache__` directories appeared anyway, clean them:

```bash
find .wavefoundry/framework/scripts -type d -name '__pycache__' -prune -exec rm -rf {} \;
```

## Git Commits (Operator-Owned)

Agents must **not** run `git commit` unless the operator explicitly instructs them to finalize that commit in the **current** request after reviewing the diff. Default agent behavior: hand off a suggested commit message and diff for the operator to commit locally.

This applies to all changes: framework source edits, self-hosted docs changes, platform surface renders, and packaging builds. See `docs/contributing/build-and-verification.md` **Git commits** for the full policy.

## Core Principles

- Local-only by default: no network dependency, no remote indexing, no hosted service requirement.
- Project-visible contracts: generated project-local files remain the operating contract for agents.
- Canonical source in one place: seed prompts, renderers, lifecycle rules, validators, and upgrade logic live here.
- MCP as capability, not identity: the MCP server is one Wavefoundry interface.
- Typed tools over arbitrary shell: MCP tools should expose structured operations rather than raw command execution.
- Read-first mutation model: tools should inspect, validate, and propose patches before writing where practical.
- Reusable target model: every tool should accept a target repository root or use configured allowed roots.
- Drift detection is a first-class feature: Wavefoundry should compare canonical framework state with project-local rendered surfaces.

## MCP Server

The Wavefoundry MCP server ships at `.wavefoundry/framework/scripts/server.py` and runs via stdio transport.

**Build the semantic index before first use:**

```bash
python3 .wavefoundry/framework/scripts/setup_index.py
```

This checks for the required runtime packages (`fastembed`, `numpy`, `mcp[cli]`) and builds the docs/seed index. If dependencies are missing, it prints an isolated tool-venv install command instead of modifying the system Python. Pass `--root <path>` to target a different repository. Semantic code embeddings are optional and slower; add `--include-code` only when needed. Code indexing defaults to source files only and skips tests/generated platform hooks; add `--include-tests` or `--include-generated` when those are useful. Wavefoundry framework internals under `.wavefoundry/framework/scripts/tests/` are never included in the semantic code index. The setup wrapper runs docs and code indexing in separate subprocesses to keep each pass isolated.

The project-local index is stored at `.wavefoundry/index/` (gitignored). Packaged framework docs/seeds are indexed at `.wavefoundry/framework/index/` during `Package Wavefoundry`, then searched as a read-only framework layer. The project-local index is rebuilt incrementally — the post-edit hook fires `indexer.py` as a background process after each file edit. The MCP server is registered in `.mcp.json` and `.junie/mcp/mcp.json`.

**Available tools:** `wave_help`, `wave_map`, `docs_search`, `code_search`, `seed_get`, `wave_current`, `wave_list_waves`, `wave_list_plans`, `wave_get_change`, `wave_get_prompt`, `wave_create_wave`, `wave_add_change`, `wave_remove_change`, `wave_prepare`, `wave_pause`, `wave_review`, `wave_close`, `wave_change_create`, `wave_new_feature`, `wave_new_bug`, `wave_new_enhancement`, `wave_new_refactor`, `wave_new_change`, `wave_new_documentation`, `wave_new_tech_debt`, `wave_new_task`, `wave_new_maintenance`, `wave_new_operations`, `wave_validate`, `wave_garden`, `wave_sync_surfaces`.

For change-plan creation, prefer MCP `wave_change_create` (or the `wave_new_*` compatibility wrappers). They wrap lifecycle ID generation and scaffold `docs/plans/<change-id>.md` in one call. Use `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>` only as a CLI fallback when MCP is unavailable, or for wave-folder IDs until lifecycle mutation tools exist.

## Repository Layout

Current repository shape:

```text
wavefoundry/
  AGENTS.md
  README.md
  docs/
  .wavefoundry/
    framework/
      README.md
      VERSION
      seeds/        ← canonical seed prompts and framework reference material
      scripts/      ← validation, packaging, rendering, MCP server, index builder
    index/          ← gitignored; generated by indexer.py
```

`.wavefoundry/framework/seeds/` contains canonical seed prompts and framework reference material. `.wavefoundry/framework/scripts/` contains framework validation, packaging, rendering, migration, maintenance, and MCP tooling.

## Target Repository Model

A target repository may contain:

- `AGENTS.md`
- `docs/prompts/`
- `docs/prompts/agents/`
- `docs/prompts/prompt-surface-manifest.json`
- `docs/agents/`
- `docs/agents/session-handoff.md`
- `docs/agents/journals/`
- `docs/waves/`
- `docs/plans/`
- `docs/workflow-config.json`
- `docs/repo-profile.json`
- project-specific `docs/specs/`, `docs/architecture/`, `docs/contributing/`, `docs/references/`

Wavefoundry may also support repositories that do not yet have these files, using install/bootstrap tools.

## What Wavefoundry Owns

- Canonical Wave Framework seed prompts.
- Framework reference docs.
- Renderers for project-local prompt and agent surfaces.
- Install and upgrade logic.
- Lifecycle ID generation.
- Wave validation and docs-lint style checks.
- Docs-gardener style metadata refresh.
- Framework packaging/export logic.
- Local MCP server tools.
- Optional local code index and source search.

## What Target Repositories Own

- Product code and product docs.
- Local rendered framework surfaces.
- Wave and plan records.
- Project-specific workflow config and repo profile.
- Product/persona/reviewer policy customizations.
- Any local modifications that should be preserved during upgrade.

## Initial MCP Tool Surface

Start with a small, reliable read-only tool set.

- `wave.current`
  - Return active wave, last closed wave, handoff state, admitted changes, and next lifecycle action.

- `wave.validate`
  - Run framework validation against a target repository and return structured failures.

- `wave.prompt_surface_audit`
  - Compare shortcut table, prompt index, manifest, seed references, and rendered local prompt bodies.

- `wave.resolve_seed`
  - Resolve `seed-175`, `prepare-wave`, or similar references to canonical files and generated local surfaces.

- `code.search`
  - Local exact search over target repository files.

- `code.read`
  - Read file ranges with line numbers.

Add `wave.lifecycle_id` early if lifecycle ID generation is needed before mutation tools.

## Later MCP Tool Surface

- `wave.lifecycle_id`
- `wave.install`
- `wave.upgrade`
- `wave.package`
- `wave.create`
- `wave.add_change`
- `wave.prepare`
- `wave.review`
- `wave.close`
- `wave.archive_reports`
- `wave.memory_candidates`
- `code.symbols`
- `code.references`
- `code.semantic_search`

Lifecycle mutation tools should be introduced only after validation and audit tools are trustworthy.

## Configuration Sketch

Target repositories should be configured explicitly.

```json
{
  "allowed_roots": [
    "/path/to/target-repository"
  ],
  "default_root": "/path/to/target-repository",
  "index": {
    "enabled": true,
    "path": ".wavefoundry/index.sqlite",
    "ignore": [".git", ".build", "DerivedData", "node_modules", "__pycache__"]
  },
  "framework": {
    "canonical_revision": "local-dev",
    "render_project_surfaces": true
  }
}
```

Use real target paths only in local configuration, fixtures, or operator-provided examples. Do not hardcode any one product repository as the only supported target.

## Safety Rules

- Never operate outside configured allowed roots.
- Never run destructive operations by default.
- Never overwrite project-local customizations without showing a diff or conflict report.
- Never require a network call for install, upgrade, validation, indexing, or packaging.
- Keep generated project-local surfaces readable and reviewable.
- Treat target repository docs as source of truth for project-specific facts.
- Treat canonical framework seeds as source of truth for framework behavior.

## Cleanup and Destructive Operations

**Historical reference preservation:** During legacy cleanup, only remove live working docs and deprecated prompt/wrapper files that have valid replacements. Do not delete mentions of removed artifacts from wave records, closed-wave archives, or historical documentation.

**Framework distribution zip archives:** Zip files at the repository root (`wavefoundry-*.zip`) are transport artifacts only. Never commit them. If a zip was accidentally committed, remove it with `git rm --cached <file>.zip`.

**Seed prompts:** Never delete or overwrite seed prompts under `.wavefoundry/framework/seeds/` without an explicit wave and `seed_edit_allowed` guard approval. Seed edits affect all target repositories.

## Initial Milestones

1. Inventory `.wavefoundry/framework/seeds/` and `.wavefoundry/framework/scripts/`.
2. Implement `wave.current`, `code.search`, and `code.read`.
3. Port lifecycle ID generation into Wavefoundry.
4. Port or wrap validation logic for `wave.validate`.
5. Add `wave.resolve_seed` for canonical seed lookup.
6. Add `wave.prompt_surface_audit` for shortcut/index/manifest/seed drift.
7. Add install/upgrade rendering for project-local surfaces.
8. Add package/export support.
9. Add local code index only after exact search and wave tools are stable.

## Definition Of Done For MVP

- Runs as a local MCP stdio server.
- Can inspect a configured target repository without modifying it.
- Can report active wave state and validation failures as structured JSON.
- Can search and read target repository files.
- Can resolve canonical seed references.
- Can audit prompt surface drift.
- Has tests for target-root safety, seed resolution, exact search, and prompt-surface audit behavior.
- Uses `Wavefoundry` consistently for the project identity.
