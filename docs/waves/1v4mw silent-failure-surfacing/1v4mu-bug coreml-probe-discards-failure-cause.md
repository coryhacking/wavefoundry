# CoreML Probe Discards Its Own Failure Cause

Change ID: `1v4mu-bug coreml-probe-discards-failure-cause`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-12
Wave: 1v4mw silent-failure-surfacing

## Rationale

`accel_embedder._coreml_static_probe_passes` runs the production static graph in a crash-isolated
child, captures the child's stderr into `completed.stderr`, and then inspects only `returncode`. The
captured cause is discarded. When the probe rejects CoreML, the resulting warning names no reason and
the degradation to CPU is otherwise silent.

Field-reported cost: a full reverse-engineering session, and the root cause is **still unknown**
because the condition stopped reproducing before it could be instrumented. Logging the return code
plus a stderr tail would have made it a thirty-second diagnosis.

The probe exists because CoreML can fail natively during session construction, beyond Python
exception handling. That design is sound. The gap is that the one place holding the evidence throws
it away.

Companion, same report: the deliberate small-batch CPU routing message reads like a fault when it
appears near the GPU degradation warning. The reporter conflated the two themselves. These are
distinct conditions, one an optimization and one a failure, and should not read alike.

## Requirements

1. When the probe rejects CoreML, the emitted warning carries the child's return code and enough of
   its stderr to identify the cause.
2. Output stays bounded: a stderr tail, not an unbounded dump.
3. No absolute filesystem paths leak into the message, consistent with the path-free diagnostic
   convention this codebase already follows elsewhere.
4. The deliberate small-batch CPU routing message is distinguishable from a degradation warning.

## Scope

**Problem statement:** the probe captures the evidence for its own decision and discards it, so a
CoreML rejection is undiagnosable after the fact.

**In scope:**

- Including return code and a bounded stderr tail in the probe's rejection warning.
- Wording the small-batch routing message so it does not read as a fault.

**Out of scope:**

- Changing what the probe decides, or when it runs. Only its reporting changes.
- The embedder and reranker precision ladders.
- Chasing the underlying CoreML failure itself; it no longer reproduces, which is exactly why the
  logging is the deliverable.

## Acceptance Criteria

- [x] AC-1: A probe rejection emits the child's return code and a bounded stderr tail; asserted with a fake child that fails with known stderr.
- [x] AC-2: The tail is length-bounded, asserted with oversized child output.
- [x] AC-3: No absolute filesystem path appears in the message.
- [x] AC-4: A passing probe emits no new output, so healthy runs stay quiet.
- [x] AC-5: The small-batch routing message states it is a deliberate optimization, not a failure.

## Tasks

- [x] Add return code and bounded stderr tail to the rejection warning.
- [x] Confirm the message is path-free.
- [x] Reword the small-batch routing message.
- [x] Tests for reject-with-stderr, oversized-stderr truncation, and silent-on-pass.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| logging | implementer | — | Bounded tail; path-free; quiet when healthy. |
| wording | implementer | — | Small-batch routing message; independent of the logging change. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_accel_embedder.py`

## Affected Architecture Docs

`N/A`. Diagnostic output only; no boundary, contract, or flow changes.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect: the cause is captured and discarded. |
| AC-2 | required | An unbounded dump into a warning path is its own problem. |
| AC-3 | required | The codebase closed this leak class deliberately; do not reopen it. |
| AC-4 | required | Healthy runs must not gain noise. |
| AC-5 | important | Reduces a conflation the reporter actually made, but not a correctness issue. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-12 | Filed from downstream upgrade feedback. The probe captures `completed.stderr` and branches only on `returncode`; the underlying CoreML failure no longer reproduces, so improved reporting is the deliverable rather than a root-cause fix. | Field report; `accel_embedder._coreml_static_probe_passes`. |
| 2026-08-12 | Implemented as `_probe_failure_detail(returncode, stderr)`: return code plus a 600-character scrubbed TAIL, appended to the existing warning as `Cause: ...`. The tail rather than the head, because the terminating exception is what names the cause. Path scrubbing collapses absolute POSIX and Windows paths to their basename, which keeps a traceback readable without publishing the operator's filesystem layout. ASCII truncation marker, since this text reaches non-UTF-8 Windows consoles. | `accel_embedder.py` `_probe_failure_detail` / `_coreml_static_probe_passes`; five tests in `test_accel_embedder.AccelEmbedderTests`; suite 49/49 in that file. |
| 2026-08-12 | Found and closed an unlisted leak on the same code path: the `except Exception` arm previously recorded no cause at all, and the obvious repair (`str(exc)`) would have been worse than silence. A `subprocess.TimeoutExpired`'s `str` embeds the command, and the command embeds the entire probe source. The arm names the exception CLASS only, which still distinguishes a timeout from an OS error. | `test_probe_rejection_names_the_class_when_the_child_never_completes` asserts the sentinel probe-source token is absent from the message. |
| 2026-08-12 | Delivery review found one defect, repaired in session: the path scrubber's regex matched a bare `/` anywhere in the text, so ordinary prose was mangled. `RuntimeError: GPU/CPU parity failed` scrubbed to `GPUCPU parity failed`, and `N/A` to `NA`, degrading exactly the diagnostic AC-1 exists to make readable. The pattern now requires the path to START a token via a lookbehind, which still matches the quoted and space-preceded forms a traceback uses. | `_ABSOLUTE_PATH_RE`; `test_probe_rejection_keeps_prose_slashes`; the existing path-free test still passes, so the fix did not trade AC-3 for readability. |
| 2026-08-12 | AC-5: the small-batch message now leads with `OPTIMIZATION (not a failure)` and states that GPU use is unchanged for larger runs. The reporter conflated it with the adjacent CoreML degradation WARNING; the two conditions now read differently. | `indexer.py` small-run branch in `_get_embedder`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-12 | Ship the diagnostics, not a root-cause fix. | The failure stopped reproducing before it could be instrumented, so there is nothing to fix yet. Making the next occurrence a thirty-second diagnosis is the achievable and useful outcome. | Attempt to reproduce and fix the CoreML failure (rejected: not reproducible; would be speculative). Fail loudly instead of degrading (rejected: the crash-isolated degrade is the correct design and is why the host survives at all). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Child stderr could contain absolute paths, which the message must not leak. | AC-3 asserts it directly. |
| Extra output could add noise on healthy hosts. | AC-4 asserts silence when the probe passes. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
