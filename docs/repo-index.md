# Repo Index — Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Repository Summary

Wavefoundry is the canonical home for the Wave Framework and its future local MCP server. It owns the seed prompts, framework scripts, packaging logic, migration helpers, and planned tool surface for framework-aware work across target repositories.

**Self-hosting note:** Wavefoundry uses the Wave Framework to develop itself. `framework/` is canonical framework product source; `docs/` is Wavefoundry's self-hosted project operating surface.

## Top-Level Modules and Roots

| Path | Role | Notes |
|------|------|-------|
| `framework/seeds/` | Canonical Wave Framework seed prompts and overview docs | 37 files, numbered 001–250 |
| `framework/scripts/` | Framework tooling: lint, gardener, lifecycle ID, packaging, rendering, tests | Python 3.13 |
| `framework/README.md` | Canonical framework map: prompt numbering, public commands, factor model, seeding overview | |
| `framework/VERSION` | Current framework version (`2026-04-28a`) | Updated by `build_pack.py` |
| `docs/` | Wavefoundry self-hosted project operating surface (this tree, seeded by Wave Framework init) | |
| `.wavefoundry/framework` | Symlink → `../framework` (self-hosting mode; same tree as `framework/`) | Not a separate copy |

No shipped product implementation sources exist yet. The MCP Python package (`src/wavefoundry/`) is planned but not scaffolded.

## Primary Technologies and Runtime Model

- **Language:** Python 3.13 (framework scripts, future MCP server)
- **Runtime model:** local-only; no network dependency for core tooling; future MCP server runs as a local stdio or socket daemon
- **Package manager:** none yet (pyproject.toml planned for MCP package)
- **Test runner:** `run_tests.py` (custom wrapper using `python3 -B -m unittest`)
- **Build tool:** `build_pack.py` (custom script producing dated `.zip` distribution)

## IDE and Toolchain Signals

| Category | Signal | Source |
|----------|--------|--------|
| Python version | 3.13 | `.venv/pyvenv.cfg` |
| Virtual environment | `.venv/` at repo root | `.venv/pyvenv.cfg` |
| No CI/CD pipeline | No `.github/workflows/` | None detected |
| No build manifest yet | `pyproject.toml` planned | Not present |

## Framework Script Inventory

| Script | Purpose |
|--------|---------|
| `framework/scripts/lifecycle_id.py` | Generate wave and change IDs using configured epoch |
| `framework/scripts/docs_lint.py` | Validate Wave Framework docs gate (metadata, manifest, prompt surface) |
| `framework/scripts/docs_gardener.py` | Refresh metadata timestamps and surface drift candidates |
| `framework/scripts/build_pack.py` | Package framework into dated `.zip` distribution |
| `framework/scripts/render_platform_surfaces.py` | Render platform hook/config surfaces (.claude/, .cursor/, .github/hooks/) |
| `framework/scripts/run_tests.py` | Run framework script tests without bytecode |
| `framework/scripts/tests/` | Unit and fixture tests for docs_lint and build_pack |
| `framework/scripts/wave_lint_lib/` | Library modules for docs_lint: validators, context, helpers |

## Architecture Handoff for seed-060

### Deployable Units

| Unit | Kind | Build/Run Entrypoint | Notes |
|------|------|----------------------|-------|
| Framework scripts | CLI tools | `python3 framework/scripts/<script>.py` | Run directly from repo root |
| Wave Framework zip | Distribution archive | `python3 framework/scripts/build_pack.py` | Produces `wavefoundry-framework-<date><letter>.zip` |
| Future MCP server | stdio daemon | `src/wavefoundry/server.py` (planned) | Not yet scaffolded |

### Inter-Unit Edges

| Edge | Kind | Parties | Notes |
|------|------|---------|-------|
| `build_pack.py` → `framework/VERSION` | file write | packager → VERSION file | Stamps VERSION on each build |
| `lifecycle_id.py` → `docs/workflow-config.json` | file read | script → config | Reads `lifecycle_id_policy` for epoch |
| `docs_lint.py` → `docs/` tree | file read | linter → docs | Validates prompt surface and manifest |
| `render_platform_surfaces.py` → `.claude/`, `.cursor/`, `.github/hooks/` | file write | renderer → hook dirs | Materializes hook entrypoints |
| Future MCP server → target repository | file read | tool → configured root | Reads target repo docs/code; no writes without explicit mutation tool |

### Ownership of Shared State

| State | Owner | Path | Notes |
|-------|-------|------|-------|
| Framework VERSION | build_pack.py | `framework/VERSION` | Updated at each packaging run |
| Workflow config | project docs | `docs/workflow-config.json` | Lifecycle epoch, wave settings |
| Prompt surface manifest | docs_lint / seed-100 | `docs/prompts/prompt-surface-manifest.json` | Refreshable |

### Sensitivity

- No network exposure in current scripts (all local file operations)
- No secrets, credentials, or PII in framework scripts or seed prompts
- Future MCP server: explicit allowed-roots configuration; no mutation without operator confirmation

### Concurrency / Single-Lane Hints

| Area | Concurrency Safety |
|------|-------------------|
| `framework/seeds/` | Safe for parallel read; single-lane for framework seed edits (protected surface) |
| `docs/` | Single-lane for broad framework-maintenance edits per framework plan gate |
| `framework/scripts/` | Generally safe for parallel; `build_pack.py` writes VERSION (single-lane during packaging) |
| Future MCP tools | Read-only tools: safe for concurrency; mutation tools: serialize per target root |

## Open Questions / Weak Evidence

- MCP server transport (stdio vs socket): TBD until server scaffolded
- Config file format for target repository allowed-roots: draft in AGENTS.md; not yet implemented
- Factor 07 (port binding): partial — future MCP server may bind a port or use stdio only
- Factor 09 (disposability): partial — depends on server architecture decision

## Persona Candidate Evidence

| Candidate | Evidence | Related Factors |
|-----------|---------|-----------------|
| `wave-coordinator` | Framework is used by developers running waves; wave coordinator is a distinct operating mode described extensively in the framework seeds | — |
| `framework-operator` | Users who install, upgrade, and operate the Wave Framework in their own repositories; documented in seed-010 operator summary | — |
