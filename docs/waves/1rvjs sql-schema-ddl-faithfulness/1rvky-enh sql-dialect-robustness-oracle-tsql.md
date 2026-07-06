# SQL dialect robustness — Oracle & SQL Server / T-SQL

Change ID: `1rvky-enh sql-dialect-robustness-oracle-tsql`
Change Status: `landed`
Owner: Engineering
Status: planned
Last verified: 2026-07-06
Wave: TBD

## Rationale

The SQL graph extractor uses a single non-dialect-specific tree-sitter grammar (`derekstride/tree-sitter-sql`, a "general/permissive SQL grammar"), so it is Postgres/ANSI-biased and a range of common Oracle (PL/SQL) and SQL Server (T-SQL) constructs either fail to parse (fall into ERROR regions) or are mis-handled. A Guru dialect-coverage audit (2026-07-06, verified against the live grammar) mapped the gaps. The **builtin-type-name subset was already fixed** under `1rvjs`/`1rvdq` (AC-8 — Oracle/T-SQL type names stoplisted so they no longer leak phantom `reads`). This change collects the remaining CHEAP + MEDIUM tier that does not require a new grammar; the architectural procedural-body / grammar-swap questions are explicitly DEFERRED and recorded, not attempted here.

Goal: on Oracle/MSSQL schemas, stop dropping genuine table lineage (recall) and stop the residual phantom/loudness noise (precision), without chasing full dialect parity.

## Requirements

Each requirement cites the audited current behavior; all are `graph_indexer.py` SQL-region work.

1. **T-SQL `SELECT … INTO newtable FROM src` mints a table definition + a `write` to `newtable` — GATED to TOP-LEVEL scope only.** Today it parses with NO error but the target lands as `select > keyword_into > select_expression > term > field > identifier` (a skipped `field`), so the new table is INVISIBLE — no definition, no write edge. This is the T-SQL twin of CTAS (`CREATE TABLE … AS SELECT`, which IS handled). Signal: a `keyword_into` child directly under a `select` node; `newtable` = the first field-identifier in the following `select_expression`. **CRITICAL GUARD (readiness primer 2026-07-06):** PL/pgSQL `SELECT col INTO myvar FROM src;` (a variable assignment) produces a BYTE-IDENTICAL tree — the grammar cannot distinguish it. The only discriminator is STATEMENT SCOPE: `SELECT … INTO` at the top level = create-table (T-SQL and Postgres both); the assignment form exists ONLY inside a procedural body. So the write-mint MUST be gated to top-level statements (`owner is None` / the top-level statement loop), never inside a routine body — otherwise every procedural `SELECT … INTO var` mints a phantom table + write (a precision regression on exactly the Oracle/T-SQL corpus this targets). Requires a PL/pgSQL-body fixture proving no phantom.
2. **Oracle `CREATE GLOBAL TEMPORARY TABLE` is a real table definition, not a dropped temp.** Today `handle_create_table`'s `keyword_temporary` detection fires and the table is excluded as ephemeral — but an Oracle GTT is a PERMANENT schema object (only its DATA is session-scoped), unlike Postgres/T-SQL temp tables. Signal (readiness primer 2026-07-06): there is NO clean `keyword_global` — `GLOBAL` becomes a sibling `ERROR 'GLOBAL'` node alongside `keyword_temporary`; key on that. Distinguish `GLOBAL TEMPORARY` (Oracle, permanent) from `TEMP`/`TEMPORARY`/`#`/`@` (ephemeral) so the GTT mints a table node. **Update BOTH paths:** `handle_create_table`'s is_temp branch AND `_SQL_RECOVERY_CREATE_RE`'s temp group (it also folds GLOBAL into temp).
3. **T-SQL `GO` batch separator is recognized-benign.** Today a bare `GO` between statements parses as its own top-level ERROR and increments `unrecovered_regions` loudness (no data loss, but noise). Add it to `_sql_region_is_benign` / `_SQL_BENIGN_REGION_RE` (mirroring the `1rvdq` CREATE OPERATOR / locking-clause handling).
4. **Parenthesized custom/dialect type with precision (`number(10,2)` / `varchar2(50)` / `footype(n)`) no longer desyncs the parse and drops a trailing column's FK.** Discovered during the `1rvjs` AC-8 fold-in (pre-existing): the `(n)` becomes an ERROR and the columns AFTER it spill into a sibling top-level ERROR under `create_table`, where the FK target parses as a bare `identifier` (not `object_reference`), so `_emit_fk_and_like` never mints it. Recovery-tier fix: scan such a trailing ERROR for a `keyword_references`-preceded name (identifier OR object_reference) and recover the FK read. This is common in Oracle/MSSQL DDL (`number(p,s)`, `varchar2(n)`).
5. **T-SQL bracket-quoted identifiers (`[dbo].[Users]`) in ordinary statements do not corrupt the clause.** Today `[dbo].[Users]` does NOT natively parse (verified `has_error: True`); worse, it currently mints a MANGLED `read dbo].[Users` (readiness primer 2026-07-06), not just corruption. `_sql_normalize_object_name("[dbo].[Users]")` already returns `dbo.Users` correctly — the fix runs the raw bracketed span through normalize in the statement/recovery path so `dbo.Users` is recovered clean. (The `[]`-strip already runs in the embedded-SQL/recovery string paths; extend it to the ordinary-statement path.)
6. **T-SQL `MERGE` without `INTO` recovers its table names — via a RAW-TEXT REGEX SNIFF (mandatory, not optional).** Legal T-SQL `MERGE t USING s ON … WHEN MATCHED …` (no `INTO`) fails to parse entirely. **Readiness primer 2026-07-06: the parse tree DROPS `t`/`s`/`x`/`y` entirely — the inner ERROR preserves only keywords, so NODE-scan recovery is IMPOSSIBLE.** The ONLY viable path is a raw-text regex sniff in `_sql_recover_error_region` (the region_text is available there, and top-level MERGE ERRORs reach it) matching `MERGE\s+<target>\s+USING\s+<source>` → `write target` + `read source`. AC-6 mandates the regex tier.
7. **Oracle sequence references (`seq.NEXTVAL`) and `DUAL` are handled honestly.** `SELECT seq.NEXTVAL FROM dual` — the `seq` qualifier is dropped (inside a skipped `field`, silent recall miss) and `dual` mints a spurious `reads dual` (not stoplisted). Decide per-item: stoplist `dual` (it is never a real user table — a precision fix); optionally capture the sequence dependency (recall — lower priority, sequences are not tables).

