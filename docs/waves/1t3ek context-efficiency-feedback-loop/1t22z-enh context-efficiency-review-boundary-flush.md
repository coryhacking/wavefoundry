# Context Efficiency Review-Boundary Checkpoint Flush

Change ID: `1t22z-enh context-efficiency-review-boundary-flush`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

The wave.md Context Efficiency checkpoint is republished only at the mutating lifecycle
boundaries: `wf_create_wave`, `wf_prepare_wave`, `wf_implement_wave` (activation), and
`wf_close_wave` (which also seals and compacts). `wf_review_wave` is observational and passes
`flush=False` through `_lifecycle_context_result`, so it moves the focus to `review` without
publishing.

The consequence, observed directly on wave `1t3gt` (2026-07-20): the entire implementation
period accumulates live in the SQLite write-through store, but the wave.md table stays frozen
at activation time. The delivery-phase council therefore reviews a wave record whose
Context Efficiency table shows only the activation call for the `implement` stage, and the
implementation numbers first become visible at close, after the review that should have read
them.

The fix makes the flush symmetric with the three-stage model (change `1t3ld`): each stage's
accumulated numbers are published at the boundary where the next stage begins. Activation
publishes the `plan` totals; the implementation-phase review publishes the `implement`
totals; close publishes the `review` totals and seals.

## Requirements

1. `wf_review_wave(phase='implementation')` must publish the Context Efficiency checkpoint
   projection to `wave.md` (the same projection path the mutating boundaries use), while
   remaining observational with respect to wave lifecycle state: no status transition, no
   review-evidence mutation, no general-producer transfer, and no milestone prompt credit
   beyond what it grants today.
2. The prepare-phase review (`phase='prepare'`) is unchanged: it runs before implementation
   and the prepare boundary already publishes.
3. A review that could not run at all (wave not found, validation crash — no structured
   lane summary produced) must not publish. A review that RAN but reports pending
   signoffs (error status with `lane_results` present — the normal pre-close state)
   MUST still publish: that is precisely when the delivery council needs current
   numbers. Scope-discovery refinement of the original "error-status reviews do not
   publish" wording; see Decision Log.
4. The tool's `_OBSERVATIONAL_TOOL` MCP annotation stays. The checkpoint projection is
   accounting bookkeeping, not a wave-state mutation; the write it performs is the same
   marker-owned block rewrite every other boundary already performs. If the annotation
   contract is judged to forbid ANY file write, the alternative is a `flush` opt-in
   parameter defaulting true for `phase='implementation'`; decide at implementation with
   the reviewer and record the decision.
5. The published table reflects the three-stage model ordering and signed-sum invariants
   from `1t3ld`/`1sx2f` unchanged.

## Requirements

1. [Numbered behavioral requirement — specific enough for an implementer to act on unambiguously]
2. …

## Scope

**Problem statement:** Implementation-stage Context Efficiency numbers are invisible in
`wave.md` until close, because the review boundary moves focus without publishing; the
delivery council reads a stale activation-time table.

**In scope:**

- The `wf_review_wave` registration call site in `server_impl.py` (`_lifecycle_context_result`
  flush behavior for `phase='implementation'`)
- Test coverage: implementation-phase review publishes the checkpoint; prepare-phase review
  and failed reviews do not change behavior
- `docs/references/context-efficiency.md` boundary-publication wording

**Out of scope:**

- Any change to what is measured or how stages are bucketed (owned by `1t3ld`)
- Sealing/compaction semantics at close
- The retrieval-posture sensor (separate change `1t230-enh
  implement-wave-retrieval-posture-sensor`, which consumes the numbers this change makes
  visible at review time)

## Acceptance Criteria

- [x] AC-1: After instrumented implement-stage activity, `wf_review_wave(phase='implementation')`
      leaves the `wave.md` Context Efficiency table reflecting the implement-stage
      accumulation, verified by test.
- [x] AC-2: `wf_review_wave(phase='prepare')` does not publish, and a review that fails
      to run (no structured lane summary) does not publish; a review that ran with
      pending signoffs does, verified by test.
- [x] AC-3: The review publish performs no wave-state mutation: status, review evidence,
      and general-producer buckets are byte-identical before and after, verified by test.
- [x] AC-4: `docs/references/context-efficiency.md` documents the symmetric
      boundary-publication model; docs-lint passes.
- [x] AC-5: Full framework test suite passes
      (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Tasks

- [x] Enable checkpoint publication on successful `wf_review_wave(phase='implementation')`
      via `_lifecycle_context_result`, preserving observational wave-state semantics
- [x] Decide and record (Decision Log) whether the observational annotation permits the
      projection write or a `flush` parameter is needed
- [x] Add tests: implementation-review publishes; prepare/error reviews do not; no
      state mutation beyond the checkpoint block
- [x] Update `docs/references/context-efficiency.md`
- [x] Run full framework test suite

## Agent Execution Graph


| Workstream     | Owner       | Depends On | Notes |
| -------------- | ----------- | ---------- | ----- |
| review-flush   | Engineering | —          | Single small workstream in `server_impl.py` plus tests |


## Serialization Points

- Touches the `wf_review_wave` call site in `server_impl.py`; if admitted alongside
  `1t230` (same wave), sequence the two `server_impl.py` edits.

## Affected Architecture Docs

`docs/references/context-efficiency.md` (subsystem reference), tracked in Tasks. `N/A` for
the architecture hub docs: publication timing changes, not data flow or component
boundaries.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The observed defect: implement numbers invisible to the delivery council until close |
| AC-2 | required  | Prepare-phase and failure behavior must not change; regression there breaks existing flows |
| AC-3 | required  | The tool's observational contract is load-bearing; any state mutation beyond the checkpoint block is a new defect class |
| AC-4 | important | Reference-doc accuracy; behavior is test-verified independently |
| AC-5 | required  | Suite-green is the delivery gate for all framework script changes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Requirement 4 resolved: keep the `_OBSERVATIONAL_TOOL` annotation unchanged and publish without a `flush` parameter — the annotation already declares `readOnlyHint: False`, so the checkpoint-block write is annotation-compatible. | Verified in `register_mcp_surface`'s annotation constants; observational means "no wave-state mutation", not "no writes". | Explicit `flush` parameter (rejected: adds API surface for a contract the annotation already permits). |
| 2026-07-20 | AC-2/Requirement 3 refined: the publish boundary is "review ran" (`reached_review`: structured lane summary present), not "status ok" — a review reporting pending operator signoff is the NORMAL pre-close state and is exactly when the council reads the table. | The original wording would have deferred publication to close in practice, defeating the change's purpose; discovered at implementation against the real `_lifecycle_context_result` error gating. | Publish only on fully-passing reviews (rejected: pre-close reviews nearly always carry a pending operator lane). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The projection write conflicts with the tool's observational annotation contract | Requirement 4 names the fallback (explicit `flush` parameter); decision recorded at implementation with the reviewer |
| Publishing at review could mask a store/projection divergence the close-time seal would have caught | AC-3 asserts the review publish is limited to the checkpoint block; close-time seal semantics untouched |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
