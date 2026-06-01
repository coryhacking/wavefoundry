# `render_bin_launchers` Missing the `mcp-server` Bin Launcher

Change ID: `130eu-bug render-bin-launchers-missing-mcp-server`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130et framework-bin-mcp-server-launcher

## Rationale

The framework references `.wavefoundry/bin/mcp-server` in five places as the canonical, portable entry point for the local MCP stdio server:

- `.wavefoundry/framework/scripts/render_platform_surfaces.py:764` — Claude `.mcp.json` registration uses this path
- `.wavefoundry/framework/scripts/render_agent_surfaces.py:135` — agent-surface generation references it
- `.wavefoundry/framework/scripts/setup_index.py:821` — operator hand-off message points to it
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py:329` — asserts the path
- `.wavefoundry/framework/scripts/tests/test_setup_index.py:484` — asserts the path

The `render_bin_launchers()` function in `render_platform_surfaces.py` (lines 896-989) is the canonical writer for everything under `.wavefoundry/bin/`. It currently writes six scripts: `docs-lint`, `docs-gardener`, `wave-dashboard`, `update-indexes`, `setup-wavefoundry`, `upgrade-wavefoundry`. **It never writes `mcp-server`.** In a freshly provisioned target repo, the `.mcp.json` Claude/Codex/Junie configurations would register a path that doesn't exist.

The script exists in this repo because it was created by hand or by an earlier render generation that has since been overridden — it's drift, not provisioning.

Source: operator report 2026-05-31 from another project where the gap manifested.

## Requirements

1. `render_bin_launchers()` in `render_platform_surfaces.py` must write `.wavefoundry/bin/mcp-server` alongside the existing six launchers.
2. The launcher must follow the same shape as the others: shebang, `set -euo pipefail`, repo-root resolution from `BASH_SOURCE`, venv-aware Python selection, and `exec` to the canonical framework script.
3. The script that `mcp-server` exec's is `.wavefoundry/framework/scripts/server.py --root .` (matching the existing hand-installed launcher in this repo).
4. The launcher must be executable (mode 0755 — same `executable=True` flag as the others).

## Scope

**Problem statement:** Framework code references `.wavefoundry/bin/mcp-server` in five places but `render_bin_launchers` never creates it. New target repos register a missing executable.

**In scope:**

- `.wavefoundry/framework/scripts/render_platform_surfaces.py` — add the `mcp_server_src` block and the `write_text(bin_dir / "mcp-server", ...)` call inside `render_bin_launchers()`.
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py` — add a test that asserts the launcher is created and has the expected content (delegates to `server.py`, uses venv block).

**Out of scope:**

- Generating `wave-gate` from `render_bin_launchers`. `wave-gate` is a standalone Python script (not a thin shell launcher) and is referenced only in `CLAUDE.md` as a CLI fallback, not in framework code. Generating it would require moving its logic into a framework script and rewriting as a delegating launcher — separate change, file if reported.
- Refactoring the launcher templates into a data-driven loop. The current 6→7 pattern is clear and the duplication is mechanical; deferring until a future change introduces a 4th repetition.
- Touching the hand-installed `mcp-server` in this repo. Once render_bin_launchers writes it, the next `wave_sync_surfaces` will overwrite the hand-installed file with the canonical content.

## Acceptance Criteria

- [x] AC-1: `render_bin_launchers()` writes `.wavefoundry/bin/mcp-server` with the canonical content (shebang, `set -euo pipefail`, repo-root resolution, venv block, `cd "$REPO_ROOT"`, `exec "$PYTHON" ".wavefoundry/framework/scripts/server.py" --root . "$@"`). Verified: rendered content is byte-identical to the hand-installed launcher already in this repo.
- [x] AC-2: The new launcher is created with `executable=True`. Verified: rendered file has mode bits including execute (`st_mode & 0o111 != 0`).
- [x] AC-3: `tests/test_render_platform_surfaces.py::TestRenderBinLaunchers` gains assertions for the new launcher folded into the existing `test_creates_bin_launchers` and `test_bin_launchers_are_executable` tests (matches the existing convention — one test per shape, asserting all launchers). Assertions cover existence, executable bit, presence of `server.py`, `--root .`, the venv block, and the shebang.
- [x] AC-4: All existing tests continue to pass — 1878/1878. (The new assertions extended existing tests rather than adding a new test case; per the existing convention in the file. Net assertion count grew without changing the test case count.)
- [ ] AC-5: Manual smoke verification — pending operator confirmation in a fresh target repo after their next `wave_sync_surfaces` or `wave_upgrade`.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `mcp_server_src` template in `render_bin_launchers()` immediately after `upgrade_wavefoundry_src`
- [x] Add `write_text(bin_dir / "mcp-server", mcp_server_src, executable=True)` after the upgrade-wavefoundry write
- [x] Add assertions to `test_render_platform_surfaces.py` for the new launcher (folded into existing tests per file convention)
- [x] Close gate
- [x] Run framework tests — 1878/1878 pass
- [x] Diff canonical render against hand-installed copy — byte-identical
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The missing launcher is the bug; writing it is the fix |
| AC-2 | required | Executable bit must be set or the launcher can't run |
| AC-3 | required | Test guards against future regressions of the same shape |
| AC-4 | required | No existing tests regress |
| AC-5 | important | Manual smoke confirms the end-to-end provisioning works in a fresh target repo |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Reuse the existing `_venv_block` shell snippet | Matches all six existing launchers; venv-aware Python selection is the established pattern | Inline a different venv-resolution scheme (rejected — drift) |
| 2026-05-31 | Use `cd "$REPO_ROOT" && exec "$PYTHON" ".wavefoundry/framework/scripts/server.py" --root . "$@"` | Mirrors the structure of `docs-lint` / `update-indexes` (which also `cd` first) and matches the hand-installed launcher already in this repo | Pass repo root as `--root "$REPO_ROOT"` without `cd` (rejected — small drift from the existing hand-installed shape) |
| 2026-05-31 | Out of scope: generate `wave-gate` here too | `wave-gate` is a Python script with its own logic, not a thin delegating launcher; folding it in would mean either inlining ~70 lines of Python or rewriting its architecture | File a separate change if `wave-gate` provisioning is observed as broken in target repos |

## Risks

| Risk | Mitigation |
|---|---|
| The hand-installed `mcp-server` in this repo has subtly different behavior than the canonical render | Diff before sync; if differences exist, document them and adapt the canonical content |
| Target repos that already have a hand-installed `mcp-server` will see it overwritten on next sync | This is the desired behavior — `wave_sync_surfaces` is authoritative; the canonical content is what we want |

## Related Work

- Reported from another project after wave `1305t` shipped. Demonstrates the value of the `1305d` fix-now-not-later principle: small framework gap → small change → fix in-session, not deferred.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
