# Tell Claude what to keep when it compacts a conversation

Change ID: `2136m-enh claude-compaction-guidance`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-18
Wave: 2136r agent-guidance-best-practices

## Rationale

The Claude Code best-practices guide recommends a compaction instruction in `CLAUDE.md`, for example "When compacting, always preserve the full list of modified files and any test commands", so critical context survives summarization.

Long Wavefoundry sessions compact routinely. The facts a wave session needs after compaction are:
- the open wave and its change ids;
- which edit gates are open;
- the files modified;
- the exact verification commands and their last results;
- the decisions still waiting on the operator.

Losing a gate state or a pending decision across compaction is the failure that matters. An open `seed_edit_allowed` gate left open is one example. Another is an approval inferred from a summary.

The only part of `CLAUDE.md` the framework writes mechanically is the `wave:root-bridge` region (`ROOT_BRIDGE_BLOCK`, `render_agent_surfaces.py:75-79`; `patch_root_bridge` at about 1969). That region holds `@AGENTS.md`, and the rest of `CLAUDE.md` is project-owned. `patch_root_bridge` already refreshes an existing bridge in place, so the instruction needs no new mechanism. Reach is Guru-gated: `render_agent_surfaces()` returns before `patch_root_bridge` when `docs/agents/guru.md` is absent (about 4845-4846, call at about 4896). So the line reaches Guru-enabled Claude targets, which is the standard install. Widening the bridge to non-Guru targets would change 1p5xc behaviour, and is out of scope. Claude Code re-reads the project-root `CLAUDE.md` after compaction (Claude Code memory docs), so the instruction is present when it matters.

## Requirements

1. `ROOT_BRIDGE_BLOCK` gains one line after `@AGENTS.md`, inside the markers, exactly: "When compacting, preserve the open wave and change ids, the operator's scoped authorizations and decisions still pending, the files modified, and the exact verification commands with their last results; a summary never records an approval the operator did not give. After resuming, recheck mutable state such as open gates and wave status with the tools instead of trusting the summary." The line contains no backslash, because the block is a `re.sub` replacement string, and does not contain the literal `@AGENTS.md`.
2. `@AGENTS.md` stays the bridge's first line and its only import.
3. An existing bridge is refreshed in place to the new block, as today. A legacy prose pointer is still replaced by the full block.
4. The seed 050 text that describes the root bridge names the added line.
5. Claude only. Other hosts' compaction does not read `CLAUDE.md`, and their entry files are out of scope.
6. Behaviour is the same on Windows, macOS, Linux and WSL2. The change is a renderer string through the existing platform-newline write path.

## Scope

**Problem statement:** Claude's compaction has no project instruction about what to preserve.

**In scope:**

- `.wavefoundry/framework/scripts/render_agent_surfaces.py` `ROOT_BRIDGE_BLOCK`.
- The bridge tests in `test_per_area_agents_context.py`: `test_replaces_prose_pointer_with_import`, `test_bridge_idempotent`, `test_root_claude_md_is_import_not_prose`, `test_no_import_outside_root_and_no_subdir_claude_md`. Plus `test_render_agent_surfaces.py` entry-path tests where affected.
- Seed 050's root-bridge text.
- This repo's re-rendered root `CLAUDE.md`.

**Out of scope:**

- Compaction guidance for other hosts.
- The project-owned sections of `CLAUDE.md`.

## Acceptance Criteria

- [x] AC-1: Rendering into a `CLAUDE.md` holding the pre-change bridge produces the new block, and a new assertion checks the rendered bridge region equals `ROOT_BRIDGE_BLOCK` byte for byte, on both the marker-replace and the legacy-pointer paths, so a backslash or group reference mangled by `re.sub` cannot pass. A second render changes nothing, and the import test still finds exactly one `@AGENTS.md` import, at the root only.
- [x] AC-2: Rendering into a `CLAUDE.md` holding the legacy prose pointer replaces it with the new block.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Extend `ROOT_BRIDGE_BLOCK`, and add the compaction-line assertion to the bridge tests (the existing ones pin only the import and markers).
- [x] Update seed 050's root-bridge text under `seed_edit_allowed`.
- [x] Re-render this repo's `CLAUDE.md`.
- [x] Run the touched test files, then the whole suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| renderer | implementer | none | Requirements 1 to 4 |

## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/tests/test_per_area_agents_context.py`, `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`

## Affected Architecture Docs

N/A: one line added inside an existing rendered region.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Upgraded Guru-enabled targets must get it. |
| AC-2 | required | Legacy targets must get it. |
| AC-3 | required | The bridge is pinned by tests. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-18 | Planned. The root bridge is the only mechanically rendered `CLAUDE.md` region; the auto-Guru block renders only when `docs/agents/guru.md` exists. | Guru investigation |
| 2026-10-18 | Readiness QA: the AC-1 assertion is region equality with `ROOT_BRIDGE_BLOCK` on both `re.sub` paths, not a keyword check. | 2136r readiness review |
| 2026-10-18 | Implemented under `framework_edit_allowed`: `ROOT_BRIDGE_BLOCK` gains the compaction line after `@AGENTS.md` (no backslash). Tests assert the rendered region equals `ROOT_BRIDGE_BLOCK` on the legacy-pointer path and on the new pre-change-bridge refresh test; the second-render check compares the bridge region only, because a second render of that minimal fixture also rewrites its auto-Guru region (pre-existing, same scoping as `test_bridge_idempotent`). Seed 050 bridge text names the line. Re-rendered `CLAUDE.md`. QA scratch mutant appending a backslash group reference failed three bridge tests. | test_per_area_agents_context 10 OK; delivery reviews |
| 2026-10-18 | Whole suite `--no-cache` after settled inputs: 11907 tests OK, fresh green receipt. Two earlier runs had no test failures but tripped the repository-change guard on concurrent edits (CHANGELOG, gardener stamps, and another session writing wave 2124l). | scratchpad suite-2136r-3.txt |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | -------- |
| 2026-10-18 | Put the line in the root bridge, and accept Guru-gated reach. | It is the only mechanically rendered `CLAUDE.md` region, and it refreshes in place. Both rendered regions are Guru-gated, so reach is the same as the auto-Guru block, but the bridge is the Claude entry point rather than a Guru topic. | (a) The auto-Guru block; same reach, off-topic. (b) Move `patch_root_bridge` above the Guru gate; changes 1p5xc for non-Guru targets. (c) A new rendered region; new mechanism. (d) Seed 050 prose only; agent-applied, so it drifts. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A target hand-edited inside the bridge markers. | The markers already say "do not edit", and the refresh already overwrites the region. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
