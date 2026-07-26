# wf_reopen_wave forces implement-stage CE attribution even when reopening to review

Change ID: `1tj0k-bug reopen-wave-forces-implement-stage-attribution`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-25
Wave: `1ti11 remove-unused-context-efficiency-schema`

## Rationale

`wf_reopen_wave` unconditionally sets the context-efficiency focus to the implement stage:

```python
# server_impl.py (wf_reopen_wave)
context_efficiency.unseal_wave(handler.root, canonical)
handler.telemetry.set_focus(canonical, "implement", new_phase=True)
```

There is no way to reopen a wave for review. That is a problem because *reopen-to-review-before-closing is a primary reopen use case*: an operator who wants a second look at a wave's plan and implementation before it closes must reopen it, and every retrieval call that review makes is then attributed to implement.

This was measured on wave `1ti11` itself. The operator asked to reopen it and review the plan and implementation. The review used MCP retrieval correctly (`code_keyword`, `code_read`, `docs_search`), so the savings were genuinely captured — but landed in the wrong bucket: **23 retrieval calls and ~570k estimated tokens saved recorded against `implement`**, while the `review` stage showed 3 calls and 3,432. The per-wave Context Efficiency table therefore reports review work as implementation work.

The failure is silent and systematically biased in one direction: it inflates implement and deflates review for exactly the waves that get the most review scrutiny. It cannot be corrected after the fact, because re-running the retrieval purely to move credits into the right bucket is the inflation the telemetry design exists to prevent — mis-attributed credits must stay where they landed.

An agent can work around this by calling `wf_review_wave` before any review retrieval, and the retrieval-posture directive already pushes MCP-first behavior. But the workaround depends entirely on the agent remembering, against a default that is wrong for the stated use case; this has now been observed four times across sessions.

## Requirements

1. **Reopening for review must not attribute to implement.** `wf_reopen_wave` must support reopening a wave for review such that subsequent retrieval is credited to the review stage.
2. **The chosen stage must be visible in the response.** The reopen envelope reports the focus stage it set, so a caller can see immediately where subsequent credits will land and correct course in the same turn rather than discovering it at close.
3. **Mechanism (settled, not deferred): a REQUIRED `purpose` parameter.** `wf_reopen_wave(wave_id, purpose="review" | "implement")`. Status-based inference is rejected: reopening a fully-implemented wave to fix a late defect is legitimately implement work, while reopening it for a pre-close review is not, so the tool cannot infer intent without guessing.
   - **`purpose` has no default.** A caller census found no runtime caller and no persisted migration depending on an omitted value, so the compatibility fallback was removed rather than documented. A silent default necessarily selects one stage and is wrong for the other, which is the original misattribution defect.
   - **Canonical review flows pass `purpose="review"` explicitly.**
   - **Rejected values fail closed and fail early**, all mutating nothing: the wave status is not changed, telemetry is not unsealed, and focus does not move. The two rejection paths are NOT interchangeable: an **empty or unrecognized** value returns the typed `invalid_purpose` error with recovery hints, while an **omitted** argument is rejected by the published MCP schema before the tool body runs and produces a `Field required` validation error with no diagnostic and no hints. Callers must not branch on `invalid_purpose` to recover from omission.
   - **The response never names a stage it did not apply.** On success it reports `focus_stage`. If the focus write fails, the reopen still succeeds (telemetry is observational) but the response reports `focus_stage: null` with `focus_error` and a `focus_stage_not_applied` diagnostic. There is no `focus_stage_source` field: once `purpose` is required, every successful selection comes from the request, so a source field whose only success value is "explicit" is redundant.
4. **Regression coverage with the correct polarity.** The two paths are not symmetric, because the implement path is already correct and must stay correct:
   - **Review path — RED before, GREEN after.** Demonstrated failing against the current unconditional implement focus.
   - **Implement path — GREEN before and after.** A control proving the change did not move behavior that was already right; requiring it to fail first would be impossible and would signal a regression if it ever did.
   - **Every new permanent regression must fail against the behavior it replaces**, demonstrated through the registered-tool seam. Named precisely, because the empty and omitted paths are distinct: the two failure-envelope tests go RED against the original false-success implementation; `test_empty_purpose_fails_closed_before_any_mutation` goes RED against the restored legacy fallback; and `test_omitted_purpose_is_rejected_before_the_tool_body_runs` goes RED against a restored optional-`purpose` default.
