# SQL extraction: DDL recovery tier for statements the grammar cannot parse (procedures, functions, dialect forms)

Change ID: `1p9qe-enh sql-ddl-error-recovery`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-05
Wave: TBD

## Rationale

Live-verified (guru investigation, 2026-07-03): the installed `tree_sitter_sql` grammar produces an **ERROR node** for `CREATE PROCEDURE get_active_users() BEGIN ... END;` — only stray keyword tokens parse, so no definition node and no `defines` edge is ever produced for procedures. The `kind="function"` handling for `procedure`-typed nodes (`_ts_kind_for_definition` SQL branch, `graph_indexer.py:2386-2387`) is unreachable given the grammar's actual output. SQL is dialect-fragmented (T-SQL, PL/pgSQL, MySQL, Oracle) and no single tree-sitter grammar parses them all — procedures, triggers, and dialect-specific DDL will keep hitting ERROR nodes whatever grammar version ships.

The framework already has the honest-degradation answer **designed**: the oversized-file line-scan tier (`1p9q6`, wave `1p9q8 graph-index-accuracy` — readied but **not yet landed** as of 2026-07-04; the only oversized-file behavior in tree is the `1p5c4` parse skip, no line-scan code exists) recovers imports/definitions where full parsing is unavailable, loudly labeled. The same pattern applies here at statement granularity: when a top-level statement region parses to ERROR, a bounded line-anchored scan recovers `CREATE {PROCEDURE|FUNCTION|TRIGGER|TABLE|VIEW|INDEX} <name>` definitions (and, best-effort, table references inside the unparsed body via the `1p9qd` statement unit applied to recognizable sub-statements), labeled as recovery-extracted. Interesting consequence already proven in the live run: references inside a failed procedure body were still emitted from file scope — recovery should *attach* them to the recovered procedure node instead of leaving them dangling at module level.

## Requirements

