# SQL extraction: suppress keyword tokens leaking into call/import edges

Change ID: `1p9qc-bug sql-keyword-noise-suppression`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

Live-run confirmed (guru investigation, 2026-07-03): indexing a plain `SELECT * FROM users JOIN orders ON users.id = orders.user_id` emits — alongside the one correct `calls → users` edge — spurious edges to `external::FROM`, `external::JOIN`, `external::ON`, `external::SELECT`, `external::WHERE`, plus dotted-column tokens (`external::users.id`, `external::orders.user_id`). Root cause: SQL-mode call nodes are matched by type substring (`select`/`where`/`join`/`from`/`into`/`call`/`update`/`delete`/`insert`, `graph_indexer.py:2428-2429`) and their targets come from the generic identifier-regex fallback (`_ts_relation_candidates`, `graph_indexer.py:5240`), whose keyword-noise strip applies **only when `relation == "import"`** (`graph_indexer.py:5249`) — call-relation candidates are never keyword-filtered.

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

- [ ] AC-1: The investigation's live-repro script (`SELECT * FROM users JOIN orders ON ...` with schema files) produces zero edges whose target label is a stoplisted keyword (asserted over the full payload edge set) and zero dotted column-token externals, while `users`/`orders` references remain with unchanged targets and confidences. Unit-tested with an exact expected edge set.
- [ ] AC-2: Cross-file table resolution (`queries.sql` → `schema.sql::users`) still binds at the same confidence — regression-pinned. Unit-tested.
- [ ] AC-3: Non-SQL languages' candidate extraction is byte-identical on a representative fixture set (the filter is SQL-gated). Unit-tested.
- [ ] AC-4: `GRAPH_BUILDER_VERSION` bumped; `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Add the SQL keyword stoplist constant and apply it to all-relation candidate filtering in SQL mode; implement dotted-token reduction.
- [ ] Replace/extend the SQL test with the exact-edge-set fixture (multi-clause script incl. JOIN/WHERE/INSERT/UPDATE forms); regression fixtures for cross-file resolution and non-SQL languages.
- [ ] Bump `GRAPH_BUILDER_VERSION` with changelog entry; run `run_tests.py` + `wave_validate`; clean `__pycache__`.

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
| 2026-07-03 | Scoped from the Java/SQL accuracy investigation. Live extraction run reproduced the noise (`external::FROM/JOIN/ON/SELECT/WHERE`, dotted column tokens); root cause traced to import-only keyword strip (`graph_indexer.py:5249`) over substring-matched SQL call nodes (`:2428-2429`) with regex fallback (`:5240`); sole SQL test asserts nothing about reference edges (`test_graph_indexer.py:296,317-331`). | Guru investigation 2026-07-03 (live runs via `~/.wavefoundry/venv`). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | SQL-gated stoplist filter at the candidate stage (approach A). | Kills the pollution at its source for every relation type with a bounded, testable constant; zero risk to other languages; leaves the door open for `1p9qd`'s structured extraction to replace regex candidates entirely. | (B) Extend `_RELATION_KEYWORD_NOISE` (the shared import-strip) to calls for all languages — weakness: `select`/`update`/`delete` are legitimate identifier names in host languages; a global call-relation stoplist would suppress real references outside SQL. (C) Wait for `1p9qd` structured extraction to obsolete the regex path — weakness: leaves the pollution live meanwhile and forces `1p9qd`'s tests to encode noise; the stoplist is cheap insurance either way. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Stoplist over-suppresses a legitimate table named like a keyword (a table named `values`). | Real but rare and detectable: suppression only in SQL mode where the identifier-vs-keyword ambiguity is the grammar's, not ours; the stoplist is a reviewable constant; a table named `values` referenced via `schema.values` still survives (dotted reduction keeps the table segment). Documented limitation. |
| Dialect keywords missing from the stoplist leak through. | The exact-edge-set test uses multi-clause fixtures; the constant is extensible; residual rare leaks are strictly better than today's systematic ones. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
