# SQLite Index-State Store (Freshness/Decay Sidecar Substrate)

Change ID: `1rq4h-enh sqlite-index-state-store`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-11
Wave: `1rsh9 sqlite-index-substrate`

## Rationale

Wave 1p9q3 proved the embedded-SQLite pattern for index-adjacent relational state: the graph's per-file merge store (`project-graph-state.sqlite`) runs WAL journaling, single-transaction builds, and a crash-binding state machine, and it made zero-change builds write nothing. The semantic index has no equivalent — its only sidecar state is `meta.json`, a whole-file JSON snapshot rewritten and atomically swapped every build, and everything else lives in Lance rows.

That gap is about to matter. The decay work (`1ro43-enh churn-aware-retrieval-decay`, wave `1ro44`) needs per-file relational state — `last_modified`, `churn_score`, wave→landing-commit attribution, wave change sets, doc drift summaries — and its change doc already records the storage recommendation: a per-file SQLite sidecar, because `churn_score` changes on every build for active files even when chunk content is unchanged, and rewriting unchanged Lance rows would defeat `chunk_hash` reuse and add fragment churn. This change ships that store as a proper substrate: one SQLite file for semantic-index relational state, on the proven graph-store pattern, with the freshness/attribution schema as its first resident. Follow-on internals (FTS5 lexical tables, per-path bookkeeping) build on the same store in `1rrr0-enh sqlite-fts5-and-index-internals`.

The load-bearing design rule is **derived-only content**: the store holds nothing unrecoverable. Vectors and chunk content stay in Lance; docs stay in the repo; git remains the source of churn truth. A missing, corrupt, or schema-mismatched store is a rebuild, never data loss — which keeps the operational risk of adding a second database near zero.

## Requirements

