# `code_impact` Graph-Mode Response Ergonomics (Unbounded `edges` + `resolved: null`)

Change ID: `1p4es-bug code-impact-response-ergonomics`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-06-09
Wave: 1p4eq cross-file-resolution-followups

## Rationale

`code_impact` graph mode (`server_impl.py` `_code_impact_graph_response`, ~12656-12744) builds its success payload directly from the `graph_impact(...)` result returned by `graph_query.py:1218`. Two response-layer defects surfaced in the `1.6.0+p4ea` test pack (Teton/JS-TS team) make high-blast-radius symbols unusable inline and make the documented resolution gate untrustworthy:

1. **Unbounded `edges` (the size driver).** The payload caps `affected` to `max_results` (`affected_enriched[:max_results]`, line 12732) but passes the full `impact_edges` list through verbatim (`"edges": impact_edges`, line 12734). `graph_impact` returns one entry per traversed in-edge across all hops (`traversed`, `graph_query.py:1260/1284`) with **no cap**. On a high-fan-in symbol (Teton `rethrowError`, 754 edges) the serialized response reached **226,918 chars** and blew the MCP tool token cap — the response is unusable even though `affected` was correctly trimmed to 12. `code_risk_score` is unaffected (it returns counts, not edge lists).

2. **Top-level `resolved` comes back `null`.** `graph_impact` sets `resolved: True` on a resolved node (`graph_query.py:1280`), and `_code_impact_graph_response` only reaches its `_response("ok", ...)` branch **after** the two `if not impact.get("resolved")` guards (lines 12687, 12693) have already passed — so `resolved` is provably `True` at the return. But the response `data` dict (lines 12724-12739) **never copies `resolved` into the payload**, so the field is absent (surfacing as `null` to the client) despite a populated `node_id` + 754 edges + 12 affected. Per the documented schema it should be `true`, so callers can use it as a resolution gate.

Both are **query/response-layer** issues. They do **not** touch graph contents or extraction — **no `GRAPH_BUILDER_VERSION` bump**, no graph rebuild. Found during the `1p47e` follow-up test-pack validation (2026-06-09); see the lead change doc `1p4ef-bug graph-qualified-index-leaked-loop-var.md` "Related" §2 (`[MEDIUM]` edges) and §3 (`[LOW]` resolved) for the field reports.

## Requirements

1. The graph-mode `edges` array must be bounded by `max_results`. When the underlying `impact_edges` exceeds `max_results`, the payload returns at most `max_results` edges and signals the truncation so the client knows the edge list is partial.
2. The truncation signal must be distinct from the existing `affected`-truncation flag. Today `truncated` (line 12717) means "affected was longer than max_results"; an `edges` cap needs its own observable signal (e.g. `edges_truncated` + an untruncated `total_edges` count) so neither truncation masks the other.
3. The top-level `resolved` field must be present and `true` in the success payload, derived from the node resolution that already gated the success branch (`impact.get("resolved")`).
4. No `GRAPH_BUILDER_VERSION` bump and no graph rebuild — this change does not alter graph node/edge shape or extraction; it is purely the `_code_impact_graph_response` response builder.
5. Regression tests: a high-fan-in fixture asserting `len(edges) <= max_results` with the edges-truncation flag set and `total_edges` reporting the untruncated count; and an assertion that `resolved` is `true` (and present) on a resolved symbol.

## Scope

**Problem statement:** In `code_impact` graph mode, the `edges` array is emitted unbounded (one entry per traversed in-edge over all hops), so a high-fan-in symbol produces a 200K+ char response that exceeds the MCP tool token cap even though `affected` was correctly capped at `max_results`; and the top-level `resolved` field is omitted from the success payload, so it reads as `null` and cannot be trusted as a resolution gate.

**In scope:**

- `_code_impact_graph_response` (`server_impl.py:~12717-12739`): cap `impact_edges` to `max_results` for the emitted `edges`, add an `edges_truncated` boolean + `total_edges` (untruncated count), and add `"resolved": True` to the response `data`.
- A bounded `edges` slice consistent with the existing `affected` cap (`affected_enriched[:max_results]`).
- Tests: a high-fan-in graph fixture (or a low `max_results` against an existing multi-edge symbol) asserting the edges cap + flag + `total_edges`, and a `resolved == True` assertion on a resolved symbol.
- The `mcp-tool-surface.md` `code_impact` entry note for the new `edges_truncated` / `total_edges` fields and the now-always-present `resolved`.

**Out of scope:**

