# Confidence-weighted blast radius / risk (code_impact, code_risk_score)

Change ID: `1p5l4-bug confidence-weighted-blast-radius-risk`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-14
Wave: `1p5dk 1-6-release-hardening`

## Rationale

Surfaced by downstream **Aceiss/javaagent** (Java, 519 indexed files) in two independent smoke tests of pack `1.6.0+p5ky`: `code_risk_score(scope="custom/.../javaagent/")` ranked `ApplicationToken.getKey` **#1** (risk 37.4, `affected_file_count` 17, `fan_in` 8) — 12× the runner-up (3.1). The rank is a **name-collision artifact**. `code_references("getKey", exclude_tests=true)` shows only **2 of 9** call sites are the real `ApplicationToken.getKey()` (both correctly `RECEIVER_RESOLVED`: `AceissAutoConfiguration.java:382,393`); the other 7 are `Map.Entry.getKey()` / generic `getKey()` on unrelated maps (ReflectionUtil, Util, JSON, ImportHandler, JdbcUserListJob, SmokeTest) — a *different symbol* sharing the method name, all tagged `EXTRACTED` (heuristic name-based fallback that can't disambiguate receiver type).

The disambiguation signal is fully present in the data — each edge carries `confidence` (`RECEIVER_RESOLVED`/`CONSTRUCTION_RESOLVED` vs `EXTRACTED`), and the tool docstrings already advise "filter to RECEIVER_RESOLVED + CONSTRUCTION_RESOLVED for refactor-safety." The defect is that **`code_impact.affected_file_count` and `code_risk_score.risk` are computed over all edges at full weight**, so ubiquitous accessor names (`getKey`/`getValue`/`getName`/`toString`/`run`/`invoke`) routinely top a module's risk ranking for the wrong reason on real polyglot/idiomatic-Java repos. This is the **same low-trust `EXTRACTED` edge class** that wave `1p41l` found *under*-counting cross-file reach on Python (session-7 quality log) — opposite symptom, same root: name-based edges must not be weighted equal to type-resolved edges in headline numbers.

Confirmed in code: `graph_query.py` `graph_impact` (the reverse-`calls` BFS) ignores `confidence` entirely; `risk_score` counts `fan_in` over all `calls` edges and multiplies the raw `affected_file_count`. The fix is **query-layer arithmetic only** — the per-edge `confidence` is already on each edge dict and `graph_impact` already returns the traversed `edges`. No chunk/graph shape change → **no `GRAPH_BUILDER_VERSION`/`CHUNKER_VERSION` bump**.

## Requirements

1. `code_risk_score` weights `EXTRACTED` edges *fractionally* (not zero — `1p41l` showed `EXTRACTED` is sometimes the only cross-file signal) when computing both the blast-radius file count and `fan_in`, and ranks on the weighted composite. `RECEIVER_RESOLVED`/`CONSTRUCTION_RESOLVED` keep full weight. The down-weight factor is a single named constant so it is tunable and auditable.
2. A file reached **only** via `EXTRACTED` edges contributes its fractional weight to blast radius; a file reached by at least one resolved edge counts in full (max-confidence-per-file attribution).
3. Each `code_risk_score` result surfaces a confidence breakdown so a high-but-mostly-`EXTRACTED` score is visibly discountable without a second `code_references` call: `extracted_edge_fraction` plus the raw, un-weighted `affected_file_count` and `fan_in` (so the weighted vs raw delta is transparent) and the weighted values that drive the rank.
4. The `score_formula` / `score_components` strings in the response and the tool docstrings (`code_risk_score`, and the `code_impact` confidence note) describe the weighted model accurately. No silent behavior the docs don't state.
5. **No regression** to the `1p41o`/`1p41l` value gate (the AC-8 degeneracy check — risk must not collapse to a pure `fan_in` proxy) nor to the `1p4hj` AC-10 retrieval eval (untouched, but re-run as a tripwire). On the Aceiss repro, a confidence-resolved symbol must out-rank a collision-driven accessor.

## Scope

**Problem statement:** `code_impact`/`code_risk_score` fold heuristic `EXTRACTED` name-collision edges into headline blast-radius/risk at full weight, inflating the rank of trivial accessors that share a method name with unrelated symbols (e.g. `Map.Entry.getKey()`).

