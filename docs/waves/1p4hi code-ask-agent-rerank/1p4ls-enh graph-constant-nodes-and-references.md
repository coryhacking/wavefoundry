# Graph Constant Nodes + Reference Edges

Change ID: `1p4ls-enh graph-constant-nodes-and-references`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-10
Wave: `1p4hi code-ask-agent-rerank`

## Rationale

The code graph models only **callable/structural** symbols — functions, methods, classes, modules — connected by `calls` / `imports` / `defines` edges. **Module-level constants and variables are not nodes, and there is no "reads/references" edge.** Confirmed live: `code_definition("RERANKER_MODEL")` → `graph_definitive_not_found` against the refreshed project graph.

This blind spot has concrete costs, several of which this wave hit directly:

- **`1p4hj` AC-10:** "what value/model/flag is X" queries can't be answered structurally — the `RERANKER_MODEL` constant under-ranked (rank 11) with no graph fallback. `1p4lr` patches the *ranking* with a text heuristic; this change makes the constant a **structural fact**.
- **`1p4hu` (graph signal):** can't surface a constant from its consumers because there is no node/edge to traverse to — its 1-hop is blind to `_get_reranker → RERANKER_MODEL`. This change gives `1p4hu` something to reach.
- **`code_impact` / blast-radius (the `1p41l`/`1p41o` finding):** changing a widely-read constant (a flag, a model name, a threshold) shows near-zero graph reach because constant reads are invisible. "What breaks if I change this constant?" is unanswerable.
- **General navigation:** "where is constant X defined?", "who reads flag X?" fall back to keyword search.

Adding constant nodes + `references` edges is the structural complement to `1p4lr`'s ranking heuristic. **Sequenced after `1p4lr` and before `1p4hu`** so `1p4hu` can consume the new edges.

## Requirements

1. **Constant/named-declaration nodes — ALL core supported graph languages.** The extractor emits graph nodes for module-/namespace-/class-level named constant declarations across **every language the graph already extracts symbols for** — **Python, JavaScript, TypeScript, Java, Kotlin, C#, Go, Rust, Swift, Ruby, PHP** (and C++ where the extractor supports it) — each via its existing mechanism (Python AST; tree-sitter for JS/TS/Java/C#; structural matchers for Go/Rust/Kotlin/Swift/PHP/Ruby). Capture the declared name and, where the RHS is a simple literal, the value. Per-language declaration forms (non-exhaustive): Python `UPPER_SNAKE =`; TS/JS top-level `const` (exported AND non-exported); Java `static final`; Kotlin `const val` / top-level `val`; C# `const` / `static readonly`; Go `const`; Rust `const` / `static`; Swift `let` / `static let`; Ruby `CONST =`; PHP `const` / `define()`. **Scoping follows the canonical Per-Language Constant Detection table in `1p4mf`** — detect by mechanism + scope; **casing gates ONLY Python** (Ruby via its grammar `constant` node); keyword languages (Go/C#/Swift/JS/TS/Kotlin/Java/Rust/PHP) are **NOT** casing-gated (`apiURL`/`MaxRetries`/`StatusOK` are real constants). The `1p4ls` **graph lane is BROADER** than `1p4mf`'s chunk lane: it additionally includes class/type-level constants, Kotlin bare top-level/object `val` (no `const`), and TS/Swift enum members as structural nodes — keep the lane delta documented.
2. **`references` (reads) edges — all core languages.** Emit a `references` edge from a function/method node to the constant node it reads, resolved for **same-scope** (module/namespace/class) constants and **explicitly imported** constants, in each supported language. Bounded; do not chase dynamic/computed access.
3. **`GRAPH_BUILDER_VERSION` bump (25 → 26) in the same change** — node/edge shape changes, so consumer graph caches must re-extract (per the established builder-version rule; see [[graph-builder-version-bump]]).
4. **Consumers surface constants:** `code_definition` resolves a constant name to its declaration node; `code_references` returns its readers; `graph_neighbors` (on `code_references`/`code_definition`) includes constants and `references` edges. A 1-hop from a reader function reaches the constants it reads.
5. **Faithful resolution (no wrong-twin binding):** a `references` edge binds only to a uniquely resolvable constant (same-module, or an unambiguous import); ambiguous/external references stay unresolved rather than binding a coincidental same-name constant — mirroring the `1p4eq` cross-file faithfulness discipline.

