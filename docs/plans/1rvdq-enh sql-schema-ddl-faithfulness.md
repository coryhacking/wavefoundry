# SQL schema-DDL faithfulness — suppress custom-type phantoms, model CREATE TYPE/DOMAIN/OPERATOR, fix SKIP LOCKED

Change ID: `1rvdq-enh sql-schema-ddl-faithfulness`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-06
Wave: TBD

## Rationale

Validating the SQL graph extractor against a real, type-dense production Postgres schema (an operator-supplied corpus: dozens of tables, ~10 custom domains, ~9 composite types, several enums, and a family of custom operators) surfaced a class of phantom `reads` edges and unmodeled definitions that the current statement unit produces on schema DDL. On a schema this type-heavy, every column whose type is a custom domain/composite/enum mints a phantom `read <typename>` edge, so the noise is proportional to the schema's type density — not a corner case. These are pre-existing behaviors in the SQL statement-unit territory (the clause-aware extraction rewrite + the in-body statement dispatch), NOT the loop-recovery tier delivered in `1rs45`; they were recorded during the `1rvdp` real-corpus validation and split here so they are tracked rather than dangling.

The core faithfulness principle: a graph `reads`/`writes` edge is DATA LINEAGE (a routine/table reads data FROM a table). A column's *type* is a type dependency, not a data read; a function call in a column DEFAULT or a `GENERATED` expression is not a table read; a pseudo-type parameter (`anyelement`) is not a table. Minting reads for these inflates the graph with edges that misrepresent data flow.

**Proprietary-data constraint:** the operator's real schema/routine corpus is proprietary and must NOT be committed. The examples in this doc use generic invented identifiers; the committed test fixtures must likewise use generic invented schemas. The real corpus is used only as a local (uncommitted) validation oracle.

## Requirements

1. **Custom-type column names no longer mint phantom `reads`.** In `handle_create_table` (and the analogous column-type positions in `create_*` handlers), a column's TYPE name — including custom domains, composite types, and enums — must NOT be emitted as a `reads` reference. Today `handle_create_table` treats every `object_reference` in the table subtree as an FK-style read; builtin types (`int`, `text`, `jsonb`, `uuid`, `timestamptz`) parse as keyword nodes (already clean) but custom-type names parse as identifiers and leak. The GENUINE FK targets (`REFERENCES parent_tbl (id)`) must still be captured — and captured RELIABLY: the census found FK capture inconsistent (one table's FK read was dropped while a type-name phantom on the same table surfaced).
2. **`GENERATED ALWAYS AS (…)` and column `DEFAULT (…)` expressions no longer mint phantom reads** for the function/keyword tokens inside them (e.g. `extract`/`epoch` from a generated duration column; a schema-qualified `schema.gen_id()` default). A genuine table read inside such an expression (rare) may be preserved or dropped — decide during design — but the invocation/keyword noise must go.
3. **Pseudo-type parameters (`anyelement`, `anyarray`, `anynonarray`, `anyenum`, `record`, `trigger`, `void`, …) never mint a `reads`** from a routine's signature.
4. **`CREATE TYPE` (composite + enum) and `CREATE DOMAIN` are modeled as definition nodes** (a new `sql_kind`, e.g. `type`/`domain`), so a column typed by one resolves to a real definition node instead of dangling `external::` — and so R1's suppression does not merely drop the type but connects columns to their type where useful. Scope the edge model conservatively (a column→type dependency edge is optional; decide during design whether it earns its place or whether definition nodes alone suffice).
5. **`CREATE OPERATOR` no longer falls into an unrecovered ERROR region** with no signal — at minimum recognize it (recover its `procedure = <fn>` function reference, or explicitly skip it cleanly) rather than counting it as `unrecovered_regions` noise. The tree-sitter-sql grammar does not parse `CREATE OPERATOR`, so this is a recovery-tier or sniff-gate question.
6. **`FOR UPDATE SKIP LOCKED` no longer mints a phantom `read skip`** (folded in from the `1rvdp` real-corpus finding). The row-locking clause `FOR UPDATE SKIP LOCKED` / `FOR UPDATE NOWAIT` / `FOR SHARE` parses such that `skip` (and possibly `locked`/`nowait`/`share`) is read as a table. This is a common job-queue idiom (a `SELECT … FOR UPDATE SKIP LOCKED` inside a claim-next-work routine), so the phantom recurs at scale on real corpora.

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

