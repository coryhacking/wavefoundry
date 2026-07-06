# SQL schema-DDL faithfulness — suppress custom-type phantoms, model CREATE TYPE/DOMAIN/OPERATOR, fix SKIP LOCKED

Change ID: `1rvdq-enh sql-schema-ddl-faithfulness`
Change Status: `implementing`
Owner: Engineering
Status: planned
Last verified: 2026-07-06
Wave: TBD

## Rationale

Validating the SQL graph extractor against a real, type-dense production Postgres schema (an operator-supplied corpus: dozens of tables, ~10 custom domains, ~9 composite types, several enums, and a family of custom operators) surfaced a class of phantom `reads` edges and unmodeled definitions that the current statement unit produces on schema DDL. On a schema this type-heavy, every column whose type is a custom domain/composite/enum mints a phantom `read <typename>` edge, so the noise is proportional to the schema's type density — not a corner case. These are pre-existing behaviors in the SQL statement-unit territory (the clause-aware extraction rewrite + the in-body statement dispatch), NOT the loop-recovery tier delivered in `1rs45`; they were recorded during the `1rvdp` real-corpus validation and split here so they are tracked rather than dangling.

The core faithfulness principle: a graph `reads`/`writes` edge is DATA LINEAGE (a routine/table reads data FROM a table). A column's *type* is a type dependency, not a data read; a function call in a column DEFAULT or a `GENERATED` expression is not a table read; a pseudo-type parameter (`anyelement`) is not a table. Minting reads for these inflates the graph with edges that misrepresent data flow.

**Proprietary-data constraint:** the operator's real schema/routine corpus is proprietary and must NOT be committed. The examples in this doc use generic invented identifiers; the committed test fixtures must likewise use generic invented schemas. The real corpus is used only as a local (uncommitted) validation oracle.

## Requirements

