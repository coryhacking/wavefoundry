# Chunk-Index Backfill Fails Permanently on Every Real Lance Table (Schema-Tolerant Fetch + Visibility)

Change ID: `1sbfj-bug chunk-index-backfill-schema-tolerance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-11
Wave: `1sbfk chunk-index-backfill-repair`

## Rationale

Field-confirmed on the 1.12.0 release candidate (local build `1.12.0+pbj4`, operator's TS/CDK test repo, 2026-07-11) — exception captured verbatim:

```
RuntimeError: lance error: Invalid user input: Schema error: No field named tags.
Valid fields are id, path, kind, language, lines, text, chunk_hash.
```

Root cause, three confirmed parts (initial "pre-`tags`-era table" hypothesis CORRECTED by follow-up field evidence + local verification):

1. **The reconcile's Lance projection requests a column that no production Lance table has ever had.** `_sync_chunk_derived_state._fetch_rows` selects `["id","path","kind","language","tags","lines","text","chunk_hash"]`, but the production pipeline never writes `tags`: `chunker.py` imports `_infer_tags` and never calls it, no chunk dict carries a `tags` key, so Lance schema inference at table creation never produces the column. Real schema everywhere: `['id','path','kind','language','lines','section','text','chunk_hash','vector']` — verified identical on the field repo AND this repo. The projection can never succeed against any real table; `--full` rebuilds don't help (the recreated table still has no `tags`).
2. **The tests pass because the fixtures diverge from production.** The reconcile/backfill test fixtures hand-build Lance rows WITH a `tags` key, so the fixture-created tables have the column and the projection succeeds — a fixture-reality divergence that hid a never-worked code path behind a green suite.
3. **The failure is swallowed by design and invisible.** The fail-safe catch prints `chunk-index reconcile for '<table>' skipped (…Schema error: No field named tags…)` to raw stdout/stderr only — never persisted to `upgrade.log`/build logs (the field investigation only captured it by forcing `--full` and tapping raw stdout). The store is left with only the delta-written rows: field repo `fts_code` 0 vs 7,473 Lance rows (provisioned fresh under the 1.12 FTS-drop step, failed on first attempt), `fts_docs` 162 (stale pre-1.12 incremental leftovers); **this repo: registry docs 598 vs 20,020, code 1,310 vs 14,683**. Zero-change builds exit before the reconcile, so re-runs look silent and healthy. Downstream: `code_ask`/`code_search` lexical fusion runs near-blind (`["code","lexical"]` provenance never observed in the field), while `wave_index_health` reports `integrity: ok`.

Blast radius: **every repo, including this one** — the backfill/reconcile path has never once succeeded outside test fixtures. The 1rsh9 lexical-fusion eval ran on partial delta-only coverage and still improved; full coverage is untapped upside. This blocks the 1.12.0 release; the zip was never published, so the fix folds into 1.12.0.

## Requirements

1. **Schema-tolerant reconcile fetch:** the backfill projection intersects the requested columns with the table's actual schema (`table.schema` names); rows simply lack the absent columns and the store writers' existing `.get(...) or ""` coercion supplies the defaults. `id`, `path`, and `text` remain required (a table missing those is genuinely unreadable and keeps the current skip path); every other column (`tags`, `language`, `kind`, `lines`, `chunk_hash`) is optional.
2. **Heals in place, no forced rebuild:** on any existing repo the next build's reconcile must fully backfill FTS + registry from Lance with empty defaults for the missing columns — no `--full` rebuild, no operator step. This repo's own store (registry 598/20,020 + 1,310/14,683) is the live verification target.
   - **Including zero-change builds:** the up-to-date early return (`build_index` exits at ~`indexer.py:3438` before the reconcile at ~`:3884` when nothing changed) must first run a CHEAP coverage probe (SQLite registry count vs Lance `count_rows()` — two metadata reads, no row scan) and fall through to the reconcile when a store is materially under-covered or cold. Otherwise an upgraded-but-idle repo stays broken until its next real edit — the exact field-retest scenario. Hot-path cost on healthy repos stays bounded to the two counts.
3. **Fixtures mirror production schema:** the end-to-end reconcile/backfill fixtures use the REAL production column set (`id, path, kind, language, lines, section, text, chunk_hash, vector` — no `tags`); the fixture-reality divergence that hid this defect is retired. A with-`tags` variant may remain as a secondary case, never as the primary path.
4. **Persist the one-time diagnostics:** the store's provisioning note, crash-window warning, reconcile-skip message (with the exception text), and legacy-FTS-drop lines are appended (best-effort, bounded) to a persisted log under `.wavefoundry/logs/` so field anomalies are greppable after the fact — the field investigation only recovered the skip line by forcing `--full` and tapping raw stdout.
5. **`wave_index_health` chunk-index advisory:** the `state_store` block gains per-table `{lance_rows, registry_rows}` and health emits a diagnostic when the registry covers materially less than Lance (the field signature: 110 registry ids vs ~12,500 Lance rows read as `integrity: ok`). Fail-safe, read-only, absent tables skipped.
6. **Regression fixture:** a Lance table with the production schema (no `tags`) must backfill successfully through the reconcile; the fixture also pins that `id`/`path`/`text`-missing tables still take the skip path.

## Scope

**Problem statement:** the chunk-index backfill projects a column (`tags`) that production Lance tables never contain; the projection fails on every real repo, silently, leaving the lexical layer partially or completely empty with no health signal — and the test fixtures include the phantom column, so the suite never noticed.

**In scope:**

- `indexer.py`: schema-tolerant `_fetch_rows` (intersect with `table.schema`); route store diagnostics to the persisted log.
- `index_state_store.py`: best-effort bounded append-log helper; use it alongside the existing stdout/stderr prints (provisioning, crash-window, reconcile rebuild, skip reasons).
- `server_impl.py`: `_state_store_health_summary` chunk-index coverage counts + health diagnostic.
- Tests: production-schema (no-`tags`) fixture end-to-end as the primary reconcile path; required-column skip path; health advisory fixture; log persistence.

**Out of scope:**

- Changing Lance table schemas or forcing rebuilds (the fix reads what exists).
- The `wave_scan_secrets` instrumentation passthrough (separate queued follow-up).
- TS/JS supertype extraction (separate queued follow-up).

## Acceptance Criteria

- [x] AC-1: A fixture Lance table with the PRODUCTION schema (`id, path, kind, language, lines, section, text, chunk_hash, vector` — no `tags`; field- and local-verified) backfills fully through the reconcile — registry and FTS row counts equal Lance's, `tags` defaults empty, lexical search over the backfilled rows works; the verbatim field exception can no longer occur (projection never requests absent optional columns). *(`SchemaTolerantBackfillTests.test_production_schema_table_backfills_end_to_end` — real Lance table, schema pinned to the production column list.)*
- [x] AC-2: The primary end-to-end reconcile fixtures use the production column set; any with-`tags` table is a secondary variant only (fixture-reality divergence retired). *(Primary fixture is tag-less; `test_with_tags_table_still_backfills` is the explicit secondary variant. Note: the prior "divergence" was precisely NO end-to-end coverage — every old reconcile test passed a `lambda: rows` fetcher, so `_fetch_rows` never ran against a real table; these are the first tests that exercise the projection itself.)*
- [x] AC-3: A table missing a REQUIRED column (`id`/`path`/`text`) still takes the fail-safe skip path (no crash, no partial write), now with the skip reason persisted to the log. *(`test_missing_required_column_takes_skip_path_and_persists_reason`.)*
- [x] AC-4: The store's one-time diagnostics (provisioning, crash-window, reconcile skip/rebuild, legacy-FTS drop) are appended to a persisted, bounded log under `.wavefoundry/logs/`, and a fixture proves a reconcile-skip reason is recoverable from disk after the fact. *(`StoreLogTests` ×4 + AC-3's persistence assert; live-verified — `.wavefoundry/logs/index-state.log` captured this repo's own heal.)*
- [x] AC-5: `wave_index_health`'s `state_store` block reports per-table `lance_rows`/`registry_rows`, and a materially-under-covered chunk index (field signature) produces a visible diagnostic instead of `integrity: ok` silence. *(`test_health_summary_reports_chunk_index_coverage` — asserts `integrity: ok` alongside `covered: false`, then covered after backfill; `chunk_index_undercovered` diagnostic wired in `wave_index_health_response`.)*
- [x] AC-6: A ZERO-CHANGE build against an under-covered store still heals it (the up-to-date early return falls through to the reconcile when the cheap coverage probe flags a gap; a healthy store keeps the fast exit) — fixture-proven. *(`ZeroChangeHealProbeTests` ×5 + LIVE: deleted 5,000 registry rows, ran a no-change build — "index is up to date" AND the gap healed to 14,389; healthy rerun exited in 1.4s with no reconcile.)*
- [x] AC-7: This repo's own store backfills to full coverage on a live post-fix build (registry/FTS counts reach Lance row counts for both tables), and full framework tests run bytecode-free with docs validation passing. *(Live heal DONE — docs 622→20,043, code 1,310→14,389 unique ids (Lance's raw 14,683 includes the known ~294 dup-id rows the rebuild dedupes); post-refinement health reads `covered: true` on both tables; full suite 4,847 OK bytecode-free; `wave_validate` clean.)*

## Tasks

- [x] Make `_fetch_rows` schema-tolerant (intersect with `table.schema`; required-column guard).
- [x] Add the zero-change heal fall-through (cheap coverage probe in the up-to-date early return).
- [x] Add the bounded store log helper; wire the four diagnostic sites through it.
- [x] Add chunk-index coverage to `_state_store_health_summary` + health diagnostic.
- [x] Convert primary reconcile/backfill fixtures to the production (no-`tags`) schema; add required-column skip, log persistence, and health advisory fixtures.
- [x] Live verification: post-fix build on this repo backfills the store to full Lance coverage.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| schema-tolerance | implementer | — | The release-blocking fix |
| visibility | implementer | — | Persisted log + health advisory |
| tests-docs | qa-reviewer | both | Fixtures + suite + validation |


## Serialization Points

- Single-change wave; the production-schema fixture plus the live backfill of this repo's own store are the completion gates (they reproduce the field precondition exactly).

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — backfill schema-tolerance note (one line).
- N/A otherwise: a robustness fix inside existing flows; no boundary change.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The release-blocking defect. |
| AC-2 | required | The divergent fixtures are WHY a never-worked path shipped green. |
| AC-3 | required | The fail-safe posture must survive the fix. |
| AC-4 | required | The field investigation was blinded by stderr-only diagnostics — twice. |
| AC-5 | required | An empty lexical layer must never read as healthy. |
| AC-6 | required | The field-retest scenario is upgrade-then-idle; without the fall-through the fix is invisible there. |
| AC-7 | required | Live proof on real data + standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-11 | Drafted from the operator's field test of RC `1.12.0+pbj4`: verbatim `Schema error: No field named tags` from the hardcoded reconcile projection; swallow-by-design left the field store delta-only, invisible to health. Release held; fix folds into 1.12.0. | Field report (exception + schema listing + row counts + retry semantics); `indexer.py` `_fetch_rows` hardcoded cols; fail-safe catch. |
| 2026-07-11 | Root cause CORRECTED by second field report + local verification: production Lance tables NEVER have `tags` (chunker imports `_infer_tags`, never calls it; schema inferred from tag-less chunk dicts). Field repo schema `[id,path,kind,language,lines,section,text,chunk_hash,vector]` matches this repo exactly; this repo's own store is equally broken (registry docs 598/20,020, code 1,310/14,683). Tests passed only because fixtures hand-build rows WITH `tags`. Field `fts_docs` 162 = stale pre-1.12 incremental leftovers; `fts_code` 0 = fresh 1.12 provisioning failing on first attempt. Diagnostics confirmed never persisted (recovered only via forced `--full` + raw stdout capture). | Field follow-up (verbatim skip lines for docs AND code, on-disk schema listing, unchanged row counts after `--full`); local schema/count probes; `chunker.py` grep (`_infer_tags` dead import). |
| 2026-07-11 | Implemented: schema-tolerant `_fetch_rows` (column intersection with `table.schema`, `id`/`path`/`text` required guard); zero-change heal fall-through in `build_index`'s up-to-date early return (cheap probe: cold flag + registry `count(*)` vs Lance `count_rows()`, material gap = `max(8, lance_rows // 50)`); persisted store log `store_log()` → `.wavefoundry/logs/index-state.log` (bounded 512KB, best-effort) wired at provisioning/crash-window/rebuild-complete/reconcile-skip/delta-sync-skip/legacy-FTS-drop sites; `wave_index_health` `state_store.chunk_index` coverage block + `chunk_index_undercovered` diagnostic. Bonus defect found by the new fixtures and fixed: the cold flag leaked permanently-set when the reconcile itself CREATED the store (read-before-create saw False → the `if cold:` clear never ran) — the clear is now unconditional after a successful rebuild. LIVE verification on this repo: changed build healed docs 622→20,043 / code 1,310→14,389; sabotage (−5,000 registry rows) + zero-change build healed via the fall-through; healthy zero-change rerun kept the 1.4s fast exit. 18 new tests (9 backfill/probe + 4 log + 2 health + wiring pins) green. | `indexer.py` `_fetch_rows`/`_chunk_index_needs_heal`/early-return fall-through; `index_state_store.py` `store_log`/`registry_chunk_count`/`chunk_index_is_cold`/unconditional cold-clear; `server_impl.py` coverage + diagnostic; `test_fts_lexical_layer.py` `SchemaTolerantBackfillTests`/`ZeroChangeHealProbeTests`/`StoreLogTests`; `test_server_tools.py` coverage tests; live build transcripts + `.wavefoundry/logs/index-state.log`. |
| 2026-07-11 | FIELD-VERIFIED on the original broken fixture (RC `1.12.0+pbjw`): repair half fired inside the upgrade's own index phase — no `tags` error, no skip; `fts_code` 8→3,029, `fts_docs` 102→3,085 (full parity with Lance unique ids; the fixture's 90 extra raw code rows are dup-id churn, correctly excluded by id-based coverage). Subsequent zero-change build ran clean with no repair re-fire (stable, not looping). Detection half verified by swapping the preserved broken `index-state.sqlite` back in: `covered: false` both tables + the `chunk_index_undercovered` diagnostic fired verbatim; restored store reads `covered: true`, integrity ok, zero diagnostics. Provenance restored: `code_ask` citations now carry `["docs","lexical"]`/`["code","lexical"]` on previously FTS-less docs. Same-semver build-successor adoption (`pbj4`→`pbjw`) worked. Operator verdict: RC clear to release from this fixture. | Operator retest report 2026-07-11: verbatim `index-state.log` provisioning/crash-window lines, before/after row counts, swapped-store health output, `code_ask` provenance probe. |
| 2026-07-11 | Refinement from live health verification: coverage compares made exact-first via sync-time counts (see Decision Log) after the raw-vs-registry threshold misread this repo's +294 Lance dup-id margin as permanent under-coverage. Probe/health/tests updated: `test_exact_tracking_heals_even_small_drift` (any drift from recorded counts heals — exact knowledge beats proportional waiting), `test_duplicate_lance_ids_do_not_read_as_undercoverage` (raw 30/unique 20 fixture keeps the fast exit). Live: post-build health reads `covered: true` on both tables; zero-change rerun exits in 1.2s with no reconcile. | `chunk_sync_counts`/`_record_chunk_sync_counts` in `index_state_store.py`; probe + health updated; 52 tests green in `test_fts_lexical_layer.py`, 9 in the health class. |



## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-11 | Fix = column-intersection at the fetch (heal in place), NOT auto-escalating schema mismatch to a full rebuild. | The store writers already default missing fields, so tag-less rows are perfectly usable with empty `tags`; a forced full re-embed punishes every field repo for a column the lexical layer can live without. Field evidence proves rebuild wouldn't even help: `--full` recreates the table with the SAME tag-less schema. | **Auto full rebuild on schema mismatch:** weakness — hours of re-embedding fleet-wide AND ineffective (rebuilt tables are still tag-less). **Require operator `--full`:** same ineffectiveness plus silent-until-manual, the exact failure mode being fixed. |
| 2026-07-11 | Do NOT start emitting `tags` from the chunker in this wave. | Wiring `_infer_tags` into chunk emission changes chunk hashes/Lance schemas fleet-wide (full re-embed) to populate a filter column whose value is derivable from `path` at query time; it is a separate enhancement decision, not part of the release-blocking repair. | **Wire `_infer_tags` now:** weakness — turns a surgical release-blocker fix into a schema migration; the `tags_any` filter can be served later or computed query-side. |
| 2026-07-11 | Coverage compares (heal probe + health `covered` flag) are EXACT-FIRST against sync-time counts recorded at each successful reconcile (`chunk_sync_raw_<table>` / `chunk_sync_unique_<table>` meta), with the proportional raw-vs-registry threshold only as the never-reconciled fallback. | Live health on this repo exposed the flaw in the raw compare: Lance ids are NOT unique (+294 dup-id rows here), so raw `count_rows` exceeds the registry's unique count on a FULLY-SYNCED store — one row past the threshold meant `covered: false` forever and a quiet full-id-scan reconcile on every zero-change build. Exact tracking eliminates the dup-margin false positive AND promptly heals even 1-row genuine crash windows (better than the threshold's wait-for-next-changed-build). | **Dedupe-aware live compare (count distinct Lance ids per probe):** weakness — requires the full id scan on every probe, exactly the cost the cheap probe exists to avoid. **Loosen the threshold:** weakness — the dup margin is unbounded and repo-specific; any fixed slack either false-positives or masks real gaps. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Another absent column class appears later | The intersection is generic (any optional column); only `id`/`path`/`text` are load-bearing and guarded explicitly. |
| Log growth | Bounded append (size-capped truncate-and-continue), best-effort, never fails a build. |
| Health count reads add cost | Read-only row counts, fail-safe, only on the explicit health tool — not on any hot path. |
| Zero-change probe slows the post-edit-hook hot path | Probe = one SQLite `count(*)` + one Lance `count_rows()` per table (metadata reads); the reconcile itself only runs when under-coverage is detected. |
| Empty `chunk_hash` defaults could churn incremental drift compares | `chunk_hash` exists in every real schema (field + local verified); its optionality is defensive only — pinned by the production-schema fixture. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