## Scope

**In scope:** the seven requirements above, all in `.wavefoundry/framework/scripts/graph_indexer.py`'s SQL statement-unit + recovery tiers; generic-fixture tests per requirement; a `GRAPH_BUILDER_VERSION` bump (extraction-output change); the mandatory adversarial-faithfulness review lane (SQL detection surface). Committed fixtures use GENERIC invented schemas — no proprietary identifiers; the proprietary corpus is a local-only oracle.

**Out of scope (DEFERRED — the architectural tier, recorded for a later decision):**

- **Dialect-aware / per-dialect grammar.** The single permissive grammar is the root limitation; true Oracle-PL/SQL and T-SQL fidelity would need a different grammar (or per-dialect grammars) — a large investment, separate decision.
- **Oracle PL/SQL & T-SQL stored-procedure bodies.** `AS BEGIN … END` (T-SQL) and `AS/IS … BEGIN … END` (Oracle) bodies have no `$$` wrapper, so `_sql_routine_body_inner` returns None and the `1rs45` loop recovery never engages; the `CREATE … AS/IS` header does not parse as `create_procedure` (falls to ERROR, only partially recovered via dangling-block reattachment). Full native procedural-body extraction depends on the grammar question.
- **Oracle `CREATE PACKAGE` / `CREATE PACKAGE BODY`** — no recovery vocabulary; would need its own modeling.
- **Oracle `/` terminator** standalone behavior (unverified in the audit).
- Column-level lineage; cross-schema `search_path` resolution beyond today's.

## Acceptance Criteria

