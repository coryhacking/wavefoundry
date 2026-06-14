# Project-relative paths in tracked editor/MCP surfaces

Change ID: `1p590-maint project-relative-tracked-surfaces`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p58z repo-portability-and-install-docs`

## Rationale

The platform-surface renderer (`.wavefoundry/framework/scripts/render_platform_surfaces.py`) bakes a per-machine ABSOLUTE command path into the hook/MCP configs it generates: `launcher_command()` returns `repo_root / rel_base` when given a root, and the editor MCP configs use the absolute `_venv_python_path()`. Those rendered surfaces were committed to this repo with the author's `/Users/coryhacking/...` paths, so a contributor cloning the repo inherits dead Edit/Write hooks and a non-resolving MCP command — a real onboarding blocker. The portable pattern already exists in-repo: the root `.mcp.json` invokes `.wavefoundry/bin/mcp-server`, a launcher that resolves the venv via `$HOME` itself. Tracked files should never carry an absolute machine path.

## Requirements

1. `render_platform_surfaces.py` emits project-relative command paths for all tracked surfaces — no `repo_root`-absolute output. Claude hooks use a project-relative form (a relative command, or `$CLAUDE_PROJECT_DIR/...` only where the tool cannot resolve a relative command).
2. Editor MCP configs (`.cursor/mcp.json`, `.junie/mcp/mcp.json`) invoke the portable `.wavefoundry/bin/mcp-server` launcher (parity with root `.mcp.json`), not the absolute venv python.
3. The committed surfaces are regenerated/reconciled to the portable forms: `.claude/settings.json`, `.cursor/hooks.json`, `.cursor/mcp.json`, `.github/hooks/hooks.json`, `.junie/mcp/mcp.json`.
4. Remaining tracked absolute-path leaks are removed: the `test_graph_indexer.py` hard-coded fallback path derives from the repo root; the benchmark report JSONs with an absolute `root` field are de-pathed or untracked (decide at prepare).
5. No tracked file contains an absolute machine path.

## Scope

**Problem statement:** committed rendered editor/MCP surfaces (plus a few stragglers) hard-code the author's absolute paths, breaking hooks and the MCP command for anyone who clones the repo.

**In scope:**

- `render_platform_surfaces.py` path/command emission + its 11 tests.
- The 5 committed surfaces (`.claude/settings.json`, `.cursor/hooks.json`, `.cursor/mcp.json`, `.github/hooks/hooks.json`, `.junie/mcp/mcp.json`).
- The `test_graph_indexer.py` absolute fallback path; the benchmark report `root` field.

**Out of scope:**

- Changing what the hooks/MCP server DO (behavior-neutral).
- The install-doc reorganization (that is `1p591`).
- Per-user gitignored files (allowed to remain machine-specific).

## Acceptance Criteria

- [x] AC-1: `render_platform_surfaces.launcher_command` emits a project-relative command (the `repo_root`-absolute branch was removed) and the MCP renders use the `.wavefoundry/bin/mcp-server` wrapper; `test_render_platform_surfaces` runs the renderer in a temp dir and asserts the emitted commands are relative.
- [x] AC-2: the renderer was run from a non-author checkout (the renderer test's temp-dir subprocess) and emits portable forms; the MCP wrapper path is proven by the root `.mcp.json` (this very session's MCP runs through it). **Operator note:** live hook-firing in Cursor/Copilot/Junie should be confirmed on those editors — Claude (`$CLAUDE_PROJECT_DIR`-equivalent project-root resolution) and the wrapper-based MCP are the verified paths; bare-relative hook resolution for the other editors is the remaining live check.
- [x] AC-3: case-insensitive `git grep -i "/users/"` over tracked files shows **no** hits in the editor/MCP surfaces, the renderer, or the graph-indexer test fallback. (Remaining hits are intentional: secrets-detection regexes/fixtures, CHANGELOG prose, doc examples, and this wave's own docs describing the gate.)
- [x] AC-4: `.cursor/mcp.json` and `.junie/mcp/mcp.json` both invoke `.wavefoundry/bin/mcp-server` (parity with root `.mcp.json`).
- [x] AC-5: full framework suite (`run_tests.py`) → 3154 OK; `wave_validate` → docs-lint ok.

## Tasks

- [x] Drop the `repo_root`-absolute branch in `launcher_command` (emit relative); route MCP-command emission through the `.wavefoundry/bin/mcp-server` launcher.
- [~] Confirm whether Claude Code resolves a relative hook command; if not, use `$CLAUDE_PROJECT_DIR/...`. *Deferred:* chose bare-relative (proven for Claude + the MCP wrapper); per-editor live confirmation for Cursor/Copilot/Junie is operator-side (AC-2).
- [x] Regenerate the 5 surfaces and reconcile the committed copies to the portable forms.
- [x] Derive the `test_graph_indexer.py` fallback path from the repo root; de-path or untrack the benchmark report `root` field.
- [x] Update the renderer tests (11) to assert project-relative output.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- [Shared file or integration gate that requires coordination before parallel work proceeds]

## Affected Architecture Docs

N/A for the core architecture docs — this is a behavior-neutral path-portability change confined to the surface renderer and its generated outputs. Update the contributing/setup reference doc (`docs/contributing/build-and-verification.md` and/or the platform-surface/setup reference) if it documents the command-path form; otherwise no architecture-doc impact.

## AC Priority

| AC   | Priority      | Rationale |
| ---- | ------------- | --------- |
| AC-1 | required      | The renderer is the source of every install's surfaces; relative emission is the actual fix. |
| AC-2 | required      | Fresh-clone resolution is the user-visible goal (contributors can run hooks/MCP). |
| AC-3 | required      | The grep gate is the objective, regression-proof check that no machine path leaks. |
| AC-4 | important     | Launcher parity removes the absolute venv path; high value but the hook paths are the primary blocker. |
| AC-5 | required      | Suite + docs-lint green is the non-negotiable regression gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-13 | Implemented: `launcher_command` emits project-relative (dropped `repo_root`-absolute); Cursor/Junie MCP switched to the `.wavefoundry/bin/mcp-server` wrapper; the now-dead absolute-venv helper `_venv_python_path`/`_VENV_DEFAULT` removed; 5 committed surfaces regenerated by the renderer; `test_graph_indexer` absolute fallback derived from `__file__`; benchmark report JSONs untracked + gitignored. Renderer tests updated. | suite 3154 OK; docs-lint ok; AC-3 grep clean over surfaces/renderer/test-fallback |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
