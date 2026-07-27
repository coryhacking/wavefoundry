# A Failed Lifecycle Call Leaves Context-Efficiency Focus Stale And Says Nothing

Change ID: `1tmb3-bug failed-lifecycle-call-leaves-focus-stale-and-silent`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-26
Wave: `1to7k lifecycle-evidence-and-focus-integrity`

## Rationale

Context-efficiency credits attribute to the process focus wave. Focus moves only when a lifecycle
call succeeds. In `_lifecycle_context_result` (`server_impl.py`):

```python
core_succeeded = response.get("status") in {"ok", "dry_run"}
...
if (core_succeeded or reached_review) and focus_stage is not None and wave_md is not None:
    handler.telemetry.set_focus(wave_id, focus_stage, new_phase=bool(credit))
```

Not moving focus on a failed call is correct. A call that did not happen should not re-point
accounting, and the surrounding code was already hardened for a related hazard: a stale-code session
once focused a raw change ID string, producing a phantom wave key that made every later projection
refuse. The defect here is not the focus rule. It is that the caller is never told focus is now
pointing somewhere else.

Observed live in this repository on 2026-07-26. Wave `1tj0l` was blocked at its readiness gate.
`wf_prepare_wave(wave_id="1tj0l", mode="dry_run")` returned `status: "error"` carrying the single
diagnostic `missing_wave_council_signoff`, so `core_succeeded` was `False` and focus stayed on
`1tmb1`, an unrelated single-change documentation wave that happened to be the last wave successfully
created. Work performed on `1tj0l`'s change documents afterward credited `1tmb1`. The response gave
no indication of this. The operator noticed the symptom; the tool never reported it.

The consequence compounds with the blockage that causes it. A wave stuck at a gate is precisely the
wave being actively worked on, so the period of heaviest retrieval is exactly the period during which
that retrieval cannot be attributed to it. The longer the block lasts, the more of the wave's own work
lands elsewhere.

The framework already treats this as worth reporting in the one place someone hit it.
`wf_reopen_wave` emits a `focus_stage_not_applied` diagnostic when its
focus write fails:

> "The wave was reopened, but context-efficiency focus was NOT moved to '{focus_stage}': {focus_error}.
> Retrieval done now will be attributed to the previous stage."

That diagnostic exists because the problem was encountered on the reopen path and fixed there. The
identical consequence on the prepare path, and on every other lifecycle tool, is silent. This is a
coverage gap in an existing and already-endorsed idea, not a new proposal.

A supporting signal, offered as suggestive rather than as proof: at filing time `1tmb1` carried 58
recorded calls against `1tj0l`'s 38, despite representing a small fraction of the session's work.
Attribution history cannot be replayed to apportion this precisely, and this change does not try to.

## The sharper case: `ready_for_council_review` is an unmodelled third outcome

Observed later the same day, and stronger than the case above. `wf_prepare_wave(wave_id="1tj0l",
mode="ready")` returned `status: "ready_for_council_review"`: technical checks passed, and the wave
now needs its prepare-phase council before it can be readied. That status is neither `ok`/`dry_run`
nor an error. The focus condition models only those two classes, so it fell through to "not
successful" and focus did not move.

But the same call **did** publish durable state for the target wave. `1tj0l`'s `wave.md` checkpoint
went from 1 call / 981 tokens to 46 calls / 661,367 in that single call, while `wf_current_wave`
continued to report `focus.wave_id = "1tmb1"`. `1tmb1` then climbed from 58 calls to 72 as the
council review of `1tj0l` proceeded.

So one call treated the target wave as successful enough to write and publish its durable
accounting, and simultaneously not successful enough to attribute the work that immediately follows.
The two halves of the same tool call disagree about whether the wave was engaged.

The divergence may be defensible in principle: flushing publishes what is *already* attributed, while
focus governs what happens *next*, and a call that did not complete arguably should not claim future
work. But `ready_for_council_review` is not an incomplete call. It is the normal, expected state of a
wave that has passed its technical gates and is undergoing council review, which is a period of
concentrated retrieval about exactly that wave. This plan therefore preserves the existing projection
and makes the council-ready outcome move focus to its target; it does not generalize that narrow choice
into an equivalence between publication of past work and focus for future work.

## Requirements

