# Claude Edit Hooks Cover Every Edit Tool and Fail Closed

Change ID: `1z8op-bug claude-edit-hook-coverage`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-28
Wave: 1z8ot edit-gate-and-lock-hardening

## Rationale

A downstream validation of `d295b92` found three gaps in the rendered Claude edit hooks. The seed and framework gates protect the prompts every target repository renders.

- The rendered `PreToolUse` and `PostToolUse` entries use `"matcher": "Edit|Write"` (`render_platform_surfaces`, the Claude hook table). Claude Code matches each alternative exactly, so `NotebookEdit`, and `MultiEdit` where a host still offers it, never runs the pre-edit gate or the post-edit docs-lint and reindex.
- The hook's `detect_file_path` reads `tool_input.file_path`, `tool_input.path`, `tool_info.file_path`, `file_path` and `path`, but not `tool_input.notebook_path`. So even a hook that ran would allow a `NotebookEdit` of a gated file.
- The Claude pre-edit hook allows (exit 0) a payload it cannot parse as JSON, and an edit-tool payload with no recognisable path.

## Requirements

1. **Matcher.** The Claude `PreToolUse` and `PostToolUse` matchers cover `Edit|Write|MultiEdit|NotebookEdit`.
2. **Notebook path.** `detect_file_path` also reads `tool_input.notebook_path`.
3. **Fail closed.** The Claude pre-edit hook fails closed on payloads it cannot inspect, through a pre-edit-only strict parser. The shared `load_payload` is used by every host hook and keeps its lenient behaviour.
   - It blocks (exit 2) when stdin is empty, is not valid JSON, or is not an object.
   - It blocks when `tool_name` is one of `Edit`, `Write`, `MultiEdit` or `NotebookEdit`, or is absent, and no path is found.
   - It allows any other `tool_name`.
   - The block message names the payload keys it looked for.
4. **Other hosts, checked against evidence.** Each host hook (Copilot pre-tool-use, Cursor, Windsurf) is checked against a cited payload fixture for that host's plain file edits first, then notebook and multi-file edits. Citing the host documentation or a captured payload counts as evidence.
   - The readiness review suspects the Copilot gate reads neither Copilot CLI's `toolArgs` (a JSON string) nor VS Code's `filePath`, which would make it inert. This is verified first.
   - Any host whose gate cannot see the path is fixed so it reads that host's shape.
   - A fail-closed rule for a host uses that host's own list of edit tool names, so shell and read tools are never blocked.
   - Cursor (`afterFileEdit`, top-level `file_path`) and Windsurf (`pre_write_code`, `tool_info.file_path`) are expected to be covered, with notebooks not applicable; that is confirmed and recorded.
5. **Windsurf reindex.** The Windsurf docs-lint hook (`windsurf_docs_lint_source`) calls `maybe_trigger_reindex` (not `mark_reindex_pending_for`, whose marker only a turn-end flush clears, and Windsurf has no Stop hook) for every edit. Today it triggers no reindex at all. It does this before reporting a lint failure.
6. **Known limits, stated once where targets see them.** Seed `050-agent-entry-surface-bootstrap.prompt.md`'s per-platform capability matrix records the edit gates' known limits:
   - the shell tool is not gated on any host;
   - file-writing MCP tools (the Wavefoundry server's and third-party servers') are not gated on Claude, because the matcher covers only built-in tools;
   - a hook resolves the path and then the host writes it (a check-then-use window), which needs an actor who can already write the repository;
   - a missing `python3` makes the shell return 127, not 2, so the gate fails open on Claude and Windsurf.

   `docs/architecture/threat-model.md` adds rows under `## Current Risks`, next to the seed-protection and plan-gate bypass rows, pointing at the seed's matrix rather than repeating it.
7. **Seeds.** Seed 050's Claude Code JSON block and seed `160-upgrade-wavefoundry.prompt.md` (which states the `Edit|Write` matcher) are updated to the new matcher, under `seed_edit_allowed`.
8. **Re-render safely.** The composed hook body is tested through a subprocess before this repository's surfaces are re-rendered: a broken `pre-edit.py` would block every edit, including its own fix. The rendered surfaces (`.claude/settings.json`, the hook bodies, the Windsurf hook, and the Copilot and Cursor hooks if changed) are then regenerated, and the CHANGELOG operator note names the re-render.

## Scope

**Problem statement:** some edit tools and malformed payloads bypass the edit gates, and the gates' limits are not stated where targets see them.

**In scope:**

- `render_platform_surfaces.py` hook table and hook sources.
- Seeds 050 and 160; `threat-model.md`; the rendered surfaces; tests.

**Out of scope:**