1. **Custom-type column names no longer mint phantom `reads` — WITHOUT regressing FK / LIKE / CTAS reads.** In `handle_create_table` a column's TYPE name (custom domains, composites, enums) must NOT be emitted as a `reads`. **Verified discrimination signal (readiness primer 2026-07-06):** an `object_reference` in the create subtree is an FK read iff a `keyword_references` node precedes it within its `column_definition` (column-level FK) or within a sibling `constraint` node (table-level FK); a custom-type column's type name is a `column_definition > object_reference` with NO `keyword_references` — cleanly separable. Only NON-keyword custom names leak (builtin types like `int`/`text`/`money`/`timestamptz` parse as keyword nodes and are already clean). **The blanket `object_reference` walk does TRIPLE duty (primer strongest-challenge), so the redesign MUST NOT be "REFERENCES-only":** it also currently carries (a) `CREATE TABLE t (LIKE parent …)` — `LIKE parent` parses as `column_definition > identifier(LIKE) + object_reference(parent)`, structurally identical to a custom-type column except the `LIKE` identifier text — a GENUINE read to preserve; and (b) `CREATE TABLE t AS SELECT … FROM src` (CTAS) reads, which arrive via a `create_query` subtree `handle_create_table` has no dedicated handler for and today relies on the blanket walk to surface. The fix must PRESERVE FK reads (references-preceded), LIKE reads (whitelist the `LIKE` identifier), and CTAS reads (route `create_query` through `walk_reads`), and suppress ONLY the column-type object_references. (The earlier "FK-capture reliability gap" was NOT reproducible on generic DDL across six FK shapes — treat FK reliability as a verify-across-shapes item, not an asserted pre-existing drop.)
2. **`GENERATED ALWAYS AS (…)` and column `DEFAULT (…)` expressions no longer mint phantom reads** for the function/keyword tokens inside them. Confirmed (primer): a `DEFAULT`/generated expression with a function invocation (`DEFAULT nextval(…)`, `DEFAULT schema.gen_id()`) leaks `read nextval`/`read <fn>`; a pure arithmetic generated column (`GENERATED ALWAYS AS (col_b - col_a)`) leaks nothing. Suppress the invocation/keyword noise (reuse the existing `invocation`/`function_declaration` skip family). A genuine table read inside such an expression (rare) may be preserved or dropped — decide during design.
3. **Pseudo-type parameters (`anyelement`, `anyarray`, `anynonarray`, `anyenum`, `record`, `trigger`, `void`, …) never mint a `reads`** from a routine's signature.
4. **`CREATE TYPE` (composite + enum) and `CREATE DOMAIN` are modeled as definition nodes** (a new `sql_kind`, e.g. `type`/`domain`), so a column typed by one resolves to a real definition node instead of dangling `external::`. Confirmed (primer): today `CREATE TYPE addr AS (…)` mints a phantom self-`read addr` with no definition node; `CREATE TYPE … ENUM` leaks `read <name>` + an unrecovered region; `CREATE DOMAIN` is a full ERROR region. Scope the edge model conservatively (a column→type dependency edge is optional; decide during design whether definition nodes alone suffice).
5. **`CREATE OPERATOR` no longer falls into an unrecovered ERROR region** with no signal — recognize it (recover its `procedure = <fn>` function reference, or skip cleanly) rather than counting it as `unrecovered_regions` noise. Confirmed (primer): `CREATE OPERATOR` is a full ERROR region today, the `procedure =` fn lost. The tree-sitter-sql grammar does not parse `CREATE OPERATOR`, so this is a recovery-tier or sniff-gate question.
6. **`FOR UPDATE SKIP LOCKED` no longer inflates `unrecovered_regions` (and no phantom read).** RE-SCOPED per the readiness primer: across generic standalone / lowercase / JOIN / in-function / FOR-loop forms, `FOR UPDATE SKIP LOCKED` did NOT reproduce a `read skip` — it lands in an ERROR/unrecovered region (`unrecovered_regions: 1`), so the GENERICALLY-reproducible defect is unrecovered-region inflation, not a phantom read. (A phantom `read skip` was observed once on the proprietary corpus in a more complex FOR-loop-header SELECT; that exact shape is proprietary and stays a LOCAL oracle check, not a committed fixture.) The fix: recognize/skip the `FOR UPDATE [SKIP LOCKED|NOWAIT] | FOR SHARE` locking clause so it neither inflates unrecovered regions nor (in the complex shape) mints a phantom; the real table read is preserved. AC-6 must NOT assert "no `read skip`" against generic DDL (vacuous) — assert the unrecovered-region drop + preserved read, and cover the phantom variant only in the local proprietary check.

## Scope

**Problem statement:** The SQL statement unit mints phantom `reads` edges for custom column types, `DEFAULT`/`GENERATED` expression tokens, pseudo-type params, and `FOR UPDATE SKIP LOCKED`; and it does not model `CREATE TYPE`/`CREATE DOMAIN`/`CREATE OPERATOR`. On a type-dense schema this is broad noise that misrepresents data lineage.

**In scope:**

- `handle_create_table` column-type vs FK-target discrimination in `.wavefoundry/framework/scripts/graph_indexer.py` (the `object_reference`-as-references-read walk).
- `DEFAULT`/`GENERATED ALWAYS AS` expression handling (invocation/keyword suppression — likely reuses the existing `invocation`/`function_declaration` skips).
- Pseudo-type stoplist (extend `_SQL_RELATION_KEYWORD_STOPLIST` or a dedicated pseudo-type set).
- `CREATE TYPE`/`CREATE DOMAIN` definition nodes (new `sql_kind`); the `create_type`/`create_domain` statement dispatch in `analyze_statement`.
- `CREATE OPERATOR` recognition (sniff/recovery).
- `FOR UPDATE SKIP LOCKED` phantom suppression.
- Faithfulness fixtures using GENERIC invented schemas (the proprietary real corpus is the local-only oracle; no proprietary identifiers in committed tests).
- A `GRAPH_BUILDER_VERSION` bump (extraction-output change) and a mandatory adversarial-faithfulness review lane (this touches the SQL detection surface).

**Out of scope:**

