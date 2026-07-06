# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-06

wave-id: `1rvdp carryover-followups`
Title: Carryover Followups

## Objective

Gather the discrete, recorded carryover follow-ups from prior closed waves into one wave so they are tracked and admittable rather than dangling as plan docs: the PL/pgSQL loop-body DML recovery split out of `1rs44` at readiness, and the ADR-aligned removal of the pre-3.11 `tomllib` import fallbacks flagged during the `1p9pe` review. When this wave closes, both carryover items are resolved and the follow-up backlog is drained (except the deliberately-held `1rtar` spike).

## Changes

Change ID: `1rs45-enh sql-plpgsql-loop-body-dml-recovery`
Change Status: `implementing`

Change ID: `1rqh2-debt remove-tomllib-import-fallback`
Change Status: `implementing`

Completed At: 2026-07-06

## Wave Summary

Wave `1rvdp` (Carryover Followups) delivered two changes: Recover in-loop DML from PL/pgSQL control-flow bodies and Remove stale tomllib import fallbacks. Notable adjustments during implementation: Recover in-loop DML from PL/pgSQL control-flow bodies: **Implemented + real-corpus-validated.** Strip helpers (`_sql_strip_loop_scaffolding`/`_sql_body_is_loop_bearing`/`_sql_routine_body_inner`) + augment-with-dedup integration in `handle_create_routine`; `sql_partial_bodies_recovered` split (node property + `recovery` dict + build-log); `GRAPH_BUILDER_VERSION` 40→41. 3 new tests (recovery flip, strip robustness, mixed-body/gate) + version pin; full `test_graph_indexer` green (508). Real corpus (~90 routines, operator-supplied): recovery PRECISE (no mis-binds, verified in isolation) but incremental delta ~0 (the walk already recovers structured bodies; the strip's value is the tight inline-query-FOR shape only). Surfaced a pre-existing baseline `read skip` phantom from `FOR UPDATE SKIP LOCKED` (out of 1rs45 scope — follow-up).; Recover in-loop DML from PL/pgSQL control-flow bodies: **Prepare-council security-reviewer (rotating seat) — mixed-body gap folded in.** The seat found the loop-gating narrative treats the partial-body population as binary but it is ternary: a MIXED body (`FOR…LOOP` + sibling `IF…INSERT…END IF`) has the `\bLOOP\b` gate fire for the whole body, routing IF-branch DML that `walk_reads` recovers today through strip-reparse with the walk suppressed — an under-capture regression risk no fixture pinned. Added a mixed loop+branch no-regression fixture to AC-4, a MIXED-body caveat to R4, and softened the "never wrong-bind" risk claim (a mis-located `LOOP` splice yields clean-but-wrong, not ambiguous).; Remove stale tomllib import fallbacks: Implemented: `secrets_validators.py` + `render_agent_surfaces.py` direct imports, `_require_tomllib()` + all `is None`/`is not None` guards removed; `test_secrets_validators.py` direct import + 7 dead guards dropped; repo-wide sweep clean.

**Changes delivered:**

- **Recover in-loop DML from PL/pgSQL control-flow bodies** (`1rs45-enh sql-plpgsql-loop-body-dml-recovery`) — 6 ACs completed. Key decisions: Split from `1rrx5` into its own change.; **Recovery mechanism = Approach B (strip loop scaffolding, reparse the body through the existing statement unit).**
- **Remove stale tomllib import fallbacks** (`1rqh2-debt remove-tomllib-import-fallback`) — 4 ACs completed. Key decisions: Track as a tech-debt change rather than fixing inline immediately
## Journal Watchpoints

- **BLOCKING pre-implementation for `1rs45`:** the recovery MECHANISM decision is OPEN (Decision Log) — line-anchored DML regex over masked ERROR text vs. body-text re-parse after stripping `FOR…LOOP`/`END LOOP` scaffolding — and must be settled (spike if needed) before implementation; the choice sets `1rs45`'s true size and its faithfulness surface. `1rs45` also carries a mandatory adversarial-faithfulness review lane (new DML-recovery vocabulary + a new regex-scanner CTE exclusion = a new detection surface) and requires a `GRAPH_BUILDER_VERSION` bump (extraction-output change) — coordinate merge order with any other wave touching `graph_indexer.py`'s SQL region (`1p9q8` landed; the SQL extractor is otherwise idle).
- `1rqh2` is a bounded debt cleanup (no behavior change under the ADR's ≥3.11 guarantee); its risk is only test-file fallback imports that intentionally exercise version compatibility — call those out rather than blind-strip. No version bump, no faithfulness surface.
- The two changes are DISJOINT (`graph_indexer.py` SQL recovery tier vs. `secrets_validators.py`/`render_agent_surfaces.py` tomllib imports) — implement in parallel; no shared serialization point.
- DELIBERATELY EXCLUDED (operator direction 2026-07-06): `1rtar-task spike-embedded-sql-strict-validity-gate` is held — NOT admitted to this wave. Also still out: the in-doc follow-up NOTES not yet minted as plans — the `_source_location` splitlines-per-symbol perf hotspot (recorded in the `1p9q7` change doc) and the `1p9q5` candidate-index-collapse relaxation that would activate the zero-delta Rust disambiguation tier (recorded in the `1p9q5`/`1p9q8` records). If the operator wants those in a wave, mint plans and admit them.

## Participants

- implementer — `1rs45` in `.wavefoundry/framework/scripts/graph_indexer.py` (SQL recovery tier); `1rqh2` in `secrets_validators.py` + `render_agent_surfaces.py`
- code-reviewer — both changes
- qa-reviewer — `1rs45` exact-set recovery tests + faithfulness fixtures; `1rqh2` import-path regression
- security-reviewer — `1rs45` mandatory adversarial-faithfulness lane (recovery detection surface); `1rqh2` no trust-boundary impact
- red-team, reality-checker, senior-engineering-challenger — council seats
- performance-reviewer — `1rs45` recovery-scan cost (bounded, ERROR-region-gated)

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-06: PASS WITH NOTES** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker/spike, qa-reviewer, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the loop-bearing gate reads as a clean binary but the partial-body population is TERNARY — a MIXED body holding both a `FOR…LOOP` and a sibling non-loop IF-block INSERT has the loop-word gate fire for the whole body, routing the IF-branch DML that `walk_reads` recovers today through strip-reparse with the normal walk suppressed, so recovery now rides on the reparse unit's statement-dispatch re-firing and no fixture pinned that shape → resolved by a mixed loop+branch no-regression fixture folded into AC-4 and a MIXED-body caveat in R4; strongest-alternative: none advanced — seats endorsed Approach B as designed once the mixed-body fixture was added; notes: the never-wrong-bind claim was softened for the mis-located-LOOP splice case and 1rqh2 is provably inert under Python 3.11+)

- **Delivery-phase Wave Council [delivery-council] — 2026-07-06: PASS WITH NOTES** (moderator: wave-council; primer-depth: standard; seats: adversarial-faithfulness, code-reviewer, performance-reviewer; rotating-seat: adversarial-faithfulness; strongest-challenge: could the loop-strip mint a wrong `reads`/`writes` edge or silently drop a walk-recovered ref — 18 adversarial probes could NOT force a wrong-bind, wrong-direction, wrong-owner, phantom external, or drop; the augment-with-dedup design is a strict superset of the walk baseline by construction so no walk-found ref can vanish; strongest-alternative: none advanced — one fix-now (gate the strip on `recover` for an explicit one-level contract) applied and re-verified; notes: the real-corpus incremental recall delta over the 1p9qi baseline is ~zero because realistic structured loop bodies already recover via the walk + 1p9qe tier, so the shipped value is a correct+zero-risk recovery for the tight inline-query-FOR shape plus the honest `sql_partial_bodies_recovered` loudness split — recorded for operator disposition)

## Review Evidence

- wave-council-delivery: approved 2026-07-06 — PASS WITH NOTES. `1rs45`: adversarial-faithfulness (mandatory, the strip is a new detection surface) found no wrong binds and no drops across 18 probes; the code/performance lane confirmed bounded cost + a correct dedup floor and drove one fix-now (explicit `recover` gate, re-verified). Full framework suite green (4665 tests); `GRAPH_BUILDER_VERSION` 40→41; no `CLUSTER_BUILDER_VERSION` bump (projection unchanged). Honest outcome recorded: the strip is correct and zero-risk but adds ~zero incremental recall on the operator's real corpus (the walk already covers structured bodies) — durable-but-narrow-delta, for operator disposition. `1rqh2`: dead-code cleanup verified behavior-preserving under the ≥3.11 floor. No product-owner acknowledgment required (framework-internal accuracy work).
- wave-council-readiness: approved 2026-07-06 — READY. Two independent carryover follow-ups; both docs technically ready (lint clean, garden clean, single-OPEN slot free). The hard pre-implementation gate for `1rs45` (recovery mechanism) is SETTLED via the 2026-07-06 spike (Approach B: strip loop scaffolding, reparse through the existing statement unit — zero new DML/CTE vocabulary). All seat notes resolved in-doc. No product-owner acknowledgment required (framework-internal accuracy work).
- red-team (readiness): reframed `1rs45` against a live baseline probe (only the inline-query-FOR shape drops its post-`LOOP` DML; the other headers already recover via `walk_reads`) and drove the loop-bearing gating decision.
- reality-checker/spike (readiness): confirmed the recovery-mechanism gate settled via the 11-probe spike (Approach B) and the `1rqh2` ADR-`12tm5` ≥3.11 premise.
- security-reviewer (readiness, rotating): added the mixed-body no-regression fixture requirement (AC-4) and softened the "never wrong-bind" claim for the mis-located-`LOOP` splice case.
- qa-reviewer (readiness): corrected `1rqh2` scope to the single test file that actually carries the fallback and named the downstream dead-path deletions; flagged the stale "(Populated at Prepare wave.)" boilerplate (removed).
- operator-signoff: pending operator confirmation at closure

## Dependencies

- No external wave dependencies. `1rs45` builds on the landed `1p9qe`/`1rs44` SQL recovery tier + `sql_partial_bodies` signal; `1rqh2` builds on ADR `12tm5`.
