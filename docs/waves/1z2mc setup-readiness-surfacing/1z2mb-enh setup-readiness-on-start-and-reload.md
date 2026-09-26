# Surface Setup Readiness to the Agent on MCP Start and Reload

Change ID: `1z2mb-enh setup-readiness-on-start-and-reload`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-26
Wave: 1z2mc setup-readiness-surfacing

## Rationale

The MCP server already runs the `wf setup --check` assessment: `server.py` `_assess_startup` at launch, and `ImplHandler.assess_setup` on every index-monitor tick (cached by `setup_readiness.assessment_signature`). But the agent rarely sees the result. A non-ready result goes to stderr, which most hosts do not show the agent, and to `index_health().data.setup_readiness`, which the agent must think to call. After `wf_reload_mcp`, the rebuilt handler does not assess until the monitor's first tick, and the reload response carries no readiness result. The operator hit this on another machine: after a reload they had to ask the agent by hand to run the check. The Claude Code session-start hook covers only session start, and only in Claude Code.

## Requirements

1. **Reuse the startup assessment; assess on reload.** `ImplHandler.__init__` starts with the runner's launch result and no second probe runs. The seeding already exists: `server.py` `_record_runner_identity`, which `build_server` calls before the handler is built, assigns `server_impl._SETUP_STARTUP_RESULT` and `_SETUP_STARTUP_ROOT` (the root from `repo_root.discover_root`, always resolved). This change adds no second seed; it pins the existing one with a test. `perform_mcp_reload` calls `new_handler.assess_setup()` (not forced) after building the new handler, so a reload assesses at once. No thread is added to `ImplHandler.__init__`. A reload performed by a runner that predates this change starts from the runner's launch-time result, which may be out of date, until the index monitor's next tick reassesses.
2. **Tell the agent through tool responses, only when the operator must act.** A new `setup` wrapper, the last entry in the `MIDDLEWARE` chain, adds one `setup_not_ready` diagnostic to a tool's dict response when the handler's cached assessment (read only, never computed by the wrapper) is not `ready` and carries at least one action. That covers `action_required` and an `indeterminate` result that still carries an action, such as the restart action after an upgrade (`loaded_code_stale`); an action-less `indeterminate` (index publication in progress, probe timeout, changed inputs) never produces it. The diagnostic names the reasons and the recommended command (`setup_readiness.format_command`), is bounded in length, and says to ask the operator before running anything. It appears once per distinct result per handler, tracked in a new handler attribute `_setup_agent_notice_key` (never the stderr notice state `_setup_notice_signature`); a new handler (after reload) or a changed result shows it again. The wrapper skips runner-registered tools (`mcp_tool_roster.RUNNER_TOOLS`; the runner's `_RELOAD_SURVIVOR_TOOLS` is not importable from `server_impl`), coroutine functions, and `index_health` (which already returns the result); it carries an idempotence marker so a reload never nests it; it reads handler attributes with `getattr` defaults, copies the envelope before adding, and never raises or blocks a call.
3. **Include readiness in the reload response.** `perform_mcp_reload` adds that assessment as `setup_readiness` to the payload, plus a `setup_not_ready` diagnostic under the same rule as Requirement 2, and records `_setup_agent_notice_key` (computed with `server_impl._setup_notice_key`, set tolerantly) so the same result is not repeated on the next tool call. The registered `wf_reload_mcp` description lists the new field. Because `server.py` is the runner that a reload does not replace, the reload assessment and Requirement 3 take effect after one host restart; Requirement 2 is reloaded code and takes effect on the reload itself.
4. **Docs.** `docs/specs/mcp-tool-surface.md` (setup-readiness notices and `wf_reload_mcp`), the wrapper-order statements in `docs/architecture/current-state.md`, `docs/architecture/layering-rules.md` and `docs/contributing/build-and-verification.md`, and a `CHANGELOG.md` `[Unreleased]` Added bullet. The ADR `1ye5y` is a historical record and is left unchanged.

## Scope

**Problem statement:** the server knows setup needs attention after a start or reload, but the agent is not told unless it asks.

**In scope:**

- a test for the existing startup seeding, the reload assessment and payload field, the response diagnostic wrapper, tests and docs.

**Out of scope:**

- running setup automatically (never; the agent asks the operator);
- other hosts' session-start hooks;
- changing what the assessment checks.

## Acceptance Criteria

- [x] AC-1: a handler built by the runner starts with the runner's launch assessment and no second probe; `perform_mcp_reload` assesses the new handler and returns `setup_readiness`, with a `setup_not_ready` diagnostic when the result carries an action, and the next wrapped tool call does not repeat it.
- [x] AC-2: with a cached result that carries an action (`action_required`, or `indeterminate` with a restart action), the first wrapped tool response carries one `setup_not_ready` diagnostic naming the reasons and the recommended command; a second call with the same result carries none; a changed result or a new handler carries it again; `ready` and an action-less `indeterminate` (including index publication in progress) carry none.
- [x] AC-3: the wrapper skips `wf_reload_mcp`, coroutine functions and `index_health`, is applied once across a reload, tolerates a handler without setup attributes, and never breaks a tool call.
- [x] AC-4: The change's own tests pass and the documents this change edits validate.

## Tasks

- [x] Pin the existing startup seeding with a test; assess and report in `perform_mcp_reload`; update the `wf_reload_mcp` description.
- [x] `setup` middleware wrapper and its `MIDDLEWARE` entry; update the middleware label pins in `test_mcp_tool_registry.py`.
- [x] Tests for AC-1 to AC-3; docs and changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Surfacing | implementer | readiness | Single write owner; reads through the MCP code tools |
| Review | combined reviewer | Surfacing | One combined reviewer |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/server.py`, `.wavefoundry/framework/scripts/tests/test_setup_readiness_integration.py`, `.wavefoundry/framework/scripts/tests/test_mcp_tool_registry.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`, `docs/specs/mcp-tool-surface.md`, `docs/architecture/current-state.md`, `docs/architecture/layering-rules.md`, `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/layering-rules.md` state the wrapper chain and its order; a fourth, outermost wrapper changes both.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | A start or reload must know setup state without waiting for the monitor |
| AC-2 | required | The operator's reported problem: the agent was not told |
| AC-3 | required | The wrapper must not break the runner's async tool or nest across reloads |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-26 | Full suite found one consumer this change affects: `test_upgrade_reload_runner` asserted the post-upgrade reload returns no diagnostic codes, and its scratch repo is not set up, so the reload now correctly adds `setup_not_ready`. The test now ignores that one advisory code and still fails on `handler_not_ready`. Reviewer note (b) also fixed: a command's trailing period is stripped, so the restart notice no longer reads "host.." | `test_upgrade_reload_runner`, `test_setup_readiness_integration` |
| 2026-09-26 | Delivery review (one combined reviewer, MCP code tools): architecture and docs-contract approve; code and QA blocked on B1, where the length bound cut from the end, so a long list of reasons (7 plausible post-upgrade reasons) dropped the command and the ask-first text. Repaired: only the reasons are cut, and the command and instruction are always kept. N1: the notice key is now recorded after the diagnostic is built, so a failed build does not consume the result. N2: the reload builds the diagnostic inside the guarded block. N3 and N6: the spec's `wf_reload_mcp` bullet now points "above" and says an old runner's reload starts from the launch-time result. N7: the reload test now calls a wrapped tool afterwards, with a positive control. New tests for B1 and N1; the original truncation and key-first mutants each fail one. N4 (a torn tree reports `setup_readiness_unavailable` on each reload) and N5 (the reload assessment can block the loop about 2 s) accepted as is | `test_setup_readiness_integration`, `test_server_tools.SetupReadinessOnStartAndReloadTests`, scratch-tree mutants |
| 2026-09-26 | Implementation found the startup seeding already present in `_record_runner_identity` (the plan and readiness review had missed it). A duplicate seed added to `build_server` was removed; the start test uses the resolved root that `discover_root` returns in production. Mutants: removing the existing seed, the reload assessment, the action predicate, once-per-result or the skips each fail a test | `test_server_tools`, `test_setup_readiness_integration`, scratch-tree mutants |
| 2026-09-26 | Readiness round 2: B1, B2, B4 and D1 resolved; red-team R1 (an `action_required`-only predicate hides the post-upgrade restart, which assesses `indeterminate` with a restart action) fixed by the reviewer's proposed predicate; N1 (`_RELOAD_SURVIVOR_TOOLS` not importable) and N3 (reload tests file) folded in | Readiness review |
| 2026-09-26 | Readiness review found four build-changing defects (B1 wrapper would wrap the async runner tool and nest on reload; B2 notice state collided with the stderr notice; B3 transient `indeterminate` would notify during every index build; B4 a constructor thread would run probes in every test) and one docs gap (D1 wrapper-order statements); plan revised to the reviewer's simpler alternative | Readiness review |
| 2026-09-26 | Planned at the operator's request after they had to ask for a manual check following a reload on another machine. Code facts checked with the MCP tools: `_assess_startup` prints non-ready results to stderr only; `ImplHandler.assess_setup` runs on the monitor tick; `perform_mcp_reload` lives in the runner and builds its payload from `version_payload`; `MIDDLEWARE` holds cost, lock and guard | `code_read`, `code_keyword` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-26 | Surface through a response diagnostic, once per distinct result per handler | Reaches the agent on every host through responses it already reads, without noise on every call | Every response while not ready; stderr only; a new tool |
| 2026-09-26 | Seed the runner's startup result and assess from the reload instead of a thread in `ImplHandler.__init__` (readiness B4 and alternative) | A constructor thread would run real probes in every test that builds a handler and race captured stderr; the runner already assessed at launch | A background thread per handler |
| 2026-09-26 | Notify when the result carries an action, never for an action-less `indeterminate` (readiness B3, round-2 R1) | An in-progress index build yields an action-less `indeterminate`, so it stays quiet; the post-upgrade restart yields `indeterminate` with a restart action, which the operator must see | Notify only on `action_required` (hides the post-upgrade restart); notify on any non-ready result |
| 2026-09-26 | Keep the diagnostic advisory, never running setup | Setup changes the environment and needs the operator's consent | Auto-run setup |

## Risks

| Risk | Mitigation |
| --- | --- |
| Tests pin the middleware label list | Update the `test_mcp_tool_registry.py` pins; other wrapper-order tests tolerate a new outermost label |
| A provenance test derives diagnostic codes from functions that rebind `tool.fn` | The wrapper adds the diagnostic to the envelope and returns the result, never a helper-built response |
| The reload assessment races the monitor | `assess_setup` serializes under `_setup_assessment_lock` and caches by signature |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
