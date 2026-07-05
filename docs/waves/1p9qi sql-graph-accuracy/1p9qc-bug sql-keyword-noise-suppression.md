# SQL extraction: suppress keyword tokens leaking into call/import edges

Change ID: `1p9qc-bug sql-keyword-noise-suppression`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-05
Wave: TBD

## Rationale

Live-run confirmed (guru investigation, 2026-07-03): indexing a plain `SELECT * FROM users JOIN orders ON users.id = orders.user_id` emits — alongside the one correct `calls → users` edge — spurious edges to `external::FROM`, `external::JOIN`, `external::ON`, `external::SELECT`, `external::WHERE`, plus dotted-column tokens (`external::users.id`, `external::orders.user_id`). Root cause: SQL-mode call nodes are matched by type substring (`select`/`where`/`join`/`from`/`into`/`call`/`update`/`delete`/`insert`, `_ts_is_call_node`, `graph_indexer.py:2844-2845`) and their targets come from the generic identifier-regex fallback (`_ts_relation_candidates`, `graph_indexer.py:6021`, regex fallback at `:6061`), whose keyword-noise strip applies **only when `relation == "import"`** (`graph_indexer.py:6070`) — call-relation candidates are never keyword-filtered. Freshness re-verify 2026-07-04 (tree at `GRAPH_BUILDER_VERSION` 37, post-`1p9qh`/`1p9q3`): the defect reproduces unchanged, and the same keyword tokens **also leak on the `imports` relation** (`external::FROM/JOIN/ON/WHERE` import edges, plus self-referential `schema.sql::users → external::users` from CREATE TABLE) — the SQL import field-name path bypasses the strip and the `_RELATION_KEYWORD_NOISE` membership check is case-sensitive (`FROM` ≠ `from`), so Requirement 1's all-relation, case-insensitive filter is exactly what is needed.

Every SQL file in a target repo therefore mints fake external nodes named after SQL keywords. These pollute unique-candidate sets (an `external::SELECT` in one file and a legitimate symbol named `select` elsewhere can now interfere), inflate edge counts, degrade `wave_graph_report`/community quality, and would poison the `1p9qf` embedded-SQL bind stage's candidate space. The single existing SQL test (`test_tree_sitter_markup_and_sql_extract_symbols`, `test_graph_indexer.py:296`) asserts nothing about reference edges, so the bug ships silently.

## Requirements

1. **SQL keyword stoplist for call/reference candidates.** In SQL mode, relation candidates are filtered against a case-insensitive SQL keyword stoplist (SELECT/FROM/JOIN/ON/WHERE/GROUP/ORDER/BY/INSERT/INTO/UPDATE/DELETE/SET/VALUES/AS/AND/OR/NOT/NULL/LEFT/RIGHT/INNER/OUTER/UNION/CREATE/TABLE/VIEW/INDEX/PRIMARY/KEY/... — enumerated as a constant, not exhaustive here) before any edge is emitted, for **all** relation types, not just imports.
2. **Column-token handling.** Dotted `table.column` candidates do not emit their own external edges; they reduce to the table segment (which then resolves or goes external once) or are dropped when the table is already referenced in the same statement — no `external::users.id`-style nodes remain.
3. **Genuine references preserved.** Table/view references (`users`, `orders`, `schema.users`) continue to emit exactly as today, including the working cross-file resolution to SQL-defined nodes.
4. **Scope discipline.** The filter applies in SQL mode only; no other language's candidate stream changes (the shared regex itself is untouched or changes are SQL-gated).
5. **Version bump + tests.** `GRAPH_BUILDER_VERSION` bumped; the SQL test surface grows from one vacuous assertion to a pinned edge-set test (exact expected edges for a representative multi-clause script, asserting both presence of real references and absence of every keyword/column token).

## Scope

**Problem statement:** SQL keyword and column tokens leak into call/import candidates because the keyword-noise strip is import-only, minting fake `external::` nodes from every SQL file and polluting candidate sets graph-wide.

**In scope:**

- SQL-mode candidate filtering (keywords, all relations) and dotted column-token reduction.
- Exact-edge-set SQL fixture test replacing the vacuous coverage.
- Version bump.

**Out of scope:**

