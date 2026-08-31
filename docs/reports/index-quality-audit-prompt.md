# Index Quality Audit Prompt

Owner: Engineering
Status: active
Last verified: 2026-08-30

## Purpose

Provide a reusable, read-only multi-agent prompt for auditing Wavefoundry's semantic, full-text, and graph indexes for retrieval-quality improvements, correctness defects, coverage gaps, and operational concerns.

## Prompt

Perform a read-only, evidence-driven audit of Wavefoundry's semantic, full-text, and graph indexes. The objective is to find concrete ways to improve indexing and retrieval quality and identify bugs, correctness issues, coverage gaps, performance risks, misleading diagnostics, and maintainability concerns.

Do not edit repository files, rebuild indexes, create change docs, mutate wave state, or implement fixes. Temporary evaluation output may be written under a temporary directory only. End with findings and recommendations suitable as input to a future **Plan feature** workflow.

### Coordination

You are the coordinator. Read `AGENTS.md` and the required startup documents first. Follow the repository's Guru workflow in `docs/agents/guru.md`.

Capture a read-only baseline using:

- `index_health()`
- `index_build_status()`; use `lock.held` as the authority, never the presence of the lock file
- `git status --short`
- Current index sizes, row counts, graph node/edge counts, chunker version, builder versions, and degraded-mode signals

Then spawn exactly three subagents concurrently:

1. `semantic_index_review`
2. `full_text_index_review`
3. `graph_index_review`

Each subagent must act as a Guru/reviewer, use the Wavefoundry MCP retrieval tools before native searching, and validate conclusions with `code_outline` followed by targeted `code_read`. A subagent must not report a semantic-search result, documentation claim, or graph edge as fact without validating it against source code, a deterministic query, a test, or a bounded executable probe.

Keep the coordinator slot free for cross-layer analysis and final synthesis.

### Shared rules for all subagents

Each subagent must:

- Remain read-only.
- Consult any applicable area `AGENTS.md`.
- Inspect current implementation, tests, architecture docs, historical changes, and known open plans.
- Distinguish current implementation evidence from historical wave records.
- Check whether a suspected issue is already planned, fixed, superseded, accepted, or intentionally constrained.
- Prefer public MCP tool paths for behavioral probes.
- Record expected versus observed results for every claimed defect.
- Attempt to falsify each material hypothesis.
- Report negative findings explicitly instead of turning speculation into an issue.
- Separate indexing defects from retrieval/ranking defects.
- Separate correctness, relevance, completeness, freshness, performance, observability, and maintainability concerns.
- Treat empty graph results as possible extraction gaps until corroborated with `code_references` or exact search.
- Inspect graph edge `relation`, `kind`, and `confidence`; never equate every graph path with a call chain.
- Avoid expensive full rebuilds and network access.
- Include symbol-led citations in the form `symbol (path:start-end)`.

Use this finding schema:

- ID and title
- Layer
- Classification: bug | retrieval-quality gap | coverage gap | performance risk | reliability risk | observability gap | maintainability concern | not an issue
- Severity: critical | high | medium | low
- Status: new | already known | already planned | superseded | intentional constraint
- Expected behavior
- Observed behavior
- Reproduction or evaluation query
- Source/test evidence
- User or agent impact
- Root-cause hypothesis
- Falsification attempt and result
- Confidence
- Recommended correction
- Verification needed for the correction
- Estimated scope and affected modules
- Actionability: `do_now` | `maybe_later` | `dont_do_later` | `not_issue`

Do not recommend an abstraction, model replacement, or large rewrite without measured evidence that the existing mechanism is the limiting factor.

### Subagent 1: Semantic index and retrieval

Audit the complete semantic pipeline:

