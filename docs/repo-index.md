# Repo Index — Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-06-28

## Repository Summary

Wavefoundry is the canonical home for the Wave Framework and its future local MCP server. It owns the seed prompts, framework scripts, packaging logic, migration helpers, and planned tool surface for framework-aware work across target repositories.

**Self-hosting note:** Wavefoundry uses the Wave Framework to develop itself. `.wavefoundry/framework/` is the canonical framework directory; `docs/` is Wavefoundry's self-hosted project operating surface.

## Top-Level Modules and Roots


| Path                               | Role                                                                                         | Notes                      |
| ---------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------- |
| `.wavefoundry/framework/seeds/`    | Canonical Wave Framework seed prompts and overview docs                                      | 37 files, numbered 001–250 |
| `.wavefoundry/framework/scripts/`  | Framework tooling: lint, gardener, lifecycle ID, packaging, rendering, tests                 | Python 3.13                |
| `.wavefoundry/framework/README.md` | Canonical framework map: prompt numbering, public commands, factor model, seeding overview   |                            |
| `.wavefoundry/framework/VERSION`   | Current framework version (`2026-04-28a`)                                                    | Updated by `build_pack.py` |
| `docs/`                            | Wavefoundry self-hosted project operating surface (this tree, seeded by Wave Framework init) |                            |
| `docs/design-system/`                     | Design-system extraction contract hub (seeded by wave `12as1`; machine-readable token/spec tree + operator-owned `design-language.md`) | Seeded; not yet populated |
| `docs/architecture/design-system.md` | Design-system architecture hub: extraction philosophy, regeneration semantics, semantic index relationship | Seeded by wave `12as1` |


The table above is human/agent-authored. The structural module list below is
generated from the codebase map (Option A, wave `1p5x8`) — only the content
between the markers is machine-maintained; the surrounding narrative is not.

### Generated structural areas (from the codebase map)

<!-- waveframework:repo-index-modules begin -->
<!-- Generated from the codebase map (.wavefoundry/framework/scripts/gen_codebase_map.py). The narrative outside these markers is human/agent-authored and never touched. -->

| Area | Path | Kind | Size (nodes) |
| ---- | ---- | ---- | ------------ |
| tests | `.wavefoundry/framework/scripts/tests` | code | 5942 |
| server_impl | `.wavefoundry/framework/scripts` | code | 586 |
| graph | `.wavefoundry/framework/scripts` | code | 224 |
| dashboard | `.wavefoundry/framework/dashboard` | code | 213 |
| wave_lint_lib | `.wavefoundry/framework/scripts/wave_lint_lib` | code | 172 |
| chunker | `.wavefoundry/framework/scripts` | code | 161 |
| subprocess_util | `.wavefoundry/framework/scripts` | code | 145 |
| scripts/workflow-config | `.wavefoundry/framework/scripts` | code | 130 |
| indexer | `.wavefoundry/framework/scripts` | code | 102 |
| upgrade_wavefoundry | `.wavefoundry/framework/scripts` | code | 81 |
| render_platform_surfaces | `.wavefoundry/framework/scripts` | code | 61 |
| gen_codebase_map | `.wavefoundry/framework/scripts` | code | 56 |
| render_agent_surfaces | `.wavefoundry/framework/scripts` | code | 48 |
| graph_cluster | `.wavefoundry/framework/scripts` | code | 38 |
| server | `.wavefoundry/framework/scripts` | code | 36 |
| graph_query | `.wavefoundry/framework/scripts` | code | 27 |
| accel_embedder | `.wavefoundry/framework/scripts` | code | 25 |
| design_token_build | `.wavefoundry/framework/scripts` | code | 25 |
| upgrade_extensions | `.wavefoundry/framework/scripts` | code | 21 |
| docs_gardener | `.wavefoundry/framework/scripts` | code | 17 |
| tokens | `docs/design-system/tokens` | config | 320 |
| docs | `docs` | config | 187 |
| modes | `docs/design-system/tokens/modes` | config | 150 |
| json | `docs/design-system/exports/json` | config | 86 |
<!-- waveframework:repo-index-modules end -->

No shipped product implementation sources exist yet. The MCP Python package (`src/wavefoundry/`) is planned but not scaffolded.

## Primary Technologies and Runtime Model

- **Language:** Python 3.13 (framework scripts, future MCP server)
- **Runtime model:** local-only; no network dependency for core tooling; future MCP server runs as a local stdio or socket daemon
- **Package manager:** none yet (pyproject.toml planned for MCP package)
- **Test runner:** `run_tests.py` (custom wrapper using `python3 -B -m unittest`)
- **Build tool:** `build_pack.py` (custom script producing dated `.zip` distribution)

## IDE and Toolchain Signals


| Category              | Signal                   | Source             |
| --------------------- | ------------------------ | ------------------ |
| Python version        | 3.13                     | `.venv/pyvenv.cfg` |
| Virtual environment   | `.venv/` at repo root    | `.venv/pyvenv.cfg` |
| No CI/CD pipeline     | No `.github/workflows/`  | None detected      |
| No build manifest yet | `pyproject.toml` planned | Not present        |


