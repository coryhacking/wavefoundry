# MCP Tool Routing Guidance

Change ID: `12bb9-doc mcp-search-tool-routing-guidance`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-02
Wave: `12b9x journal-signal-over-log`

## Rationale

The MCP tool surface has 40+ tools, but most docstrings describe *what* a tool does, not *when* to prefer it over alternatives. This leaves three concrete gaps:

1. **Search routing**: agents cannot determine whether to use semantic search, keyword search, or AST-based definition lookup for a given query. `code_search` in particular has no routing guidance, no degradation behavior note, and no example query style.
2. **Change creation selection**: ten `wave_new_*` tools share identical one-line docstrings. An agent cannot determine whether a documentation improvement is `wave_new_documentation`, `wave_new_enhancement`, or `wave_new_change` without external context.
3. **Lifecycle tool sequencing**: `wave_prepare`, `wave_pause`, `wave_validate`, `wave_audit`, `seed_get`, `wave_current`, and `wave_list_waves` lack "when to call this" framing — agents miss the sequencing contract (e.g., prepare before code edits, pause at session end, audit after mutations).

These gaps cause agents to skip better-fit tools, pick the wrong change kind, and miss lifecycle requirements that only become visible after violations.

## Requirements

1. `code_search` docstring must include: routing guidance (when to prefer over `code_keyword_search`), degradation behavior when the index is unavailable, and an example query style.
2. `docs_search` docstring must state that it covers framework seeds (`.wavefoundry/framework/seeds/`) in addition to project docs, architecture, and prompts.
3. All five search tool docstrings (`docs_search`, `code_search`, `code_keyword_search`, `code_definition`, `code_references`) must include a one-line "prefer this tool when" routing hint.
4. Each `wave_new_*` tool docstring must include a one-line "use for" description that distinguishes it from adjacent kinds (e.g., `wave_new_documentation` vs `wave_new_enhancement`).
5. `wave_validate` docstring must note it is for lint-only targeted checks; prefer `wave_audit` for combined state + lint + index.
6. `wave_audit` docstring already says "preferred landing tool after any mutation" — no change needed; verify it remains accurate.
7. `seed_get` docstring must note: use when you know the seed name; use `docs_search` when searching by concept.
8. `wave_prepare` docstring must note: call after all changes are admitted and before any code edits to framework files.
9. `wave_pause` docstring must note: call at session end when work is incomplete and must resume in a later session.
10. `wave_map` docstring must note: use to navigate from a search result anchor (`doc:`, `code:`, `seed:`) to the actual file.
11. `wave_current` docstring must note: use for active work context; use `wave_list_waves` when discovering across all waves.
12. `docs/specs/mcp-tool-surface.md` "Planned Navigation Tools" section must be updated to reflect that all listed tools are already shipped and live.
13. `docs/specs/mcp-tool-surface.md` must include a "Tool Selection Guide" section with a routing decision table: query type → recommended tool → fallback.

## Scope

**Problem statement:** Agent tool selection is guided only by tool names and "what it does" descriptions. No tool explains when to prefer it over alternatives, causing agents to pick wrong tools, miss lifecycle requirements, and create change docs of the wrong kind.

**In scope:**

- `server.py` docstrings: all tools with routing or sequencing gaps identified in Requirements
- `docs/specs/mcp-tool-surface.md`: retire "Planned Navigation Tools" framing, add Tool Selection Guide section

**Out of scope:**

- Changes to tool behavior, parameters, or return shapes
- `code_read` and `code_list_files` — navigation tools, routing is self-evident from names
- `wave_create_wave`, `wave_add_change`, `wave_remove_change`, `wave_close`, `wave_review`, `wave_garden`, `wave_sync_surfaces` — lifecycle position implied by name, no routing ambiguity
- `wave_open_gate` / `wave_close_gate` — paired call contract already documented in current docstring
- Routing guidance in `AGENTS.md` — covered by reference to `docs/specs/mcp-tool-surface.md`

## Acceptance Criteria

- AC-1: `code_search` docstring includes: routing hint (semantic vs keyword preference), degradation note (index required), example query format.
- AC-2: `docs_search` docstring states it covers seeds at `.wavefoundry/framework/seeds/`.
- AC-3: Each of the five search tool docstrings (`docs_search`, `code_search`, `code_keyword_search`, `code_definition`, `code_references`) contains a "prefer when" routing hint.
- AC-4: Each `wave_new_*` tool docstring contains a one-line "use for" description that distinguishes it from adjacent kinds.
- AC-5: `wave_validate` docstring references `wave_audit` as the preferred combined check.
- AC-6: `seed_get`, `wave_prepare`, `wave_pause`, `wave_map`, `wave_current` docstrings each contain a routing or sequencing hint per Requirements 7–11.
- AC-7: `docs/specs/mcp-tool-surface.md` no longer uses "Planned Navigation Tools" framing for shipped tools.
- AC-8: `docs/specs/mcp-tool-surface.md` contains a Tool Selection Guide table mapping query type to recommended tool with fallback.

## Tasks

