# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-03
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uas8 verified-online-model-set`
Title: Verified Online Model Set

## Objective

Make a verified Hugging Face model download equivalent to the matching offline companion without placing model bytes in the standard feature package. A cache earns the release-pinned v1 identity only after full manifest verification.

## Changes

Change ID: `1uas7-enh verify-downloaded-model-set`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer

Completed At: 2026-08-03

## Wave Summary

Wave `1uas8` (Verified Online Model Set) delivered one change: Verify Downloaded Model Set.

**Changes delivered:**

- **Verify Downloaded Model Set** (`1uas7-enh verify-downloaded-model-set`) — 4 ACs completed. Key decisions: Carry verification metadata in the standard package, not model bytes.
## Watchpoints

- Watchpoint: online adoption must validate the complete manifest, including hashes and revisions, before minting a marker; no name-only or revision-only equivalence.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| standard-feature-pack-omits-online-verification-manifest | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare Council evidence — 2026-08-03:** red-team found no safe path to mint a marker without the full manifest; docs-contract-reviewer found the standard-package/no-model-bytes contract is explicit and consistent.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-03: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: generated feature metadata could drift from the companion file map and falsely mint a v1 cache marker; strongest-alternative: ship model bytes in every feature ZIP — rejected because it breaks the compact source-only feature boundary and makes the optional companion redundant.)

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 21 | 4,018 |
| implement | 4 | 867 |
| review | 117 | 1,576,896 |
| **Total** | **142** | **1,581,781** |

<!-- wave:context-efficiency-state {"generation":144,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":4,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":867,"estimated_tokens_saved":867,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28,"response_debit":536,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":21,"content_source_credit":18530,"derived_artifact_credit":1742,"direct_net":4018,"estimated_tokens_saved":4018,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3305,"response_debit":16314,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3365},"review":{"calls":117,"content_source_credit":1825086,"derived_artifact_credit":2185,"direct_net":1576896,"estimated_tokens_saved":1576896,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14084,"response_debit":237637,"source_credit_count":71,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":142,"content_source_credit":1843616,"derived_artifact_credit":3927,"direct_net":1581781,"estimated_tokens_saved":1581781,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17417,"response_debit":254487,"source_credit_count":85,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6142},"wave_id":"1uas8 verified-online-model-set"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 6 | 5,597,606 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":5597606,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->
