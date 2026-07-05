# SQL graph accuracy follow-ups (1p9qi review residuals)

Change ID: `1rrx5-enh sql-graph-accuracy-followups`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-05
Wave: TBD

## Rationale

Wave `1p9qi sql-graph-accuracy` shipped the graph's first code→data-layer edge family (clause-aware `reads`/`writes`, ERROR-region recovery, embedded-SQL capture/bind, ORM `maps_to`). Its delivery council fixed the one severe defect it found (routine-body write-direction inversion) and recorded a set of smaller, non-blocking residuals as honest follow-ups rather than expanding an already-large wave at close time. This change consolidates those recorded residuals into one admittable plan so they are not lost. Every item here is either safe under-capture (a recall gap, never a confidently-wrong edge) or reserved-name/edge-case noise that `LITERAL_DERIVED` + unique-match-or-drop already contains — none is a shipped-behavior regression. The value is closing the recall gaps and removing the residual phantoms so "which code touches table X" is complete for the Postgres/PL-SQL routine-heavy shapes the 1p9qi census corpora (MySQL/Java Fineract, Tomcat) never exercised.

## Requirements

Bounded faithfulness fixes (each is a small, self-contained correction to the `1p9qi` statement unit / capture path):

1. **`EXECUTE FUNCTION <name>` trigger action must not mint a phantom read.** A Postgres `CREATE TRIGGER … EXECUTE FUNCTION log_it()` currently emits a `reads` reference for the function name `log_it`. The invocation/name-family exclusion (the scalar-invocation-name and `RETURNS <type>` skips already landed in `1p9qi`) must be extended to the `EXECUTE FUNCTION`/`EXECUTE PROCEDURE` action position: a routine name in that position is a call target, not a table reference.
2. **MERGE `WHEN … THEN` branch subqueries must surface their table reads.** `MERGE … WHEN MATCHED THEN UPDATE SET x = (SELECT v FROM lookup_tbl)` / `WHEN NOT MATCHED THEN INSERT … VALUES ((SELECT … FROM seed_tbl))` currently drop the subquery's `lookup_tbl`/`seed_tbl` reads. The statement unit's "`when_clause` never contains table references" assumption is wrong for subqueries — walk into `when_clause` subquery nodes and route them through the same clause dispatch used elsewhere.
3. **`DECLARE <var> <type>` type names must not mint phantom reads.** A PL/pgSQL `DECLARE r record;` / `DECLARE n integer;` currently emits a `reads` reference for the type token (`record`, `integer`). Type-name positions in a declaration are not table references — exclude them (same "a name is not a reference" family as R1 and the landed `RETURNS <type>` skip).
4. **Bracket-quoted T-SQL identifiers on the SQL-file path must normalize to a clean external id.** `SELECT * FROM [dbo].[users]` currently yields the mangled external `external::dbo].[users`. The earlier in-review fix attempt was reverted because normalizing inside the statement unit broke the pinned "names-as-written" contract (`1p9qd` deliberately preserves quoting; the bind stage normalizes). The recorded alternative is to normalize at the external-id minting site (`_sql_apply_file_extraction`'s external-id path) rather than in the frozen unit — apply quote-stripping there so the emitted external node id is clean without changing the unit's as-written reference text.
5. **The embedded-SQL sniff gate must recognize DDL/DML leading keywords it currently omits.** The `1p9qf` sniff set (`SELECT/INSERT/UPDATE/DELETE/WITH/MERGE/CALL/EXEC`) drops SQL literals that lead with `TRUNCATE`/`ALTER`/`DROP` (one live Apache Fineract site was observed). Add those leading keywords so schema-affecting embedded statements are captured and bound (as `writes` where the direction is a mutation).

Larger recall item (may split into its own change when a wave is formed):

6. **Recover in-loop DML from PL/pgSQL control-flow bodies.** `FOR r IN … LOOP … END LOOP` / `WHILE … LOOP` constructs are unparseable by tree-sitter-sql; the routine header parses natively so the loop body lands in a nested `ERROR` region that top-level `scan_top` never sees. In-loop `INSERT/UPDATE/DELETE` writes are therefore silently dropped (compounded by the `1p9qi` invocation-name exclusion, which skips the misparsed `INSERT INTO t (cols)` because it re-shreds to an `invocation` node). `1p9qi` already made this OBSERVABLE via the `sql_partial_bodies` module-node counter; this requirement is to RECOVER the dropped in-loop DML — descend into a natively-parsed routine's nested-in-body ERROR regions and run the same masked, anchored recovery scan the top-level ERROR tier (`1p9qe`) uses, honoring its degradation convention (`extraction: "sql_recovery"` provenance, bounded, temp/CTE exclusions), so in-loop writes bind at the correct direction instead of vanishing.

Edge-case and monitoring items (low priority; may be recorded-and-closed rather than fully implemented):

7. **Close the two recorded edge cases.** (a) A non-temp body-local `CREATE TABLE scratch` has its definition correctly dropped, but a later in-body read of `scratch` can cross-file unique-bind a same-named real table — decide whether body-local created names should suppress subsequent in-body reads of that name (like temp objects) or remain in the standard unique-bare model. (b) The routine body-definition drop is name-parse-gated (`body_def_floor` is set only when the header name parses as an `object_reference`), so the "routine bodies never define at module scope" invariant is non-total for an unnamed-but-parseable header — make the drop unconditional on routine nodes so the invariant is total.
8. **Instrument (do not pre-emptively change) the `writes`/`maps_to` clustering asymmetry.** Community detection excludes `reads` but not `writes`/`maps_to`; a hot write-target table (an audit/events log written by many routines) can bridge otherwise-unrelated modules — the exact failure mode the `reads` exclusion prevents, now amplified by denser in-body writes. The recorded stance is "accepted at weight 1, revisit if community quality degrades on write-hub-heavy repos." This item is to add a measurement (e.g. surface high-in-degree data-layer nodes in the graph report / a diagnostic) so the decision to exclude `writes`/`maps_to` from clustering can be made on evidence rather than pre-emptively.

## Scope

**Problem statement:** The `1p9qi` SQL graph accuracy wave shipped with a set of recorded, non-blocking residuals — several small faithfulness defects (phantom reads of routine/type/action names; a dropped MERGE-subquery read; a mangled bracket-quoted external id; an incomplete embedded-SQL sniff set), one larger recall gap (in-loop DML in PL/pgSQL control-flow bodies, currently observable but unrecovered), two edge cases, and one monitoring decision. They were deferred to keep the wave's review surface bounded; this change gathers them.

**In scope:**

- The five bounded statement-unit / capture faithfulness fixes (R1–R5) in `.wavefoundry/framework/scripts/graph_indexer.py`, each with exact-edge-set flip tests.
- The in-loop DML recovery for control-flow bodies (R6), extending the `1p9qe` recovery tier to nested-in-body ERROR regions; the `sql_partial_bodies` count should drop toward zero on recovered bodies (or gain a recovered-vs-unrecovered split).
- The two edge cases (R7) and the clustering instrumentation (R8).
- Whatever coordinated `GRAPH_BUILDER_VERSION` bump the eventual wave requires (R6 adds recovered edges → an extraction-output change → a bump; the R1–R5 corrections that only remove phantom edges or add contained reads also change the emitted edge set → fold into the same single bump).

**Out of scope:**

- The deliberately out-of-scope future features from the `1p9qi` watchpoints: JPQL binding, column-level lineage, convention-derived table names, Python/Go/TS SQL sinks, and Liquibase-changelog as a higher-recall definition source. Those are roadmap, not review residuals.
- The same-file origin-scope limitation of the embedded-SQL impostor check is an ACCEPTED, documented limitation (zero real-corpus false positives; most cross-file lookalikes are genuine SQL wrappers) — cross-file receiver-type resolution is explicitly NOT required here; if a future field false-positive appears, it gets its own change.
- Separately tracked, unrelated work: `1rqh2-debt remove-tomllib-import-fallback`, the planned `1p9q8 graph-index-accuracy` wave, and the standing install/TLS/GPU field-feedback items.

## Acceptance Criteria

- [ ] AC-1: An exact-edge-set test proves `CREATE TRIGGER … EXECUTE FUNCTION log_it()` mints no `reads`/`external::` reference for `log_it` (R1), both flip directions pinned.
- [ ] AC-2: An exact-edge-set test proves MERGE `WHEN … THEN` branch subqueries surface their table reads (`lookup_tbl`/`seed_tbl` read), and non-subquery `when_clause` content still mints nothing (R2).
- [ ] AC-3: An exact-edge-set test proves `DECLARE <var> <type>` type names (`record`, `integer`, custom types) mint no reference (R3).
- [ ] AC-4: A test proves `[dbo].[users]` (and `` `db`.`users` `` / `"USERS"` quoting variants) mint a clean external id (`external::dbo.users` or the agreed normalized form), with the frozen statement-unit reference text unchanged (R4) — the pinned "names-as-written" unit test stays green.
- [ ] AC-5: A test proves an embedded `TRUNCATE TABLE t` / `ALTER TABLE t …` / `DROP TABLE t` literal at a known sink captures and binds (as a mutation/`writes` where applicable), and non-SQL strings at sinks still refuse (R5).
- [ ] AC-6: An exact-edge-set test proves in-loop DML in a `FOR … LOOP` / `WHILE … LOOP` PL/pgSQL body binds at the correct direction (in-loop INSERT/UPDATE/DELETE → `writes`), with the recovery-provenance marker applied and the degradation bounds honored; `sql_partial_bodies` reflects recovery (R6).
- [ ] AC-7: Tests pin the two edge-case resolutions (R7): body-local created-name read suppression (or the conscious decision to leave it in the unique-bare model, recorded), and the unconditional routine body-definition drop making the module-scope-definition invariant total.
- [ ] AC-8: The clustering-asymmetry measurement (R8) exists and is documented; the exclude-or-not decision for `writes`/`maps_to` is recorded on evidence (either "no change, evidence shows no bridging" or a scoped exclusion change).
- [ ] AC-9: Standing gates — single coordinated `GRAPH_BUILDER_VERSION` bump covering all landed edge-set changes; the consolidated adversarial-faithfulness review lane runs (binding/recovery changes); full suite green; `wave_validate` clean; live upgrade-heal verified.

## Tasks

- [ ] Implement R1–R5 as symbol-disjoint statement-unit / capture edits with per-item exact-set flip tests.
- [ ] Implement R6 by extending the `1p9qe` recovery tier to nested-in-body ERROR regions (reuse its masking, anchored patterns, temp/CTE exclusions, and provenance marker); confirm no double-processing with the native path and no regression to the top-level recovery behavior.
- [ ] Resolve R7 edge cases; instrument R8 and record the clustering decision.
- [ ] Coordinate a single `GRAPH_BUILDER_VERSION` bump at integration; run the full suite, `wave_validate`, and a live upgrade-heal.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| bounded-fixes (R1–R5) | implementer | — | Five small statement-unit/capture corrections; symbol-disjoint, parallelizable; each with an exact-set flip test. |
| loop-recovery (R6) | implementer | — | Larger; extends the `1p9qe` recovery tier into nested-in-body ERROR regions. Candidate to SPLIT into its own change when a wave is formed. |
| edge-and-monitor (R7, R8) | implementer | bounded-fixes | Small edge-case pins + a clustering measurement/diagnostic. |
| integration | implementer | bounded-fixes, loop-recovery, edge-and-monitor | Single coordinated version bump + full suite + upgrade-heal; adversarial-faithfulness lane at review. |


## Serialization Points

- All workstreams converge on `.wavefoundry/framework/scripts/graph_indexer.py` (and the recovery tier for R6) — parallel lanes must work symbol-disjoint regions with a serialized integration step, exactly as `1p9qi` did.
- Single coordinated `GRAPH_BUILDER_VERSION` bump at integration, not per-item.
- Cross-wave: if `1p9q8 graph-index-accuracy` activates first and touches the same SQL extractor regions, coordinate merge order (both waves share `graph_indexer.py`).

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — the relation/recovery notes will need the in-loop recovery behavior (R6) and any clustering-exclusion decision (R8) folded in; the same-file origin-scope limitation note is already present. No `docs/ARCHITECTURE.md` hub change expected (confined to the graph-index subsystem).

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required / important / nice-to-have / not-this-scope | Provisional: R1–R5 faithfulness fixes lean required/important; R6 recall recovery important; R7/R8 nice-to-have. Set at Prepare. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-05 | Plan authored from the `1p9qi` delivery-council recorded follow-ups (before `1p9qi` close, at operator direction). | `1p9qi` change-doc Decision Logs (`1p9qd`/`1p9qf`) + wave.md `wave-council-delivery` synthesis. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-05 | Consolidate the `1p9qi` review residuals into ONE enhancement plan rather than leaving them as prose notes. | Operator direction to fold follow-ups into a plan before closing `1p9qi`; keeps the recall gaps/phantoms admittable and discoverable. | Leave as Decision-Log prose (rejected: not admittable, easy to lose); one change doc per item (rejected: too granular for planning — split at wave formation if needed). |
| 2026-07-05 | R4 bracket-quote normalization targets the external-id minting site, not the frozen statement unit. | The in-review attempt to normalize inside the unit broke the pinned "names-as-written" contract test; the bind stage already normalizes, so the external-id emission site is the correct locus. | Normalize in the frozen unit (rejected: breaks the deliberate as-written contract). |
| 2026-07-05 | R6 (in-loop recovery) is flagged as a split candidate. | It is materially larger than R1–R5 (recovery-tier extension vs point fixes) and grammar-limited; a wave may want it as its own reviewed change. | Force it into one change with the point fixes (kept as an option; decided at wave formation). |


## Risks


| Risk | Mitigation |
| --- | --- |
| R6's nested-in-body recovery re-introduces the noise classes `1p9qc`/`1p9qd` eliminated (keyword/alias/temp phantoms) via the recovery scan. | Reuse the `1p9qe` recovery tier's masking + anchored patterns + temp/CTE exclusions unchanged; exact-set tests with absence sweeps; the adversarial-faithfulness lane is mandatory (recovery is a detection surface). |
| A point fix (R1–R5) subtly changes an existing exact-set expectation. | Each fix carries its own flip test; the full existing exact-set suite must stay green UNMODIFIED except where a test encoded the buggy behavior (fixed consciously, documented). |
| R4 normalization collides two differently-quoted names onto one external id and wrong-binds. | Normalize to a canonical form only for the external-id string; binding stays unique-match-or-drop, so a collision degrades to ambiguous-drop, never a wrong bind; add a collision test. |
| This work overlaps `1p9q8`'s extractor regions if both are in flight. | Single-OPEN-wave rule already serializes activation; coordinate merge order at wave formation (serialization point recorded). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
