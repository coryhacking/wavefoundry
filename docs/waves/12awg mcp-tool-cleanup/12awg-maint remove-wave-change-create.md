# Remove wave_change_create

Change ID: `12awg-maint remove-wave-change-create`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-01
Wave: `12awg mcp-tool-cleanup`

## Rationale

`wave_change_create` was deprecated in `12aj7-enh mcp-layer-polish` (wave `12ahv`) in favor of the ten kind-specific `wave_new_<kind>` tools. Per SEP-986 deprecation policy, one migration window was required before removal. That window has elapsed: no seeds, prompts, or documented callers reference `wave_change_create` as a primary creation path (confirmed during 12aj7 review). Removing the tool eliminates the redundant generic dispatcher from every tool listing, reducing agent confusion about which tool to use.

## Requirements

1. Remove the `wave_change_create` tool registration and its handler from `server.py`.
2. Remove the `[DEPRECATED — use wave_new_<kind> instead]` docstring prefix that was added in 12aj7 (it goes with the tool).
3. Remove the `deprecated_tool` diagnostic injection logic that was added in 12aj7.
4. Update `test_all_tools_registered` in `test_server_tools.py` to remove `wave_change_create` from the expected tool list.
5. Update `AGENTS.md` to remove the deprecation note for `wave_change_create` and confirm the tool is gone.
6. Update `docs/architecture/current-state.md` if it lists `wave_change_create` by name.

## Scope

**Problem statement:** `wave_change_create` was deprecated but not removed. It still appears in every tool listing alongside the ten `wave_new_*` tools, creating an unnecessary ambiguity for agents choosing a creation path.

**In scope:**

- Removing the `wave_change_create` tool from `server.py` (handler + registration)
- Removing the 12aj7-era deprecation shim (docstring prefix + diagnostic injection)
- Updating `test_all_tools_registered` and any tests that call `wave_change_create` directly
- Updating `AGENTS.md` and `current-state.md` references

**Out of scope:**

- Changing any `wave_new_<kind>` tool behavior
- Updating seeds or prompts — confirmed none reference `wave_change_create` as primary (AC-13 in 12aj7)
- Any other `wave_change_create` follow-ons not related to the tool removal itself

## Acceptance Criteria

- AC-1: `wave_change_create` is not registered in the MCP server — it does not appear in `test_all_tools_registered`.
- AC-2: Calling the old tool name via MCP returns a standard "tool not found" error (no special handling needed; FastMCP handles unregistered tools).
- AC-3: No deprecation diagnostic injection code remains in `server.py`.
- AC-4: `test_all_tools_registered` passes with `wave_change_create` absent.
- AC-5: All existing tests that exercised `wave_change_create` are removed or updated.
- AC-6: `AGENTS.md` no longer references `wave_change_create` as deprecated — the tool is simply gone.
- AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes.
- AC-8: `.wavefoundry/bin/docs-lint` is clean.

## Tasks

- In `server.py`: locate the `wave_change_create` tool handler and registration; delete both, along with the deprecated-tool diagnostic injection.
- In `test_server_tools.py`: remove `wave_change_create` from `test_all_tools_registered`; remove `WaveChangeCreateDeprecationTests` class (or repurpose any setup fixtures used elsewhere).
- In `AGENTS.md`: remove the deprecation note; confirm `wave_change_create` is no longer listed.
- In `docs/architecture/current-state.md`: remove any mention of `wave_change_create` as deprecated.
- Run `python3 .wavefoundry/framework/scripts/run_tests.py` and confirm all pass.
- Run `.wavefoundry/bin/docs-lint` and confirm clean.

## Agent Execution Graph

| Workstream    | Owner       | Depends On | Notes                                              |
| ------------- | ----------- | ---------- | -------------------------------------------------- |
| server-remove | implementer | —          | Delete handler, registration, and deprecation shim |
| tests         | implementer | server-remove | Update test_all_tools_registered; remove deprecation tests |
| docs          | implementer | server-remove | AGENTS.md and current-state.md updates             |

## Serialization Points

- `server.py` edit should land before tests are updated (tests reference the tool list).

## Affected Architecture Docs

- `docs/architecture/current-state.md` — remove `wave_change_create` from the deprecated-tools list if present.
- No other architecture doc changes expected; this is a pure removal with no new behavior or boundaries.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority       | Rationale |
| ---- | -------------- | --------- |
| AC-1 | required       | Primary deliverable — tool must be absent from the MCP listing |
| AC-2 | nice-to-have   | FastMCP handles unregistered tool calls gracefully; no special handling needed |
| AC-3 | required       | Deprecation shim removal is part of the cleanup; leaving it would be dead code |
| AC-4 | required       | Test suite must not reference a tool that no longer exists |
| AC-5 | required       | Test hygiene — deprecation test class must be removed with the tool |
| AC-6 | required       | AGENTS.md is the primary agent reference; stale deprecation notes mislead |
| AC-7 | required       | Tests are the verification gate |
| AC-8 | required       | docs-lint is the docs verification gate |

## Progress Log

| Date       | Update         | Evidence |
| ---------- | -------------- | -------- |
| 2026-05-01 | Change doc authored. Migration window from 12aj7 confirmed elapsed; no callers found. | 12aj7 AC-13: not-this-scope; guard-overrides.json seed_edit_allowed: false |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-01 | Remove tool entirely rather than keep as no-op stub | A no-op stub still pollutes the tool listing and confuses agents — the entire point of removal is to clean up the listing | Keep as no-op (rejected: defeats the purpose) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| An undiscovered seed or prompt still references `wave_change_create` | Confirmed none during 12aj7 AC-13 review; do a final `code_keyword_search` for `wave_change_create` before deleting |
| Tests that relied on the deprecation diagnostic path break in unexpected ways | `WaveChangeCreateDeprecationTests` is the only class; delete it cleanly alongside the tool |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
