# Graph Rebuild Discoverability — Health Breakdown, Build Counts, Last-Built Timestamp

Change ID: `1316n-enh graph-rebuild-discoverability-and-health`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Aceiss round-trip report on `1.2.1+315o` (2026-06-01): the semantic `wave_index_build(content='code'|'all', mode='rebuild')` doesn't rebuild the graph layer. The `content='graph'` option exists, but the operator-facing surfaces don't make this clear:

- `wave_index_health` returns a single `readiness: current` per layer with no breakdown of graph vs semantic.
- The `wave_index_build` response reports `doc_chunks` and `code_chunks` but says nothing about graph state.
- No `last_graph_built_at` timestamp anywhere — operators can't tell if the graph reflects current code.
- Seed-160 and the upgrade prompt mention `mode='rebuild'` for refreshing but don't mention `content='graph'` separately.

Net effect: operator runs `wave_index_build(mode='rebuild')`, sees "passed: true", `wave_index_health` says everything is current, and assumes the graph rebuilt. It didn't. Aceiss caught this only because graph queries returned byte-identical results across two rebuild attempts.

## Requirements

1. **`wave_index_health` response breaks out graph readiness separately** from semantic readiness. New fields per layer: `graph_readiness`, `graph_last_built_at`, plus the existing semantic fields. Both project and framework layers carry the breakdown.
2. **`wave_index_build` response always carries graph counts** when the graph artifact exists for the target layer: `graph_node_count`, `graph_edge_count`, `graph_community_count`, `graph_last_built_at`. Present even when `content='code'` or `content='docs'` (so operators see the graph wasn't touched).
3. **`wave_index_build` notice message clarifies what was/wasn't rebuilt** when `content='code'` or `'docs'` or `'all'` — explicit "Graph layer was NOT rebuilt. Run wave_index_build(content='graph') if graph refresh is required."
4. **Seed-160 (upgrade) and any other operator-facing prompt mentioning rebuild** carries an explicit "semantic vs graph" callout — graph is rebuilt only by `content='graph'` (or `content='all'` if that's the actual contract — verify during implementation).
5. **Tests** cover (a) graph readiness reported separately when graph is stale; (b) build response carries graph counts; (c) notice message includes the "graph not rebuilt" callout when content is not graph.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — `wave_index_health_response`, `wave_index_build_response` field additions.
- `.wavefoundry/framework/scripts/graph_indexer.py` or wherever graph state is read — expose `last_built_at` from the graph artifact.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` — semantic vs graph callout.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — 3 regression tests.

**Out of scope:**

- Changing the `content='code'`/`'docs'`/`'all'` semantics to also rebuild graph. The current separation is intentional (semantic is slow, graph is fast — different cadences make sense).
- A new unified `wave_index_build_all` that rebuilds both layers. Operators can invoke twice if they need both.
- Auto-detection of stale graph based on code changes. Operator-triggered rebuild is the right cadence.

## Acceptance Criteria

- [x] AC-1: `wave_index_health` response carries `graph_readiness` and `graph_last_built_at` per layer, separate from semantic readiness.
- [x] AC-2: `wave_index_build` response carries `graph_node_count` / `graph_edge_count` / `graph_community_count` / `graph_last_built_at` when the graph artifact exists.
- [x] AC-3: When `content` is not `'graph'`, the response notice message explicitly states the graph was NOT rebuilt and points at `content='graph'` for graph refresh.
- [x] AC-4: Seed-160 carries the semantic vs graph callout.
- [x] AC-5: 3 regression tests cover the field presence and notice wording.
- [x] AC-6: docs-lint passes after seed edit.
- [x] AC-7: All existing tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Extend `wave_index_health_response` with graph fields
- [x] Extend `wave_index_build_response` with graph counts + notice clarification
- [x] Open `seed_edit_allowed` gate
- [x] Update seed-160 with semantic vs graph callout
- [x] Run docs-lint
- [x] Close `seed_edit_allowed` gate
- [x] Add 3 regression tests
- [x] Run framework tests
- [x] Close `framework_edit_allowed` gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline observability gap Aceiss reported |
| AC-2 | required | Build response signals what was/wasn't touched |
| AC-3 | required | The actionable callout that prevents the "didn't rebuild graph" misread |
| AC-4 | required | Operator guidance for upgrade flow |
| AC-5 | required | Regression coverage |
| AC-6 | required | docs-lint hygiene |
| AC-7 | required | No collateral breakage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Surface graph state on every wave_index_build response (not just content='graph') | Operators running content='code' or 'docs' need to see the graph wasn't touched. Silence implies the rebuild covered everything | Only report graph state when content='graph' (rejected — preserves the misread Aceiss caught) |
| 2026-06-01 | Explicit notice callout when content is not 'graph' | Aceiss confirmed "passed: true" + wave_index_health "current" is the misleading combo. The notice message is the breakpoint where operators read what happened | Documentation-only fix (rejected — seed updates don't help mid-flow when operator is reading the response) |
| 2026-06-01 | Don't auto-rebuild graph when content='all' | Graph rebuild has its own cadence. `content='all'` already implies "both semantic layers" — adding graph would surprise consumers expecting only semantic rebuild | Make 'all' rebuild graph too (rejected — silent behavior change) |

## Risks

| Risk | Mitigation |
|---|---|
| Adding fields to wave_index_health response could break consumers parsing the exact response shape | Fields are additive; no removal or rename. Schema-strict consumers receive extra keys (standard JSON parsing tolerates) |
| Operators interpret graph_last_built_at as a freshness guarantee | The field is a timestamp, not a stale/current verdict. Operators inspecting it understand the freshness model |

## Related Work

- Direct response to Aceiss field feedback on `1.2.1+315o` (Finding 1).
- Same wave: companion to `1316j` / `1316l` / `1316p` / `1316r` / `1316t` (all six round-3 follow-ons land together to minimize the operator round-trip count).

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
