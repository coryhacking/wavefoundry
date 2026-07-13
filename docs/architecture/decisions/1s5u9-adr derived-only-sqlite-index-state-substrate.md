# 1s5u9-adr — Derived-Only SQLite Index-State Substrate (with FTS5 Lexical Layer)

Owner: Engineering
Status: accepted (amended)
Last verified: 2026-07-12

## Context

The semantic index needed a home for relational sidecar state, and three concurrent needs made the gap acute. The churn-aware retrieval decay work needs per-file freshness/attribution tables whose values change on every build for active files — storing them in Lance rows would rewrite unchanged vectors and defeat `chunk_hash` reuse, while growing `meta.json` scales badly in whole-file rewrite and parse cost. The documented retrieval-quality lever is hybrid lexical + reranking, and LanceDB has no BM25 — hand-rolled term scoring bolted onto a vector store is a poor fit. And the secrets scanner's only state was a single-field `scan-state.json`, so any ruleset edit re-scanned the whole repository with no per-file memory.

The graph subsystem had already proven the embedded-SQLite pattern (wave 1p9q3): WAL journaling, single-transaction builds, version-gated whole-store invalidation, reset-and-recreate on corruption.

## Decision

One derived-only SQLite store per project index — `.wavefoundry/index/index-state.sqlite` — is the substrate for all semantic-index relational sidecar state, with resident schemas added under a single sequenced schema version: freshness/attribution tables, contentful FTS5 lexical tables fused into ranked retrieval pre-rerank, per-path build bookkeeping + chunk registry, and the per-file secret-scan cache.

**Amendment (2026-07-12, wave `1sed7`):** the store is now the SOLE semantic-index state authority — `meta.json` is retired entirely. The original decision demoted `meta.json` to an exported reader-contract-compatible snapshot; that dual surface allowed a JSON-success/SQLite-failure mode in which a build could publish JSON state the store could not serve. Now no `meta.json` is written or read at all — not even by the upgrade's version probes (an absent/empty store reads as unknown, forcing convergence; a legacy file is removed after the first successful convergence), a store write failure is a structured build failure (never a silent JSON fallback), and readiness is published exclusively through a FULL-durable build epoch: a `building` fence committed before the first Lance/FTS mutation and an attempt-ID compare-and-set completion that alone advances the build generation. Readers validate the complete-epoch token before and after every indexed operation and fail closed on any incomplete or changed state.

The load-bearing rules:

- **Derived-only:** every table rebuilds from git, Lance, and the repo itself; corruption or version mismatch is a loud drop-and-rebuild, never data loss. (Since the `1sed7` amendment a whole-store reset also erases build/readiness state, so recovery is mandatory all-layer convergence — re-chunk with vector reuse — never a manufactured per-layer state.)
- **Ordered consistency with Lance:** Lance is authoritative for chunk existence; store transactions commit after the corresponding Lance writes; an end-of-build chunk-id reconciliation repairs any crash window. Cross-engine atomicity is explicitly not claimed.
- **Extract-alongside, not refactor:** the store module (`index_state_store.py`) generalizes the graph store's proven posture without touching `graph_indexer.py` — the graph store's reviewed build path stays byte-identical.
- **One maintenance verb:** `wave_index_optimize` maintains every index — Lance compaction plus SQLite WAL checkpoint/truncate, `VACUUM`, `PRAGMA optimize`, FTS5 segment optimize, and a two-layer integrity check (structural pragmas + source-fingerprint staleness binding) — across the index-state store and the graph state store, under the index-build lock, on demand and at setup/upgrade.

## Consequences

**Positive:**
- Real BM25 lexical retrieval with zero new dependencies (FTS5 ships in Python's bundled SQLite), fused before the cross-encoder so one unified relevance scale arbitrates.
- Completes the single-lexical-engine consolidation (`1sauc`, same wave): the Lance/Tantivy FTS is retired entirely — `search_code`'s hybrid lexical half reads the FTS5 tables, no Lance FTS is ever built, and the reclaim path drops legacy indices at upgrade (148 MB reclaimed live on this repo; the `_indices/` version-leak class is gone at its source).
- Freshness/attribution storage the decay work (`1ro43`) consumes as-is, without Lance row rewrites.
- Crash-safe, content-addressed secret-scan skips that fail toward a full scan.
- The registry-backed incremental skip removes Lance vector reads for provably-unchanged files (measured 0.14s vs 1.68s per table on a rechunk-all pass of this repo).
- Operational risk stays near zero: losing the store is a rebuild, never data loss.

**Negative / tradeoffs:**
- A second on-disk copy of chunk text (contentful FTS) — accepted for delete-support portability (contentless deletes need SQLite ≥ 3.43) and posture-tested (gitignored, never packaged).
- The store is read on the MCP server's query path, so end-of-build `wal_checkpoint(TRUNCATE)` is load-bearing (a pinned long-lived reader could otherwise starve autocheckpoint); server reads must open/close per operation.
- Every resident schema shares one schema-version lifecycle: a bump invalidates the whole store (cheap by the derived-only rule, but a whole-store rebuild nonetheless).

**Constraints imposed:**
- No parallel sidecar stores: new semantic-index relational state must become a resident schema here, with sequenced (never concurrent) version bumps.
- No parallel maintenance or integrity surfaces: new residents contribute into `wave_index_optimize` and the shared probe.
- stdlib `sqlite3` only — no loadable extensions.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| Reuse the graph state store file | Couples two subsystems' schema lifecycles and crash semantics for no shared-data benefit. |
| Per-concern store files (freshness.sqlite, fts.sqlite, …) | Multiplies recovery/versioning/locking surfaces without isolation benefits WAL doesn't already give. |
| Widen Lance rows / grow the legacy meta.json | Unchanged-row rewrites defeat `chunk_hash` reuse; whole-file JSON rewrite and parse costs grow with the repo. |
| Lexical scoring inside LanceDB | No BM25; hand-rolled term scoring bolted onto a vector store. |
| External lexical engine (tantivy-class) | New dependency and a second index lifecycle for capability FTS5 already provides. |
| Refactor GraphStateStore onto the shared helper now | Touches landed, reviewed build-path machinery scoped to stay untouched; a future follow-up if posture drift ever bites. |

## References

- `docs/waves/1rsh9 sqlite-index-substrate/` — wave record and the three change docs (full decision logs and evidence)
- `docs/waves/1sed7 sqlite-only-index-state/` — the SQLite-only amendment: meta.json retirement, build epoch, fail-closed readers
- `.wavefoundry/framework/scripts/index_state_store.py` — the substrate module
- `docs/architecture/search-architecture.md` — hybrid lexical layer and index format
- `docs/architecture/data-and-control-flow.md` — build-path store passes and state ownership
