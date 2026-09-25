# Session-Start Setup Readiness Hook

Change ID: `1yzcx-enh session-start-setup-readiness-hook`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-09-24
Wave: `1yzcz setup-readiness-at-session-start`

## Rationale

After a teammate commits a framework upgrade and a developer pulls it, the local runtime (tool environment, dependencies, launch surfaces, indexes) can be out of date until `wf setup` runs. Today every detector lives inside a running MCP server: the startup assessment and background monitor print to stderr, which agents may never see (`AGENTS.md`, "Check readiness after Git changes"). Nothing reaches the agent's context at the start of a session.

The operator decided (2026-09-24) to surface setup readiness at agent session start and have the agent report and ask, never run setup automatically. Git hooks stay retired (wave `1p88t`; excluded again by change `1y3hc` in wave `1y3og`), and the `1y3hc` rule that nothing consuming the readiness check may run setup automatically is kept.

Brief: render a Claude Code `SessionStart` hook that runs the same read-only assessment as `wf setup --check` and, only when the result is not ready, adds a short block to the agent's context naming the reasons and the recommended command, with an instruction to report it to the operator and ask before running it.

## Requirements

1. **Registration.** A new Claude hook `wf-session-start` (namespaced so it never collides with an operator's own `session-start` hook) is added to the `CLAUDE_HOOKS` registry in `render_platform_surfaces.py` with event `SessionStart`, matcher `startup|resume` and a new optional registry key `timeout` (15). `render_claude_settings` emits `timeout` on the command object only when the registry entry carries it, so existing entries stay byte-stable. The body is rendered as `.claude/hooks/wf-session-start.py` with the same owner-bound `CLAUDE_PROJECT_DIR` launcher as the existing hooks; simulate-hooks parity derives from the registry as today. It does not fire on `clear` or `compact`.
2. **Pre-activation body.** The body is composed WITHOUT `HOOK_BOOTSTRAP` and without the hook helpers, through a new compose variant: it sets `sys.dont_write_bytecode = True`, inserts the framework scripts directory on `sys.path`, configures UTF-8 stdio through `cli_stdio`, and never calls `venv_bootstrap.activate_tool_venv` (the module is imported by `setup_readiness` but its activation is never invoked), so no tool-environment `.pth` file executes and no framework bytecode is written, matching the `wf setup --check` contract (wave `1y3og`) and `docs/architecture/layering-rules.md` ("metadata inspection must not activate the tool environment").
3. **Assessment.** The body calls `setup_readiness.assess_setup(root)` in-process with the project root from `CLAUDE_PROJECT_DIR`. When the only reason is `inputs_changed` (state changed while assessing, for example the MCP server starting concurrently), it reassesses once. It never runs setup, installs dependencies, rebuilds, resumes recovery or writes the stamp.
4. **Output contract** (stdout, which Claude Code adds to the session context on exit 0):
   - `ready`: no output.
   - `action_required`: a fixed header line identifying the block as Wavefoundry setup-readiness tool output; one line per reason (`code: message`), at most 8 reasons; each recommended action rendered with the platform quoting `format_text` uses (extracted into a shared `setup_readiness` helper that `format_text` also calls, so its output is unchanged); for a `setup` action a note that setup ends by asking for an agent-host restart; for a `resume` action a note to stop Wavefoundry hosts and run it from an external terminal; for a `restart` action "restart the agent host"; and the instruction: report this to the operator and ask before running any command.
   - `indeterminate`: one line naming the first reason and `wf setup --check --json` as the command to run by hand.
   - Every emitted line has control characters and newlines replaced and is capped at 240 characters.
5. **Never blocks.** The rendered body uses syntax that parses on older Python 3 interpreters (no `match` statements, no runtime `X | Y` unions), so the guard below can fire there. The whole body runs under `except BaseException` (including `SystemExit`, and an import failure on a `python3` older than 3.11); on failure it prints at most one short line naming the failure and the manual `wf setup --check` command, and always exits 0.
6. **Canonical guidance.** Seed 050 section "Check readiness after Git changes" and the `AGENTS.md` copy gain one sentence: where the host supports it, a session-start hook runs the same read-only check and reports it; at session start no task authorization exists yet, so the agent reports and asks the operator before running setup, and the existing task-authorization rule applies after that. The existing sentence "No Git hooks are installed by this guidance." stays. A test asserts the section is byte-identical in seed 050 and `AGENTS.md`, from the heading through the sentence "No Git hooks are installed by this guidance."
7. **Hook inventories.** Seed 050's Claude Code hook and generated-entrypoint inventory and seed 160's hook-body verification checklist (hand-mirrored in `docs/prompts/upgrade-wavefoundry.prompt.md`, since `wf render-surfaces` does not propagate seed prose to existing prompts) list `wf-session-start` and the existing `session-capture` and `context-efficiency-project` Stop hooks they currently omit. `docs/agents/platform-mapping.md` records the session-start hook in the Claude Code launcher row; `docs/architecture/layering-rules.md` names the hook as a pre-activation readiness consumer; `docs/specs/mcp-tool-surface.md` "Setup readiness notices" names it as a consumer.
8. **Other hosts** are out of scope: no session-start hook is emitted for Cursor, Copilot, Windsurf, Codex, Junie, Air, Warp or Antigravity.
9. **Changelog**: an Added bullet with an operator note that the committed `.claude/settings.json` gains a `SessionStart` entry (operator hook entries are preserved), that nothing runs setup automatically, and that no git hooks are installed. The seed 050 sentence reaches existing targets' `AGENTS.md` through the upgrade reconciliation pass, not a re-render.

## Scope

**Problem statement:** setup-readiness results never reach the agent's context at session start, so a stale checkout after a pull is noticed late or not at all.

**In scope:**

- The `wf-session-start` Claude hook: registry entry with `timeout`, pre-activation compose variant and body, settings registration, simulate parity.
- Output sanitizing and the shared quoting helper in `setup_readiness.py`.
- Tests through the real renderer and by executing the rendered hook body against fixtures.
- Seed 050, seed 160, the prompt mirror, `AGENTS.md`, `platform-mapping.md`, `layering-rules.md`, `mcp-tool-surface.md`, changelog.

**Out of scope:**

- Any git hook or `core.hooksPath` handling.
- Running setup automatically, from the hook or the agent.
- Session-start hooks for other hosts (their event contracts are unverified here).
- Fingerprint changes (change `1yzcy-enh setup-fingerprint-completeness`).

## Acceptance Criteria

- [x] AC-1: `render_platform_surfaces --platform claude` renders `.claude/hooks/wf-session-start.py` and a `SessionStart` entry with matcher `startup|resume` and `timeout` 15 on the command object; existing hook entries are byte-unchanged; the simulate-hooks parity test covers the new hook; re-rendering is byte-stable; the rendered body contains no `venv_bootstrap` activation.
- [x] AC-2: Executing the rendered hook body in a subprocess: against a subprocess-ready fixture (the one change `1yzcy` builds) it prints nothing and exits 0; against an `action_required` fixture it prints the header, the reason codes, the recommended command and the report-and-ask instruction and exits 0; against a `recovery_pending` fixture (continuation recorded with the hook process's exact `sys.executable`) it prints the resume note instead of the setup note; against an `indeterminate` fixture it prints one line with the manual check command and exits 0; when the first assessment reports only `inputs_changed` it reassesses once.
- [x] AC-3: Failure paths exit 0 with at most one line: an assessment that raises, and missing framework scripts. Separately, a tool environment whose `pyvenv.cfg` Python version differs from the running interpreter exits 0 (never 2) and is reported through the `action_required` block with reason `environment_incompatible`. A mutant that catches only `Exception`, or that restores the venv bootstrap, fails a test.
- [x] AC-4: The hook performs no setup action and no activation: a poison `.pth` marker in the fixture tool environment is never created; no `__pycache__` appears; it never invokes `setup_wavefoundry`, `setup_index` or a subprocess other than the assessment's own bounded database probe; and every fixture file is byte-identical afterwards except SQLite WAL/SHM coordination files.
- [x] AC-5: A reason message containing a newline, control characters and an injected instruction is emitted as a single sanitized line of at most 240 characters, and more than 8 reasons are truncated to 8.
- [x] AC-6: Seed 050 and `AGENTS.md` carry the new sentence and the byte-identity test passes; seed 160, the prompt mirror, `platform-mapping.md`, `layering-rules.md`, `mcp-tool-surface.md` and the changelog are updated; the documents this change authors or edits validate, and the change's suites and every test it adds pass.

## Tasks

- [x] Registry `timeout` key and settings emission; pre-activation compose variant; hook body with retry, sanitizing and `BaseException` guard.
- [x] Extract the quoting helper in `setup_readiness.py` with `format_text` output unchanged.
- [x] Renderer, parity and executed-hook tests for AC-1 to AC-5, with mutants recorded in wave evidence.
- [x] Seed 050 and seed 160 under the `seed_edit_allowed` gate; mirror in `AGENTS.md` and the upgrade prompt; the byte-identity test; the other docs and the changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Hook, renderer and tests | implementer | change `1yzcy` | Single write owner; reuses the subprocess-ready fixture |
| Seeds and docs | implementer | hook | Seed gate opened and closed around the seed edits |
| Verification | code, qa, security, architecture, release, docs-contract reviewers | implementation | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/agents/platform-mapping.md`, `docs/architecture/layering-rules.md`, `docs/specs/mcp-tool-surface.md`
- `.claude/settings.json`, `.claude/hooks/`

## Affected Architecture Docs

`docs/architecture/layering-rules.md` (the hook is a pre-activation readiness consumer) and `docs/agents/platform-mapping.md`. The hook is an optional host surface (tier 3) over the canonical `AGENTS.md` guidance and adds no new boundary.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Rendering is the delivery surface |
| AC-2 | required | The output contract is the feature |
| AC-3 | required | A session must never be blocked by the hook |
| AC-4 | required | Operator decision: report and ask; `1y3og` pre-activation contract |
| AC-5 | required | Hook output enters agent context |
| AC-6 | required | Canonical guidance and validation |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-24 | Planned from operator decision: session-start report-and-ask, no git hooks, no automatic setup | Operator request |
| 2026-09-24 | Readiness round 1: red-team, code and architecture blocked on the standard hook bootstrap activating the tool environment (runs `.pth` files, and `activate_tool_venv` can `sys.exit(2)` past an `except Exception`); one bounded repair applied (pre-activation compose variant, `BaseException` guard, `timeout` on the command object, inputs-changed retry, action-specific notes, output sanitizing, seed/prompt/spec/layering docs census, AGENTS parity test) | readiness-review.md |
| 2026-09-24 | Implemented: `session-start` registry entry with `timeout`, `compose_preactivation_script`, `claude_session_start_source`, `format_command` extracted in `setup_readiness.py` (`format_text` output unchanged); rendered `.claude/settings.json` and `.claude/hooks/wf-session-start.py` (diff limited to the new entry and simulate line). Seeds 050 and 160 edited under the seed gate; `AGENTS.md` mirrored with a byte-identity test. `docs/prompts/upgrade-wavefoundry.prompt.md` does not carry seed 160's hook checklist, so no mirror edit was needed. The launcher's own missing-`CLAUDE_PROJECT_DIR` exit is shared with every Claude hook and precedes the body. Tests in `test_session_start_hook.py` (render, parity, executed launcher against the subprocess-ready fixture, in-process failure/retry/sanitize); 12 hook mutants in evidence/mutants.py all killed. Hook runs silent in this repository in about 0.16 s and writes no bytecode. Gapfill: code reads by shell over anchors verified during readiness | evidence/mutants.py |
| 2026-09-24 | Delivery repair DEL-HOOK-NAME-COLLISION (red-team RT-DEL-1): the hook is renamed `wf-session-start` so the render never deletes or overwrites an operator's own `session-start` hook; regression test renders over operator `session-start{,.sh,.py,.cmd}` files and entries and requires them unchanged (fails against the old name). Also SEC-DEL-1/RT-DEL-4: an overlong recommended command is replaced by a pointer to `wf setup --check` instead of being cut. Seeds 050/160 updated under the seed gate; this repository's never-shipped old entry and body removed by hand before re-render | tests/test_session_start_hook.py |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-24 | Agent-host session-start hook, report and ask | Visible in agent context, catches any kind of checkout change, keeps git hooks retired and the `1y3hc` no-auto-setup rule | Git hook running `wf setup` (rejected: network, slow, writes tracked files mid-checkout, lock contention); check-only git hook (deferred) |
| 2026-09-24 | Claude Code only | Its `SessionStart` context contract is known; other hosts' session-start contracts are unverified | Emit for Copilot/Cursor now (rejected: unverified schema) |
| 2026-09-24 | Compose the body without the venv bootstrap | The readiness check must run before activation; activation can exit 2 and runs `.pth` code | Reuse `compose_script` (rejected by readiness) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Hook output inflates context every session | Silent when ready; bounded, capped block otherwise |
| Concurrent MCP startup makes the first assessment `inputs_changed` | One reassessment |
| Reason text carries unexpected strings into agent context | Sanitized single lines, 240-character cap, 8-reason cap, fixed tool-output header |
| Hook failure blocks or slows session start | `BaseException` guard, exit 0, 15 s timeout, assessment's own 2 s database bound |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
