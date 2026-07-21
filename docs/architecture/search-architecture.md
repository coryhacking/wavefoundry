# Search Architecture

Owner: Engineering
Status: active
Last verified: 2026-07-21

## The Problem

Agents navigating a project through Wavefoundry's MCP server face two distinct retrieval problems:

**Discovery**: "I don't know where this is documented" — finding relevant docs, prompts, or code without knowing the exact filename or keyword. A query like "how do I start a wave?" should surface the prepare-wave prompt even though that doc uses the word "prepare," not "start." Lexical search fails here; semantic similarity handles it.

**Navigation**: "I know what I'm looking for, find it exactly" — reading a specific file, searching for a known function name, jumping to a definition. Semantic search is worse than useless here: it introduces noise, requires a model to be available, and is non-deterministic. An exact grep is better in every way.

These are different enough problems that they warrant different tools. Trying to solve both with a single approach (pure semantic, pure lexical, or pure AST) produces a system that handles neither well.

---

## The Three-Layer Model

The MCP search surface is organized into three layers, each solving a narrower and more precise version of the navigation problem:

```
Layer 1: Semantic search — docs_search, code_search
Layer 2: Exact navigation — code_keyword, code_constants, code_pattern, code_outline, code_read, code_list_files
Layer 3: Symbol navigation — code_definition, code_references, code_dependencies
Layer 4: Codebase Q&A — code_ask
```

They are ordered from broadest to narrowest:

| Layer | Input | Output | When to use | Always available? |
|-------|-------|--------|-------------|-------------------|
| Semantic | Natural language query | Ranked relevant chunks | Orientation, discovery, "find something like X" | No — requires model cache |
| Exact | Literal text substring | File path + line + snippet | Known keyword, function name, exact string | Yes — always |
| Symbol | Symbol name or position | Definition/reference locations; import graph | Jump-to-definition, find-all-references, dependency tracing | Partial — Python AST; other languages use keyword fallback |
| Codebase Q&A | Natural language question | Grounded answer with citations | Open-ended questions spanning multiple files | No — requires semantic index |

The layering matters because agents should reach for the narrowest tool that fits the task. Using semantic search to find a function you know the name of is slower, less reliable, and wastes tokens. Using exact keyword search to find documentation about a concept you can't name exactly is fruitless.

---

## Design Decisions

### Decision 1: Offline-first semantic search

The MCP server runs embedded inside the IDE process. Network calls during agent sessions are unacceptable — they introduce latency spikes, fail silently in restricted environments, and make query results non-deterministic across sessions. The embedding model must run fully locally.

This is the constraint that shapes everything about Layer 1:
- The model is pre-cached by `setup_index.py` (explicit setup step, network allowed)
- All queries use `local_files_only=True` and `HF_HUB_OFFLINE=1`
- The model choice (`BAAI/bge-base-en-v1.5`) was driven in part by reliable offline support in fastembed
- When the model is unavailable, the system falls back to lexical search rather than failing

See `docs/architecture/embedding-model.md` for the model choice rationale.

### Decision 2: Transparent fallback, not silent degradation

When semantic search is unavailable, `docs_search` automatically falls back to `search_docs_lexical`. The response always includes `data.mode: "semantic" | "lexical"` so agents know which path they got. This matters because the quality difference is significant — an agent acting on lexical results as if they were semantic results may miss the right document entirely.

The fallback is intentional rather than accidental: a useful-but-lower-quality answer is better than an error. But it must be transparent.

### Decision 3: Embedded vector store (LanceDB)

The vector retrieval layer uses **LanceDB** — an Apache 2.0 embedded in-process vector database — as its persisted backend. There is no numpy or legacy-JSON serving fallback: readers require a completed build epoch and the canonical Lance tables, and fail closed when either is unavailable.

**Why LanceDB:**

1. **Memory-mapped files, not full matrix loads.** The legacy numpy path loaded the full `.npy` matrix into RAM on every cold start. LanceDB memory-maps Lance columnar files — only pages touched by a query are read.
2. **Native HNSW index above threshold.** When a table reaches `LANCEDB_INDEX_THRESHOLD = 1000` rows, an `IVF_HNSW_SQ` index is built automatically. Below that threshold, LanceDB performs a flat scan (comparable to numpy) with no index overhead.
3. **True deletion path.** The numpy backend had no deletion path — a file removal required a full rebuild. LanceDB supports filtered deletes for incremental updates, including row-level deletes by chunk id.
4. **Predicate pushdown.** `where` SQL predicates are pushed into the scan layer, avoiding loading filtered-out rows. The numpy path filtered post-scan.
5. **Operational simplicity retained.** LanceDB is embedded (no server process). Wavefoundry connects directly to `.wavefoundry/index/`; the canonical tables are `.wavefoundry/index/docs.lance/` and `.wavefoundry/index/code.lance/`. LanceDB may also maintain its own `.wavefoundry/index/__manifest/` metadata at that database root. A nested `.wavefoundry/index/lancedb/` directory is not part of the canonical layout and is a removable legacy artifact once the root tables are complete.

