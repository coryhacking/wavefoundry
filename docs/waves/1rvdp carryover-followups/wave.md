# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-06

wave-id: `1rvdp carryover-followups`
Title: Carryover Followups

## Objective

Gather the discrete, recorded carryover follow-ups from prior closed waves into one wave so they are tracked and admittable rather than dangling as plan docs: the PL/pgSQL loop-body DML recovery split out of `1rs44` at readiness, and the ADR-aligned removal of the pre-3.11 `tomllib` import fallbacks flagged during the `1p9pe` review. When this wave closes, both carryover items are resolved and the follow-up backlog is drained (except the deliberately-held `1rtar` spike).

## Changes

Change ID: `1rs45-enh sql-plpgsql-loop-body-dml-recovery`
Change Status: `planned`

Change ID: `1rqh2-debt remove-tomllib-import-fallback`
Change Status: `planned`

## Wave Summary

Two INDEPENDENT carryover follow-ups batched by operator direction: `1rs45` recovers in-loop DML writes from PL/pgSQL control-flow routine bodies (nested-in-body ERROR regions tree-sitter-sql can't parse — the under-capture `1p9qi`/`1rs44` recorded and `sql_partial_bodies` already flags); `1rqh2` removes the now-dead `tomllib`→`tomli`→`None` import fallbacks in `secrets_validators.py` and `render_agent_surfaces.py` per ADR `12tm5` (Python ≥3.11 guarantees `tomllib`). The two changes touch disjoint code and can proceed in parallel.

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

## Review Evidence

- operator-signoff: pending operator confirmation at closure

## Dependencies

- No external wave dependencies. `1rs45` builds on the landed `1p9qe`/`1rs44` SQL recovery tier + `sql_partial_bodies` signal; `1rqh2` builds on ADR `12tm5`.