1. When a lifecycle tool does not move focus, the response reports a best-effort **effective
   attribution destination**, computed with the same rules as telemetry commit: usable explicit focus
   first; a sealed focused wave routes to `general`; with no explicit focus, the unique OPEN-wave
   fallback is used when one exists, otherwise attribution is `general`/unattributed. A diagnostic is
   emitted when that effective destination is an unrelated wave, and names the raw focused wave only
   as observed state—not as a promise of where future credits land. An unresolved/invalid target does
   not echo an unresolved raw identifier as canonical state. A non-engaged operation uses diagnostic
   code `focus_target_not_engaged` and directs the caller to repair/retry that lifecycle call.
2. One shared focus-attempt/reporting primitive covers set and clear operations across the current
   focus consumers. It distinguishes
   `core_not_engaged` from `focus_write_failed`: both report focus not applied, but the former directs
   the caller to repair/retry the lifecycle operation while the latter preserves the already-successful
   lifecycle result, preserves the existing `focus_stage_not_applied` code, and directs a focus
   retry/next boundary. Diagnostic construction is observational
   and best-effort; it cannot overturn a successful lifecycle mutation.
   A mutating pause that succeeds calls the existing `clear_focus` operation; a dry-run pause does not
   attempt a clear. If `clear_focus` fails after a successful pause, the lifecycle result stays successful, prior focus
   remains, and the response carries the named write-failure diagnostic and retry guidance.
   Dry-run pause has `focus_action=none`: its desired state is the unchanged current focus, so it
   performs no focus write and emits no not-applied diagnostic.
3. A `core_not_engaged` diagnostic is suppressed only when the exact desired focus state is already
   current or effective attribution resolves to the target or to true `general`/unattributed state.
   Empty explicit focus is not sufficient for suppression: if the unique OPEN-wave fallback is an
   unrelated wave, the response reports that destination. A `focus_write_failed` diagnostic is
   suppressed only when no write was needed because the exact requested state was already current;
   otherwise it fires even if prior focus was empty. Wave equality alone is insufficient when the
   requested stage differs.
4. Focus behavior on genuinely failed calls is unchanged. A failed call still does not move focus.
5. `ready_for_council_review` is explicitly target-engaged: it moves focus to the canonical target
   at stage `plan` (the stage supplied by the prepare wrapper) and
   preserves the existing publication of that wave's durable accounting. `ok`, `dry_run`, and a
   review that reached prepare/implementation lane evaluation are classified explicitly; genuine
   errors/rejections remain non-engaged. Publication of already-attributed work and focus for future
   work remain distinct policies outside the observed council-ready case.
6. The diagnostic names a concrete recovery path rather than only describing the problem.
7. Processing order is canonical-target resolution, engagement classification, effective-attribution
   classification, focus set/clear attempt and best-effort reporting, workflow-call recording, then the existing publication policy.
   An unknown status leaves focus unchanged and returns `unknown_lifecycle_outcome`; it cannot engage
   until the classifier is deliberately updated.
8. The public response contract is stable and documented: diagnostics carry `code`, a message naming
   only resolved canonical focus/target state, the effective attribution destination and its source,
   `recovery_tools`, and `recovery_usage`.
   `focus_target_not_engaged`, `focus_stage_not_applied`, and
   `unknown_lifecycle_outcome` have the distinct meanings and recovery paths above. Relevant lifecycle
   tool docstrings and `docs/specs/mcp-tool-surface.md` use the same vocabulary. Upgrade replaces the
   packaged server surface and requires the normal MCP reload before the new response contract is
   active; no data migration, compatibility alias, or fallback is added.

## Scope

**Problem statement:** a lifecycle call that does not move focus leaves it pointing at a previously
focused wave and reports nothing, so retrieval performed afterward is silently credited to the wrong
wave for as long as the blockage lasts. In the `ready_for_council_review` case the same call also
publishes durable accounting for the wave it declines to focus, so one call answers the same question
two opposite ways.

**In scope:**

- A canonical target-engagement classifier covering the current status/reached-review classes, with
  an unknown-outcome diagnostic instead of silent fallthrough.
- Preserving publication semantics generally while pinning the observed council-ready outcome as
  both published and focused.
- A shared focus-attempt/reporting primitive covering all current helper and direct focus consumers,
  with separate core-not-engaged and focus-write-failed recovery.
