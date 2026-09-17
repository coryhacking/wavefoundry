# Search Architecture

Owner: Engineering
Status: active
Last verified: 2026-09-17

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
- The active embedding model (`Snowflake/snowflake-arctic-embed-s`) is supplied in the verified v2 offline companion and resolves cache-first
- When the model is unavailable, the system falls back to lexical search rather than failing

See `docs/architecture/embedding-model.md` for the model choice rationale.

### Decision 2: Transparent fallback, not silent degradation

When semantic search is unavailable, `docs_search` automatically falls back to `search_docs_lexical`. The response always includes `data.mode: "semantic" | "lexical"` so agents know which path they got. This matters because the quality difference is significant — an agent acting on lexical results as if they were semantic results may miss the right document entirely.

The fallback is intentional rather than accidental: a useful-but-lower-quality answer is better than an error. But it must be transparent.

### Decision 3: Unified local SQLite storage

The semantic backend uses `apsw==3.53.4.0` (SQLite 3.53.4) with
`sqlite-vec==0.1.9`. Docs, code and — since wave `1xny6` — the code graph all
share `.wavefoundry/index/index.sqlite` with the indexing state, so ONE
transaction publishes every layer and ONE generation is what readers see. Only
the memory store remains separate. No server or hosted database is required.

Each layer has canonical `chunks_*` rows, keyed float32 `vectors_*` BLOBs and an
external-content `fts_*` index. An internal integer key joins them; public chunk
IDs retain their existing layer scope. Text lives once in the canonical row.
Docs and code keep separate FTS populations, the same eight FTS columns and
`unicode61 tokenchars '_'` tokenizer, preserving BM25 behavior.

`sqlite_vector_store.dense_rows` performs exact 384-dimensional cosine search,
with bound metadata filters before the result limit and stable internal-ID tie
ordering. There is no ANN index or vector quantization. The adapter returns
`_distance = 1 - cosine_similarity`; serving converts it to the existing
higher-is-better score. Embedding, fusion, candidate budgets and reranking remain
the responsibility of the existing retrieval pipeline.

The indexer prepares embeddings outside the writer transaction, then commits
canonical chunks, vectors, FTS postings, registry/digests and related file/layer
bookkeeping together with `BEGIN IMMEDIATE`. Triggers keep FTS synchronized.
Readers still require a completed generation and validate it after retrieval.
Since wave `1xny6` the graph is a participant in this same transaction rather
than separately fenced work, so the guarantee is now an actual SQL transaction
over one file rather than a fence spanning two databases.

All connections to the shared file use `sqlite_runtime`; the standard-library
binding remains available for separate stores. Data writes use WAL/NORMAL,
publication fences use FULL durability, and foreign keys and a 5-second busy
timeout are enabled. New or migrated databases use incremental auto-vacuum and
4 KiB pages. The measured starting configuration uses a 256 MiB mmap limit and
SQLite's default page cache (about 2 MiB per connection), with the default
1,000-page WAL autocheckpoint and no global `temp_store=MEMORY` override. Mmap is
a mapping limit, not a reserved RAM allocation. The tuning evaluation found no
clear additional benefit from the larger cache/1 GiB mmap/MEMORY combinations;
those suggestions were evaluated rather than adopted as defaults. See the
[tuning evidence](../waves/1xhbo%20lancedb-038-evaluation/1xhdh-maint%20evaluate-lancedb-038-upgrade.md).

Writable store close and controlled maintenance run `PRAGMA optimize`; the
startup-only `PRAGMA optimize=0x10002` suggestion is not configured. End-of-build
maintenance uses a passive checkpoint. Controlled index maintenance also checks
integrity and optimizes FTS segments, then reclaims at most 5,000 free pages per
store through incremental vacuum, preserving reusable space during branch churn.
A full VACUUM is reserved for explicit exceptional maintenance or one-time
conversion.

Existing Lance stores are migration inputs only. Standard `wf_upgrade` retains
them through verified SQLite publication, then removes owned `docs.lance/`,
`code.lance/` and `__manifest/`. Normal queries and fresh setup do not require
LanceDB. Unknown schemas and corruption are reported rather than silently
recreating canonical storage. See
[ADR 1xjmn](decisions/1xjmn-adr%20unified-sqlite-vector-storage.md) and the
[conversion gates](../waves/1xjmm%20unified-sqlite-vector-storage/1xj6o-ref%20unified-sqlite-vector-storage.md)
for the measured operating envelope and remaining release qualifications.

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

**The walk-exclusion contract (wave `1wfsl`, `1wfsn`).** The exclusion surface is consolidated
behind one documented story — the "CORPUS EXCLUSION STORY" banner above the constants in
`indexer.py` — because its fragmentation across unrelated constants caused a false planning
census. The layers, in application order: directory pruning (hardcoded dirs, the dot-directory
rule, gitignored dirs), exact-path exclusions, the machine-authority path predicates (owned by
`machine_authority.py` since wave `1x5tr` and consumed by `indexer.py` and by the secrets scanner's
non-git candidate walk: per-wave `events.jsonl` ledgers, memory-archive bodies, and the committed secret-scan findings ledger
`docs/scan-findings.json` — never re-includable, also enforced on the `files=` incremental build
seam), prefix exclusions, the NAME layer (`HARDCODED_EXCLUDE_FILENAMES` exact names such as
`package-lock.json` and `npm-shrinkwrap.json`, plus `HARDCODED_EXCLUDE_FILENAME_SUFFIXES`
patterns `*.min.js`/`*.min.css`), the extension layers (`BINARY_EXTENSIONS` including `.lock`;
generated extensions), the content sniff, and finally ignore files plus the size cap. After the
walk, `_filter_code_files` gates the code corpus on `SOURCE_CODE_EXTENSIONS` (dropping e.g.
`go.sum`, `gradle.lockfile`, `*.map`). A per-project re-include hatch —
`indexing.walk_reinclude_filenames` in `docs/workflow-config.json`, default empty, exact
filenames only — subtracts from the NAME layer alone: it cannot override the extension, sniff,
or machine-authority layers (re-including `yarn.lock` by name is therefore a no-op, because the
`.lock` binary extension still excludes it). All three retrieval corpora (semantic docs,
semantic code plus lexical, graph) derive from this one walk, so the layers apply uniformly.
The standalone secret scanner's git-tracked candidate set (all tracked files) is independent of these
walk exclusions by design and is regression-pinned against narrowing; only its non-git fallback walk
shares the machine-authority layer (wave `1x5tr`, change `1x550`), so index internals never enter the
scan cache on a target without git.

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

