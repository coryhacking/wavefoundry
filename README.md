# Wavefoundry

Wavefoundry is the repository for the Wave Framework and its future local MCP implementation.

It owns the canonical Wave Framework seed prompts, framework scripts, packaging logic, migration rules, and the planned local MCP server that will make framework-aware work searchable, auditable, and operable across target repositories.

## Product Boundary

Wavefoundry is a framework and tooling repository, not a target product repository.

It should work against any explicitly configured target repository with Wave Framework state. Target examples in docs and tests must stay generic unless a fixture intentionally names a sample repository.

## What This Repository Owns

- Canonical Wave Framework seed prompts and reference material under `.wavefoundry/framework/seeds/`.
- Framework scripts under `.wavefoundry/framework/scripts/` for validation, rendering, packaging, migration, lifecycle IDs, and maintenance.
- Distribution packaging for the canonical framework source.
- Migration guidance for projects moving from the old `agent-workflows/wave-context-framework/` layout to the Wavefoundry layout.
- The future local MCP server and code index.
- Project docs for Wavefoundry itself under `docs/`.

## What Target Repositories Own

Target repositories keep their own local operating surface:

- `AGENTS.md`
- `docs/prompts/`
- `docs/agents/`
- `docs/waves/`
- `docs/plans/`
- `docs/workflow-config.json`
- project-specific specs, architecture docs, and workflow policy

Wavefoundry can install, upgrade, audit, and validate those surfaces, but target repositories remain the authority for project-specific facts and customizations.

## Repository Layout

```text
wavefoundry/
  AGENTS.md
  README.md
  start-wavefoundry.prompt.md
  docs/
    README.md
  framework/
    README.md
    VERSION
    seeds/
    scripts/
```

Planned MCP implementation layout:

```text
wavefoundry/
  pyproject.toml
  src/
    wavefoundry/
      __init__.py
      server.py
      config.py
      tools/
        __init__.py
        code.py
        framework.py
        wave.py
      index/
        __init__.py
  tests/
  examples/
```

## Framework Source

`.wavefoundry/framework/` is the canonical Wave Framework source tree in this self-hosted repository.

`.wavefoundry/framework/seeds/` contains the seed prompts and framework reference material. `.wavefoundry/framework/scripts/` contains the executable framework tooling. `.wavefoundry/framework/README.md` is the canonical map of the seed pack, prompt numbering, public command surface, and package behavior.

Package Wavefoundry from this repository with:

```bash
python3 .wavefoundry/framework/scripts/build_pack.py
```

The package is a dated `wavefoundry-framework-YYYY-MM-DDx.zip` archive. Packaging is a maintainer action; target-repository install and upgrade behavior is a separate concern.

## MCP Direction

The MCP server is a capability inside Wavefoundry, not the whole product.

The first MCP surface should be local, read-only, and reliable:

- `wave.current`
- `wave.validate`
- `wave.prompt_surface_audit`
- `wave.resolve_seed`
- `code.search`
- `code.read`

Mutation tools come later, after validation and audit are trustworthy:

- `wave.install`
- `wave.upgrade`
- `wave.package`
- `wave.create`
- `wave.prepare`
- `wave.review`
- `wave.close`

The server should use explicit allowed target roots, avoid network dependencies for the MVP, and expose structured operations rather than arbitrary shell execution.

## Self-Hosting

Wavefoundry should use the Wave Framework to develop the Wave Framework.

That self-hosting boundary is:

- `.wavefoundry/framework/` is canonical framework product source.
- `docs/` is Wavefoundry's project operating surface.
- Framework behavior changes should be planned, reviewed, and closed through Wavefoundry's local wave process once the local docs surface is installed.
- If rendered local docs conflict with `.wavefoundry/framework/seeds/`, the seed source wins for generic framework behavior.
- If Wavefoundry-specific policy under `docs/` conflicts with generic defaults, the local project policy governs this repository until a wave changes the framework default.

## Existing Project Migration

Existing projects that already vendor the old framework under `agent-workflows/wave-context-framework/` should use the explicit migration flow:

```text
Migrate to Wavefoundry
Upgrade to Wavefoundry
```

The migration prompt is `.wavefoundry/framework/seeds/250-migrate-existing-wave-project.prompt.md`. It preserves target-local docs and customizations, stages the canonical framework under `.wavefoundry/framework/`, validates compatibility, and leaves the old tree in place until validation passes and the operator has reviewed the migration result.

## Non-Goals

- Do not make Wavefoundry specific to any one target repository.
- Do not hide all framework behavior inside MCP.
- Do not require hosted services for install, upgrade, validation, indexing, or packaging.
- Do not start with semantic/vector search before exact search and wave validation are stable.
- Do not let tools overwrite target-local docs without diff or conflict reporting.
- Do not implement lifecycle mutation tools before read-only validation and audit tools are trustworthy.

## Current Status

This repository currently contains the canonical framework source and kickoff documentation. The MCP implementation has not been scaffolded yet.
