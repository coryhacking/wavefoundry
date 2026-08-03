# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-03
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1u5vl upgrade-reporting-window-closure`
Title: Upgrade Reporting Window Closure

## Objective

Close the old-code reporting window: when this wave closes, the primary-phase upgrade summary and the reconciliation scan are produced by the freshly extracted code behind a pinned, permanently tested entry-point contract, so every future sentinel-carried reporting change takes effect on the upgrade that installs it. Now, because three consecutive releases each produced a false "the fix does not work" field report from exactly this window, and the operator has directed this change ship inside the 1.15.0 release so 1.16's reporting arrives clean.

## Changes

Change ID: `1u44o-enh post-extract-summary-subprocess-backstop`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (single `fix` workstream)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-08-01

## Wave Summary

Wave `1u5vl` (Upgrade Reporting Window Closure) delivered one change: Build Upgrade Summaries and Post-Extract Reporting on Freshly Extracted Code. Notable adjustments during implementation: Build Upgrade Summaries and Post-Extract Reporting on Freshly Extracted Code: Implementation complete; change marked implemented. All docs surfaces landed (ADR `1u49j`, cross-cutting pointer, layering-rules Boundary Invariants row, data-and-control-flow paragraph, mcp-tool-surface provenance sentence, CHANGELOG Upgrading item 8 + Fixed bullet, seed-160 disclosure with the gate opened and closed around both seed edits, rendered prompt mirror). Operator mid-implementation clarification (tripwire-not-wall contract framing) folded into ADR, module docstrings, argparse help, contract-test docstring, seed/prompt disclosure, layering row, CHANGELOG. Verification: docs-lint ok (`wf_validate_docs` twice, after each docs pass); seam cluster together (test_upgrade_wavefoundry, test_review_policy, test_index_state_store, test_upgrade_protocol, test_server_tools, test_reconcile_scan): 2131 tests OK; full suite: 6690 tests / 61 files OK; 1u44n clusters 14 tests OK. Em-dash rule enforced across every added line (scripted pass over diff-added lines; zero remaining in authored text).; Build Upgrade Summaries and Post-Extract Reporting on Freshly Extracted Code: Six-lane prepare review (red-team seat, code, qa, architecture, docs-contract/rotating seat, release) of the first draft; consolidated repair pass folded. Red-team NOT-READY corrections: the covered class split honestly (sentinel-carried vs server-resident; runner_stale is server-resident and out of this remedy's reach), the entry-point stability contract promoted to requirement 5, parent-only-facts input carrier promoted into requirement 1, the last-wins sentinel hazard closed in requirement 1/AC-2, and the two refuted Decision Log absolutes rewritten (a pre-emit hook seam DOES exist and is rejected on fail-safety; the old parser is passthrough, field-proven by pg5l's new fields surfacing through the pg1a server). Code lane confirmed the pg1a mechanism structurally (2-tuple unpack vs 3-channel return, swallowed), the 18-key source census (only skipped_scan_locations is memory-only), the cleanup emit already running fresh-process new code, and the capture-and-re-emit transport requirement. QA lane: AC-1 schema-divergent vacuity guard, parser-side end-to-end coverage, marker bounder-survivability, four enumerated failure classes, and the full re-point census including two AST pins. Architecture lane: standalone-flag identity (not hook, not import), lock-as-input with old-schema tolerance, stdlib-only import surface, ADR as canonical home, layering-rules and data-and-control-flow additions. Docs lane: the phantom "changelog template guidance" surface re-pointed at the living CHANGELOG Upgrading section, AC-4 made congruent with the last-window residual, drafted disclosure adopted as the acceptance target. Release lane: commit-before-implement precondition (rebase alternative struck), the contract test as the standing guard for the fielded runner population, pack-contents and release-preflight checks clean.

**Changes delivered:**

- **Build Upgrade Summaries and Post-Extract Reporting on Freshly Extracted Code** (`1u44o-enh post-extract-summary-subprocess-backstop`) — 7 ACs completed. Key decisions: Generalize the fresh-code producer rather than adding per-field bridges; Runner-side delegation is sufficient for sentinel-carried fields; the parser needs no bridge
## Watchpoints

- Blocking precondition: the 1u44n-era tree (two closed waves' delivery-verified state, uncommitted on `3870201b`) is COMMITTED before the first implementation edit. `upgrade_wavefoundry.py` carries that state and is a named fragile file; there is no rebase alternative (release lane, 2026-08-01).
- Watchpoint: the entry-point contract (requirement 5) is permanent, old-calls-new, additive-only. It is a fixed standalone flag, NOT a hook (exit-3 fail-fatal semantics) and NOT an in-process import (the pg1a defect mechanism). Missing entry point is a marker-carrying degradation, never a silent no-op.
- Watchpoint: delegate the PRIMARY emit only. The cleanup emit already runs in a fresh post-extract process on new code; wrapping it adds a failure mode for zero window closure.
- Watchpoint: exactly one sentinel per run. The server parser is last-sentinel-wins; the delegated emit and the parent fallback must be mutually exclusive by construction, with the ordering hazard driven by a test.
- Watchpoint: the disclosure must carry the server-resident exclusion and the last-window residual (this change's own installing upgrade), or it ships the fourth false field report itself.
- Watchpoint: `upgrade_wavefoundry.py` fragile-file rule (`1u0dl-mem`): rerun the phase-transition seam test cluster together, not just the touched surfaces. The two AST pins (`test_upgrade_wavefoundry.py` emit-call-count; `test_reconcile_scan.py` exhaustive emitter set) break by construction and are re-point-not-delete.
- Watchpoint: the seed-160 edit (line ~81) is gated: open `seed_edit_allowed` before, close immediately after; line ~91 stays untouched.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the first draft's covered class bundled a motivating instance the remedy cannot reach — `runner_stale` is computed in the SERVER's response assembly, never travels in the sentinel, and only a host restart cures it — and the draft's two supporting absolutes were refuted against the tree (a pre-emit hook seam DOES exist, `post_index_update` dispatches before the primary emit, rejected instead on exit-3 fail-fatality and last-wins sentinel collision; the old server's parser is passthrough-with-caps, field-proven by the pg1a-era server surfacing pg5l's new fields), so the plan was rewritten with the honest sentinel-carried vs server-resident split, a pinned permanent entry-point contract (fixed standalone flag, lock input with old-schema tolerance, versioned sentinel envelope with unrecognized-token-degrades, contract test locking name, argv, envelope, and sentinel prefix), the parent-only-facts input carrier, and mutual-exclusion of delegated and fallback emits; strongest-alternative: move authoritative emission into an already-fresh spawned phase (the topology whose first-time success the prior art actually proves) — rejected because the default upgrade flow runs no such phase and last-sentinel-wins parsing collides, recorded in the requirement 6 ADR as the named alternative. Both seats verified claims code-grounded: the pg1a defect mechanism confirmed structurally (pfxp-era 2-tuple unpack against the pg1a 3-channel return, swallowed by the blanket except into empty channels), the 18-key summary-input census (only `skipped_scan_locations` is memory-only), and all five lanes' repairs re-adjudicated on the final bytes with six CONFIRM verdicts.)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 19 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 93 | 2,006,928 |
| implement | 17 | 850,420 |
| review | 24 | 139,530 |
| **Total** | **134** | **2,996,878** |

<!-- wave:context-efficiency-state {"generation":119,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":17,"content_source_credit":878698,"derived_artifact_credit":0,"direct_net":850420,"estimated_tokens_saved":850420,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":252,"response_debit":29457,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":93,"content_source_credit":2198606,"derived_artifact_credit":2449,"direct_net":2006928,"estimated_tokens_saved":2006928,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8228,"response_debit":189264,"source_credit_count":53,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3365},"review":{"calls":24,"content_source_credit":167310,"derived_artifact_credit":4212,"direct_net":139530,"estimated_tokens_saved":139530,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5634,"response_debit":27704,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":134,"content_source_credit":3244614,"derived_artifact_credit":6661,"direct_net":2996878,"estimated_tokens_saved":2996878,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14114,"response_debit":246425,"source_credit_count":78,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6142},"wave_id":"1u5vl upgrade-reporting-window-closure"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 1 | 3,641,306 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":3641306,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