**In scope:**

- `graph_query.py`: `graph_impact` records per-affected-node max edge confidence weight + returns a confidence breakdown; `risk_score` computes weighted `affected_file_count` + weighted `fan_in`, recomputes `risk` on the weighted inputs, surfaces `extracted_edge_fraction` + raw + weighted components; a `_edge_confidence_weight` helper + `_EXTRACTED_EDGE_WEIGHT` constant.
- `server_impl.py`: `code_risk_score`/`code_impact` docstring response-field + formula updates.
- Regression tests (`test_graph_query.py` / `test_server_tools.py`): the Aceiss collision repro (resolved symbol out-ranks a name-colliding accessor), weighted-file-count attribution, `extracted_edge_fraction` correctness, AC-8 non-degeneracy re-check.
- Doc surfaces that document the response shape (`docs/specs/mcp-tool-surface.md`, guru seed-211 + rendered `guru.md` if they enumerate the fields), CHANGELOG.

**Out of scope:**

- A `min_confidence` floor on `code_risk_score` (operator chose down-weight + transparency, not the hard filter). `code_impact` keeps its existing `min_confidence`.
- The extractor itself — improving cross-file receiver resolution (`EXTRACTED` → `RECEIVER_RESOLVED`) is the durable fix but is a `GRAPH_BUILDER_VERSION` change, deferred.
- Re-weighting `code_graph_path` cost (already confidence-aware via `_path_edge_cost`).

## Acceptance Criteria

- [x] AC-1: On the Aceiss repro shape (a low-fan-in accessor whose in-edges are mostly `EXTRACTED` name collisions vs a confidence-resolved symbol), `code_risk_score` ranks the resolved symbol above the collision-driven accessor — `GraphQueryConfidenceWeightedRiskTests.test_resolved_symbol_outranks_collision_accessor` (synthetic graph mirroring `getKey`: raw blast radius would invert the rank, weighting flips it back). This is the gate for the fix.
- [x] AC-2: `code_risk_score` results carry `extracted_edge_fraction`, raw `affected_file_count`/`fan_in`, and the weighted values; `score_formula`/`score_components` + `extracted_edge_weight` and the tool docstrings describe the weighted model; the AC-8 non-degeneracy (live-graph dogfood: ranking is a genuine composite, not `fan_in` order) and the AC-10 eval (**11/11, exit 0**) both still pass. Adversarial faithfulness review (below) confirms the weighting narrows the rank for the right reason (confidence), not by silently dropping real `EXTRACTED` reach — raw counts are retained and the weight is fractional (0.25), not zero.

## Tasks

- [x] `_EXTRACTED_EDGE_WEIGHT` constant (0.25) + `_edge_confidence_weight(edge)` helper in `graph_query.py`.
- [x] `graph_impact`: track per-affected-node max edge weight (`confidence_weight`); return `confidence_counts` (receiver_resolved/construction_resolved/extracted over the traversal).
- [x] `risk_score`: weighted `affected_file_count` (max-confidence per file) + weighted `fan_in`; `risk = weighted_affected_file_count * log1p(weighted_fan_in)`; emit `extracted_edge_fraction`, raw + weighted components, `extracted_edge_weight`; update `score_formula`/`score_components`.
- [x] `server_impl.py` docstring updates (`code_risk_score` response fields + formula); `code_impact` already surfaces `attribution_counts_by_language` + now per-node `confidence_weight`.
- [x] Regression tests (4 new in `GraphQueryConfidenceWeightedRiskTests`; updated v1→v2 formula assertions in `test_graph_query` + `test_server_tools` wrapper) + re-ran `run_recall_eval.py` (11/11) + live-graph dogfood.
- [x] Adversarial faithfulness review (recorded in Decision Log); doc surfaces (`mcp-tool-surface.md`, seed-211 + `guru.md`) + CHANGELOG.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes                                              |
| -------------- | ----------- | ------------ | -------------------------------------------------- |
| graph-query    | Engineering | —            | weighting + breakdown in `graph_query.py`          |
| surface-tests  | Engineering | graph-query  | docstrings, tests, faithfulness review, docs/CHANGELOG |


## Serialization Points

- `graph_query.py` (`graph_impact` + `risk_score`) is the shared file; both tasks touch it — sequence graph-query before surface-tests.

