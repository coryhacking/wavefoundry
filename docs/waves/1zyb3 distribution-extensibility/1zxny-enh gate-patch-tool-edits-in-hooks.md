# Gate Copilot apply_patch Edits by the File Headers in the Patch Text

Change ID: `1zxny-enh gate-patch-tool-edits-in-hooks`
Change Status: `implemented`
Owner: framework-operator
Status: planned
Last verified: 2026-10-06
Wave: 1zyb3 distribution-extensibility

## Rationale

The Copilot pre-tool-use gate ignores `apply_patch`. At HEAD `06c02e63`:

- `render_platform_surfaces.COPILOT_EDIT_TOOL_NAMES` (`.wavefoundry/framework/scripts/render_platform_surfaces.py` line 1197) does not list `apply_patch`, so `copilot_is_edit` returns False for it.
- The comment at line 1196 states the gap as "a known limit". The source comment at line 1180 notes that the Copilot hooks reference maps `apply_patch` to Claude's `Edit`.
- Seed `050-agent-entry-surface-bootstrap.prompt.md` line 499 tells targets "`apply_patch` carries its paths inside the patch text and is not gated". Its "Known limits of the edit gates" list (line 377) does not mention it.

So a Copilot agent can change a seed prompt or a framework-maintenance surface through `apply_patch` with no guard override. The patch format names every file it touches on a header line, so those paths can be gated by the same check every other Copilot edit tool goes through.

Census (predicate: every mention of `apply_patch` outside wave records and memory). Command: `grep -rn "apply_patch" --exclude-dir=waves --exclude-dir=memory --exclude-dir=.git --exclude-dir=index .`. Result: three hits, render_platform_surfaces.py lines 1180 and 1196 and seed 050 line 499 (plus this change doc).

Other hosts, checked for a patch-style tool the gates miss:

- **Claude Code.** `CLAUDE_EDIT_TOOL_NAMES` (line 248) is `Edit`, `Write`, `MultiEdit`, `NotebookEdit`. Claude Code's built-in tools include no patch tool: this session's own built-in edit tools are `Edit`, `Write` and `NotebookEdit`. The gaps on Claude are shell writes (`Bash`) and file-writing MCP tools, both already listed known limits. No matcher change is needed.
- **Cursor.** `render_cursor_hooks` registers only `afterFileEdit`, which reports a path after the write and has no tool name to match. Seed 050 line 434 already states there is no pre-write event.
- **Windsurf.** `pre_write_code` and `post_write_code` pass the file path the host is writing, with no tool-name filter, so no patch tool can bypass them.
- **Codex, Junie, Antigravity.** `render_platform_entrypoints` renders no hook for these hosts, only MCP config (and `.aiignore` for Junie). Codex's `apply_patch` therefore stays ungated: there is no hook host to put the check in.

## Requirements

1. `apply_patch` joins `COPILOT_EDIT_TOOL_NAMES`, so both Copilot hooks treat it as an edit.
2. **Finding the patch text.** For `apply_patch`, the hook reads the patch text from the tool arguments' `input` key, then `patch`. If the arguments field (`toolArgs` or `tool_input`) is a string that is not a JSON object, the hook uses that string as the patch text.
3. **Header paths.** The hook removes an optional trailing `\r` and any leading whitespace from each line, then extracts a path from each line that begins with one of: `*** Add File: `, `*** Update File: `, `*** Delete File: `, `*** Move to: `.
   - The path is the rest of the line with surrounding whitespace removed. An empty result is no path.
   - Leading whitespace is stripped so an indented patch (some hosts indent the envelope) still gates. An added or removed hunk line begins with `+` or `-`, so its content never counts as a header. A context line (space prefix) that happens to read like a header is counted, which can only add a gated path, so it errs toward blocking.
