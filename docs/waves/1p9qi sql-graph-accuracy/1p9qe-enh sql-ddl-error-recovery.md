# SQL extraction: DDL recovery tier for statements the grammar cannot parse (procedures, functions, dialect forms)

Change ID: `1p9qe-enh sql-ddl-error-recovery`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

Live-verified (guru investigation, 2026-07-03): the installed `tree_sitter_sql` grammar produces an **ERROR node** for `CREATE PROCEDURE get_active_users() BEGIN ... END;` — only stray keyword tokens parse, so no definition node and no `defines` edge is ever produced for procedures. The `kind="function"` handling for `procedure`-typed nodes (`graph_indexer.py:1976-1981`) is unreachable given the grammar's actual output. SQL is dialect-fragmented (T-SQL, PL/pgSQL, MySQL, Oracle) and no single tree-sitter grammar parses them all — procedures, triggers, and dialect-specific DDL will keep hitting ERROR nodes whatever grammar version ships.

The framework already has the honest-degradation answer: the oversized-file line-scan tier (`1p9q6`) recovers imports/definitions where full parsing is unavailable, loudly labeled. The same pattern applies here at statement granularity: when a top-level statement region parses to ERROR, a bounded line-anchored scan recovers `CREATE {PROCEDURE|FUNCTION|TRIGGER|TABLE|VIEW|INDEX} <name>` definitions (and, best-effort, table references inside the unparsed body via the `1p9qd` statement unit applied to recognizable sub-statements), labeled as recovery-extracted. Interesting consequence already proven in the live run: references inside a failed procedure body were still emitted from file scope — recovery should *attach* them to the recovered procedure node instead of leaving them dangling at module level.

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

- [ ] AC-1: The live-repro fixture (`CREATE PROCEDURE ... BEGIN SELECT * FROM users; END;`) produces a procedure definition node (correct kind, `sql_recovery` marker) with a `defines` edge, and its body's `users` reference attaches to the procedure node, not the module node. Unit-tested.
- [ ] AC-2: Dialect-form fixtures (T-SQL `CREATE PROCEDURE ... AS BEGIN`, PL/pgSQL `CREATE FUNCTION ... $$...$$`, MySQL delimiter style) each recover their definition nodes; forms outside the vocabulary degrade to a logged unrecovered count, never silence. Unit-tested per form.
- [ ] AC-3: Commented-out DDL (line and block comments) and DDL text inside string literals of parsed statements emit nothing. Adversarial unit tests.
- [ ] AC-4: Parsed statements are untouched — files with zero ERROR regions produce byte-identical extraction before/after (regression pin), and recovery never runs on successfully parsed regions. Unit-tested.
- [ ] AC-5: Build log reports per-file recovered/unrecovered counts; bounds respected on a pathological fixture. Unit-tested on the log shape.
- [ ] AC-6: `GRAPH_BUILDER_VERSION` bumped; migration-fixture recovered-vs-parsed counts in the Progress Log; `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] ERROR-region identification + routing in SQL-mode extraction.
- [ ] Recovery scan: comment stripping, line-anchored CREATE-form vocabulary, kind mapping, `sql_recovery` marker, bounds, logging.
- [ ] Body-reference re-attachment through the `1p9qd` statement unit (parseable fragments only).
- [ ] Fixtures/tests per AC-1..AC-5; calibration counts on the migration fixture.
- [ ] Bump `GRAPH_BUILDER_VERSION`; run `run_tests.py` + `wave_validate`; clean `__pycache__`.

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


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Statement-granular ERROR-region recovery scan, grammar unchanged (approach A). | Dialect fragmentation means ERROR nodes are permanent weather, not a bug to fix once; recovery at the ERROR boundary keeps the parsed path pure while making the unparsed path visible and bounded; reuses the proven `1p9q6` degradation pattern and the `1p9qd` unit. | (B) Swap/upgrade the tree-sitter SQL grammar — weakness: no grammar covers all dialects; dependency churn with Windows-install risk for a partial fix; recovery is still needed after. (C) Regex-scan whole SQL files unconditionally — weakness: double-extraction of parsed statements and string/comment false positives; scanning only ERROR regions eliminates both. |
| 2026-07-03 | Body references attach to the recovered procedure node. | The live run proved they otherwise dangle at module scope, which answers "does this file touch X" but not "does this procedure touch X" — the question impact analysis actually asks. | Leave at module scope — rejected: loses the attribution for free once the procedure node exists. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| ERROR-region boundaries mis-segment (one region spans two statements), attributing references to the wrong recovered node. | Segmentation by top-level statement terminators within the region (`;`, `$$` pairs, `GO`) before attribution; the adversarial fixtures include multi-statement ERROR regions; wrong-attribution cases fall back to module scope rather than guessing. |
| Comment-stripping bugs create false negatives (real DDL after a `/*` on the same line). | Comment stripping is a small, separately unit-tested function; the fixtures include mixed comment/DDL lines both ways. |
| Recovery vocabulary drift vs real dialect usage. | Vocabulary is a reviewable constant; unrecovered counts in the build log are the field signal for extension. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
