# Retrieval-Posture Loop: Full Activation Coverage and Honest Counting

Change ID: `1t67p-enh posture-loop-full-coverage`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

Wave 1t72b was implemented with exactly one implement-stage tool call, and the
1t230 feedback loop never engaged — the operator caught it, not the framework.
Two structural holes, both live-demonstrated on this wave: (1) the in-band
retrieval-posture directive is served only by `wf_implement_wave`, but a wave
can be activated through `wf_prepare_wave(mode='create')` (prepare-and-open)
or `wf_reopen_wave`, which serve nothing; (2) the posture-gap sensor counts
`event_kind='retrieval'` rows, and since the 1t3s7 full-surface wrapper every
first-party call records such a row — one incidental `wf_sync_surfaces` probe
made the count 1 > the max_calls=0 threshold and silenced the sensor while
zero code-retrieval calls had happened.

## Requirements

1. **Directive on every activation path**: `wf_prepare_wave(mode='create')`
   (the prepare-and-open flip) and `wf_reopen_wave` include the same
   `retrieval_posture` directive block in their response data that
   `wf_implement_wave` serves, sourced from the single existing constant —
   no duplicated text. Readiness-only modes (`dry_run`, `ready`) do not serve
   it (they do not open the wave). Operator extension (2026-07-20): the
   directive text covers implementation AND review retrieval, and
   `wf_review_wave` serves it in-band too — review work (verifying claims
   against the tree) is retrieval work.
2. **Sensor counts code retrieval only**: the posture-gap count is restricted
   to the code-retrieval census (`_CONTEXT_RETRIEVAL_TOOLS`: the `code_*`
   tools + `docs_search`), so incidental wrapped lifecycle/audit calls can
   never mask the drift. The review telemetry summary keeps reporting the
   overall stage totals; only the sensor's gap decision uses the filtered
   count.
3. Threshold semantics (`max_calls`, `min_files`, workflow-config override
   path) are unchanged.

## Scope

**Problem statement:** the posture feedback loop has activation-path and
counting blind spots, both demonstrated live on wave 1t72b.

**In scope:**

- The directive block in the two additional activation responses
- The filtered count in the sensor path (and its read helper)
- Hermetic tests for both

**Out of scope:**

- Directive in readiness-only responses
- Threshold default changes
- Any new sensor

## Acceptance Criteria

- [x] AC-1: `wf_prepare_wave(mode='create')` and `wf_reopen_wave` responses
      carry the retrieval-posture directive sourced from the shared constant;
      `dry_run`/`ready` responses do not; verified by test. Extended by
      operator direction: the directive names implementation AND review, and
      `wf_review_wave` serves it in-band (source-census test).
- [x] AC-2: The sensor's gap decision counts only code-retrieval census tools:
      a stage whose only retrieval rows are non-census calls (e.g.
      `wf_sync_surfaces`) counts 0 and fires the gap on a qualifying
      footprint, verified by test reproducing the 1t72b masking scenario.
- [x] AC-3: A stage with census calls above the threshold stays silent
      (existing behavior preserved), verified by test.
- [x] AC-4: Full framework test suite passes (6,041 tests across 56 files, OK, 2026-07-20).

## Tasks

- [x] Serve the directive from the shared constant on both activation paths
- [x] Filter the sensor count to the code-retrieval census
- [x] Hermetic tests per AC (including the live-demonstrated masking scenario)
- [x] Run full framework test suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| posture    | Engineering | —          | server_impl.py + context_efficiency.py read helper |


## Serialization Points

- `server_impl.py` is shared with the 1t727 TOCTOU repair in this wave;
  sequence edits.

## Affected Architecture Docs

`docs/references/context-efficiency.md` (posture sensor counting note). `N/A`
otherwise.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The live-demonstrated activation bypass |
| AC-2 | required | The live-demonstrated masking |
| AC-3 | required | No new advisory noise |
| AC-4 | required | Suite-green delivery gate |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | The gap DECISION counts only the code-retrieval census; the telemetry summary keeps unfiltered totals | The sensor's question is "did code exploration route through retrieval," and lifecycle traffic answers a different question — an all-tools count is vacuously satisfied by any normally-run wave (operator asked; live-demonstrated on 1t72b) | Count all tools (rejected: permanently silent); separate second counter in the summary (rejected: the summary already shows stage totals) |
| 2026-07-20 | `implement_stage_retrieval_calls` gains an optional `tool_names` filter rather than a second function | One read path, summary callers pass nothing and keep prior behavior | Hardcode the census in the reader (rejected: context_efficiency must not import server_impl) |
| 2026-07-20 | The directive covers review retrieval and `wf_review_wave` serves it in-band on both phases (operator extension) | Review work is retrieval work: prepare-phase reviewers verify plans against the tree, implementation-phase reviewers verify delivery claims — the same MCP-first discipline applies and the reminder belongs at the entry point of that work | Review-only variant text (rejected: one constant, no drift); implement-phase-only serving (rejected: prepare-phase plan verification reads code too) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Directive block bloats every prepare response | Served only on the mode='create' open path, from the shared constant |
| Census drift (new code tools not counted) | The filter references `_CONTEXT_RETRIEVAL_TOOLS` itself, which the registration census test already pins |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