- Full PL/pgSQL grammar support.
- Modeling operator semantics beyond recovering the `procedure =` function reference.
- Column-level lineage (this is table-granularity, as today).
- Cross-schema/`search_path` resolution beyond what the statement unit already does.

## Acceptance Criteria

- [x] AC-1: An exact-edge-set test over a generic schema fixture (custom-type names non-keyword: `usd`/`addr`/`status`) proves NO `reads` for a custom column type; genuine FK reads (column-level `REFERENCES` + table-level `CONSTRAINT … REFERENCES`) ARE all present + correctly directed; FK capture verified across ≥5 shapes; a graph-level check confirms `external::orders` (FK) present and `external::usd` (type) absent. (`test_sql_ddl_custom_type_phantom_suppression_fk_preserved`.)
- [x] AC-1b: `CREATE TABLE t (LIKE parent …)` keeps `read parent`; CTAS keeps its reads exactly once (the old blanket walk doubled them — fixed). (`test_sql_ddl_like_and_ctas_reads_preserved`.)
- [x] AC-2: `GENERATED ALWAYS AS (extract(epoch from now()))` and `DEFAULT gen_uuid()` mint no `reads`. (`test_sql_ddl_default_generated_and_pseudo_type_suppression`.)
- [x] AC-3: An `anyelement` param/return mints no `reads` (pseudo-type stoplist). (same test.)
- [x] AC-4: `CREATE TYPE … AS (…)`, `… AS ENUM (…)`, and `CREATE DOMAIN` each mint a definition node (`sql_kind` `type`/`domain`); the CREATE TYPE self-`read` phantom is gone. (`test_sql_ddl_create_type_and_domain_definition_nodes`.)
- [x] AC-5: `CREATE OPERATOR …` recognized-benign — does not inflate `unrecovered_regions`. (`test_sql_ddl_operator_and_locking_clause_recognized_benign`.)
- [x] AC-6: `SELECT … FOR UPDATE [SKIP LOCKED|NOWAIT]` / `FOR SHARE` / `FOR UPDATE OF q …` no longer inflate `unrecovered_regions`; the real table read preserved. (same test.)
- [x] AC-8 (operator-directed dialect fold-in 2026-07-06): common Oracle (`number`/`varchar2`/`clob`/`rowid`/`long`/`raw`/`nclob`/`binary_float`/`binary_double`/…) and SQL Server / T-SQL (`uniqueidentifier`/`money`/`smallmoney`/`datetime2`/`datetimeoffset`/`nchar`/`ntext`/`image`/`hierarchyid`/`sql_variant`/`geography`/`geometry`/`bit`/…) builtin type names are stoplisted, so they no longer leak phantom `reads` on non-Postgres schemas; FK reads on clean columns preserved; a CAST to a dialect type mints no phantom. (`test_sql_ddl_oracle_tsql_builtin_types_suppressed`.) KNOWN LIMITATION deferred to the `sql-dialect-robustness` follow-up: a PARENTHESIZED custom type (`number(10,2)`/`varchar2(50)`) desyncs the tree-sitter parse and can drop a trailing column's FK (pre-existing — the bare `orders` lands as an `identifier` in a sibling ERROR, not an `object_reference`); the stoplist fix does not address that deeper recovery-tier gap.
- [~] AC-7: `GRAPH_BUILDER_VERSION` bumped 41→42; full framework suite green (confirmed at integration); adversarial-faithfulness delivery lane run; `wave_validate` clean; live upgrade-heal. **The local proprietary-corpus precision re-check is `[~]`: the proprietary corpus was deleted for data hygiene per the operator constraint, so the committed generic fixtures + the earlier census stand as the validation; the operator can re-run the phantom-count-drop check locally against their corpus. No proprietary artifact committed.**

## Tasks

