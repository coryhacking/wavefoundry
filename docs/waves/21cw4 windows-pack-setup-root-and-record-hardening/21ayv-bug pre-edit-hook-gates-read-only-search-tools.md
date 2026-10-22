# Let the Claude Pre-Edit Hook Pass Read-Only Grep and Glob

Change ID: `21ayv-bug pre-edit-hook-gates-read-only-search-tools`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-21
Wave: 21cw4 windows-pack-setup-root-and-record-hardening

## Rationale

A downstream distribution reported after upgrading to 1.34 that the pre-edit hook blocks a read-only Grep on framework seeds, so agents fall back to shell reads. Verified at `1c5ba851`:

- The rendered Claude hook registers `PreToolUse` with no matcher, so it sees every tool.
- `CLAUDE_NON_EDIT_TOOL_NAMES` (`.wavefoundry/framework/scripts/render_platform_surfaces.py:1012`) is `("Read", "Bash")`. Any other tool not in the edit list is treated as unfamiliar: its `tool_input.path` is passed to `gate_file_path`, which refuses seed and framework paths while the edit gates are closed.
- Grep and Glob carry `tool_input.path`, so a search scoped to `.wavefoundry/framework/seeds/` is blocked although neither tool can write.
- The list dates from `6717540a`; no hook test exercises Grep or Glob.

## Product Intent

Agents on Claude Code can search framework seeds and scripts with Grep and Glob while the edit gates are closed, as they already can with Read. Before: a scoped search is refused with a seed or framework edit message. After: it runs; edit tools stay gated exactly as now. Boundaries: only Claude's documented read-only search tools are added; other hosts' tool lists and the unfamiliar-tool path for undocumented tools are unchanged. AC-1 with AC-2 tests whether the intent was established.

## Requirements

1. `Grep` and `Glob` are classified as non-edit tools in the rendered Claude pre-edit hook, alongside `Read` and `Bash`.
2. `Edit`, `Write`, `MultiEdit` and `NotebookEdit` on seed and framework paths are still refused while the matching gate is closed.
3. An unfamiliar tool naming a gated path is still refused.

## Scope

**Problem statement:** the Claude pre-edit hook treats read-only search tools as possible edits and blocks them on gated paths.

**In scope:**

- The Claude non-edit tool list in the renderer and the re-rendered `.claude/hooks/pre-edit.py`.
- Hook tests driving the rendered hook with Grep, Glob and edit payloads, and `test_evidenced_non_edit_names_preserve_no_feedback` (`tests/test_render_platform_surfaces.py`), which pins the Claude list.

**Out of scope:**

- Copilot, Cursor, Codex or other host hook tool lists (no verified report; their search tool names are not confirmed here).
- The core-read MCP exemption contract.

## Acceptance Criteria

- [x] AC-1: The rendered hook exits 0 for a Grep payload and a Glob payload whose `path` is under `.wavefoundry/framework/seeds/`, with both gates closed; the current hook refuses both.
- [x] AC-2: With both gates closed, an Edit payload on a seed path and an unfamiliar-tool payload naming a seed path are still refused with the existing messages.
- [x] AC-3: The re-rendered `.claude/hooks/pre-edit.py` matches the renderer output (no render drift).
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add `Grep` and `Glob` to `CLAUDE_NON_EDIT_TOOL_NAMES`, update its source comment, and update the test that pins the list.
- [x] Re-render platform surfaces.
- [x] Add hook tests for AC-1 and AC-2.
- [x] CHANGELOG Unreleased entry (Fixed).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                       |
| ---------- | ----------- | ---------- | --------------------------- |
| fix        | implementer | none       | renderer list and re-render |
| tests      | implementer | fix        | rendered hook payload tests |


## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.claude/hooks/pre-edit.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: one classification list in an existing hook; no boundary, flow or verification seam changes.

## Platform Behavior

The hook is a Python script with identical behaviour on native Windows, macOS, Linux and WSL2; tool names are host identities, not paths, so no separator or case handling changes. Target repositories receive the updated hook when setup or upgrade re-renders platform surfaces.

## AC Priority


| AC   | Priority | Rationale                  |
| ---- | -------- | -------------------------- |
| AC-1 | required | the reported block         |
| AC-2 | required | edit gating unchanged      |
| AC-3 | required | rendered surface in sync   |
| AC-4 | required | change-local verification  |


## Progress Log


| Date       | Update  | Evidence                                              |
| ---------- | ------- | ----------------------------------------------------- |
| 2026-10-21 | Planned | distribution 1.34 upgrade note, verified at `1c5ba851` |
| 2026-10-21 | Readiness amendments: name the pinning test; state target delivery on re-render. | readiness qa-reviewer and release-reviewer findings |
| 2026-10-21 | Implemented: `CLAUDE_NON_EDIT_TOOL_NAMES` is `("Read", "Bash", "Grep", "Glob")` with an updated comment; pinning test updated; new rendered-hook tests for Grep/Glob on the seeds folder and for Edit, Write, MultiEdit, NotebookEdit and an unfamiliar tool on a seed path. Re-render left to the coordinator. | known-bad: with the old list the AC-1 test and the pinning test fail ("unfamiliar tool" exit 2); AC-2 test passes on both. Focused `test_render_platform_surfaces.py` 153 run, only `test_committed_rendered_hooks_match_the_renderer` fails (expected drift until re-render) |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-21 | Name Grep and Glob as non-edit tools | Smallest fix; both are documented read-only Claude tools | Give `PreToolUse` an edit-tool matcher (also drops the unfamiliar-tool coverage the hook relies on); leave as is and document shell reads (keeps the friction) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A future Claude tool named Grep or Glob gains write behaviour | Same exposure as Read today; revisit if the host documents such a change |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