**Lifecycle:**

- The indexer passes `index_dir` itself to `lancedb.connect(...)`, so LanceDB writes the `docs` and `code` tables as `index_dir/docs.lance/` and `index_dir/code.lance/`.
- SQLite `index-state.sqlite` is the sole authority for build state and provenance. Readers require a completed epoch before opening either root-level table; legacy `meta.json`, numpy, and JSON index artifacts are never serving inputs (wave `1sed7`).
- During incremental updates, the indexer reads existing rows for stale paths, compares `chunk_hash` values against freshly generated chunks, reuses unchanged vectors, embeds only changed/new chunks, deletes removed or replaced row ids, and appends current rows. `_optimize_lance_table` compacts the table when the fragment count exceeds `LANCEDB_COMPACT_THRESHOLD = 20`.
- A full rebuild recreates the canonical root tables. If LanceDB is unavailable or the tables cannot be opened, the build or reader reports the failure rather than manufacturing readiness from a secondary format.

**Score convention:** LanceDB's cosine metric returns `_distance = 1 - cosine_similarity`. `_lance_search` converts this to `score = 1 - distance` so higher scores always mean more similar.

### Decision 4: Single project index (framework docs folded in)

There is **one** semantic index: the project index at `.wavefoundry/index/`, built from the
user's own docs, code, and seeds. **The framework seeds and README are folded into this same
project docs index** by the walker — `indexer.FRAMEWORK_FOLD_DOCS_PREFIXES`
(`.wavefoundry/framework/seeds`, `.wavefoundry/framework/README.md`) is appended to the project
docs include-prefixes, scoped past the `.wavefoundry/` blanket exclusion. The index is built
locally at setup/upgrade and rebuilt by `setup_index.py` or the post-edit hook; a change to a
framework seed or the README marks the project index stale and triggers the same single rebuild.

Wave 1p4ww removed the previously-separate, pre-built **framework index**
(`.wavefoundry/framework/index/`) that was packaged in the release zip. The two-layer design
carried a real cost — a separate build/ship/publish-guard and, critically, a model-pinning
constraint: the shipped framework vectors had to use the same embedding model as the project
docs, or `docs_search` mixed two vector spaces. Folding framework docs into the locally-built
project index removes the whole layer (no shipping, no publish guard, no cross-layer
model-pinning) and unblocks a per-project docs-model choice. Framework docs are small, so the
local build is cheap. See `docs/architecture/decisions/1p4xx-adr fold-framework-index-into-project-docs.md`.

Because there is only one layer and one model, the previous "skip a layer whose vector dimension
or model name mismatches" safety net is no longer needed for the docs/code index.

### Decision 5: Exact navigation uses live file walks, not an index

`code_keyword`, `code_constants`, `code_pattern`, `code_outline`, `code_read`, and `code_list_files` operate directly on the filesystem rather than querying a pre-built index. This was a deliberate choice:

**Staleness is not acceptable for exact navigation.** An agent using `code_keyword` to find a function definition must get the current state of the file, not a cached state from the last index build. Doc search can tolerate some staleness; exact code navigation cannot.

**The cost is acceptable.** A `rg`-style substring walk over a typical repository is fast enough (milliseconds to low seconds) that the simplicity of no-index-required outweighs the marginal latency cost.

**It keeps the two concerns separate.** The semantic index is for concepts; the filesystem is for facts. Blurring this boundary would require the index to be rebuilt on every code edit and kept perfectly in sync — a reliability problem that adds complexity without benefit.

All file walks reuse the same ignore/exclusion rules as the indexer (`walk_repo()`, `.gitignore`, `.aiignore`, hardcoded excludes) to keep results consistent.

### Decision 6: Symbol navigation uses Python AST plus targeted tree-sitter-backed languages

Language-aware symbol navigation (jump-to-definition, find-references) benefits from parsing where available, but the tool surface does not need to wait for full LSP coverage. The implementation uses a tiered approach:

- **Python**: AST-based, using `ast.walk()` to find `FunctionDef`, `AsyncFunctionDef`, and `ClassDef` nodes by name. Reliable and dependency-free. Returns `method: "ast"`.
- **Tree-sitter-backed languages**: JavaScript, TypeScript, Java, and C# use the existing chunker parser stack for structural definitions and identifier-level references. Returns `method: "treesitter"` or per-result `treesitter_*`.
- **Additional supported definition languages**: Go, Rust, Kotlin, and Swift use structural regex matching for top-level symbols. Returns `method: "regex"`.
- **References across the remaining known code languages**: language-filtered text matching. Returns `method: "text"`.
- **Fallback**: broad repo keyword matching when no structural/text layer finds a result. Returns `method: "keyword_fallback"`.