- [x] AC-1: top-level T-SQL `SELECT a, b INTO newtbl FROM src` mints a `newtbl` table def + a `write`; `src` reads. GATED to top-level scope so PL/pgSQL `SELECT … INTO var` (body) mints nothing (proven by fixture). A `#tmp`/`##g`/`@tv` temp target is suppressed (temp_names, no def/write — adversarial fix); dotted `dbo.newtbl` keeps its schema. (`test_sql_dialect_tsql_select_into_top_level_gated`.)
- [x] AC-2: Oracle `CREATE GLOBAL TEMPORARY TABLE gtt` mints a `gtt` table def; plain `CREATE TEMP/TEMPORARY TABLE` still excluded; a temp table literally NAMED `global` is not mis-flipped (adversarial fix — name-node excluded from the GLOBAL check). (`test_sql_dialect_oracle_global_temporary_table`.)
- [x] AC-3: `GO` no longer inflates `unrecovered_regions`; both tables extract. (`test_sql_dialect_go_and_dual_and_locking`.)
- [x] AC-4: `number(10,2)`/`varchar2(50)`/`footype(n)` parenthesized-type desync recovers the orphaned trailing FK read (text-regex over the top-level ERROR), incl. schema-qualified + multi-FK; no type-name phantom. (`test_sql_dialect_parenthesized_type_fk_recovery`.)
- [~] AC-5: the bracket-quoted `[dbo].[Users]` read resolves to a CLEAN graph edge `external::dbo.Users` (via the landed emit-normalize) — lineage preserved, not corrupted. `[~]`: the unit's names-as-written output stays quote-mangled by the frozen-unit design and the bracket ERROR adds a minor unrecovered-loudness overcount; the EDGE (what binds) is clean, so the AC is satisfied at the graph level. A unit-level normalize is a possible small future follow-up for the embedded-SQL bracket-bind path. (`test_sql_dialect_tsql_bracket_quote_edge_is_clean`.)
- [x] AC-6: T-SQL `MERGE t USING s …` (no `INTO`) recovers `write t` + `read s` via a raw-text regex sniff; MERGE-with-INTO unchanged (native). (`test_sql_dialect_tsql_merge_without_into_recovery`.)
- [x] AC-7: `SELECT … FROM dual` mints no `read dual` (stoplisted). Sequence-dependency capture NOT done (optional; sequences are not tables) — the `seq` qualifier stays a documented recall miss. (`test_sql_dialect_go_and_dual_and_locking`.)
- [~] AC-8: `GRAPH_BUILDER_VERSION` bumped 42→43; mandatory adversarial-faithfulness lane run (found + fixed 2 wrong-edges: SELECT-INTO temp sigil, GLOBAL name collision) + re-verified; code/perf lane; full framework suite green; `wave_validate` clean; live upgrade-heal. Local proprietary Oracle/MSSQL corpus re-check is `[~]` — no such corpus was supplied (the earlier corpus was Postgres + deleted); generic fixtures stand.

## Tasks

- [x] Characterize each dialect construct's exact parse shape with generic-DDL probes (readiness primer + implementation probes).
- [x] T-SQL `SELECT … INTO` write/definition handler (top-level-gated; temp-sigil-suppressed).
- [x] Oracle `GLOBAL TEMPORARY` vs ephemeral-temp discrimination in `handle_create_table` (name-node-excluded).
- [x] `GO` benign-region pattern.
- [x] Parenthesized-type trailing-ERROR FK recovery (`_SQL_RECOVERY_REFERENCES_RE` in the recovery tier).
- [~] Bracket-quoted identifier handling — the graph EDGE is already clean via the landed emit-normalize; unit-level normalize deferred (frozen-unit design).
- [x] `MERGE`-without-`INTO` recovery (`_SQL_RECOVERY_MERGE_RE` raw-text sniff).
- [x] `dual` stoplist (sequence capture deliberately not done — optional).
- [x] Generic-fixture tests (6 new methods + adversarial regressions); version bump 42→43; adversarial + code/perf lanes; local corpus re-check `[~]` (no Oracle/MSSQL corpus supplied).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| recall-fixes | implementer | — | R1 SELECT INTO, R2 Oracle GTT, R4 parenthesized-type FK, R6 MERGE — the lineage-recovery half. |
| precision-loudness | implementer | — | R3 GO, R5 bracket-quote, R7 dual — the noise-reduction half; shares the recovery/benign-region code. |
| validation | implementer | recall-fixes | Generic fixtures + adversarial lane + version bump. |

## Serialization Points