- Corpus discovery, ignores, include-prefix behavior, secrets handling, generated-file exclusions, and docs/code layer routing
- Chunk dispatch, structural chunking, summary chunks, breadcrumbs, size guards, fallback chunking, chunk identity stability, and content loss
- Embedding models, query/document prefixes, batching, truncation, vector normalization, LanceDB indexing, ANN parameters, incremental updates, and stale-row cleanup
- Candidate generation, filtering, candidate-window sizes, dense/lexical fusion, cross-encoder reranking, result selection, partitioning, confidence calibration, second-hop expansion, freshness signals, and degraded modes
- Differences between `docs_search`, `code_search`, and `code_ask`
- Whether evaluation harnesses exercise the real shipped hybrid/reranked path or only isolated dense cosine retrieval

Begin with:

- `docs/architecture/search-architecture.md`
- `docs/architecture/chunking-and-indexing-pipeline.md`
- `.wavefoundry/framework/scripts/chunker.py`
  - `chunk_file`
  - `_chunk_file_dispatch`
  - Summary and oversized-chunk helpers
- `.wavefoundry/framework/scripts/indexer.py`
  - Model and ANN constants
  - `build_index`
  - `_build_index_locked`
  - Incremental and streaming rebuild paths
- `.wavefoundry/framework/scripts/server_impl.py`
  - `WaveIndex.search_docs`
  - `WaveIndex.search_code`
  - `WaveIndex.search_combined`
  - Reranking, RRF, partition, confidence, and graph-signal helpers
- `.wavefoundry/framework/scripts/benchmarks/embed_bench.py`
- `.wavefoundry/framework/scripts/benchmarks/retrieval_eval.json`
- `.wavefoundry/framework/scripts/tests/fixtures/retrieval_golden/run_retrieval_eval.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`

Run a bounded set of representative queries covering paraphrases, architecture questions, known symbols, exact identifiers, error strings, rare tokens, enumeration, irrelevant-query abstention, and symptom-only bug localization. Inspect top results and the first relevant rank rather than trusting aggregate scores alone.

### Subagent 2: Full-text/FTS5 index and retrieval

Audit the complete full-text path:

- FTS schema creation and lifecycle
- Tokenizer behavior, especially `snake_case`, punctuation, qualified names, paths, partial identifiers, quoted strings, and error messages
- Safe MATCH-expression construction and query-token limits
- BM25 ranking and length-normalization effects
- Kind, tag, language, and table filtering
- Dense/lexical fusion and RRF weighting
- Coverage parity between Lance rows, the chunk registry, and FTS rows
- Incremental insert, update, delete, reconcile, recovery, merge, vacuum, and cold-start behavior
- Published-epoch consistency and behavior during interrupted builds
- `lexical_fallback`, `live_fallback`, fallback reasons, diagnostics, and zero-hit honesty
- Direct `code_lexical` behavior versus lexical candidates used internally by semantic tools
- Cases where summaries outrank implementation bodies or compound identifiers become unintentionally undiscoverable

Begin with:

- `.wavefoundry/framework/scripts/index_state_store.py`
  - `IndexStateStore`
  - `rebuild_chunk_index`
  - `reconcile_chunk_index`
  - `_fts_match_expression`
  - `fts_probe`
  - `fts_search`
  - Build-epoch functions
- `.wavefoundry/framework/scripts/indexer.py`
  - Derived-state rebuild and healing paths
- `.wavefoundry/framework/scripts/server_impl.py`
  - `_fts5_lexical_search`
  - `_lexical_candidates`
  - `_rrf_merge`
  - `_fts_degraded_serve`
  - `code_lexical_response`
  - `docs_search_response`
  - `code_search_response`
- Relevant retrieval and state-store tests

Construct exact-token probes for full identifiers, identifier prefixes and suffixes, camelCase, dotted names, file paths, punctuation-heavy errors, multiple-token queries, stopword-heavy queries, Unicode, malformed syntax, empty queries, and high-frequency tokens. Verify both ranking and diagnostic behavior.

### Subagent 3: Structural graph index and retrieval

