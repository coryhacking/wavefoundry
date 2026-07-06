# Recover in-loop DML from PL/pgSQL control-flow bodies

Change ID: `1rs45-enh sql-plpgsql-loop-body-dml-recovery`
Change Status: `implementing`
Owner: Engineering
Status: planned
Last verified: 2026-07-06
Wave: `1rvdp carryover-followups`

## Rationale

Split out of `1rrx5-enh sql-graph-accuracy-followups` at the `1rs44` readiness primer and tracked on its own. When a natively-parsing PL/pgSQL routine (`CREATE FUNCTION … AS $$ … $$`) has a `FOR r IN … LOOP … END LOOP` / `WHILE … LOOP` body, tree-sitter-sql cannot parse the loop construct: the routine header parses at top level so the loop body lands in **nested** `ERROR` regions that `scan_top` never sees (`error_regions` stays 0; `sql_partial_bodies`, landed in `1rs44`, flags it).

**Mechanism-spike reframing (2026-07-06 — corrects the split-time premise).** A live spike (11 real-grammar probes) established that in-loop DML is **NOT wholesale "silently dropped"** as the split-time doc assumed: wave `1p9qi`'s `walk_reads` `statement`-node branch already dispatches every cleanly-parsed in-loop statement (a sibling of the loop's ERROR nodes) through `analyze_statement` with correct direction — so most in-loop `INSERT/UPDATE/DELETE`/reads already recover today. **The true residual loss is narrow:** only the statement whose leading keyword gets ABSORBED into an adjacent ERROR span — specifically the DML statement immediately after `LOOP`, where tree-sitter-sql shreds `INSERT INTO dst (…)` into `keyword_from, relation` + a `term` node `dst (id) VALUES`, so the target is unrecoverable and its direction lost. Recovery targets that residual, not a wholesale gap. Consequences: AC fixtures must target the absorbed-keyword statement specifically, and the real-corpus recall claim must be measured against the `1p9qi` baseline, not zero.

## Requirements

Mechanism (Decision Log 2026-07-06): **Approach B — strip-and-reparse through the existing statement unit** (chosen over Approach A regex-over-masked-ERROR by the spike; B reuses the already-adversarially-reviewed unit and gets direction/CTE/temp/alias/nested-loop handling for free with ZERO new DML/CTE vocabulary, collapsing the whole faithfulness surface to "is the strip correct?").

