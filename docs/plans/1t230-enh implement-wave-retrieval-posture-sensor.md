# Implement Wave Retrieval-Posture Sensor

Change ID: `1t230-enh implement-wave-retrieval-posture-sensor`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

The framework's MCP-first retrieval posture for implementation is currently
feedforward-only: the implement-wave prompt carries an "MCP-first code exploration"
guardrail and a `Gapfill:` note requirement, and the seeds carry the retrieval order. It
has now failed twice in practice: wave `1sufq` (2026-07-18) and wave `1t3gt` (2026-07-20)
were both implemented almost entirely through harness file tools, leaving the
implement-stage Context Efficiency telemetry at or near zero while the waves produced
large code diffs. Both times the operator, not the framework, noticed.

Per the framework's own philosophy (feedforward seeds plus feedback sensors), an
instruction that keeps failing needs a sensor. The `1stwj` telemetry now provides the
signal: instrumented retrieval calls (`code_*`, `docs_search`) recorded under the
`implement` stage. This change closes the loop in three places: the directive arrives
in-band at activation, the number is visible at review, and a deterministic gap check
demands an explanation when retrieval is near zero against a non-trivial code diff.

The gate is "explain or fix", not "forbid": legitimate near-zero cases exist (bulk
mechanical renames, docs-only changes), so the sensor emits an advisory that must be
dispositioned, never a hard block on its own.

## Requirements

1. **In-band feedforward:** the successful `wf_implement_wave` activation response gains a
   `retrieval_posture` field carrying the MCP-first directive (search/read/navigate via
   `code_*`/`docs_search` first; harness shell/file tools are fallback). The field must be
   self-contained: it explicitly names the escape hatch alongside the rule — when fallback
   is the right instrument (bulk-mechanical edits, docs-only work), record a `Gapfill:`
   entry in the Progress Log explaining why, and that same entry is what clears the
   `retrieval_posture_gap` advisory at review/close. An implementing agent reading only
   the envelope knows the rule, the escape hatch, and the consequence, without opening
   any prompt doc. Wording sourced from the existing implement-wave prompt guardrail,
   stated inline without referencing wavefoundry-internal artifact IDs.
2. **Sensor:** `wf_review_wave(phase='implementation')` and `wf_close_wave(mode='dry_run')`
   compute a retrieval-posture gap check: implement-stage instrumented retrieval call
   count from the context-efficiency store versus the wave's code footprint (count of
   tracked files changed under code roots since wave activation, derived without network
   access). When retrieval calls are near zero and the footprint is non-trivial
   (thresholds configurable via `workflow-config.json` with conservative defaults), the
   response carries a `retrieval_posture_gap` advisory diagnostic naming both numbers.
3. **Disposition path:** the advisory clears when the wave record (Progress Log or
   Decision Log of any admitted change, or wave.md) contains a `Gapfill:` entry
   explaining the fallback. The advisory is non-blocking at review; at close it follows
   the standing advisory pattern (surfaced, never a hard block by itself).
4. **Visibility:** the `wf_review_wave(phase='implementation')` response includes an
   `implement_stage_telemetry` summary (calls, request/response debits, estimated
   savings) so the delivery council reads the number in context. Depends on the
   review-boundary checkpoint flush (`1t22z`) for the wave.md table itself; this field is
   response-envelope data and works independently.
5. No change to what is measured: the sensor consumes existing store data; it records
   nothing new.

## Requirements

1. [Numbered behavioral requirement — specific enough for an implementer to act on unambiguously]
2. …

## Scope

**Problem statement:** MCP-first implementation retrieval is prompt-guidance only;
violations are invisible until an operator inspects telemetry after the fact, and it has
failed twice in three days.

**In scope:**

- `retrieval_posture` field on the `wf_implement_wave` activation response
- Gap computation + `retrieval_posture_gap` advisory at implementation-phase review and
  close dry-run, with configurable thresholds
- `Gapfill:` disposition detection
- `implement_stage_telemetry` summary in the implementation-phase review response
- Tests for each; docs updates (implement-wave prompt/seed wording pointing at the
  in-band field, `docs/references/context-efficiency.md` sensor note)

**Out of scope:**

- Hard-blocking enforcement or hooks intercepting harness tools (habit-level prevention
  is not enforceable at the framework layer without breaking legitimate bulk-mechanical
  work)
- Changing what telemetry is recorded
- The review-boundary wave.md checkpoint flush (separate change `1t22z`)

## Acceptance Criteria

- [ ] AC-1: Successful activation responses carry `retrieval_posture` with the MCP-first
      directive, the explicit `Gapfill:` disposition convention, and the advisory it
      clears, verified by test asserting all three elements are present in the field.
- [ ] AC-2: A wave with near-zero implement-stage retrieval calls and a non-trivial code
      footprint receives the `retrieval_posture_gap` advisory (with both numbers) at
      implementation-phase review and at close dry-run, verified by hermetic test.
- [ ] AC-3: A recorded `Gapfill:` entry clears the advisory; a wave with healthy
      retrieval or a trivial footprint never receives it, verified by test.
- [ ] AC-4: The implementation-phase review response includes the
      `implement_stage_telemetry` summary, verified by test.
- [ ] AC-5: Thresholds are configurable via `workflow-config.json`; defaults documented;
      docs-lint passes.
- [ ] AC-6: Full framework test suite passes
      (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Tasks

- [ ] Add `retrieval_posture` to the activation response
- [ ] Implement the gap computation (store query + code-footprint census) and the
      advisory with configurable thresholds
- [ ] Implement `Gapfill:` disposition detection over the wave record and admitted
      change docs
- [ ] Add `implement_stage_telemetry` to the implementation-phase review response
- [ ] Update implement-wave prompt/seed wording and `docs/references/context-efficiency.md`
- [ ] Add hermetic tests for AC-1 through AC-5
- [ ] Run full framework test suite

## Agent Execution Graph


| Workstream       | Owner       | Depends On | Notes |
| ---------------- | ----------- | ---------- | ----- |
| posture-sensor   | Engineering | —          | `server_impl.py` + `context_efficiency.py` read path + tests |


## Serialization Points

- Touches `server_impl.py` (activation/review/close call sites); if admitted alongside
  `1t22z` (same wave), sequence the two `server_impl.py` edits. `1t22z` landing first is
  preferred so review-time wave.md numbers and the envelope summary agree.

## Affected Architecture Docs

`docs/references/context-efficiency.md` gains the sensor note (tracked in Tasks). `N/A`
for the architecture hub docs: a new advisory on existing lifecycle responses, no new
component or flow.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | TBD      | Populated at Prepare wave. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Advisory noise on legitimate bulk-mechanical waves erodes trust in the sensor | Conservative default thresholds; `Gapfill:` disposition clears it; advisory-only, never blocking by itself |
| Code-footprint census depends on git state in ways hermetic tests cannot reproduce | Footprint derivation gets a seam (injectable file-list provider) so hermetic tests drive it without a real git history |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