5. **AC-1 is proven through the public tool and durable storage, not an in-memory field.** The test invokes the registered `wf_reopen_wave` tool (not an internal focus setter), then records a subsequent retrieval call and asserts that call's **durable telemetry row is stored under the `review` stage**, and separately pins the stage reported in the reopen response. Inspecting `telemetry.focus.stage` alone would pass even if nothing durable followed the focus.
6. **Correct the docstring's status claim while touching it.** The `wf_reopen_wave` docstring states it "Only works on waves with status 'closed'", but the implementation accepts `("closed", "paused")` and its own error message says so. Seed 190 repeats the same incorrect claim. Both are corrected.
7. **No change to stage semantics or accounting.** Stage names, credit rules, sealing/unsealing, and the flush at reopen are untouched; this only selects which existing stage the focus advances to, and reports that selection.

## Scope

**Problem statement:** `wf_reopen_wave` hardcodes implement-stage focus, so review work performed on a reopened wave is durably recorded as implementation work.

**In scope:**

- `wf_reopen_wave` in `.wavefoundry/framework/scripts/server_impl.py`: the required `purpose` parameter, early validation of empty and unrecognized values (an omitted argument is rejected earlier still, by the required-parameter signature), focus selection, and the reported `focus_stage` / `focus_error` / `focus_stage_not_applied` envelope.
- **Public guidance surfaces that currently teach the failing flow** (`seed_edit_allowed` for the seed):
  - `.wavefoundry/framework/seeds/190-finalize-feature.prompt.md` — line ~112 instructs a bare `wf_reopen_wave(wave_id)` followed by `wf_review_wave`, which is exactly the mis-attributing sequence; it also repeats the incorrect closed-only claim. Regenerate the rendered prompt via the canonical renderer.
  - `docs/prompts/index.md` — reopen entry.
  - `docs/references/context-efficiency.md` — the stage-selection rule is explicitly operator-visible and belongs with the stage model.
- Tool docstring and the `docs/specs/mcp-tool-surface.md` entry.
- Regression coverage in `test_server_tools.py` / `test_server_context_efficiency.py`, including the boundary case.

**Out of scope:**

- Retroactively re-attributing already-recorded credits, including wave `1ti11`'s own. Mis-attributed savings stay where they landed; re-running retrieval to relocate them would be inflation.
- Changing `wf_review_wave`, the stage model, credit rules, or the retrieval-posture directive.
- The separate question of whether repair work performed inside a review cycle should credit implement or review; this change only fixes the reopen entry point.

## Acceptance Criteria

- [x] AC-1: `wf_reopen_wave(purpose="review")`, invoked through the registered public tool, causes a subsequent retrieval call's **durable telemetry row to be stored under the `review` stage**, and the reopen response reports that stage.
- [x] AC-2: `purpose="implement"` focuses `implement` and durably records a subsequent call under that stage; `purpose` is marked required in the registered MCP schema so it cannot be omitted.
- [x] AC-3: an **empty or unrecognized** `purpose` returns a typed `invalid_purpose` error, and an **omitted** `purpose` is rejected by the required-parameter signature before the tool body runs. All three mutate nothing — wave status unchanged, telemetry not unsealed (asserted via a call spy on `unseal_wave`, not only stored seal state), exact focus unchanged. The empty and omitted paths are covered by separately named tests, because only the former produces the guided envelope.
- [x] AC-4: the review-path regression is demonstrated RED against the current unconditional implement focus and GREEN after; the implement control is GREEN both before and after.
- [x] AC-8: the focus-failure envelope is pinned by permanent registered-tool regressions — a failed focus write yields `focus_stage: null`, `focus_error`, and a `focus_stage_not_applied` diagnostic, never a claimed stage. Both failure-envelope tests, `test_empty_purpose_fails_closed_before_any_mutation`, and `test_omitted_purpose_is_rejected_before_the_tool_body_runs` are each demonstrated RED against the implementation they replace.
- [x] AC-5: seed 190 no longer teaches a bare reopen before review (and no longer claims closed-only). **No rendered file was hand-edited, and none required regeneration:** `docs/prompts/finalize-feature.prompt.md` is a short pointer that never carried this section, and no renderer in the tree owns it — `render_platform_surfaces.py` covers only host hook/config surfaces, `render_agent_surfaces.py` does not list `finalize-feature`, and the sole script naming the file is a docs-lint expected-file list. (`wf_sync_surfaces(mode="run")` returning `written: []` is consistent with this but does NOT establish it, since that renderer would never touch the file regardless; the ownership census is the actual basis.) `docs/prompts/index.md`, `docs/references/context-efficiency.md`, the tool docstring, and the tool-surface spec (including its signature line) state the stage-selection rule.
- [x] AC-6: the docstring's status claim matches the implementation (closed **or paused**).
- [x] AC-7: docs gate and full framework suite green.