4. **Pre-tool-use.** Every extracted path, the source and destination of a move included, goes through the existing `gate_file_path`. The first blocking verdict blocks the whole patch.
   - For `apply_patch` the gated set is the header paths alone. The generic `detect_file_path` fallback that `copilot_edit_paths` appends for other tools is not merged, so a stray top-level `file_path` in the payload can neither satisfy the fail-closed check nor stand in for the patch's real targets.
   - If no header path can be extracted (no patch text, or no header), the hook blocks with `block_uninspectable`. The message lists the patch headers among the inspected keys (fail closed, as for an edit tool with no path).
5. **Post-tool-use.** The hook runs `maybe_docs_lint` and `maybe_trigger_reindex` for each extracted path, as it does for the other edit tools, so the move's source and a deleted file are reindexed too.
6. **Known-limit text.** The text is updated in three places:
   - the comment at render_platform_surfaces.py line 1196;
   - seed 050 line 499: `apply_patch` is gated by its header paths, and an `apply_patch` whose paths cannot be read is blocked;
   - seed 050's "Known limits of the edit gates" list gains one bullet: Codex `apply_patch` is not gated because Wavefoundry renders no Codex hook, and AGENTS.md rules are the only control there.
7. The existing known-limit bullets stay as they are: shell writes on every host, MCP writes on Claude, check-then-use, and missing `python3`. `docs/architecture/threat-model.md` gains a row for the Codex limit that points at seed 050.

## Scope

**Problem statement:** Copilot `apply_patch` edits bypass the seed and framework-maintenance gates.

**In scope:**

- `render_platform_surfaces.py`: `COPILOT_EDIT_TOOL_NAMES`, patch-text reading and header extraction inside `_COPILOT_PAYLOAD_SOURCE`, the `COPILOT_PATH_KEYS` message, and the comment.
- Re-rendered self-host surfaces `.github/hooks/pre-tool-use.py` and `.github/hooks/post-tool-use.py`.
- Seed 050 (line 499 and the known-limits list), `docs/architecture/threat-model.md`, CHANGELOG.
- Tests in `test_render_platform_surfaces.py`.

**Out of scope:**

What stays ungated after this change, stated precisely:

- File writes through a shell tool on every host (Claude `Bash`, Copilot `bash`/`powershell`, a terminal).
- File-writing MCP tools on Claude.
- Every edit on Codex, Junie and Antigravity, which have no rendered hook; Codex `apply_patch` included.
- Cursor edits, which are checked only after the write.
- The check-then-use window.
- A missing `python3` on Claude and Windsurf.
- Relative patch paths are resolved against the repository root, as `repo_relative` already does for every Copilot path. A patch relative to a subdirectory working directory would be judged at the wrong location. This is the same behavior as today's relative `path` arguments and is not changed here.

Also out of scope: adding hooks for Codex or other hook-less hosts, and changing the Claude matcher.

## Acceptance Criteria

- [x] AC-1: The rendered Copilot pre-tool-use hook, driven with an `apply_patch` payload in each of these shapes, blocks (exit 2) when any header path is a seed prompt or framework-maintenance surface and the matching gate is closed, and allows the same payload when the gate is open: CLI form: `toolName` with `toolArgs` a JSON string holding `input`; VS Code form: `tool_name` with `tool_input.input`; raw form: `toolArgs` the raw patch string.
- [x] AC-2: Each header kind is gated on its own: `Add File`, `Update File`, `Delete File`, and a `Move to` whose source is ungated and destination gated (blocked) or the reverse (blocked). A multi-file patch with one gated path among ungated ones is blocked.
- [x] AC-3: A patch whose hunk content contains a line such as `+*** Add File: .wavefoundry/framework/seeds/x.prompt.md` while its only header names an ungated file is allowed. A patch with CRLF line endings, and one whose header lines are indented, is gated exactly like its plain LF form. An `apply_patch` payload with no header but a top-level `file_path` is still blocked as uninspectable (no fallback merge).
- [x] AC-4: An `apply_patch` payload with no patch text, or with text that has no header, is blocked by `block_uninspectable`, and its message names the patch headers.
- [x] AC-5: The post-tool-use hook runs docs-lint and reindex for every header path of an `apply_patch` payload. This is proven with the existing post-hook test doubles.
- [x] AC-6: Non-patch Copilot tools behave as before. The existing coverage test over `COPILOT_EDIT_TOOL_NAMES` passes with `apply_patch` covered, and shell and read tools are still never gated.
- [x] AC-7: The census command in Rationale, rerun, finds no text claiming Copilot `apply_patch` is ungated. Seed 050's known-limits list names Codex `apply_patch` as ungated, and `threat-model.md` has the matching row.
- [x] AC-8: `.github/hooks/pre-tool-use.py` and `.github/hooks/post-tool-use.py` in this repository equal the renderer's output after `wf render-surfaces`.

