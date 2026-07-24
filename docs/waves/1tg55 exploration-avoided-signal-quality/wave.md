# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-23
review-evidence-source: events.jsonl

wave-id: `1tg55 exploration-avoided-signal-quality`
Title: Exploration Avoided Signal Quality

## Objective

Make the estimated-exploration-avoided metric honest in both directions: the wave.md block renders only when nonzero (a permanently-empty table is noise), and the grounding `Source exploration cost` stamp survives supersession (the minting seam currently drops it on rewrites and supersedes-adds — exactly the records that surface most as advisories). Crediting surfaces are deliberately NOT expanded; if the metric stays zero after these fixes, that becomes the recorded evidence for removing it.

## Changes

Change ID: `1tdl8-enh exploration-avoided-render-and-cost-propagation`
Change Status: `implemented`

Completed At: 2026-07-23

## Wave Summary

Wave `1tg55` (Exploration Avoided Signal Quality) delivered one change: Exploration-Avoided: Conditional Rendering and Cost Propagation. Notable adjustments during implementation: Exploration-Avoided: Conditional Rendering and Cost Propagation: Full-suite verification took three runs to land honestly: two loaded runs failed in `test_repeated_warm_estimator_and_projection_budgets` (a warm p95 25ms budget assertion; 29.7ms under concurrent suite/MCP load), which also retroactively explains the unnamed 1tbt7-review flake; the test passes in isolation and the QUIET full run is green: 6,181 tests across 59 files OK, zero failures. Docs gate clean. The flake is captured as active memory `1tdvh-mem warm-perf-budget-test-flakes-under-load` and is follow-up material (load-aware budget), out of this wave's scope — the timing path is untouched by this change and the first failure predates it.

**Changes delivered:**

- **Exploration-Avoided: Conditional Rendering and Cost Propagation** (`1tdl8-enh exploration-avoided-render-and-cost-propagation`) — 4 ACs completed. Key decisions: Render only when nonzero; keep the machine state comment.; Inherit cost through supersession at the one minting seam.
## Watchpoints

- Watchpoint: never rewrite closed waves' historical zero tables; the conditional render applies to future flushes only. Follow-up if the metric remains zero after these fixes: remove it entirely, citing that evidence.
- Watchpoint: inheritance applies only through explicit supersession links; a blocking concern in review would be any path that stamps cost onto a record with no supersession lineage.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| rewrite-inheritance-not-visible-at-mint-seam | do_now | no | completed | wave-council-readiness |
| zero-cost-key-omission-breaks-draft-consumers | do_now | no | completed | wave-council-readiness |
| zero-render-contract-allows-empty-visible-section | do_now | no | completed | wave-council-readiness |

*Machine review evidence — 36 records; 11 runs; 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Delivery-phase Wave Council [delivery-council] — 2026-07-23: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the rewrite path's missing supersedes would have left the primary defect case unfixed — live-caught in implementation testing and repaired with an explicit-cost pass at the rewrite site, pinned by the inheritance matrix; strongest-alternative: treating the loaded-run suite failures as blockers — resolved by isolation plus quiet-run evidence identifying the pre-existing warm-p95 budget flake, captured as a typed memory and named follow-up.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-23: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: supersession inheritance stamping a wrong grounding cost onto a semantically new record — bounded by inheritance flowing only through explicit supersession links where the grounding exploration is shared by construction, with explicit cost always winning; strongest-alternative: removing the metric now — rejected as premature, the propagation fix may light it up, and staying zero afterward becomes the recorded removal evidence.)

## Prepare Review Evidence

Readiness council pass, 2026-07-23 (single change; claims verified against the tree):