## Tasks

- [x] Add the required `purpose` parameter with early fail-closed validation for empty and unrecognized values (omission is rejected by the signature before the body runs); select and report `focus_stage`, and report `focus_error` plus a `focus_stage_not_applied` diagnostic when the focus write fails. Remove `REOPEN_LEGACY_STAGE`, the omitted-purpose fallback, the `legacy_default` vocabulary, and the now-redundant `focus_stage_source`.
- [x] Update seed 190 (flow + closed-only claim) under `seed_edit_allowed` and regenerate its rendered prompt; update `docs/prompts/index.md`, `docs/references/context-efficiency.md`, the docstring (including the paused correction), and the tool-surface spec.
- [x] Add the review-path regression (prove RED pre-change), the implement control (GREEN throughout), and the empty-, unrecognized-, and omitted-`purpose` no-mutation boundary tests.
- [x] Docs gate; full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| focus | implementer | — | Stage selection + reported stage in `wf_reopen_wave` |
| verify | qa-reviewer | focus | Review-path regression proven RED pre-change then green; the implement control stays green throughout, since it asserts only pre-existing behavior; each new permanent regression is mutation-proven against the behavior it replaces |

## Serialization Points

- None; single entry point plus its tests. Independent of the schema-removal change in this wave.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (`wf_reopen_wave` stage selection) and `docs/references/context-efficiency.md` (the stage-selection rule is operator-visible guidance, so this surface is affected unconditionally). No boundary or flow change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect: review work on a reopened wave must be durably stored as review. |
| AC-2 | required | The implement path must keep working, and `purpose` must be required in the published schema so no caller can omit it and silently inherit a stage. |
| AC-3 | required | A rejected argument must never leave the wave or telemetry half-mutated. |
| AC-4 | required | Correct polarity: the review test must be shown red; the controls must never have been red. |
| AC-5 | required | The canonical seed currently teaches the failing flow, so code-only fixes would leave it in place. |
| AC-6 | important | A docstring that contradicts the implementation misleads every caller that reads it. |
| AC-7 | required | Standard gates. |
| AC-8 | required | The failure envelope is a public response shape; unpinned, a regression to false success would pass the whole suite. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-25 | Delivery council (moderator `wave-council`; seats `red-team`, `docs-contract-reviewer`) returned CHANGES REQUESTED on one P2 and it was repaired. The documented response shape was flat (`{"status": "ok", "focus_stage": "review"}`) while the implementation writes both fields through `_context_data`, which returns `response["data"]` — so a caller following the docs would read a top-level key, find nothing on BOTH the applied and not-applied paths, and be unable to distinguish them. That erases the exact guarantee the block was added to state. Corrected in the tool docstring and `docs/specs/mcp-tool-surface.md`, both of which now show the fields nested under `data` and say explicitly that a top-level read cannot tell the two paths apart. Documentation only; no code or test change. | Confirmed against `_context_data` (`server_impl.py:21701-21707`) and the passing test's own `data.get("focus_stage")` assertion; suite 6,211 / 59 files OK after the edit |
| 2026-07-25 | Gapfill: this was the THIRD contract mismatch in the same documentation block (after the stale `purpose: str = ""` signature line and the refuted missing-`invalid_purpose` claim). Root cause of the miss is methodological: the prior residual censuses were token-shaped (`legacy.default`, `purpose: str = `, `invalid_purpose`), and a nesting error contains none of those tokens, so that method structurally could not detect it. Re-swept by response SHAPE instead of by token; no flat-shape claim remains anywhere in the tree. | Structural sweep over every documented literal containing `focus_stage` |
| 2026-07-25 | Third independent pass returned APPROVED with nothing outstanding. It swept by exhaustive enumeration of every `invalid_purpose` occurrence rather than by pattern, and found no fourth instance of the refuted claim; it independently re-derived (rather than accepted) the four sites judged to need no change, and verified the docs-only assertion by file mtime. Took its one deferred judgment call: the loose "missing" cover term at Scope, Tasks, and the boundary-test task now reads "empty and unrecognized (omission is rejected by the signature before the body runs)", so the durable record no longer conflates two paths that behave differently. | Third-pass verdict APPROVED; suite 6,211 / 59 files OK, docs lint clean, `git diff --check` clean, reviewer tree byte-identical to baseline |
| 2026-07-25 | Repaired three findings from the independent RE-review. (5) The refuted "a missing `purpose` returns `invalid_purpose`" claim survived at two further sites after the first repair reached only the Risks row and AC-3: the public spec bullet and Requirement 3. Both now distinguish the two rejection paths explicitly and warn against branching on `invalid_purpose` to recover from omission. (6) AC-5 had been reworded from "unverifiable" into a claim cited to evidence that cannot establish it; a renderer-ownership census shows NO renderer owns `docs/prompts/finalize-feature.prompt.md`, so that census is now stated as the basis and the `wf_sync_surfaces` result is marked as merely consistent. (7) Requirement 4 and AC-8 still named a "missing-purpose test" that no longer exists; both now name `test_empty_purpose_...` and `test_omitted_purpose_...` separately, since those are distinct paths. | Exhaustive sweep for the refuted claim across all surfaces (co-occurrence of "missing" with `invalid_purpose`, the stale test descriptor, and "missing or/and unrecognized/invalid"): only Progress Log history remains. Independently re-confirmed that `context-efficiency.md:132`, seed 190 `:115`, and the docstring `server_impl.py:24942` need no change, because each says "rejected before anything changes" without claiming the envelope, which is true on both paths |
| 2026-07-25 | Repaired four findings from the independent contract review. (1) `docs/specs/mcp-tool-surface.md` signature line still advertised `purpose: str = ""`, contradicting the required-purpose bullets three lines below it and re-creating the documented-contract-mismatch class the P1 was raised to close. (2) Four change-doc sites still referenced the removed `legacy-default` control, including an AC-2 priority rationale demanding a visible legacy default the shipped tool deliberately lacks. (3) The breaking-change risk row claimed a stale caller receives the guided `invalid_purpose` envelope; measured, an OMITTED argument is rejected by the schema with no diagnostic and no recovery hints, so only the empty/unrecognized case is self-explaining. (4) `test_missing_purpose_...` passed `""`, which is empty rather than missing; renamed to `test_empty_purpose_...` and added `test_omitted_purpose_is_rejected_before_the_tool_body_runs` covering the path a stale pre-1.15.0 caller actually takes. | Suite 6,211 tests / 59 files OK; docs lint clean; new omitted-purpose test falsified (control green; RED against a restored optional-`purpose` default with "TypeError not raised") |
| 2026-07-25 | Gapfill: the residual census that missed defect (2) searched the underscore token `legacy_default`, but the prose form is hyphenated `legacy-default`, which that pattern cannot match. Re-run as `legacy.default` across both spellings plus a `purpose: str = ` signature sweep; remaining hits are only intentional history and the negative assertion pinning that `focus_stage_source` cannot resurface. | Case-insensitive two-spelling census after repair |
| 2026-07-25 | Repaired `reopen-failure-envelope-undocumented-and-unpinned` (P1) by simplifying the contract rather than documenting the old one, per independent review. `purpose` is now REQUIRED; `REOPEN_LEGACY_STAGE`, the omitted-purpose fallback, the `legacy_default` vocabulary, its compatibility test, and `focus_stage_source` are all removed. Missing and invalid values fail closed on one path. Success returns `focus_stage`; a failed focus write returns `focus_stage: null` with `focus_error` and a `focus_stage_not_applied` diagnostic. Eight permanent registered-tool regressions replace the temporary probe. All public surfaces reconciled: docstring, tool-surface spec, seed 190, prompts index, context-efficiency reference, and this document's requirements/ACs/risks/decision record. No deprecated alias added. | Falsification: failure-envelope and never-claims-a-stage tests both RED against the original false-success implementation; missing-purpose test RED against the legacy fallback; control green. Suite 6,210 tests / 59 files OK; `wf_sync_surfaces` no drift; residual census clean (only intentional history plus the negative assertion pinning that `focus_stage_source` cannot resurface) |
| 2026-07-25 | Gapfill: the required-`purpose` cutover surfaced one internal TEST caller the review census did not cover, `test_server_context_efficiency.py:2583`, which invoked `wf_reopen_wave(wave_id)` with no purpose. Updated to `purpose="implement"`, preserving that test's intent (it asserts persistence-failure passthrough, not stage selection). The census claim that no RUNTIME caller depends on omission still holds. | Full-suite run caught it as a `TypeError: missing 1 required positional argument: 'purpose'` |
| 2026-07-25 | Repaired three delivery-review findings. (1) `reopen-reports-unapplied-focus`: `focus_stage` / `focus_stage_source` were assigned OUTSIDE the `try`, so a swallowed `set_focus` failure still reported `('review','explicit')`. The reopen still succeeds (telemetry is observational) but now reports `focus_stage: None`, `focus_stage_source: "not_applied"`, `focus_error`, and a `focus_stage_not_applied` diagnostic. (2) `invalid-purpose-test-misses-focus-and-seal`: the regression compared only `review`/`implement` counters, so a move to `plan` and an unseal both passed; it now asserts the exact `Focus` value and spies the `unseal_wave` seam (state comparison alone is vacuous when the fixture has no `wave_state` row). (3) `reopen-plan-retains-rejected-polarity`: Execution Graph, Affected Architecture Docs, and both Risk rows reconciled with the settled explicit-`purpose` mechanism and the asymmetric test polarity. | Falsification probe: control passes; known-bad focus-to-`plan` CAUGHT; known-bad unseal CAUGHT; injected `set_focus` failure yields `not_applied` + diagnostic. Full suite 6,207 tests / 59 files OK |
| 2026-07-25 | Implemented. `wf_reopen_wave` gains `purpose`, validated BEFORE any mutation (a rejected value leaves status, seal, and focus untouched), selecting the focus stage from `REOPEN_PURPOSE_STAGES` and reporting `focus_stage` / `focus_stage_source`. Public surfaces updated: seed 190 (flow + the false closed-only claim), `docs/prompts/index.md`, `docs/references/context-efficiency.md`, the tool docstring, and the tool-surface spec. `wf_sync_surfaces` reports no rendered drift — the rendered finalize prompt does not carry that section, so there was nothing to regenerate. | `server_impl.py` `wf_reopen_wave`; seed 190; 4 doc surfaces; `wf_sync_surfaces` written: [] |
| 2026-07-25 | Test polarity demonstrated, not asserted. PRE-FIX run: 5 tests, 4 RED (review-path durable storage, stage reporting, invalid-purpose no-mutation, docstring/paused) and 1 GREEN — the implement/legacy control, which asserts only pre-existing behavior and therefore could be green against the unfixed tree. POST-FIX: 5/5 green. An earlier draft of the control also asserted the NEW reporting fields, which made it impossible to be green pre-change; it was split into a behavior-only control plus a separate new-surface test. | Pre-fix run (4 failures / 1 pass); post-fix run 5/5 OK |
| 2026-07-25 | Plan revised on operator review before implementation: mechanism settled (explicit `purpose`, no inference, legacy default surfaced via `focus_stage_source`, invalid values fail before any mutation); the impossible both-tests-red requirement corrected to review-path red-then-green with implement/legacy controls green throughout; AC-1 strengthened from an in-memory focus check to a durable-row assertion through the registered tool; public-surface scope expanded after verifying seed 190 line ~112 teaches the exact failing flow; docstring's closed-only claim confirmed false against `("closed", "paused")`. | Operator plan review; `seeds/190-finalize-feature.prompt.md`; `wf_reopen_wave_response` status guard |
| 2026-07-25 | Drafted from a measured occurrence on wave `1ti11`: the operator asked to reopen and review, and the review's 23 retrieval calls (~570k estimated savings) were recorded against `implement` while `review` held 3 calls / 3,432. Root cause confirmed by reading the seam rather than inferring: `wf_reopen_wave` calls `set_focus(canonical, "implement", new_phase=True)` unconditionally. | `server_impl.py` `wf_reopen_wave`; `wf_current_wave` CE stages for 1ti11; `wf_review_wave` `implement_stage_telemetry.retrieval_calls: 23` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-25 | Use an explicit `purpose` parameter; reject status-based inference. | The tool cannot infer intent: reopening a fully-implemented wave to fix a late defect is implement work, while reopening it to review before closing is not. Inference would guess and be silently wrong half the time. | Infer from change statuses (rejected: guesses); inferred default with explicit override (rejected: two mechanisms, more surface, still guesses when the override is omitted). |
| 2026-07-25 | Make `purpose` REQUIRED; delete `REOPEN_LEGACY_STAGE`, the omitted-purpose fallback, the `legacy_default` vocabulary, its compatibility test, and `focus_stage_source`. | An independent caller census found canonical guidance already passes `purpose` explicitly, no internal runtime caller depends on omission, and no persisted data migration depends on the fallback branch; the operator confirmed they were the sole 1.14.0 deployer. With no external population to protect, the fallback is counterproductive: omission silently selects `implement`, which IS the original misattribution defect. Once `purpose` is required, every successful selection comes from the request, so `focus_stage_source` has exactly one success value and is redundant; `"not_applied"` was in any case an application result, not a source. | Keep the fallback and document the failure envelope (rejected: preserves the defect for exactly the callers most likely to hit it); add a deprecated alias or transitional warning (rejected: no independently verified external consumer requires one). |
| 2026-07-25 | Fix the reopen entry point rather than relying on agents to call `wf_review_wave` first. | The workaround depends on memory against a default that is wrong for the stated use case, and it has been missed four times across sessions. A wrong default that is silently biased in one direction is a tool defect, not a discipline problem. | Document the workaround only (rejected: already documented, still missed); make `wf_review_wave` mandatory before review retrieval (rejected: cannot be enforced and does not fix the default). |
| 2026-07-25 | Do not retroactively re-attribute 1ti11's own mis-bucketed credits. | Re-running retrieval to move credits is precisely the inflation the telemetry design prevents; the honest record is the one that was measured. | Re-run the review retrieval after advancing the boundary (rejected as inflation). |
| 2026-07-25 | *(Historical, superseded by the required-`purpose` decision above.)* Keep the omitted-`purpose` default at `implement` and report `focus_stage_source: "legacy_default"`. | Preserved because it was really decided and really reversed. The compatibility argument held only while an external caller population was assumed to exist; an independent census plus the operator's confirmation of sole 1.14.0 deployment removed that assumption, at which point the fallback silently selected `implement`, which was the original defect. | Flip the default to review (rejected then: silent re-bucketing of shipped callers); leave the default unreported (rejected: hides whether attribution was chosen or inherited). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Removing the omitted-`purpose` fallback breaks an unknown external caller that relied on the v1.14 signature | Accepted deliberately on evidence: an independent caller census found no runtime caller and no persisted migration depending on omission, and the operator confirmed sole 1.14.0 deployment. The failure mode is loud and safe rather than silent, though it is **not uniformly guided**: a stale caller that OMITS the argument is rejected by the published schema before the tool body runs, producing a `Field required` validation error (or `TypeError` on the raw callable) with no `invalid_purpose` diagnostic and no recovery hints; a caller that passes an empty or unrecognized value gets the guided `invalid_purpose` envelope with `recovery_usage`. Both mutate nothing, which is the property that matters, but only the second is self-explaining. No deprecated alias was added, per review direction. |
| A regression that passes both before and after the change (proving nothing) | AC-4 requires the review-path regression to be demonstrated failing against the current unconditional implement focus before the fix lands, and AC-8 requires every new permanent regression to be mutation-proven against the behavior it replaces. The implement control is deliberately green throughout: it asserts only pre-existing behavior, so requiring it to fail first would be impossible, and a later failure in it would mean the implement path moved. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