## Tasks

- [x] Open `framework_edit_allowed` for the renderer and the rendered hooks and close it after. Open `seed_edit_allowed` for seed 050 and close it right after.
- [x] `render_platform_surfaces.py`: add `apply_patch` to the names, add patch-text reading and header extraction to `copilot_edit_paths` (in the embedded source), extend `COPILOT_PATH_KEYS`, and update the comment.
- [x] Tests for AC-1 to AC-6 in `test_render_platform_surfaces.py`.
- [x] Record in the Progress Log the host parser behavior found during implementation: the documented Copilot `apply_patch` argument key (or its absence), and whether the host itself accepts indented headers.
- [x] Re-render the self-host surfaces (`wf render-surfaces` or `wf_sync_surfaces`) for AC-8.
- [x] Seed 050 edits, the `threat-model.md` row, and the CHANGELOG entry.
- [x] Run `wf_validate_docs`, then the full suite last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 hook source and tests | implementer | - | `render_platform_surfaces.py`, `test_render_platform_surfaces.py` |
| ws-2 render, seed and docs | implementer | ws-1 | `.github/hooks/`, seed 050, threat model, CHANGELOG |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.github/hooks/pre-tool-use.py`, `.github/hooks/post-tool-use.py`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `docs/architecture/threat-model.md`
- Root-level file edited (not a path token): CHANGELOG.md.

No `@mcp.tool` handler or tool schema changes, so neither the handler digest fixture nor any tool-surface golden is touched. The embedded hook source carries no record-vocabulary literal.

## Affected Architecture Docs

`docs/architecture/threat-model.md`: one row for Codex `apply_patch` (no hook host), pointing at seed 050's known limits. No existing threat-model row names Copilot `apply_patch`, so none needs correcting. `docs/ARCHITECTURE.md` and the other child docs: N/A, since this is a change inside one hook body.

## Platform Behavior

- The Copilot hook runs through the `bash` launcher on macOS, Linux and WSL2 and through the `powershell` launcher on native Windows (`render_copilot_hooks`). The parsing is pure Python in the rendered body, so it is identical on every platform.
- A trailing `\r` is removed from each line before header matching, so a CRLF patch from a Windows host gates the same as an LF patch (AC-3).
- Header paths go through `gate_file_path`, which uses `repo_relative`. That function resolves relative paths against the repository root, resolves symlinks, and casefolds on case-insensitive filesystems (macOS APFS default, Windows NTFS, WSL2 `/mnt/c`), as for every other Copilot path.
- Copilot denies on any non-zero pre-tool-use exit on every platform, so a block from this change is enforced everywhere the hook runs.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The gate itself, over each payload form we can name. |
| AC-2 | required | Every header kind, including both sides of a move. |
| AC-3 | required | No false positives from patch content; CRLF parity. |
| AC-4 | required | Fail closed when the paths cannot be read. |
| AC-5 | important | Docs gate and index stay correct after patch edits. |
| AC-6 | required | No regression for the other Copilot tools. |
| AC-7 | required | The documented known limits must be true. |
| AC-8 | required | The self-hosted hooks are what actually runs here. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-06 | Planned from the verified Waveforge report Part 3(f); claims checked against HEAD `06c02e63`; Claude, Cursor, Windsurf, Codex, Junie and Antigravity hook surfaces checked for patch-style tools. | Census command in Rationale. |
| 2026-10-06 | Implemented in `render_platform_surfaces.py`: `apply_patch` in `COPILOT_EDIT_TOOL_NAMES`; new `COPILOT_PATCH_TOOL_NAMES` and `COPILOT_PATCH_HEADERS`; embedded `copilot_patch_text` (`input`, then `patch`, or a non-object arguments string) and `copilot_patch_paths` (trailing `\r` and leading whitespace removed, header prefixes only, path trimmed, empty dropped); `copilot_edit_paths` returns the header paths alone for `apply_patch`; pre-tool-use blocks with `no patch file header was found`; `COPILOT_PATH_KEYS` names the patch headers. Self-host `.github/hooks/pre-tool-use.py` and `post-tool-use.py` re-rendered with `wf render-surfaces --platform copilot` (only those two files changed; byte-equal to a scratch render). Seed 050 line and known-limits bullet, threat-model row, CHANGELOG Security bullet. | `RenderedEditHookPathTests`: four new tests plus a `cli apply_patch` fixture in the coverage test; 14 tests ok. AC-7 census: only the new gating text and the Codex known limit remain. |
| 2026-10-06 | Host parser behavior: the Copilot hooks reference (docs.github.com/en/copilot/reference/hooks-reference) names `apply_patch` only in the tool-name mapping table (to Claude's `Edit`) and documents no argument key and no header indentation rule, so the `input`/`patch`/raw candidates and the fail-closed rule stand; whether the host accepts indented headers was not verified against a live host. | Mutation probes in scratch: header `lstrip` dropped, `+`/`-` stripped before matching, fail open with no header, `Move to` not read, fallback path merged, `apply_patch` removed from the edit names: all killed. Removing the explicit trailing `\r` strip is an equivalent mutant (the header prefix still matches and the path `.strip()` removes the `\r`), so CRLF parity holds either way. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-06 | Fail closed when an `apply_patch` payload yields no header path. | It matches the existing rule for an edit tool with no path, and an unreadable patch could touch anything. | Allow it (keeps the bypass for any unrecognized payload shape). |
| 2026-10-06 | Read `input`, then `patch`, then a raw string argument. | The patch argument's key is not documented for every Copilot surface. Reading the known candidates and failing closed otherwise keeps the gate safe whatever the shape. | Only `input` (blocks every other shape as uninspectable, which is safe but noisier). |
| 2026-10-06 | No change to the Claude matcher. | Claude Code has no patch-style built-in tool; its remaining gaps are already listed known limits. | Add speculative names. |
| 2026-10-06 | Leading whitespace is stripped from patch lines before the header check, and a trailing carriage return is stripped explicitly. | Indented and CRLF headers gate exactly like their plain LF form; the explicit strip states the intent even though the path strip already removes it. | Match headers only at column zero (an indented header would bypass the gate). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Copilot sends `apply_patch` arguments under a key not anticipated here, so every `apply_patch` is blocked as uninspectable. | The block message names the keys it read, so an operator can report the shape. The fail-closed choice is deliberate (Decision Log). The implementer checks the current Copilot hooks reference during implementation and records the documented shape, or its absence, in the Progress Log. |
| A patch header path that contains a trailing space is trimmed, so the gate checks a slightly different path than the host writes. | Trailing-space file names are already unusual. Gating the trimmed name errs toward the guarded location, because the seed and framework checks are prefix based. |
| Shared file `render_platform_surfaces.py` and seed 050 with other waves. | No sibling wave plan (A to E) names either file, so there is no ordering constraint. Re-check at Prepare. |
| Shared file `docs/architecture/threat-model.md` with wave A (`1zx02`, lock integrity), which lands first. | This change adds one row and rebases on A's threat-model edits. |
| Shared files inside wave D. | None of this change's files are shared with `1zxnu` or `1zxnv`; for wave-level consistency it is edited last (`1zxnu`, then `1zxnv`, then this change). |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