- A single effective-attribution resolver used by both telemetry commit and lifecycle reporting for
  explicit focus, sealed focus, unique-OPEN fallback, and general/unattributed state.
- Reconciling `wf_reopen_wave`'s existing `focus_stage_not_applied` with the shared path so the two
  do not diverge.
- Tests over both failure causes, suppressed cases, council-ready engagement, unknown outcomes, and
  the current consumer census.
- Recording the reporting contract in `docs/references/context-efficiency.md`.
- Applicable prepare/review/implement/reopen/pause lifecycle docstrings and
  `docs/specs/mcp-tool-surface.md`, including exact diagnostic codes, fields, recovery, and upgrade
  reload behavior.

**Out of scope:**

- Re-attributing credits already recorded. Durable history that can be reassigned after the fact is
  history that can be made to say anything, which defeats the point of measuring.
- Letting a genuinely failed call (a rejected or errored operation) move focus. Reclassifying
  `ready_for_council_review`, which is a successful technical pass awaiting a further step, is a
  different question and is in scope.
- An explicit set-focus call, considered and deferred in the Decision Log.

## Acceptance Criteria

- [ ] AC-1: A committed desired-behavior test calls a lifecycle tool that fails against wave B while
  focus is on wave A and expects the response diagnostic to name wave A and its recovery. It is
  observed RED against current code and GREEN after the fix.
- [ ] AC-2: The diagnostic is produced through the real tool response envelope, reproducing the
  observed case: a prepare blocked on a missing council signoff while focus sits on another wave.
- [ ] AC-3: An AST/source census pins every current focus consumer—calls through
  `_lifecycle_context_result` plus direct reopen/pause focus paths—to the shared classifier/reporting
  primitive. A new consumer that bypasses the primitive fails the census; the plan does not claim to
  prove arbitrary future statuses correct without updating the canonical classifier.
- [ ] AC-4: `core_not_engaged` suppression is proven for exact desired state and true
  general/unattributed fallback; stage-mismatch is not suppressed. No explicit focus plus one unrelated
  OPEN wave reports that fallback rather than suppressing. `focus_write_failed` is reported for set and
  clear failures even from empty focus unless the desired state was already current.
- [ ] AC-5: `wf_reopen_wave` uses the shared primitive while preserving the existing
  `focus_stage_not_applied` code and successful-reopen semantics; tests pin the distinct recovery text
  and codes for `focus_target_not_engaged`, `focus_stage_not_applied`, and
  `unknown_lifecycle_outcome`.
- [ ] AC-6: Existing focus tests remain green, and direct known-bad probes cover council-ready,
  unknown status, genuine error, focus-write exception, different focus, same focus, and no focus.
  Each probe asserts the expected focus, publication, diagnostic code/recovery, and that diagnostics
  never overturn a successful lifecycle mutation.
  A sealed focused wave proves effective attribution is `general` and the response does not claim the
  sealed wave will receive credits. Mutating-pause success, `clear_focus` failure, and dry-run pause prove the shared clear-operation
  contract without changing the successful lifecycle result; dry-run asserts no focus attempt and no
  not-applied diagnostic.
- [ ] AC-8: A test executes `wf_prepare_wave(mode="ready")` on a wave whose prepare-council verdict is
  absent, asserts `ready_for_council_review`, and proves projection still publishes while focus moves
  to the canonical target at stage `plan`. It fails against current code, where projection publishes
  but focus stays elsewhere.
- [ ] AC-9: The canonical classifier maps `ok`, `dry_run`, `ready_for_council_review`, reached-review,
  and genuine error/rejection explicitly. An unknown status fails closed for focus and returns a named
  diagnostic rather than silently falling through; a structural census rejects bypass consumers.
- [ ] AC-7: Docs gate and full framework suite green.
- [ ] AC-10: Relevant lifecycle tool docstrings and `docs/specs/mcp-tool-surface.md` pin all three
  diagnostic envelopes and recovery fields; disposable install/upgrade fixtures use the updated
  packaged server code and reproduce council-ready focus plus failed-call reporting without fallback.

## Tasks

- [ ] Write the AC-1 desired-behavior test for the observed prepare case and record it failing against
  current code before the fix; keep it as the permanent green regression.
