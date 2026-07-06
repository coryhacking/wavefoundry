# Recover in-loop DML from PL/pgSQL control-flow bodies

Change ID: `1rs45-enh sql-plpgsql-loop-body-dml-recovery`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-05
Wave: TBD

## Rationale

Split out of `1rrx5-enh sql-graph-accuracy-followups` at readiness (2026-07-05, `1rs44` prepare-phase red-team primer). The primer's live tree evidence falsified the original "reuse the `1p9qe` recovery tier unchanged" framing, showing this item is materially larger and riskier than the bounded point fixes it was bundled with — so it is tracked and reviewed on its own.

When a natively-parsing PL/pgSQL routine (`CREATE FUNCTION … AS $$ … $$`) has a `FOR r IN … LOOP … END LOOP` / `WHILE … LOOP` body, tree-sitter-sql cannot parse the loop construct: the routine header parses at top level so the loop body lands in a **nested** `ERROR` region that `scan_top` never sees (`error_regions` stays 0), and in-loop `INSERT/UPDATE/DELETE` writes are silently dropped. Wave `1p9qi` made this OBSERVABLE via the `sql_partial_bodies` module-node counter; this change RECOVERS the dropped in-loop DML so "which code writes table X" is complete for the Postgres/PL-SQL routine-heavy shapes the `1p9qi` census corpora (MySQL/Java Fineract, Tomcat) never exercised.

## Requirements

1. **Recover in-loop DML writes/reads from nested-in-body ERROR regions.** For a natively-parsed routine whose body subtree contains a nested `ERROR` (the `sql_partial_bodies` case), extract the ERROR-region text and recover the DML statements the shredded AST dropped, attributing them to the routine owner with `extraction: "sql_recovery"` provenance and the correct direction (INSERT/UPDATE/DELETE/MERGE → `writes`; SELECT/FROM → `reads`).
2. **Add a DML recovery vocabulary to the recovery scanner.** `_sql_recover_error_region` currently recovers only CREATE definitions (`_SQL_RECOVERY_CREATE_RE`) and `ALTER TABLE` writes (`_SQL_RECOVERY_ALTER_RE`) — it has NO INSERT/UPDATE/DELETE/MERGE patterns. Add bounded, line-anchored, masked-text DML-write/read patterns (reviewable constants) that recover the target table of each in-loop mutation. Line-anchored regex over masked text is required (not AST re-parse): the top-level `handle_error_region` re-parse trick does not transfer, because the poison token (`LOOP`) remains in the extracted text and re-breaks the parse identically, and the insert target is shredded into `ERROR > term`, not a clean `object_reference`.
3. **Provide a CTE-exclusion story for the regex scanner.** The AST path's CTE exclusion (`make_ref`'s `cte_names` check, fed by `_sql_collect_cte_names`) does NOT exist in the recovery scanner. A regex DML scanner over an ERROR region has no CTE context, so an in-loop `WITH x AS (…) INSERT INTO x …` would mint a phantom write to the CTE name `x`. Add a recovery-scanner-local CTE-name collection (or an equivalent exclusion) so recovered DML never binds a loop-local CTE name — this is the primary noise-reintroduction vector and must be closed, not waved off.
4. **Honor the existing degradation convention and bounds.** Reuse `_sql_recovery_mask_noncode` (comment/string masking) and the temp-name exclusion (`_sql_recovery_clean_name` is_temp) unchanged; keep the byte/line ceilings; recovered writes carry provenance; `sql_partial_bodies` reflects recovery (e.g. a recovered-vs-still-unrecovered split so the loudness signal stays honest).
5. **Descend + attribute orchestration.** Add the orchestration in the routine-body handling to (a) find the nested ERROR subtree of a natively-parsed routine (currently only counted), (b) extract its text, (c) run the extended recovery scan, (d) attribute the recovered references to the routine owner — without double-processing the top-level recovery path or regressing it.

## Scope

**Problem statement:** In-loop DML in PL/pgSQL control-flow routine bodies is silently under-captured (the writes vanish) on the trusted native-parse path; `1p9qi` made it observable but did not recover it. Recovery needs a new DML vocabulary in the recovery scanner, a new nested-ERROR descent/attribution path, and a new regex-scanner CTE-exclusion — none of which the existing tier provides.

**In scope:**

- Extend `_sql_recover_error_region` with DML-write/read patterns (R2) + a scanner-local CTE exclusion (R3), all in `.wavefoundry/framework/scripts/graph_indexer.py`.
- Nested-in-body ERROR descent + recovery + owner attribution (R1, R5).
- `sql_partial_bodies` recovered/unrecovered honesty (R4).
- Exact-set flip tests over real-grammar FOR/WHILE-body fixtures; the mandatory adversarial-faithfulness review lane (this activates a recovery/detection surface); real-corpus validation against a Postgres routine-heavy repo (the mechanism decision below determines the corpus).
- Whatever `GRAPH_BUILDER_VERSION` bump the recovered edges require (extraction-output change → a bump; coordinate with `1rrx5`/`1p9q8` merge order if landing near them).

**Out of scope:**

