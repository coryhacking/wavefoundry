# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-21
review-evidence-source: events.jsonl

wave-id: `1t550 upgrade-field-fixes`
Title: Upgrade Field Fixes

## Objective

Repair the three field-reported 1.14.0 pack bugs the operator had to work around during cross-project upgrade testing: the pre-extract lock cutover fails crossing the tool rename, the post-extraction docs gate can run a stale cached review_evidence module, and a recovered resume-after-memory leaves a permanent failure marker. These block the 1.14.0 publish; a fresh pack build follows this wave.

## Changes

Change ID: `1t49m-bug upgrade-cross-rename-recovery-robustness`
Change Status: `implemented`

Change ID: `1t551-bug prepare-create-activation-implement-focus`
Change Status: `implemented`

Completed At: 2026-07-21

## Wave Summary

Wave `1t550` (Upgrade Field Fixes) delivered two changes: Upgrade Robustness: Cross-Rename Hooks and Recovery-Phase Failure Markers and Prepare-Create Activation Advances Context-Efficiency Focus to Implement. Notable adjustments during implementation: Upgrade Robustness: Cross-Rename Hooks and Recovery-Phase Failure Markers: All three seams implemented: getattr fallback (retired symbol verified against git history as `wave_dashboard_stop_response`, present v1.9.1 through the rename), `_reload_cached_review_evidence` before the pre-docs-gate projection, `upgrade_lib.clear_failed_phase` called on both resume success paths. Seven hermetic tests added; module suite 339 OK; two known-bad mutation probes (neutered clear, neutered reload) both detected.

**Changes delivered:**

- **Upgrade Robustness: Cross-Rename Hooks and Recovery-Phase Failure Markers** (`1t49m-bug upgrade-cross-rename-recovery-robustness`) — 4 ACs completed. Key decisions: getattr fallback at the call site, not a shim module.; Clear only the marker naming the phase the resume recovered.
- **Prepare-Create Activation Advances Context-Efficiency Focus to Implement** (`1t551-bug prepare-create-activation-implement-focus`) — 3 ACs completed. Key decisions: Derive the stage from the response's `transitioned_to_active`, in the wrapper only.; Historical splits are not rebalanced.
## Journal Watchpoints

- Watchpoint (release gate): 1.14.0 publish waits on this wave plus a fresh pack build; the pdqr zip under test carries the bugs.
- Watchpoint (marker semantics): the resume clears ONLY the failure marker naming the phase it recovered; never launder unrelated failures.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 9 records; 4 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Prepare Review Evidence

Readiness council pass, 2026-07-21 (single change, upgrade-robustness scope; all claims code-grounded via the field report cross-checked against the tree):

- reality-checker: all three defect sites resolve exactly as the operator reported — `_stop_dashboard_for_lock_cutover` calls `server_impl.wf_stop_dashboard_response` unconditionally against the INSTALLED module (upgrade_extensions.py:171, inside the pre-extract lock cutover whose target from-versions predate the rename); `pre_docs_gate` (:275) loads the installed upgrade module by file path but the named-import `review_evidence` seam resolves through the pre-extraction sys.modules cache; the standalone resume block sets `failed_phase="index_update"` on exception with no success-path clear, and the retained-marker messaging offers resume recovery only for review/docs-gate phases.
- red-team: strongest challenge is the marker-clearing scope — clearing on any success could launder unrecovered damage. The plan pins the narrow rule (clear only the marker naming the phase the resume just recovered) as a Decision Log entry and a required test case. Second challenge: the reload could break holders of old module references — answered by in-place importlib.reload (module identity preserved) and a poisoned-stale-module test through the real call path.
- qa-reviewer: each AC has a falsifiable hermetic proof — a stub installed server_impl with only the retired symbol (and one with neither); a planted poisoned review_evidence in sys.modules observed replaced through the real projection call; lock-state fixtures for cleared/retained markers. All fixture shapes come from canonical producers (the real lock writer, real module objects).
- docs-contract-reviewer: requirements/ACs/tasks/decisions are internally consistent; Affected Architecture Docs correctly claims N/A with the upgrade prompt already describing the intended behavior; the release-gate watchpoint records that 1.14.0 publish waits on this wave plus a fresh pack.

Synthesis verdict: READY. Three independent, narrowly-scoped seams, each with an executable regression boundary, unblocking the 1.14.0 publish.

Delta readiness pass for the late admission of `1t551-bug prepare-create-activation-implement-focus` (operator-directed, 2026-07-21): reality-checker confirmed the mechanism against the tree (hardcoded `focus_stage="plan"` in the `wf_prepare_wave` wrapper; `wf_implement_wave` and `wf_reopen_wave` carry the only `focus_stage="implement"` sites; the envelope already reports `transitioned_to_active`); red-team's strongest challenge is edits inside the five-times-repaired CE instrumentation region, answered by the envelope-derived single-parameter design plus the fragile-file live post-reload probe pinned as AC-3; qa-reviewer confirmed both boundary outcomes are hermetically testable against real envelopes; docs-contract-reviewer confirmed the doc is complete with the no-history-rebalance decision recorded. Synthesis: READY, no findings.

## Review Checkpoints