These tiers keep one public tool API while making provenance explicit via the `method` field. Future tree-sitter or LSP upgrades can improve precision without changing the tool names or call shape.

### Decision 7: Orientation chunks (`code-summary`, `doc-summary`) enable fast first-pass retrieval

A full semantic search over all file chunks is expensive when the agent only needs to know which files are relevant. Two orientation chunk kinds solve this:

- **`kind="code-summary"`**: one chunk per source file — module docstring (or leading comment) + top-level symbol names (capped at 20). Produced by `_chunk_code_summary` in `chunker.py`; routes to the code index. Queried with `code_search(kind="code-summary")` to get a file-level orientation map without reading full source chunks.
- **`kind="doc-summary"`**: one chunk per markdown file — first non-heading paragraph + all H1/H2/H3 headings concatenated as `Sections: A · B · C`. Produced by `_chunk_doc_summary`; routes to the docs index (via `_is_docs_kind`). Queried with `docs_search(kind="doc-summary")` for documentation orientation.

Both kinds are prepended to their file's chunk list so they appear first in retrieval results when the query matches the file-level summary.

### Decision 8: `code_ask` does mechanical retrieval routing, not LLM synthesis

`code_ask` is a structured routing tool, not an LLM-in-the-loop summarizer. Given a question, it:

1. Classifies the question type (`navigational` / `explanatory` / `instructional`) using the `_classify_question` keyword heuristic
2. Runs a broad semantic pass via `search_combined()` — fetches from both docs and code indexes, then (wave `1p52p`, ADR `1p52q`) applies a **rerank-FIRST** cross-encoder that scores the whole pool on one unified `sigmoid(logit)` relevance scale BEFORE the agent selection (per-index floor / relevance drop-off / text budget). This is `code_ask`'s single ranking path — the former `rerank="local"` and `rrf_fallback` paths were removed. The cross-encoder runs on whatever hardware is present (FP16 on GPU, INT8 on CPU); ordering falls back to vector/coverage order (`reranked=false`) only when reranking is explicitly disabled or unbuildable. The unified scale matters because the docs/code model split (`1p4wx`) put arctic-doc and bge-code cosines on different scales — only the cross-encoder makes docs and code candidates comparable
3. If fewer than 2 citations, runs a targeted keyword fallback pass (`code_keyword`) — SUPPRESSED in `lexical_fallback` mode and on infrastructure failure (wave 1seav: live keyword hits must not mix into a lexical envelope or mask an outage as indexed evidence)
4. Returns `{answer, citations, confidence, gaps, question_type, index_freshness, search_mode, fallback_reason, rerank_mode, reranked, partition_applied, demotion_count, total_ms, vector_ms, rerank_ms, definition_boosted, second_hop_symbols}` — plus `drift_partition_applied`/`drift_demoted_count` when the (default-off) doc-code-drift partition fired (plus `coverage` on every degraded/failed envelope — `{}` when collection was unavailable) and per-citation metadata including `score`, `final_rank`, `demoted`, and `partition_reason`

The `answer` field is mechanically assembled from the top citation — it names the file and line range, not a synthesized prose response. This is intentional: the tool is designed to be called by an agent that will read the cited sources and reason over them, not to replace that reasoning. Synthesis is the caller's job; retrieval and citation is `code_ask`'s job.

`confidence` is heuristic. When the cross-encoder ran (`reranked=true`), it is calibrated on the
unified cross-encoder relevance (`sigmoid(logit)`): `high` = top ≥ `CONF_AGENT_RERANK_HIGH` (0.5) with
≥2 citations, `low` = top < `CONF_AGENT_RERANK_LOW` (0.1, nothing relevant retrieved), else `medium`
(live-index separation: on-topic ≥0.95, off-topic ≤0.07). Two `reranked=false` cases (wave 1seav):
on the HEALTHY path (reranker disabled/unbuildable) ordering is vector/coverage over mixed-model
cosine and confidence is capped at `medium` (`low` with zero citations — `high` is never claimed
without the cross-encoder); in `lexical_fallback` mode ordering is BM25 exact-token and confidence
is `low`. `index_freshness` is the cached three-state verdict (`current`/`stale`/`unknown` — see
`mcp-tool-surface.md`).

`CHUNKER_VERSION` `"22"` introduced per-row `chunk_hash` metadata so incremental updates can reuse existing LanceDB vectors for unchanged chunks inside a changed file. The version bump intentionally forces a one-time rebuild of existing tables so old rows without `chunk_hash` are not mixed with new rows that depend on it.

