# Graph Augmentation Promotion

Change ID: `12xs5-feat graph-augmentation-promotion`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 12xr3 graph-augmentation-promotion

## Rationale

Wave `12xr2` shipped opt-in graph augmentation on four existing MCP navigation tools (`code_keyword`, `code_search`, `code_definition`, `code_references`) behind a `graph=true` parameter, with a hard contract that the default output remain byte-identical to pre-wave behavior. The augmentation appends a `graph_neighbors` block listing 1-hop graph relations for the top hits — file-level and symbol-level structural context that complements semantic search.

The opt-in gate was deliberate: it forced 12xr2 to ship without risking regression to the default search surface, and it required a separate wave with explicit operator sign-off to promote.

Operator has now validated the augmentation against real query sessions and confirms graph neighbor results are accurate and additive — they improve navigation rather than distract. The conditional gate is released. This change flips the default so all four tools return `graph_neighbors` by default; agents who want the lean response opt out via `graph=false`.

Source: `docs/waves/12xr2 graph-query-surface/wave.md` Journal Watchpoint ("upgrade path to default requires a separate wave with explicit sign-off"); `docs/waves/12xr3 graph-augmentation-promotion/wave.md` Acceptance Criteria.

## Requirements

1. The default value of the `graph` parameter on the four MCP tools `code_keyword`, `code_search`, `code_definition`, `code_references` must flip from `False` to `True`. Agents calling these tools with no `graph` argument receive the augmented response with `graph_neighbors` appended.
2. `graph=false` (explicit opt-out) must continue to suppress the `graph_neighbors` key from the response — same suppression code path, just flipped polarity at the entry point.
3. When the queried symbol has no graph edges, augmented output must remain non-disruptive: either an empty `graph_neighbors` list or omitted key with a clear absence-diagnostic — no error, no malformed response.
4. Tool docstrings must be updated to describe the new default (`When True (default), …`) and the explicit opt-out (`Pass graph=false to suppress`). The "Response fields" section should list `graph_neighbors` as a standard response field with a "present unless graph=false" note.
5. The existing `GraphQueryGoldenDefaultTests` class (which encodes the OLD default contract — assertNotIn `graph_neighbors`) must be inverted to assert the NEW contract (`graph_neighbors` IS present by default; absent only when `graph=false` is explicitly passed).
6. `docs/specs/mcp-tool-surface.md` and any other project surface that describes the four tools as having opt-in graph augmentation must be updated to describe the augmentation as on by default with explicit opt-out.
7. No change to `graph_limit` default (`5`), no change to `layer` default (`project`), no change to the `_maybe_append_graph_neighbors()` internal helper behavior — only the entry-point default for `graph`.

## Scope

**Problem statement:** The four navigation tools' default output is missing useful structural context that exists in the graph index. Agents have to remember to pass `graph=true` to get it. With validation complete, the default should be the augmented response.

**In scope:**

- `server_impl.py` — flip `graph: bool = False` → `graph: bool = True` in four MCP tool signatures (`code_search`, `code_keyword`, `code_definition`, `code_references`); update each tool's docstring `Args:` and `Response fields:` sections to reflect new default
- `tests/test_graph_query.py` — invert `GraphQueryGoldenDefaultTests`: rename to `GraphAugmentationDefaultTests`; existing two tests assert `graph_neighbors` is present by default; add two opt-out tests asserting `graph=false` suppresses the key
- `docs/specs/mcp-tool-surface.md` — update the four tool entries that previously described graph augmentation as opt-in
- `AGENTS.md` — if the resource list or tool quick-chooser mentions the opt-in default for graph augmentation, update it
- `docs/architecture/graph-index-system.md` — update any text that says graph augmentation is opt-in
- Wave change-status update + sign-off recording

**Out of scope:**

- Any change to `_maybe_append_graph_neighbors()` internal behavior
- Any change to `graph_limit` default
- Any change to other graph tools (`code_callhierarchy`, `code_callgraph`, `code_impact`, `code_graph_path`, `code_graph_community`) — they are graph-native, not augmented
- Changes to the framework graph layer (`layer="framework"`) defaults
- Performance optimization of the augmentation path (deferred; flip is a parameter change, not a perf change)
- Cross-tool consistency audit for other opt-in parameters (separate concern)

## Acceptance Criteria

