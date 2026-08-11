# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ur6o closure-narrative-digest-boundary`
Title: Closure Narrative Digest Boundary

## Objective

Make one property mechanical that is currently enforced only by a test this repository runs and by prose instruction to an upgrade agent: a scaffold must declare no review targets. A target repository upgraded to 1.15.5 shipped a `plan-template.md` whose unfenced example declared `path/to/file.swift` and `docs/specs/`, so every plan created from it was born in declared mode and silently lost two review lanes. A docs-lint rule keyed off the shipped parser, plus a pre-gate repair for already-contaminated repositories, closes that everywhere rather than in this repository alone.

## Changes


Change ID: `1ur6p-bug scaffold-declaring-targets-has-no-mechanical-gate`
Change Status: `implemented`

## Participants

- Coordinator: session agent (Claude Code)
- Write-owning roles: implementer (red-test, rule, census, upgrade workstreams for 1ur6p)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-08-08

## Wave Summary

Wave `1ur6o` (Closure Narrative Digest Boundary) delivered one change: Scaffold Declaring Targets Has No Mechanical Gate. Notable adjustments during implementation: Scaffold Declaring Targets Has No Mechanical Gate: Its one residual, a false claim inside a `[x]` Task, is fixed: the task said the pin included "a closed-wave change doc that must never block" and no such fixture exists. The task now states what is actually true — the property holds by scope, and what the tests kill is any widening of it; Scaffold Declaring Targets Has No Mechanical Gate: Its precision note also acted on rather than accepted: my new debris test had a subtest ORDERING dependency, where the mid-staged-write case passed by tripping on debris the rename case left behind. Each case now resets the directory first and a third injection was added that fails after the staged file exists, so cleanup is pinned by two independent cases. Re-measured: the cleanup mutant now fails exactly the two cases that genuinely create debris; Scaffold Declaring Targets Has No Mechanical Gate: Final precision folds, all cheap and none behavioral: the `not failed_phase` guard was described as if it covered all three `_run_reconciliation_scan` call sites when it guards one, so the phrasing now rests on the property that is true of all three (every site is post-gate); `1uo1w` named as a change rather than a wave; AC-5's priority rationale reconciled with its own body; and the out-of-scope trigger-registry bullet no longer presents a withdrawn change's non-reproducing 36-document figure as a measured decline.

**Changes delivered:**

- **Scaffold Declaring Targets Has No Mechanical Gate** (`1ur6p-bug scaffold-declaring-targets-has-no-mechanical-gate`) — 12 ACs completed. Key decisions: Keep the insertion-only fencing repair rather than re-rendering the whole `## Serialization Points` section; Gate it in docs-lint rather than strengthening the seed instruction
## Watchpoints

- Blocking: the docs-lint rule must call `serialization_point_paths`, never re-implement extraction. A second extractor would drift from the evaluator and pass a template the evaluator reads as declaring, recreating the same silent gap one layer up. AC-2 pins it by patching `wave_lint_lib.core_validators.serialization_point_paths`, the name the rule actually resolves. NOT `docs_lint`, which is a 27-line venv shim that exposes no such attribute; patching a module that does not hold the name is observationally identical to the re-implementation the AC exists to catch.
- Blocking: the rule consumes parser OUTPUT only. Scanning raw text fails against the one artifact the rule actually reads: `docs/plans/plan-template.md` mentions `src/app/handler.py` in prose and carries a fenced example naming a wave path, yet must PASS. `1ur6p`'s own change doc mentions `path/to/file.swift` repeatedly but is NOT a control, because no authored change doc is in `SCAFFOLD_DOCS` and the rule never reads it. The placeholder heuristic itself is measured-and-declined: every literal deny-list matches zero of the 56 real declared targets corpus-wide.
- Blocking: the repair lands in `upgrade_extensions.pre_docs_gate`, NOT in `upgrade_wavefoundry.py`. Two lanes disagreed on this and the code settles it: `_load_extension_module` execs the module from inside the zip and binds it before extraction, so the hook is class-a; a repair in the orchestrator would be class-b and arrive one upgrade after the gate it mitigates.
- Blocking: severity is ERROR, and the upgrade must repair a contaminated template BEFORE the docs gate. A docs-lint ERROR sets `failed_phase == "docs_gate"` (`upgrade_wavefoundry.py:2477`), which would halt the upgrade for exactly the already-contaminated repositories AC-6 exists to serve.
- Watchpoint: "scaffold" is an explicit opt-in file set, not a predicate. Existing plan validators deliberately skip the template (`wave_lint_lib/wave_validators.py:900`), so the new rule opts in by name.
- Watchpoint: this change edits no seeds and moves no evaluator version, so no `seed_edit_allowed` gate and no re-Prepare transition are required.
- Context: this repository is NOT affected by the scaffold defect, because wave `1uo1x` pinned it by test here. The gap is that target repositories get prose instruction instead of a gate.
- Withdrawn at readiness: `1upqx` (Completion Notes digest exclusion). Both council seats independently disproved its premise — `## Completion Notes` is defined by no seed, prompt, template, or script, and `wf_close_wave` writes only to `wave.md`, which is not digested, so closing a wave produces zero change-doc churn on a stock repository. Red-team additionally showed the proposed body-only exclusion would not fix the reported shape anyway, because the section is CREATED at close rather than appended to. The disproof is recorded here; the plan document itself was later deleted as redundant, since this record carries the substance. Its 36-document word-boundary figure did NOT reproduce (independent runs gave 51, 23, or 0 depending on variant) and must be re-measured before reuse.