- reality-checker: every load-bearing claim was censused before drafting — the credit preconditions (exact-target match, positive stamped cost, action-time surface, open wave) resolve at `exploration_avoided.py` `estimate_credit` (the `confidence != 1.0` skip and nonpositive-cost skip) and `server_impl.py` `_credit_exploration_avoided_surface`; 19 of 82 records carry positive cost; the minting seam `_memory_add_response_locked` demonstrably passes no cost (the `_render` call carries no such kwarg); `wf_audit` already gates its display on `> 0`; lint carries no exploration-avoided validation, so conditional rendering cannot trip the docs gate.
- red-team: strongest challenge — inheritance stamping a wrong cost on a new record; bounded to explicit supersession lineage with explicit-cost override, and pinned by the non-superseding-add regression. Second — a hidden consumer of the always-rendered table; censused: audit reads the store, nothing parses the table, and both render states are pinned by tests. Third — flush regressions on the zero-to-nonzero transition; required as an explicit AC with idempotence in both states.
- qa-reviewer: the AC matrix is falsifiable end to end (both render states plus transition, rewrite inheritance, supersedes-add inheritance, explicit override, non-superseding non-inheritance, backfill zero-omission, estimator byte-unchanged); existing estimator invariant tests remain untouched behavioral controls.
- docs-contract-reviewer: the non-expansion of crediting surfaces is recorded as a Decision Log entry with the anti-inflation rationale, and the removal follow-up is named with its evidence condition; reference-doc updates are scoped in AC-4.

Synthesis verdict: READY.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

Delivery council pass, 2026-07-23 (single change; claims verified against the tree and the suite):

- reality-checker: all three behaviors verified on disk — `render_checkpoint_block` emits markers plus machine state only at zero totals with the full section only when nonzero; the minting seam carries `_source_exploration_cost` with explicit-wins-then-inherit ordering gated to positive costs and supersession lineage; `memory_supply` normalizes a zero measured cost to an omitted stamp. The live render probe is this very ledger write: the wave's own zero table must collapse to the compact marker form in this projection rebuild.
- red-team: strongest challenge — the primary defect case silently unfixed; it nearly WAS: implementation-time testing live-caught that the rewrite path never passes `supersedes` into the minting call, so param-keyed inheritance would never have fired for rewrites; the rewrite site now passes the predecessor's cost explicitly, and the inheritance matrix pins it. Second — wrong-cost stamping; bounded to explicit lineage, positive-only, explicit-wins, with the non-superseding and zero-predecessor regressions. Third — flush regressions; the both-direction tests include legacy-full-table collapse and single-heading idempotence.
- qa-reviewer: `test_memory_records` 168 OK including the render transition matrix, five-case inheritance matrix, and propose zero-omission; quiet full suite 6,181 tests across 59 files OK with zero failures (two loaded runs failed only in the pre-existing warm-p95 budget flake, isolated, root-caused, and captured as memory `1tdvh-mem warm-perf-budget-test-flakes-under-load` — the timing path is untouched by this change).
- docs-contract-reviewer: the estimated-exploration-avoided reference carries the two new invariants (nonzero-only rendering; grounding survives supersession) and the memory README's cost section documents omission plus inheritance; the crediting-surface non-expansion stands as a recorded decision with the removal follow-up's evidence condition named.

Synthesis verdict: PASS.


- operator-signoff: approved 2026-07-23 (operator directed the change, reviewed the delivery report incl. the live zero-table collapse and the three terminal plan-review chains, and instructed close in session)

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 33 | 455,593 |
| implement | 7 | 2,475 |
| review | 35 | 781,997 |
| **Total** | **75** | **1,240,065** |

<!-- wave:context-efficiency-state {"generation":55,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":7,"content_source_credit":3211,"derived_artifact_credit":17,"direct_net":2475,"estimated_tokens_saved":2475,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":305,"response_debit":2021,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1573},"plan":{"calls":33,"content_source_credit":513252,"derived_artifact_credit":258,"direct_net":455593,"estimated_tokens_saved":455593,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5383,"response_debit":55725,"source_credit_count":72,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"review":{"calls":35,"content_source_credit":876810,"derived_artifact_credit":1126,"direct_net":781997,"estimated_tokens_saved":781997,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6138,"response_debit":91013,"source_credit_count":36,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1212}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":75,"content_source_credit":1393273,"derived_artifact_credit":1401,"direct_net":1240065,"estimated_tokens_saved":1240065,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11826,"response_debit":148759,"source_credit_count":109,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5976},"wave_id":"1tg55 exploration-avoided-signal-quality"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
