# MCP Layer Polish

Change ID: `12aj7-enh mcp-layer-polish`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-01
Wave: `12ahv mcp-agent-surface`

## Rationale

Six related gaps in the MCP layer reduce agent effectiveness and create friction in day-to-day use. They were identified during the `129p8 mcp-docs-search-reliability` wave:

1. **Wave status drift** — `wave_current` shows change statuses from `wave.md` which can be stale relative to the actual change doc files. No tool detects or warns about this mismatch.
2. **`wave_change_create` duplication** — After `1297t` ships all 10 `wave_new_*` tools, `wave_change_create` becomes a redundant generic dispatcher sitting alongside the specific tools in every tool listing, confusing agents about which to use. MCP best practices (and the spec's SEP-986) recommend granular action-specific tools; `wave_change_create` should be deprecated in favor of `wave_new_*`.
3. **N+1 reads to inspect a wave** — Reading all change docs in a wave requires `wave_current` (to get IDs) then a separate `wave_get_change` per change. For a 10-change wave that's 11 round trips. A single call returning all changes with content would cut this substantially.
4. **Session handoff has no dedicated tool** — `docs/agents/session-handoff.md` is the primary state-continuity artifact referenced in every change doc, AGENTS.md, and journal, but agents must use the general `wave_map` tool to read it. A dedicated read/write pair makes session handoff a first-class MCP operation.
5. **`docs_search` mode is opaque** — When the semantic index is missing or stale, `docs_search` silently falls back to lexical search. The response `status` is still `"ok"` so agents can't distinguish lexical from semantic results without parsing diagnostics. A top-level `mode` field in the response data makes this transparent.
6. **AC priority tables are never enforced** — Change docs have AC priority tables that are meant to be filled in at Prepare wave, but `wave_prepare` passes with every row still containing the unpopulated placeholder text. A lint warning (not a hard block) would prompt operators to actually fill them in.

## Requirements

1. **Wave status drift detection:** `wave_current` cross-checks the change statuses declared in `wave.md` against the `Change Status:` fields in the actual change doc files under the wave folder. When any mismatch is found, the response `diagnostics` includes a `change_status_drift` entry listing the divergent IDs and their wave.md vs file values. The tool remains `status: "ok"` (drift is advisory, not a hard error).

2. **`wave_change_create` deprecation:** `wave_change_create` remains registered but its docstring prepends `[DEPRECATED — use wave_new_<kind> instead]`. Every response from `wave_change_create` includes a `diagnostics` entry with `code: "deprecated_tool"` and `message` pointing to the appropriate `wave_new_*` replacement. The tool is not removed in this change — removal is a follow-on after callers migrate. Seeds and prompt docs that reference `wave_change_create` are updated to prefer `wave_new_<kind>` with the script as the CLI fallback (seed edits require `seed_edit_allowed` guard).

3. **`wave_get_change` bulk mode:** `wave_get_change` gains an optional `wave_id` parameter. When `wave_id` is provided and `change_id` is omitted (or empty), the tool returns all change docs admitted to that wave as a list under `data.changes`, each with `id`, `status`, `path`, and `content`. Individual change lookup by `change_id` continues to work unchanged.

4. **Session handoff tool pair:**
   - `wave_get_handoff()` reads `docs/agents/session-handoff.md` and returns its content and last-modified time. Returns a not-found response with recovery hint when the file is absent.
   - `wave_set_handoff(content: str)` writes `docs/agents/session-handoff.md` with the provided content. Annotated as a mutating, non-destructive tool. Triggers a background docs-index refresh after write.

5. **`docs_search` mode transparency:** `docs_search` response `data` includes a top-level `"mode"` field: `"semantic"` when embeddings were used, `"lexical"` when the fallback path was taken. This is in addition to (not replacing) the existing `fallback_reason` diagnostics.

6. **AC priority lint warning:** `wave_prepare` checks each admitted change doc for the AC priority table. If every AC row still contains the unpopulated placeholder text (`required / important / nice-to-have / not-this-scope` verbatim), `wave_prepare` adds a `diagnostics` entry with `code: "ac_priority_unpopulated"` and a message naming the change doc. This is advisory (does not change `status` from `"ok"` to `"error"`).

7. **Tests** cover all six behaviors at parity with existing coverage: drift detection, deprecation diagnostic, bulk `wave_get_change`, handoff read/write, search mode field, and AC priority warning.

8. **AGENTS.md** "MCP Server" section documents `wave_get_handoff`, `wave_set_handoff`, the bulk `wave_get_change` usage, and notes `wave_change_create` as deprecated.

## Scope

**Problem statement:** Six independently small MCP gaps collectively degrade agent experience: stale wave state goes undetected, two competing creation patterns confuse tool selection, reading a full wave requires N+1 calls, the most-referenced state doc has no dedicated tool, search mode is invisible, and AC priority fills are never enforced.

**In scope:**

- `wave_current` drift detection (Requirement 1)
- `wave_change_create` deprecation annotation + seed/prompt updates (Requirement 2)
- `wave_get_change` bulk mode via optional `wave_id` param (Requirement 3)
- `wave_get_handoff` and `wave_set_handoff` tools (Requirement 4)
- `docs_search` `mode` field in response data (Requirement 5)
- `wave_prepare` AC priority warning (Requirement 6)
- Tests and AGENTS.md updates

**Out of scope:**

- Removing `wave_change_create` entirely — one migration window per SEP-986 deprecation guidance
- Making `wave_prepare` hard-block on unpopulated AC priority (advisory only; hard block deferred)
- Handoff tool formatting/templating — `wave_set_handoff` writes content as-is; no scaffolding
- Semantic index rebuilding from within the handoff tool
- Changing `docs_search` fallback behavior — only adding observability

## Acceptance Criteria

- AC-1: `wave_current` response `diagnostics` includes a `change_status_drift` entry when any change doc's `Change Status:` field differs from the corresponding status in `wave.md`.
- AC-2: `wave_current` response is `status: "ok"` even when drift is present (drift is advisory).
- AC-3: Calling `wave_change_create` produces a valid change doc AND a `diagnostics` entry with `code: "deprecated_tool"` naming the correct `wave_new_*` replacement.
- AC-4: `wave_get_change(wave_id="<id>")` (no `change_id`) returns all admitted change docs for that wave in `data.changes`, each with `id`, `status`, `path`, and `content`.
- AC-5: `wave_get_change(change_id="<id>")` still works exactly as before (no regression).
- AC-6: `wave_get_handoff()` returns the content and mtime of `docs/agents/session-handoff.md`, or a structured not-found response when absent.
- AC-7: `wave_set_handoff(content="...")` writes `docs/agents/session-handoff.md` and returns `status: "ok"` with the written path.
- AC-8: `docs_search` response `data` includes `"mode": "semantic"` or `"mode": "lexical"` in every successful response.
- AC-9: `wave_prepare` emits a `ac_priority_unpopulated` diagnostic (advisory) for any admitted change doc whose AC priority table contains only placeholder text.
- AC-10: `wave_prepare` continues to pass (status `"ok"`) when AC priority is unpopulated — it is a warning, not a block.
- AC-11: `python3 .wavefoundry/framework/scripts/run_tests.py` passes with new tests for all six behaviors.
- AC-12: `AGENTS.md` documents `wave_get_handoff`, `wave_set_handoff`, bulk `wave_get_change`, and `wave_change_create` deprecation.
- AC-13: Seeds and prompt docs that reference `wave_change_create` as the primary creation path are updated to prefer `wave_new_<kind>` (seed edits under `seed_edit_allowed` guard, guard restored after).

## Tasks

- Read `wave_current_response` in `server.py`; add drift check that compares wave.md statuses against change doc `Change Status:` fields.
- Read `wave_change_create` handler; add deprecation diagnostic to every response; update docstring.
- Inventory seeds/prompts that reference `wave_change_create`; update under `seed_edit_allowed` window; restore guard.
- Extend `wave_get_change` to accept optional `wave_id`; implement bulk-return path.
- Add `wave_get_handoff` and `wave_set_handoff` tool registrations; implement read/write logic with background refresh on write.
- Add `"mode"` field to `docs_search_response` return value.
- Add AC priority unpopulated check to `wave_prepare_response`; confirm it is advisory.
- Add tests for all six behaviors in `test_server_tools.py`.
- Update `AGENTS.md`.
- Run `python3 .wavefoundry/framework/scripts/run_tests.py` and confirm all pass.
- Run `.wavefoundry/bin/docs-lint` and confirm clean.

## Agent Execution Graph

| Workstream          | Owner       | Depends On       | Notes                                              |
| ------------------- | ----------- | ---------------- | -------------------------------------------------- |
| server-changes      | implementer | —                | Items 1–6 all touch `server.py`; single author     |
| seed-deprecation    | implementer | server-changes   | `seed_edit_allowed` guard; update `wave_change_create` refs |
| tests               | implementer | server-changes   | Cover all six new behaviors                        |
| docs                | implementer | server-changes   | AGENTS.md update                                   |
| guard-restore       | implementer | seed-deprecation | Reset guard before lint                            |

## Serialization Points

- `server.py` is single-author for the duration; all six server changes should land together before tests are written.
- `seed_edit_allowed` toggle is single-author for the seed deprecation window.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` Path 6 (MCP Tool Calls) — `wave_get_handoff`/`wave_set_handoff` and bulk `wave_get_change` are new read/write paths; update the inspection-tools and mutation-tools descriptions.
- `docs/architecture/current-state.md` — if it lists MCP tools by name, update to include new tools and mark `wave_change_create` deprecated.

## AC Priority

(Populated at Prepare wave.)

| AC    | Priority        | Rationale |
| ----- | --------------- | --------- |
| AC-1  | required        | Drift detection is the primary deliverable of item 1 |
| AC-2  | required        | Advisory-only behavior must be enforced; blocking would be a regression |
| AC-3  | required        | Deprecation diagnostic is the core of item 2 |
| AC-4  | required        | Bulk mode is the core of item 3; eliminates N+1 round trips |
| AC-5  | required        | Backwards compatibility for existing callers |
| AC-6  | required        | Handoff read is the core of item 4 |
| AC-7  | required        | Handoff write is the core of item 4 |
| AC-8  | required        | Mode transparency is the core of item 5 |
| AC-9  | required        | AC priority warning is the core of item 6 |
| AC-10 | required        | Warning must not become a block |
| AC-11 | required        | Tests are the verification gate for all six behaviors |
| AC-12 | required        | AGENTS.md is the primary agent reference |
| AC-13 | not-this-scope  | No seeds or prompts referenced wave_change_create as primary path; nothing to update |
| AC-13 | required / important / nice-to-have / not-this-scope |           |

## Progress Log

| Date       | Update         | Evidence                 |
| ---------- | -------------- | ------------------------ |
| 2026-05-01 | Plan authored. | Operator session — gaps identified during `129p8` wave work; `wave_change_create` deprecation pattern confirmed against MCP spec SEP-986 and best practices research. |
| 2026-05-01 | Implementation complete. All 6 items shipped: (1) `_detect_wave_status_drift` added to `wave_current_response`; (2) `wave_change_create` deprecation diagnostic on every call; (3) bulk `wave_get_change(wave_id=...)` returning all admitted changes with 300-line content cap; (4) `wave_get_handoff` / `wave_set_handoff` tools with background refresh; (5) `docs_search` adds `mode` field alongside `search_mode`; (6) `wave_prepare` advisory `ac_priority_unpopulated` diagnostic for unpopulated AC tables. 22 new tests added (391 total pass). AGENTS.md, architecture docs updated. No seeds required updating. docs-lint clean. | `python3 .wavefoundry/framework/scripts/run_tests.py` → 391 OK; `.wavefoundry/bin/docs-lint` → ok |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-01 | Standardize on `wave_new_*` specific tools; deprecate `wave_change_create` rather than remove immediately | SEP-986: deprecated tools should remain as aliases for at least one major version; `wave_change_create` may appear in seeds/prompts that need a migration window | Remove immediately (rejected: breaks callers before docs/seeds are updated); keep both as equals (rejected: perpetuates confusion) |
| 2026-05-01 | AC priority warning is advisory, not a hard block | Hard blocking would prevent prepare on existing waves that predate this change; advisory gives visibility without being disruptive | Hard block (deferred — can be promoted in a follow-on once the pattern is established) |
| 2026-05-01 | Bulk `wave_get_change` extends existing tool via optional param rather than adding a new tool | Avoids adding `wave_list_change_content` as a separate tool when the existing tool's signature can accommodate it cleanly | New `wave_list_changes` tool (rejected: unnecessary proliferation for a small extension) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Drift check adds latency to `wave_current` by reading change doc files | Read only files in the active wave folder (not all waves); use cached mtimes where possible |
| Bulk `wave_get_change` returns too much content for large waves | Cap content per change at a reasonable line limit; document the cap |
| `wave_set_handoff` overwrites handoff state from a parallel session | Caller responsibility; tool is single-write; no locking — document this |
| Seed deprecation window leaves guard enabled if interrupted | Single guarded window per policy; guard-restore is the final task before lint |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
