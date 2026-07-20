# Context Efficiency Three-Stage Model

Change ID: `1t3ld-enh context-efficiency-three-stage-model`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

The Context Efficiency table in `wave.md` currently reports token accounting against a
seven-value stage vocabulary that leaks lifecycle-tool internals rather than telling the
operator a coherent story. Lifecycle tools stamp `plan` (`wave_create_wave`,
`server_impl.py:23009`), `prepare` (`wave_prepare`, `:23104`), `review` (`wave_review`,
`:23164`), `implement` (`wave_implement`, `:23338`), and `close` (`wave_close`, `:23418`);
`context_efficiency.py` adds two synthetic values: `general` (unattributed-focus fallback,
lines 1004/1017) and `pre-wave` (stamped onto adopted unattributed telemetry at wave
creation/preparation, lines 1415-1440). A single wave's table can therefore show rows like
`plan`, `pre-wave`, `prepare`, `close` whose boundaries are tool-implementation details, not
operator-meaningful phases.

Operator direction (2026-07-20): collapse to exactly three categories, `plan`, `implement`,
`review`; everything must land in one of the three.

## Requirements

1. The canonical stage vocabulary becomes exactly three values: `plan`, `implement`,
   `review`. New telemetry writes may not record any other stage value.
2. Lifecycle-tool stamping maps as: `wave_create_wave` and `wave_prepare` stamp `plan`;
   `wave_implement` stamps `implement`; `wave_review` and `wave_close` stamp `review`.
3. The adoption path for unattributed telemetry (`context_efficiency.py` general-producer
   adoption, currently stamping `phase_id='pre-wave', stage='pre-wave'`) stamps `plan`
   instead. The internal pre-adoption `general` bucket remains an internal holding state,
   not a displayed wave stage.
4. No migration code and no read-side legacy-mapping machinery (operator direction
   2026-07-20). Instead, a one-time manual cleanup pass re-buckets old stage rows in
   existing wave records into the three categories by hand; the code only ever knows the
   three canonical values.
5. The rendered Context Efficiency table in `wave.md` shows stage rows in fixed order
   `plan`, `implement`, `review` (stages with zero calls omitted, as today), plus the
   Total row. The signed per-stage display semantics from change `1sx2f` (stage rows sum
   to the total) are unchanged.
6. `docs/references/context-efficiency.md` and any seed or spec text naming the old stage
   vocabulary are updated to document the three-stage model.

## Scope

**Problem statement:** Context Efficiency stage rows expose a seven-value internal
vocabulary (`plan`, `pre-wave`, `prepare`, `implement`, `review`, `close`, plus the
internal `general` bucket) where the operator wants a three-phase story: plan, implement,
review.

**In scope:**

- Stage vocabulary constant + write-time canonicalization in `context_efficiency.py`
- The five lifecycle-tool `focus_stage` stamp sites in `server_impl.py`
- The adoption-path stamp (`pre-wave` to `plan`) in `context_efficiency.py`
- Fixed stage row order (`plan`, `implement`, `review`) in the rendered table
- Tests for write-time vocabulary and the adoption path
- `docs/references/context-efficiency.md` and related doc text

**Out of scope:**

- Migration code or read-side legacy mapping of any kind: the code never handles or
  recognizes the old stage names (history is handled once, by hand, per the manual
  cleanup task)
- Changing any credit/debit accounting semantics, floors, sealing, or paired-evaluation
  mechanics; this change only re-buckets which stage a measurement reports under
- The metric-key schema (`_STAGE_KEYS` in `context_efficiency.py:1520` names per-stage
  metric fields, not stage names, and is unchanged)

## Acceptance Criteria

- [x] AC-1: After this change, a full lifecycle pass (create, prepare, implement, review,
      close) produces telemetry whose stored stage values are only `plan`, `implement`,
      `review`, verified by test.
- [x] AC-2: Adopted unattributed telemetry lands in `plan` (no new `pre-wave` values are
      ever written), verified by test.
- [x] AC-3: The rendered table shows stage rows in fixed `plan`, `implement`, `review`
      order and the signed rows still sum to the total, verified by test.
- [x] AC-4: `docs/references/context-efficiency.md` documents the three-stage model;
      docs-lint passes.
- [x] AC-5: Full framework test suite passes
      (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Tasks

- [x] Define the canonical three-value stage vocabulary in `context_efficiency.py` and
      enforce it at write time
- [x] Update the five `focus_stage` stamp sites in `server_impl.py` (`prepare` to `plan`,
      `close` to `review`; others unchanged in value)
- [x] Update the adoption path to stamp `plan` instead of `pre-wave`
- [x] Fix stage row ordering to `plan`, `implement`, `review` in the rendered table
- [x] Update `docs/references/context-efficiency.md` and any seed/spec text naming old
      stage values
- [x] Manual one-time history cleanup: re-bucket old stage rows (`pre-wave`, `prepare`,
      `close`) in existing wave.md Context Efficiency tables and their checkpoint state
      into `plan`/`implement`/`review` by hand; no code path handles or recognizes the
      old names
- [x] Add tests: write-vocabulary and adoption path
- [x] Run full framework test suite

## Agent Execution Graph


| Workstream        | Owner       | Depends On | Notes |
| ----------------- | ----------- | ---------- | ----- |
| three-stage-model | Engineering | —          | Single workstream; `context_efficiency.py` plus five stamp sites in `server_impl.py` |


## Serialization Points

- This change edits `server_impl.py` (the five `focus_stage` stamp sites), which changes
  `1t3gs` and `1t3gu` in this wave also touch. Sequence all `server_impl.py`-touching
  changes; never run them concurrently.

## Affected Architecture Docs

`docs/references/context-efficiency.md` (the subsystem reference) requires the vocabulary
update, tracked in Tasks. `N/A` for `docs/architecture/*.md` hub docs: the accounting
data flow, storage substrate, and component boundaries are unchanged; only the stage
bucketing vocabulary and its projection change.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The operator-stated outcome: only three stage values may ever be written |
| AC-2 | required  | The adoption path is the one writer that does not go through lifecycle-tool stamping; missing it leaves `pre-wave` leaking back in |
| AC-3 | important | Display polish; the `1sx2f` signed-sum invariant is the part that must not regress |
| AC-4 | required  | The reference doc is the operator-facing contract for this subsystem |
| AC-5 | required  | Suite-green is the delivery gate for all framework script changes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Manual history cleanup executed as: one-time SQL canonicalization of the live store (telemetry_event/source_credit stage+phase_id: pre-wave/prepare to plan, close to review; 8 waves affected) plus re-rendering each affected wave.md checkpoint block through the canonical normalizer/renderer with merged stage sums. | The store feeds any future checkpoint republish of the open wave; leaving old values there would re-emit non-canonical rows. Rendering through ce._normalized_checkpoint_state/render_checkpoint_block keeps the 1sx2f signed-sum invariant instead of hand-editing tables. | Leave the store untouched (rejected: open-wave republish would resurrect pre-wave rows); read-side mapping code (rejected by operator direction) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The `1sx2f` signed-display reconciliation could regress with the reordered rows | AC-3 asserts stage rows still sum to the total |
| Three changes in this wave now touch `server_impl.py` | Serialization point recorded here and in the wave watchpoints; sequence, never parallelize |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
