# Python Tool Venv Bootstrap

Change ID: `12tm5-enh python-tool-venv-bootstrap`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-05-22
Wave: TBD

## Rationale

Wavefoundry's `setup_index.py` currently installs framework dependencies (`fastembed`, `lancedb`, `tree-sitter`, `mcp[cli]`, etc.) into whatever Python interpreter is active at runtime, with a `--break-system-packages` fallback for Homebrew/PEP 668 environments. This is not an acceptable operator contract for broader rollout: it mutates arbitrary interpreters, creates environment ambiguity across repos, and produces support burden. The code already has a `WAVEFOUNDRY_TOOL_VENV` / `_tool_venv_python()` concept but it is dead — `_install_deps()` ignores it. This change wires up that concept, adopts `~/.wavefoundry/venv` as the standard shared tool environment, and removes the `--break-system-packages` hack.

## Requirements

1. Create and bootstrap `~/.wavefoundry/venv` (or `$WAVEFOUNDRY_TOOL_VENV` override) if it does not exist, using `python3 -m venv`.
2. Install all framework dependencies into the venv, not into `sys.executable`.
3. Run the index builder under the venv Python so all indexed imports resolve correctly.
4. Remove the `--break-system-packages` retry path from `_install_deps()`.
5. Update the `WAVEFOUNDRY_TOOL_VENV` default in `_tool_venv_python()` from `~/.cache/wavefoundry/indexer-venv` to `~/.wavefoundry/venv`.
6. Add `pyproject.toml` at the repo root declaring the Python ≥ 3.11 requirement and all framework dependencies as the authoritative manifest.
7. Update `README.md`, `install-wavefoundry.prompt.md`, and `upgrade-wavefoundry.prompt.md` to state the Python ≥ 3.11 requirement and the `~/.wavefoundry/venv` shared tool environment.

## Scope

**Problem statement:** `setup_index.py` installs deps at runtime into the active interpreter with a `--break-system-packages` fallback. The `WAVEFOUNDRY_TOOL_VENV` venv concept exists in the code but is not wired up. No declared dependency manifest exists.

**In scope:**

- Bootstrap `~/.wavefoundry/venv` (create + install deps) in `setup_index.py`
- Wire `_tool_venv_python()` into `_install_deps()` and the index build invocation
- Remove `--break-system-packages` retry path
- Add `pyproject.toml` with declared dependencies and Python ≥ 3.11 minimum
- Update operator-facing docs (README, install prompt, upgrade prompt)
- Update `test_setup_index.py` to reflect the new venv-based install behavior

**Out of scope:**

- Packaging Wavefoundry as a PyPI or Homebrew package
- Per-repo virtual environments — the shared user-level venv is the standard path
- Changing the MCP server entry point or server bootstrapping beyond the Python interpreter used

## Acceptance Criteria

- [x] AC-1: Running `setup_index.py` on a machine with no existing `~/.wavefoundry/venv` creates the venv and installs all dependencies into it without touching `sys.executable`.
- [x] AC-2: Running `setup_index.py` on a machine with an existing `~/.wavefoundry/venv` skips venv creation and only installs missing packages.
- [x] AC-3: The `--break-system-packages` code path is removed; `setup_index.py` never calls `pip install --break-system-packages`.
- [x] AC-4: `WAVEFOUNDRY_TOOL_VENV` env var overrides the venv path; the default is `~/.wavefoundry/venv`.
- [x] AC-5: `pyproject.toml` exists at the repo root and declares all framework runtime dependencies and Python ≥ 3.11.
- [x] AC-6: `README.md`, `install-wavefoundry.prompt.md`, and `upgrade-wavefoundry.prompt.md` state the Python ≥ 3.11 requirement and describe the shared venv at `~/.wavefoundry/venv`.
- [x] AC-7: `test_setup_index.py` is updated to cover venv bootstrap and venv-based install; old `--break-system-packages` tests are removed.

## Tasks

