# Correct shipped guidance: README shortcut names and the Claude edit-gate limit

Change ID: `2134x-doc shipped-guidance-vocabulary-and-edit-gate-corrections`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-19
Wave: `2136y distribution-test-portability-round-2`

## Rationale

Two shipped texts are wrong or distribution-hostile (Waveforge X6, X7). The framework README `.wavefoundry/README.md`, packaged as-is by `build_pack.py`, names default shortcuts ("`Plan change` or `Prepare wave`" on line 145, "Review wave" near line 202), so `test_wf_cli`'s retired-name check flags it on a renamed tree. Seed `050-agent-entry-surface-bootstrap.prompt.md` (the "Known limits of the edit gates" list, around line 383) says the Claude matcher names only the built-in edit tools, so MCP writes never reach the pre-edit hook; the renderer now installs the Claude pre-edit hook with no matcher (`render_platform_surfaces.CLAUDE_HOOKS`), so it receives every tool call, and the hook gates an unrecognised tool only when its input carries a path field it knows (`file_path`, `notebook_path`, `path`).

## Product Intent

Readers of the framework README on any distribution see no shortcut names that the distribution renamed, and the seed states the Claude edit gate's real limit. Boundaries: text only. AC-1 and AC-2 test the outcome.

## Requirements

1. `.wavefoundry/README.md` describes shortcuts without naming any lifecycle shortcut phrase (for example "When you type a lifecycle shortcut (listed in `docs/prompts/index.md`)"), at every place `test_wf_cli`'s retired-name check flagged.
2. Seed 050's MCP edit-gate bullet says the Claude pre-edit hook receives every tool call, exempts the Wavefoundry read-tier MCP tools, blocks another tool only when its input names a gated path in a path field it recognises (for example `file_path`, `notebook_path`, `path`, `tool_info.file_path`), and lets other calls through with a warning; the bullet does not enumerate the fields as complete. The shell bullet stays as it is.
3. No other seed or doc changes (the investigation found `docs/architecture/threat-model.md` and seed 160 already accurate).

## Scope

**Problem statement:** Shipped text names default shortcuts and misstates the Claude gate.

**In scope:**

- `.wavefoundry/README.md`, seed 050 (seed edit gate), rendered copies if the seed renders into project docs, one CHANGELOG bullet.

**Out of scope:**

- Rendering the README through the profile.
- Gating shell or other MCP writes.

**Platform behaviour:** documentation only; describes behaviour that is the same on every platform.

## Acceptance Criteria

- [x] AC-1: In a scratch Set/Wave copy, `test_wf_cli.NoLiveReferenceToRetiredWrapperTests` reports no offender in `.wavefoundry/README.md`; the README still validates. Oracle: the scratch run.
- [x] AC-2: Seed 050's edit-gate bullet matches `render_platform_surfaces.CLAUDE_HOOKS` and the rendered pre-edit hook (`NON_EDIT_TOOL_NAMES`, `FILE_PATH_KEYS`). Oracle: review against the code, recorded in the Progress Log.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Reword the README shortcut mentions.
- [x] Update the seed 050 bullet (open and close `seed_edit_allowed`).
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| docs | technical-writer | none | README and seed |

## Serialization Points

- `.wavefoundry/README.md`, `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`

## Affected Architecture Docs

N/A: text corrections.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required | Unblocks the retired-name check. |
| AC-2 | important | Accuracy of a security-relevant limit. |
| AC-3 | required | Standard verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned. | Waveforge X6 and X7; investigation of `CLAUDE_HOOKS`, `.claude/settings.json`, `.claude/hooks/pre-edit.py`. |
| 2026-10-19 | Readiness red-team primer: requirement 2 now names the read-tier exemption and does not overclaim the recognised path fields. | Red-team primer report. |
| 2026-10-19 | Implemented. `.wavefoundry/README.md` line 145 now says "When you type a lifecycle shortcut (listed in `docs/prompts/index.md`)" and line 202 "the distinct review phase (see the review shortcut in `docs/prompts/index.md`)". Seed 050 bullet rewritten (seed gate opened and closed around the edit); no rendered copy of the bullet exists, so no re-render. AC-2 code review: `render_platform_surfaces.CLAUDE_HOOKS` registers `pre-edit` with `matcher: None`; the rendered `.claude/hooks/pre-edit.py` returns early for `NON_EDIT_TOOL_NAMES` (`Read`, `Bash`) and `CORE_READ_TOOLS` (Wavefoundry read-tier, only while its contract hash matches), gates other non-edit tools only through `FILE_PATH_KEYS` (`tool_input.file_path`, `tool_input.notebook_path`, `tool_input.path`, `tool_info.file_path`, `file_path`, `path`) and otherwise prints a COMPATIBILITY warning and allows; the bullet matches. CHANGELOG bullet under Fixed. AC-1: in both Set/Wave scratch copies the retired-name scan reports no `.wavefoundry/README.md` offender; with the HEAD README restored it reports lines 145 (`Plan change`, `Prepare wave`) and 202 (`Review wave`). The root `README.md` and `AGENTS.md` offenders there are this repository's own docs, out of scope. test_wf_cli 54 OK on the default profile and under both profile runs. | Scratch logs under `/private/tmp/claude-502/-Users-coryhacking-Developer-wavefoundry/64d2b992-b50d-423e-985d-22b0c59dd1ac/scratchpad/2134w`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Reword rather than render. | The README is a static packaged doc; two phrases do not justify a rendering path. | Render the README through the profile. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The README loses useful examples. | Point to the shortcut index instead. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
