# Bound index-build peak memory independent of corpus size

Change ID: `1p7iv-debt bound-index-build-peak-memory`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-23
Wave: `1p7ir index-build-robustness`

## Rationale

The 1.8.0 OOM reached ~14 GiB RSS for an 811-file repo on CPU. The buffer-default + sequential mitigations (`1p7it`) bring peak RSS down to a workable level, but **~14 GiB for 811 files is far higher than the working set should require** — it suggests memory accumulates with corpus size somewhere beyond the embed buffer (retained chunk text/objects, the model plus per-pass duplicates, un-released LanceDB write buffers, or per-file artifacts held across the build). This change is the root-cause follow-up to `1p7it`: profile where RSS scales and bound it so peak memory is a function of the buffer/model, not the file count.

## Requirements

1. **Profile the working set.** Instrument a build (the multi-module repro or a synthetic large corpus) to attribute RSS growth across the code pass — embed buffer vs retained chunks/artifacts vs model vs Lance write buffers — and identify what scales with file count.
2. **Bound peak memory to O(buffer + model), not O(corpus).** Release/stream the identified accumulator(s) so a 5,000-file repo peaks near the same RSS as an 800-file repo at the same `embed_buffer_chunks`.
3. **Regression guard.** A test (or measured CI check) asserts peak RSS does not scale materially with file count at a fixed buffer — so the accumulation can’t silently return.

## Scope

**Problem statement:** Build RSS scales with corpus size beyond the embed buffer; the mitigations cap the symptom but the underlying accumulation remains.

**In scope:**

- Memory profiling of the code (and docs) embedding pass.
- The fix to release/stream whatever accumulates (the profile decides exactly what).
- A peak-RSS-vs-file-count regression guard.

**Out of scope:**

- The buffer default / sequential degrade / loud failure (`1p7it`) — the mitigations this builds on.
- Health honesty (`1p7is`) and TLS (`1p7iu`).

## Acceptance Criteria

- [ ] AC-1: a memory profile attributes the code-pass RSS growth and names the accumulator(s) that scale with file count.
- [ ] AC-2: peak RSS at a fixed `embed_buffer_chunks` is bounded ~O(buffer + model) — a large corpus peaks near a small one (measured before/after).
- [ ] AC-3: a regression guard asserts peak RSS does not scale materially with file count at a fixed buffer.
- [ ] AC-4: no regression to index correctness/coverage (same nodes/edges/chunks as before the memory fix).
- [ ] AC-5: framework tests bytecode-free; `wave_validate` clean.

## Tasks

- [ ] Profile a code-pass build (repro / synthetic large corpus); attribute RSS growth.
- [ ] Release/stream the scaling accumulator(s) per the profile.
- [ ] Add the peak-RSS-vs-file-count regression guard.
- [ ] Verify index output unchanged (correctness/coverage).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                         |
| ---------- | ----------- | ---------- | --------------------------------------------- |
| profile    | reviewer    | —          | attribute RSS growth across the pass           |
| memory-fix | implementer | profile    | release/stream the scaling accumulator         |
| guard      | implementer | memory-fix | peak-RSS-vs-file-count regression check        |


## Serialization Points

- Builds on `1p7it` (shares the build/memory path) — sequence after `1p7it` lands so the profile measures against the mitigated baseline, and avoid double-implementing the same flush.

## Affected Architecture Docs

- **Update if present:** the indexing/build architecture doc — the peak-memory bound (O(buffer+model), not O(corpus)) as a stated contract. Confirm at Prepare.

## AC Priority

(Populated at Prepare wave — proposed below.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The profile scopes the fix — without it this is guesswork. |
| AC-2 | required  | The bound is the deliverable. |
| AC-3 | important | Regression guard so the accumulation can’t return. |
| AC-4 | required  | Memory fix must not change index output. |
| AC-5 | required  | Test-locked, bytecode-free. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-23 | Drafted from the 1.8.0 field report as the root-cause follow-up to `1p7it` (~14 GiB / 811 files is higher than the working set warrants). Profile-first; value-gates on a real before/after. | memory `project_field_feedback_1p8_oom_tls` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-23 | Profile-first, then bound | The ~14 GiB suggests an accumulator beyond the buffer; fixing blind risks the wrong target (the literal-edge lesson: measure before binding). | Assume it’s only the buffer — rejected: the mitigation already covers the buffer; this exists because that’s not the whole story. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The profile shows the buffer/concurrency *was* the whole story (no extra accumulator) | Then this change closes as confirmed-no-op with the profile recorded — `1p7it` already shipped the fix; honest outcome, not forced work. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