`code_ask` citations preserve the pre-partition reranker `score`, but `final_rank` reflects the actual output order after the soft partition rules run. The historical per-citation `seed`/`feedback` partition tags were removed with that mechanic (change `12q5v`); the doc-type demotion is now a SCORE demotion reported only by the top-level `partition_applied`/`demotion_count`. Wave `1ro44` reintroduced the per-citation fields for one reason only: `demoted: true` + `partition_reason: "doc_code_drift"` marks a drift-flagged doc stable-partitioned behind a comparably-relevant current alternative (see the Temporal Decay section below).

**Question-type-aware retrieval in `search_combined`:**

- `navigational`: code-index candidates receive a `RRF_NAVIGATIONAL_CODE_WEIGHT` (1.5×) multiplier in RRF scoring to bias toward code results
- `explanatory`: after reranking, results whose path contains any segment from `INFRASTRUCTURE_PATH_SEGMENTS` (scaffolding-layer paths: CDK constructs/stacks, Terraform modules/resources, Spring config/beans, Express/NestJS routes/wiring, generic infra/infrastructure) are stable-partitioned to the end of the result list. This prevents CDK scaffolding and wiring files from displacing business-logic files for multi-hop explanatory questions.
- `instructional` and default: no weight bias; no partition

**Dynamic `VECTOR_TOP_K`:**

The candidate pool size scales with question type:
- `explanatory`: `VECTOR_TOP_K_EXPLANATORY = 50` candidates per index (100 total) — larger pool improves recall for multi-hop call chains where the correct answer spans multiple layers
- All other types: `VECTOR_TOP_K = 30` candidates per index (60 total)

The tradeoff: the cross-encoder reranker scales approximately linearly with candidate count, so smaller pools should reduce rerank cost. On GPU-enabled hardware the ceiling is 500ms; on CPU this is infeasible regardless of TOP_K (see `12mns-enh dynamic-vector-top-k` for the benchmark).

**Per-query timing:**

`search_combined` returns `(results, reranked, vector_ms, rerank_ms, definition_boosted, second_hop_symbols)`. `code_ask_response` adds `total_ms` (wall-clock for the entire handler). All three timing values are emitted in the MCP response and printed to the server log per invocation as `[wavefoundry] code_ask timing: total=Xms vector=Yms rerank=Zms`.

**`search_combined` execution pipeline (reranker path):**

```
1. Vector fetch (timed as vector_ms)
 ├─ Embed query with DOCS_MODEL → cosine search over docs index → top_k candidates
 ├─ Embed query with CODE_MODEL → cosine search over code index → top_k candidates
 └─ top_k = VECTOR_TOP_K_EXPLANATORY (50) if explanatory; VECTOR_TOP_K (30) otherwise

2. Definition-file boosting
 └─ For each DEFINITION_BOOST_RULES entry whose vocabulary matches the query:
 keyword-search on the most specific matching term, inject ≤ DEFINITION_BOOST_CANDIDATES (5)
 hits with score=0.0 into the combined pool; record rule label in definition_boosted

3. First rerank (rerank_ms starts here)
 └─ _rerank(query, all_candidates, top_n) — cross-encoder scores each [query, text] pair

4. Two-hop symbol expansion (explanatory only — see Decision 11)
 └─ Extract symbols from top-3 non-infra citations → keyword-search each →
 inject ≤ MAX_SECOND_HOP_CANDIDATES (10) new candidates with score=0.0

5. Second rerank (if second-hop produced candidates)
 └─ _rerank(query, results + second_hop_candidates, top_n)

6. Infrastructure partition (explanatory only)
 └─ _partition_infra(): stable-push INFRASTRUCTURE_PATH_SEGMENTS citations to end

7. Return (results, True, vector_ms, rerank_ms, definition_boosted, second_hop_symbols)
```

**`search_combined` no-reranker degradation (reranker disabled/unbuildable):**

The former `_rrf_merge` fallback path was removed with the rerank-first unification (`1p52p`) — there is no
separate RRF pipeline anymore. When the cross-encoder cannot run, the single pipeline degrades in place:
ordering falls back to vector/coverage order over mixed-model cosines (`reranked=false`, confidence capped at
`medium`), lexical candidates join with rank-derived fallback scores, and two-hop symbol expansion is skipped
because cross-encoder scoring is required to evaluate injected candidates on content merit.

### Decision 9: `max_per_file` cap in `code_search` for result diversity

Without a per-file cap, `code_search` can return many chunks from a single large file when that file dominates cosine similarity scores — useful for deep dives into one file, but unhelpful for orientation across the codebase. The `max_per_file` parameter caps how many chunks from the same file can appear in results. Order is: rank (cosine score descending) → language filter → kind filter → per-file cap → `[:top_n]`. The highest-scoring chunk per file is always retained when the cap is applied.