- [ ] AC-1: An exact-edge-set test over a generic schema fixture proves NO `reads` edge is minted for a custom column type (a domain, a composite, an enum used as column/return types), while the genuine FK reads (a child table → its two parent tables) ARE all present and correctly directed — including the FK-capture reliability gap the census exposed.
- [ ] AC-2: A `GENERATED ALWAYS AS (extract(epoch from (col_b - col_a)) …)` column and a `DEFAULT schema.gen_id()` column mint no `reads` for `extract`/`epoch`/the default function.
- [ ] AC-3: A routine with an `anyelement` (and other pseudo-type) parameter mints no `reads` for the pseudo-type.
- [ ] AC-4: `CREATE TYPE … AS (…)`, `CREATE TYPE … AS ENUM (…)`, and `CREATE DOMAIN … AS …` each mint a definition node (with the new `sql_kind`); a column typed by one resolves to that node, not `external::`.
- [ ] AC-5: `CREATE OPERATOR … (procedure = <fn>, …)` is recognized (its `procedure` function reference recovered, or a clean skip) — it does not inflate `unrecovered_regions`.
- [ ] AC-6: `SELECT … FOR UPDATE SKIP LOCKED` (in a FOR-loop header and standalone) mints no `read skip`/`read locked`; the real table read is preserved.
- [ ] AC-7: Standing gates — `GRAPH_BUILDER_VERSION` bump; the mandatory adversarial-faithfulness review lane run (SQL detection surface); full framework suite green; `wave_validate` clean; live upgrade-heal. Real-corpus precision re-verified LOCALLY against the operator's proprietary schema+routine corpus (phantom count drops; no genuine edge lost) — no proprietary artifact committed.

## Tasks

- [ ] Characterize the exact parse shapes: dump the AST for a custom-type column, an FK column, a `GENERATED`/`DEFAULT` column, an `anyelement` param, `CREATE TYPE`/`DOMAIN`/`OPERATOR`, and `FOR UPDATE SKIP LOCKED` — the discrimination signal for each (a spike, mirroring the `1rs45` mechanism spike). Use generic invented DDL for any artifacts that get recorded.
- [ ] `handle_create_table`: distinguish column-type object_references from FK-target object_references (likely: only object_references under a `REFERENCES` clause are FK reads; column-position type names are skipped) and fix the FK-capture reliability gap.
- [ ] Suppress `DEFAULT`/`GENERATED` expression invocation/keyword noise (reuse the `invocation`/`function_declaration` skip family).
- [ ] Pseudo-type stoplist.
- [ ] `CREATE TYPE`/`CREATE DOMAIN` definition-node handlers + new `sql_kind`.
- [ ] `CREATE OPERATOR` recognition (sniff or recovery).
- [ ] `FOR UPDATE SKIP LOCKED` phantom suppression.
- [ ] Generic-schema faithfulness fixtures; version bump + upgrade-heal at integration; adversarial-faithfulness lane; local proprietary-corpus precision re-check (uncommitted).

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

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The custom-type phantom is the dominant noise class on a type-dense schema. |
| AC-2 | required | Default/generated expression noise. |
| AC-3 | important | Pseudo-type params — narrower but real. |
| AC-4 | important | Type/domain modeling closes the dangling `external::` and enables column→type resolution. |
| AC-5 | nice-to-have | CREATE OPERATOR recognition — low frequency, mostly a loudness cleanup. |
| AC-6 | required | SKIP LOCKED recurs at scale in job-queue idioms. |
| AC-7 | required | Standing version/adversarial/suite gates. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-06 | Split out of the `1rvdp` real-corpus validation. A production PL/pgSQL routine corpus surfaced the `SKIP LOCKED` phantom; a production schema DDL surfaced the custom-type-column / default-generated / pseudo-type phantoms and the unmodeled `CREATE TYPE`/`DOMAIN`/`OPERATOR` + inconsistent FK capture. All pre-existing (statement-unit territory), none introduced by `1rs45`. Proprietary corpus kept local (uncommitted); this doc uses generic examples. | `1rvdp` close readout; local schema/routine census (uncommitted). |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-06 | Track as a dedicated follow-up rather than expanding `1rvdp`. | `1rvdp` was close-ready; this is a distinct faithfulness surface (schema DDL, not loop recovery) that warrants its own review + adversarial lane. | Fold into `1rvdp` (rejected — scope expansion of a close-ready wave); fix inline (rejected — needs a mechanism spike + adversarial review). |
| 2026-07-06 | Committed fixtures use generic invented schemas; the proprietary real corpus is a local-only oracle. | The validation corpus is proprietary and must not leak into committed artifacts. | Commit the real corpus as a fixture (rejected — proprietary-data leak). |

## Risks

| Risk | Mitigation |
| --- | --- |
| Suppressing column-type reads also drops a genuine FK read (they occupy overlapping `object_reference` positions). | The mechanism spike must nail the discrimination signal (REFERENCES-clause containment vs column-type position) before implementation; exact-set fixtures assert FK reads PRESENT + type reads ABSENT on a generic schema; adversarial-faithfulness lane targets exactly this boundary. |
| New `CREATE TYPE`/`DOMAIN` node kinds ripple into consumers (code_outline, clustering, node-kind assumptions). | Follow the `sql_kind` precedent (the clause-aware rewrite added `table`/`view`/`procedure`/… without a node-kind change — kind stays class/function); bump `GRAPH_BUILDER_VERSION`; check cluster projection unchanged. |
| Real delta is modest (like `1rs45`). | This one is a PRECISION fix (removing phantom edges), not a recall add — on a type-dense schema the phantom count is proportional to column count, so the precision gain is directly measurable (phantom-edge count before/after on the local real corpus). Report honestly. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
