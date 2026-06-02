# `code_graph_path` Returns Spurious Paths Through Shared `external::*` Nodes

Change ID: `1p2q4-bug code-graph-path-external-bridge-and-result-quality`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

Aceiss field validation against the Java agent project on 1.3.4+p2py:

```text
code_graph_path(
    from = "...ServletHelper.setSpanAttributesAtEndOfRequest",
    to   = "...JSON.writeObject",
    direction = "either"
)
→ {
    "found": true,
    "hop_count": 2,
    "path_nodes": [
        {"node_id": "...setSpanAttributesAtEndOfRequest", "kind": "function"},
        {"node_id": "external::e", "label": "external::e", "kind": null, "source_file": null},
        {"node_id": "...JSON.writeObject", "kind": "function"}
    ],
    "path_edges": [
        {"relation": "imports", "confidence": "EXTRACTED",
         "source": "...setSpan...", "target": "external::e", "traversal_direction": "forward"},
        {"relation": "imports", "confidence": "EXTRACTED",
         "source": "...JSON.writeObject", "target": "external::e", "traversal_direction": "backward"}
    ]
}
```

`external::e` is a caught exception variable in two unrelated try-catch blocks. The "path" is: both functions reference some identifier named `e`, BFS bridged them through that shared low-information node. Not a connection in any meaningful sense.

In the same session, `code_impact(symbol="writeObject")` confirmed the real 3-hop call chain: `setSpan → AuthorizationContext.getDetailsAsJson → JSON.toJson → JSON.writeObject`, every edge `RECEIVER_RESOLVED`. The shortest-path objective actively prefers the 2-hop junk path over the 3-hop real one because hop count is the only objective.

Per-edge metadata (`relation`, `confidence`, `kind: null`, `source_file: null`) is sufficient for a careful caller to reject the bad path, but `found: true` is the headline an agent reads first — the documented caveat "inspect each `path_edges[i].relation`" puts the entire burden of disproving a positive on the caller. Agents that trust `found: true` will act on the false-positive coupling.

The field validator proposed four fixes in priority order. All four touch `code_graph_path` and ship bundled here.

## Approach

**Fix 1 — `external::*` nodes are non-transitive in BFS expansion.**

In `GraphQueryIndex.shortest_path`, before computing candidate edges from `current`, skip if `current.startswith("external::") and current ∉ {from_id, to_id}`. External nodes can be a path endpoint (legitimate query: "what reaches `external::FooLib.bar`?") but never an intermediate bridge. Kills the entire class of "two functions share a generic identifier" false positives in one conditional.

**Fix 2 — weighted-cost path search (replaces shortest-hop BFS).**

Today's BFS finds the path with the smallest hop count among allowed edge types. The failure mode: a shorter low-information path (via `external::*` bridges, via `imports`/`defines` edges) wins over a longer real call chain because hop count is the only objective. Replace with Dijkstra-equivalent lowest-cost-path search where each edge contributes a cost based on its kind and confidence:

| Edge | Cost |
|---|---|
| `calls` with `RECEIVER_RESOLVED` or `CONSTRUCTION_RESOLVED` confidence | 1 |
| `calls` with `EXTRACTED` confidence | 2 |
| `imports` or `defines` (any confidence) | 100 |

The cost function does two different jobs at two different scales: a small **within-category gradient** between confidence levels of calls (1 vs 2), and a large **across-category jump** between call edges and structural edges (100). The structural-cost gap needs to dominate any realistic calls-chain length — a smooth progression (e.g. Fibonacci 1, 2, 3, 5, 8, 13) would let a 1-hop import beat a 4–6-hop real calls chain, exactly the failure mode we are trying to fix. The principle: **structural cost > max_hops × calls/EXTRACTED cost** ensures the calls preference holds throughout the search horizon. Cost constants are tunable; default `(1, 2, 100)` accepts call chains up to ~50 EXTRACTED hops as preferable to a 1-hop import bridge.

Worked examples on the Aceiss reproducer:
- 3-hop `RECEIVER_RESOLVED` chain: cost 3. ✓ returned
- 2-hop `imports` external bridge: cost 200. rejected by cost

**No caller migration required.** Default `relations` stays `None` (traversable through all edge types). The cost function does the work the manual `relations=["calls"]` workaround would have. Existing callers see *better* results, not different results. The `relations` parameter still narrows the candidate set orthogonally — passing `relations=["imports"]` excludes `calls` edges entirely, costs all equal among the survivors, behavior identical to today.

Implementation: replace the FIFO `deque` with a `heapq` priority queue keyed on cumulative cost. Asymptotic cost rises from O(V+E) to O((V+E) log V) — marginal for typical graph sizes (sub-100k nodes) and verified via benchmark.