### Decision 10: Definition-file boosting uses an extensible rule table, not hardcoded logic

When a query vocabulary signals that schema-language files are relevant, `search_combined` injects candidates from those files before reranking via `DEFINITION_BOOST_RULES`. Each rule is a dict with three fields:

```python
{
 "vocabulary": frozenset({"sql", "stored procedure", "proc", ...}),
 "extensions": [".sql"],
 "label": "sql",
}
```

When any vocabulary term appears in the lowercased query, the rule fires: `code_keyword` runs on the most specific matching term (longest vocabulary term > 3 chars present in the query), and up to `DEFINITION_BOOST_CANDIDATES = 5` matching files are injected into the candidate pool with `score=0.0`. The cross-encoder then evaluates them on content merit alongside vector candidates.

`score=0.0` means the injected candidates enter at the bottom of any pre-rerank order, so the reranker promotes them only if their content is genuinely relevant. This avoids false promotion of unrelated schema files when the vocabulary fires incidentally.

The rule fires only when injection produces at least one candidate; the `definition_boosted` response field is non-empty only when files were actually injected. Adding a new schema language (GraphQL, protobuf, OpenAPI) requires appending one entry to `DEFINITION_BOOST_RULES` — no logic changes.

**Note:** In the RRF fallback path (reranker unavailable), injected definition candidates are currently dropped because `_rrf_merge` operates on `docs_candidates` and `code_candidates` separately. Definition-boost candidates only appear in results when the cross-encoder reranker is available.

### Decision 11: Two-hop symbol expansion follows call chains across vocabulary gaps

Vector search retrieves what the original query vocabulary can reach. For explanatory questions tracing a multi-layer call chain ("how does a new tenant get created?"), the API handler and service layer typically surface in the top-5 results, but the repository layer and SQL schema do not — they share less lexical overlap with the query than the shallower layers. Two-hop expansion follows the symbol references found in the first hop to reach layers the query could not name.

**Gate condition**: fires only when `question_type == "explanatory"` and the cross-encoder reranker is available. The second hop is skipped entirely in the RRF fallback path (see Decision 8 pipeline above) and when no symbols can be extracted from the top citations.

**Extraction scope**: top-3 results after first rerank, filtered to non-infra citations only (INFRASTRUCTURE_PATH_SEGMENTS). Infrastructure-layer files (CDK constructs, Terraform modules, Spring config, NestJS routes) import many application symbols and would bias expansion toward wiring files rather than business logic.

**Symbol extraction** — tiered by language support:

| Strategy | Languages | How |
|---|---|---|
| AST | Python | `ast.parse()` → walk `Call` / `Attribute` nodes for callee names; `Import` / `ImportFrom` for imported names |
| Tree-sitter | JS, TS, Java, C#, Go, Rust, C, C++, Kotlin, Bash, SQL | `_ts_parse(lang, text)` + `_extract_symbols_ts()` — walks call/invocation node types, extracts callee identifier; lazy-loaded via `_get_chunker_module()` at first use |
| Regex fallback | All others, or when parse fails | `r'\b([A-Za-z_][A-Za-z0-9_]{3,})\s*\('` (calls), `r'\b(?:EXEC\|EXECUTE\|CALL)\s+([A-Za-z_][A-Za-z0-9_.]{3,})\b'` (SQL), `r'\bimport\s+([A-Za-z_][A-Za-z0-9_]{3,})'` (imports) |

**Post-filter** (all paths): deduplicate, require length ≥ 4, remove `_SYMBOL_BLOCKLIST` entries (common built-ins: `get`, `set`, `run`, `init`, `main`, `self`, `this`, `true`, `false`, `null`, `new`, `return`, `create`, `update`, `delete`, `list`, `find`, etc.), cap at `MAX_SYMBOLS_EXTRACTED = 5`.

**Second hop**: for each extracted symbol, call `code_keyword_response(root, symbol)`. Skip any result whose `(path, start_line)` is already in `first_hop_keys` (built from the full first-hop pool, not just top-N). Inject new candidates with `score=0.0`. Stop when `MAX_SECOND_HOP_CANDIDATES = 10` total is reached across all symbols.

**Second rerank**: re-run `_rerank(query, results + second_hop_candidates, top_n)`. The cross-encoder evaluates second-hop candidates against the original query on content merit. `score=0.0` injection ensures injected candidates are promoted only if their content is genuinely relevant to the question.

**Output**: `second_hop_symbols` in the `code_ask` response lists the symbol names that triggered retrieval. Present and non-empty only when the second hop produced at least one candidate that survived deduplication. When non-empty, the citation set already includes results from the second hop — callers should not re-chase those symbols manually.