## Scope

**Problem statement:** Constants/module-variables are invisible to the graph (no nodes, no reference edges), so structural answers to "what value is X", "where is constant X", "who reads X", and constant-level blast radius are impossible — and `1p4hu`'s graph signal can't traverse to a constant from its consumers.

**In scope:**

- `graph_indexer.py`: constant/named-declaration node emission + `references` edge emission **across all core supported graph languages** (Python, JS/TS, Java, Kotlin, C#, Go, Rust, Swift, Ruby, PHP; C++ where the extractor supports it), each via its existing per-language mechanism, with same-scope + imported-constant resolution and the faithfulness gate.
- `GRAPH_BUILDER_VERSION` 25 → 26.
- Consumer surfacing: `code_definition`, `code_references`, `graph_neighbors` recognize constant nodes + `references` edges.
- `docs/architecture/graph-index-system.md` update (node kinds, the new `references` edge, constants; version table → 26).
- Value eval on the real project graph (constants resolvable; reader edges correct; no regression to existing attribution buckets).

**Out of scope (explicit follow-up candidates):**

- **`code_impact` / `code_risk_score` integration** (counting constant reads toward blast radius) — deferred to keep this change to *graph shape + navigation* and avoid perturbing risk-score calibration in the same step. Note the opportunity; gate it separately.
- Local-variable / parameter nodes (only module-level — and possibly class-level — named constants/vars).
- Cross-file constant resolution beyond explicit imports (no heuristic same-name binding — see Requirement 5).
- Languages the graph does NOT already extract symbols for (e.g. plain C, Scala, Objective-C if they are not in the current extractor set) — this change matches the existing graph language coverage, it does not expand the language set.

## Acceptance Criteria

- [ ] AC-1: **Constant nodes — all core languages.** Named constant declarations become graph nodes in **every core supported language** (Python, JS/TS, Java, Kotlin, C#, Go, Rust, Swift, Ruby, PHP), each carrying the name and, for simple-literal RHS, the value. `code_definition("RERANKER_MODEL")` (Python) resolves to the declaration node (no longer `graph_definitive_not_found`); **per-language fixtures** verify a constant declaration in each language produces a node.
- [ ] AC-2: **`references` edges — all core languages.** A function/method that reads a constant has a `references` edge to it (same-scope + imported), **in each core supported language**. `code_references("RERANKER_MODEL")` returns `_get_reranker` / `_rerank`; a 1-hop neighbor query from `_get_reranker` includes `RERANKER_MODEL`; **per-language fixtures** verify a reader→constant edge in each language.
- [ ] AC-3: **Version bump.** `GRAPH_BUILDER_VERSION` is 26; building against a 25 cache triggers a full re-extract (self-heal verified).
- [ ] AC-4: **Consumers.** `code_definition`, `code_references`, and `graph_neighbors` recognize constant nodes + `references` edges (queryable, labeled).
- [ ] AC-5: **Faithful resolution (per-language).** An ambiguous/external constant reference (same simple name in multiple modules, no import) stays unresolved — it does NOT bind a coincidental twin. Verified by adversarial tests across the core languages (mirrors `1p4eq`'s per-language faithfulness tests — each language with cross-file/cross-package ambiguity gets a "never binds the wrong twin" test).
- [ ] AC-6 (**VALUE GATE**): on the real project graph — `RERANKER_MODEL` and ≥2 other constants are graph-resolvable with correct reader edges; **no regression** to existing graph attribution buckets (`receiver_resolved`/`construction_resolved`/`extracted` counts) or existing `calls`/`imports`/`defines` query correctness. Recorded with before/after graph stats.
- [ ] AC-7: **Architecture doc.** `graph-index-system.md` documents constant nodes + the `references` edge + the node-kind set; version table → 26.

## Tasks

- [ ] Constant/named-declaration node emission in `graph_indexer.py` **across all core supported languages** (Python AST; tree-sitter for JS/TS/Java/C#; structural matchers for Go/Rust/Kotlin/Swift/PHP/Ruby) — declared name + simple-literal value, per-language declaration forms.
- [ ] `references` edge emission **across all core languages** (function body reads a constant) — same-scope + imported resolution, with the faithfulness gate (Requirement 5 / AC-5).
- [ ] Per-language fixtures (one per core language) covering constant-node emission, a reader→constant `references` edge, and the wrong-twin faithfulness case (AC-1/AC-2/AC-5).
- [ ] `GRAPH_BUILDER_VERSION` 25 → 26 (same change).
- [ ] Consumer surfacing: `code_definition` / `code_references` / `graph_neighbors`.
- [ ] Tests: node emission, reference resolution, faithfulness (AC-5), version-bump self-heal.
- [ ] AC-6 value eval on the real graph (resolvable constants; reader edges; no bucket regression) + `graph-index-system.md` update.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| const-node-emission | Engineering | — | `graph_indexer.py` Python AST first |
| references-edge-resolution | Engineering | const-node-emission | same-module + imported; faithfulness gate |
| version-bump + consumers | Engineering | references-edge-resolution | `GRAPH_BUILDER_VERSION` 26; `code_definition`/`code_references`/neighbors |
| tests + AC-6 value eval | Engineering | version-bump + consumers | real-graph stats, no-regression |


## Serialization Points

- **`graph_indexer.py`** — graph-builder change; coordinates with any in-flight extractor work. Independent *file* from `search_combined`, but the `GRAPH_BUILDER_VERSION` bump forces a full graph rebuild for all consumers on upgrade.
- **Sequencing:** land **after `1p4lr`** (independent mechanism, but keeps the wave's "constants" work grouped) and **before `1p4hu`** (so `1p4hu`'s graph signal can traverse the new `references` edges to constants).

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — **required** (node kinds, the new `references` edge relation, constant nodes, version table 25 → 26). Possibly `data-and-control-flow.md` if the navigation-tool surface description enumerates edge types.

## AC Priority


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | Constant nodes are the core deliverable (the structural fact). |
| AC-2 | required   | `references` edges are the core deliverable — the reach `1p4hu` needs. |
| AC-3 | required   | The `GRAPH_BUILDER_VERSION` bump is mandatory for consumer cache-rebuild correctness. |
| AC-4 | required   | Constants must be queryable via the consumers to deliver any value. |
| AC-5 | required   | Faithfulness guard — coincidental same-name binding is the dominant wrong-edge failure (`1p4eq`). |
| AC-6 | required   | The value gate — must not regress existing graph attribution buckets / query correctness. |
| AC-7 | important  | Architecture doc keeps the graph reference truthful (node kinds + the new edge + version). |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-10 | **Scoped (write-up; not yet implemented).** Operator directive: do `1p4lr` first, write up this change and add to the wave; both before `1p4hu`. Motivated by the live finding that constants are absent from the graph (`code_definition("RERANKER_MODEL")` → `graph_definitive_not_found`), which blocks structural "what value is X" answers, constant blast-radius, and `1p4hu`'s reach to constants. | `code_definition` probe; `graph_indexer.py` node-kinds (code/module/seed) + edges (calls/imports/defines) audit; [[project-mcp-code-tool-quality-log]] session 8. |
| 2026-06-10 | **Scope expanded to ALL core supported graph languages** (operator directive) — Python, JS/TS, Java, Kotlin, C#, Go, Rust, Swift, Ruby, PHP (C++ where supported), NOT Python-first. Each reuses its existing extractor mechanism (AST/tree-sitter/structural); per-language fixtures + faithfulness tests (AC-1/AC-2/AC-5). | Operator message; canonical set from `_ATTR_LANG_BY_EXTENSION` (`server_impl.py:12202`) + the per-language graph extractors (`_extract_simple_{java,kotlin,csharp,swift,ts,php}_type_name`). |
| 2026-06-10 | **Prepare-council must-fixes (READY-WITH-FIXES) — fold in before implementing.** (1) **Cluster layer:** the new relation is absent from `graph_cluster.py:59-64 _RELATION_WEIGHTS`; decide whether constants/`reads` edges participate in clustering and if so bump `CLUSTER_BUILDER_VERSION` (clusters go stale on a graph-shape change) — extend AC-6 to assert no `code_graph_community` label regression. (2) **Constant fan-out:** `one_hop_neighbors` (graph_query.py:1041) traverses ALL relations by default, so a hot constant becomes a high-degree hub ballooning every 1-hop (incl. `1p4hu`'s expansion) — make the new relation **opt-in** for default traversal (mirror `_DEFAULT_IMPACT_RELATIONS` at graph_query.py:21, which excludes it by construction) + add a degree/neighbor-size bound AC. (3) **Cross-kind resolution:** `resolve_symbol`'s bare-label fallback (graph_query.py:984-989) returns None on >1 same-name match — a constant sharing a simple name with a function could break a previously-resolving callable lookup; make it **kind-aware** (prefer callable on multi-match) + add an AC + capture before/after callable-resolution counts in AC-6. (4) **Rename `references` → `reads`/`reads_constant`** — collides with the existing `doc_references_code` relation (graph_cluster.py:63) AND the `code_references` tool's top-level `references` field (which today means CALLERS); tag constant-reader results with an explicit kind. Add a guard AC asserting the new relation stays OUT of `_DEFAULT_IMPACT_RELATIONS`/`_DEFAULT_CALL_RELATIONS` (locks the deferral). | prepare-council `wf_c657bb0e-791` (moderator-verified against live code). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-10 | Add **constant nodes + a new `references` edge**, not overload `calls`. | A read is not a call; consumers (`code_callgraph`, attribution buckets) reason about `calls` semantics — overloading would corrupt them. A distinct `references` relation keeps call-graph queries clean. | Reuse `calls` for reads (rejected — pollutes call-graph + risk semantics). |
| 2026-06-10 | **Defer `code_impact`/`code_risk_score` integration** (constant reads toward blast radius) to a separate follow-up. | This change is graph *shape* + navigation; folding constant reads into impact would perturb risk-score calibration (the `1p41l` gate) in the same step. Add nodes/edges first, integrate scoring deliberately later. | Integrate impact now (rejected — couples two gates; risk-score regression risk). |
| 2026-06-10 | **Faithful resolution only** (same-module + explicit import; no same-name heuristic binding). | The `1p4eq` adversarial review showed coincidental same-name binding is the dominant wrong-edge failure; constants have the same risk. | Bind nearest same-name constant (rejected — wrong-twin edges). |
| 2026-06-10 | **All core supported graph languages** (Python, JS/TS, Java, Kotlin, C#, Go, Rust, Swift, Ruby, PHP), not Python-first (operator directive). | Constants must be modeled wherever the graph already models code symbols — a Python-only constant graph would be inconsistent and would help only one language's "what value is X" / blast-radius. Each language reuses its EXISTING extractor mechanism (AST / tree-sitter / structural), so no new parsers. | Python-first + others as a follow-up (rejected by operator — wanted parity with the existing multi-language graph coverage from the outset). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Constant-node explosion / graph bloat (every assignment a node) | Scope to module-/type-level named constants **by per-language mechanism + scope** (NOT `UPPER_SNAKE` — see the `1p4mf` Per-Language Constant Detection table; the ancestor scope gate, not casing, bounds bloat); exclude locals/params; measure node-count delta per-language in AC-6 |
| Reference-edge mis-binding (wrong same-name constant) | Faithful resolution only (Req 5 / AC-5 adversarial test); unresolved stays external |
| `GRAPH_BUILDER_VERSION` bump forces full rebuild for all consumers | Expected, documented self-heal (standard post-bump behavior); AC-3 verifies the re-extract |
| Perturbing existing attribution buckets / call-graph correctness | New relation is additive (`references`, separate from `calls`); AC-6 asserts no bucket/correctness regression on the real graph |
| Large per-language extraction surface (~11 languages × declaration syntax + reference resolution) — implementation effort + wrong-binding risk scale with the language count | Reuse each language's EXISTING extractor mechanism (no new parsers); stage per-language each with its own faithfulness test (AC-5); the AC-6 value gate measures real-graph coverage + no-regression; languages can land incrementally behind the version bump |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