## Review Checkpoints

**SUPERSEDED CLAUSES in the 2026-08-08 prepare-council entry below.** The entry is preserved as recorded, but implementation falsified two of its clauses and they must not be read as current:

1. "AC-6's work lands in `reconcile_scan.py`, not the caller" is **false as delivered**. AC-6 reports from the pre-gate repair (`upgrade_extensions.repair_declaring_scaffold`), because a post-gate scan cannot serve this population: after a successful repair the tree is clean, and after a failed gate `_run_reconciliation_scan` is not reached at all (all three call sites are post-gate, and the summary one is additionally guarded by `not failed_phase`). `reconcile_scan.py` is byte-identical to HEAD and is not a declared review target.
2. "the placeholder check ... now consumes parser output only" is **superseded**: no placeholder check ships at all. Requirement 4 declines the heuristic on measurement, and AC-7 forbids the CHANGELOG from claiming it. The third clause of that same sentence, that the scaffold population is an explicit opt-in file set, remains true.

- **Prepare-phase Wave Council [prepare-council] — 2026-08-08 (re-run after amendment): PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: red-team WITHHELD with a P1 that the amendment pass reproduced this document's OWN recorded defect, one session later. Reconciling AC-3 and AC-5 with the narrowed Requirement 1 struck the retired claims from the AC bodies but left them mandating in a Scope bullet, two Risk rows, AC-4's second control, both AC-Priority rationales and a wave.md watchpoint, so a reader auditing the risk register would still conclude that a repository upgraded before this ships is served by upgrade reconciliation, which the change explicitly proved cannot happen and explicitly did not build. Docs-contract APPROVED with no P1, having reproduced every operator-facing CHANGELOG sentence against executed code including the lane-loss claim end to end (three lanes on a clean template, one on the contaminated one). Folding took FIVE passes, each verified by an independent reverifier that withheld until the last: the sweep was partial four times, missing Requirement 5, Requirement 6, the AEG census row, and finally two live-false clauses inside this very Review Checkpoints section, which three earlier passes never opened. A self-inflicted measurement error was also caught: correcting the census to 58 and undeclaring two review targets in the same fold dropped the true figure to 56, because no other document declared those paths. Five false CHANGELOG claims were corrected across the wave, every one found by review rather than by the author. Final verification CONFIRMED and judged the loop finished on the stated basis that the four prior rounds each found a false statement about delivered behavior and the fifth found none; strongest-alternative: replace the insertion-only fencing repair with a canonical section render, which would delete the entire shape-recognition surface that produced both fence-blindness defects found this wave. Rejected because it would overwrite operator-authored prose inside the section, which the fencing repair provably never does: across every repaired shape the change is insertion-only and zero original lines are lost. Recorded in the Decision Log with that reasoning rather than left implicit under a Scope bullet written before the repair existed)
- **Prepare-phase Wave Council [prepare-council] — 2026-08-08: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: both seats independently FAILED the wave as originally composed, and both P1 sets landed on the same change, `1upqx`. Docs-contract verified that `## Completion Notes` is defined by no seed, prompt, template, or script and that `wf_close_wave` writes only to the undigested `wave.md`, so the plan's central claim that writing the section is a closure step is false on this tree and closing a wave produces zero change-doc churn on a stock repository; it further showed the cited `1uhcb` precedent INVERTS, since that wave's three-part test for granting a digest exclusion is scored zero-for-three by Completion Notes and `1uhcb` rejected `## Session Handoff` on weaker grounds. Red-team added two independent kills: the mandated body-only sentinel substitution would not have fixed the reported shape at all, because the section is CREATED at close rather than appended to, so the heading still enters the canonical body and every AC could have gone green with the defect untouched; and `canonical_review_policy_body` has a THIRD production consumer feeding the receipt-semantic `delivery_council_required`, so the exclusion could have flipped a required delivery council from true to false. Red-team also refuted the coordinator's own 36-document word-boundary census, which does not reproduce at any variant. The wave was re-scoped by WITHDRAWING `1upqx` with the disproof recorded here rather than repairing a plan whose premise had been falsified; the surviving change `1ur6p` carries NO P1 from either seat, and docs-contract stated it would pass that seat independently. Its three red-team P2s are folded: severity was unstated across three conflicting phrasings and an ERROR alone would have aborted the upgrade at `docs_gate` for exactly the contaminated population the change serves, so AC-6a adds a pre-gate repair; the placeholder check would have failed against this wave's OWN artifacts and now consumes parser output only; and the scaffold population was an uncodeable predicate, now an explicit opt-in file set because existing validators deliberately skip the template. A coordinator-found carrier miss was also folded before the seats reported: AC-6's work lands in `reconcile_scan.py`, not the caller; strongest-alternative: route closure narrative to `## Wave Summary` in `wave.md`, which is already non-digested and already generated at close, or generalize to a declared exclusion set with a stated admission test rather than granting a permanent normalizer exception to a heading the framework does not define. Adopted as the recorded path forward for the withdrawn change; the open question underneath, why narrative prose scores review lanes at all, is deferred to its own wave with its own measurement)