1. **ERROR-region detection.** SQL-mode extraction identifies top-level ERROR regions in the parse tree and routes their source text to a recovery scan instead of dropping them silently.
2. **Definition recovery.** A line-anchored, case-insensitive scan over the ERROR region recovers `CREATE [OR REPLACE] {PROCEDURE|FUNCTION|TRIGGER|TABLE|VIEW|INDEX}` (and `ALTER TABLE` as a reference, not a definition) names — emitting definition nodes with correct kinds (per `1p9qd`'s kind representation) and an `extraction: "sql_recovery"` marker, mirroring `1p9q6`'s labeling convention.
3. **Reference recovery and re-attachment.** Statement fragments inside a recovered procedure/function body that the grammar CAN parse (the live run showed body `SELECT`s parse as bare blocks) route through the `1p9qd` statement unit, and their reference edges attach to the recovered procedure node — not the file module node — so "which procedures touch table X" is answerable.
4. **Bounded and loud.** The recovery scan is single-pass with the same line-length/byte-ceiling discipline as `1p9q6`; the build log counts recovered definitions and unrecoverable regions per file; nothing is silently dropped.
5. **Faithfulness.** Recovery emits only on unambiguous line-anchored matches; commented-out DDL (`-- CREATE TABLE ...`, `/* ... */`) must not emit (comment-stripping precedes the scan); string literals containing DDL text inside parsed statements are never scanned (only ERROR regions are).
6. **Version bump + tests + calibration.** `GRAPH_BUILDER_VERSION` bumped; fixtures per dialect-ish form (MySQL-style, T-SQL-style, PL/pgSQL-style `CREATE FUNCTION ... $$ ... $$`); adversarial comment/string fixtures; recovered-vs-parsed counts recorded on a realistic migration fixture.

## Scope

**Problem statement:** Procedures, functions, triggers, and dialect DDL the grammar cannot parse vanish from the graph entirely (ERROR nodes discarded), and references inside failed bodies dangle at file scope — an invisible hole in exactly the database logic enterprises need traced.

**In scope:**

- ERROR-region routing; definition recovery scan with kinds + `sql_recovery` marker; body-reference re-attachment via the `1p9qd` unit; bounds and logging; comment stripping.
- Dialect-form and adversarial fixtures; calibration counts; version bump.

**Out of scope:**

- Swapping or forking the tree-sitter SQL grammar (dependency churn for partial dialect wins; recovery makes the choice less critical).
- Parsing procedure body control flow (variables, cursors, dynamic SQL inside procedures — the body reference recovery is best-effort statement-level only).
- Dialect-complete DDL coverage (the recovery vocabulary is a reviewable constant, extensible on field evidence).

## Acceptance Criteria

- [x] AC-1: The live-repro fixture (`CREATE PROCEDURE ... BEGIN SELECT * FROM users; END;`) produces a procedure definition node (correct kind, `sql_recovery` marker) with a `defines` edge, and its body's `users` reference attaches to the procedure node, not the module node. Unit-tested. — `test_sql_recovery_procedure_definition_and_body_reattachment` (exact edge set; `kind=function`, `sql_kind=procedure`, `extraction="sql_recovery"`, cross-file bind at RECEIVER_RESOLVED).
- [x] AC-2: Dialect-form fixtures (T-SQL `CREATE PROCEDURE ... AS BEGIN`, PL/pgSQL `CREATE FUNCTION ... $$...$$`, MySQL delimiter style) each recover their definition nodes; forms outside the vocabulary degrade to a logged unrecovered count, never silence. Unit-tested per form. — `test_sql_recovery_dialect_forms_with_loud_degradation` (note: the PL/pgSQL dollar-quoted form parses NATIVELY on the trusted path — pinned with `extraction: None` and zero recovery counts; T-SQL `GO` and `DELIMITER` fragments pin the counted-unrecovered degradation). Trigger form also covered: ON-table + re-parsed body INSERT both attach to the recovered trigger.
- [x] AC-3: Commented-out DDL (line and block comments) and DDL text inside string literals of parsed statements emit nothing. Adversarial unit tests. — `test_sql_recovery_commented_and_string_ddl_never_mints` (ghosts in line/block comments outside AND inside ERROR regions, in an `EXECUTE '...'` string inside an ERROR region, and in a string literal of a parsed INSERT) + `test_sql_recovery_masking_and_name_validation_units` (mask preserves offsets/lines; real DDL after a same-line `/* */` still recovers — the risk-table case both ways).
- [x] AC-4: Parsed statements are untouched — files with zero ERROR regions produce byte-identical extraction before/after (regression pin), and recovery never runs on successfully parsed regions. Unit-tested. — `test_sql_recovery_parsed_extraction_untouched` (exact pre-1p9qe edge-set pin; no `extraction`/recovery properties anywhere) + all 9 pre-existing 1p9qd exact-set tests green unmodified; recovery is structurally unreachable for parsed statements (only `ERROR` nodes route to it).
- [x] AC-5: Build log reports per-file recovered/unrecovered counts; bounds respected on a pathological fixture. Unit-tested on the log shape. — `test_sql_recovery_bounds_and_log_shape` (module-node counts `sql_error_regions`/`sql_recovered_definitions`/`sql_unrecovered_regions`; exact `_sql_recovery_log_line` string; byte-ceiling region degrades to counted-unrecovered; over-length line skipped).
- [x] AC-6: `GRAPH_BUILDER_VERSION` bumped; migration-fixture recovered-vs-parsed counts in the Progress Log; `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`. — Satisfied at wave integration (2026-07-05): the coordinated 37→38 bump landed with a changelog naming 1p9qe's contribution (ERROR-region recovery tier, `sql_recovery` provenance, `sql_recovered_definitions`/`sql_unrecovered_regions` count properties, body-reference re-attachment); recovered-vs-parsed counts were already in the Progress Log; full suite green post-bump, `wave_validate` clean, no `__pycache__` (integration gates, wave.md Review Checkpoints).

## Tasks

- [x] ERROR-region identification + routing in SQL-mode extraction. — ordered document-order top-level scan in `_sql_analyze_program` (`scan_top` + `handle_error_region`); `error_regions` count semantics unchanged (frozen 1p9qd contract).
- [x] Recovery scan: comment stripping, line-anchored CREATE-form vocabulary, kind mapping, `sql_recovery` marker, bounds, logging. — `_sql_recovery_mask_noncode` (comments + string/dollar-quote bodies, offset-preserving), `_sql_recover_error_region`, `_SQL_RECOVERY_*` constants, `_sql_recovery_log_line` + verbose per-file line in `update_graph_index`.
- [x] Body-reference re-attachment through the `1p9qd` statement unit (parseable fragments only). — two mechanisms: dangling top-level `block` following a single-routine region attributes its parsed statements to the routine; region text after a single recovered routine header re-parses one level (`recover=False`) with owner re-attribution (the trigger form).
- [x] Fixtures/tests per AC-1..AC-5; calibration counts on the migration fixture. — 5 new tests (see ACs); calibration in Progress Log.
- [x] Bump `GRAPH_BUILDER_VERSION`; run `run_tests.py` + `wave_validate`; clean `__pycache__`. — Done at wave integration 2026-07-05: coordinated 37→38 bump with 1p9qe named in the changelog; suite/validate/pycache gates re-verified post-bump.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-error-routing | implementer | — | ERROR-region detection + routing; comment stripping. |
| ws2-recovery-scan | implementer | ws1-error-routing | CREATE-form vocabulary scan + kinds + marker + bounds + logging. |
| ws3-body-reattachment | implementer | ws2-recovery-scan | Parseable-fragment references attached to recovered nodes (consumes the `1p9qd` unit). |
| ws4-tests-calibration | implementer | ws3-body-reattachment | Dialect/adversarial/regression fixtures; counts. |


## Serialization Points

- Depends on `1p9qd`'s statement-analysis unit (ws3 consumes it) — land `1p9qd` ws1 first; coordinate the unit's ERROR-fragment behavior as a shared contract.
- After `1p9qc` (clean candidate space).
- Cross-wave: `1p9q6` (wave `1p9q8`, status `planned` as of 2026-07-04) defines the degradation labeling/bounds convention this change mirrors — it is a readied-change contract, **not in-tree code available for reuse**. Whichever change lands first establishes the convention family (marker property shape, per-file count logging, byte/line ceilings); coordinate so both stay one family, and do not block on `1p9q8` landing.
- Single wave-level `GRAPH_BUILDER_VERSION` bump.

## Affected Architecture Docs

Wave-level capability-notes audit: SQL extraction documentation gains the recovery tier and its `sql_recovery` labeling (same honest-degradation family as the oversized-file tier). No boundary/flow impact beyond the `1p9qd` unit contract already documented there.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The live-verified hole (procedures vanish, references dangle) is the change's reason to exist. |
| AC-2 | required | Dialect variance is the actual field condition; per-form recovery with loud degradation is the contract. |
| AC-3 | required | Recovering commented-out DDL would invent schema objects — worse than the hole. |
| AC-4 | required | Recovery must be strictly additive; parsed extraction is the trusted path. |
| AC-5 | important | Loudness is the honesty guarantee; log-shape drift is low-stakes. |
| AC-6 | required | Standing gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the Java/SQL accuracy investigation. Live parse dump confirmed `CREATE PROCEDURE` → ERROR node (no definition emitted; `kind="function"` procedure branch unreachable); body `SELECT` parsed as bare block with its reference emitted at file scope (the dangling-reference behavior AC-1 fixes). Degradation-pattern precedent: `1p9q6` oversized-file line scan. | Guru investigation 2026-07-03 (live runs + raw tree dump via `~/.wavefoundry/venv`). |
| 2026-07-04 | Reality-check freshness lane (wave open): procedure-branch anchor refreshed after `1p9qh` line drift (`:2386-2387`; mechanism unchanged, still unreachable for ERROR-parsed procedures). Corrected the `1p9q6` precedent status: wave `1p9q8` is still `planned`, so the line-scan tier is a designed contract, not shipped code — cross-wave coordination note added to Serialization Points. Coordinated wave version bump is now 37→38. | Reality-check 2026-07-04. |
| 2026-07-04 | **Implemented.** (1) **Pre-fix live reproduction** (venv tree dumps, all dialect forms): MySQL/T-SQL/delimiter procedure headers → top-level ERROR nodes, zero definitions, body `SELECT` in a dangling `block` emitting at MODULE scope; trigger form swallows its whole body into one ERROR region (its `INSERT INTO audit_log` vanished entirely); `OR REPLACE` also ERRORs; PL/pgSQL `$$` form parses natively. (2) **Recovery tier** (`graph_indexer.py`): document-order top-level scan routes ERROR regions to `_sql_recover_error_region` — offset-preserving comment/string/dollar-quote masking (`_sql_recovery_mask_noncode`), line-anchored `CREATE [OR REPLACE] [TEMP] {PROCEDURE\|FUNCTION\|TRIGGER\|TABLE\|VIEW\|MATERIALIZED VIEW\|[UNIQUE] INDEX}` + `ALTER TABLE` vocabulary (reviewable `_SQL_RECOVERY_*` constants), strict name validation (bracket/backtick quoting stripped, garbage refused, `#`/`@` sigils → temp exclusion). Recovered definitions carry `extraction: "sql_recovery"` (node property + unit key); INDEX recovers the `index_on` table READ, never an index definition (parity with the parsed path — recovered files can never claim more than parsed ones). (3) **Re-attachment**: a dangling `block` after a single-routine region attributes its parsed statements to the routine; region body text after the recovered header re-parses one level through the unit (`recover=False`) with owner re-attribution — trigger body INSERT and ON-table both attach. Multi-routine regions refuse attribution (module scope; risk-table rule). Parsed extraction wins name collisions; recovery is strictly additive. (4) **Loudness**: module-node `sql_recovered_definitions`/`sql_unrecovered_regions` beside the unchanged `sql_error_regions`; verbose per-file `_sql_recovery_log_line` in `update_graph_index` (worker-safe — counts ride node properties). Unit contract extended compatibly: `recovery: {recovered_definitions, unrecovered_regions}` + uniform `extraction` key on defs/refs. Bounds: 128 KiB region ceiling, 4,096-char line ceiling — over-bound degrades to counted-unrecovered. (5) **Calibration** (6-file migration fixture, verbose build): parsed 4 definitions (3 tables + 1 view), recovered 4 (3 procedures + 1 trigger incl. schema-qualified `dbo.rebuild_stats`); per-file counts V4: 2/2/0, V5: 1/1/0, V6: 2/1/1 (`GO` counted unrecovered); ALL 6 routine-body references bound cross-file at RECEIVER_RESOLVED with correct read/write direction and routine-node sources; zero table externals. **Flip evidence both directions**: pre-fix probes on the same fixtures show zero routine definitions + module-scope dangling refs (and the trigger's body reference lost entirely); post-fix exact-set tests forbid every pre-fix symptom; AC-4 pin + all 9 pre-existing 1p9qd exact-set tests green unmodified. Full suite 4,547/43 green (baseline 4,541 + 5 tests this change + 1 from the parallel `1p9qf` lane); `wave_validate` clean; no `__pycache__`. **Finding (pre-existing, out of scope)**: the 1p9qd parsed path collects function invocations as reads (`WHERE created < NOW()` → `reads external::NOW`; grammar shape `invocation > object_reference`) — pre-dates this change (reproduced on parsed-only text with zero ERROR regions), surfaced by the calibration fixture; needs a coordinated decision on skipping `invocation` subtrees vs. keeping table-valued-function refs. **RESOLVED at wave integration (2026-07-05):** measured on the Fineract census corpus (42/953 = 4.4% of unit references were scalar-invocation noise), then fixed in the shared statement unit — the walk skips only the invocation's function-name `object_reference` while preserving argument-subquery table reads; relation-position (table-valued-function) handling unchanged. Recovery's body re-parse consumes the same unit, so re-attributed recovered-body references are noise-free for free; all 5 `test_sql_recovery_*` tests pass unmodified. Full decision + alternatives in `1p9qd`'s Decision Log (2026-07-05 entry). | `graph_indexer.py` (SQL unit + recovery tier + verbose log), `test_graph_indexer.py` (5 new `test_sql_recovery_*`); venv probe runs + calibration 2026-07-04. |
| 2026-07-05 | **Native path now consistent with this change's recovery tier for in-body statements.** This change's recovery tier already re-enters `analyze_statement` for recovered routine bodies (owner re-attribution, correct read/write direction). The delivery-review red-team confirmed the TRUSTED native `$$`/`$tag$` parse path did NOT do the same: it flattened in-body statements through the generic read walk, inverting the direction of in-body `INSERT`/`UPDATE`/`DELETE`/`MERGE` (writes emitted as reads) and minting phantom reads for nested `CREATE TABLE`/`CREATE TEMP TABLE`. Fixed in `graph_indexer.py` (`walk_reads` now dispatches nested `statement` nodes through `analyze_statement`; `handle_create_routine` drops body-minted definitions — same "routine bodies never define at module scope" stance this recovery tier already takes for its body re-parse). The recovery case is NOT double-processed: recovered bodies re-parse through a separate `_sql_analyze_program` call, while the native fix only changes how the already-parsed native subtree is walked. Full decision, AST-shape finding, and flip evidence in `1p9qd`'s Decision Log (2026-07-05 in-body-routine entry); pinned by `test_sql_in_body_routine_statements_get_correct_direction`. | `graph_indexer.py` (walk_reads + handle_create_routine), `test_graph_indexer.py` (1 new in-body-routine exact-set test); primer probe flip 2026-07-05. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Statement-granular ERROR-region recovery scan, grammar unchanged (approach A). | Dialect fragmentation means ERROR nodes are permanent weather, not a bug to fix once; recovery at the ERROR boundary keeps the parsed path pure while making the unparsed path visible and bounded; reuses the proven `1p9q6` degradation pattern and the `1p9qd` unit. | (B) Swap/upgrade the tree-sitter SQL grammar — weakness: no grammar covers all dialects; dependency churn with Windows-install risk for a partial fix; recovery is still needed after. (C) Regex-scan whole SQL files unconditionally — weakness: double-extraction of parsed statements and string/comment false positives; scanning only ERROR regions eliminates both. |
| 2026-07-03 | Body references attach to the recovered procedure node. | The live run proved they otherwise dangle at module scope, which answers "does this file touch X" but not "does this procedure touch X" — the question impact analysis actually asks. | Leave at module scope — rejected: loses the attribution for free once the procedure node exists. |
| 2026-07-04 | `CREATE INDEX` in the recovery vocabulary emits the `index_on` table READ, never an index definition. | The parsed path (`create_index`) emits no definition node either — if recovery minted index definitions, recovered files would claim MORE than parsed ones, violating strict additivity (AC-4's spirit). | Emit index definitions per a literal reading of Requirement 2 — rejected: breaks parsed/recovered representation parity. |
| 2026-07-04 | The mask covers string literals (`'...'`, `"..."`, `$$...$$`) in addition to comments. | Live probe: dynamic SQL inside ERROR regions (`EXECUTE 'CREATE TABLE ghost'`) surfaces as scannable text; string-DDL minting is the same invented-schema-object failure as comment-DDL. Masking double-quoted identifiers costs only recall (a quoted name is not recovered), never precision. | Comments-only masking per the literal requirement — rejected: leaves the string-DDL minting hole open inside ERROR regions. |
| 2026-07-04 | Batch/terminator fragments (`GO`, `DELIMITER ;`) count as unrecovered regions. | They are real ERROR regions the scan cannot claim; counting them is honest even though they carry no lost schema content — "nothing silently dropped" outranks count aesthetics. | Special-case a known-terminator allowlist — rejected: vocabulary creep for cosmetics; field counts stay interpretable either way. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| ERROR-region boundaries mis-segment (one region spans two statements), attributing references to the wrong recovered node. | Segmentation by top-level statement terminators within the region (`;`, `$$` pairs, `GO`) before attribution; the adversarial fixtures include multi-statement ERROR regions; wrong-attribution cases fall back to module scope rather than guessing. |
| Comment-stripping bugs create false negatives (real DDL after a `/*` on the same line). | Comment stripping is a small, separately unit-tested function; the fixtures include mixed comment/DDL lines both ways. |
| Recovery vocabulary drift vs real dialect usage. | Vocabulary is a reviewable constant; unrecovered counts in the build log are the field signal for extension. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