**Cap constants** (module-level in `server.py`): `MAX_SYMBOLS_EXTRACTED = 5`, `MAX_SECOND_HOP_CANDIDATES = 10`. These are security-relevant: they bound the server work a crafted repository file can trigger. See `docs/agents/security-reviewer.md` for the security reviewer's check procedure.

**Tree-sitter coupling**: the chunker's tree-sitter parser stack is a runtime dependency of this path, loaded lazily at query time. This coupling is documented in `docs/architecture/domain-map.md` under MCP Server "Inbound Deps." Any change to `_TS_SYMBOL_LANG_MAP` (the set of languages routed through tree-sitter for extraction) must update that entry.

---

## Fallback Chain

The search fallback chain (wave `1seav` — driven by the CAPTURED `1sed7` epoch token):

```
1. docs_search / code_search / code_ask (query)
 ↓
2. Semantic/hybrid retrieval [embed query → vector + FTS fusion → rerank]
 ↓ if SemanticModelUnavailableOfflineError (or unservable tables) AND the captured epoch is COMPLETE
3. FTS fallback [_fts_degraded_serve: BM25 from fts_docs/fts_code, filters preserved,
   typed {available, failure_reason, results, coverage}; a broken FTS layer under a
   readable build_state probes as query_failed, never a silent zero-hit]
 ↓ docs_search ONLY, when NO published epoch exists (absent/uninitialized/building/interrupted)
4. Live-filesystem walk [search_docs_lexical: per-call re-chunk — its only reachable states]
 ↓ if no results
5. Typed zero/failed result: search_mode + always-present fallback_reason (null when healthy)
   + a token-semantics note on WORKING-lexical zero-hits + recovery diagnostics
```

`code_search`/`code_ask`/`code_lexical` have NO degraded path on a not-ready index — they refuse (`index_not_ready`, the 1sed7 lockout). `code_ask` additionally classifies its artifact-anchored exact-first pass as `search_mode: "exact"` (healthy) and caps confidence in lexical fallback. The legacy `mode: "semantic" | "lexical"` field remains for back-compat; `search_mode` is the authoritative signal.

For code navigation (Layer 2 and 3), there is no fallback: the tools either return results or return a clear empty/unsupported response. This is intentional — exact and symbol navigation are not degraded by missing infrastructure, only by missing language support.

---

## Hybrid Lexical Layer (SQLite FTS5)

Wave 1rsh9 added the retrieval-quality lever the project's own findings kept pointing at: hybrid lexical + reranking, not a better embedder. Dense retrieval is weakest exactly where agents need precision — exact identifiers, rare tokens, error strings — and the cross-encoder can only rerank candidates the fetch actually surfaced.