1. Create a single semantic-index state store (working name `.wavefoundry/index/index-state.sqlite`; final name at implementation, recorded in the Decision Log) with WAL journaling, `busy_timeout`, single-transaction build updates, and a `schema_version` table. The graph's `project-graph-state.sqlite` remains separate and untouched; shared connection/pragma/crash-handling machinery is factored into a common helper (generalized from the graph store or extracted alongside it — decide at implementation without destabilizing the graph store).
2. **Derived-only rule:** every table must be rebuildable from git, Lance, the repo, or `meta.json`. On corruption, schema mismatch, or unknown `schema_version`, the store is dropped and rebuilt with a loud diagnostic — never a hard failure, never silent data invention.
3. Ship the **freshness/attribution schema** consumed by `1ro43` (the decay sidecar path): per-file `last_modified` and `churn_score`; wave→landing-commit(s); wave→change-set membership; per-doc drift summaries (`drifted`, `drift_refs`, `commits_since`, `anchor_kind`, waves-behind for the historical class). Schema shapes follow `1ro43` Requirements 1–3 and 12–13; the per-path freshness primitive (`1ro43` Requirement 6) reads from this store.
4. Build integration: the indexer writes freshness/attribution rows in one transaction per build pass, refreshing all files' churn values every build without touching unchanged Lance rows. Zero-change builds may skip the write entirely when inputs are fingerprint-identical.
5. Cross-wave coordination with `1ro43` (either landing order works, one store either way): if wave `1ro44` implements first with a minimal sidecar, this change absorbs and migrates it into the substrate; if this change lands first, `1ro43` consumes these tables as-is. Two parallel sidecar files must never exist.
6. Concurrency: writers cooperate with the existing index-build lock discipline; MCP server reads use read-only connections with `busy_timeout`; no new lock files beyond SQLite's own machinery.
7. Portability: stdlib `sqlite3` only — no extensions required by this change; Windows behavior follows the graph store's proven posture (WAL on NTFS, no console-window regressions, UTF-8 discipline).
8. Observability: `wave_index_health` (and `wavefoundry://index/status`) report store presence and schema version alongside existing layer health.
9. **Store maintenance primitives (SQLite analog of Lance compaction):** the shared store helper owns a maintenance policy so every resident schema inherits it rather than reinventing it: `auto_vacuum = INCREMENTAL` set at store creation; a `PRAGMA wal_checkpoint(TRUNCATE)` at the end of each index-state-store build pass (writers done, before the build lock releases) to keep the `-wal` file bounded under the long-lived MCP server; `PRAGMA optimize` at connection close for planner stats; and a reclaim step (`PRAGMA incremental_vacuum`, with full `VACUUM` reserved for the explicit on-demand path in Requirement 10). All are stdlib pragmas, no extensions. These run only against the index-state store in this change; applying automatic build-path maintenance to the graph store is deferred (see Out of scope) to respect the graph-store-untouched guarantee (AC-7). **Note the exposure asymmetry (2026-07-05 investigation):** unlike the graph state store — which no long-lived process opens — this store *is* read on the query path inside the MCP server (FTS fusion, freshness primitive, secret-scan reads), so it genuinely has the long-lived-reader profile that makes end-of-build WAL truncation load-bearing here. Server-side reads must open/close per operation or otherwise avoid pinning a persistent connection that would starve autocheckpoint between builds.
10. **`wave_index_optimize` becomes the unified maintenance verb for all indexes:** extend the existing tool (today Lance-only, explicitly skipping the graph index) to also run SQLite maintenance — WAL checkpoint/truncate, incremental or full `VACUUM`, and `PRAGMA optimize` — across every SQLite store it can reach: the index-state store **and** the graph's `project-graph-state.sqlite`, closing the current "graph index is not reclaimed this way" gap. SQLite maintenance runs under the same index-build lock as Lance compaction, is on-demand only (does not alter the graph build path), reports per-store reclaim (`size_before/size_after/reclaimed`) mirroring the per-table Lance report, and — like Lance compaction — runs automatically at the end of `setup` and `upgrade`. FTS-specific merge is contributed by `1rrr0` into this same maintenance path.
11. **Integrity verification (proactive, two-layer):** the shared helper exposes an integrity probe covering both failure classes, since they are distinct and `integrity_check` alone catches only the first:
    - **Physical/structural** — `PRAGMA quick_check` at store open (upgrading the graph store's reactive "reset only when a read raises" posture to proactive detection) and again in `wave_index_optimize`; the heavier full `PRAGMA integrity_check` runs on the on-demand `wave_index_optimize` path. FTS5's own `INSERT INTO <fts>(<fts>) VALUES('integrity-check')` is contributed by `1rrr0` into the same probe. Stdlib pragmas only — no checksum VFS/extension.
    - **Logical/staleness** — bind each resident schema's derived tables to their source-of-truth fingerprint (Lance table version, git HEAD, `rules_hash`, etc.), mirroring the graph store's `payload_fingerprint`/`size`/`mtime_ns` keys, so a structurally-sound-but-stale store is detected too. `integrity_check` cannot see this class.
    Any failure of either layer routes to the existing derived-only drop-and-rebuild with a loud diagnostic — detection is the whole job because recovery is already free (nothing unrecoverable is stored). `wave_index_health` reports the result (`ok` / `structural-fail` / `stale-fingerprint`) so "verify there's no corruption" is answerable on demand.

## Scope

**Problem statement:** The semantic index has no home for relational sidecar state. The decay work needs per-file/per-wave tables that would be wrong in Lance rows (rewrite cost for unchanged chunks) and wrong in `meta.json` (whole-file rewrite/parse growth), and upcoming internals (FTS5, bookkeeping) need the same substrate.

**In scope:**

- The store file, schema versioning, WAL/transaction/crash posture, and shared helper extraction from the graph store pattern.
- Freshness/attribution tables and their build-time write path + read primitive.
- Drop-and-rebuild recovery with loud diagnostics.
- Health/status surfacing.
- Store maintenance primitives in the shared helper (incremental auto_vacuum, end-of-build WAL truncate, `PRAGMA optimize`, incremental_vacuum) for the index-state store.
- `wave_index_optimize` extension to a unified all-index maintenance verb (Lance + index-state store + graph store), on-demand and at setup/upgrade, under the build lock, with per-store reclaim reporting.
- Integrity verification: proactive `quick_check` (open + optimize) and full `integrity_check` (on-demand), source-fingerprint binding per resident schema, `wave_index_health` integrity reporting, all routing to drop-and-rebuild.
- Tests: schema creation/versioning, corruption recovery, build-transaction behavior, unchanged-Lance-rows guarantee, concurrent read during build, Windows-relevant pragmas, WAL bounded after builds, maintenance reclaim across all stores, integrity detection (structural + stale-fingerprint) → rebuild.

**Out of scope:**

- FTS5 lexical tables, per-path bookkeeping migration, and other internals — owned by `1rrr0-enh sqlite-fts5-and-index-internals` (same wave, after this change).
- Any vector or chunk-content storage in SQLite; Lance remains the vector store and the numpy fallback is untouched.
- Changes to the graph state store's schema or **build-path behavior**. This change adds *on-demand* graph-store maintenance via `wave_index_optimize` only; wiring automatic end-of-build WAL/vacuum maintenance into the graph build path is a separate follow-up so the graph store's build behavior and test suite stay untouched (AC-7). **Investigated 2026-07-05 (see Progress Log):** the graph store's `-wal` is confirmed NOT growing — it is opened only by short-lived build subprocesses (never by the long-lived server, which reads the derived `project-graph.json`), so each build closes and checkpoints, leaving no `-wal`/`-shm` on disk. On-demand `wave_index_optimize` coverage is therefore a completeness convenience for the graph store, not a fix for an active leak; no separate graph-store WAL follow-up is needed.
- The decay computation logic itself (drift, anchors, annotation) — owned by `1ro43`; this change ships storage the computation writes/reads.

## Acceptance Criteria

- [x] AC-1: A build creates the store with WAL mode, `busy_timeout`, and a populated `schema_version`; re-running against a current-version store performs no schema churn. — `index_state_store.py::IndexStateStore` (WAL + busy_timeout 10000 + `store_schema_version`); `StoreSubstrateTests::test_creation_sets_wal_busy_timeout_schema_version_and_auto_vacuum` / `test_reopen_current_version_performs_no_schema_churn`.
- [x] AC-2: A corrupted or unknown-version store is dropped and rebuilt on the next build with a loud diagnostic (fixture test), and no code path treats store absence as an error. — reset-and-recreate at open + `ensure_current` whole-store invalidation; `test_corrupted_store_is_dropped_and_rebuilt_loudly`, `test_unknown_schema_version_resets_store_with_diagnostic`, `test_store_absence_is_not_an_error_for_readers`.
- [x] AC-3: Freshness/attribution tables match the `1ro43` consumption contracts (per-path primitive reads `{age_days, churn_score, commits_since}`; wave attribution and drift summaries resolvable per doc) with fixture coverage. — `freshness_for_path` / `wave_attribution_for_path` / `doc_drift_for_path`; `FreshnessContractTests` (git repo, since_ts filter, mtime fallback, attribution + drift + historical/waves-behind round-trips).
- [x] AC-4: A build refreshing churn for N unchanged files rewrites zero Lance rows (differential test against Lance fragment/row state before and after). — the freshness write path never opens a Lance table (separate sqlite file); `BuildIntegrationTests::test_freshness_refresh_touches_no_lance_artifacts` (mtime_ns+size differential over the table dir across skip and full-rewrite passes).
- [x] AC-5: A reader querying the store during an in-progress build transaction gets a consistent snapshot or a bounded retry — never an exception surfaced to the tool response (concurrency test). — WAL snapshot isolation + read-only URI opens with busy_timeout; `test_reader_during_in_progress_transaction_sees_consistent_snapshot`.
- [x] AC-6: `wave_index_health` reports store presence and schema version; absence reports as a normal not-yet-built state. — `_state_store_health_summary` in `server_impl.py` + `health["state_store"]` block + index-status resource section; `StateStoreOptimizeAndHealthTests::test_health_summary_*` / `test_health_response_wires_state_store_block`.
- [x] AC-7: Shared store helpers are covered by tests proving the graph store's build-path behavior is unchanged (its existing suite stays green without modification); on-demand maintenance via `wave_index_optimize` is the only new operation the graph store gains. — extract-alongside: `graph_indexer.py` untouched (zero edits); graph suite unmodified and green in the full run; `optimize_state_stores` reaches the graph store's sqlite FILE only (`MaintenanceTests::test_optimize_covers_the_graph_state_store_file` + relpath wiring lock).
- [x] AC-8: The index-state store is created with `auto_vacuum=INCREMENTAL`; after a build pass its `-wal` file is checkpoint-truncated (a fixture asserts the WAL is bounded after repeated builds), and `PRAGMA optimize` runs at connection close. — creation pragma + `end_of_build_maintenance` (wal_checkpoint TRUNCATE + incremental_vacuum) + optimize-at-close; `MaintenanceTests::test_wal_is_truncated_after_repeated_builds` (asserts 0 bytes after each of 3 builds).
- [x] AC-9: `wave_index_optimize` runs SQLite maintenance across the index-state store and the graph store in addition to Lance, reports per-store `size_before/size_after/reclaimed`, runs under the index-build lock, and executes at the end of `setup`/`upgrade`; a fixture shows delete-churned stores reclaim space. — `stores` section in `_wave_index_optimize_response` (under `_index_build_lock`), `setup_index._optimize_after_build` extension (runs on install AND upgrade — upgrade's rebuild invokes setup_index); `test_optimize_state_stores_reclaims_delete_churned_store`, `StateStoreOptimizeAndHealthTests` (totals, lock-busy, no-Lance-tables path), `IndexerWiringTests::test_setup_optimize_after_build_wires_state_store_pass`.
- [x] AC-10: The integrity probe detects both corruption classes and routes to drop-and-rebuild: a fixture that byte-corrupts a store file is caught by `quick_check` (at open and via `wave_index_optimize`), rebuilt loudly with no data loss (derived-only), and reported by `wave_index_health` as `structural-fail`; a fixture whose source fingerprint no longer matches (stale table) is caught without a structural error and reported `stale-fingerprint`; a clean store reports `ok`. — `probe_state_store` (quick_check/integrity_check + git-HEAD freshness-fingerprint binding); `IntegrityProbeTests` (clean-ok incl. deep, byte-corrupt → structural-fail → rebuild → ok, stale-fingerprint → refresh → ok, maintenance-pass detection); `test_store_structural_fail_emits_diagnostic` on the optimize surface.
- [x] AC-11: Full framework tests run bytecode-free and docs validation passes. — full suite 4,809 tests OK bytecode-free (run_tests.py, 2026-07-10); `wave_validate` clean.

## Tasks

- [x] Extract/generalize shared SQLite store helpers (connection, pragmas, schema-version gate, drop-and-rebuild) without altering graph-store behavior. — new `index_state_store.py`, extract-alongside (graph store untouched; see Decision Log).
- [x] Implement the index-state store with the freshness/attribution schema and build-transaction write path. — `IndexStateStore` (file_freshness, file_commits, wave_landing, wave_change_files, doc_drift) + `update_freshness_from_build` wired into `_build_index_locked` after `_save_meta`, inside the build lock.
- [x] Implement the per-path freshness read primitive against the store (the `1ro43` Requirement 6 seam). — `freshness_for_path(index_dir, path, since_ts=None)` → `{age_days, churn_score, commits_since}` over a read-only URI connection.
- [x] Wire zero-change fingerprint skip and unchanged-Lance-rows guarantee; add the differential test. — git-HEAD + path-set-hash fingerprint skip; `test_freshness_refresh_touches_no_lance_artifacts`.
- [x] Add corruption/version-mismatch recovery with diagnostics; fixture tests. — reset-and-recreate + `ensure_current`; `StoreSubstrateTests` fixtures.
- [x] Surface store presence/schema version in `wave_index_health` / index status resource. — `_state_store_health_summary` + `wavefoundry://index/status` section.
- [x] Add maintenance primitives to the shared helper (auto_vacuum=INCREMENTAL at creation, end-of-build WAL checkpoint(TRUNCATE), PRAGMA optimize at close, incremental_vacuum); WAL-bounded fixture. — `end_of_build_maintenance` + close-time optimize; `test_wal_is_truncated_after_repeated_builds`.
- [x] Extend `wave_index_optimize` to run SQLite maintenance across the index-state store and graph store (per-store reclaim reporting, under the build lock, at setup/upgrade); reclaim fixture. — `optimize_state_stores` / `sqlite_store_maintenance` + server `stores` section + `setup_index._optimize_after_build` extension; reclaim + graph-store-file fixtures.
- [x] Add the integrity probe to the shared helper (open-time `quick_check`, full `integrity_check` on the optimize path, per-schema source-fingerprint binding) with `wave_index_health` reporting and drop-and-rebuild routing; corruption + stale-fingerprint fixtures. — `probe_state_store` two-layer probe; `IntegrityProbeTests`.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`. — full suite 4,809 tests OK bytecode-free (run_tests.py, 2026-07-10); `wave_validate` clean.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| store-substrate | implementer | — | Shared helpers, store file, schema versioning, recovery |
| freshness-schema | implementer | store-substrate | 1ro43 consumption tables + read primitive |
| build-integration | implementer | freshness-schema | Transaction write path, zero-change skip, Lance guarantee |
| health-surfacing | implementer | store-substrate | wave_index_health / status resource |
| maintenance | implementer | store-substrate | Maintenance primitives + wave_index_optimize all-index extension |
| integrity | implementer | store-substrate | quick_check/integrity_check probe, fingerprint binding, health reporting |
| tests-docs | qa-reviewer | all implementation streams | Differential, concurrency, recovery, WAL-bounded, reclaim, integrity, validation |


## Serialization Points

- Store substrate and schema versioning land before any resident schema (freshness tables) or downstream consumer (`1rrr0`).
- Cross-wave seam with `1ro43` (wave `1ro44`): coordinate landing order per Requirement 5 — one store, no parallel sidecars; whichever lands second consumes/migrates, and both change docs record the outcome.
- Shared-helper extraction must not modify graph-store build-path behavior; its existing tests are the regression gate (AC-7). The graph store gains only on-demand `wave_index_optimize` maintenance in this change.
- Maintenance primitives live in the shared helper so resident schemas (freshness here, FTS/bookkeeping in `1rrr0`, secret-scan cache in `1rsha`) inherit them; `1rrr0` contributes the FTS `optimize` step into the same `wave_index_optimize` path rather than a parallel one.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — index-state store role beside Lance and `meta.json`.
- `docs/architecture/current-state.md` — new store artifact in the index directory topology.
- `docs/architecture/data-and-control-flow.md` — build-transaction write path, read primitive, and end-of-build maintenance.
- ADR recommended: derived-only SQLite sidecar substrate vs widening Lance rows vs growing `meta.json`.
- `docs/specs/mcp-tool-surface.md` — `wave_index_optimize` extended to unified all-index maintenance (Lance + SQLite stores).

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The substrate contract (WAL, versioning) is what everything else builds on. |
| AC-2 | required | Derived-only recovery is the rule that keeps a second database operationally safe. |
| AC-3 | required | The 1ro43 consumption contract is the reason this change exists. |
| AC-4 | required | Not rewriting unchanged Lance rows is the core efficiency claim vs chunk-row storage. |
| AC-5 | required | The MCP server reads while builds write; contention must be handled by design. |
| AC-6 | important | Observability matters but degrades gracefully. |
| AC-7 | required | The graph store is landed, reviewed machinery; destabilizing it is not an acceptable cost. |
| AC-8 | required | Unbounded WAL growth under the long-lived server is the realistic SQLite failure mode; end-of-build truncate is the fix. |
| AC-9 | required | The unified maintenance verb is the operator-facing deliverable; one command must maintain every index or the graph store stays unmaintained. |
| AC-10 | required | Proactive integrity detection is the difference between "we recover when a read happens to hit corruption" and "we verify, then recover"; both corruption classes must be covered. |
| AC-11 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-04 | Drafted from operator direction: generalize SQLite from the graph store into a semantic-index state substrate, shipping the decay sidecar path (`1ro43` storage recommendation) as its first resident schema; FTS5/bookkeeping internals follow in `1rrr0`. | `graph_indexer.py` store (wave 1p9q3); `1ro43` Requirements 1–2 storage recommendation; `meta.json` swap machinery (wave 1p9iw). |
| 2026-07-05 | Added SQLite maintenance (Req 9) and the `wave_index_optimize` unified all-index extension (Req 10) after operator asked whether SQLite needs Lance-style maintenance. Investigation found the codebase does zero explicit SQLite maintenance (no VACUUM/checkpoint/optimize anywhere) and `wave_index_optimize` explicitly skips the graph index — so the graph store is unmaintained today. ACs 8–9 added; verification gate → AC-10. Graph-store automatic build-path maintenance deferred to a follow-up to preserve AC-7. | `wave_index_optimize` docstring (Lance-only, graph skipped); keyword sweep: no VACUUM/wal_checkpoint/PRAGMA optimize/auto_vacuum in `.wavefoundry/framework/scripts`. |
| 2026-07-05 | Investigated whether the graph store's `-wal` is already growing (operator ask). Finding: NOT growing, structurally can't. On-disk while the server runs: only `project-graph-state.sqlite` (3.7 MB), no `-wal`/`-shm`. `GraphStateStore` has zero refs in `server_impl.py` — the long-lived server reads `project-graph.json`, never the state store; the store is opened only by short-lived build subprocesses (`graph_indexer.py`) that close-and-checkpoint per build. Resolution: no graph-store WAL follow-up needed; the maintenance exposure is real for THIS store (query-path reads in the server), confirming Req 9's WAL-truncate is load-bearing here. | `ls .wavefoundry/index/graph/` (no -wal/-shm); `GraphStateStore` absent from `server_impl.py`; `GraphQueryIndex(...JSON payload...)` at server_impl.py:15229/15242/15257; `GraphStateStore.close()`/`close_store()` in graph_indexer.py. |
| 2026-07-10 | Implemented: new `index_state_store.py` (substrate + freshness/attribution schema + read primitives + maintenance + two-layer integrity probe); indexer build-path wiring (`update_freshness_from_build` after `_save_meta`, in-lock, fail-safe); server surfaces (`wave_index_health` `state_store` block, `wave_index_optimize` unified `stores` maintenance, index-status resource section); `setup_index._optimize_after_build` store pass (covers install + upgrade). 25 new store tests + 7 server-surface tests green; corruption fixture corrected to corrupt page-tail cell areas (mid-page bytes can land in free space quick_check legitimately ignores). | `index_state_store.py`; `indexer.py` (`_get_index_state_store`, post-`_save_meta` call); `server_impl.py` (`_state_store_health_summary`, optimize `stores` section); `setup_index.py`; `tests/test_index_state_store.py` (25); `test_server_tools.py::StateStoreOptimizeAndHealthTests` (7). |
| 2026-07-05 | Added integrity verification (Req 11, AC-10) after operator asked what corruption checks are possible. Investigation confirmed zero integrity checks exist today (no `quick_check`/`integrity_check` anywhere); the graph store only reacts to corruption when a read raises. Two-layer probe added: physical (`quick_check`/`integrity_check` + FTS `integrity-check` from `1rrr0`) and logical (source-fingerprint binding, since `integrity_check` cannot see staleness), both routing to the existing derived-only rebuild and surfaced in `wave_index_health`. Verification gate → AC-11. | Keyword sweep (no integrity pragmas); graph store docstring "corruption at open time is handled by reset-and-recreate" (reactive); graph store `payload_fingerprint`/`size`/`mtime_ns` binding as the logical-check precedent. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-04 | One semantic-index state store file with schema versioning, separate from the graph state store, holding derived-only relational state. | One liveness/versioning/recovery surface for all semantic-index relational state; the graph store stays scoped to graph merge state it already owns; derived-only keeps corruption cost at "rebuild". | **Reuse the graph store file for index state:** weakness — couples two subsystems' schema lifecycles and crash semantics for no shared-data benefit. **Per-concern store files (freshness.sqlite, fts.sqlite, …):** weakness — multiplies recovery/versioning/locking surfaces without isolation benefits WAL doesn't already give. **Widen Lance rows / grow meta.json:** weaknesses already recorded in `1ro43` (unchanged-row rewrites; whole-file rewrite and parse growth). |
| 2026-07-05 | Route all SQLite maintenance through the existing `wave_index_optimize` tool (extended to cover the SQLite stores) rather than a new tool; run automatic maintenance only on the index-state store's build path, and cover the graph store on-demand only. | One operator-facing maintenance verb that already fires at setup/upgrade and already reports per-target reclaim; on-demand-only for the graph store keeps its reviewed build path untouched (AC-7) while still giving it a maintenance path it lacks today. | **New dedicated maintenance tool:** weakness — a second maintenance surface to discover and document when one already exists and auto-runs. **Auto-maintain the graph build path now:** weakness — changes landed, reviewed graph-store behavior in a change scoped to leave it untouched; correctly a separate follow-up. **Do nothing (rely on WAL autocheckpoint):** weakness — a pinned long-lived reader can starve autocheckpoint, so the `-wal` can grow unbounded; explicit truncate is the reliable fix. |
| 2026-07-10 | Shared helpers EXTRACTED ALONGSIDE the graph store (new `index_state_store.py` modeled on `GraphStateStore`) rather than refactoring `graph_indexer.py` to use a common module. | Zero risk to the landed, reviewed graph store (AC-7 satisfied by construction: zero edits to `graph_indexer.py`); the module documents the graph-store provenance, and a wiring-lock test pins the duplicated graph-store path constant to `graph_indexer`'s values. | **Refactor GraphStateStore onto the shared helper now:** weakness — touches reviewed build-path machinery this change is scoped to leave alone; correctly a future follow-up if drift ever bites. |
| 2026-07-10 | Store file name confirmed as `.wavefoundry/index/index-state.sqlite` (`STATE_STORE_FILENAME`), schema version `"1"`. | Matches the Req 1 working name; lives beside `meta.json` under the gitignored index dir. | None serious — a `state/` subdirectory adds a level for no isolation benefit. |
| 2026-07-10 | Freshness logical-staleness fingerprint = git HEAD (plus an indexed-path-set hash for the zero-change skip). | last_modified/churn derive entirely from commit history, so HEAD equality means the tables are current by construction; `stale-fingerprint` is informational (the next build refreshes), while `structural-fail` routes to drop-and-rebuild. Non-git roots have no fingerprint and always rewrite (cheap mtime pass). | **File-content hashing:** weakness — O(repo) hashing per probe for no added precision on git-derived data. |
| 2026-07-10 | Churn extraction = ONE batched `git log --name-only` pass per build (newest→oldest; first-seen ts = last_modified; window occurrences = commit_count; capped at `FRESHNESS_GIT_LOG_MAX_COMMITS`), fully skipped when the HEAD fingerprint matches. | Single subprocess, single parse, satisfies the no-per-query-git rule (build-path only); beyond-cap/untracked files fall back to honest `source='mtime'` rows. | **Per-file `git log -1`:** weakness — O(files) subprocesses. **Window-only log:** weakness — loses last_modified for files untouched in the window. |
| 2026-07-05 | Verify corruption with a two-layer probe (`quick_check`/`integrity_check` + source-fingerprint binding) routed to the existing drop-and-rebuild, not with page checksums. | Everything in the store is derived-only, so detection is the whole task and recovery is already free; stdlib pragmas plus fingerprint binding cover both structural and logical corruption with zero new dependencies. Checksums would need a loadable VFS extension this project bars, and would only cover the structural class the pragmas already catch. | **Page-level checksums (cksmvfs):** weakness — a loadable extension the portability rule (Req 7) forbids, and it misses logical staleness entirely. **integrity_check only:** weakness — proves the b-tree is sound but not that its rows still match source; a stale-but-intact store passes. **Stay reactive (rebuild only when a read raises):** weakness — silent structural damage in untouched pages persists undetected; proactive `quick_check` at open is nearly free for our small stores. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Two SQLite stores (graph, index-state) drift in posture and bug-fixes | Shared helper module owns connection/pragma/recovery/maintenance behavior; graph-store tests gate regressions (AC-7). |
| `-wal` grows unbounded under the long-lived MCP server (reader starves autocheckpoint) | End-of-build `wal_checkpoint(TRUNCATE)` on the index-state store (AC-8) plus on-demand `wave_index_optimize` coverage; a WAL-bounded fixture asserts the ceiling. |
| Full `VACUUM` under the build lock stalls builds on a large store | Default reclaim is incremental (`auto_vacuum=INCREMENTAL` + `incremental_vacuum`); full `VACUUM` is reserved for the explicit on-demand `wave_index_optimize` path, matching how Lance heavy compaction is on-demand. |
| Corruption goes undetected until a read happens to hit it (today's reactive posture) | Proactive `quick_check` at open + full `integrity_check` on the optimize path; source-fingerprint binding catches logical staleness `integrity_check` misses; any failure drops-and-rebuilds loudly (derived-only) and is reported by `wave_index_health`. |
| `integrity_check` on a large store adds latency | `quick_check` (the cheaper structural pass) is the default at open and in routine optimize; the full `integrity_check` runs only on the explicit on-demand path, same tiering as reclaim. |
| Store schema churn breaks 1ro43 or 1rrr0 consumers mid-wave | `schema_version` gate + drop-and-rebuild; consumer contracts fixed in change docs before implementation. |
| Windows file semantics (WAL on network shares, AV interference) | Same posture the graph store already runs in the field; store lives under `.wavefoundry/index/` (local, gitignored); busy_timeout + bounded retry. |
| Parallel sidecar appears if 1ro44 implements before this lands | Explicit coordination requirement (Req 5) mirrored in both change docs and both wave records. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