- Gating the shell tool or MCP write tools, and closing check-then-use windows. All three are documented as known limits (Requirement 6), not changed.

## Acceptance Criteria

- [x] AC-1: the rendered Claude settings match `Edit`, `Write`, `MultiEdit` and `NotebookEdit` for both pre- and post-edit hooks, and seeds 050 and 160 state the same matcher.
- [x] AC-2: a `NotebookEdit` payload whose `notebook_path` is a seed prompt is blocked with the seed gate closed and allowed with it open.
- [x] AC-3: fixtures with and without a `tool_name` cover empty stdin, invalid JSON, a non-object payload, and an edit tool with no path; each is blocked (exit 2), and the message names the keys looked for. A non-edit `tool_name` with no path is allowed; an ordinary `Write` of a seed is still blocked (positive control); other host hooks that share `load_payload` are unchanged.
- [x] AC-4: each host has a cited payload fixture for plain file edits and, where the host supports them, notebook and multi-file edits. The host's gate blocks a gated path in each (on Cursor, whose `afterFileEdit` gate cannot block, it halts with `continue: false`). Any host found inert today (Copilot suspected) is fixed and recorded; a case a host cannot express is recorded as not applicable.
- [x] AC-5: on Windsurf, both a doc edit with failing lint and a code edit trigger a reindex.
- [x] AC-6: seed 050's capability matrix states the four known limits, and `threat-model.md` has `## Current Risks` rows pointing at it.
- [x] AC-7: the change's own suites pass, the rendered surfaces match the renderer, and the documents it edits validate.

## Tasks