**Mechanics.** The index-state store (`index-state.sqlite`, see Index Format) carries one contentful FTS5 table per Lance content table (`fts_docs`, `fts_code`), keyed by chunk id and maintained by the build under an ordered-consistency model: Lance is authoritative for chunk existence, the store's rows commit in one SQLite transaction ordered after the Lance writes, and an end-of-build reconciliation pass (chunk-id set comparison → derived-only rebuild from Lance) repairs any crash window. Tokenizer: `unicode61 tokenchars '_'` — compound identifiers stay whole tokens, because exact-identifier queries are this layer's reason to exist (concept queries are the dense layer's job).

**Fusion.** `search_combined` (the `code_ask` retrieval core) fetches top-`LEXICAL_TOP_K` BM25 candidates per table alongside the vector candidates and merges them into the pool **before** the cross-encoder rerank, so the reranker arbitrates on one unified scale. Lexical hits form a third selection source, so the selection's key-merge unions `sources` — a chunk found by both passes carries `["code", "lexical"]` (multi-source agreement, same convention RRF fusion rewarded). User query text reaches FTS5 only as a bound parameter with every token quoted (operators become literals); a query FTS5 rejects degrades that call to vector-only with no error. When the reranker is unavailable, lexical candidates get rank-derived fallback scores (`LEXICAL_RRF_FALLBACK_WEIGHT`). Kill switch: `WAVEFOUNDRY_DISABLE_LEXICAL_FUSION`.

**Availability.** FTS5 presence is probed once per process and recorded in store meta; absence degrades to vector-only retrieval with no lexical tables and no errors. `code_keyword` is untouched — live grep remains the exactness contract; FTS is a ranked-retrieval candidate source, not a keyword-tool replacement.

**One lexical engine.** The FTS5 layer is the ONLY lexical index. The former Lance/Tantivy FTS (retired in wave 1rsh9/1sauc) rebuilt whole on every changed build and leaked un-GC-able index versions under `_indices/` (measured 98 MB on this repo); its one consumer — `search_code`'s hybrid lexical half — now reads the FTS5 tables (`kind`/`tags` filter inside the query; `language` rides the rows for the post-filter; scores are −bm25 so the RRF merge order holds), and the reclaim path drops legacy Tantivy indices from field repos at upgrade.

---

## Index Format

```
.wavefoundry/index/
 docs.lance/ LanceDB table: doc chunks + vectors (vector index only —
 the Lance/Tantivy FTS was retired in wave 1rsh9; legacy
 indices are dropped by the reclaim path at upgrade)
 code.lance/ LanceDB table: code chunks + vectors
 index-state.sqlite semantic-index state store (waves 1rsh9/1sed7) — the SOLE state
 authority: per-path build bookkeeping + chunk registry, the
 build_state epoch row, freshness/attribution tables, FTS5 lexical
 tables (fts_docs/fts_code), per-file secret-scan cache. WAL
 journaling; schema-versioned; drop-and-rebuild on corruption or
 version mismatch.
```

There is **no `meta.json`** (wave `1sed7`): the store's bookkeeping tables are the only source of per-path build state, and every consumer — indexer change detection, `WaveIndex` loading, MCP health/status, dashboard, upgrade version probes — reads the store (`export_meta_snapshot` provides the same dict shape the JSON used to carry). A store write failure is a structured build failure, never a silent fallback. A legacy `meta.json` left by a pre-`1sed7` install is never read by anything — including the upgrade's version probes (an absent/empty store reads as unknown, which forces convergence) — and is removed after the first successful build.

**Degradation ladder (wave `1seav`):** semantic/hybrid retrieval is the healthy path; when the
embedding model is unavailable but the index is PUBLISHED (captured complete epoch), the tools
serve BM25 results from the FTS5 layer with filters preserved (`search_mode: lexical_fallback`,
confidence capped for `code_ask`); when no published index exists, `docs_search` serves the
live-filesystem walk (`live_fallback` — the only state where it is reachable; a healthy store
never walks) and the code tools refuse (`index_not_ready` — unchanged from 1sed7). The shared
FTS serving path returns a typed `{available, failure_reason, results, coverage}` result so
infrastructure failure (`query_failed`) is never presented as an empty corpus.

**Readiness — the build epoch (wave `1sed7`):** the store's `build_state` row is a small state machine (`uninitialized` → `building` → `complete`). A mutating build commits a FULL-durable `building` fence BEFORE the first Lance/FTS mutation and publishes completion with an attempt-ID compare-and-set transaction — the only operation that advances the build `generation`. Readers (`docs_search`, `code_search`, `code_ask`, `code_lexical`, `seed_get`, `wf_map`) capture the FULL state token `(attempt_id, status, generation)` — ABA-proof; every fence and every publication changes it — before the operation and re-validate the SAME token after: any transition means the result set could span two index states, so results are discarded (`index_not_ready`). The strict code tools additionally refuse up front unless the captured token's status is `complete`; `docs_search`/`seed_get`/`wf_map` serve sanctioned degraded/disk paths under a STABLE non-complete state. `WaveIndex` reload uses the same token as its freshness signature, so a completed build invalidates cached handles without a server restart. `docs_search`'s live-filesystem walk (plus `seed_get`/`wf_map`'s disk fallbacks) are the sanctioned degraded paths when no complete epoch exists; the code retrieval tools refuse outright (FTS is derived from Lance and mid-build state is mixed). A `building` epoch whose build lock is gone reads as *interrupted* — still fail-closed, healed by the next ordinary build superseding the dead attempt (a zero-change retry performs this recovery explicitly: reconcile, bookkeeping refresh, finalize). Completion is globally gated: a scoped build over a reset store (a Lance table present with no provenance in the canonical state) escalates to all-layer convergence before it may publish, a rear guard refuses finalization if any present table would publish unprovenanced, and the derived-FTS/optimize maintenance verbs are restore-only — they refuse on a store with no completed epoch and never manufacture `complete`.

**Chunk schema:**

```json
{
 "id": "unique string",
 "path": "repo-relative/path/to/file.md",
 "kind": "doc | doc-summary | seed | prompt | code | code-summary | python | ...",
 "language": "python | null",
 "lines": [start_line, end_line],
 "section": "Header text or null",
 "text": "chunk text — what was embedded"
}
```

The `kind` field now includes two orientation kinds:
- `code-summary` — file-level symbol index for source files; routes to code index
- `doc-summary` — heading index for markdown files; routes to docs index

The `text` field is what was embedded. The `path` and `lines` fields are what the agent sees in results. Keeping the two separate means the embedded text can be a normalized or chunked version of the file without changing what's reported back.

---

## Temporal Decay: Per-Citation Freshness and the Drift Partition (wave 1ro44)