- [ ] Write the AC-8 red test proving the flush/focus asymmetry on `ready_for_council_review`, and
  confirm it fails against current code for that reason and not another.
- [ ] Implement the canonical target-engagement classifier and explicitly map the current outcomes.
- [ ] Use one effective-attribution resolver for telemetry commit and lifecycle reporting, including
  sealed focus and the no-focus/unique-OPEN fallback.
- [ ] Add the shared focus-attempt/reporting primitive and separate `core_not_engaged` from
  `focus_write_failed` recovery.
- [ ] Pin canonical processing order and unknown-outcome fail-closed behavior.
- [ ] Add the structural census for all current helper and direct focus consumers.
- [ ] Reconcile the `wf_reopen_wave` diagnostic with the shared path.
- [ ] Route mutating pause clear through the shared primitive and add success, clear-failure, and
  dry-run/no-clear probes.
- [ ] Add the suppression tests for AC-4.
- [ ] Record the reporting contract in `docs/references/context-efficiency.md`.
- [ ] Update the MCP tool-surface spec and relevant prepare/reopen/pause/lifecycle docstrings; extend
  disposable install/upgrade response probes for the packaged server code, including replacement plus
  reload and explicit absence of migration/fallback behavior.
- [ ] Full suite and docs gate.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-test | implementer | — | Desired-behavior probes must fail against current code for the observed silence/asymmetry, then pass after repair |
| outcome-classes | implementer | red-test | Canonical explicit classifier; council-ready is target-engaged; unknown fails closed with diagnostic |
| diagnostic | implementer | outcome-classes | Shared best-effort focus attempt/reporting across all current consumers |
| reopen-reconcile | implementer | diagnostic | Preserve or unify the existing reopen diagnostic |
| docs | implementer | diagnostic | Reporting contract in the context-efficiency reference, lifecycle tool docstrings, and MCP tool-surface spec |

## Serialization Points

- Begin only after 1tmb2 is implemented and independently reverified, and after
  any concurrent editor of `server_impl.py` or shared lifecycle tests has stopped.
- `_lifecycle_context_result` is shared by every lifecycle tool, so a defect introduced here affects
  all of them. AC-6 directly probes the changed and preserved outcome classes.
- The effective-attribution resolver remains owned by the telemetry authority layer in
  `context_efficiency.py`; lifecycle reporting calls it rather than duplicating sealed/open/general
  rules in `server_impl.py`.

## Affected Architecture Docs