- **Seat evidence [red-team] — 2026-08-08:** two P1s, both against `1upqx` and both accepted. Proved by executed probe that the plan's mandated body-only sentinel substitution would not fix the reported shape at all, because `## Completion Notes` is CREATED at close rather than appended to, so the heading still enters the canonical body and the digest still moves; and found a THIRD production consumer of `canonical_review_policy_body` at `server_impl.py:7119` feeding the receipt-semantic `delivery_council_required`, so the proposed exclusion could have flipped a required delivery council from true to false. Also refuted the coordinator's own 36-document word-boundary census, which does not reproduce at any variant (independent runs gave 51, 23, or 0). No P1 against `1ur6p`; its three P2s (unstated severity, placeholder check failing this wave's own artifacts, uncodeable scaffold predicate) are folded.
- **Seat evidence [docs-contract-reviewer] — 2026-08-08:** two P1s against `1upqx`, both accepted and decisive. Verified by repo-wide search that `## Completion Notes` is defined by no seed, no install lifecycle prompt, no `docs/prompts/` surface, no spec, no script, and appears in neither `docs/plans/plan-template.md` nor seed 170's required-section list, so the plan's central claim that writing it is a closure step is false on this tree; `wf_close_wave` writes only to `wave.md`, which is not digested. Further showed the cited `1uhcb` precedent INVERTS: that wave's three-part test for granting a digest exclusion (observed churn source, mandated by a surface, gains an explicit narrate-not-amend rule) is scored zero-for-three by Completion Notes, and `1uhcb` rejected `## Session Handoff` on weaker grounds. Second P1: an undeclared carrier at `seeds/180-implement-feature.prompt.md:71`, which states Progress Log is "the one" section the digest excludes, a singular-exclusivity claim the change would falsify, together with the `review_policy_reconcile.py` propagation seam `1uhcb` used to reach existing repositories. On `1ur6p`: no P1, and the seat stated it would pass independently.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 73 | 1,436,786 |
| implement | 14 | 24,380 |
| review | 64 | 1,189,664 |
| **Total** | **151** | **2,650,830** |

<!-- wave:context-efficiency-state {"generation":152,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":14,"content_source_credit":34732,"derived_artifact_credit":770,"direct_net":24380,"estimated_tokens_saved":24380,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3240,"response_debit":9313,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":73,"content_source_credit":1533599,"derived_artifact_credit":3175,"direct_net":1436786,"estimated_tokens_saved":1436786,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6573,"response_debit":96798,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3383},"review":{"calls":64,"content_source_credit":1304254,"derived_artifact_credit":1449,"direct_net":1189664,"estimated_tokens_saved":1189664,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4873,"response_debit":112512,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":151,"content_source_credit":2872585,"derived_artifact_credit":5394,"direct_net":2650830,"estimated_tokens_saved":2650830,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14686,"response_debit":218623,"source_credit_count":94,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6160},"wave_id":"1ur6o closure-narrative-digest-boundary"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 10 | 0 | 5 | 3,277,046 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":5,"estimated_exploration_avoided":3277046,"surfaced_events":10} -->
<!-- wave:exploration-avoided end -->