Retrieval ranks by relevance; temporal currency is surfaced as **annotation first, demotion only on strong
evidence** — raw scores are never blended with age (the rejected alternative is recorded in the change doc's
Decision Log: score-perturbation buries correct answers about stable code, since old ≠ wrong).

**Build-time substrate** (`index-state.sqlite`, optional residents at the build tail — never fail a build, no
per-query git ever): per-file freshness/churn from one batched `git log` (`file_freshness`/`file_commits`),
wave→files attribution derived from landing-commit subjects (`wave_landing`/`wave_change_files`), and per-doc
drift summaries (`doc_drift`). A doc's **drift anchor** is the newer of its last content change in git and its
`Verified against: <hex-sha>` verification stamp (gardener `Last verified` dates carry NO verification meaning);
drift = distinct commits touching the doc's referenced code paths after the anchor, flagged at
`DRIFT_COMMITS_THRESHOLD`. `docs/waves/` chunks are the **historical** class: anchored at their wave's landing
commit with `waves_behind` decay, never drift-flagged, never worklisted. `docs/reports/` is drift-exempt
(point-in-time artifacts — census finding).

**Query-time surfacing:** `docs_search`/`code_search`/`code_ask`/`code_lexical` results carry an optional
per-citation `freshness` object (`{age_days, churn_score}` for any path; docs rows add
`{drifted, commits_since_verified}` or `{historical, waves_behind}`) attached by ONE batched state-store read
per response. Distinct vocabulary from the envelope `index_freshness` (index-vs-working-tree currency).
Annotation is omitted on `live_fallback` (live content may be newer than stored metadata) and silently absent on
metadata-free stores.

**Drift partition** (`_partition_drift`, the `_partition_infra` stable-partition pattern): drift-flagged docs
citations move behind comparably-relevant current alternatives (`DRIFT_RELEVANCE_BAND` guard on the unified
reranker scale) with per-citation `demoted: true` + `partition_reason: "doc_code_drift"`. Runs ONLY on the
healthy reranked path — suppressed on `lexical_fallback`/`live_fallback`/`exact`/unreranked envelopes where the
relevance band is undefined. Ships **default-OFF** (`DRIFT_PARTITION_DEFAULT_ON = False`): flipping the default
requires the recorded drift-precision census AND a golden-query eval run per the standing ranking-eval gate.
Env toggles: `WAVEFOUNDRY_ENABLE_DRIFT_PARTITION` (census/eval opt-in), `WAVEFOUNDRY_DISABLE_DRIFT_PARTITION`
(kill switch). Code chunks are never drift-demoted (a current code chunk is ground truth for itself).

**Worklist:** `wf_audit` exposes the `doc_drift` sub-object (flagged living docs, `commits_since` DESC) — the
stable consumer contract for the future verify-docs review loop; `wf_garden_docs` points at it and gardener stamps
never clear drift.

**Agent memory retrieval** (same wave): typed memory records under `docs/agents/memory/` are indexed through the
docs path with a `memory` tag and served by `memory_search`/`memory_brief` — record files are the
source of truth, the semantic index is an optional assist, and ranking is kind-aware-decayed confidence (via the
per-path freshness primitive) with persisted-betweenness tie-breaks.

## Index Readiness: Two Surfaces (wave 1t59p)

Index health is deliberately split into a fast surface and a deep surface:

- **`wf_audit` (bounded metadata snapshot):** readiness from the index control plane only — completed build
  epoch (SQLite), Lance table-directory presence, the bounded build summary (`read_build_summary`: layer
  scalars plus one COUNT, never per-file rows), configured include-prefixes. It never
  imports LanceDB, never opens a table, never materializes per-file store rows, and never hashes the
  working tree, so it is bounded on every OS
  (the unbounded native cold-load plus full-corpus hash walk was a field-reported native-Windows hang on the
  default first call of a session). Consequently it reports `freshness: "unknown"` and can never claim the
  index is current.
- **`index_health` (full verification):** the complete hash-walk freshness scan (`stale_paths`,
  `semantic_ready`) — O(total-indexed-bytes) by design, invoked explicitly when verified freshness matters.

The fast surface always names the deep surface (`freshness_verification_tool: "index_health"` plus an
`index_freshness_unverified` advisory), so metadata readiness is never mistaken for a freshness verdict.

## Relationship to Other Architecture Docs

- **`embedding-model.md`** — the specific model choice, its properties, regression tests, and upgrade procedure
- **`data-and-control-flow.md`** — the runtime control paths for index build and MCP query calls
- **`current-state.md`** — the deployed MCP topology, including which tools belong to each search layer
- **`docs/agents/guru.md`** — the Guru agent role doc: retrieval loop, citation format, confidence model, and per-agent usage guidance