- [x] Characterize the exact parse shapes (done at readiness + implementation via generic-DDL probes): column-type = direct `object_reference` in `column_definition` with no preceding `keyword_references`; FK = `keyword_references`-preceded (column-level or table-level `constraint`); LIKE = leading `LIKE` identifier; CTAS = `create_query` subtree; DEFAULT/GENERATED = nested under `invocation`/`parenthesized_expression`; `CREATE TYPE` = native `create_type`; `CREATE DOMAIN`/`OPERATOR` = ERROR regions; `FOR UPDATE SKIP LOCKED` = a shred ERROR tail.
- [x] `handle_create_table` rewritten: parse-position discrimination (`_emit_fk_and_like`) — FK reads (`keyword_references`-preceded), LIKE source, CTAS via `walk_reads`; column-type/default/generated/check tokens suppressed by not minting non-FK/LIKE positions and not recursing into expression subtrees. FK verified across ≥5 shapes.
- [x] Preserve LIKE + CTAS reads (primer strongest-challenge) — AC-1b green; CTAS doubling fixed.
- [x] Suppress `DEFAULT`/`GENERATED` expression noise (achieved by the non-recursion of `_emit_fk_and_like`).
- [x] Pseudo-type stoplist (+ `skip`/`locked`/`nowait` shred tokens) in `_SQL_RELATION_KEYWORD_STOPLIST`.
- [x] `CREATE TYPE` native definition handler (`sql_kind="type"`); `CREATE DOMAIN` via recovery vocabulary (`sql_kind="domain"`).
- [x] `CREATE OPERATOR` recognition — `_sql_region_is_benign` / `_SQL_BENIGN_REGION_RE` (no `unrecovered_regions` inflation).
- [x] `FOR UPDATE [SKIP LOCKED|NOWAIT]` / `FOR SHARE` recognized-benign (same helper).
- [x] Generic-schema faithfulness fixtures (5 new tests); version bump 41→42; full suite at integration; adversarial-faithfulness lane at delivery. Local proprietary re-check `[~]` (corpus deleted for hygiene).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| ddl-phantom-suppression | implementer | — | R1/R2/R3/R6 — the column-type/default/pseudo-type/SKIP-LOCKED phantom fixes; the bulk of the recall-neutral precision gain. |
| type-domain-operator-modeling | implementer | — | R4/R5 — new definition nodes + operator recognition; disjoint from the suppression work but shares the `create_*` dispatch. |
| validation | implementer | ddl-phantom-suppression | Generic fixtures + adversarial-faithfulness lane + version bump + local proprietary-corpus re-check. |

## Serialization Points