1. **Recover in-loop DML by stripping loop scaffolding and reparsing the body through the statement unit.** For a natively-parsed routine whose body subtree contains a nested `ERROR` (the `sql_partial_bodies` case): extract the `$$…$$` body text, **mask non-code first** (reuse `_sql_recovery_mask_noncode`), lexically strip the loop scaffolding (`FOR <var…> IN <query> LOOP` / `WHILE … LOOP` / `FOREACH … LOOP` / `END LOOP [label]` / bare `LOOP`), then reparse the residue through `sql_statement_references`/`_sql_analyze_program` with `recover=False` (mirroring `handle_error_region`'s no-recursion reentry). The reparsed statements get correct read/write direction, CTE exclusion, temp exclusion, and alias handling from the unit — no new vocabulary. Recovered references attribute to the routine owner with `extraction: "sql_recovery"` provenance.
2. **The strip is keyword/token-oriented over masked text, NOT line-oriented** (the spike's decisive finding — the naive line-strip failed multi-line and single-line loop headers; the masked keyword strip passed all 11 shapes incl. `LOOP` inside a string literal). Match `\bLOOP\b`/`\bEND\s+LOOP\b` on word boundaries so identifiers (`loop_events`) and columns (`loop`) survive; locate a query-FOR's closing `LOOP` as the first top-level `\bLOOP\b` after `IN` on masked text.
3. **Preserve the loop-header query's real reads.** `FOR r IN SELECT id FROM src LOOP` — `src` is a GENUINE read to keep (rewrite the header `<query>` as a standalone `SELECT …;` so the unit recovers it). Distinguish query-FOR (keep the query) from integer-range FOR (`FOR i IN 1..10` → drop, no read), cursor-FOR (`FOR r IN c(…)`), and `FOREACH … IN ARRAY`. Handle labelled loops (`<<lbl>> LOOP` / `END LOOP lbl;`) and nested loops.
4. **Integration = AUGMENT the body walk (dedup), GATED to LOOP-BEARING bodies only.** Superseding the readiness "REPLACE" framing — an implementation-time real-corpus finding (2026-07-06, ~90-routine PL/pgSQL corpus) showed the normal `walk_reads` statement dispatch is MORE robust than the strip-reparse for assignment-heavy bodies: with `recover=False`, a `l1 := value; … INSERT …` body re-traps the `INSERT` in an ERROR the reparse drops, while the normal walk descends through the ERROR to the nested `statement` node and recovers it. So the normal body walk **always runs** (the recall floor, zero regression), and for a loop-bearing body (`\bLOOP\b` on masked text) the strip-reparse runs ADDITIONALLY, appending ONLY references the walk did not already produce for this routine (dedup on `direction`+`name`). This yields exactly-once (a table the walk found is recorded once, never doubled) AND recovers the tight-shape residual the walk cannot reach — strictly safer than REPLACE, which could lose a walk-recoverable ref when the strip returns non-empty-but-incomplete. Routines with NO loop stay entirely on today's walk. The **top-level** `handle_error_region` path stays untouched (AC-4). Recovered (added) refs attach to the routine owner with `sql_recovery` provenance; in-body definitions from the reparse are ignored.
   **MIXED-body handling (security-reviewer prepare-council 2026-07-06):** the augment design resolves the mixed-body concern by construction — a loop-bearing body holding a sibling non-loop DML (`IF cond THEN INSERT … END IF`) keeps that DML because the normal walk (which recovers it today) still runs unconditionally; the strip only ADDS the post-`LOOP` residual on top. Verified by an explicit mixed loop+branch fixture (AC-4). There is no under-capture risk from gating, because the walk is never suppressed.
5. **`sql_partial_bodies` honesty.** Since recovery now fires, expose a recovered-vs-still-unrecovered split so the loudness signal stays honest; a genuinely-unrecoverable construct still flags. Residue (`BEGIN`/`END`/`DECLARE`/assignments/`EXIT`/`CONTINUE`) produces a benign top-level ERROR on reparse that mints nothing — pin this with an absence sweep.

## Scope

**Problem statement:** The DML statement absorbed into the loop's ERROR span (the one right after `LOOP`) is the residual in-loop write that the `1p9qi` statement-dispatch does not recover — its target is shredded into a `term` node. Recovering it needs the loop scaffolding stripped so the body reparses cleanly through the existing unit; NO new DML/CTE regex vocabulary (Approach A, rejected).

**In scope:**

- The mask → strip-scaffolding → reparse-through-unit path (R1–R3) in `.wavefoundry/framework/scripts/graph_indexer.py`, augmenting-with-dedup the body walk for loop-bearing partial-body routines (R4).
- `sql_partial_bodies` recovered/unrecovered split (R5).
- Exact-set flip tests targeting the absorbed-keyword statement + header-read preservation + CTE-free + nested-loop + labelled-loop + `LOOP`-in-string; the mandatory adversarial-faithfulness lane (recovery detection surface); real-corpus validation measured against the `1p9qi` baseline.
- The `GRAPH_BUILDER_VERSION` bump the recovered edges require (extraction-output change).

**Out of scope:**

- Approach A (regex DML vocabulary + a new scanner CTE exclusion) — rejected: re-implements the reviewed unit lossily, a broad permanent noise surface.
- Full plpgsql grammar support (a tree-sitter grammar change).
- Argument tracing through `CALL`/`PERFORM`.
- Recovery of statements the strip leaves genuinely unparseable (flagged by `sql_partial_bodies`, not recovered).

## Acceptance Criteria

- [x] AC-1: An exact-edge-set test proves the ABSORBED-keyword statement recovers for the shape that actually drops it — the `INSERT`/`UPDATE`/`DELETE` immediately after `LOOP` in an **inline-query-FOR** body (`FOR r IN SELECT … LOOP <DML>`), which the `1p9qi` baseline drops (the parser is still in SELECT/FROM state at `LOOP`), now recovers as a `write` to the correct table, attributed to the routine, with `sql_recovery` provenance; a `SELECT … FROM t` in such a loop recovers as `reads`. The other loop headers (`WHILE … LOOP`, integer-range `FOR i IN 1..10`, cursor-`FOR`, `FOREACH … IN ARRAY`) assert NO-REGRESSION, not a flip. (`test_sql_partial_body_loop_dml_recovery` — flips `loop_audit` write to recovered + write-edge; `test_sql_loop_recovery_strip_robustness_and_faithfulness` — WHILE/integer-range no-regression.)
- [x] AC-2: A faithfulness test proves the header query's reads are PRESERVED (`FOR r IN SELECT id FROM src LOOP` keeps `src`), integer-range `FOR i IN 1..10` mints no phantom read, and a loop-local `WITH x AS (…) INSERT INTO x …` mints NO write to CTE name `x` (CTE exclusion inherited free from the unit); masked comment/string DML mints nothing (incl. `LOOP` inside a string literal). (`test_sql_loop_recovery_strip_robustness_and_faithfulness`.)
- [x] AC-3: The strip is keyword/token-masked (not line-oriented) — tests pin multi-line loop headers, single-line full loops, labelled loops (`<<lbl>>`/`END LOOP lbl`), nested loops, and identifiers/columns containing "loop" all handled correctly. (`test_sql_loop_recovery_strip_robustness_and_faithfulness`.)
- [x] AC-4: The top-level recovery tier's behavior is unchanged (its exact-set tests stay green unmodified); NO double-processing — a table the walk found is recorded exactly once (the strip AUGMENTS with dedup, never doubles). **Mixed-body no-regression fixture:** a body holding BOTH a `FOR…LOOP` and a sibling non-loop DML (`IF cond THEN INSERT INTO t … END IF`) recovers the non-loop DML exactly as `walk_reads` does (same edge/direction/table) because the walk runs unconditionally and the strip only adds the post-`LOOP` residual on top; the `SKIP LOCKED`/PROCEDURE scope boundary is pinned too. (`test_sql_loop_recovery_mixed_body_and_gating`.)
- [x] AC-5: `sql_partial_bodies` exposes the recovered-vs-unrecovered split honestly (`sql_partial_bodies_recovered`); a genuinely-unrecoverable body still flags; residue mints nothing. **Real-corpus validation (2026-07-06, ~90-routine PL/pgSQL corpus):** recovered in-loop writes hand-verified PRECISE (every recovered ref points to a real table, correct direction + owner; the strip never mis-binds, verified in isolation). **Honest recall finding: incremental delta over the `1p9qi` baseline is ~ZERO on this real corpus** — realistic multi-statement loop bodies already recover their in-loop DML via the normal `walk_reads` statement dispatch + the `1p9qe` top-level tier; the strip's genuine gain is confined to the tight `FOR r IN SELECT…FROM t LOOP <DML>` shape (proven by the synthetic AC-1 test) which hand-written PL/pgSQL rarely uses. Durable-but-narrow-delta outcome (cf. `1p9q5` Rust); the implementation is correct + zero-risk (augment+dedup adds nothing when the walk already covers). Recorded for operator disposition.
- [x] AC-6: Standing gates — `GRAPH_BUILDER_VERSION` bumped 40→41; full `test_graph_indexer` suite green (508); the adversarial-faithfulness review lane is selected for delivery review (the strip is the target). Full framework suite + `wave_validate` + live upgrade-heal confirmed at wave integration.

## Tasks

- [x] Decide the recovery mechanism (spike 2026-07-06): **Approach B (strip-and-reparse)** chosen with decisive evidence (see Decision Log + Progress Log).
- [x] Implement mask → keyword-strip-scaffolding → reparse-through-unit (`recover=False`), AUGMENTING the body walk (dedup) for loop-bearing routines; preserve header-query reads; owner attribution. (`_sql_strip_loop_scaffolding`/`_sql_body_is_loop_bearing`/`_sql_routine_body_inner` + the augment block in `handle_create_routine`.)
- [x] `sql_partial_bodies` recovered/unrecovered split (`sql_partial_bodies_recovered` node property + `recovery` dict + build-log split).
- [x] Exact-set + faithfulness + strip-robustness + mixed-body tests; real-corpus validation vs 1p9qi baseline (corpus); version bump 40→41. Live upgrade-heal at wave integration.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| strip-reparse | implementer | — | Mask + keyword-oriented scaffolding strip + reparse through the unit; header-read preservation; owner attribution; augment-with-dedup body walk (walk stays the recall floor). |
| partial-body-honesty | implementer | strip-reparse | `sql_partial_bodies` recovered/unrecovered split. |
| validation | implementer | strip-reparse | Exact-set (absorbed-keyword) + faithfulness + strip-robustness tests; real-corpus validation vs 1p9qi baseline; adversarial-faithfulness lane. |


## Serialization Points

- Shares `graph_indexer.py`'s SQL recovery/statement region — `1p9qi`/`1rs44` landed (v39/40); coordinate merge order only if `1p9q8`-region work reopens (it closed).
- The mechanism decision was the hard pre-implementation gate — now SETTLED (Approach B).

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — the recovery-tier note gains the nested-in-body loop recovery via scaffolding-strip-and-reparse (reusing the statement unit; no new regex vocabulary) and the `sql_partial_bodies` recovered/unrecovered split.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The absorbed-keyword write recovery is the deliverable. |
| AC-2 | required | Header-read preservation + CTE-exclusion are the strip's faithfulness edges. |
| AC-3 | required | The strip robustness (keyword-masked, not line) is the whole faithfulness surface. |
| AC-4 | required | No-double-processing + top-level-untouched are the regression guards. |
| AC-5 | important | Honest partial-bodies signal + real-corpus recall vs baseline. |
| AC-6 | required | Standing version/adversarial/suite gates. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-05 | Split out of `1rrx5` at the `1rs44` readiness primer (the "reuse the `1p9qe` tier unchanged" premise was falsified). | `1rs44` red-team readiness primer. |
| 2026-07-06 | **Delivery review — adversarial-faithfulness (mandatory) + code/perf lanes, both PASS WITH NOTES.** Adversarial lane: 18 probes (mis-located-`LOOP` splice, `loop`-as-identifier, masked-string ghost DML, nested/labelled loops, multi-DML chains, dollar-tag body, temp exclusion, CTE collision) — NO wrong-binds, NO drops; the recovered set is a strict superset of the walk baseline (augment is purely additive). Code/perf lane: dedup floor correct, `_sql_routine_body_inner` 0/1/3-quote safe, strip cost bounded (gated on `has_body_error AND \bLOOP\b`; `while`-loop terminates), 1rqh2 provably inert. FIX-NOW applied: gated the strip on `recover` so the one-level no-recursion contract is explicit (`if loop_bearing_body and recover:`). Suite still 508 green. Non-blocking note: a table literally named `loop` (reserved word, illegal unquoted) is not recovered — pre-existing, no wrong edge. | adversarial + code/perf delivery lanes 2026-07-06; graph suite 508 green post-fix. |
| 2026-07-06 | **Implemented + real-corpus-validated.** Strip helpers (`_sql_strip_loop_scaffolding`/`_sql_body_is_loop_bearing`/`_sql_routine_body_inner`) + augment-with-dedup integration in `handle_create_routine`; `sql_partial_bodies_recovered` split (node property + `recovery` dict + build-log); `GRAPH_BUILDER_VERSION` 40→41. 3 new tests (recovery flip, strip robustness, mixed-body/gate) + version pin; full `test_graph_indexer` green (508). Real corpus (~90 routines, operator-supplied): recovery PRECISE (no mis-binds, verified in isolation) but incremental delta ~0 (the walk already recovers structured bodies; the strip's value is the tight inline-query-FOR shape only). Surfaced a pre-existing baseline `read skip` phantom from `FOR UPDATE SKIP LOCKED` (out of 1rs45 scope — follow-up). | `test_graph_indexer` 508 green; `~/.claude/jobs/e29ad14d/tmp/{corpus,iso}_val.py` corpus probes. |
| 2026-07-06 | **Prepare-council security-reviewer (rotating seat) — mixed-body gap folded in.** The seat found the loop-gating narrative treats the partial-body population as binary but it is ternary: a MIXED body (`FOR…LOOP` + sibling `IF…INSERT…END IF`) has the `\bLOOP\b` gate fire for the whole body, routing IF-branch DML that `walk_reads` recovers today through strip-reparse with the walk suppressed — an under-capture regression risk no fixture pinned. Added a mixed loop+branch no-regression fixture to AC-4, a MIXED-body caveat to R4, and softened the "never wrong-bind" risk claim (a mis-located `LOOP` splice yields clean-but-wrong, not ambiguous). | security-reviewer prepare-council seat 2026-07-06. |
| 2026-07-06 | **Mechanism spike — DECIDED: Approach B (strip-and-reparse).** 11 live probes: B's keyword-oriented masked strip passed every shape (multi-line/single-line/labelled/nested loops, `LOOP`-in-string) and, via reparse through the existing unit, recovered the absorbed-keyword write, preserved header reads, and excluded a loop-local CTE with zero new vocabulary. Reframing finding: in-loop DML is NOT wholesale dropped — `1p9qi`'s `walk_reads` statement-dispatch already recovers most; the residual is the absorbed-keyword statement after `LOOP`. Requirements/ACs rewritten to B + the residual framing; integration = replace body walk for partial-body routines. | mechanism spike 2026-07-06 (probe artifacts `~/.claude/jobs/e29ad14d/tmp/spike*_1rs45.py`). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-05 | Split from `1rrx5` into its own change. | Materially larger and its own review surface. | Keep unified in `1rrx5` (rejected). |
| 2026-07-06 | **Recovery mechanism = Approach B (strip loop scaffolding, reparse the body through the existing statement unit).** | Spike: B reuses the already-adversarially-reviewed unit (correct direction, CTE/alias/temp exclusion, nested loops ALL free — zero new DML/CTE vocabulary); the whole faithfulness surface is "is the strip correct?", which the keyword-oriented masked strip passed on all 11 probes. Approach A would re-implement the unit lossily in regex (6+ constants + a new CTE collector + direction logic) — a broad permanent noise-reintroduction surface (1p9qc/1p9qd/1p9qi classes). | Approach A regex-over-masked-ERROR (rejected: broad permanent faithfulness surface); naive line-oriented strip (rejected: failed multi-line + single-line loop headers — must be keyword/token-masked). |
| 2026-07-06 | Reframe from "in-loop DML silently dropped" to "the absorbed-keyword statement after `LOOP` is the residual." | Live baseline probes: `1p9qi`'s `walk_reads` statement-dispatch already recovers cleanly-parsed in-loop statements; only the keyword-absorbed one is lost. AC fixtures target the residual; real-corpus recall measured vs the `1p9qi` baseline, not zero. | Measure recall against zero (rejected: overstates the gap and the change's value). |
| 2026-07-06 | **Gate the strip-reparse REPLACE to LOOP-bearing bodies only** (`\bLOOP\b` on the masked body text); routines whose masked body has no loop construct stay entirely on today's already-working walk. | Readiness primer's strongest challenge: the `_sql_subtree_has_error` gate fires for the WHOLE partial-body class (IF/CASE/`RETURN QUERY`/`EXECUTE`), and in-branch DML inside an `IF` block already recovers today — a blanket "replace the body walk for every `_sql_subtree_has_error` routine" would put those non-loop partial bodies through the strip and risk regressing what already works. The loop scaffolding is the only thing the strip exists to remove, so gate the replace to exactly the population that needs it. | Replace the body walk for all `_sql_subtree_has_error` routines (rejected: needlessly re-routes already-recovering non-loop partial bodies through the strip). |
| 2026-07-06 | Scope the AC-1 recovery FLIP to the **inline-query-FOR** shape (`FOR r IN SELECT…LOOP`); the other loop headers (`WHILE`, integer-range, cursor-`FOR`, `FOREACH`) assert NO-REGRESSION, not a flip. | Live probe: only the inline-query-FOR body drops its post-`LOOP` DML target (`dst_a` lost); the other headers already recover their in-loop DML via `walk_reads`. Claiming a flip for all headers would overstate the change. | Assert a recovery flip for every loop header (rejected: false for the four already-recovering shapes). |
| 2026-07-06 | **Integration = AUGMENT the walk with dedup, NOT REPLACE it** (implementation-time supersede of the readiness "REPLACE" framing). | Real-corpus finding: with `recover=False` the strip-reparse re-traps a DML in an ERROR for assignment-heavy bodies (`l1 := value; … INSERT …`) and returns fewer refs than the normal `walk_reads` statement dispatch, which descends through the ERROR. REPLACE-on-nonempty would silently drop a walk-recoverable ref when the strip returns non-empty-but-incomplete. Augment-with-dedup keeps the walk as the recall floor (zero regression), adds only the strip's NEW `(direction,name)` refs (exactly-once preserved), and resolves the security-reviewer mixed-body concern by construction (the walk that recovers the IF-branch DML is never suppressed). | REPLACE the walk on non-empty strip (rejected: partial-miss regression risk the real corpus exposed); merge without dedup (rejected: doubles walk-found tables). |
| 2026-07-06 | **Deliver the correct implementation despite ~zero real-corpus recall delta; report honestly for operator disposition.** | Real corpus: the walk + `1p9qe` tier already recover realistic structured loop bodies; the strip's genuine gain is the tight inline-query-FOR shape only, which this corpus does not use. Augment+dedup makes the strip zero-risk when zero-delta (adds nothing the walk found). Durable, correct, safe — analogous to the `1p9q5` durable-but-zero-delta Rust outcome; the standing stance is report-and-let-operator-decide. | Drop `1rs45` as no-value (rejected: the tight shape IS a genuine faithfulness gap, proven by synthetic tests, and the implementation is zero-risk); re-scope to only ship the loudness split (deferred to operator). |


## Risks


| Risk | Mitigation |
| --- | --- |
| The scaffolding strip is incorrect — over-strips (drops a real statement/read) or under-strips (leaves a poison `LOOP` that re-ERRORs). | Keyword/token-oriented masked strip (proven on 11 probes incl. adversarial); header-query reads preserved as standalone `SELECT`; exact-set + strip-robustness tests (multi-line/single-line/labelled/nested/`LOOP`-in-string); adversarial-faithfulness lane targets exactly the strip. |
| Double-processing — the strip-reparse plus the normal body walk both mint a partial-body routine's clean statements. | Integration AUGMENTS the walk with DEDUP (`\bLOOP\b`-gated): the strip appends only refs the walk did not already produce for the routine (dedup on direction+name), so a table the walk found is recorded exactly once. Non-loop partial bodies (IF/CASE/`RETURN QUERY`/`EXECUTE`) never trigger the strip. AC-4 pins exactly-once + the mixed-body no-regression. |
| Recovered writes wrong-attributed or wrong-table. | Reparse runs through the unique-match-or-drop unit — genuine AMBIGUITY drops rather than wrong-binds; provenance-marked; real-corpus precision hand-check. Residual edge (security-reviewer prepare-council 2026-07-06): a MIS-LOCATED closing `LOOP` could splice header-query text into the following DML and yield a *clean-but-wrong* parse (confident, not ambiguous — so it bypasses the drop). Bounded by the keyword/token-masked strip robustness (AC-3), the adversarial-faithfulness lane targeting exactly the `\bLOOP\b` location logic, and the real-corpus precision hand-check — not by the drop path. "Never wrong-bind" holds only for the ambiguous case, not this splice case. |
| Real-corpus delta is negligible (the residual is narrow). | Honest: measure vs the `1p9qi` baseline and report; the absorbed-keyword write is a genuine faithfulness gap even if low-frequency. Re-scope on negligible delta per the standing stance. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
