# Generated-Code Collapse Mode — File-as-Black-Box View for Architectural / Visualization Use

Change ID: `130su-enh generated-code-collapse-mode`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Change 5 (`130rj-enh generated-code-classifier-and-filters`) classifies generated files and tags their nodes with `generated: true`, then filters them out of architectural metrics via `exclude_generated`. That handles the "filter the noise out of architectural mode" use case correctly.

But there's a second axis Change 5 doesn't address: **graph visualization** in the dashboard and **architectural overviews** that want to *show* the existence of generated code but not its internal structure. A 330-node generated parser (Aceiss's ELParser case) renders as a hairball in any graph visualization regardless of whether it dominates fan_in rankings. The architect's mental model of the codebase is "there's a parser over there"; they don't want 330 nodes to skim past.

Classify-and-collapse keeps the same `generated: true` tag from Change 5 and offers a query-time *aggregation* of generated nodes by file. In collapse mode:

- Each generated FILE is represented by ONE node (the file's module node).
- Internal edges within a generated file are dropped.
- External-to-internal edges (handwritten code calling INTO generated code, e.g. `Runtime.parse() → ELParser.Statement()`) get *rewritten* to terminate at the file node (`Runtime.parse() → ELParser.java`). Caller still has evidence that the call lands "somewhere in ELParser"; the specific method node is hidden.
- External-from-internal edges (generated code calling INTO handwritten code, e.g. `ELParser.error() → Logger.log()`) get rewritten the same way (`ELParser.java → Logger.log()`). Logger's incoming count includes "from ELParser (collapsed)" without the parser's internal 1500-edge chain.

This preserves edge integrity at the file granularity while shrinking the graph's apparent complexity dramatically. For a 330-node + 1500-internal-edge generated parser, the collapsed view is 1 node + boundary edges only.

The mode is **opt-in per query**, not the default. Per-symbol navigation tools (`code_callhierarchy`, `code_impact`, `code_graph_path`) keep the full graph by default because operators investigating specific generated symbols still need the internal granularity. Architectural views (`wave_graph_report`, dashboard graph render) get a `collapse_generated_files: bool` toggle that switches to the file-as-black-box view.

This change deliberately follows Change 5 — the `generated: true` tag from Change 5 is the input that collapse mode reads. Without Change 5, collapse mode has nothing to collapse.

## Requirements

1. **`collapse_generated_files: bool = False` parameter** on `wave_graph_report` and dashboard graph-render endpoints. Default `False` (full graph; matches existing behavior). Default `True` is OUT OF SCOPE — operators who want full graph by default keep it; those who want collapsed-by-default opt in per call.
2. **Collapse logic operates on the in-memory graph snapshot at query time.** No persistent index change; the classification tag from Change 5 is the only stored signal.
3. **Aggregation rules:**
   - Each unique generated file (per `source_file` field on nodes tagged `generated: true`) collapses to a single "file node" with `node_id = <source_file>`, `label = <basename>`, `kind = "module"`, `generated: true`, `collapsed_node_count: <N>` (how many symbol nodes were rolled up).
   - Edges where BOTH endpoints are in the same generated file are dropped.
   - Edges where ONE endpoint is in a generated file get the generated endpoint rewritten to the file node. The relation is preserved; the line/snippet info on the edge is dropped (it pointed at an internal symbol now hidden).
   - Edges where both endpoints are in *different* generated files get both endpoints rewritten to file nodes.
4. **`wave_graph_report` in collapse mode** runs all sections (`fan_in`, `fan_out`, `chokepoints`, `betweenness`, `communities`) over the collapsed graph. Per-section semantics unchanged; the underlying topology is just smaller.
5. **Per-symbol navigation tools are NOT affected.** `code_callhierarchy(symbol="ELParser.Statement")` continues to return the per-method symbol view because operators investigating specific generated symbols need it. `collapse_generated_files` is not a parameter on these tools.
6. **Dashboard graph view** gains a toggle (UI-level, scope tracked in the dashboard work, may land in a follow-up dashboard change). At the API level, the dashboard graph endpoint accepts the same parameter.
7. **No new regression tests required for navigation tools** (they don't change). New tests cover: (a) collapse aggregation correctness (`N` internal nodes → 1 file node), (b) edge rewrite correctness (handwritten→generated edges land on file node, internal edges dropped), (c) `wave_graph_report` section parity under collapse (no crashes; rankings make sense), (d) `collapsed_node_count` field present and accurate.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_query.py` (or `graph_cluster.py` — pick at implementation time based on where the collapse helper most naturally lives): new `_collapse_generated_view(nodes, edges) -> (nodes', edges')` helper.
- `.wavefoundry/framework/scripts/server_impl.py`: `wave_graph_report_response` accepts `collapse_generated_files: bool = False`. When True, applies the collapse before computing sections.
- MCP wrapper for `wave_graph_report` exposes the parameter.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`: regression tests covering aggregation, edge rewrite, section parity, `collapsed_node_count` field.

**Out of scope:**

- Persistent index change. The collapse is query-time only.
- `code_callhierarchy` / `code_impact` / `code_graph_path` / `code_callgraph` collapse support. These tools answer per-symbol questions where the collapsed view loses the answer.
- Default-on collapse. Always opt-in.
- Dashboard UI toggle — the API parameter is in scope; the dashboard surfacing follows separately.
- Cross-file generated-file collapse semantics for languages where generated files are split across many tiny files (e.g. JAXB-generated POJOs, one file per schema element). Defer until operator reports show whether the per-file collapse is too coarse or too fine.

## Acceptance Criteria

- [x] AC-1: `_collapse_generated_view(nodes, edges)` returns (`nodes'`, `edges'`) where each unique generated file is represented by ONE node with `node_id == source_file`, `kind == "module"`, `generated: True`, `collapsed_node_count: <N>` reflecting how many tagged nodes were rolled into it.
- [x] AC-2: Edges with BOTH endpoints in the same generated file are dropped from `edges'`.
- [x] AC-3: Edges with one endpoint in a generated file have the generated endpoint rewritten to the file node id. Relation and confidence preserved.
- [x] AC-4: Edges with both endpoints in DIFFERENT generated files have both endpoints rewritten.
- [x] AC-5: `wave_graph_report_response` accepts `collapse_generated_files: bool = False`. When True, applies `_collapse_generated_view` before computing all sections. All sections produce sensible output on the collapsed graph (no crashes).
- [x] AC-6: MCP wrapper for `wave_graph_report` exposes `collapse_generated_files` and threads it through.
- [x] AC-7: Per-symbol navigation tools (`code_callhierarchy`, `code_impact`, `code_graph_path`, `code_callgraph`) do NOT accept `collapse_generated_files` — they always use the full graph.
- [x] AC-8: New regression tests cover AC-1 through AC-5. Existing tests continue to pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Implement `_collapse_generated_view` helper with the aggregation rules from AC-1 through AC-4
- [x] Add `collapse_generated_files` parameter to `wave_graph_report_response`
- [x] Apply collapse before report sections when flag is True
- [x] Update MCP wrapper signature + docstring
- [x] Add regression tests
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline aggregation rule — file becomes one node |
| AC-2 | required | Internal-edge drop is what shrinks the graph |
| AC-3 | required | External→internal edge rewrite preserves the "X calls into ELParser" signal |
| AC-4 | required | Cross-generated-file edge rewrite for repos with multiple generated parsers |
| AC-5 | required | The wave_graph_report integration — without it the helper has no consumer |
| AC-6 | required | MCP wrapper surface is how agents access the toggle |
| AC-7 | required | Defensive: per-symbol tools must continue to return the full per-symbol view |
| AC-8 | required | Regression coverage + no existing-test regressions |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Opt-in (`collapse_generated_files=False` default), not default-on | The full graph is the correct underlying truth; collapse is an abstraction over it. Operators investigating specific generated symbols (debugging the parser, tracing into JAXB output) need the per-symbol view. Default-on would silently hide answers from these queries | Default-on for `wave_graph_report` only (rejected — splits "report mode is collapsed, navigation mode isn't" into a mental-model footgun; cleaner to default off everywhere and let operators opt in) |
| 2026-05-31 | Query-time collapse over persistent index change | Persistent collapse would require re-indexing on policy change and removes operator ability to switch views per query. Query-time collapse is O(nodes + edges) on the in-memory snapshot — negligible for typical graph sizes | Persistent collapse during index build (rejected — locks in a one-view-fits-all and forces re-indexing for operators who change mind) |
| 2026-05-31 | Apply only to `wave_graph_report` in this change | Per-symbol tools (`code_callhierarchy`, `code_impact`) lose their answer if the queried symbol is hidden inside a collapsed file. Architectural-view tools (`wave_graph_report`) are where the noise actually hurts — that's where the collapse pays off | Apply to all graph tools (rejected — destroys per-symbol value for the collapsed-symbol case) |
| 2026-05-31 | Drop line/snippet info on rewritten edges | An edge from `Runtime.parse()` to `ELParser.java` (file node) no longer has a specific line in ELParser to point at — the internal method is hidden. Edge metadata that referred to internal positions becomes meaningless | Preserve original line/snippet (rejected — points at hidden symbol; confusing to operators who can't dereference it) |
| 2026-05-31 | Add as Change 5b in this wave rather than a follow-up wave | Operator direction during wave 130rj implementation: classify-and-filter (Change 5) + classify-and-collapse (5b = this change) are companion modes over the same `generated: true` tag. Shipping them in the same wave keeps the design intent legible and the operator experience coherent at release | Ship as a follow-up wave once Change 5 lands and operator feedback materializes (deferred but kept in the same wave per operator direction; would have lost design-intent context) |
| 2026-05-31 | Collapse by source file, not by community or other groupings | Source file is the unit operators reason about ("ELParser is generated"). Collapsing by community would conflate generated code with neighboring handwritten code; collapsing by classname adds complexity without clear win | Collapse by community (rejected — operators don't think in community-id terms). Collapse by classname (rejected — many generated files have one class anyway; doesn't shrink) |

## Risks

| Risk | Mitigation |
|---|---|
| Collapsed view confuses operators who don't realize they're seeing aggregated nodes | The collapsed node carries `collapsed_node_count: <N>` and `generated: true` — both visible in the response. Dashboard surfacing (out of scope here) should render collapsed nodes with a distinct visual treatment |
| Some generated codebases use many tiny files (e.g. one POJO per schema element) where per-file collapse is too fine | Defer per AC scope; operator reports would inform whether to add "collapse by generated directory" or similar coarser aggregation |
| Per-symbol tools don't get the collapse mode and may surface hairballs in `code_callgraph(depth>1)` traversals through generated code | `code_callgraph` is the explicit "I want depth" tool; operators using it already accept hairball output. Per-symbol tools could gain `collapse_generated_files` in a future change if reports surface that need |
| Edge rewrite collapses multiple internal edges into a single file-to-X edge, losing edge count semantics | Edges between distinct (src, tgt) pairs after rewrite are deduped to one edge. Fan-in/fan-out counts on the file node reflect unique external edges, not call multiplicity. Acceptable trade — the collapse mode is about topology, not multiplicity |

## Related Work

- Companion to `130rj-enh generated-code-classifier-and-filters` (Change 5) — consumes the same `generated: true` node tag. Change 5 must ship first; this change adds the collapse-mode view on top.
- Same wave: `130rj-enh seeds-pattern-library-and-recipes` (implemented), `130rj-enh graph-tool-shape-consistency` (implemented), `130rj-enh code-ask-fast-mode` (implemented), `130rj-enh aop-advice-empty-incoming-detection`, `130r7-bug java-method-reference-call-sites`.
- Future enhancement candidate: extend `collapse_generated_files` to per-symbol tools if operator reports surface that need.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