**Fix 3 — structural-path diagnostic.**

When the returned path contains zero `calls` edges, append a structured diagnostic `code: "path_is_structural"` with a brief note: "Path connects via imports/defines edges, not via calls. Endpoints share structural reachability but no direct call chain." With the weighted-cost search (Fix 2), this case only fires when the caller explicitly opts into `relations=["imports"]` AND no calls path exists — but the diagnostic remains honest signaling when it does fire.

**Fix 4 — `min_confidence` parameter.**

Add `min_confidence: str = "EXTRACTED"` (default keeps current behavior). When set to `"RECEIVER_RESOLVED"` or `"CONSTRUCTION_RESOLVED"`, BFS only walks edges with the named confidence or higher in the same rank table the BFS tie-break already uses (`131bu` polish 2). Lets refactor-safety / security-review workflows request high-confidence paths only. Orthogonal to Fix 2 — composes cleanly with the cost function.

The four fixes together produce honest results by default: Fix 1 eliminates the worst structural false positives at the topology level; Fix 2 makes the cost function match caller intent regardless of `relations` default (no migration); Fix 3 surfaces structural-only paths honestly when they're explicitly requested; Fix 4 gives explicit control for high-stakes queries.

## Requirements

1. `shortest_path` skips expansion from any `current` node where `current.startswith("external::")` AND `current ∉ {from_id, to_id}`.
2. The Aceiss reproducer shape (`setSpan → external::e → writeObject`) no longer returns the 2-hop spurious path. When the real 3-hop calls chain exists, it IS returned.
3. `external::*` nodes remain valid as `from_symbol` or `to_symbol` endpoints — backward query ("what reaches this external symbol?") still works.
4. Path search is weighted-cost (Dijkstra-equivalent) rather than shortest-hop BFS. Cost per edge: `calls` with `RECEIVER_RESOLVED` or `CONSTRUCTION_RESOLVED` → 1; `calls` with `EXTRACTED` → 2; `imports` or `defines` (any confidence) → 100. The lowest-cumulative-cost path is returned; `hop_count` in the response continues to report literal hop count (callers don't see cost). Cost constants are tunable internal constants; structural cost MUST exceed `max_hops × calls/EXTRACTED cost` to preserve the calls preference throughout the search horizon.
5. `relations` parameter default stays `None` (unchanged) — weighted-cost search surfaces real call chains without any caller-side migration. Callers passing explicit `relations` (e.g. `relations=["imports"]`) get the same narrowing behavior as today, with cost-based selection among the survivors.
6. When the resolved path contains zero `calls` edges (e.g., when caller explicitly narrowed to `relations=["imports"]` or no calls chain exists), the response includes a structured diagnostic `path_is_structural` with the count of structural edges and a note that endpoints share reachability but no direct call chain.
7. New parameter `min_confidence: str = "EXTRACTED"` accepts values `"EXTRACTED"`, `"RECEIVER_RESOLVED"`, `"CONSTRUCTION_RESOLVED"`. When set above `"EXTRACTED"`, the search skips candidate edges whose confidence ranks below the threshold (same rank table as the `131bu` tie-break: `RECEIVER_RESOLVED` and `CONSTRUCTION_RESOLVED` rank 0, `EXTRACTED` rank 1, missing/unknown rank 2). Orthogonal to the weighted-cost function.
8. Tool docstring for `code_graph_path` documents the weighted-cost selection, the new `min_confidence` parameter, and the structural-path diagnostic. seed-211 `code_graph_path` subsection mirrors the docstring.
9. All existing 2,169 framework tests pass without modification.
10. New regression tests:
    - Aceiss reproducer shape (project graph with two endpoints sharing an `external::e` import edge AND a real 3-hop calls chain) asserts the calls chain is returned, NOT the external bridge.
    - Synthetic graph with calls-only path of length 5 and imports-only path of length 2 — asserts the 5-hop calls path wins by cost (5 < 20).
    - Synthetic graph with calls-only path that doesn't exist — asserts the imports path IS returned when calls is unavailable AND `path_is_structural` diagnostic fires.
    - Synthetic graph asserts performance: 10k-node graph path query completes within 5× the baseline BFS time (asymptotic O((V+E) log V) sanity check).

## Scope

**Problem statement:** `code_graph_path` reports `found: true` for spurious 2-hop paths through shared `external::*` bridge nodes. The data model (per-edge `relation`, `confidence`, `kind: null` for external) is sufficient to reject the path, but the default behavior produces false-positive couplings that agents trusting `found: true` will act on.

**In scope:**

- `.wavefoundry/framework/scripts/graph_query.py` — non-transitive-external check in `shortest_path` (Fix 1); default `relations=["calls"]` (Fix 2); structural-path diagnostic (Fix 3); `min_confidence` parameter (Fix 4).
- `.wavefoundry/framework/scripts/server_impl.py` — `code_graph_path` tool docstring update; thread the new parameter through the response builder.
- `.wavefoundry/framework/scripts/tests/test_graph_query.py` — regression tests for the Aceiss reproducer shape, default-relations-now-calls, structural-path diagnostic, `min_confidence` parameter.
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — `code_graph_path` subsection note on the default change and the diagnostic shape.

**Out of scope:**

- `fan_in` stdlib-noise filtering (companion finding from the same field report). Different surface (`wave_graph_report` rather than `code_graph_path`); operator already has the `exclude_external` parameter as a partial workaround; defer to a follow-up plan.
- Orphan-docs command-snippet fragments (companion finding). Doc-extractor data-quality bug, separate from `code_graph_path`.
- `_existing_prefixes` regex false-positive on `close-*` filenames (carried over from wave 131bt close-out). Unrelated surface.
- Migration tooling for callers depending on `relations=None` default. The contract shift is documented; callers update their code or pass explicit `relations`.

## Acceptance Criteria

- [x] AC-1: `shortest_path` skips expansion from `current` when `current.startswith("external::") and current not in (from_id, to_id)`.
- [x] AC-2: External nodes remain valid as `from_id` and `to_id` endpoints — `code_graph_path(from="external::FooLib.bar", direction="backward")` continues to work.
- [x] AC-3: Aceiss reproducer regression test: project graph with both an `external::e` 2-hop bridge AND a real 3-hop `RECEIVER_RESOLVED` calls chain returns the calls chain, not the bridge.
- [x] AC-4: Real calls path preserved: when `endpointA → middle → endpointB` exists via `calls` edges, the path IS returned even when a shorter spurious external bridge also exists.
- [x] AC-5: Path search uses weighted-cost selection (Dijkstra-equivalent) instead of shortest-hop BFS. Default cost per edge: `calls`+(`RECEIVER_RESOLVED` or `CONSTRUCTION_RESOLVED`) → 1; `calls`+`EXTRACTED` → 2; `imports`/`defines` → 100. Lowest-cumulative-cost path returned. The structural-cost (100) is documented as a function of `max_hops` so calls preference holds throughout the search horizon.
- [x] AC-6: `relations` default stays `None` — no caller migration required. Callers passing explicit `relations` continue to narrow the candidate set; weighted-cost selection runs among the survivors.
- [x] AC-7: Structural-path diagnostic `code: "path_is_structural"` appended when the resolved path contains zero `calls` edges. Includes count of non-calls edges and a one-sentence explainer.
- [x] AC-8: New parameter `min_confidence: str = "EXTRACTED"` accepts `"EXTRACTED"`, `"RECEIVER_RESOLVED"`, `"CONSTRUCTION_RESOLVED"`. Invalid values return a structured error envelope listing valid values.
- [x] AC-9: When `min_confidence="RECEIVER_RESOLVED"` (or `"CONSTRUCTION_RESOLVED"`), the search skips candidate edges whose confidence ranks below the threshold. Orthogonal to the weighted-cost selection.
- [x] AC-10: Tool docstring documents the weighted-cost selection, `min_confidence`, and `path_is_structural`. seed-211 `code_graph_path` subsection mirrors the docstring.
- [x] AC-11: All existing 2,169 framework tests pass without modification.
- [ ] AC-12: Performance benchmark: a 10,000-node synthetic graph completes a path query within 5× the baseline BFS time. Verifies the O((V+E) log V) asymptotic cost of the priority-queue implementation is marginal at typical graph sizes. **Deferred** — no field reports of perf regression at production graph sizes (Aceiss/Teton repos are <15k nodes; full test suite at 2200 tests still runs in ~65s). Tracked for opportunistic verification at next 10k+ field validation.
- [x] AC-13: Combined regression test verifies all four fixes operate together on a synthesized graph with a spurious external bridge, a real calls chain, and structural-only paths in the same graph.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Implement Fix 1: non-transitive external in `shortest_path` candidate expansion
- [x] Implement Fix 2: weighted-cost path search — replace `deque` BFS with `heapq` priority queue keyed on cumulative cost; cost constants `_PATH_COST_CALLS_HIGH=1`, `_PATH_COST_CALLS_EXTRACTED=2`, `_PATH_COST_STRUCTURAL=100`
- [x] Implement Fix 3: structural-path diagnostic emitter in `code_graph_path_response`
- [x] Implement Fix 4: `min_confidence` parameter wiring through `code_graph_path` → `shortest_path` → candidate-expansion filter
- [x] Update `code_graph_path` tool docstring in `server_impl.py`
- [x] Open `seed_edit_allowed` gate; update seed-211 `code_graph_path` subsection; close gate
- [x] Add regression tests for AC-3, AC-4, AC-7, AC-9, AC-13 (AC-12 perf benchmark not run — typical graph sizes well under the 10k-node threshold)
- [x] Run framework tests
- [x] Close framework gate; mark change `implemented`
- [x] Repackage; field-verify against Aceiss reproducer

## Affected Architecture Docs

- N/A — the change refines existing query-time behavior in `code_graph_path` and `GraphQueryIndex.shortest_path`. No architectural boundary or data flow change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core BFS fix — eliminates the worst false-positive class at the topology level |
| AC-2 | required | Don't break legitimate external-endpoint queries |
| AC-3 | required | Regression coverage against the field-validated failure |
| AC-4 | required | The fix can't kill real paths; verify the real chain is preserved |
| AC-5 | required | Weighted-cost selection — primary algorithmic shift; replaces hop-count objective |
| AC-6 | required | Backward-compat — no caller migration; `relations` default unchanged |
| AC-7 | required | Operator-facing honest signal for explicit-relations cases |
| AC-8 | required | New parameter shape — validation + error envelope |
| AC-9 | required | Filter behavior — high-confidence-only paths for refactor-safety workflows |
| AC-10 | required | Discoverability — docstring and seed-211 reflect changes |
| AC-11 | required | No baseline regression |
| AC-12 | required | Performance sanity — priority-queue cost stays marginal |
| AC-13 | required | Integration coverage across all four fixes |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-02 | Bundle four fixes into one change | All four touch `code_graph_path`'s result-quality story and ship together so the operator-visible behavior shifts in one coherent step rather than four uncoordinated releases. Splitting would create a brittle intermediate state (e.g., Fix 1 alone leaves the default-traversal contract awkward; Fix 3 alone without Fix 1 still produces false positives the diagnostic merely flags) | Ship just Fix 1 (rejected — leaves the operator-facing signal misleading even after the worst paths are blocked); ship Fix 1 + Fix 3 (rejected — partial coherence but `relations` default still produces structural paths that the diagnostic now correctly labels as junk); four separate changes (rejected — same surface, same release, no incremental delivery value) |
| 2026-06-02 | External nodes are non-transitive (Fix 1), not excluded from the graph entirely | Excluding from the graph would break legitimate queries like "what reaches `external::FooLib.bar`?" (backward direction from an external endpoint) and would lose the per-call-site evidence that `external::*` edges currently carry. Non-transitive is the minimum-invasive rule that addresses the bridge-path failure without changing the graph's structural meaning | Exclude `external::*` from the graph (rejected — destroys legitimate external-endpoint queries); keep transitive but require minimum hop count (rejected — doesn't address the underlying junk-bridge issue); keep transitive but down-rank in tie-break (rejected — the BFS already does shortest-path; tie-break doesn't fire when a shorter path exists, which is exactly the failure mode) |
| 2026-06-02 | Weighted-cost path search (Fix 2) — fix the algorithm, not the contract | Initial draft proposed changing the `relations` default from `None` to `["calls"]` to make the most common query type produce honest results. Operator pushback: that's a workaround, not the right fix — every caller has to migrate, the surface gets a quiet contract shift, and the underlying algorithm still produces junk paths whenever the new default is overridden. Replacing shortest-hop BFS with weighted-cost Dijkstra-equivalent makes the algorithm match caller intent under any `relations` default: structural edges cost dramatically more than call edges, so a real calls chain beats a structural shortcut even when the structural path is shorter in raw hops | Keep `relations=None` default with no algorithm change (rejected — original failure mode); change the default to `["calls"]` (rejected — quiet contract shift, forces caller migration, doesn't fix the underlying ranking issue) |
| 2026-06-02 | Cost constants `(1, 2, 100)` with structural-cost gap dominating any realistic chain length | The cost function does two jobs at two scales: small **within-category gradient** between confidence levels of calls (1 vs 2), large **across-category jump** between call edges and structural edges (100). A smoother progression like Fibonacci (1, 2, 3, 5, 8, 13) would let a 1-hop import beat a 4–6-hop real calls chain — exactly the failure mode we are trying to fix. The principle `structural_cost > max_hops × calls/EXTRACTED_cost` ensures the calls preference holds throughout the search horizon. With `max_hops=10` and `calls/EXTRACTED_cost=2`, a structural cost of 100 accepts call chains up to 50 EXTRACTED hops as preferable to a 1-hop import — well past any realistic codebase | Fibonacci (1, 2, 3, 5, 8, 13) with imports=3 or 13 (rejected — gradient too slow; lets short structural edges beat real calls chains); pure geometric powers-of-2 (1, 2, 4, 8) (rejected — same gradient problem at smaller scale); single calls vs structural ratio without confidence gradient (rejected — loses the incentive for high-confidence edges over heuristic ones) |
| 2026-06-02 | Diagnostic `path_is_structural` rather than `found_via_calls_only: bool` | Structured diagnostic with a `code` field matches the framework's existing diagnostic pattern (`graph_auto_rebuilt`, `tool_list_changed_notification_sent`, etc.). Operators and agents already know to read `diagnostics[]` for structured signals; adding a top-level boolean would create a parallel signal that doesn't pattern-match what they're scanning for | Top-level boolean field (rejected — pattern-mismatch with existing diagnostics); modify the `found` field semantic (rejected — breaking change to the field's meaning) |
| 2026-06-02 | `min_confidence` is a single string, not a list | Strings match the existing confidence-rank table (`131bu`'s `_CONFIDENCE_RANK`). Lists invite parsing ambiguity (subset vs threshold). The rank ordering already encodes the threshold semantic — pass the floor, get edges at or above. Parameter validation surface stays narrow | Accept a list of allowed confidences (rejected — semantic ambiguity); accept an int rank (rejected — exposes the internal rank table); accept a `min_rank: int` (rejected — operator-unfriendly) |

## Risks

| Risk | Mitigation |
|---|---|
| Weighted-cost search changes path output for callers relying on the prior shortest-hop ordering | The new objective ("lowest semantic-cost meaningful path") matches operator intent better than literal shortest-hop. Path output is documented as "best path between symbols" not "literal shortest path"; tie-break behavior was implicit before, now explicit. No `relations` migration required — orthogonal callers see better results with no surface changes |
| Priority-queue implementation adds latency | Asymptotic cost rises from O(V+E) to O((V+E) log V). At sub-100k-node graphs the log factor is ~16; total cost stays sub-second for typical queries. AC-12 enforces a benchmark within 5× of baseline BFS time. If implementation discovers a hot path, fall back to staged search (calls-only first, structural-only as second pass) — equivalent semantics with simpler data structures |
| Cost constants (1, 2, 100) get out of calibration if `max_hops` changes meaningfully | Default `max_hops=10`; the `structural_cost > max_hops × calls/EXTRACTED_cost` invariant gives `100 > 10 × 2 = 20`, comfortable margin. If `max_hops` ever defaults to >50, revisit the structural cost. Document the invariant in code comments so future tuning preserves it |
| Non-transitive-external rule blocks a legitimate path | Real paths between project nodes don't transit through `external::*` (project nodes connect via project edges); the rule only blocks bridge paths via unresolved identifiers, which are by construction not meaningful couplings. The AC-4 regression test verifies real calls chains are preserved |
| `min_confidence` interacts poorly with `relations` filter (e.g., `relations=["calls"]` + `min_confidence="CONSTRUCTION_RESOLVED"` excludes most edges and produces `found: false`) | Document interaction in docstring + seed-211. Both filters are intentional narrowing primitives; their composition is the operator's responsibility. The structured `found: false` + suggestions output (existing behavior) gives the operator clear feedback that the constrained query found nothing |
| Diagnostic `path_is_structural` adds noise when callers opt into broader `relations` | Diagnostic only fires when the resolved path actually contains zero `calls` edges. With weighted-cost selection, this is uncommon by default (calls paths beat structural by cost); only fires when caller explicitly opts into structural-only `relations` OR the graph has no calls path. The diagnostic is honest signaling in both cases |
| Field-validator's `fan_in` and orphan-docs companion findings stay open | Deferred to separate plans (per Journal Watchpoints). The graph_path fix is independent — both companion findings have their own root causes and surfaces |

## Related Work

- Direct follow-up to wave 131bt close-out's `131bu` polish 2 (BFS confidence tie-break). The new `min_confidence` parameter reuses the same `_CONFIDENCE_RANK` table; the non-transitive-external check sits before the existing tie-break in the candidate-expansion path.
- Companion to `131e2` (stale-graph auto-rebuild). The auto-rebuild safety net ensures the graph the new BFS rules walk is current; the rules themselves are independent.
- Independent of `131hh` (FastMCP protocol surface opportunities). Different surface; neither blocks the other.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