- Read `server.py` tool docstrings and current `docs/specs/mcp-tool-surface.md` to baseline before editing.
- **Search tools:** Update docstrings for `docs_search`, `code_search`, `code_keyword_search`, `code_definition`, `code_references` with routing hints per Requirements 1–3.
- **Change creation tools:** Update all ten `wave_new_*` docstrings with "use for" one-liners per Requirement 4. Canonical mapping:
  - `wave_new_feature` — net-new capability with user-visible behavior
  - `wave_new_bug` — fix for a defect in existing behavior
  - `wave_new_enhancement` — improvement or extension of existing functionality
  - `wave_new_refactor` — code structure change with no behavior change
  - `wave_new_change` — general change that doesn't fit a more specific kind
  - `wave_new_documentation` — docs-only: new or updated docs, spec, or seed content
  - `wave_new_tech_debt` — cleanup of known technical debt
  - `wave_new_task` — one-off task with no ongoing code artifact (e.g., fixture refresh)
  - `wave_new_maintenance` — routine upkeep (e.g., rotating generated surfaces, version bumps)
  - `wave_new_operations` — operational/process change (e.g., release checklist, runbook)
- **Lifecycle tools:** Update `wave_validate`, `seed_get`, `wave_prepare`, `wave_pause`, `wave_map`, `wave_current` per Requirements 5, 7–11.
- **Spec:** Rename "Planned Navigation Tools" section and add Tool Selection Guide table to `docs/specs/mcp-tool-surface.md`.
- Run `wave_validate` after all edits.

## Agent Execution Graph

| Workstream                  | Owner       | Depends On                          | Notes                                                    |
| --------------------------- | ----------- | ----------------------------------- | -------------------------------------------------------- |
| search-docstrings           | implementer | —                                   | Five search tool docstrings in `server.py`               |
| change-creation-docstrings  | implementer | —                                   | Ten `wave_new_*` docstrings in `server.py`               |
| lifecycle-docstrings        | implementer | —                                   | Six lifecycle tool docstrings in `server.py`             |
| spec-updates                | implementer | —                                   | `docs/specs/mcp-tool-surface.md` section rename + table  |
| validation                  | implementer | all four above                      | `wave_validate` after all edits                          |

## Serialization Points

- All four `server.py` workstreams edit the same file — serialize them or coordinate line ranges to avoid conflicts.
- `docs/specs/mcp-tool-surface.md` is independent and can run in parallel with `server.py` edits.

## Affected Architecture Docs

N/A — this change updates tool documentation and spec copy only. No boundary, flow, or verification architecture is affected.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority      | Rationale |
| ---- | ------------- | --------- |
| AC-1 | required      | `code_search` is the most misused tool; routing + degradation guidance is the core gap |
| AC-2 | important     | Seed coverage is a frequent blind spot; low-cost fix with high discovery value |
| AC-3 | required      | Consistent routing hints across all five search tools is the deliverable for this cluster |
| AC-4 | required      | Change kind selection is the highest-friction gap for agents starting a new change |
| AC-5 | important     | Reduces `wave_validate` / `wave_audit` confusion; small change with high clarity payoff |
| AC-6 | important     | Lifecycle sequencing hints prevent missed gates; multiple tools, each a one-liner |
| AC-7 | required      | Stale "Planned" framing is actively misleading — shipped tools must not be labeled planned |
| AC-8 | required      | Durable routing table is the primary reference artifact for this entire change |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-05-02 | Created |          |
| 2026-05-02 | Implementation complete | 21 docstrings updated in server.py, spec rewritten; docs-lint clean. wave_change_create refs also cleaned from spec and architecture docs. |

## Decision Log

| Date       | Decision                                                             | Reason                                                                              | Alternatives |
| ---------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------ |
| 2026-05-02 | Routing guidance lives in docstrings AND spec, not only one place    | Docstrings are visible to agents inline; spec provides durable reference for humans | Docstrings only — not enough for spec readers; spec only — not enough for inline callers |
| 2026-05-02 | "Planned Navigation Tools" renamed rather than deleted               | Existing backlinks and references should resolve; rename preserves discovery path   | Delete section — breaks any docs that reference the heading |
| 2026-05-02 | Change kind mapping included in Tasks, not just AC                   | Implementer needs the canonical mapping to write accurate "use for" lines without guessing | Leave it to implementer — risks inconsistent or vague distinctions |
| 2026-05-02 | `wave_audit` docstring excluded from changes (already adequate)      | Current "preferred landing tool after any mutation" framing is correct; AC-6 verifies it remains accurate | Rewrite anyway — unnecessary churn |

## Risks

| Risk                                                                   | Mitigation                                                                                  |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Docstring verbosity degrades tool call UX for LLMs                     | Keep routing hints to one line each; full decision guidance goes in the spec                |
| Spec routing table becomes stale as tools evolve                       | Update spec as part of any future tool surface change (existing docs gate)                  |
| `server.py` has 40+ tools — edits to many docstrings risk merge errors | Serialize all `server.py` workstreams; do not parallelize edits to the same file            |
| Change kind distinctions are subjective — "use for" lines may conflict | Canonical kind mapping is defined in Tasks; implementer must follow it without editorializing |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
