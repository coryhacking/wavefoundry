# Complete Graph-Tools Agent Guidance and Tool-Surface Spec

Change ID: `1p41m-doc complete-graph-tools-agent-guidance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-07
Wave: 1p41l graph-tools-field-feedback-round-5

## Rationale

Round-5 grounding of the Aceiss graph-tools field eval (logged in `project_mcp_code_tool_quality_log`) confirmed that two **already-shipped** capabilities lack the agent-facing guidance / accurate documentation needed to use them. These are pure doc/guidance gaps — the mechanisms exist in code — so closing them prevents agents (and external teams reading the spec) from concluding a shipped capability is missing.

- **§4.4 — betweenness reliability note absent from seed-211.** `wave_graph_report` emits a `betweenness_dominated_by_generated` warning (wave `130rj`, `server_impl.py:13029`) when >50% of top-N betweenness nodes are generated. The mechanism and the `exclude_generated` / `collapse_generated_files` filters are documented in the MCP docstring, but `211-guru.prompt.md` never tells an agent to *act* on the warning. `grep betweenness_dominated_by_generated .wavefoundry/framework/seeds/211-guru.prompt.md` returns zero hits. The `130rj-enh seeds-pattern-library-and-recipes` change doc claimed this anti-pattern note; it is not present today (likely regressed out during a later seed rewrite).
- **§2.2 — `mcp-tool-surface.md` section list incomplete.** `docs/specs/mcp-tool-surface.md` lists the `wave_graph_report` sections as `fan_in`/`fan_out`/`chokepoints`/`orphan_docs`/`cross_layer` but omits the `communities` and `betweenness` sections that ship in the default set (`server_impl.py:12943`, `13017`).

## Requirements

1. Add an anti-pattern note to the `wave_graph_report` guidance in `.wavefoundry/framework/seeds/211-guru.prompt.md`: when the response carries `betweenness_dominated_by_generated: true`, treat betweenness as unreliable, re-run with `exclude_generated=true` (or `collapse_generated_files=true`), and prefer `fan_in`/`fan_out` for hotspot identification. Place it in the existing wave_graph_report parameter/cheat-sheet block alongside the `exclude_generated` / `collapse_generated_files` entries.
2. Complete the `wave_graph_report` section list in `docs/specs/mcp-tool-surface.md` to include `communities` (per-community overview: `community_id`, `label`, `node_count`, `hub_node_id`/`hub_label`) and `betweenness` (bridge nodes by centrality; skipped >10k nodes; carries `betweenness_computed` / `betweenness_dominated_by_generated`).
3. No code changes and no behavior change. The rendered role doc `docs/agents/guru.md` is regenerated separately in `1p41n-maint`, which carries Requirement 1 into the per-project doc (seed-first ordering).

## Scope

**Problem statement:** Two shipped graph-tools capabilities (the betweenness generated-dominated warning; the `communities`/`betweenness` report sections) are under-documented, so agents and external readers do not discover or act on them.

**In scope:**

- `211-guru.prompt.md` — add the betweenness `betweenness_dominated_by_generated` anti-pattern note.
- `docs/specs/mcp-tool-surface.md` — complete the wave_graph_report section list.

**Out of scope:**

- Regenerating `docs/agents/guru.md` (handled by `1p41n-maint`, which depends on this change).
- Any code change to `wave_graph_report` or the betweenness computation.

## Acceptance Criteria

- [x] AC-1: `211-guru.prompt.md` contains an actionable instruction to treat betweenness as unreliable and re-run with `exclude_generated`/`collapse_generated_files` when `betweenness_dominated_by_generated` is set. Verify: `grep betweenness_dominated_by_generated .wavefoundry/framework/seeds/211-guru.prompt.md` returns ≥1 hit.
- [x] AC-2: `docs/specs/mcp-tool-surface.md` wave_graph_report section list includes `communities` and `betweenness`. Verify: both terms appear in that section list line.
- [x] AC-3: `docs-lint` / `wave_validate` clean after the edits.

## Tasks

- [x] Open `seed_edit_allowed`; add the betweenness anti-pattern note to the seed-211 wave_graph_report block; close the gate.
- [x] Edit `docs/specs/mcp-tool-surface.md` to add `communities` and `betweenness` to the section list.
- [x] Run `wave_validate` / docs-lint.

## Agent Execution Graph


| Workstream         | Owner       | Depends On | Notes |
| ------------------ | ----------- | ---------- | ----- |
| seed-211 note      | Engineering | —          | Needs `seed_edit_allowed` gate |
| mcp-surface fix    | Engineering | —          | Plain docs edit, no gate |


## Serialization Points

- `211-guru.prompt.md` is also the regeneration source for `1p41n-maint`; `1p41n` must run **after** this change so the regenerated `guru.md` carries the new note.

## Affected Architecture Docs

N/A — guidance/spec prose only; no architecture boundary, flow, or verification change.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The core guidance gap — agents don't act on the shipped betweenness warning without it |
| AC-2 | important | Spec completeness so external readers see the shipped `communities`/`betweenness` sections |
| AC-3 | required  | Docs gate must pass |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-07 | Implemented: seed-211 betweenness anti-pattern note + `mcp-tool-surface.md` section list (`communities`, `betweenness`). | seed-211 grep `betweenness_dominated_by_generated` = 1; `mcp-tool-surface.md` lists `communities`+`betweenness`; docs-lint ok |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Note regresses out again on a future seed rewrite | Anchor it next to the `exclude_generated` entry it references so it travels with that block |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