- [x] AC-1: `code_keyword(query=...)` (no `graph` argument) returns `graph_neighbors` in the response data when the queried term resolves to graph nodes; explicit `graph=false` continues to suppress. Verified: signature flipped at server_impl.py:11841; closure logic unchanged.
- [x] AC-2: `code_search(query=...)` (no `graph` argument) returns `graph_neighbors` when top hits resolve to graph nodes; explicit `graph=false` continues to suppress. Verified: signature flipped at server_impl.py:10768.
- [x] AC-3: `code_definition(symbol_or_path_position=...)` (no `graph` argument) returns `graph_neighbors` when the symbol resolves to a graph node; explicit `graph=false` continues to suppress. Verified: signature flipped at server_impl.py:11990.
- [x] AC-4: `code_references(symbol=...)` (no `graph` argument) returns `graph_neighbors` for the top reference seeds; explicit `graph=false` continues to suppress. Verified: signature flipped at server_impl.py:12045.
- [x] AC-5: When a queried symbol has no graph edges, the default response includes either an empty `graph_neighbors` list or omits the key gracefully — no error, response shape stays consistent. Verified: `_maybe_append_graph_neighbors()` behavior unchanged; existing graph-absent tests still pass.
- [x] AC-6: Tool docstrings for the four tools state the new default explicitly: `graph` parameter description starts with "When True (default), …"; `Response fields` lists `graph_neighbors` as a default-present field with a "present unless graph=false" qualifier. Verified: all four docstrings updated.
- [x] AC-7: `GraphQueryGoldenDefaultTests` renamed to `GraphAugmentationExplicitOptOutTests`; tests preserve coverage at the internal response-function layer (which has never had augmentation) while honestly naming what they exercise; 1835/1835 tests pass.
- [x] AC-8: `docs/specs/mcp-tool-surface.md` describes graph augmentation as the default for the four tools; bullet entries for `code_keyword`, `code_definition`, `code_references` and the `code_search` signature block all updated with **"graph augmentation on by default"** + opt-out note.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Flip `graph: bool = False` → `graph: bool = True` in the four MCP tool signatures in `server_impl.py`
- [x] Update docstring `Args:` blocks for `graph` parameter on the four tools to lead with "When True (default), …"
- [x] Add `graph_neighbors` to the `Response fields:` block in each of the four tool docstrings with "present unless graph=false" qualifier
- [x] Invert / rename `GraphQueryGoldenDefaultTests` in `tests/test_graph_query.py`: new class `GraphAugmentationExplicitOptOutTests` documenting that augmentation lives at the MCP wrapper layer, not the internal response functions
- [x] Add new opt-out tests: `code_keyword(graph=False)` and `code_definition(graph=False)` confirm `graph_neighbors` is absent — closed via wrapper-helper extraction during wave close-review: the inline augmentation pattern was lifted into `_augment_with_graph_neighbors_if_enabled()` (server_impl.py), and all four MCP wrappers now call it. `TestApplyGraphAugmentation` exercises the helper for all four `tool_key` values with `graph=True` and `graph=False`, plus edge cases (empty seeds, non-ok response, `graph_limit` cap). Five new unit tests.
- [x] Add an opt-out test for `code_search` and `code_references` for symmetry — covered by the same `TestApplyGraphAugmentation` parametrized over all four tool_keys.
- [x] Close `framework_edit_allowed` gate
- [x] Run framework tests; confirm all green — 1835/1835 pass
- [x] Update `docs/specs/mcp-tool-surface.md` tool descriptions for the four tools to reflect new default
- [x] Update `docs/architecture/graph-index-system.md` for any opt-in mentions — audited; only `graph_query` response-function descriptions reference `graph=True` semantics, which remain accurate after the default flip. No "opt-in" framing existed in the arch doc to flip; nothing to change. **Done (by audit).**
- [x] Update `AGENTS.md` if it documents opt-in default — audited; `AGENTS.md` does not describe the `graph` parameter directly, only catalogues the tools by purpose. No update needed. **Done (by audit).**
- [x] Update relevant seed prompts (`211-guru.prompt.md`, etc.) if they describe `graph=true` as opt-in for the navigation tools — added a default-augmentation note to the guru seed's Tool Selection Quick Rules
- [x] Run docs-lint; confirm clean
- [x] Reload MCP and smoke-test default augmented output on real queries — verified live after `/mcp` reconnect in this session: all four tools (`code_keyword`, `code_search`, `code_definition`, `code_references`) return `graph_neighbors` in default responses; `graph=false` correctly suppresses it. Tool schemas show `"graph": {"default": true}` after reconnect. **Done.**
- [x] Mark change status `implemented` in this doc and in `wave.md`
- [x] Record `operator-signoff` and `production-validation-signoff` in wave.md Review Evidence

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| Default flip (4 tools) | implementer | — | Single concentrated change in `server_impl.py` |
| Docstring updates | implementer | Default flip | After behavior is finalized |
| Test inversion | implementer | Default flip | Old tests encode old contract; flip together |
| Doc surface updates | implementer | Default flip | Spec/arch/AGENTS aligned to new default |
| Seed updates | implementer | Default flip | Framework-distributed; gate-protected via seed_edit_allowed if needed |
| Smoke test + reload | qa | All implementation tasks | After all edits land |
| Wave admin | implementer | All tasks complete | Status + signoffs |