- Structured clause-aware extraction, view→table `reads` edges, table/view kinds (`1p9qd`).
- Procedure recovery (`1p9qe`); embedded SQL (`1p9qf`).
- Dialect-specific keyword variance beyond a sane common superset (the stoplist constant is extensible).

## Acceptance Criteria

- [x] AC-1: The investigation's live-repro script (`SELECT * FROM users JOIN orders ON ...` with schema files) produces zero edges whose target label is a stoplisted keyword (asserted over the full payload edge set) and zero dotted column-token externals, while `users`/`orders` references remain with unchanged targets and confidences. Unit-tested with an exact expected edge set. — `test_sql_keyword_and_column_noise_suppressed_exact_edge_set` (exact 12-edge set at THIS change's landing + explicit absence sweeps); flip-verified: fails pre-fix (11 keyword externals, 3 dotted column externals, 2 self-referential imports), passes post-fix. **History note (1p9qi review):** `1p9qd`'s later clause-aware rewrite (same wave) REWROTE this same test to the clause-aware model — `calls`/`imports` migrated to `reads`/`writes`, consolidating the schema-qualified split — landing at an exact 8-edge set (see `1p9qd`'s own AC-1 evidence). The 12-edge count above is this change's point-in-time result, superseded in-tree by 1p9qd's rewrite; both numbers are correct for their respective moment, not a discrepancy.
- [x] AC-2: Cross-file table resolution (`queries.sql` → `schema.sql::users`) still binds at the same confidence (currently `RECEIVER_RESOLVED`, via the `1p7dg` unique-bind promotion — live-verified 2026-07-04) — regression-pinned. Unit-tested. — pinned inside the exact edge set (`("calls", "db/queries.sql", "db/schema.sql::users", "RECEIVER_RESOLVED")` and the `orders` twin); live post-fix probe confirms unchanged targets and confidences.
- [x] AC-3: Non-SQL languages' candidate extraction is byte-identical on a representative fixture set (the filter is SQL-gated). Unit-tested. — the pre-existing `SharedImportCandidateBaselineTests` (Kotlin/C#/Go/TS import-candidate baselines pinned in 1p9q9) pass unchanged, and new `test_sql_stoplist_never_touches_non_sql_candidates` pins the call-relation flip direction (JS functions literally named `select`/`update`/`from` keep emitting).
- [x] AC-4: `GRAPH_BUILDER_VERSION` bumped; `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`. — Satisfied at wave integration (2026-07-05): the coordinated 37→38 bump landed with a changelog naming 1p9qc's contribution (all-relation SQL keyword stoplist + column-token reduction + self-referential import suppression = extraction-output change); full suite green post-bump, `wave_validate` clean, no `__pycache__` (integration gates, wave.md Review Checkpoints).

## Tasks

- [x] Add the SQL keyword stoplist constant and apply it to all-relation candidate filtering in SQL mode; implement dotted-token reduction. — `_SQL_RELATION_KEYWORD_STOPLIST` + `_sql_relation_candidate_filter` in `graph_indexer.py`, applied at both `_ts_relation_candidates` return paths (field-name path and regex fallback), SQL-gated; plus the SQL self-referential-import skip at the import emit loop.
- [x] Replace/extend the SQL test with the exact-edge-set fixture (multi-clause script incl. JOIN/WHERE/INSERT/UPDATE forms); regression fixtures for cross-file resolution and non-SQL languages. — 4 new tests in `test_graph_indexer.py` (exact edge set incl. DELETE + schema-qualified SELECT; self-referential CREATE TABLE; unit-level dotted-reduction pins; JS SQL-gating flip); existing 1p9q9 non-SQL import-candidate baselines pass unchanged.
- [x] Bump `GRAPH_BUILDER_VERSION` with changelog entry; run `run_tests.py` + `wave_validate`; clean `__pycache__`. — Done at wave integration 2026-07-05: coordinated 37→38 bump with 1p9qc named in the changelog; suite/validate/pycache gates re-verified post-bump.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-filter | implementer | — | Stoplist + all-relation SQL-mode filtering + dotted-token reduction. |
| ws2-tests | implementer | ws1-filter | Exact-edge-set fixture + regression pins. |


## Serialization Points

