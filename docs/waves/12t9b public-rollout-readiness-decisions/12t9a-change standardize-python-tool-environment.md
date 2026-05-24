# Standardize Python Tool Environment

Change ID: `12t9a-change standardize-python-tool-environment`
Change Status: `implemented`
Owner: planner
Status: implemented
Last verified: 2026-05-22
Wave: `12t9b public-rollout-readiness-decisions`

## Rationale

Wavefoundry's Python runtime story is inconsistent. The repository appears to use a local `.venv` for development, but the framework currently has no committed dependency manifest and `setup_index.py` installs packages into the active interpreter at runtime, including a `--break-system-packages` retry path. That is not an acceptable operator contract for broader rollout. The project should define a shared Wavefoundry tool environment and a declared dependency model for both maintainers and downstream operators.

## Requirements

1. Define the official Python runtime and dependency-management model for Wavefoundry.
2. Create a declared dependency surface for framework scripts and the MCP server rather than relying on ad hoc runtime installs into whichever interpreter is active.
3. Decide how contributor-local development environments and shared operator tool environments relate to each other.
4. Remove or replace operator flows that mutate arbitrary system Python environments during normal setup.
5. Update docs and verification guidance to reflect the chosen Python environment strategy.

## Scope

**Problem statement:** The framework's Python tooling works today, but its environment and dependency model is not disciplined enough for a larger external audience.

**In scope:**

- Define the supported Python environment strategy for maintainers and operators.
- Identify the required dependency manifest and bootstrap surfaces.
- Decide whether a shared user-level Wavefoundry tool environment is the standard install path.
- Audit current scripts and docs for implicit active-interpreter assumptions.
- Capture implementation follow-ups needed to enforce the chosen environment model.

**Out of scope:**

- Packaging Wavefoundry as a hosted service.
- Solving non-Python dependency distribution such as Node/browser tooling beyond documenting current expectations.
- Rewriting unrelated framework scripts that are unaffected by the Python environment contract.

## Acceptance Criteria

- [x] AC-1: The change doc defines the target Python environment model, including whether Wavefoundry uses a shared tool environment across repos.
- [x] AC-2: The plan identifies the current gaps between repository practice and the intended operator contract, including undeclared dependencies and runtime `pip install` behavior.
- [x] AC-3: The plan names the implementation surfaces needed for dependency declaration, bootstrap, and script/runtime alignment.
- [x] AC-4: The plan distinguishes contributor development setup from downstream operator/runtime setup.

## Tasks

- [x] Review current Python dependency assumptions in framework scripts, docs, and local repo metadata.
- [x] Define the recommended shared tool-environment model and its boundary relative to per-repo dev envs.
- [x] Identify the dependency manifest and bootstrap changes needed to stop mutating arbitrary active interpreters.
- [x] Record required docs, test, and upgrade-surface updates for the later implementation wave.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| environment-audit | planner | — | Enumerate current Python runtime and dependency assumptions |
| contract-definition | planner | environment-audit | Define official tool env and dependency model |
| implementation-scope | planner | contract-definition | Name required bootstrap, manifest, and docs changes |

## Serialization Points

- Bootstrap scripts and docs should not be updated piecemeal; dependency declaration and environment guidance need one consistent contract.
- Any change to runtime dependency installation should align with upgrade and index-setup flows before rollout.

## Affected Architecture Docs

`docs/architecture/current-state.md`, `docs/architecture/cross-cutting-concerns.md`, `docs/architecture/data-and-control-flow.md`, `docs/architecture/testing-architecture.md`, and likely `docs/architecture/decisions/` for the Python environment contract.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Rollout needs a stable operator runtime contract before wider adoption |
| AC-2 | required | The current gaps must be named before implementation starts so the fix is scoped correctly |
| AC-3 | required | Implementation scope spans manifests, bootstrap, and docs and must be explicit |
| AC-4 | important | Contributor and operator setups should be related but can follow the primary operator contract |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-22 | Change scaffolded from rollout-readiness evaluation. | Repository inspection of `.venv` signals, `setup_index.py`, architecture docs, and runtime guidance. |
| 2026-05-22 | Completed environment audit. Gaps found: no `pyproject.toml` or `requirements.txt`; `setup_index.py` installs into `sys.executable` at runtime with `--break-system-packages` fallback; `WAVEFOUNDRY_TOOL_VENV` env var and `_tool_venv_python()` exist in code but are dead — `_install_deps()` ignores the tool venv and installs into the active interpreter. Operator docs and README give no Python version requirement. Target model, implementation surfaces, and docs/test updates recorded. | `setup_index.py`, `README.md`, `docs/prompts/install-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-22 | Track Python environment strategy as a dedicated rollout change. | Dependency declaration and environment bootstrapping are now first-class adoption concerns. | Keep the current implicit active-interpreter model; defer dependency-manifest work. |
| 2026-05-22 | Adopt a **shared user-level tool environment** at `~/.cache/wavefoundry/tool-venv` (overridable via `WAVEFOUNDRY_TOOL_VENV`) as the standard operator install path for the MCP server and index tooling. | Installs into the active interpreter are error-prone (wrong env, `--break-system-packages` PEP 668 hacks, support burden). A shared venv at a stable path removes environment ambiguity for operators across repos. | Per-repo venv inside each project; pipx-managed install; require operators to pre-install deps manually. |
| 2026-05-22 | Complete the dead `WAVEFOUNDRY_TOOL_VENV` / `_tool_venv_python()` code path in `setup_index.py`: bootstrap the venv if absent, install into it, and run the index builder under the venv Python. Remove `--break-system-packages` once the venv path is active. | The concept is already there but was never wired up. Activating it removes the `--break-system-packages` hack without a large rewrite. | Replace `setup_index.py` bootstrapping entirely with `uv` or `pipx`. |
| 2026-05-22 | Add `pyproject.toml` declaring the framework's Python dependencies (fastembed, lancedb, tree-sitter family, mcp[cli]) as the authoritative dependency manifest. | No current manifest means operators cannot inspect or pin deps without reading the source. | Use `requirements.txt`; continue with in-code `REQUIRED_IMPORTS` as the only dependency surface. |
| 2026-05-22 | Minimum Python version: **3.11**. Contributor dev setup and operator runtime setup share the same tool venv; contributors add no separate dev-only surface. | Python 3.11 provides `tomllib` and `ExceptionGroup` used in the tree-sitter family; the framework does not currently distinguish dev vs runtime deps. | Require 3.10; require 3.12; maintain separate dev requirements. |
| 2026-05-22 | Update `README.md`, `install-wavefoundry.prompt.md`, and `upgrade-wavefoundry.prompt.md` to state the Python ≥ 3.11 requirement and the shared tool-venv install model. | Operators have no stated Python requirement today. | Leave docs as-is until the implementation wave updates them. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The repository's current docs and metadata disagree about Python dependencies and environment strategy. | Use the planning change to reconcile the target contract before implementation edits begin. |
| Ad hoc installs into the active interpreter create operator friction and support burden. | Standardize on a declared dependency surface and shared tool-environment bootstrap path. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