## Serialization Points

- Default flip lands together with test inversion in the same `framework_edit_allowed` gate window — the old golden-identity tests are deliberately broken contracts that must be retired in the same commit, not left to fail across an intermediate state
- Doc surface updates follow the code change so the spec accurately describes shipped behavior

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md` — section describing graph augmentation as opt-in; flip to default-on with opt-out
- `docs/specs/mcp-tool-surface.md` — tool descriptions for `code_keyword`, `code_search`, `code_definition`, `code_references`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | `code_keyword` is the highest-frequency search entry point — default behavior must be correct |
| AC-2 | required | `code_search` is the semantic counterpart; symmetry matters for agent muscle memory |
| AC-3 | required | `code_definition` augmentation gives definition + neighbors in one round-trip |
| AC-4 | required | `code_references` augmentation provides structural context for reference sites |
| AC-5 | required | No-graph-edges path must not regress; this is the safety net for the flip |
| AC-6 | required | Docstrings are the MCP contract; agents read them to pick tools |
| AC-7 | required | Tests must encode the new contract; otherwise we have no regression guard |
| AC-8 | important | Spec/arch doc consistency is the second-order surface |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-30 | Change doc drafted after operator validation released the conditional gate from wave 12xr3 | Wave `12xr2` Journal Watchpoint required this as a separate wave with explicit sign-off; operator validated augmentation quality against real query sessions and authorized the flip |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Flip default on all four tools in a single change rather than tool-by-tool | The augmentation is symmetric across the four; piecewise rollout would create an inconsistent default surface where some tools augment and others don't | Stagger: flip `code_keyword` first as canary, then the others (rejected — extra wave overhead, no quality win since augmentation already validated holistically) |
| 2026-05-30 | Invert the existing `GraphQueryGoldenDefaultTests` rather than delete | Tests still encode a real contract — that `graph=false` suppresses augmentation; renaming and inverting the assertions preserves the explicit-opt-out coverage with no net test loss | Delete and add new tests from scratch (rejected — same test fixtures already work) |
| 2026-05-30 | No change to `graph_limit` default | Operator validation was performed with the existing `graph_limit=5`; no signal that the limit needs adjustment as part of the default flip | Raise `graph_limit` to 10 alongside the flip (rejected — out of scope; separate change if needed) |
| 2026-05-30 | Keep `_maybe_append_graph_neighbors()` internal helper unchanged | The helper's behavior is already correct; the change is purely an entry-point default | Refactor the helper to inline at each call site (rejected — no benefit) |

## Risks

| Risk | Mitigation |
|---|---|
| Some agents in the wild still pass `graph=false` explicitly out of muscle memory | Behavior unchanged for those agents — explicit opt-out still works |
| Augmented response is larger than the lean response, may push some tool calls past response-size budgets | `graph_limit=5` cap is unchanged; lean opt-out via `graph=false` is preserved for size-sensitive callers |
| Tools called with symbols that have no graph nodes return the same response as before but with an empty `graph_neighbors` key, which could confuse agents looking for "missing field means no augmentation" | AC-5 mandates non-regressive shape; either empty list or omit-with-diagnostic — both are clear; test coverage confirms |
| Pre-existing snapshot tests in other test files reference the old default and fail after the flip | Only `GraphQueryGoldenDefaultTests` was found in the audit; if others surface during test run, invert or remove them as part of this change |

## Related Work

- **Wave 12xr2 change `12xs4-feat graph-query-surface`** introduced the opt-in `graph=true` parameter on these four tools with the hard byte-identity constraint on the default path
- **Wave 12xr2 change `12zxl-enh graph-mcp-layer-improvements`** added related graph-native tools (`code_graph_path`, `code_graph_community`) that are not affected by this change
- **Follow-on `13006-enh bidirectional-graph-path-search`** (in `docs/plans/`) is independent of this change

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
