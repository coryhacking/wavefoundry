# Turn off Claude Code's automatic commit attribution in rendered settings

Change ID: `2136n-enh claude-commit-attribution-hook`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-18
Wave: 2136r agent-guidance-best-practices

## Rationale

Seed 020:21 says commit messages must not mention Claude, Claude Code or any AI tool, and must omit `Co-Authored-By` trailers. That rule is prose only. The host pushes the other way: Claude Code adds attribution to commits by default and tells the model to append a `Co-Authored-By: Claude …` trailer. In this repository's history, 24 of 470 commits carry such a trailer.

Claude Code has a native control for this. The `attribution` setting (installed 2.1.302; `includeCoAuthoredBy` is marked "Deprecated: Use attribution instead") accepts `attribution.commit: ""` to suppress automatic commit attribution. That addresses the cause at its source, with no new mechanism.

`render_claude_settings` (`render_platform_surfaces.py:1952-2039`) already merges framework-owned entries into `.claude/settings.json` and keeps everything else. One more framework-owned key fits that path.

A hook that inspects `git commit` commands was considered and dropped (plan review, 2026-10-18):
- it would reject a clean commit chained after a command that names `Claude.md`;
- it would still miss `-F` and editor messages;
- a bug in a fail-closed pre-tool hook blocks every shell call.

The prose rule stays. Enforcement is added later only if a need remains after this setting.

## Requirements

1. `render_claude_settings` writes `"attribution": {"commit": ""}` into `.claude/settings.json` when the file has no `attribution.commit` value.
2. An existing `attribution.commit` value, of any content, is left unchanged. Sibling keys under `attribution` (such as `pr`) are kept. Every other key keeps today's merge behaviour. If `attribution` exists but is not an object, the file is left unchanged for that key, matching the renderer's non-object policy for permissions (`test_valid_non_object_payload_leaves_file_untouched`); the AC-2 test covers it with one subTest.
3. A repeat render is byte-identical.
4. `attribution.pr` is not written: seed 020's rule covers commit messages only.
5. Seed 050's Claude settings text names the key and the reason in one sentence.
6. Seed 020:21 is unchanged.
7. Behaviour is the same on Windows, macOS, Linux and WSL2. The setting is host-level JSON written through the existing write path, and Claude Code reads it on every platform.

## Scope

**Problem statement:** Claude Code's default commit attribution contradicts the framework's commit-message rule.

**In scope:**

- `render_claude_settings`.
- Tests in `test_render_platform_surfaces.py`.
- Seed 050's Claude settings text.
- This repo's re-rendered `.claude/settings.json`.

**Out of scope:**

- A commit-inspecting hook.
- PR attribution.
- Other hosts' attribution settings.
- Rewording seed 020.

## Acceptance Criteria

- [x] AC-1: Rendering into a settings file with no `attribution` key adds `attribution.commit == ""`, and a second render is byte-identical.
- [x] AC-2: Rendering into a settings file whose `attribution` is `{"commit": "custom", "pr": "x"}` leaves both values unchanged.
- [x] AC-3: After re-render, a dogfood commit made through Claude Code in a fresh session in a fresh scratch repository with no `CLAUDE.md` or `AGENTS.md` carries no `Co-Authored-By` trailer. The Progress Log records the command, the resulting message, and whether the host's commit-attribution instruction was present in that session's context, so the result shows the setting, not prose, removed the trailer. The authority for the scratch commit is the operator's instruction to implement this wave. This is host behaviour, so a failure is reported as a finding against the setting, not worked around.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the key to `render_claude_settings`, plus the AC-1 and AC-2 tests.
- [x] Update seed 050 under `seed_edit_allowed`, and re-render this repo's settings.
- [x] Run the AC-3 dogfood check in a scratch repository.
- [x] Run the touched test files, then the whole suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| settings | implementer | none | Requirements 1 to 5 |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`, `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`, `.claude/settings.json`

## Affected Architecture Docs

N/A: one framework-owned settings key through the existing merge.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The change itself. |
| AC-2 | required | Operator customizations must survive. |
| AC-3 | important | Confirms the host honours the setting. |
| AC-4 | required | Settings rendering is pinned. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-18 | Planned as a commit-inspecting hook. | Guru investigation |
| 2026-10-18 | Replanned around the native `attribution.commit` setting, after plan review. The review found: false positives on chained commands; misses on `-F` and editor messages; fail-closed risk to every shell call; and 11 legitimate post-rule commits naming Claude host surfaces. The `attribution` key was confirmed present in the installed 2.1.302 binary. | Operator plan review; Fable plan review; `git log` counts |
| 2026-10-18 | Readiness red-team: a non-object `attribution` leaves the file unchanged for that key (Requirement 2, AC-2 subTest). | 2136r readiness red-team primer |
| 2026-10-18 | Readiness QA: AC-3 runs in a scratch repository with no framework prose and records whether the host attribution instruction was present, so it can fail on an ignored key. | 2136r readiness review |
| 2026-10-18 | Implemented under `framework_edit_allowed`: `render_claude_settings` sets `attribution.commit` to empty only when `attribution` is absent or an object without `commit`; non-object and existing values are untouched. Tests cover AC-1 and AC-2 (three subTests). Seed 050 settings text updated, then tightened after delivery docs-contract review to name the sibling-key and non-object cases. AC-3 dogfood (authority: the operator's instruction to implement this wave): two fresh scratch repositories with no CLAUDE.md or AGENTS.md, each committed through a fresh `claude -p` session (Claude Code 2.1.302). With `.claude/settings.json` `attribution.commit` empty: message `Add hello.txt`, no trailer, and the session reported no commit-attribution instruction in its context. Control without the setting: the same prompt produced `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and the session reported the instruction present. The live coordinator session also lost its commit-attribution instruction right after this repository's settings were re-rendered. | scratchpad ac3/with.out, ac3/without.out; test_render_platform_surfaces 149 OK |
| 2026-10-18 | Whole suite `--no-cache` after settled inputs: 11907 tests OK, fresh green receipt. Two earlier runs had no test failures but tripped the repository-change guard on concurrent edits (CHANGELOG, gardener stamps, and another session writing wave 2124l). | scratchpad suite-2136r-3.txt |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | -------- |
| 2026-10-18 | Use the native `attribution.commit: ""` setting, and add no hook. | It removes the cause with no new mechanism. | A pre-tool hook matching `git commit` text; false positives, misses, and fail-closed risk. |
| 2026-10-18 | Set the key only when absent. | `.claude/settings.json` is merged, and an operator's explicit value is a customization. | Always overwrite; overrides operator intent. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A future Claude Code renames or drops the key. | AC-3 dogfood check; the prose rule still applies. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