`.wavefoundry/framework/scripts/context_efficiency.py`, `docs/references/context-efficiency.md`, and
`docs/specs/mcp-tool-surface.md`. No ADR: this extends an existing reporting pattern to the paths it
should already have covered.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The defect itself is the silence, not the focus behavior, so the red test must assert the silence. |
| AC-2 | required | Proves it through the real response envelope, reproducing the case actually observed rather than a constructed one. |
| AC-3 | required | Fixing only prepare would leave the same silence on every other lifecycle tool, which is how this gap arose. |
| AC-4 | required | A diagnostic that fires when nothing is wrong trains readers to ignore it, which is worse than silence. |
| AC-5 | required | Two divergent messages for one condition is the drift this change exists to remove. |
| AC-6 | required | Existing regressions alone can encode or miss the defect; named known-bad probes establish each outcome and failure mode. |
| AC-8 | required | The strongest form of the defect: one call publishing a wave's accounting while declining to focus it. Two opposite answers to one question is a design fault, not a reporting gap. |
| AC-9 | required | The root cause is an unmodelled outcome class; a canonical classifier plus bypass census makes unknown additions fail visibly. |
| AC-7 | required | Standard gates. |
| AC-10 | required | The response contract and behavior must reach installed/upgraded targets, not only this self-hosted checkout. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-26 | Filed after observing the case live: `wf_prepare_wave(1tj0l, dry_run)` returned `status: "error"` on a missing council signoff, leaving focus on the unrelated wave `1tmb1` with nothing in the response to say so. | `server_impl.py` `_lifecycle_context_result`; observed tool response with sole diagnostic `missing_wave_council_signoff`; `wf_current_wave` reporting `focus.wave_id = 1tmb1` |
| 2026-07-26 | Scope widened after observing a stronger case: `wf_prepare_wave(1tj0l, mode="ready")` returned `ready_for_council_review`, an outcome class the focus condition does not model. The same call published `1tj0l`'s checkpoint (1 call / 981 to 46 calls / 661,367) while leaving focus on `1tmb1`, which then climbed 58 to 72 calls during the council review of `1tj0l`. This is a design inconsistency, not only a missing diagnostic, so AC-8 and AC-9 were added. | Observed `wf_prepare_wave` response with `context_efficiency_persistence.projection: "published"`; `wave.md` checkpoint before and after; `wf_current_wave` focus and durable totals for both waves |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-26 | For genuinely failed calls, report the stale focus rather than moving it. | A failed call moving focus would let a rejected operation or a typo re-point accounting, which is the hazard the existing wave-resolution guard was hardened against. For that class the gap is in reporting, so the fix belongs in reporting. | Set focus on failed calls (rejected: lets rejected operations move accounting); do nothing (rejected: the operator caught this, not the tool). |
| 2026-07-26 | Treat `ready_for_council_review` as target-engaged: preserve its existing durable publication and move focus to that wave. Keep publication and future-focus policies distinct for other outcomes. **This narrows the preceding row**, which predates the observed council-ready case. | The status is a successful technical pass awaiting work on that exact wave, not a rejected operation. The current code already publishes its accounting; failing to focus it misattributes the ensuing council retrieval. | Suppress publication to force symmetry (rejected: discards legitimate already-attributed state); focus every non-error status (rejected: broader than observed evidence); diagnostic only (rejected: knowingly preserves council-review misattribution). |
| 2026-07-26 | Use one explicit target-engagement classifier and one shared best-effort focus/reporting primitive; unknown outcomes fail closed for focus with a diagnostic. | A source census can pin current consumers but cannot prove arbitrary future status semantics. One chokepoint makes additions visible and distinguishes core rejection from focus-write failure. | Hand-maintained per-tool wording and claims of future-proof enumeration were rejected as the same drift class. |
| 2026-07-26 | Report effective attribution rather than equating raw focus with future credit, and clear mutating-pause focus with `clear_focus`. | Telemetry redirects sealed focus to `general` and uses a unique OPEN-wave fallback when explicit focus is empty; `pause_focus` deliberately retains the wave at stage `paused`. The lifecycle contract must match those real semantics. | Report raw focus as attribution (rejected: false for sealed focus); suppress whenever focus is empty (rejected: hides unrelated OPEN fallback); redefine `pause_focus` (rejected: broader and unnecessary). |
| 2026-07-26 | Do not add a re-attribution tool for credits already recorded. | Durable history that can be reassigned after the fact is history that can be made to say anything, which defeats the purpose of measuring at all. Already-misattributed credits stay where they are. | Re-attribute on demand (rejected: makes every number negotiable); silently correct at close (rejected: the same defect, less visible). |
| 2026-07-26 | Defer an explicit set-focus call rather than adding one here. | It is a plausible answer to the underlying awkwardness that focus can only be moved by passing a gate, but it is a new capability with its own abuse surface: focus becomes freely assertable, and with it attribution. It deserves its own change and its own argument rather than riding in on a reporting fix. | Add it here (rejected: scope creep into a capability needing separate justification); rule it out entirely (rejected: the underlying awkwardness is real and worth revisiting). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The diagnostic fires on ordinary blocked calls and becomes noise readers filter out | AC-4 suppresses it only when effective attribution resolves to the target or true general/unattributed storage; empty focus with an unrelated unique-OPEN fallback remains visible. |
| Adding reporting perturbs focus accounting | AC-6 retains existing coverage and adds direct known-bad probes for every current outcome/failure class. |
| Only the prepare path is fixed, reproducing this same gap on the next tool | AC-3 pins all current helper and direct focus consumers to the shared primitive and fails on bypass. |
| The deferred set-focus question is forgotten | Recorded in the Decision Log with its reasoning intact so a future change can pick it up. |
| Reclassifying `ready_for_council_review` lets focus move on a call that should not claim future work | The status is the successful technical gate immediately preceding council work on that wave; AC-8 pins this narrow engaged-target choice and keeps genuine errors non-focusing. |
| The change is narrowed to the diagnostic during implementation, dropping the asymmetry | AC-8 and AC-9 are `required`, and the Decision Log records that the first decision row was narrowed by the second, so the broader scope cannot be read back out of an earlier row. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
