# [Change Title]

Change ID: `1p590-maint project-relative-tracked-surfaces`
Change Status: `planned`
Owner: [role or person]
Status: planned
Last verified: 2026-06-13
Wave: [wave-id or TBD]

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

- [ ] AC-1: `render_platform_surfaces.launcher_command` and the MCP-command emission produce project-relative paths; a unit test asserts no rendered output contains an absolute path or the repo root.
- [ ] AC-2: after running the renderer from a non-author checkout path (fresh-clone simulation), the 5 surfaces resolve correctly — hooks fire and the MCP server starts.
- [ ] AC-3: a case-insensitive `git grep -nI "/users/"` over tracked files returns no hits in the editor/MCP surfaces, renderer output, or the graph-indexer test fallback. (Case-insensitive per the rename-gate practice.)
- [ ] AC-4: `.cursor/mcp.json` and `.junie/mcp/mcp.json` invoke `.wavefoundry/bin/mcp-server` (parity with root `.mcp.json`).
- [ ] AC-5: full framework suite (`run_tests.py`) and docs-lint are green.

## Tasks

- [ ] Drop the `repo_root`-absolute branch in `launcher_command` (emit relative); route MCP-command emission through the `.wavefoundry/bin/mcp-server` launcher.
- [ ] Confirm whether Claude Code resolves a relative hook command; if not, use `$CLAUDE_PROJECT_DIR/...`. Confirm the equivalent for Cursor/Copilot/Junie.
- [ ] Regenerate the 5 surfaces and reconcile the committed copies to the portable forms.
- [ ] Derive the `test_graph_indexer.py` fallback path from the repo root; de-path or untrack the benchmark report `root` field.
- [ ] Update the renderer tests (11) to assert project-relative output.

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

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required / important / nice-to-have / not-this-scope |           |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


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
