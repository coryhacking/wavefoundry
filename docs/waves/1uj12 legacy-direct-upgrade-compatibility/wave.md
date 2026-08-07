# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uj12 legacy-direct-upgrade-compatibility`
Title: Legacy Direct Upgrade Compatibility

## Objective

Allow supported protocol-1 installations from 1.8.0 onward to upgrade directly to the current protocol-2 release. Preserve the bridge's strict integrity boundary while removing the arbitrary requirement to stage through 1.14.0.

## Changes

Change ID: `1uj11-bug legacy-direct-upgrade-compatibility-floor`
Change Status: `implemented`

Change ID: `1ulnt-bug wave-admission-metadata-and-ledger-readiness-projection`
Change Status: `implemented`

Change ID: `1ulnu-enh defer-ac-refreshes-review-receipt`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-08-06

## Wave Summary

Wave `1uj12` (Legacy Direct Upgrade Compatibility) delivered 3 changes: Legacy direct-upgrade compatibility floor, Wave admission metadata and ledger readiness projection, and Deferring an AC refreshes its review receipt.

**Changes delivered:**

- **Legacy direct-upgrade compatibility floor** (`1uj11-bug legacy-direct-upgrade-compatibility-floor`) — 3 ACs completed. Key decisions: Support direct protocol-1 upgrades from 1.8.0+, not only 1.14.0.
- **Wave admission metadata and ledger readiness projection** (`1ulnt-bug wave-admission-metadata-and-ledger-readiness-projection`) — 5 ACs completed. Key decisions: Automate only deterministic metadata; make the event ledger the sole modern readiness authority; retain prose only for legacy waves.
- **Deferring an AC refreshes its review receipt** (`1ulnu-enh defer-ac-refreshes-review-receipt`) — 5 ACs completed. Key decisions: Refresh the receipt automatically but never approvals.
## Watchpoints

- Blocking: do not activate or implement until the active `1ui1d review-loop-friction` wave is closed.
- Watchpoint: do not weaken host quiescence, hash, containment, rollback, protocol, or explicit second-hop checks while broadening version eligibility.

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
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-05: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: broaden legacy upgrade eligibility without weakening the bridge, while replacing only deterministic lifecycle metadata and duplicate typed/prose readiness reporting; strongest-alternative: remove either legacy guard without preserving its authority boundary, rejected because it would claim untested compatibility or weaken legacy safety.)

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 57 | 722,643 |
| implement | 26 | 1,554,937 |
| review | 36 | 808,265 |
| **Total** | **119** | **3,085,845** |

<!-- wave:context-efficiency-state {"generation":124,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":26,"content_source_credit":1599064,"derived_artifact_credit":0,"direct_net":1554937,"estimated_tokens_saved":1554937,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":772,"response_debit":44786,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":57,"content_source_credit":812625,"derived_artifact_credit":4769,"direct_net":722643,"estimated_tokens_saved":722643,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4157,"response_debit":104204,"source_credit_count":47,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13610},"review":{"calls":36,"content_source_credit":861742,"derived_artifact_credit":4847,"direct_net":808265,"estimated_tokens_saved":808265,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5622,"response_debit":52702,"source_credit_count":62,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":119,"content_source_credit":3273431,"derived_artifact_credit":9616,"direct_net":3085845,"estimated_tokens_saved":3085845,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10551,"response_debit":201692,"source_credit_count":134,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15041},"wave_id":"1uj12 legacy-direct-upgrade-compatibility"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 4 | 4,709,089 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":4709089,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
