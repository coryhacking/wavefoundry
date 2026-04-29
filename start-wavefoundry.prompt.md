# Start Wavefoundry

You are working in the `wavefoundry` repository. This is the canonical repository for the Wave Framework and the future local MCP implementation.

Wavefoundry is a local-first project that combines:

- The canonical Wave Framework seed prompts and reference material.
- A local MCP server for framework-aware project inspection, validation, installation, upgrade, packaging, and code search.
- Tooling that renders explicit project-local instructions into target repositories so agents can operate from readable local context.

Wavefoundry is a framework and tooling repository, not a target product repository.

## First Principles

- Keep the canonical framework source in this repository.
- Keep generated target-repository surfaces readable and reviewable.
- Do not hide required operating context exclusively inside MCP tools.
- Start with read-only MCP tools before mutation tools.
- Prefer structured tools over arbitrary shell execution.
- Treat target repository roots as explicit allowed roots.
- Never overwrite target repository customizations without reporting a diff or conflict.
- Keep everything local by default; no hosted service or network dependency is required for the MVP.

## Current Repository Layout

```text
wavefoundry/
  AGENTS.md
  README.md
  docs/
    README.md
  start-wavefoundry.prompt.md
  framework/
    README.md
    VERSION
    seeds/
    scripts/
```

The root `README.md` explains Wavefoundry as the product. `docs/README.md` is the project-docs entry point. `framework/README.md` explains the canonical Wave Framework seed set.

## Initial Work

1. Read `AGENTS.md`, `README.md`, `docs/README.md`, `framework/README.md`, and `framework/VERSION`.
2. Inventory `framework/seeds/` and `framework/scripts/`.
3. Create a minimal Python project skeleton:

```text
pyproject.toml
src/wavefoundry/
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

4. Implement only the first read-only tool contracts:
   - `wave.current`
   - `wave.resolve_seed`
   - `wave.validate`
   - `wave.prompt_surface_audit`
   - `code.search`
   - `code.read`
5. Add tests for target-root safety, seed resolution, and basic exact search.
6. Defer mutation tools such as install, upgrade, create, prepare, review, and close until the read-only surface is reliable.

## Definition Of Done For This Kickoff

- The project can run tests locally.
- The MCP server has a minimal stdio entrypoint or clearly documented placeholder.
- Framework seed files remain under `framework/seeds/`.
- Framework scripts remain under `framework/scripts/`.
- No target-repository-specific assumptions are hardcoded except in explicit fixtures or operator-provided examples.
- README and AGENTS terminology consistently uses `Wavefoundry`.