- Shares `graph_indexer.py`'s SQL statement unit with any other SQL-region work — coordinate merge order + the single `GRAPH_BUILDER_VERSION` bump.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — the SQL statement-unit section gains the `CREATE TYPE`/`DOMAIN`/`OPERATOR` definition kinds and the column-type-vs-FK discrimination. No module-boundary or data/control-flow change beyond the SQL extractor.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The custom-type phantom is the dominant noise class on a type-dense schema. |
| AC-1b | required | Recall no-regression — the primer proved the naive REFERENCES-only redesign would drop LIKE + CTAS reads. |
| AC-2 | required | Default/generated expression noise. |
| AC-3 | important | Pseudo-type params — narrower but real. |
| AC-4 | important | Type/domain modeling closes the dangling `external::` and enables column→type resolution. |
| AC-5 | nice-to-have | CREATE OPERATOR recognition — low frequency, mostly a loudness cleanup. |
| AC-6 | required | SKIP LOCKED recurs at scale in job-queue idioms. |
| AC-7 | required | Standing version/adversarial/suite gates. |
| AC-8 | important | Operator-directed: the phantom-suppression precision must carry to Oracle/MSSQL schemas, not just Postgres. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-06 | Split out of the `1rvdp` real-corpus validation. A production PL/pgSQL routine corpus surfaced the `SKIP LOCKED` phantom; a production schema DDL surfaced the custom-type-column / default-generated / pseudo-type phantoms and the unmodeled `CREATE TYPE`/`DOMAIN`/`OPERATOR`. All pre-existing (statement-unit territory), none introduced by `1rs45`. Proprietary corpus kept local (uncommitted); this doc uses generic examples. | `1rvdp` close readout; local schema/routine census (uncommitted). |
| 2026-07-06 | **Operator-directed dialect fold-in (AC-8):** extended `_SQL_RELATION_KEYWORD_STOPLIST` with common Oracle + SQL Server/T-SQL builtin type names so the 1rvdq column-type suppression carries to non-Postgres schemas (a Guru dialect-coverage audit found the stoplist was Postgres/ANSI-biased; without this, `amt number`/`id uniqueidentifier` still leaked phantom reads). +1 test. Discovered + deferred: a parenthesized custom type (`number(10,2)`/`varchar2(50)`) desyncs the parse and drops a trailing FK (pre-existing recovery-tier gap) → routed to the `sql-dialect-robustness` follow-up. | `test_graph_indexer` green; Guru dialect audit 2026-07-06. |
| 2026-07-06 | **Delivery code+performance lane — PASS WITH NOTES, 3 fix-nows applied.** Verified linear cost, no double-count/infinite-loop in the ERROR-recurse, native-vs-recovery CREATE TYPE non-collision, owner/temp handling. Fix-nows: (1) bounded the benign-region regex to `[^;]*` so a `CREATE OPERATOR;` merged with a following unrecoverable CREATE no longer swallows it (loudness honesty); (2) reset the `saw_references` latch before the constraint/ERROR recurse (robustness); (3) removed duplicate stoplist entries. Suite re-green (513). | code/perf delivery lane 2026-07-06; probes. |
| 2026-07-06 | **Delivery adversarial-faithfulness lane — BLOCKED then fixed.** The lane (generic-DDL probes) found NO wrong edges but one SEVERE change-introduced DROP: a column-list-less `REFERENCES parent` shorthand (no `(id)`) shreds into an `ERROR` under `column_definitions` that `_emit_fk_and_like` didn't reach → the FK read was silently dropped (contradicting AC-1b). FIXED: `_emit_fk_and_like` now recurses into `ERROR` shards too (safe — only `keyword_references`-preceded object_references are minted, so no phantom resurrection); +4 regression fixtures. Also recorded the accepted stoplist over-reach trade-off. Suite re-green (513). | delivery adversarial lane 2026-07-06; `test_graph_indexer` 513 green post-fix. |
| 2026-07-06 | **Implemented all six requirements.** `handle_create_table` rewritten with `_emit_fk_and_like` parse-position discrimination (FK/LIKE/CTAS kept, column-type/default/generated suppressed, CTAS doubling fixed); pseudo-type + `skip`/`locked`/`nowait` stoplist; native `create_type` definition handler; `CREATE DOMAIN` via recovery vocabulary; `_sql_region_is_benign` for `CREATE OPERATOR` + row-locking clauses; `GRAPH_BUILDER_VERSION` 41→42. 5 new tests (all ACs) + version pin. Full `test_graph_indexer` green (513, no regressions from the rewrite). | `test_graph_indexer` 513 green; generic-DDL probes. |
| 2026-07-06 | **Readiness primer (red-team + reality-checker) — mechanism VERIFIED achievable, 4 corrections folded in.** R1 discrimination proven on the real parse tree (`keyword_references`-preceded = FK; column-type = none). Strongest challenge (severe): the blanket walk also carries `LIKE parent` + CTAS `create_query` reads → a REFERENCES-only redesign would regress recall → added AC-1b + a preservation task. R6 re-scoped (SKIP LOCKED = unrecovered-region inflation on generic DDL, not a reproducible phantom read). R1/R2 examples corrected (builtin `money` never leaks; use non-keyword custom names). FK-reliability-gap claim softened to verify-across-shapes (not reproducible on generic DDL). | readiness primer 2026-07-06 (generic-DDL parse probes). |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-06 | Track as a dedicated follow-up rather than expanding `1rvdp`. | `1rvdp` was close-ready; this is a distinct faithfulness surface (schema DDL, not loop recovery) that warrants its own review + adversarial lane. | Fold into `1rvdp` (rejected — scope expansion of a close-ready wave); fix inline (rejected — needs a mechanism spike + adversarial review). |
| 2026-07-06 | Committed fixtures use generic invented schemas; the proprietary real corpus is a local-only oracle. | The validation corpus is proprietary and must not leak into committed artifacts. | Commit the real corpus as a fixture (rejected — proprietary-data leak). |
| 2026-07-06 | **The redesign is NOT "REFERENCES-only" — it preserves LIKE + CTAS reads while suppressing only column-type names** (readiness primer strongest-challenge). | The blanket `object_reference` walk does triple duty (FK + `LIKE parent` + CTAS `create_query` reads); a naive REFERENCES-only scope would silently regress lineage recall. Discrimination signal verified: FK = `keyword_references`-preceded; LIKE = `LIKE`-identifier-preceded; CTAS = `create_query` subtree; column type = none of these → suppress. | REFERENCES-only suppression (rejected — drops LIKE + CTAS reads); suppress by a type-name stoplist (rejected — can't enumerate custom types). |
| 2026-07-06 | **R6 re-scoped to unrecovered-region inflation** (the generically-reproducible defect); the phantom-`read skip` variant is a LOCAL-oracle check only. | The primer could not reproduce `read skip` on generic DDL across five forms — SKIP LOCKED lands in an unrecovered region; the phantom appeared once on a complex proprietary FOR-loop-header SELECT (proprietary, kept local). Asserting "no read skip" against generic DDL would be a vacuous-truth test. | Keep AC-6 as "no read skip" (rejected — vacuous on generic DDL); commit the proprietary shape as a fixture (rejected — leak). |
| 2026-07-06 | R1/R2 examples corrected: custom-type fixtures must use NON-keyword names. | The primer found `money` parses as a grammar keyword (never leaks); only non-keyword custom type names (`usd`/`addr`/`status`) leak — a `money`-based fixture would be vacuous. | — |

## Risks

| Risk | Mitigation |
| --- | --- |
| Suppressing column-type reads also drops a genuine FK read (they occupy overlapping `object_reference` positions). | Discrimination signal VERIFIED at readiness (`keyword_references`-preceded = FK; else column-type); exact-set fixtures assert FK reads PRESENT + type reads ABSENT across ≥5 shapes; adversarial-faithfulness lane targets exactly this boundary. |
| **Recall regression: the type-suppression also scopes out `LIKE parent` and CTAS reads** (they share the blanket-walk path). | AC-1b pins both (`CREATE TABLE t (LIKE parent)` → `read parent`; CTAS → `read src`); the fix whitelists the `LIKE` identifier and routes `create_query` through `walk_reads`; adversarial lane targets the type-vs-FK-vs-LIKE-vs-CTAS boundary. |
| New `CREATE TYPE`/`DOMAIN` node kinds ripple into consumers (code_outline, clustering, node-kind assumptions). | Follow the `sql_kind` precedent (the clause-aware rewrite added `table`/`view`/`procedure`/… without a node-kind change — kind stays class/function); bump `GRAPH_BUILDER_VERSION`; check cluster projection unchanged. |
| Real delta is modest (like `1rs45`). | This one is a PRECISION fix (removing phantom edges), not a recall add — on a type-dense schema the phantom count is proportional to column count, so the precision gain is directly measurable (phantom-edge count before/after on the local real corpus). Report honestly. |
| **Stoplist over-reach (accepted trade-off):** a genuine table literally named `record`/`internal`/`void`/`skip`/`locked`/`nowait` — or, from the AC-8 dialect fold-in, `number`/`money`/`image`/`long`/`raw`/`geography`/`geometry` — is now suppressed (the global stoplist is not position-scoped). | Accepted, extending the base-list philosophy (`text`/`date`/`json` are already stoplisted despite being plausible table names): builtin-type usage dominates a table coincidentally named for a type, and on Oracle/MSSQL `number`/`varchar2` columns are pervasive. `share` is deliberately NOT stoplisted (`FOR SHARE` is caught by the position-aware benign-region check instead). Recorded by the delivery adversarial lane + the AC-8 fold-in; no fix. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
