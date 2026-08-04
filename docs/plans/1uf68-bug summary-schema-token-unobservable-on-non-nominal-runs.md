# The Summary Schema Token Is Unobservable on Exactly the Runs That Deviate

Change ID: `1uf68-bug summary-schema-token-unobservable-on-non-nominal-runs`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-04
Wave: TBD

## Rationale

Target-repo field report (2026-08-04): the delegation's field proof is positively closed
(three consecutive post-transition runs reported `summary_schema_version: 1` unmarked, zero
degradation markers anywhere), with one structural caveat verified in this tree: the token is
phase-scoped. `_emit_primary_summary_via_delegate_or_fallback` has exactly ONE call site
(`upgrade_wavefoundry.py:4924`, the nominal primary-phase completion), and `phase_cleanup`
(:2432) builds its summary through `_build_upgrade_summary`/`_emit_summary_line` without the
token. A run that takes any non-nominal path through the primary phase (the memory checkpoint
pause, exit 4, is the common one) emits no token-bearing summary at all: its only summary
comes from cleanup, schema-absent. Field-observed on the pgt9 run: `schema=<ABSENT>,
degraded=<absent>`.

Absent and degraded are different states and only one is marked. The drift tripwire is
therefore unobservable precisely on the runs that deviated, which are the runs most worth
having a tripwire for.

## Requirements

1. **Every sentinel-emitting summary carries the schema token:** the cleanup-phase summary
   includes `summary_schema_version` (and the degradation marker when its producer degraded),
   so no completed upgrade path yields a token-less summary. Prepare decides whether the
   checkpoint-paused primary phase should ALSO emit its summary before pausing, or whether
   token-on-cleanup alone closes the observability gap (simplicity constraint: implement the
   minimal sufficient mechanism, not both, unless the first provably cannot cover a path).
2. **Red-first on the reported path:** a test drives the checkpoint-pause flow (exit 4) plus
   cleanup and asserts the run's summary carries the token; it fails on the current tree.
3. **Contract tests extend, not fork:** the existing `DelegatedSummaryContractTests` family
   gains the cleanup-carrier pin; no new schema key, no token value change, no new test module.
4. **Consumers unaffected:** the server-side parse remains passthrough (the key is not a
   terminal key and the server never inspects it); pin that the bounded response still carries
   the token from a cleanup summary.

## Scope

**Problem statement:** the schema token is emitted only on the nominal primary-phase path, so
deviating runs produce summaries where drift and absence are indistinguishable.

**In scope:** the cleanup summary build (`_build_upgrade_summary`/`_emit_summary_line` and
`phase_cleanup`), optionally the checkpoint-pause emission point per the Prepare decision;
`test_upgrade_wavefoundry.py` delegation clusters.

**Out of scope:** the token value and recognized set; the primary-phase delegation mechanics
(field-proven); `summary_source_degraded` semantics.

## Acceptance Criteria

- [ ] AC-1: A checkpoint-paused run's overall summary output carries `summary_schema_version`
  (red-first).
- [ ] AC-2: Nominal-path behavior is unchanged and pinned (primary summary token as today).
- [ ] AC-3: The Prepare-time mechanism decision is recorded with rationale; only the chosen
  mechanism is implemented.
- [ ] AC-4: Delegation clusters and full suite pass.

## Tasks

- [ ] Red-first checkpoint-pause test
- [ ] Prepare decision (cleanup-carries-token vs emit-before-pause); implement it
- [ ] Extend the contract tests; full suite
- [ ] CHANGELOG bullet (current unreleased section)

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          |       |


## Serialization Points

- `upgrade_wavefoundry.py` and `test_upgrade_wavefoundry.py`

## Affected Architecture Docs

Candidates at Prepare: `docs/architecture/decisions/1u49j-adr fresh-code-summary-producer-contract.md`
(the token's carrier set widens); CHANGELOG.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | TBD      |           |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-04 | Filed from the target-repo field report that positively closed the rename's second-half proof (three consecutive unmarked summary_schema_version: 1 runs) and surfaced this gap; single-call-site claim verified via code_keyword (:4924 sole caller; phase_cleanup path token-less). | Field report 2026-08-04 (pgt9 run: schema absent, degraded absent); code census this session |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Old parents parsing a token-bearing cleanup summary | The parent re-emits and parses payloads passthrough; the token is additive on an existing summary shape and the server never inspects it; AC-4 pins the bounded response |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