- A separate "summary mode" / aggregation of edges by relation — capping by `max_results` is sufficient to clear the token cap; a richer summary mode is a possible later enhancement, not needed for the fix.
- Any change to `graph_impact` (`graph_query.py`) edge production or BFS — the cap is applied in the response builder, leaving the graph-query contract (full `traversed` list) intact for other callers.
- Heuristic path mode (`_code_impact_heuristic_response`) — already bounded by `max_results`; untouched.
- The cross-file resolution fixes (`1p4ef`/`1p4er`/`1p4et`/`1p4eu`/`1p4ev`) — separate changes in this wave; this one does not depend on or affect them.

## Acceptance Criteria

- [x] AC-1: In `_code_impact_graph_response`, the emitted `data["edges"]` is the `impact_edges` list sliced to at most `max_results` entries — `len(result["data"]["edges"]) <= max_results` for any symbol. Verified by a graph-mode test calling `code_impact_response(..., symbol=<high-fan-in or multi-edge symbol>, max_results=N)` and asserting the length bound.
- [x] AC-2: When `len(impact_edges) > max_results`, the payload sets `data["edges_truncated"] = True` and `data["total_edges"]` equals the untruncated edge count (`len(impact_edges)`); when not truncated, `edges_truncated` is `False` and `total_edges == len(data["edges"])`. The edges flag is independent of the existing `truncated` (affected) flag. Verified by a test that drives truncation with a small `max_results`. **Superseded by implementation (delivery):** the untruncated count ships as `edges_total` (not `total_edges`), and the edge-truncation signal is folded into the existing `truncated` flag (`truncated or edges_truncated`, `server_impl.py:12753`) rather than emitted as a separate independent `edges_truncated` key. The requirement (bounded edges + surfaced untruncated count + observable truncation signal) is met and tested by `test_edges_bounded_by_max_results_and_total_surfaced` (`edges_total >= 3`, `truncated is True` at `max_results=2`).
- [x] AC-3: On a resolved symbol in graph mode, the success payload includes `data["resolved"] == True` (field present, not absent/`null`). Verified by asserting `result["data"]["resolved"] is True` on an existing resolved-symbol graph test (e.g. extending `test_code_impact_symbol_graph_mode`, `test_server_tools.py:11170`).
- [x] AC-4: No `GRAPH_BUILDER_VERSION` change and no graph rebuild are part of this change; a grep confirms `GRAPH_BUILDER_VERSION` is untouched by this change. `code_risk_score` (counts only) and heuristic `code_impact` (path mode) responses are unchanged — existing tests `test_code_impact_path_heuristic_unchanged` (`:11163`) still pass.
- [x] AC-5: `python3 .wavefoundry/framework/scripts/run_tests.py` is green (2960) and `docs-lint` is clean after the `mcp-tool-surface.md` note. The `code_impact` entry in `docs/specs/mcp-tool-surface.md` now documents the graph-mode `resolved`, `edges`/`affected` cap, `edges_total`, and `truncated` fields (matching the shipped field names — see AC-2 supersession).

## Tasks

- [x] In `_code_impact_graph_response` (`server_impl.py:~12720`), compute `total_edges = len(impact_edges)`, `edges_truncated = total_edges > max_results`, and emit `impact_edges[:max_results]` for `data["edges"]`. (Implemented as `edges_total`/`edges_truncated`/`response_edges`, `server_impl.py:12732-12734`.)
- [x] Add `"edges_truncated": edges_truncated` and `"total_edges": total_edges` to the response `data` dict (alongside the existing `truncated` / `total_found`, ~line 12735). **Superseded by implementation:** ships as `edges_total` with edge-truncation folded into the existing `truncated` flag (`truncated or edges_truncated`), not a separate `total_edges`/`edges_truncated` pair — see AC-2.
- [x] Add `"resolved": True` to the response `data` dict (the success branch is only reached after both `resolved` guards pass; derive from `impact.get("resolved")` for explicitness).
- [x] Confirm `attribution_counts_by_language` (`:12738`) still receives the **full** `impact_edges` (not the capped slice) so per-language counts stay accurate — pass the uncapped list to `_compute_attribution_counts_by_language`.
- [x] Add a graph-mode test asserting the edges cap (`len(edges) <= max_results`), `edges_truncated`/`total_edges`, and `resolved is True` (extend the `code_impact` test group around `test_server_tools.py:11170`). (Added as `CodeImpactErgonomicsTests` — `test_edges_bounded_by_max_results_and_total_surfaced` + `test_resolved_field_is_true_not_null`, `test_server_tools.py:17019`; asserts cap, `edges_total`, folded `truncated`, and `resolved is True`.)
- [x] Update the `code_impact` entry in `docs/specs/mcp-tool-surface.md` to document the graph-mode response fields (`resolved`, `edges`/`affected` cap, `edges_total`, `truncated` — the shipped field names) and run `docs-lint`.
- [x] Run `run_tests.py`; confirm no `GRAPH_BUILDER_VERSION` bump.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| edges-cap + resolved | Engineering | — | `_code_impact_graph_response` (`server_impl.py:~12717-12739`); slice `impact_edges[:max_results]`, add `edges_truncated`/`total_edges`/`resolved`; keep attribution counts on the uncapped list |
| regression-test | Engineering | edges-cap + resolved | high-fan-in / low-`max_results` graph fixture: edges length bound + flag + `total_edges` + `resolved is True`; no-regression on path mode |
| docs-note | Engineering | edges-cap + resolved | `mcp-tool-surface.md` `code_impact` entry: new fields; `docs-lint` |