- [x] Update `_tool_venv_python()` default path from `~/.cache/wavefoundry/indexer-venv` to `~/.wavefoundry/venv`
- [x] Add `_bootstrap_venv()` to `setup_index.py`: create venv if absent, return venv Python path
- [x] Rewrite `_install_deps()` to install into the venv Python, not `sys.executable`; remove `--break-system-packages` branch
- [x] Update the index build invocation in `setup_index.py` to use the venv Python
- [x] Add `pyproject.toml` declaring Python ≥ 3.11 and all runtime dependencies
- [x] Update `README.md`, `docs/prompts/install-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`
- [x] Update `test_setup_index.py`: add venv bootstrap tests, remove `--break-system-packages` tests

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| venv-bootstrap | implementer | — | `_bootstrap_venv()` + `_tool_venv_python()` update + `_install_deps()` rewrite |
| pyproject | implementer | — | Add `pyproject.toml`; can run in parallel |
| docs-update | implementer | venv-bootstrap | README, install prompt, upgrade prompt |
| tests | implementer | venv-bootstrap | Update `test_setup_index.py` |

## Serialization Points

- `_install_deps()` must use the venv Python before the index build invocation is updated — otherwise the build runs under the wrong interpreter.
- `pyproject.toml` and `_install_deps()` must agree on the dependency list; update both in the same pass.

## Affected Architecture Docs

`docs/architecture/current-state.md` — update the "Python environment contract" note from "decided, not yet implemented" to reflect the shipped implementation. `docs/architecture/cross-cutting-concerns.md` if it references Python environment setup.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Core behavior — venv must be created and used |
| AC-2 | required | Incremental install must not recreate the venv on every run |
| AC-3 | required | The `--break-system-packages` hack must be gone |
| AC-4 | required | Operator override path must work |
| AC-5 | required | Declared manifest is the deliverable |
| AC-6 | required | Operators need the Python version requirement stated |
| AC-7 | important | Test coverage for new bootstrap behavior |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-22 | Change created from planning decisions in wave `12t9b`. | `12t9a-change standardize-python-tool-environment.md` decision log. |
| 2026-05-22 | Implemented. `_bootstrap_venv()` + `_missing_in_venv()` added; `_install_deps()` rewritten to venv Python; `--break-system-packages` removed; `pyproject.toml` created; docs updated; `test_setup_index.py` rewritten. 1580 tests pass. | `setup_index.py`, `pyproject.toml`, `test_setup_index.py`, README.md, install/upgrade prompts |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-22 | Use `~/.wavefoundry/venv` as the default shared tool environment. | Short, obvious, and located in the Wavefoundry user directory rather than a generic cache path. Operator-confirmed. | `~/.cache/wavefoundry/indexer-venv` (existing dead code default); per-repo venv; pipx. |
| 2026-05-22 | Wire up the existing `WAVEFOUNDRY_TOOL_VENV` / `_tool_venv_python()` dead code rather than replacing it. | The concept is already correct — only the wiring is missing. Minimal blast radius. | Replace with `uv`-based venv management. |
| 2026-05-22 | Minimum Python version: 3.11. | `tomllib` (stdlib in 3.11) and tree-sitter grammar requirements. | 3.10; 3.12. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Operators who already have deps installed in a system or project interpreter must re-install into the venv. | Clearly document the migration in install/upgrade prompts; venv creation is automatic on first run. |
| WSL2 path translation could affect `~/.wavefoundry/venv` resolution on Windows. | `WAVEFOUNDRY_TOOL_VENV` override allows operators to specify an explicit path; flag as a known WSL2 consideration in docs. |
| Partial venv creation leaves a broken state. | If `_bootstrap_venv()` fails midway (disk full, permission error), `~/.wavefoundry/venv/` may exist but be incomplete. The next run sees the directory, skips creation, and fails on import. Mitigation: detect an incomplete venv by checking for the Python binary (`venv/bin/python` or `venv/Scripts/python.exe`); if absent, delete the partial directory and recreate. |
| `packaging` library used before venv is bootstrapped. | `upgrade_wavefoundry.py` imports `check_version`, which imports `packaging`. If run with system Python before `setup_index.py` bootstraps the venv, the import fails. Mitigation: use a lazy import in `check_version.py` with a clear `ModuleNotFoundError` message directing the operator to run `setup_index.py` first. Coordinate with `12tm5-enh migrate-versioning-to-semver`. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
