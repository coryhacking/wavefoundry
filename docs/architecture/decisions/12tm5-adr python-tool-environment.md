# 12tm5-adr — Python Tool Environment

Owner: Engineering
Status: accepted
Last verified: 2026-05-22

## Context

Wavefoundry's `setup_index.py` installs framework dependencies (`fastembed`, `lancedb`, `tree-sitter`, `mcp[cli]`, etc.) directly into whatever Python interpreter is active at runtime (`sys.executable`). When the active interpreter is managed by Homebrew or another PEP 668-compliant tool, `pip install` fails; the code works around this with a `--break-system-packages` retry. Consequences:

1. **Interpreter mutation.** Installing into arbitrary interpreters creates environment ambiguity across repos and is not an acceptable operator contract for broader rollout.
2. **Support burden.** `--break-system-packages` is a policy violation on managed interpreters and breaks Homebrew-managed Python installs in ways that are hard to debug.
3. **Dead-code venv concept.** `setup_index.py` already contains a `WAVEFOUNDRY_TOOL_VENV` / `_tool_venv_python()` function and an env var override, but `_install_deps()` ignores both — the venv path is never used.
4. **No declared dependency manifest.** There is no `pyproject.toml`; the authoritative dependency list exists only as inline `pip install` arguments inside `_install_deps()`.

These issues were identified during public rollout planning in wave `12t9b`. The implementation is tracked in `12tm5-enh python-tool-venv-bootstrap`.

## Decision

Wavefoundry adopts a shared user-level tool venv at `~/.wavefoundry/venv` as the standard Python environment for all framework tooling.

**Bootstrap:** `setup_index.py` creates `~/.wavefoundry/venv` via `python3 -m venv` on first run if it does not exist. Subsequent runs skip creation and install only missing packages.

**Install target:** All framework dependencies are installed into the venv Python, never into `sys.executable`. The `--break-system-packages` retry path is removed entirely.

**Override:** The `WAVEFOUNDRY_TOOL_VENV` environment variable overrides the venv path. The default is `~/.wavefoundry/venv` (updated from the previous dead-code default of `~/.cache/wavefoundry/indexer-venv`).

**Index build invocation:** The index builder (`indexer.py`) runs under the venv Python so all indexed imports resolve correctly.

**Dependency manifest:** A `pyproject.toml` at the repo root declares all framework runtime dependencies and the Python ≥ 3.11 minimum. This is the authoritative dependency list; `_install_deps()` and `pyproject.toml` must stay in sync.

**Python minimum:** Python ≥ 3.11. Required by `tomllib` (stdlib in 3.11) and tree-sitter grammar packages.

## Consequences

**Positive:**
- Framework deps are isolated from the operator's system or project interpreter; no interpreter mutation.
- `--break-system-packages` is gone; Homebrew-managed Python installs are no longer at risk.
- Single shared venv means operators install dependencies once and all local Wavefoundry repos share the environment.
- `pyproject.toml` is the declared dependency manifest, enabling standard tooling (`pip install -e .`, dependency audits).
- `WAVEFOUNDRY_TOOL_VENV` override supports non-standard setups (e.g., WSL2 path translation issues).

**Negative / tradeoffs:**
- Operators who have existing deps in a system or project interpreter must re-install into `~/.wavefoundry/venv`. The migration is automatic on first `setup_index.py` run, but prior installs are not cleaned up.
- WSL2 path translation can affect `~/.wavefoundry/venv` resolution on Windows. `WAVEFOUNDRY_TOOL_VENV` mitigates this, but operators must set it manually.
- A shared venv means a dependency version conflict in one tool affects all repos using the same venv. Per-repo venv isolation would fix this but adds setup friction.

**Constraints imposed:**
- `setup_index.py` must never call `pip install --break-system-packages` or install into `sys.executable`.
- The venv default path is `~/.wavefoundry/venv`; do not revert to `~/.cache/wavefoundry/indexer-venv` or any other path without updating this ADR.
- `pyproject.toml` and `_install_deps()` must declare the same dependency set. Update both in the same pass when adding or removing a dependency.
- Python ≥ 3.11 is the minimum supported version. Code must not use `tomllib` import fallbacks or conditionals for earlier Python versions.
- `packaging` library must be listed in `pyproject.toml` (required by the semver versioning contract; see `12tm5-adr semver-versioning-contract`).

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| Continue installing into `sys.executable` with `--break-system-packages` | Policy violation on managed interpreters; creates environment ambiguity; not an acceptable operator contract |
| Per-repo virtual environments | Adds setup friction per repo; operators with many repos pay repeated install time; shared user venv is the standard path |
| `pipx` for tool isolation | Designed for CLI tools, not library imports needed by the MCP server and indexer at runtime |
| `uv`-based venv management | Would replace the existing `WAVEFOUNDRY_TOOL_VENV` / `_tool_venv_python()` concept entirely; higher blast radius than wiring up dead code that is already correct |
| `~/.cache/wavefoundry/indexer-venv` (existing dead-code default) | Buried in a cache path; `~/.wavefoundry/venv` is shorter, obvious, and co-located with the Wavefoundry user directory |
| Python ≥ 3.10 minimum | `tomllib` is stdlib only from 3.11; tree-sitter grammar packages target 3.11+; 3.10 would require a `tomllib` shim dependency |

## References

- `docs/plans/12tm5-enh python-tool-venv-bootstrap.md` — implementation change doc with full task list and ACs
- `docs/architecture/current-state.md` — "Python environment contract" section
- Wave `12t9b public-rollout-readiness-decisions` — decision log for the Python environment strategy
- `.wavefoundry/framework/scripts/setup_index.py` — `_tool_venv_python()`, `_install_deps()`, `ensure_deps()`
- `12tm5-adr semver-versioning-contract` — requires `packaging` in `pyproject.toml`