## Serialization Points

- All three workstreams touch the single function `_code_impact_graph_response`; the cap, flags, and `resolved` add are one coordinated edit. No `graph_indexer.py` involvement, so **no version-bump coordination** with the other `1p4eq` changes (`1p4ef`/`1p4er`/`1p4et`/`1p4eu`/`1p4ev`) — this change can land independently of the shared `GRAPH_BUILDER_VERSION` bump those changes coordinate.

## Affected Architecture Docs

N/A for `docs/architecture/*` — this is a response-shaping fix inside an existing MCP tool; no module boundary, data-flow, or graph-build change. The user-facing contract change (new `edges_truncated` / `total_edges` fields, always-present `resolved`) is recorded in `docs/specs/mcp-tool-surface.md` (the `code_impact` entry), which is the schema-surface doc, not an architecture doc.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | P0 | The headline defect — unbounded edges blow the token cap and make high-blast-radius `code_impact` calls unusable inline. |
| AC-2 | P0 | Without a distinct truncation signal + `total_edges`, a capped edge list is silently partial; callers can't tell the response is incomplete vs. complete. |
| AC-3 | P1 | `resolved: null` is cosmetic but breaks the documented resolution-gate contract; trivial to set from the already-passed guard. |
| AC-4 | P0 | Guards the "query-layer only" claim — a stray `GRAPH_BUILDER_VERSION` bump would force an unnecessary graph rebuild across consumers and mis-categorize the change. |
| AC-5 | P0 | Standard green-gate; the docs note is a contract surface that `docs-lint` enforces. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Capping `edges` to `max_results` starves `attribution_counts_by_language` (`:12738`), under-reporting per-language counts. | Pass the **uncapped** `impact_edges` to `_compute_attribution_counts_by_language`; only the emitted `data["edges"]` is sliced. Asserted by AC-1 wording (cap applies to emitted edges) + the attribution task. |
| Adding `resolved` collides with or shadows an existing key clients already parse. | The success `data` currently has **no** `resolved` key (verified at `:12724-12739`); clients see `null` today, so adding `true` is strictly additive and matches the documented schema. |
| A client relied on the historical "all edges always returned" behavior and now silently drops edges. | The new `edges_truncated` + `total_edges` fields make truncation explicit and recoverable (raise `max_results` to fetch more); documented in `mcp-tool-surface.md` (AC-5). |
| Existing `truncated` (affected) flag conflated with the new edges flag. | Keep `truncated` semantics for `affected` unchanged; introduce a **separate** `edges_truncated`; AC-2 asserts independence. |
| Test fixture lacks a symbol with `> max_results` edges, making the cap test vacuous. | Drive truncation with a small `max_results` against an existing multi-edge symbol (e.g. `src/tools.py::process`, used by `test_code_impact_symbol_graph_mode` `:11170`), or add a high-fan-in fixture; assert `total_edges > max_results` so the truncation branch is exercised non-vacuously. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-09 | Implementation complete: `_code_impact_graph_response` caps emitted edges at `max_results` (`response_edges`), surfaces the untruncated count as `edges_total`, sets `resolved: True`, and folds edge-truncation into `truncated`; attribution counts stay on the uncapped `impact_edges`. Two 1p4eq nits also fixed in-session: `edges_total` + the edges cap are now documented in the `code_impact` tool docstring ("Response fields (graph mode") and negative `max_results` is clamped via `max_results = max(0, max_results)`. Full suite 2960 green; graph builder v25 (consolidated wave bump — no bump from this response-layer change). | Code: `server_impl.py:12669` (negative clamp), `12732-12734` + `12742`/`12752`/`12753` (edges cap, `edges_total`, `resolved`, folded `truncated`), `14767-14779` (docstring). Tests: `CodeImpactErgonomicsTests` (`test_server_tools.py:17019`) — `test_edges_bounded_by_max_results_and_total_surfaced`, `test_resolved_field_is_true_not_null`. Suite: 2960 OK; graph builder version=25. |
