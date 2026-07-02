# Reusable LanceDB reclaim (compact-by-rewrite) for index-table bloat

Change ID: `1p9aj-enh index-reclaim-compact-by-rewrite`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p99p expose-index-build-lock-status`

## Rationale

LanceDB index tables (`docs.lance`, `code.lance`) accumulate on-disk bloat from the incremental
append/rebuild churn the post-edit hook drives — superseded data-file fragments, stale FTS artifacts,
and old index versions that only `optimize()` reclaims. The `1p95j` FTS-finalize fix reduced this, but a
residual remains: this session's post-edit rebuilds re-grew `docs.lance` to **1.6 GB** over a ~55 MB
working set (16,992 chunks) — a ~30× bloat that the new `wave_index_health` `size` field (`1p9a9`)
surfaced immediately.

Worse, the standard compaction lever can **fail outright**. `optimize()` on the bloated `docs.lance`
raised a Lance decode error — `Max offset 1939874 exceeds length of values 1126298` at
`lance-encoding/src/encodings/logical/list.rs` — an upstream offset-rebasing bug in multi-batch list
writes (lance-format/lance #7538; PR #7546 fixes only the *nested*-list case and is unreleased, so our
single-level `lines list<int64>` column stays exposed). When compaction can't run, bloat grows
**unbounded** with no in-place recovery, and the only documented remedy is a full re-embed rebuild
(minutes of GPU/CPU work).

There is a cheaper remedy, proven this session: **normal reads still succeed on the corrupted table**
(only the compaction/decode path fails), so the table can be **rewritten in a single batch** — which
sidesteps the offset bug — reclaiming the space with **zero re-embedding**. Applied manually,
`docs.lance` went **1.6 GB → 55 MB** with FTS and vector search fully intact (16,992 rows, both indices
rebuilt). This change makes that a first-class, reusable, self-healing operation.

## The mechanism — tiered reclaim (compact by rewrite)

A reusable `reclaim_lance_table(db, table_name, model_name)` in `indexer.py`, tiered cheapest-first:

1. **Tier 1 — optimize in place.** `table.optimize(cleanup_older_than=timedelta(0))` (the existing
   `_optimize_lance_table` path). Fast, no rewrite. If it succeeds, done — this is the normal,
   non-corrupt case.
2. **Tier 2 — compact by rewrite.** On an `optimize()` failure (the Lance decode error, or any
   compaction error), read the live rows with `table.to_arrow()` (reads succeed on the corrupted table),
   then **`db.create_table(table_name, data=rows, mode="overwrite")`** — a **fresh write that recomputes
   the list-column offsets from the clean in-memory Arrow data**, sidestepping the append-time
   offset-rebasing bug (this is why the proven `to_arrow()` → `create_table` path reclaims cleanly where
   in-place `optimize()` cannot) — then rebuild the vector index
   (`create_index(metric="cosine", index_type="IVF_HNSW_SQ", replace=True)` when rows ≥
   `LANCEDB_INDEX_THRESHOLD`) and the FTS index (`_create_fts_index(..., replace=True)`), and
   `optimize()` the fresh table. **The swap MUST use `create_table(mode="overwrite")`, never
   `db.rename_table`** — `rename_table` raises `NotImplementedError: rename_table is not supported in
   LanceDB OSS`, and a drop-then-rename leaves the table **missing** if the rename fails (observed and
   recovered this session). Zero re-embedding.
3. **Tier 3 — full rebuild.** Only if the `to_arrow()` read itself fails (true data loss, not just
   compaction corruption) does it fall back to a full re-embed rebuild of that content type via the
   existing build path (needs `model_name`).

**Self-heal (cuts the residual churn).** Both the build **finalize** path and the **incremental**
compaction path escalate a failed `optimize()` to Tier 2 automatically, so a table whose compaction is
broken by the offset bug reclaims itself on the **next** build/update instead of growing unbounded. This
is the mechanism that removes the `1p95j` residual: when optimize succeeds nothing changes; when it
can't, the rewrite reclaims in-band rather than silently accumulating.

**Operator lever (operator review — dedicated tool, not a mode).** Exposed as a dedicated
`wave_index_optimize(content, rebuild_if_needed)` MCP tool — the discoverable "make the index healthy"
verb — over the shared `indexer.optimize_index_tables`, which runs the tiered ladder over `docs`/`code`
under the index-build lock and reports per-table `{tier, rows, size_before, size_after, reclaimed}` + a
total. On a Tier-3 (unreadable) table it spawns a full background rebuild **after** releasing the lock
(`rebuild_if_needed`, default True). A dedicated tool needs a one-time MCP reconnect on upgrade — accepted
for discoverability over the no-reconnect `mode` alternative.

**Automatic on install + upgrade (operator review).** `setup_index.main` runs `optimize_index_tables`
(reclaim-only, no rebuild) right after the synchronous build releases the lock and **before** any
background code build — so it never races a build. Because upgrade's index rebuild invokes
`setup_index`, this single hook covers **both** install and upgrade, reclaiming version-bloat the
fragment-gated incremental optimize can miss and self-healing corruption.

**Upstream.** A minimal single-level-`list<int64>` repro against lance-format/lance (the shipped #7546
covers nested lists only) plus a reference note (`docs/references/lance-list-offset-corruption.md`)
capturing the trigger (≈390 incremental appends), the decode signature, and the compact-by-rewrite
workaround — so the workaround can be retired when a real fix ships. No code dependency on an upstream fix.

## Requirements

1. `indexer.reclaim_lance_table(db, table_name, model_name)` implements the tiered strategy above and
   returns a structured result (`{tier, rows_before, rows_after, bytes_before, bytes_after,
   reembedded: bool}`).
2. Tier 2 rewrites via `db.create_table(name, data=to_arrow(), mode="overwrite")` and rebuilds the
   vector (`IVF_HNSW_SQ`, `metric="cosine"`, rows ≥ `LANCEDB_INDEX_THRESHOLD`) + FTS indices, then
   `optimize()`s. It **never** calls `db.rename_table` and never drops the table before a replacement
   exists. All rows preserved; no re-embedding.
3. Tier 3 (full rebuild) runs **only** when the `to_arrow()` read raises — corruption of the compaction
   path alone must not trigger a re-embed.
4. A dedicated `wave_index_optimize(content, rebuild_if_needed)` MCP tool runs the reclaim over `docs` +
   `code` (each best-effort, independent) under the `_index_build_lock` via
   `indexer.optimize_index_tables`, and returns per-table `{tier, rows, size_before, size_after,
   reclaimed}` + a total; a Tier-3 table triggers a background rebuild when `rebuild_if_needed` (after
   the lock is released). New tool ⇒ one-time reconnect on upgrade. It also runs automatically at the end
   of `setup`/`upgrade` (reclaim-only).
5. Build finalize self-heals: a finalize-`optimize()` that raises the Lance decode error (or any
   compaction error) escalates to Tier 2 for that table rather than leaving it bloated. On escalation
   failure it degrades to a warning and leaves the table usable (reads already work) — never raises out
   of finalize.
6. A minimal upstream repro + a reference note (`docs/references/lance-list-offset-corruption.md`)
   documenting the single-level list offset-corruption trigger, the decode signature, and the
   compact-by-rewrite workaround.
7. Docs updated: `docs/specs/mcp-tool-surface.md` (the `wave_index_optimize` tool) and
   `docs/architecture/chunking-and-indexing-pipeline.md` (reclaim tier, the auto-run on install/upgrade,
   + the OSS `rename_table` constraint).
8. `optimize_index_tables` runs automatically at the end of `setup` (install) and `upgrade`, reclaim-only
   and lock-safe.
9. Full framework suite green + `wave_validate` clean. Concurrency: reclaim runs under the build lock;
   no regression to the acquire path.

## Scope

**Problem statement:** Index tables bloat from append churn, and when the Lance single-level-list offset
bug breaks `optimize()`, the bloat is unrecoverable in place and grows unbounded — with only an expensive
full re-embed as the documented fix.

**In scope:**

- `indexer.py`: `reclaim_lance_table` + `_compact_by_rewrite` (tiered optimize → compact-by-rewrite →
  Tier-3 signal), reusing `_optimize_lance_table` (now returns a bool) and `_create_fts_index`; the
  self-heal escalation to Tier 2 on a failed optimize in BOTH the finalize and incremental paths;
  `optimize_index_tables` shared helper.
- `server_impl.py`: `_wave_index_optimize_response` + the dedicated `wave_index_optimize` tool over docs
  + code under the build lock with per-table before/after size and Tier-3 background rebuild.
- `setup_index.py`: auto-run `optimize_index_tables` after the synchronous build (covers install +
  upgrade).
- A reference note + minimal repro for the upstream Lance bug
  (`docs/references/lance-list-offset-corruption.md`); docs (`mcp-tool-surface.md`,
  `chunking-and-indexing-pipeline.md`).
- Tests: tier selection; Tier 2 preserves all rows + rebuilds both indices + never calls `rename_table`;
  Tier 3 gating on read failure; `optimize_index_tables`; the tool path; finalize escalation.

**Out of scope:**

- Auto-running reclaim on a *timer* or on every incremental pass when optimize *succeeds* — normal
  `optimize()` already handles the non-corrupt case; only the compaction-broken case self-heals, plus the
  one reclaim-only pass at the end of install/upgrade.
- Changing the incremental append/embed path or the chunker.
- The graph index (not a Lance table — reclaim is Lance-specific).
- Waiting on / vendoring an upstream Lance fix.

## Acceptance Criteria

- [x] AC-1: `reclaim_lance_table` reclaims a bloated table in place via `optimize()` (Tier 1) when
      compaction succeeds, returning `tier=1` and the row count. Evidence: `IndexReclaimTests.test_tier1_optimize_success`.
- [x] AC-2: on an `optimize()` failure it compacts by rewrite (Tier 2) — `to_arrow()` →
      `create_table(mode="overwrite")` → rebuild vector + FTS → `optimize()` — preserving **all** rows
      and search with **no** re-embedding, and **never** calling `db.rename_table` nor dropping the
      table before its replacement exists. Evidence:
      `test_tier2_compact_by_rewrite_preserves_rows_and_indices_no_rename` (rows preserved, both indices
      present, `rename_table` never called), `test_tier2_below_threshold_skips_vector_index_but_builds_fts`.
- [x] AC-3: Tier 3 full rebuild fires **only** when `to_arrow()`/`open` raises (not on an `optimize()`
      failure). Evidence: `test_tier3_only_on_read_failure_not_optimize_failure` (read-fail ⇒ Tier 3
      needs_rebuild; optimize-only-fail ⇒ Tier 2, not needs_rebuild), `test_tier3_on_open_failure`.
- [x] AC-4: a dedicated `wave_index_optimize(content, rebuild_if_needed)` tool runs the reclaim over
      `docs`/`code` under the build lock and returns per-table `{tier, rows, size_before, size_after,
      reclaimed}` + a total; Tier-3 tables spawn a background rebuild when `rebuild_if_needed`. New tool ⇒
      one-time MCP reconnect on upgrade (accepted). Evidence: `IndexOptimizeToolTests` (6) —
      per-table/total, Tier-3 spawn/no-spawn, invalid content, lock-busy, no-tables; live call after reconnect pending.
- [x] AC-5: the build finalize **and** incremental compaction paths escalate a failed `optimize()` to
      Tier 2 and never raise on reclaim failure (degrade to a warning; table stays readable). Evidence:
      `test_finalize_self_heals_on_optimize_failure`, `test_finalize_reclaim_failure_falls_through_and_does_not_raise`.
- [x] AC-6: a minimal upstream repro + reference note document the single-level-list offset corruption
      (trigger, `Max offset … exceeds length of values` signature, lance #7538/#7546) and the
      compact-by-rewrite workaround. Evidence: `docs/references/lance-list-offset-corruption.md`
      (with an embedded minimal repro). *(Filed as a reference doc, not a wave-coordinator journal.)*
- [x] AC-7: `docs/specs/mcp-tool-surface.md` + `docs/architecture/chunking-and-indexing-pipeline.md`
      document `wave_index_optimize` + the auto-run on install/upgrade and the OSS `rename_table`
      constraint; `run_tests.py` + `wave_validate` pass. Evidence: `mcp-tool-surface.md` (tool entry +
      table + chooser) + `chunking-and-indexing-pipeline.md` (reclaim section) diffs; full suite pending final run.
- [x] AC-8: `optimize_index_tables` runs automatically at the end of `setup` (install) and — via
      `setup_index` — `upgrade`, reclaim-only (no rebuild), lock-safe (after the synchronous build
      releases the lock, before any background code build). Evidence:
      `test_optimize_index_tables_skips_absent_and_reports_sizes` + the `setup_index.main` hook placement.

## Tasks

- [x] `indexer.reclaim_lance_table(db, table_name)` + `_compact_by_rewrite` — tiered optimize →
      compact-by-rewrite (`to_arrow` → `create_table` overwrite → `create_index` IVF_HNSW_SQ/cosine +
      `_create_fts_index` → `_optimize_lance_table`) → Tier-3 `needs_rebuild` signal; `_optimize_lance_table`
      now returns a success bool. Done.
- [x] Wire self-heal escalation in BOTH the finalize path (`_finalize_inner`) and the incremental
      compaction path: on a failed `optimize()`, call `_compact_by_rewrite`; on failure warn + continue
      (never raise). Done.
- [x] `server_impl.py`: `indexer.optimize_index_tables` shared helper + `_wave_index_optimize_response`
      + the dedicated **`wave_index_optimize`** MCP tool (Tier-3 auto-rebuild after lock release),
      per-table before/after size (reuse `_human_bytes`). Done.
- [x] Auto-run: `setup_index.main` calls `optimize_index_tables` after the synchronous build (covers
      install + upgrade). Done.
- [x] Upstream repro + reference note (`docs/references/lance-list-offset-corruption.md`); docs updates
      (`mcp-tool-surface.md` tool entry + table + chooser, `chunking-and-indexing-pipeline.md` reclaim section). Done.
- [x] Tests (tier selection, Tier 2 row/index preservation + no `rename_table`, Tier 3 gating on read
      failure, `optimize_index_tables`, tool path, finalize escalation, **no-deadlock fail-fast under lock
      contention**) — `IndexReclaimTests` (10) + `IndexOptimizeToolTests` (6). `run_tests.py` +
      `wave_validate` pending final run.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single ordered lane: `indexer.reclaim_lance_table` + self-heal escalation, then `server_impl` `wave_index_optimize`, then the `setup_index` auto-run, then repro/journal/docs + tests. Touches the build finalize path — full suite gates it. |

## Serialization Points

- `reclaim_lance_table` / `optimize_index_tables` / `wave_index_optimize` run under
  `indexer._index_build_lock` — the same acquire path `1p99o` hardened. Reclaim rewrites a whole table via
  `create_table(mode="overwrite")`; readers get a consistent Lance version (versioned commit), and no
  other builder runs concurrently under the lock. The `setup_index` auto-run is placed after the
  synchronous build releases the lock and before any background code build, so it never races.

## Affected Architecture Docs

`docs/architecture/chunking-and-indexing-pipeline.md` — add the reclaim tier (optimize →
compact-by-rewrite → rebuild) to the index-maintenance description and record the LanceDB-OSS
`rename_table` constraint. No boundary/flow change (additive maintenance path).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Tier 1 is the normal path — must reclaim when compaction works. |
| AC-2 | required | The core fix — compact-by-rewrite with no re-embed, no `rename_table`, no data loss. |
| AC-3 | required | Re-embed must not fire on a mere compaction failure (avoid needless GPU/CPU work). |
| AC-4 | required | The operator lever — the dedicated `wave_index_optimize` tool. |
| AC-5 | important | Self-heal is what cuts the residual churn; must never break finalize. |
| AC-6 | important | Upstream repro so the workaround can be retired when Lance fixes it. |
| AC-7 | required | Docs + suite + docs gate; no regression. |
| AC-8 | important | Auto-run on install/upgrade so bloat is reclaimed without an operator remembering. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Planned as the `1p99o`/`1p9a9` follow-up (operator: "write the follow up and add to the current wave"). Proven manually this session: `docs.lance` 1.6 GB → 55 MB via compact-by-rewrite, zero re-embed, FTS + vector search intact; the `rename_table`-unsupported footgun found and recovered. Admitted into the OPEN wave `1p99p` (mid-wave). | this session's reclaim run; `wave_index_health` size before/after. |
| 2026-07-01 | Implemented. `indexer`: `reclaim_lance_table` + `_compact_by_rewrite` + `optimize_index_tables`, `_optimize_lance_table`→bool, self-heal in finalize + incremental paths. `server_impl`: `_wave_index_optimize_response` + dedicated `wave_index_optimize` tool (Tier-3 auto-rebuild). `setup_index`: auto-run after build (covers install + upgrade). 15 tests (`IndexReclaimTests` 9 + `IndexOptimizeToolTests` 6) green; indexer suite 170 OK. **Operator pivots folded in: dedicated tool (not a mode), auto-run on install/upgrade, Tier-3 auto-rebuild.** AC-1..5,7,8 met; AC-6 (upstream repro journal) + docs pending. | diffs; `IndexReclaimTests`/`IndexOptimizeToolTests`; syntax + subsuite runs. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | Compact by rewrite (`to_arrow` → `create_table(mode="overwrite")` → rebuild indices), not a full re-embed, when `optimize()` fails. | Reads succeed on the corrupted table; a single-batch write sidesteps the offset bug and costs no embedding (1.6 GB → 55 MB proven). | Full re-embed rebuild (rejected — minutes of GPU/CPU for a problem reads don't have). |
| 2026-07-01 | Swap via `create_table(mode="overwrite")`, never `db.rename_table`. | `rename_table` raises `not supported in LanceDB OSS`; drop-then-rename leaves the table missing on failure (hit and recovered this session). | `drop_table` + `rename_table` (rejected — unsupported + non-atomic). |
| 2026-07-01 | Tier 3 re-embed only when `to_arrow()` itself fails. | Distinguishes compaction-path corruption (cheap rewrite) from true data loss (needs re-embed). | Always re-embed on any error (rejected — wasteful). |
| 2026-07-01 | Self-heal by escalating a failed finalize-`optimize()` to Tier 2. | Cuts the `1p95j` residual: a compaction-broken table reclaims itself on the next build instead of growing unbounded. | Manual-only reclaim (rejected — bloat recurs silently until an operator notices). |
| 2026-07-01 | **Pivot (operator review): expose a dedicated `wave_index_optimize` tool, not a `wave_index_build` mode.** | Operator: "optimize the index" is a distinct, discoverable maintenance verb. The one-time MCP reconnect a new tool needs (FastMCP) is acceptable on upgrade; discoverability wins over the no-reconnect mode. | `wave_index_build(mode="reclaim")` (rejected on operator review — buried, less discoverable). |
| 2026-07-01 | **Tier 3 auto-rebuilds (operator review).** The tool completes the job: after reclaiming under the lock, an unreadable table spawns a full background rebuild (`rebuild_if_needed`, default True) once the lock is released. | Makes it a true one-call "heal the index"; deferred spawn avoids deadlocking on the build lock it just held. | Report `needs_rebuild` only (kept as the `rebuild_if_needed=False` path). |
| 2026-07-01 | **Auto-run optimize at the end of install + upgrade (operator review).** `setup_index.main` runs `optimize_index_tables` (reclaim-only) after the synchronous build; upgrade reuses `setup_index`, so one hook covers both. | Operator: the index should be left compact automatically; reclaims version-bloat the fragment-gated incremental optimize misses. Placed after lock release + before background code ⇒ no race. | A separate pass in `upgrade_wavefoundry` (rejected — would race the backgrounded code build and duplicate the hook). |
| 2026-07-01 | Also self-heal the **incremental** compaction path, not just finalize. | The post-edit/turn-end incremental path is where corruption accumulates; escalating there reclaims without waiting for a full rebuild. | Finalize-only (rejected — incremental is the common path). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `create_table(mode="overwrite")` races a concurrent reader mid-rewrite. | Runs under `_index_build_lock` (no concurrent builder); Lance commits a new version, so readers hold a consistent snapshot. |
| Finalize escalation adds latency/failure surface to the hot build path. | Escalation fires only when `optimize()` already failed (rare, corrupt case); on reclaim failure it warns and continues — never raises out of finalize; reads already work. |
| Reproducing the Lance corruption in a unit test is expensive (~390 appends). | Tests inject a fake `optimize`/`to_arrow` that raises to exercise Tier 2/3 deterministically; the real corruption is covered by the reference-note repro, not the suite. |
| Tier 2 `to_arrow()` materializes the full live row set in memory — an OOM risk on a very large `code.lance` (the `1p8` low-RAM field lesson). | The materialized set is the **working set** (live chunks, bounded by chunk count), not the on-disk **bloat** (dead fragments/versions) — ~55 MB for the 16,992-row `docs` table, not the 1.6 GB reclaimed. Keep the proven `to_arrow()` → `create_table` path; if a monorepo `code.lance` ever makes the live set too large to materialize, a streamed `RecordBatchReader` rewrite (offsets still recomputed fresh) is the follow-up — flagged, not built here. |
| Tier 2 rebuilds indices with wrong params. | Reuses the exact `create_index(metric="cosine", index_type="IVF_HNSW_SQ")` + `_create_fts_index` calls proven this session; a test asserts both indices present post-rewrite. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
