# Journal - Embedding Retrieval Architecture

Owner: Engineering
Status: active
Role: wave-coordinator
Last verified: 2026-06-13

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-06-11

wave-id: `1p4wz embedding-retrieval-architecture`

## Operating Identity

- **Role:** wave-coordinator for wave `1p4wz embedding-retrieval-architecture`. **Responsibility:** coordinate the wave's admitted changes through prepare → implement → review → close per the lifecycle contract.

## Salience Triggers

- **critical** — operator directives that change wave scope, admitted changes, or close authorization
- **high** — review-time findings that block close, dependency changes between admitted changes
- **medium** — implementation-time observations about scope drift or unexpected blockers
- **low** — routine coordination notes, status updates, lint pass/fail signals

## Default Stance

Maintain the wave's load-bearing invariants throughout implementation. Preserve the change-doc contracts admitted at prepare time; surface drift from operator immediately rather than silently absorbing scope.

## Memory Responsibilities

- Track per-change implementation state (gate-open/close pairs, AC completion, follow-up findings)
- Record decisions made during implementation that affected scope, AC formulation, or test strategy

## Active Signals

- Pending: wave `1p4wz embedding-retrieval-architecture` opened 2026-06-11; populate as admitted changes move through implementation.

- **high — 2026-06-13 full-path code review (all 5 changes).** Operator requested a thorough review of the whole embedding/retrieval path (dead code, deadlocks, segfaults, crashes, incomplete results, edge cases), council-checked, fix what needs no confirmation, collect the rest. Method: 4 parallel read-only deep reviews (server rerank path / indexer+setup / chunker+build_pack+graph / test quality) + direct read of `accel_embedder.py` and the rerank path; council double-check (red-team / architecture / qa / reality-checker). Every load-bearing finding re-verified against source before action. Full suite green throughout (`run_tests.py`, venv python).

  **Confirmed defects fixed in-session:**
  - **HIGH incomplete-results — rerank-first defeated for navigational/instructional.** `_agent_rerank` mutated `score`→sigmoid in place but left `_docs_src`/`_code_src` in pre-rerank cosine order, so the per-index floor picked top-K by stale cosine (explanatory was saved by `_demote_doc_results`'s re-sort; others weren't). Fix: sort each source by `score` desc before selection (`server_impl.py`, no-op for explanatory, correct for the rest, safe on CPU — same model within a source).
  - **MED embedding-quality — doc-summary breadcrumb pollution.** doc-summary chunks had the literal `"doc-summary\n"` sentinel prepended into the embedding (its `section` is a fixed label, not a heading). Removed `"doc-summary"` from `chunker._DOCS_BREADCRUMB_KINDS`; added a regression guard (`test_doc_summary_chunk_not_injected`).
  - **LOW→real crash-hardening — non-atomic `build_static_onnx`.** A reader (server lazily building the reranker while `setup_index` prewarms the same model; two indexer subprocesses) could mmap a half-written graph → ORT abort. Now writes to a temp path + `os.replace` (atomic).
  - **test gaps — false-green + missing coverage.** The 3 `symbol_injection_boost_*` tests re-implemented the boost arithmetic inline (passed regardless of production); rewrote them to drive real `_agent_rerank`, and added direct tests for the **sigmoid rewrite, rerank-first ordering, no-reranker no-op, and length-mismatch rejection** (the heart of 1p52p, previously untested).
  - **comment drift (×4 + more).** `accel_embedder.py`, `indexer.py`, `setup_index.py`, `server_impl.py` all still said "GPU-only / CPU skips reranking" — contradicting the shipped CPU INT8 reranker. Corrected throughout the rerank path.

  **Council overturned two agent claims:** (a) the "dead `_extract_symbols_*` chain — delete ~80 LOC" was actually test-covered (not a blind autofix) → routed to operator; (b) the "`_get_reranker` deadlock" — there are no locks, so it can't deadlock → reclassified as pre-existing lock-free lazy-init (efficiency, not a defect).

- **critical — 2026-06-13 operator decisions on review items.**
  - **Fix 2 (build concurrency) — DONE.** Added per-instance `threading.Lock` (`_reranker_lock`/`_embedder_lock`) with double-checked locking in `_get_reranker`/`_get_embedder`; fast path stays lock-free, only the one-time build/CoreML-compile/offload-probe is serialized (resolves the `process_time()` probe-pollution and the shared offline-env race). Resilient to `WaveIndex.__new__` bypass-constructed test objects.
  - **Fix 3 (navigational tilt) — DONE.** `_agent_weights` applied only when `agent_reranked` is True (the cross-source weight is meaningful only on the unified post-rerank sigmoid scale). Operator confirmed agent rerank behaves identically on GPU (FP16) and CPU (INT8) — the only no-rerank axis is "reranker unavailable" (disabled/unbuildable), not "CPU". Replaced the weak old test with `test_search_combined_navigational_tilt_only_when_reranked` (spies on the selection call: weight passed when reranked, `None` when not).
  - **Item 4 (FP16↔FP32 parity test, GPU-gated/CI-skipped) — left as-is** per operator.
  - **Item 5 (stale `bge-reranker-base` test fixtures) — refreshed** to reality: `_prewarm_required_model` is embedding-only now, so those fixtures use a current embedding model + `model_kind="embedding"`; `_get_reranker` tests use the current `cross-encoder/ms-marco-MiniLM-L-6-v2`; stale "None on a CPU machine" docstrings corrected.
  - **Item 1 (lexical second-hop chain) — REMOVED** per operator. Deleted `_extract_symbols_from_citations` + `_extract_symbols_ts`/`_python`/`_regex` (~165 LOC) and the dead-only constants `MAX_SYMBOLS_EXTRACTED`, `MAX_SECOND_HOP_CANDIDATES`, `_RE_CALL`/`_RE_SQL_EXEC`/`_RE_IMPORT`, `_TS_CALL_TYPES`, `_TS_MEMBER_TYPES`, `_SYMBOL_BLOCKLIST` (audited as chain-only) + 6 unit tests. Kept `_TS_IDENTIFIER_TYPES`/`_TS_SYMBOL_LANG_MAP`/`_get_chunker_module`/`INFRASTRUCTURE_PATH_SEGMENTS` (live elsewhere) and the `second_hop_symbols`/`symbol_extraction_method` return fields (now always `[]`/`"none"`, response contract). **Rationale:** the lexical "follow references one hop" approximation (parse citation text → guess symbol names → keyword-re-search) was superseded by the graph-based `graph_related` expansion (1p4hu), which follows real call/import/reads edges with intent-aware direction and a separate relationship-grouped presentation. Zero production callers; no behavior change.

## Distillation

- Pending: distilled lessons emerge as the wave delivers; promote durable findings to `docs/agents/journals/README.md` at close.

## Promotion Evidence

- Pending: promotion candidates against `docs/agents/journals/README.md` emerge as the wave delivers and durable lessons are identified.

## Retirement And Supersession

- Pending: retirement happens at wave close per the closure contract in `docs/agents/journals/README.md`.

## Governance

- This journal follows the operating-memory contract in `docs/agents/journals/README.md`. Critical/high signals may be journaled during planning, implementation, review, handoff, reindex, or closure — not only at close. Distillation, promotion, and retirement happen at close.