## Affected Architecture Docs

`N/A` — query-layer scoring change; no graph/chunk contract, boundary, or data-flow change (the graph lane and edge schema are unchanged). Response-field additions are documented in `docs/specs/mcp-tool-surface.md` + the tool docstrings, not an architecture boundary.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale                                                                                          |
| ---- | -------- | -------------------------------------------------------------------------------------------------- |
| AC-1 | required | The collision-driven mis-rank is the user-facing defect; the rank-order regression test is the gate. |
| AC-2 | required | Transparency fields + accurate docs are half the fix (discountable scores); the AC-8/AC-10 + faithfulness re-checks guard against a silent narrowing. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-14 | Change admitted to 1p5dk (operator chose: fold in; scope = down-weight + transparency). Root cause confirmed in `graph_query.py` (`graph_impact` BFS + `risk_score` both confidence-blind); fix is query-layer only, no version bump. | `graph_query.py:1191,1263` |
| 2026-06-14 | **Implemented + verified.** `_EXTRACTED_EDGE_WEIGHT=0.25` + `_edge_confidence_weight`; `graph_impact` emits per-node `confidence_weight` + `confidence_counts`; `risk_score` ranks on `weighted_affected_file_count * log1p(weighted_fan_in)`, surfaces `extracted_edge_fraction` + raw + weighted components. Docstrings/spec/seed-211/guru.md/CHANGELOG updated. **Full suite 3125 OK**; AC-10 eval **11/11**; docs-lint clean. Live-graph dogfood (7,887 nodes): pure-heuristic symbols correctly down-weighted (`_file_stem` FI 31 → wFI 7.75, xEF 1.00), ranking a genuine composite (not `fan_in` order). | `graph_query.py`, `server_impl.py`, `test_graph_query.py`, `test_server_tools.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-14 | Down-weight `EXTRACTED` fractionally + surface `extracted_edge_fraction`; no hard `min_confidence` filter on `code_risk_score` | Operator choice. Fractional (not zero) keeps the real cross-file reach `1p41l` showed `EXTRACTED` sometimes uniquely provides, while stopping name collisions from dominating; transparency fields let a consumer discount without a second call. | (a) hard `min_confidence` filter on risk_score (rejected — drops real EXTRACTED reach); (b) transparency-only, no rank change (rejected — leaves the wrong default rank); (c) fix the extractor (deferred — `GRAPH_BUILDER_VERSION` change) |
| 2026-06-14 | **Faithfulness review: PASS.** Adversarial stance — does the weighting *silently narrow* the control (hide real blast radius) or change rank for the wrong reason? Checked: (1) `EXTRACTED` weight is **0.25, not 0** — an `EXTRACTED`-only blast radius still contributes and still ranks above a zero-reach symbol, so the session-7/`1p41l` "EXTRACTED is sometimes the only signal" case is preserved (a pure-heuristic symbol keeps a non-zero risk, confirmed in dogfood). (2) Raw `affected_file_count`/`fan_in` are **retained** alongside weighted values + `extracted_edge_fraction`, so nothing is hidden — a consumer can recompute the v1 score. (3) The rank flip is driven **only** by `confidence`, the documented disambiguator (oracle = the §H `code_references` ground truth: 2/9 real; the synthetic AC-1 test encodes exactly that shape and asserts the resolved symbol wins). (4) Per-file weight uses **max** confidence, so a file reached by even one resolved edge counts in full — the weighting never under-counts a genuinely-resolved file. No fail-open / silent-narrowing found. | Oracle: §H `code_references` 2/9-real ground truth + the AC-1 synthetic mirror; no external RE2-style oracle exists for risk scoring |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Down-weighting silently hides a real `EXTRACTED`-only blast radius (narrows the control wrongly) | Fractional weight (not zero) + raw `affected_file_count`/`fan_in` retained in output; adversarial faithfulness review before close |
| Weighted formula re-collapses risk to a `fan_in` proxy on graphs with little resolved structure | Re-run the `1p41o` AC-8 non-degeneracy gate; constant is tunable |
| Score magnitudes shift for all symbols, surprising existing consumers | `risk` is documented as a *relative rank within scope*, not an absolute; CHANGELOG notes the scoring change; raw components stay visible |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