- **`kind="code-summary"`**: one chunk per source file — module docstring (or leading comment) + top-level symbol names (capped at 20). Produced by `_chunk_code_summary` in `chunker.py`; routes to the code index. Queried with `code_search(kind="code-summary")` to get a file-level orientation map without reading full source chunks. For Python the symbol list is module-structure-aware (wave `1wpif`, `1wngv`): `ast` enumerates module-level def/async def/class names only, so nested methods no longer consume the 20-symbol cap and a method-heavy class cannot evict later module-level functions from the summary; the regex line scan remains only as the SyntaxError fallback.
- **`kind="doc-summary"`**: one chunk per markdown file — first non-heading paragraph + all H1/H2/H3 headings concatenated as `Sections: A · B · C`. Produced by `_chunk_doc_summary`; routes to the docs index (via `_is_docs_kind`). Queried with `docs_search(kind="doc-summary")` for documentation orientation.

Both kinds are prepended to their file's chunk list so they appear first in retrieval results when the query matches the file-level summary.

### Decision 8: `code_ask` does mechanical retrieval routing, not LLM synthesis

`code_ask` is a structured routing tool, not an LLM-in-the-loop summarizer. Given a question, it:

1. Classifies the question into the exact public five-value set: `navigational`, `explanatory`, `instructional`, `artifact_anchored`, or `assessment`. Direct artifact/path cues take precedence over phrase signals. Instructional phrases take precedence over assessment nouns, and assessment remains observable as its own value while routing through explanatory-like retrieval.
2. Runs a broad semantic pass via `search_combined()` — fetches from both docs and code indexes, then (wave `1p52p`, ADR `1p52q`) applies a **rerank-FIRST** cross-encoder that scores the whole pool on one unified `sigmoid(logit)` relevance scale BEFORE the agent selection (per-index floor / relevance drop-off / text budget). This is `code_ask`'s single ranking path — the former `rerank="local"` and `rrf_fallback` paths were removed. The cross-encoder runs on whatever hardware is present (FP16 in static batches on GPU, INT8 one query/passage at a time on a static [1,512] CPU graph). CPU passages are never batch-padded: activation quantization must not make a passage's score depend on its peers. The cached CPU model supplies a derived singleton graph, built once and reused offline; no re-embedding is required. Ordering falls back to vector/coverage order (`reranked=false`) only when reranking is explicitly disabled or unbuildable. The unified scale matters because raw bi-encoder cosines are uncalibrated similarity, not calibrated relevance: docs and code cosines now come from one shared Arctic S embedder, and the cross-encoder still supplies the calibrated relevance scale the selection thresholds are tuned against (the historical `1p4wx` docs/code model split was the original motivation). For navigational or explanatory-like (`explanatory` or `assessment`) questions naming one symbol, an exact published-graph payload bound to its read-only SQLite state receipt may contribute one unambiguous declaration-capable node whose recorded source hash matches the single buffer used to render the citation; that candidate alone receives the owner marker and is stable-pinned after selection/infra partition, while ordinary semantic and lexical context remains. Missing, stale, ambiguous, source-mismatched, or unbound graph data adds nothing and triggers no refresh, scan, or second model path.
3. If fewer than 2 citations, runs a targeted keyword fallback pass (`code_keyword`) — SUPPRESSED in `lexical_fallback` mode and on infrastructure failure (wave 1seav: live keyword hits must not mix into a lexical envelope or mask an outage as indexed evidence)
4. Returns `{answer, citations, confidence, gaps, question_type, index_freshness, search_mode, fallback_reason, rerank_mode, reranked, partition_applied, demotion_count, total_ms, vector_ms, rerank_ms, definition_boosted, second_hop_symbols}` (each citation carries `section` when its chunk metadata supplies a section path, wave `1seaw`) — plus `drift_partition_applied`/`drift_demoted_count` when the (default-off) doc-code-drift partition fired (plus `coverage` on every degraded/failed envelope — `{}` when collection was unavailable) and per-citation metadata including `score`, `final_rank`, `demoted`, and `partition_reason`

The `answer` field is mechanically assembled from the top citation — it names the file and line range, not a synthesized prose response. This is intentional: the tool is designed to be called by an agent that will read the cited sources and reason over them, not to replace that reasoning. Synthesis is the caller's job; retrieval and citation is `code_ask`'s job.

`confidence` is heuristic. When the cross-encoder ran (`reranked=true`), it is calibrated on the
unified cross-encoder relevance (`sigmoid(logit)`): `high` = top ≥ `CONF_AGENT_RERANK_HIGH` (0.5) with
≥2 citations, `low` = top < `CONF_AGENT_RERANK_LOW` (0.1, nothing relevant retrieved), else `medium`
(live-index separation: on-topic ≥0.95, off-topic ≤0.07). Two `reranked=false` cases (wave 1seav):
on the HEALTHY path (reranker disabled/unbuildable) ordering is vector/coverage over raw
single-embedder cosine and confidence is capped at `medium` on calibration grounds, since raw
cosines are uncalibrated (`low` with zero citations — `high` is never claimed
without the cross-encoder); in `lexical_fallback` mode ordering is BM25 exact-token and confidence
is `low`. `index_freshness` is the cached three-state verdict (`current`/`stale`/`unknown` — see
`mcp-tool-surface.md`).

