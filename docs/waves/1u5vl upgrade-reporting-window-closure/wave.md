# Wave Record

Owner: Engineering
Status: implementing
Last verified: 2026-08-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1u5vl upgrade-reporting-window-closure`
Title: Upgrade Reporting Window Closure

## Objective

Close the old-code reporting window: when this wave closes, the primary-phase upgrade summary and the reconciliation scan are produced by the freshly extracted code behind a pinned, permanently tested entry-point contract, so every future sentinel-carried reporting change takes effect on the upgrade that installs it. Now, because three consecutive releases each produced a false "the fix does not work" field report from exactly this window, and the operator has directed this change ship inside the 1.15.0 release so 1.16's reporting arrives clean.

## Changes

Change ID: `1u44o-enh post-extract-summary-subprocess-backstop`
Change Status: `planned`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (single `fix` workstream)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

## Wave Summary

Single-change enhancement wave delegating the primary-phase summary emit (the one old-code reporting site; the cleanup emit already runs fresh-process new code) to a subprocess on the freshly extracted tree, behind a frozen standalone-flag contract with a schema version token, four-class marked degradation, and a permanent contract test guarding the fielded runner population. The covered class is stated honestly: sentinel-carried summary fields only; server-resident response fields (runner_stale and kin) still require a host restart and are excluded.

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

*Machine review evidence — 8 records; 1 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| docs-contract-reviewer | pending | no current executed approval | record approval evidence for docs-contract-reviewer |
| release-reviewer | pending | no current executed approval | record approval evidence for release-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 91 | 2,009,308 |
| implement | 1 | 651 |
| **Total** | **92** | **2,009,959** |

<!-- wave:context-efficiency-state {"generation":75,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":651,"estimated_tokens_saved":651,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9,"response_debit":771,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":91,"content_source_credit":2198606,"derived_artifact_credit":2449,"direct_net":2009308,"estimated_tokens_saved":2009308,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8210,"response_debit":186902,"source_credit_count":53,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3365}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":92,"content_source_credit":2198606,"derived_artifact_credit":2449,"direct_net":2009959,"estimated_tokens_saved":2009959,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8219,"response_debit":187673,"source_credit_count":53,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4796},"wave_id":"1u5vl upgrade-reporting-window-closure"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