Audit graph extraction, persistence, clustering, and query correctness:

- Corpus inclusion and exclusion parity with semantic indexing
- Incremental merge and removal behavior
- Builder/schema versioning, stale-artifact detection, publication consistency, and auto-rebuild behavior
- Extraction coverage by supported language and file type
- Definitions, imports, calls, construction, inheritance, reads/writes, config reads, doc-to-code references, and external nodes
- Receiver/type resolution, overloaded symbols, same-name collisions, heuristic `EXTRACTED` edges, missing confidence fields, and phantom edges
- Large-file and unavailable-parser fallback behavior
- `GraphQueryIndex` construction and cache invalidation
- Path traversal semantics and edge-cost choices
- Call hierarchy, impact, risk, dependency, community, and graph-report correctness
- Generated/external filtering, collapse views, clustering stability, hub stability, and centrality interpretation
- Whether graph quality has a representative ground-truth evaluation or depends mainly on isolated unit fixtures

Begin with:

- `docs/architecture/graph-index-system.md`
- `.wavefoundry/framework/scripts/graph_indexer.py`
  - `GraphIndexSession`
  - Language extraction paths
  - `update_graph_index`
  - Graph state publication
- `.wavefoundry/framework/scripts/graph_query.py`
  - `_ensure_graph_builder_current`
  - `load_graph`
  - `get_query_index`
  - `GraphQueryIndex`
- `.wavefoundry/framework/scripts/graph_cluster.py`
- `.wavefoundry/framework/scripts/server_impl.py` graph response functions
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`
- `.wavefoundry/framework/scripts/tests/test_graph_query.py`
- `.wavefoundry/framework/scripts/tests/test_graph_cluster.py`

Build a small ground-truth sample across multiple relation types. Compare graph results with source definitions, `code_references`, and exact searches. Measure both false positives and false negatives. Include ambiguous same-named symbols, overloaded methods, constructors, dynamic calls, external APIs, test callers, generated files, config reads, and doc references.

### Coordinator's cross-layer review

While the subagents work, inspect the orchestration boundaries among:

- `chunker.py`
- `indexer.py`
- `index_state_store.py`
- `server_impl.py`
- `graph_indexer.py`
- `graph_query.py`
- `graph_cluster.py`

When the subagents return:

1. Deduplicate their findings.
2. Challenge at least the strongest and weakest finding from each lane.
3. Reproduce every critical or high-severity issue independently.
4. Identify cross-layer inconsistencies, including:
   - Corpus or exclusion differences
   - Stale semantic results paired with current graph results, or the reverse
   - FTS/Lance/registry coverage drift
   - Graph signals reinforcing irrelevant semantic candidates
   - Filters applied differently across tools
   - Confidence or fallback fields that overstate result quality
   - Evaluation harnesses that do not exercise the actual production path
5. Compare current coverage with prior waves and open plans so recommendations do not duplicate completed or admitted work.
6. Separate quick correctness fixes from larger research or architectural work.

### Final report

Return one consolidated report with:

1. Executive summary
2. Baseline index health and scope
3. Current end-to-end retrieval flow
4. Confirmed bugs
5. Retrieval-quality improvement opportunities
6. Graph accuracy and coverage concerns
7. FTS/tokenization and fallback concerns
8. Evaluation and observability gaps
9. Cross-layer risks
10. Prioritized recommendation table
11. Proposed evaluation suite additions
12. Investigated-but-not-an-issue findings
13. Open questions and limitations
14. Exact files, symbols, tests, and probes reviewed

Recommendations must be tied to evidence and a measurable success criterion such as Recall@k, MRR, nDCG, false-positive/false-negative rate, abstention accuracy, stale-result rate, p95 latency, index size, rebuild time, incremental-update time, or diagnostic correctness.

Do not implement anything. Conclude with the smallest coherent set of candidate changes that could be passed to separate **Plan feature** workflows.