`CHUNKER_VERSION` `"22"` introduced per-row `chunk_hash` metadata so incremental updates can reuse existing vectors for unchanged chunks inside a changed file. The version bump intentionally forces a one-time rebuild of existing tables so old rows without `chunk_hash` are not mixed with new rows that depend on it.

`code_ask` citations preserve the pre-partition reranker `score`, but `final_rank` reflects the actual output order after the soft partition rules run. The historical per-citation `seed`/`feedback` partition tags were removed with that mechanic (change `12q5v`); the doc-type demotion is now a SCORE demotion reported only by the top-level `partition_applied`/`demotion_count`. Wave `1ro44` reintroduced the per-citation fields for one reason only: `demoted: true` + `partition_reason: "doc_code_drift"` marks a drift-flagged doc stable-partitioned behind a comparably-relevant current alternative (see the Temporal Decay section below).

**Question-type-aware retrieval in `search_combined`:**

- `navigational`: when the cross-encoder ran, code-index candidates receive the legacy-named `RRF_NAVIGATIONAL_CODE_WEIGHT` (1.5×) multiplier during agent candidate selection to bias toward code results
- `explanatory` and `assessment`: use the 50-candidate-per-index explanatory window, documentation demotion, and a stable infrastructure-path partition after selection. When the top citation is documentation, the response sets `validation_required: true` and requires a `code_read` continuation. Assessment alone also runs one bounded derived docs semantic/lexical query using generic audit/findings/gaps/weaknesses/opportunities/current-implementation vocabulary; deduplicated hits rejoin the same reranker and selection caps with their true reranker scores; no path class is injected and no synthetic score is written (wave `1seaw`'s cycle-2 council removed a report-class injector because a path-class prior with a synthetic score is not retrieval and broke the citations-are-reranker-ordered invariant that the graph signal honors by living in its own labeled section). Within assessment, every `docs/reports/` record recovers the generic report down-weight as a path class (no currentness or freshness predicate is evaluated), while historical `docs/waves/` records receive an additional bounded down-weight unless the query names that path; this score-only prior never excludes a candidate and preserves the per-source floors. No other question type takes the derived-query path.
- `artifact_anchored`: direct file/path questions use the broad explanatory-like hybrid pool and stable-pin the strongest eligible exact path/basename owner at rank one after selection; the named path's published owner rows (`DIRECT_ARTIFACT_OWNER_ROWS` per table, read from the published canonical chunk tables with no vector pass) are injected into the pool before reranking so the pin never depends on vector recall of a small file, and the seven ignore-file names are indexed as line-window code units (walker 16) so a direct ignore-file question can pin the file itself. A question that asks about the mechanism around the named file (`_MECHANISM_FRAME_RE`: "how does the framework restore the `.gitignore` block", "which function renders `.aiignore`", "which tests cover `chunker.py`") keeps the injection and the artifact type but does not pin the file over reranked evidence, while a named file or path that is the question's subject, with or without a leading article or one noun before the name ("how does the `.aiignore` file exclude paths", "how does `docs/agents/guru.md` describe retrieval"), still pins; the cue regex accepts a concrete path only when its final segment carries a dotted, lettered suffix and never stops at a path separator, so prose slash pairs ("input/output"), bare directories, and dot-directory prefixes of longer paths are not cues, and owner-row ownership compares casefolded paths on both sides (the candidate fetch itself is exact-case: the cue as typed must match the stored path's case) so mixed-case names such as `AGENTS.md` inject like lowercase ones; an explanatory lead (`_EXPLANATORY_LEAD_RE`: "how does", "why", "explain") keeps a question explanatory even when an assessment noun appears later. Weak generated-symbol/config/tool questions use the exact-first short circuit and fall through to broad retrieval only when thin. Direct path, filename, and artifact-class queries are exempt from the low-information-path prior.
- `instructional`: no code tilt or infrastructure partition.

Independently of question type, the single agent path may expand graph-resolvable symbols into
relationship-grouped `graph_related` evidence and report the seeds in `second_hop_symbols`. This
type-agnostic graph signal is distinct from the narrower exact known-symbol owner correction above.

Before source-floor/drop-off selection, ignore files, lockfiles, dependency manifests, and generated
agent surfaces receive `_LOW_INFORMATION_PATH_WEIGHT = 0.50`. The prior is a bounded score
down-weight, never an exclusion, and is suppressed when the query names the artifact path, filename,
or artifact class.

**Dynamic `VECTOR_TOP_K`:**

The candidate pool size scales with question type:
- `explanatory` and `assessment`: `VECTOR_TOP_K_EXPLANATORY = 50` candidates per index (100 total) — the larger pool improves recall for multi-hop explanation and broad assessment where the correct evidence spans multiple layers
- All other types: `VECTOR_TOP_K = 30` candidates per index (60 total)

The tradeoff: the cross-encoder reranker scales approximately linearly with candidate count, so smaller pools should reduce rerank cost. On GPU-enabled hardware the ceiling is 500ms; on CPU this is infeasible regardless of TOP_K (see `12mns-enh dynamic-vector-top-k` for the benchmark).

**Per-query timing:**

`search_combined` returns `(results, reranked, vector_ms, rerank_ms, definition_boosted, second_hop_symbols)`. `code_ask_response` adds `total_ms` (wall-clock for the entire handler). All three timing values are emitted in the MCP response and printed to the server log per invocation as `[wavefoundry] code_ask timing: total=Xms vector=Yms rerank=Zms`.

**`search_combined` execution pipeline (reranker path):**

```
1. Vector fetch (timed as vector_ms)
 ├─ Embed query with DOCS_MODEL → cosine search over docs index → top_k candidates
 ├─ Embed query with CODE_MODEL → cosine search over code index → top_k candidates
 ├─ top_k = VECTOR_TOP_K_EXPLANATORY (50) for explanatory or assessment; VECTOR_TOP_K (30) otherwise
 └─ Every substrate query records (source, window, rows returned) in the call's accounting ledger

2. Lexical fusion + definition/artifact augmentation
 ├─ Assessment only: embed and search the derived docs query (query + audit/findings vocabulary),
 dedupe its hits into the docs pool at their own cosine; no path class is injected
 ├─ Merge published BM25 candidates into the vector pool and preserve multi-source agreement
 (assessment also merges the derived query's docs-kind BM25 hits)
 ├─ Direct file/path artifact: inject the named path's published owner rows (score=0.0) so the
 rank-one pin never depends on vector recall of a small file
 └─ For each DEFINITION_BOOST_RULES entry whose vocabulary matches the query:
 keyword-search on the most specific matching term, inject ≤ DEFINITION_BOOST_CANDIDATES (5)
 hits with score=0.0 into the combined pool; record rule label in definition_boosted

3. Rerank + bounded priors
 ├─ _agent_rerank(query, all_candidates) — cross-encoder scores each [query, text] pair
 ├─ _demote_doc_results() for navigational and explanatory-like questions
 ├─ _apply_assessment_evidence_prior() for assessment: docs/reports/ recovers the report
 down-weight as a path class, docs/waves/ receives the historical down-weight (score-only)
 └─ _demote_low_information_results() for every question, with direct-artifact exemption

4. Agent candidate selection
 └─ Apply per-index floor, relevance drop-off, text budget, and navigational code tilt

5. Type-agnostic graph signal (see Decision 11)
 ├─ Resolve query symbols and selected semantic context against the published graph
 ├─ Return relationship-grouped graph_related and second_hop_symbols
 └─ When reranked, merge the strongest cross-file graph neighbors into citations

6. Infrastructure partition (explanatory or assessment)
 └─ _partition_infra(): stable-push INFRASTRUCTURE_PATH_SEGMENTS citations to end

7. Stable pins: the strongest eligible exact path/basename owner of a directly named file at
 rank one (skipped when the question is mechanism-framed), then a verified exact symbol owner
 when the narrower owner-correction gate applies

8. Return results and retrieval/graph metadata; code_ask_response adds retrieval_accounting
```

**Substrate-query accounting (wave 1wpif, `1wpah`).** Every public retrieval call opens a context-local
accounting ledger; each SQLite vector search, each FTS5 MATCH per table (recorded inside the
`_fts_probed_fetch` chokepoint), and each live keyword pass records its source, window, and returned-row
count, adding no substrate work of its own. `code_ask` exposes the result as `retrieval_accounting`
(`sources`, `substrate_queries`, `examined_rows`, `ceiling`, `windows`) and `code_search` does the same.
The declared sources fix the stated ceiling at 4 queries / 240 examined rows per source: `code_ask` fuses
`docs_dense`, `code_dense`, `docs_lexical`, and `code_lexical` (16 / 960); the live keyword pass (the
artifact-anchored exact-first pass or the thin-citations pass) is accounted as a fifth source when it
fires (20 / 1200); the assessment-class derived docs expansion (one extra docs vector query plus one extra
lexical pass over both tables, docs-kind rows retained) counts inside those per-source budgets as distinct
query texts. Definition-boost keyword injections, direct-artifact owner-row reads, the published-graph
declaration lookup, and graph-signal expansion are store reads, not substrate searches, and sit outside
the definition. A source's `examined_rows` is the sum over distinct query texts of the largest returned
count (nested refill windows re-examine a prefix, so rounds are not summed).

**`search_combined` no-reranker degradation (reranker disabled/unbuildable):**

The former `_rrf_merge` fallback path was removed with the rerank-first unification (`1p52p`) — there is no
separate RRF pipeline anymore. When the cross-encoder cannot run, the single pipeline degrades in place:
ordering falls back to vector/coverage order over uncalibrated raw shared-embedder cosines (`reranked=false`, confidence capped at
`medium`) and lexical candidates join with rank-derived fallback scores. The structural `graph_related`
signal remains available when graph symbols resolve, but graph neighbors are merged into semantic citations
only when the cross-encoder ran.

### Decision 9: `max_per_file` cap in `code_search` for result diversity

Without a per-file cap, `code_search` can return many chunks from a single large file when that file dominates cosine similarity scores — useful for deep dives into one file, but unhelpful for orientation across the codebase. The `max_per_file` parameter caps how many chunks from the same file can appear in results. The highest-scoring chunk per file is always retained when the cap is applied.

**Candidate generation contract (wave 1wpif, `1wpah`).** Order is: predicate pushdown (`kind`, `tags`, and an allowlisted `language`) into BOTH candidate sources → a bounded candidate window per source → RRF merge to the window → the per-file cap (with bounded refill when underfilled) → the cross-encoder over at most the pre-refill window → `[:limit]`.

- *Pushdown.* A `language` value (single name, raw extension, or category) resolves through the fixed allowlist in `server_impl._language_filter_names` (the public extension map, the category map, and the chunker's stored-language vocabulary) into a set of canonical names; the set enters the SQLite vector query through its validated filter grammar, which binds values into the SQL `WHERE` before its result limit, and the FTS5 `WHERE` as a bound `language IN (?, ...)` (`index_state_store.fts_search(languages=...)`, reached only through the `_fts_probed_fetch` chokepoint). A value outside the allowlist is never echoed into a predicate (SEC-4): it stays a row-level equality guard served by the refill below. Before this change the language filter ran after a global window of `max(4 * limit, 30)` rows, so a selected-language row at rank 31 or beyond was a false zero on both the healthy hybrid path and the lexical fallback (AC-1); a pushed-down language keeps that former window as its single query.
- *Bounded refill.* A per-file cap (or a non-allowlisted language) cannot be pushed down. `search_code` and the lexical fallback (`_fts_degraded_serve`) then continue bounded retrieval over the monotonic, nested windows `REFILL_WINDOWS = (30, 60, 120, 240)` per source/table, stopping as soon as `limit` capped rows exist. A source that returned fewer rows than its window is exhausted and is not queried again. Per public call each source is queried at most `REFILL_MAX_QUERIES_PER_SOURCE = 4` times and examines at most `REFILL_MAX_ROWS_PER_SOURCE = 240` distinct rows; hostile skew (hundreds of top-ranked chunks in one file) therefore terminates after exactly four queries per open source.
- *Typed outcomes.* The response's `fill` object reports `requested`, `returned`, `rounds`, `windows`, `constraints`, and `reason`: `null` when filled, `substrate_exhausted` when every source returned fewer rows than its window (a genuine underfill), or `bounded_ceiling_reached` when the last window exited still underfilled with a source still open (eligible rows may remain). Both underfill reasons are also attached as diagnostics of the same code (informational: the response status stays `ok`); the ceiling diagnostic carries the round count and points at `retrieval_accounting` for the examined-row counts and at `code_keyword` / `code_pattern` for an exhaustive pass.
- *Reranker window.* Refill widens the per-file selection, never the cross-encoder cap: the candidates handed to `_rerank` are truncated to the pre-1wpah window `max(4 * limit, 30)` (`rerank_window`), so the reranker's input size is unchanged by this change (PERF-RDY-4).
- *Accounting.* `code_search` declares two sources (`code_dense`, `code_lexical`: 8 queries / 480 examined rows per call); `retrieval_accounting` on every healthy envelope reports the per-source `queries`, `examined_rows`, and `windows` actually used.

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

**Note:** The former RRF fallback path no longer exists. With the reranker unavailable, the one agent
pipeline degrades in place to vector/coverage ordering; injected candidates remain in the combined pool
and compete on the available fallback scores.

### Decision 11: Agent graph expansion is structural and question-type agnostic

Vector and lexical retrieval answer from text similarity. The current single agent path also asks
the already-published graph for structural neighbors when a query symbol or selected semantic
context resolves. This graph pass is not gated on `question_type`: navigational, explanatory,
instructional, artifact-anchored, and assessment questions can all receive it.

Direction follows query intent. Caller/reader/usage questions expand inbound relations from the
named symbol; behavioral questions can expand the named symbol and semantic context in both
directions. Results are grouped in `graph_related` by relationship (`callers`, `readers`,
`importers`, inheritance relationships, SQL writers/mappings, or generic `related`) rather than
being presented as zero-score semantic citations. `symbol_extraction_method: "graph"` identifies
the path, and `second_hop_symbols` lists the graph seeds followed.

The structural section is available independently of cross-encoder success. When reranking did
run, a bounded set of strong cross-file graph neighbors may also be merged into `citations` with
`from_graph: true`; the merge is additive and does not reorder semantic citations. A structural
match already present as a citation is marked `also_cited` and its duplicate excerpt is omitted.
Generic-word seeds, test-file neighbors, and whole-file module nodes are suppressed, and
`AGENT_GRAPH_SIGNAL_CAP` / `AGENT_GRAPH_CITATION_CAP` bound response and query work.

This type-agnostic graph expansion is separate from defensive known-symbol owner correction. The
latter is deliberately narrower: only navigational and explanatory-like (`explanatory` or
`assessment`) questions can stable-pin one hash-verified exact declaration ahead of usages.

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

`code_search`/`code_ask`/`code_lexical` have NO degraded path on a not-ready index — they refuse (`index_not_ready`, the 1sed7 lockout). `code_ask` classifies the weak generated-symbol/config/tool artifact exact-first short circuit as `search_mode: "exact"` (healthy); direct file/path artifact questions remain `hybrid`. It caps confidence in lexical fallback. The legacy `mode: "semantic" | "lexical"` field remains for back-compat; `search_mode` is the authoritative signal.

For code navigation (Layer 2 and 3), there is no fallback: the tools either return results or return a clear empty/unsupported response. This is intentional — exact and symbol navigation are not degraded by missing infrastructure, only by missing language support.

---

## Hybrid Lexical Layer (SQLite FTS5)

Wave 1rsh9 added the retrieval-quality lever the project's own findings kept pointing at: hybrid lexical + reranking, not a better embedder. Dense retrieval is weakest exactly where agents need precision — exact identifiers, rare tokens, error strings — and the cross-encoder can only rerank candidates the fetch actually surfaced.

**Mechanics.** The shared index-state database carries separate external-content FTS5 tables
(`fts_docs`, `fts_code`), linked by integer rowid to each layer's canonical chunks. Canonical row
triggers update FTS postings in the same transaction as vectors and indexing state. Text is stored
once. Reconciliation repairs derived FTS/registry data from canonical chunks without deleting vectors.
Native FTS integrity checks compare postings with canonical text, including positional damage that
row counts cannot detect. The per-row payload digest remains XOR-aggregated and maintained with
incremental removals/additions inside the write transaction. It detects accidental corruption and
partial writes; it is not tamper evidence. The tokenizer remains `unicode61 tokenchars '_'`, preserving
compound identifiers as whole tokens.

**Fusion.** `search_combined` (the `code_ask` retrieval core) fetches top-`LEXICAL_TOP_K` BM25 candidates per table alongside the vector candidates and merges them into the pool **before** the cross-encoder rerank, so the reranker arbitrates on one unified scale. Lexical hits form a third selection source, so the selection's key-merge unions `sources` — a chunk found by both passes carries `["code", "lexical"]` (multi-source agreement, same convention RRF fusion rewarded). The selection's dedupe identity is content-aware (wave `1wpif`, `1wngv`): candidates merge on `(normalized_path, normalized_lines, chunk_hash)`, with a deterministic sha256 digest of the canonical returned evidence fields (id, kind, section, text) standing in when `chunk_hash` is absent (lexical FTS rows, injected keyword/graph candidates). Only identical keys merge and merged evidence keeps its `sources` provenance, so two distinct chunks that share a path and legacy line range both survive selection while an exact cross-source clone still collapses to one representative. User query text reaches FTS5 only as a bound parameter with every token quoted (operators become literals); a query FTS5 rejects degrades that call to vector-only with no error. When the reranker is unavailable, lexical candidates get rank-derived fallback scores (`LEXICAL_RRF_FALLBACK_WEIGHT`). Kill switch: `WAVEFOUNDRY_DISABLE_LEXICAL_FUSION`.

**Availability.** FTS5 presence is probed once per process and recorded in store meta; absence degrades to vector-only retrieval with no lexical tables and no errors. `code_keyword` is untouched — live grep remains the exactness contract; FTS is a ranked-retrieval candidate source, not a keyword-tool replacement.

**Honest serving (wave 1wpif, `1wpag`).** Every public FTS read goes through one probed-serving chokepoint (`server_impl._fts_probed_fetch`): `code_lexical`, the hybrid FTS half of `code_search` / `code_ask` (`_fts5_lexical_search`, `_lexical_candidates`), and the degraded fallbacks (`_fts_degraded_serve`; healthy `docs_search` is dense-only and participates only there), so the paths cannot re-diverge into a silent healthy zero. The serve decision is an O(1) read of an in-process verdict cache keyed by the 1sed7 build-state token: the full probe (`index_state_store.fts_state_verdict`: liveness, canonical/vector/registry parity, native posting integrity and keyed digest) runs once per build-state transition per table, or once after a serving error (`fts_search(strict=True)` re-raises table-state errors instead of swallowing them to `[]`), and is then cached, so a warmed read performs no `COUNT(*)`, no `quick_check`, and no corpus scan; the per-call health/coverage tie-in `code_lexical` used to run is the same epoch-cached read. Before repair every affected query is typed, never a healthy zero: `code_lexical` returns `status: error` with `failure_reason: query_failed` (plus `damaged_tables` and a bounded, repo-relative `detail`), the degraded fallbacks keep their typed `{available, failure_reason, results, coverage}` result, and a healthy hybrid response keeps its semantic results and carries a `lexical_undercoverage` diagnostic (and a gap on `code_ask`). Healthy zero-hit queries keep their existing contracts. The query path never heals and never writes: damage at most schedules healing through the single-flight background refresh, and the indexer's ordinary reconcile path (the end-of-build reconcile, or the zero-change probe `_chunk_index_needs_heal`, which consults the same verdict) heals under the build lock and, as the lock owner, writes the per-table heal marker naming the build attempt it healed under. A table re-damaged within the epoch that already healed it is not healed again: the typed failure persists until the next epoch. `index_health` reports, per table, FTS-versus-registry row parity, liveness, the recorded digest state, the heal marker, and the epoch-cached verdict (`state_store.fts`), with an `fts_integrity_failed` diagnostic on damage.

**One lexical engine.** The FTS5 layer is the ONLY lexical index. The former Lance/Tantivy FTS (retired in wave 1rsh9/1sauc) rebuilt whole on every changed build and leaked un-GC-able index versions under `_indices/` (measured 98 MB on this repo); its one consumer — `search_code`'s hybrid lexical half — now reads the FTS5 tables (`kind`/`tags` and, since wave 1wpif `1wpah`, the allowlisted `language` set all filter inside the query as bound parameters; rows still carry `language` for the row guard; scores are −bm25 so the RRF merge order holds), and verified migration cleanup retires the obsolete Lance stores, including their legacy indices.

---

## Index Format

```text
.wavefoundry/index/
  index.sqlite          Canonical docs/code chunks, FP32 vectors, external FTS,
                        chunk registry/digests, file/layer bookkeeping, build epoch,
                        freshness/attribution, secret-scan cache, graph nodes and
                        edge evidence, per-file extraction/merge state, communities
                        and analysis, and the codebase-map receipt (schema 8)
  index.sqlite-wal / -shm         SQLite-managed companions when present
  memory-state.sqlite             Agent memory — the one store that stays separate
  sqlite-migration.json           Upgrade progress and recovery receipt
```

The shared database is opened through the qualified APSW runtime. Unknown schema versions and
corrupt canonical data are retained and refused, never dropped automatically. The memory database
retains its existing separate authority. Wave `1xny6` retired the separate graph database, the
`graph/` directory with its payload files and the standalone codebase-map fingerprint; the
pre-rename `index-state.sqlite`, legacy `docs.lance/`, `code.lance/` and `__manifest/` remain only
until migration, new-process verification and owned cleanup succeed.

There is **no `meta.json`** (wave `1sed7`): the store's bookkeeping tables are the only source of per-path build state, and every consumer — indexer change detection, `WaveIndex` loading, MCP health/status, dashboard, upgrade version probes — reads the store (`export_meta_snapshot` provides the same dict shape the JSON used to carry). A store write failure is a structured build failure, never a silent fallback. A legacy `meta.json` left by a pre-`1sed7` install is never read by anything — including the upgrade's version probes (an absent/empty store reads as unknown, which forces convergence) — and is removed after the first successful build.

**Degradation ladder (wave `1seav`):** semantic/hybrid retrieval is the healthy path; when the
embedding model is unavailable but the index is PUBLISHED (captured complete epoch), the tools
serve BM25 results from the FTS5 layer with filters preserved (`search_mode: lexical_fallback`,
confidence capped for `code_ask`); when no published index exists, `docs_search` serves the
live-filesystem walk (`live_fallback` — the only state where it is reachable; a healthy store
never walks) and the code tools refuse (`index_not_ready` — unchanged from 1sed7). The shared
FTS serving path returns a typed `{available, failure_reason, results, coverage}` result so
infrastructure failure (`query_failed`) is never presented as an empty corpus.

**Readiness — the build epoch (wave `1sed7`):** the store's `build_state` row is a small state machine (`uninitialized` → `building` → `complete`). A mutating build commits a FULL-durable `building` fence BEFORE semantic or graph mutation and publishes completion with an attempt-ID compare-and-set transaction — the only operation that advances the build `generation`. Readers (`docs_search`, `code_search`, `code_ask`, `code_lexical`, `seed_get`, `wf_map`) capture the FULL state token `(attempt_id, status, generation)` — ABA-proof; every fence and every publication changes it — before the operation and re-validate the SAME token after: any transition means the result set could span two index states, so results are discarded (`index_not_ready`). The strict code tools additionally refuse up front unless the captured token's status is `complete`; `docs_search`/`seed_get`/`wf_map` serve sanctioned degraded/disk paths under a STABLE non-complete state. `WaveIndex` reload uses the same token as its freshness signature, so a completed build invalidates cached handles without a server restart. `docs_search`'s live-filesystem walk (plus `seed_get`/`wf_map`'s disk fallbacks) are the sanctioned degraded paths when no complete epoch exists; the code retrieval tools refuse outright (the global publication includes graph and other work outside the shared semantic transaction). A `building` epoch whose build lock is gone reads as *interrupted* — still fail-closed, healed by the next ordinary build superseding the dead attempt (a zero-change retry performs this recovery explicitly: reconcile, bookkeeping refresh, finalize). Completion is globally gated: a scoped build over a reset store (canonical chunks present without matching layer provenance) escalates to all-layer convergence before it may publish, a rear guard refuses finalization if any present table would publish unprovenanced, and the derived-FTS/optimize maintenance verbs are restore-only — they refuse on a store with no completed epoch and never manufacture `complete`.

**Chunk schema:**

```json
{
 "id": "unique string",
 "path": "repo-relative/path/to/file.md",
 "kind": "doc | doc-summary | doc-code | seed | prompt | code | code-summary | python | ...",
 "language": "python | null",
 "lines": [start_line, end_line],
 "section": "Header text or null",
 "text": "chunk text — what was embedded"
}
```

The `kind` field now includes two orientation kinds:
- `code-summary` — file-level symbol index for source files; routes to code index
- `doc-summary` — heading index for markdown files; routes to docs index
- `code` chunks for YAML/JSON gain a curated spec-aware path since wave `1wfsl` (`1wfr8`): content-detected OpenAPI (3.x YAML/JSON, Swagger 2.x — root `openapi:`/`swagger:` key) and JSON Schema files (json-schema.org `$schema` dialect URI, or a schema-shaped root passing value-shape guards; schemastore config references and data files with coincidental `type`/`properties` keys stay flat) chunk at operation / definition / property level with the breadcrumb baked into kind="code" text (`paths./users/{id}.get:`); undetected files chunk byte-identically (differential-pinned), and non-curated sections of DETECTED specs (servers, security schemes, webhooks, other components subsections) keep full coverage through per-subsection and residue chunks (delivery finding ARCH-DEL-1), so detection never loses content flat emission served. Measured on the committed golden set (re-run after the residue repair): recall at 5 0.833 to 1.000, MRR 0.819 to 0.948 — shipped DEFAULT-ON per the numeric bar, per-project override `indexing.spec_aware_chunking`
- `code` spec-family units (wave `1wik9`, `1wfso`) extend the curated pattern to three more formats behind the same `indexing.spec_aware_chunking` gate, each shipped DEFAULT-ON on its own recorded measurement: **AsyncAPI** is content-detected by the root `asyncapi:` key in already-corpus YAML/JSON (the JSON check precedes the JSON-Schema shape detection so order is deterministic) and chunks channel-plus-operation, per-operation (3.x), and message/schema component units with breadcrumbed summary/description prose plus the residue chunk (measured: recall at 5 0.875 to 1.0, MRR 0.573 to 0.692 on the frozen 8-query subset); **GraphQL SDL** (`.graphql`/`.gql`, extension-gated, bounded internal parser, no grammar dependency) chunks per-type-declaration units carrying block-string descriptions plus per-described-member units with type-path breadcrumbs like `Query.user:` (measured at the recall ceiling: 1.0 held, MRR 0.9375 to 1.0); **Protobuf** (`.proto`, extension-gated internal parser) chunks message/enum/service units pairing attached leading comments with bodies plus rpc/field units for commented members under package-qualified breadcrumbs like `accounts.v1.UserService.GetUser:` — detached comments and options create no units (measured at ceiling: 1.0/1.0 held). Undetected and gate-off files chunk byte-identically; per-format content-coverage differentials (ARCH-DEL-1 pattern) prove zero coverage loss with revert-simulation.
- `doc` section chunks come from markdown AND, since wave `1wfsl` (`1wfsm`), reStructuredText (`.rst`) and AsciiDoc (`.adoc`/`.asciidoc`) — section-chunked with the same breadcrumb lever, code/listing bodies extracted per the next bullet, matched-pair golden-set measurement recorded as wave evidence (rst recall at 5 matches markdown; adoc within two twin-competition ranks)
- `doc-code` (wave `1wik9`, `1whup`) — fenced code blocks, rst code-directive bodies, and adoc listing blocks extracted from documentation files route to the DOCS index via `_is_docs_kind` (previously they were emitted as `kind="code"` and the per-table eligibility gate dropped them from BOTH tables, because docs files are never code-eligible). Identities carry a FILE-PASS-scoped ordinal (`{prefix}:code-N`, one counter per chunk_file invocation — per-section resets collide on duplicate-titled sections and the delta planner keys by chunk id); text keeps the section breadcrumb (baked for markdown fences, injected for rst/adoc via `_DOCS_BREADCRUMB_KINDS`); the code size cap applies; prompt-kind files keep fences inline by design; notebook code cells join `doc-code` (wave `1wl7u`, `1wh1b`: `#cell-N` ids and notebook-level kernel language unchanged, outputs stay unindexed; the `1whup` preserved-invisibility disposition is superseded — on the frozen notebook golden queries, code-cell recall at 5 went 0.0 to 1.0). Since `1whuq` (same wave) the kind also carries standalone hand-authored diagram files — Mermaid (`.mmd`/`.mermaid`), PlantUML (`.puml`/`.plantuml`), Graphviz DOT (`.dot`/`.gv`) — as ONE unit per file: a breadcrumb line from the declared title (mermaid frontmatter/`title` line, plantuml `title`, the DOT graph identifier) or the file stem, then the raw source (labels are the retrieval value; no diagram parsing). Registration is chunker-only (never `_KNOWN_TEXT_EXTENSIONS` — sniff bypass, binary `.dot` Word-template namesake; no walker bump), eligibility is whole-repo outside `.wavefoundry/`, and tool-generated formats contribute their extracted LABELS instead of raw serializations (wave `1wl7w`, `1wl7v`, superseding both walk exclusions): draw.io (`.drawio`) emits one breadcrumbed label unit per diagram page — `mxCell` values plus `object`/`UserObject` wrapper labels, both the canonical compressed and plain save forms, HTML markup stripped, ids `#diagram`/`#diagram~k`, a bounded per-page inflate cap against decompression bombs — and Excalidraw (`.excalidraw`) one text-and-frame unit per board with `isDeleted` ghosts skipped; degenerate inputs emit zero chunks, and geometry/style serializations are never indexed. Measured on the frozen extended diagrams golden set per format; ambiguous extensions (`.d2`, Structurizr `.dsl`) stay out by decision. Measured on the frozen 9-query `diagrams` golden set: 0.0 to 1.0 recall at 5 and MRR 1.0 (every query ranks its diagram first); post-landing prose aggregates byte-identical (per-set-disjoint corpora). Filterable via `docs_search(kind='doc-code')`; excluded from the `architecture` virtual kind (doc-summary precedent). Measured on the extended prose golden set: fence-targeted queries 0.0 to 1.0 recall at 5 on all three formats; content-anchored per-format prose aggregates unchanged at 0.875 (zero content losses; file-attributed movements are matched-trio tie-shuffle, dispositioned in the wave evidence)

The `text` field is what was embedded. The `path` and `lines` fields are what the agent sees in results. Keeping the two separate means the embedded text can be a normalized or chunked version of the file without changing what's reported back.

---

## Temporal Decay: Per-Citation Freshness and the Drift Partition (wave 1ro44)

Retrieval ranks by relevance; temporal currency is surfaced as **annotation first, demotion only on strong
evidence** — raw scores are never blended with age (the rejected alternative is recorded in the change doc's
Decision Log: score-perturbation buries correct answers about stable code, since old ≠ wrong).

**Build-time substrate** (`index.sqlite`, optional residents at the build tail — never fail a build, no
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

**Agent memory retrieval** (waves 1ro44 / 1tbt5 / 1yad2): typed memory
records under `docs/agents/memory/` remain the source of truth. Explicit free-text
`memory_search` filters eligibility, kind and exact target/symbol constraints
before retrieving at most 20 semantic identities and 20 lexical identities.
Eligible body files are SHA-256 checked against their published docs-layer
source hashes inside the vector read transaction. Missing or changed source
provenance takes the explicit fallback path. The SQLite query groups eligible
chunk distances by canonical path before its limit; compact archive entries remain individual lexical identities. Equal-weight
RRF (k=60) orders the union. Only the first five candidates receive CPU
cross-encoder checks of their summary (title when summary is empty), with raw
finite logit >= -4 admitted; rejected records do not trigger an unchecked refill.
The result cap is the smaller of five and the caller's limit, in RRF order.

These are relevance-screened search candidates, not verified answers or current
authority. The calling agent evaluates each record's relevance, applicability
and evidence, just as it does for semantic, lexical and graph results. Original
confidence, status, provenance and successor metadata remain visible. Ranking
neither promotes a record's authority nor resolves conflicting instructions.
The local search makes no extra host-agent or remote model call.

Empty-query/target-only listings, `memory_brief` and unsolicited advisories retain
policy/freshness ordering: exact-target class, confidence, status and family
precede adaptive freshness and later tie-breaks. A batched per-target commit
history read drives adaptive half-lives; decisions/preferences do not age-decay,
and fragile-file churn requests re-verification. The shared policy sort is not
changed for other consumers.

Unavailable, incomplete or stale semantic state, intentionally unindexed history,
or failed/unavailable qualification uses the existing all-token lexical-policy
recovery with explicit unavailable/fallback metadata. It never labels unchecked
semantic candidates as screened results. A healthy empty result is distinguishable
from degraded retrieval. If CPU model loading failed, check the reranker-disable
setting and local runtime/model availability, run `wf setup` if provisioning is
needed, then restart MCP to clear the cached load failure. Index refresh alone
does not clear that failure. Ordinary code/docs search is unchanged. The memory
evaluator's sampled self-summary output remains nonqualifying; detailed independent
qualification is an explicit local run. See `docs/references/memory-retrieval-eval.md`.
Physical archive bodies under `docs/agents/memory/archive/` are a historical
storage class and are excluded by both repository walking and explicit-file
index seams; graph extraction applies the same boundary. The compact register at
`docs/agents/memory-archive.md` remains indexable and searchable. Normal targeted
memory search may return a register entry, while `include_history=true` or
`status="archived"` reads the archived body directly from the record store.

## Index Readiness: Two Surfaces (wave 1t59p)

Index health is deliberately split into a fast surface and a deep surface:

- **`wf_audit` (bounded metadata snapshot):** readiness from the index control plane only — completed build
  epoch (SQLite), bounded layer-presence checks and the build summary (`read_build_summary`: layer
  scalars plus one COUNT, never per-file rows), configured include-prefixes. It never
  loads vector payloads, never materializes per-file store rows, and never hashes the
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