- [x] Matcher; `notebook_path`; a pre-edit-only strict parser with the tool-name rule.
- [x] Check the Copilot, Cursor and Windsurf payloads against cited fixtures, Copilot first; fix any inert gate.
- [x] Windsurf `maybe_trigger_reindex`.
- [x] Seeds 050 and 160 (gate), including the known-limits matrix; `threat-model.md` rows.
- [x] Subprocess-test the composed hook before re-rendering; re-render; add tests; CHANGELOG operator note.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Hooks | implementer | readiness | Renderer, seeds and rendered surfaces |
| Review | combined reviewer | Hooks | Code, QA, security, architecture, docs contract |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.claude/settings.json`, `.claude/hooks/`, `.windsurf/hooks/`, `.github/hooks/`, `.cursor/hooks/`
- `docs/architecture/threat-model.md`
- `CHANGELOG.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md`: `## Current Risks` rows pointing at seed 050's known limits (Requirement 6).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The main gap, and seeds that agree with it |
| AC-2 | required | Notebook edits of gated files |
| AC-3 | required | Fail closed on unreadable payloads |
| AC-4 | required | A host gate that cannot see the path protects nothing |
| AC-5 | important | Windsurf parity with the other post-edit hooks |
| AC-6 | required | Limits are stated where targets see them |
| AC-7 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Delivery repair DEL-F4 and the nonblocking Claude `Read` note. `copilot_is_edit` now reads `command` for the text-editor tools (`COPILOT_TEXT_EDITOR_TOOL_NAMES`: `str_replace_editor`, `str_replace_based_edit_tool`) from `copilot_tool_args`, the same place the path is read (`toolArgs` JSON string or `tool_input` object); only `view`, the one read in Anthropic's text editor tool docs (`COPILOT_TEXT_EDITOR_READ_COMMANDS`), is not an edit. `str_replace`, `create`, `insert`, `undo_edit` (text_editor_20241022/20250124) and a missing, empty, non-string or unknown command stay edits. The post hook shares the classifier, so a `view` runs no lint and marks no reindex. The Claude pre-edit hook now allows a named `tool_name` outside `CLAUDE_EDIT_TOOL_NAMES` whatever its path; a missing, empty or non-string `tool_name` is treated as an edit (gated with a path, blocked without one). Seed 050's Copilot paragraph and the Copilot CHANGELOG bullet say a text-editor `view` is a read. Scratch mutation: restoring the name-only classifier fails the new view test on all 8 view subtests (4 pre exit 2, 4 post exit 1); removing the named-non-edit allowance fails the Claude test. Scratch-root probe of the composed bodies before re-rendering: Claude Write of a non-gated path 0, of a seed 2; Copilot `str_replace_editor` view of a seed 0, str_replace of a seed 2. Re-rendered claude, copilot, cursor and windsurf surfaces. Gapfill: shell `grep` of the fetched text-editor docs page for its command list, and of seed 050 for the Copilot paragraph (prose, not code) | `test_text_editor_view_is_a_read_and_other_commands_stay_edits`, `test_claude_pre_edit_allows_named_non_edit_tools_and_gates_unnamed_ones`; `test_render_platform_surfaces.py` 116 OK |
| 2026-09-28 | Delivery repair DEL-F1 and DEL-F3. `COPILOT_EDIT_TOOL_NAMES` adds `write`, `str_replace_based_edit_tool`, `createFile`, `writeFile` and `insert_edit_into_file`; seed 050's Copilot paragraph lists them and `replacements[].filePath`. The input shapes for `insert_edit_into_file`, `create_file`, `replace_string_in_file`, `edit_notebook_file` (`filePath`) and `multi_replace_string_in_file` (`replacements[].filePath`) are confirmed in the Copilot Chat extension source (`toolNames.ts`, package.json `languageModelTools`); `str_replace_based_edit_tool` takes `path` per Anthropic's text editor tool docs; `write`, `createFile` and `writeFile` have no documented input shape, so the hook reads every known path key and fails closed when none is present. The renderer comment no longer credits `tool_input.filePath` or `edit_notebook_file` to humanwhocodes or aridanemartin (neither page shows them). Scratch-root probe of the composed bodies: Claude Write of a non-gated path 0, of a seed 2; Copilot `view` of a seed 0, `insert_edit_into_file` of a seed 2; a mutant without `replacements[].filePath` parsing exits 2 on a non-gated multi-replace, which the new fixture rejects. Gapfill: shell `grep` over the test file and seeds to locate the fixture test, its citations and the seed tool list, since MCP keyword search over the tree returned index-database hits that swamped the result | `test_render_platform_surfaces.py` (114 OK; `test_host_payload_fixtures_reach_the_gate` has one blocked-seed fixture per gated name, asserts every name is covered, and allows a non-gated `multi_replace_string_in_file`) |
| 2026-09-28 | Implemented R1 to R5, R7, R8 and the seed 050 half of R6. Matcher `Edit\|Write\|MultiEdit\|NotebookEdit` from one constant; `FILE_PATH_KEYS` adds `tool_input.notebook_path`; a pre-edit-only strict parser (Claude and Copilot pre hooks) blocks empty, non-JSON, non-object and pathless edit payloads and names the keys. Copilot gate confirmed INERT before this change (CLI sends `toolName` plus a JSON-string `toolArgs.path`; VS Code sends `tool_input.filePath` or `tool_input.files`; the gate read neither) and fixed with Copilot's own edit-tool list. Cursor (top-level `file_path`) and Windsurf (`tool_info.file_path`) confirmed covered; notebooks and multi-file edits not applicable there. Windsurf docs-lint now calls `maybe_trigger_reindex`. Composed bodies subprocess-probed in a scratch root before re-rendering `.claude`, `.github/hooks`, `.cursor/hooks` and `.windsurf/hooks`. Gapfill: shell grep for seed/test census where `code_keyword` needed multi-glob filtering | `RenderedEditHookPathTests` (5 new tests); `test_render_platform_surfaces.py` 114 ok |
| 2026-09-28 | Readiness confirmation: all findings resolved; R1 adopted (Cursor halts rather than blocks) | readiness confirmation |
| 2026-09-28 | Readiness review. B1 adopted: seeds 050 and 160 state the matcher and are in scope. N1: the Copilot gate may be inert; AC-4 requires cited per-host fixtures, Copilot first. N2: strict parse is pre-edit only, with a tool-name rule. N3: Windsurf uses `maybe_trigger_reindex` and has no reindex today. N4: MCP write tools added as a limit; limits live in seed 050, with `threat-model.md` rows pointing at them. N5: host hook paths added; re-render only after a subprocess test | readiness review |
| 2026-09-28 | Operator folded in the report's smaller observations: Windsurf docs-lint reindex marking, and the threat-model known limits (shell tool, check-then-use, missing `python3`) | operator decision |
| 2026-09-28 | Planned from a downstream validation report. Confirmed in the tree: `.claude/settings.json` matches only `Edit\|Write`; `detect_file_path` has no `notebook_path` | `.claude/settings.json`; `render_platform_surfaces.detect_file_path` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | Fail closed on unparseable and pathless edit payloads, with a pre-edit-only parser | An edit the gate cannot inspect should not proceed; the shared parser serves non-gate hooks too | Allow and warn; change the shared parser |
| 2026-09-28 | State the limits in seed 050 and point `threat-model.md` at it | The seed ships to targets; one copy cannot drift (readiness docs-contract seat) | Two full copies |

## Risks

| Risk | Mitigation |
| --- | --- |
| A host sends a legitimate edit payload shape the hook does not recognise, and it is now blocked | Per-host cited fixtures (AC-4); the block message names the keys looked for |
| A broken re-rendered pre-edit hook blocks every edit, including its own fix | Subprocess-test the composed body before re-rendering (Requirement 8) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