## Framework Script Inventory


| Script                                                       | Purpose                                                                   |
| ------------------------------------------------------------ | ------------------------------------------------------------------------- |
| `.wavefoundry/framework/scripts/lifecycle_id.py`             | Generate wave and change IDs using configured epoch                       |
| `.wavefoundry/framework/scripts/docs_lint.py`                | Validate Wave Framework docs gate (metadata, manifest, prompt surface)    |
| `.wavefoundry/framework/scripts/docs_gardener.py`            | Refresh metadata timestamps and surface drift candidates                  |
| `.wavefoundry/framework/scripts/build_pack.py`               | Package framework into dated `.zip` distribution                          |
| `.wavefoundry/framework/scripts/render_platform_surfaces.py` | Render platform hook/config surfaces (.claude/, .cursor/, .github/hooks/); calls `render_agent_surfaces.py` |
| `.wavefoundry/framework/scripts/render_agent_surfaces.py` | Render auto-Guru tier 2–3 agent routing (thin-pointer markers, Cursor rule, Claude subagent, Codex skill) |
| `.wavefoundry/framework/scripts/run_tests.py`                | Run framework script tests without bytecode                               |
| `.wavefoundry/framework/scripts/tests/`                      | Unit and fixture tests for docs_lint and build_pack                       |
| `.wavefoundry/framework/scripts/wave_lint_lib/`              | Library modules for docs_lint: validators, context, helpers               |


## Architecture Handoff for seed-060

### Deployable Units


| Unit               | Kind                 | Build/Run Entrypoint                                   | Notes                                     |
| ------------------ | -------------------- | ------------------------------------------------------ | ----------------------------------------- |
| Framework scripts  | CLI tools            | `python3 .wavefoundry/framework/scripts/<script>.py`   | Run directly from repo root               |
| Wave Framework zip | Distribution archive | `python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH` | Produces `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip`; packaging is blocked below `1.0.0` |
| Future MCP server  | stdio daemon         | `src/wavefoundry/server.py` (planned)                  | Not yet scaffolded                        |


### Inter-Unit Edges


| Edge                                                                     | Kind       | Parties                 | Notes                                                                 |
| ------------------------------------------------------------------------ | ---------- | ----------------------- | --------------------------------------------------------------------- |
| `build_pack.py` → `.wavefoundry/framework/VERSION`                       | file write | packager → VERSION file | Stamps VERSION on each build                                          |
| `lifecycle_id.py` → `docs/workflow-config.json`                          | file read  | script → config         | Reads `lifecycle_id_policy` for epoch                                 |
| `docs_lint.py` → `docs/` tree                                            | file read  | linter → docs           | Validates prompt surface and manifest                                 |
| `render_platform_surfaces.py` → `.claude/`, `.cursor/`, `.github/hooks/` | file write | renderer → hook dirs    | Materializes hook entrypoints                                         |
| Future MCP server → target repository                                    | file read  | tool → configured root  | Reads target repo docs/code; no writes without explicit mutation tool |


### Ownership of Shared State


| State                   | Owner                | Path                                        | Notes                          |
| ----------------------- | -------------------- | ------------------------------------------- | ------------------------------ |
| Framework VERSION       | build_pack.py        | `.wavefoundry/framework/VERSION`            | Updated at each packaging run  |
| Workflow config         | project docs         | `docs/workflow-config.json`                 | Lifecycle epoch, wave settings |
| Prompt surface manifest | docs_lint / seed-100 | `docs/prompts/prompt-surface-manifest.json` | Refreshable                    |


### Sensitivity

- No network exposure in current scripts (all local file operations)
- No secrets, credentials, or PII in framework scripts or seed prompts
- Future MCP server: explicit allowed-roots configuration; no mutation without operator confirmation

### Concurrency / Single-Lane Hints


| Area                              | Concurrency Safety                                                                         |
| --------------------------------- | ------------------------------------------------------------------------------------------ |
| `.wavefoundry/framework/seeds/`   | Safe for parallel read; single-lane for framework seed edits (protected surface)           |
| `docs/`                           | Single-lane for broad framework-maintenance edits per framework plan gate                  |
| `.wavefoundry/framework/scripts/` | Generally safe for parallel; `build_pack.py` writes VERSION (single-lane during packaging) |
| Future MCP tools                  | Read-only tools: safe for concurrency; mutation tools: serialize per target root           |


## Open Questions / Weak Evidence

- MCP server transport (stdio vs socket): TBD until server scaffolded
- Config file format for target repository allowed-roots: draft in AGENTS.md; not yet implemented
- Factor 07 (port binding): partial — future MCP server may bind a port or use stdio only
- Factor 09 (disposability): partial — depends on server architecture decision

## Persona Candidate Evidence


| Candidate            | Evidence                                                                                                                                  | Related Factors |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| `wave-coordinator`   | Framework is used by developers running waves; wave coordinator is a distinct operating mode described extensively in the framework seeds | —               |
| `framework-operator` | Users who install, upgrade, and operate the Wave Framework in their own repositories; documented in seed-010 operator summary             | —               |