- Shares `graph_indexer.py`'s SQL statement unit with any other SQL-region work — coordinate merge order + the single `GRAPH_BUILDER_VERSION` bump.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — the SQL statement-unit / recovery section gains the dialect-robustness handlers. No module-boundary change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | important | T-SQL SELECT INTO is a common table-creation form; its invisibility is a real recall hole. |
| AC-2 | important | Oracle GTTs silently dropped from lineage. |
| AC-3 | nice-to-have | GO is loudness-only (no data loss). |
| AC-4 | required | Parenthesized types (`number(p,s)`/`varchar2(n)`) are pervasive in Oracle/MSSQL DDL; dropping trailing FKs is a broad recall hole. |
| AC-5 | important | Bracket quoting is ubiquitous in T-SQL; clause corruption is broad. |
| AC-6 | important | T-SQL MERGE-without-INTO loses ALL its table names. |
| AC-7 | nice-to-have | `dual` phantom + sequence miss — narrow. |
| AC-8 | required | Standing gates. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-06 | Split from the `1rvjs`/`1rvdq` close. A Guru dialect-coverage audit (verified against the live tree-sitter-sql grammar) mapped Oracle/T-SQL gaps; the builtin-type-name subset was folded into `1rvjs` (AC-8), the rest collected here. Architectural procedural-body / grammar-swap tier explicitly deferred. Proprietary corpus kept local; generic examples only. | Guru dialect audit 2026-07-06; `1rvjs` close readout. |
| 2026-07-06 | **Rolled INTO wave `1rvjs` (operator direction) + readiness primer — all 7 mechanisms VERIFIED achievable, 3 guards folded in.** Primer confirmed each parse-shape signal. Strongest challenge: R1 SELECT-INTO is byte-identical to PL/pgSQL `SELECT … INTO var` → gated to top-level scope only. R6 MERGE-without-INTO drops all names from the tree → MUST be a raw-text regex sniff (node recovery impossible). R2/R5 need both parsed + recovery paths updated; R5 currently mints a mangled `dbo].[Users`. | readiness primer 2026-07-06 (generic-DDL parse probes). |
| 2026-07-06 | **Implemented all 7 requirements + delivery review.** R1 SELECT-INTO (top-level-gated, temp-sigil-suppressed); R2 Oracle GTT (name-node-excluded); R3 GO + R7 dual; R4 parenthesized-type FK recovery + R6 MERGE-without-INTO (both `_sql_recover_error_region` text regexes); R5 verified clean at the graph-edge level. `GRAPH_BUILDER_VERSION` 42→43. 6 new test methods + adversarial regressions + 2 existing GO-expectation updates. Delivery review: adversarial-faithfulness (mandatory) found + fixed 2 wrong-edges (SELECT-INTO temp sigil, GLOBAL name collision), re-verified PASS; code/perf PASS WITH NOTES (1 fix-now: bracket-qualified SELECT-INTO schema; regexes linear/no-backtrack). Full framework suite green. | `test_graph_indexer` 520 green; adversarial + code/perf delivery lanes 2026-07-06. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-06 | Do the cheap+medium dialect-robustness tier now; DEFER the grammar swap + procedural-body extraction. | The single permissive grammar is the root limitation; a dialect-aware grammar is a large separate investment, whereas the recall/precision fixes here need no grammar change. | Attempt full Oracle/T-SQL parity (rejected — grammar-swap rabbit hole); do nothing (rejected — real recall holes on Oracle/MSSQL schemas). |
| 2026-07-06 | The builtin-type-name subset was folded into `1rvjs` (AC-8), not this change. | It is the same stoplist + the same precision concern as `1rvdq`, small and low-risk, and directly gates `1rvdq`'s precision carrying to non-Postgres schemas. | Put it here (rejected — operator directed the fold-in so `1rvdq` is dialect-complete for the phantom class). |

## Risks

| Risk | Mitigation |
| --- | --- |
| **R1 SELECT-INTO false-positive (readiness primer strongest challenge):** PL/pgSQL `SELECT col INTO myvar` is a byte-identical tree to T-SQL `SELECT … INTO newtbl`; minting a table+write for the assignment form is a precision regression. | Gate the write-mint to TOP-LEVEL statement scope ONLY (`owner is None` / top-level statement loop) — the assignment form exists only inside routine bodies; a PL/pgSQL-body fixture proves no phantom. |
| Recovery-tier handling of the parenthesized-type trailing ERROR (R4) over-recovers a non-FK identifier as a read. | Gate strictly on `keyword_references`-preceded names inside the ERROR (the same discipline as `_emit_fk_and_like`); adversarial-faithfulness lane targets it; generic exact-set fixtures. |
| **R6 MERGE regex sniff over-matches** (raw-text regex on an ERROR region). | Anchor the pattern tightly (`MERGE\s+<name>\s+USING\s+<name>` with strict name shapes); it fires ONLY on an already-unrecovered ERROR region (never on a natively-parsed MERGE-INTO); adversarial lane targets it. |
| Bracket-quote handling (R5) mis-strips a legitimately-bracketed literal. | Strip only in object-reference positions (reuse `_sql_normalize_object_name`'s `[]` table); do not touch string literals (already masked). |
| Oracle GTT discrimination (R2) mis-classifies a real temp. | Key strictly on the `GLOBAL TEMPORARY` token pair vs bare `TEMP`/`TEMPORARY`/sigil; fixtures for each. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
