# SQL extraction: clause-aware table references, view lineage edges, and honest object kinds

Change ID: `1p9qd-enh sql-structured-statement-extraction`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

SQL extraction today is substring-and-regex over the parse tree: any node whose type contains `select`/`from`/`join`/etc. is a "call node" (`graph_indexer.py:2428-2429`) and its identifiers become undifferentiated `calls` candidates via the generic regex (`graph_indexer.py:5240`). Live runs confirm the consequences (guru investigation, 2026-07-03): tables and views are indistinguishable (both generic `kind="class"`, `_ts_kind_for_definition` SQL branch `graph_indexer.py:1976-1981,2049-2050`), no column nodes exist, view definitions don't record what they read from, `schema.table` qualification isn't modeled, and reference direction/statement kind (read vs write) is lost — an `INSERT INTO audit_log` and a `SELECT FROM audit_log` produce the same edge shape.

The grammar exposes clause structure (`object_reference` nodes under from/join/insert/update clauses), so the extractor can be clause-aware instead of token-scraping: precise table references with read/write distinction, view → source-table lineage, and honest node kinds. This is also the foundation `1p9qf` (embedded SQL) reuses — its bind stage needs exactly "extract referenced tables from a SQL statement" as a callable unit.

## Requirements

1. **Clause-aware reference extraction.** Table references come from `object_reference` positions in FROM/JOIN/INSERT INTO/UPDATE/DELETE FROM/MERGE clauses — not from the generic identifier regex. Each reference records the statement kind; reads (`SELECT`/`FROM`/`JOIN` sources) emit `reads` edges, writes (`INSERT`/`UPDATE`/`DELETE`/`MERGE` targets) emit a write-flavored edge (`writes` relation added to the vocabulary, or `reads` with a `mode: write` edge property — decide by consumer impact at implementation, Decision Log notes the tradeoff). The generic regex path is retired for SQL mode.
2. **Qualified names.** `schema.table` references resolve first against a `schema.table`-keyed lookup of SQL-defined objects, then by unique table-name match (the existing cross-file unique-candidate rule); ambiguity refuses as everywhere else.
3. **View lineage.** `CREATE VIEW v AS SELECT ... FROM t1 JOIN t2` emits `reads` edges from the view node to each source table/view — making view → table lineage traversable (and impact through views real).
4. **Honest kinds.** Table, view, and (when `1p9qe` recovers them) procedure/function/trigger nodes carry distinguishable kinds or a `sql_kind` node property (`table`/`view`/`procedure`/`function`/`trigger`) — decide representation by what `wave_map`/report/community consumers handle without special-casing; labels in reports must distinguish them either way.
5. **Extraction unit reusable for embedded SQL.** The statement→referenced-tables extraction is a standalone function taking SQL text (parse + clause walk + reference list with read/write kind), callable by `1p9qf`'s bind stage without file-node context.
6. **Version bump + tests + calibration.** `GRAPH_BUILDER_VERSION` bumped; exact-edge-set fixtures for each clause form; a realistic migration-directory fixture (Flyway-style numbered DDL files) demonstrating lineage; before/after edge quality counts recorded.

## Scope

**Problem statement:** SQL references are token-scraped without clause, direction, qualification, or kind information, so the graph can't distinguish a view from a table, a read from a write, or trace view lineage — and there is no reusable statement-analysis unit for embedded SQL to build on.

**In scope:**

- Clause-aware reference extraction (read/write kinds), qualified-name resolution, view lineage edges, object-kind honesty, the reusable extraction unit.
- Retirement of the generic regex candidate path for SQL mode.
- Exact-edge-set + migration-fixture tests; calibration counts; version bump.

**Out of scope:**

- Column-level nodes/edges (column lineage is a scale and dialect quagmire; table-level is the value tier).
- Procedure body recovery (`1p9qe`) and embedded SQL in host languages (`1p9qf`).
- Dialect-specific statement forms beyond the common core + what the installed grammar parses (documented limitation; ERROR-node recovery is `1p9qe`).
- CTE/subquery alias resolution beyond not-emitting-false-references (aliases must not mint external nodes; full alias lineage deferred).

## Acceptance Criteria