- The bounded `1rrx5` point fixes (its R1–R5) — this change is only the loop-body recovery.
- Full plpgsql grammar support (a tree-sitter grammar change) — recovery is a bounded regex tier, not a parser.
- Argument tracing through `CALL`/`PERFORM`.

## Acceptance Criteria

- [ ] AC-1: An exact-edge-set test proves in-loop `INSERT`/`UPDATE`/`DELETE` in a `FOR … LOOP` and a `WHILE … LOOP` PL/pgSQL body recover as `writes` to the correct table, attributed to the routine, with `sql_recovery` provenance; a `SELECT … FROM t` in a loop recovers as a `reads`.
- [ ] AC-2: A faithfulness test proves a loop-local `WITH x AS (…) INSERT INTO x …` mints NO write to the CTE name `x` (the R3 exclusion binds), and that masked comment/string DDL/DML in a loop body mints nothing.
- [ ] AC-3: `sql_partial_bodies` honestly reflects recovery (recovered bodies drop out of the unrecovered count, or a recovered/unrecovered split is exposed); a body with a genuinely unrecoverable construct still flags.
- [ ] AC-4: The top-level recovery tier's behavior is unchanged (its exact-set tests stay green unmodified); no double-processing of the recovery path.
- [ ] AC-5: Real-corpus validation on a Postgres routine-heavy repo (mechanism-decision-dependent corpus) — recovered in-loop writes hand-verified for precision; recall gap characterized.
- [ ] AC-6: Standing gates — `GRAPH_BUILDER_VERSION` bump; the consolidated adversarial-faithfulness review lane run (recovery detection surface); full suite green; `wave_validate` clean; live upgrade-heal.

## Tasks

- [ ] Decide the recovery mechanism (see Decision Log open item): line-anchored DML regex over masked ERROR text vs. body-text re-parse after stripping `FOR…LOOP`/`END LOOP` scaffolding. The choice sets the true size and faithfulness surface.
- [ ] Implement the DML recovery vocabulary + scanner-local CTE exclusion.
- [ ] Implement nested-ERROR descent + owner attribution; keep the top-level path untouched.
- [ ] Exact-set + faithfulness tests; real-corpus validation; version bump + upgrade-heal at integration.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| recovery-vocabulary | implementer | — | DML patterns + scanner-local CTE exclusion in `_sql_recover_error_region`. |
| nested-descent | implementer | recovery-vocabulary | Descend into a native routine's nested ERROR subtree, run the scan, attribute to owner. |
| validation | implementer | nested-descent | Exact-set + faithfulness tests; real-corpus Postgres validation; adversarial-faithfulness lane. |


## Serialization Points

- Shares `graph_indexer.py`'s SQL recovery/statement region with `1rrx5` and the planned `1p9q8 graph-index-accuracy` — coordinate merge order; if `1rrx5` lands first, rebase anchors.
- The recovery mechanism decision (Decision Log) is a hard gate before implementation — it determines scope.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — the recovery-tier note must gain the nested-in-body DML recovery behavior and its regex-scanner CTE-exclusion story.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required / important / nice-to-have / not-this-scope | Set at Prepare. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-05 | Split out of `1rrx5` at the `1rs44` prepare-phase readiness primer, which falsified the "reuse the `1p9qe` tier unchanged" premise with live tree evidence (no DML patterns, no CTE exclusion in the scanner; the `FOR…LOOP` ERROR shreds the insert target so AST re-parse cannot transfer). | `1rs44` red-team readiness primer, 2026-07-05. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-05 | Split from `1rrx5` into its own change. | Materially larger and riskier than the bounded point fixes: needs new DML recovery vocabulary + nested-ERROR descent/attribution + a new regex-scanner CTE exclusion, and activates a recovery/detection surface (mandatory adversarial-faithfulness lane) unvalidated against any real PL/pgSQL corpus. | Keep unified in `1rrx5` (rejected: drags five clean flip-fixes behind R6's review surface and understates its risk under a false "unchanged reuse" framing). |
| 2026-07-05 | OPEN — recovery mechanism (regex-over-masked-text vs. reparse-after-scaffolding-strip) to be decided before implementation. | The primer flagged that the plan named neither, and the choice sets the true size and faithfulness surface (regex needs a new CTE exclusion; reparse needs line surgery to remove the poison `LOOP` tokens). | Decide at Prepare with a spike if needed. |


## Risks


| Risk | Mitigation |
| --- | --- |
| The regex DML scanner re-introduces the noise classes `1p9qc`/`1p9qd`/`1p9qi` eliminated (CTE/alias/temp phantoms) — the scanner has no AST context. | R3 mandates a scanner-local CTE exclusion; reuse the masking + temp exclusion; exact-set + faithfulness tests with absence sweeps; the adversarial-faithfulness lane is mandatory. |
| Recovered writes are wrong-attributed or bind the wrong table. | Unique-match-or-drop at the bind stage (ambiguity → drop, never wrong-bind); provenance-marked; real-corpus precision hand-check. |
| Mechanism chosen without evidence bloats scope or misses shapes. | The mechanism decision is a hard pre-implementation gate with a spike option. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