- Land first in the SQL wave: `1p9qd`'s structured extraction and `1p9qf`'s bind stage both assume a keyword-clean candidate space, and their tests would otherwise encode the noise.
- Single wave-level `GRAPH_BUILDER_VERSION` bump.

## Affected Architecture Docs

N/A — defect fix restoring intended extraction semantics; no boundary, flow, or contract change (the wave-level capability-notes audit covers any SQL wording).

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The pollution must be provably gone, by exact edge-set assertion, not spot checks. |
| AC-2 | required | The one working SQL behavior (cross-file table resolution) must not regress. |
| AC-3 | required | SQL-gating must be verified, not assumed — the shared fallback serves every language. |
| AC-4 | required | Standing version-bump and merge gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the Java/SQL accuracy investigation. Live extraction run reproduced the noise (`external::FROM/JOIN/ON/SELECT/WHERE`, dotted column tokens); root cause traced to import-only keyword strip (then `graph_indexer.py:5249`) over substring-matched SQL call nodes (then `:2428-2429`) with regex fallback (then `:5240`); sole SQL test asserts nothing about reference edges (`test_graph_indexer.py:296,317-331`). | Guru investigation 2026-07-03 (live runs via `~/.wavefoundry/venv`). |
| 2026-07-04 | Reality-check freshness lane (wave open): live repro re-run on the current tree (`GRAPH_BUILDER_VERSION` 37, post-`1p9qh`/`1p9q3`) — noise unchanged: `calls → external::FROM/JOIN/ON/SELECT/WHERE` plus dotted externals (`users.id`, `orders.user_id`, `users.active`); keyword externals additionally minted on the `imports` relation; `users`/`orders` cross-file binds intact at `RECEIVER_RESOLVED` (the value AC-2 pins). Anchors refreshed after `1p9qh` line drift: call-node match `_ts_is_call_node` `:2844-2845`, regex fallback `:6061`, import-only strip `:6070`; test anchor `test_graph_indexer.py:296,317-331` unchanged. Coordinated wave version bump is now 37→38. | Reality-check live run via `~/.wavefoundry/venv`, 2026-07-04. |
| 2026-07-04 | **Implemented.** Pre-fix live repro reproduced the exact documented edge list (venv subprocess over the real grammar): calls → `external::FROM/JOIN/ON/SELECT/WHERE/INSERT/INTO/UPDATE/DELETE/SET/VALUES` + dotted `users.id`/`orders.user_id`/`users.active`; imports → `external::FROM/JOIN/ON/INTO/WHERE` + dotted; self-referential `db/schema.sql::users → external::users` and `::orders → external::orders`. Fix: (1) `_SQL_RELATION_KEYWORD_STOPLIST` (casefold-checked common superset incl. type keywords) + `_sql_relation_candidate_filter` applied to ALL relation types at both `_ts_relation_candidates` return paths, SQL-mode only; (2) dotted-token handling uses the grammar's exact structural signal within the clause node — dotted `field` descendants (column refs) reduce to their `object_reference` table segment (deduped = dropped when the table is already referenced), dotted `object_reference` descendants (schema-qualified tables, `analytics.events`) kept whole per Requirement 3, unmatched dotted tokens reduce to first segment; (3) bare column tokens (`SET active = 0`, INSERT column lists) that appear only as `field`/`column` nodes are dropped (object_reference membership wins ties) — same defect family, keeps the exact-set baseline noise-free per the wave watchpoint; (4) SQL self-referential-import skip at the import emit loop (a CREATE TABLE's own `object_reference` name node substring-matches `_ts_is_import_node` via "reference"; a definition never imports itself — deliberate: also covers self-FK self-loops). Post-fix flip verified live: all keyword/dotted/bare-column/self-referential edges gone; `users`/`orders` binds unchanged at `RECEIVER_RESOLVED`; retained as-today externals: `audit_log`, `analytics.events`, and the field-name-path split `analytics`+`events` (1p9qd consolidates). Flip direction proven by stash-run: 3 of 4 new tests fail on the pre-fix tree. Full suite 4,532/43 green (+4 over baseline); `wave_validate` clean. | `graph_indexer.py` (`_SQL_RELATION_KEYWORD_STOPLIST`, `_sql_relation_candidate_filter`, import-loop skip); `test_graph_indexer.py` (4 new `test_sql_*` tests); venv probe pre/post runs 2026-07-04. |
| 2026-07-04 | **Findings recorded for later changes (not fixed here, scope discipline):** (a) String-literal contents leak as call candidates in SQL mode — `INSERT ... VALUES ('x')` emits `calls → external::x` (the regex fallback scans the literal's text; not a keyword, not a column node). 1p9qd's structured statement extraction should replace the regex candidate source entirely; until then the exact-set fixture uses numeric literals to avoid encoding this residue. (b) The schema-qualified field-name path splits `analytics.events` into THREE import externals (`analytics.events`, `analytics`, `events`) — pre-existing today-behavior retained per Requirement 3; 1p9qd owns consolidating it. (c) `_ts_is_import_node`/`_ts_is_call_node` SQL substring matching remains broad (`object_reference` matches "reference"; `keyword_*` nodes match their keyword) — harmless now that candidates are filtered, but 1p9qd's clause-aware extraction should tighten node selection rather than rely on the filter. (d) Table aliases (`SELECT u.id FROM users u`) still mint `external::u`-style candidates (alias `u` is a bare regex token; `u.id` reduces to `u`) — pre-existing, unchanged by this fix; 1p9qd's alias exclusion (AC-6 family) covers it. | Live probe observations 2026-07-04. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | SQL-gated stoplist filter at the candidate stage (approach A). | Kills the pollution at its source for every relation type with a bounded, testable constant; zero risk to other languages; leaves the door open for `1p9qd`'s structured extraction to replace regex candidates entirely. | (B) Extend `_RELATION_KEYWORD_NOISE` (the shared import-strip) to calls for all languages — weakness: `select`/`update`/`delete` are legitimate identifier names in host languages; a global call-relation stoplist would suppress real references outside SQL. (C) Wait for `1p9qd` structured extraction to obsolete the regex path — weakness: leaves the pollution live meanwhile and forces `1p9qd`'s tests to encode noise; the stoplist is cheap insurance either way. |
| 2026-07-04 | Dotted-token classification uses the grammar's structural signal (dotted `field` descendant = column ref → reduce to its `object_reference` table; dotted `object_reference` descendant = schema-qualified table → keep whole) instead of blind text-segment reduction. | Pure text reduction cannot distinguish `users.id` (table.column → table is FIRST segment) from `analytics.events` (schema.table → the whole token is the reference); blind first-segment reduction would have turned `analytics.events` into a bogus `external::analytics`, breaking Requirement 3's "schema-qualified references emit as today". The clause node is already in hand at the filter site; scanning its descendants for `field`/`column`/`object_reference` types is a targeted disambiguation, NOT `1p9qd`'s statement-analysis unit (no clause semantics, no read/write direction, no object kinds). | Text-only heuristics (first-segment or last-segment reduction) — each breaks one of the two dotted forms. Deferring dotted handling to `1p9qd` — leaves `external::users.id` nodes live and forces noise into the wave's baseline tests. |
| 2026-07-04 | Bare column tokens (`active`, `event`) that appear in the clause only as `field`/`column` nodes are also suppressed. | Same defect family and same structural signal as the dotted rule (Requirement 2 is titled "Column-token handling"); without it the mandated INSERT/UPDATE fixture forms would force `external::active`/`external::event` noise INTO the exact-edge-set baseline, which the wave watchpoint explicitly forbids. Table wins ties (object_reference membership checked first), so a name that is genuinely referenced as a table in the same clause is never dropped. | Leave bare column tokens for `1p9qd` — would encode noise into the baseline expectations that all four later changes build on. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Stoplist over-suppresses a legitimate table named like a keyword (a table named `values`). | Real but rare and detectable: suppression only in SQL mode where the identifier-vs-keyword ambiguity is the grammar's, not ours; the stoplist is a reviewable constant; a table named `values` referenced via `schema.values` still survives (dotted reduction keeps the table segment). Documented limitation. |
| Dialect keywords missing from the stoplist leak through. | The exact-edge-set test uses multi-clause fixtures; the constant is extensible; residual rare leaks are strictly better than today's systematic ones. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