- [ ] AC-1: For a fixture covering SELECT/JOIN/INSERT/UPDATE/DELETE/MERGE forms, the payload contains exactly the expected table-reference edges with correct read/write kinds and zero regex-derived extras. Exact-edge-set unit test.
- [ ] AC-2: `schema.table` references resolve to the schema-qualified object when defined, fall back to unique bare-name match, and refuse on ambiguity (two `users` tables in different schemas, unqualified reference → refusal). Unit-tested all three.
- [ ] AC-3: A `CREATE VIEW` chain (view → view → tables) yields traversable lineage edges; `code_impact` on a base table includes dependent views. Unit-tested against the fixture graph.
- [ ] AC-4: Table/view kinds are distinguishable in the payload and in `wave_graph_report`/`wave_map` labels; existing consumers ingest without error. Integration-shaped test.
- [ ] AC-5: The statement-analysis unit, called directly with SQL text, returns the same reference list the file path produces (parity test) — the `1p9qf` contract.
- [ ] AC-6: CTE names, table aliases, derived-table (subquery) aliases, and temp-table/table-variable sigil forms (`#temp`, `##temp`, `@tablevar`, `TEMPORARY`/`TEMP TABLE` creations) do not mint external nodes or bindable references — temp objects are statement-scoped, not schema objects (council finding, prepare review 2026-07-03). Adversarial fixture with WITH-clauses, aliases, subquery aliases, and temp forms. Unit-tested.
- [ ] AC-7: Migration-directory fixture (numbered Flyway-style files defining then altering tables) produces a coherent single node per table with all references bound; counts recorded in the Progress Log.
- [ ] AC-8: `GRAPH_BUILDER_VERSION` bumped; `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Implement the standalone statement-analysis unit (parse, clause walk, reference list with read/write + qualification), with the ERROR-node behavior delegated to `1p9qe`'s hooks.
- [ ] Wire SQL file extraction through it; retire the regex candidate path for SQL mode; add the write-flavored edge representation (decide relation vs property with a consumer sweep).
- [ ] Qualified-name lookup keying; view lineage emission; kind representation + report/map label plumbing.
- [ ] Fixtures/tests per AC-1..AC-7; calibration counts.
- [ ] Bump `GRAPH_BUILDER_VERSION`; run `run_tests.py` + `wave_validate`; clean `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-statement-unit | implementer | — | The reusable parse/clause-walk/reference unit — the core. |
| ws2-file-wiring | implementer | ws1-statement-unit | SQL-mode extraction through the unit; regex retirement; write-edge representation. |
| ws3-lineage-kinds | implementer | ws2-file-wiring | View lineage; qualified lookup; kinds + labels. |
| ws4-tests-calibration | implementer | ws3-lineage-kinds | Exact-set/adversarial/migration fixtures; parity test; calibration. |


## Serialization Points

- After `1p9qc` (noise fix) — this change's exact-edge-set tests assume a keyword-clean baseline.
- The statement-analysis unit's signature (ws1) is the contract `1p9qf` consumes — freeze it before `1p9qf` implementation starts.
- The write-edge representation decision (relation vs property) affects `docs/specs/mcp-tool-surface.md` vocabulary — coordinate with `1p9qa`'s vocabulary update if both waves are in flight.
- Single wave-level `GRAPH_BUILDER_VERSION` bump.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` — relation vocabulary (if `writes` is added) and SQL extraction capability notes. The statement-analysis unit is a new intra-module seam consumed by `1p9qf` — document its contract where indexer internals are specified.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Clause-aware precision is the point; exact-set assertion is the only honest test shape here. |
| AC-2 | required | Qualification handling is where multi-schema enterprise DBs live or die. |
| AC-3 | required | View lineage is the impact-analysis payoff. |
| AC-4 | required | Kind honesty is cheap and every consumer benefits; ingestion must be verified. |
| AC-5 | required | The parity contract is what `1p9qf` builds on; without it the reuse claim is untested. |
| AC-6 | required | Alias/CTE false references would recreate the pollution `1p9qc` just removed. |
| AC-7 | important | The migration fixture is realism insurance; a weak result prompts iteration, not blockage. |
| AC-8 | required | Standing gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the Java/SQL accuracy investigation. Confirmed by live runs: no table/view kind distinction (`graph_indexer.py:1976-1981,2049-2050`), token-scraped references with no direction/qualification, no view lineage; grammar exposes object_reference clause structure; cross-file unique-name table resolution already works (the foundation to build on). | Guru investigation 2026-07-03. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Clause-aware extraction with a reusable statement unit; table-level only (approach A). | Precision comes from the grammar's clause structure the current code ignores; the standalone unit is designed once and shared with embedded SQL; table-level is where impact questions live ("who touches this table"), column-level is a different cost class. | (B) Patch the regex path with better filtering — weakness: direction/qualification/lineage are structurally unavailable to token scraping; filtering can't add information. (C) Column-level lineage now — weakness: dialect variance and node-count explosion for a consumer that doesn't exist yet; revisit on field demand. |
| 2026-07-03 | Read/write distinction representation decided at implementation (new `writes` relation vs `mode` property on `reads`). | A new relation is cleaner semantics but touches every relation-vocabulary consumer; a property is non-breaking but weaker for query tools. The consumer sweep (report/community/path/impact) is a half-day fact-finding task that should decide it — not a guess now. | Predetermining either — rejected: the tradeoff is empirical (consumer handling), and the wave already coordinates a vocabulary update with `1p9qa` if the relation route wins. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The installed grammar mis-parses some dialect's clause forms, silently dropping references. | ERROR-node paths route to `1p9qe`'s recovery tier (loudly counted); exact-set fixtures cover the common core; residual dialect gaps are documented limitations, not silent (build log counts unparsed statements). |
| Retiring the regex path loses some reference the clause walk misses. | The migration fixture (AC-7) + before/after calibration counts surface recall regressions; the regex path's "recall" today is mostly noise (`1p9qc` evidence), so the trade is measured, not assumed. |
| `writes` relation (if chosen) breaks a consumer that hard-codes relation names. | The AC-4/consumer-sweep step verifies ingestion before the representation is locked; cluster projection is relation-agnostic by design (verified in `1p9qa` AC-5 pattern). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