- pre-implementation-review: passed (2026-07-21) — pre-mortem: (1) fallback getattr could mask a genuinely broken install; keep the legible neither-symbol RuntimeError; (2) reload ordering matters (reload BEFORE the projection call, only when cached); (3) marker clear must be phase-scoped; test retention of unrelated markers; (4) upgrade tests are slow — keep new fixtures hermetic, no real pack extraction; (5) the pdqr zip under test contains the bugs — a fresh build follows, never a patched zip.
- **Delivery-phase Wave Council [delivery-council] — 2026-07-21 (delta, 1t551): PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a non-transitioning create advancing focus to implement — covered by the four-case hermetic test through the real registered wrapper; strongest-alternative: forcing wf_implement_wave on every activation — rejected, the envelope already reports the transition and the wrapper is the single seam.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-21 (delta, late admission 1t551): PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: touching the five-times-repaired CE instrumentation region — resolved by deriving the stage from the canonical envelope through the existing focus_stage parameter plus the mandatory live post-reload probe; strongest-alternative: stage-from-wave-status inside the telemetry store — rejected for blast radius, per the Decision Log.)
- **Delivery-phase Wave Council [delivery-council] — 2026-07-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: reload blast radius on the old-runner process — resolved by in-place reload preserving module identity plus the short-circuit path skipping reload and projection together; strongest-alternative: reloading every cached framework module wholesale — rejected, only the two named-import seams the hooks actually consume are refreshed.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer, reality-checker, qa-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: an unconditional marker clear on resume success could launder unrecovered failures — resolved by the phase-scoped clearing rule pinned in the Decision Log with a required retention test; strongest-alternative: a compatibility shim module exporting retired names — rejected as a broader surface than the single cross-version call requires, per the Decision Log.)

## Delivery Review Evidence

Delivery council pass, 2026-07-21, over the landed diff (4 files, +262/-2: upgrade_extensions.py, upgrade_lib.py, upgrade_wavefoundry.py, test_upgrade_wavefoundry.py), all claims verified against the tree via code_read/code_keyword/code_definition plus git-history oracle checks:

- reality-checker: the retired symbol in the fallback is `wave_dashboard_stop_response`, verified against git history at v1.9.1, v1.9.8, and the pre-rename parent of 0bfdb404 (the plan's original `wave_stop_dashboard_response` guess was wrong and was corrected in the change doc before implementation); the fallback prefers the current symbol and raises the legible neither-symbol RuntimeError inside the existing wrapping handler.
- red-team: strongest attack was the reload seam's blast radius — reload re-executes the on-disk source for ALL holders in the old-runner process. Answered: that is the documented intent of both helpers (serve the just-extracted code), reload preserves module identity, and the short-circuit path (`review_status_projection` already in the lock) skips both the reload and the projection together, so no stale code runs unprojected. Second attack: could clear_failed_phase launder a failure? No — it compares the marker to the exact recovered phase and the retention test proves an unrelated marker (`dashboard_restart`) survives a successful resume.
- qa-reviewer: eight new hermetic tests, all shapes from canonical producers (real memory_backfill runs, real upgrade locks via upgrade_lib, real review_evidence renderer for the wave fixture; SimpleNamespace stubs only where symbol ABSENCE is the fixture, since MagicMock fabricates attributes). Known-bad detection executed for the two non-structural fixes: in-process mutation probes (neutered clear_failed_phase, neutered reload hook) both flipped their tests to failure. The fallback and sibling-reload tests are structurally falsifying (the stub lacks the new symbol; the poisoned coordinator raises if used).
- docs-contract-reviewer: change doc tracked in real time (three seam entries plus the AC-4 entry); the requirement-2 sibling seam (`_installed_memory_backfill`) is inside the requirement's explicit "any sibling that consumes framework modules the pre-upgrade runner may have cached" language, not silent scope growth; Affected Architecture Docs N/A holds (behavior now matches the documented upgrade flow).

Synthesis verdict: PASS. Suite 6,113/6,113 OK on the final tree; docs lint clean; no findings.

Delta delivery pass for the late-admitted `1t551` (2026-07-21): reality-checker confirmed the landed wrapper derives the stage from the canonical envelope's `transitioned_to_active` via `_context_data` and that no other focus site changed; red-team's strongest challenge, a non-transitioning create wrongly advancing focus, is directly covered by the four-case hermetic test's third case; qa-reviewer confirmed the mutation probe (pre-fix hardcoded-plan wrapper forced through the real registered function) flipped the test to failure, and the live post-reload probe exercised the non-transition branch on live code with the field name confirmed from this session's real activation envelope, the transition branch being hermetically proven since 1t550 holds the single-OPEN slot; docs-contract-reviewer confirmed real-time tracking and the no-history-rebalance decision. Suite 6,114/6,114 OK on the final tree. Synthesis: PASS, no findings.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

operator-signoff: approved (2026-07-21, operator requested wave close in the current session: close the wave and then do a new 1.14 local build)
- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 54 | 451,588 |
| review | 5 | 0 |
| **Total** | **59** | **451,588** |

<!-- wave:context-efficiency-state {"generation":57,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":54,"content_source_credit":521510,"derived_artifact_credit":1728,"direct_net":451588,"estimated_tokens_saved":451588,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5298,"response_debit":71623,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5271},"review":{"calls":5,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-876,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":45,"response_debit":1920,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1089}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":59,"content_source_credit":521510,"derived_artifact_credit":1728,"direct_net":450712,"estimated_tokens_saved":451588,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5343,"response_debit":73543,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6360},"wave_id":"1t550 upgrade-field-fixes"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
