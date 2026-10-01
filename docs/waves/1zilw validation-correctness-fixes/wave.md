# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-30
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zilw validation-correctness-fixes`
Title: Validation Correctness Fixes

## Objective

Fix three correctness gaps from the v1.28.0 downstream validation and the 1zf1w follow-up: archived wave ledgers are treated as machine authority, the retired arctic-embed-xs caches are cleaned up, and three index-status tests no longer depend on the test process's age.

## Changes

Change ID: `1zicn-bug archive-ledger-exclusion`
Change Status: `implemented`

Change ID: `1zico-bug retire-arctic-xs-caches`
Change Status: `implemented`

Change ID: `1zicp-bug index-status-test-process-age`
Change Status: `implemented`

## Participants

- Coordinator: wave coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-09-30

## Wave Summary

Wave `1zilw` (Validation Correctness Fixes) delivered 3 changes: Archived Wave Ledgers Are Not Recognised as Machine Authority, Caches of the Retired arctic-embed-xs Model Are Never Removed, and Index Status Tests Fail When the Test Process Is Younger Than About 28 Seconds. Notable adjustments during implementation: Archived Wave Ledgers Are Not Recognised as Machine Authority: Delivery review: red-team and the four lanes (code, qa, release, security) approved, every mutation killed by the suite. Advisory taken: the code and test comments cited wave 1zicq instead of 1zilw (corrected). Not taken: a boundary test pinning the 2 s pid-reuse tolerance (pre-existing gap from 1zc7n, out of scope; follow-up); the shared custom-marker fixture uses symlinks, which can error on Windows without symlink privilege (pre-existing exposure shared with `test_custom_marker_requires_exact_legacy_inventory`). Full suite: 10200 tests OK; Caches of the Retired arctic-embed-xs Model Are Never Removed: Delivery review: red-team and the four lanes (code, qa, release, security) approved, every mutation killed by the suite. Advisory taken: the code and test comments cited wave 1zicq instead of 1zilw (corrected). Not taken: a boundary test pinning the 2 s pid-reuse tolerance (pre-existing gap from 1zc7n, out of scope; follow-up); the shared custom-marker fixture uses symlinks, which can error on Windows without symlink privilege (pre-existing exposure shared with `test_custom_marker_requires_exact_legacy_inventory`). Full suite: 10200 tests OK; Caches of the Retired arctic-embed-xs Model Are Never Removed: Implemented. Four xs entries in `_RETIRED_MODEL_ALLOWLIST` (fastembed, clean-onnx, static-onnx, coreml). Tests: the exact-allowlist enumeration now pins 17 default and 7 custom-scope ids (xs adds two custom); the residue census allows exactly the three distinct xs constants and still requires every production hit to be an allowlisted constant; new `test_arctic_xs_components_follow_the_existing_ownership_and_veto_rules` (default removal, marked custom removed, unmarked custom unowned and kept, active-authority veto for each kind). `test_upgrade_wavefoundry.py` and `test_model_bundle.py` 592 OK.

**Changes delivered:**

- **Archived Wave Ledgers Are Not Recognised as Machine Authority** (`1zicn-bug archive-ledger-exclusion`) — 3 ACs completed. Key decisions: Extend the shared predicate
- **Caches of the Retired arctic-embed-xs Model Are Never Removed** (`1zico-bug retire-arctic-xs-caches`) — 3 ACs completed. Key decisions: Keep the custom-scope ownership rule unchanged; Supersede `1v0qz` Requirement 7's xs exclusion and BAAI-only cleanup census
- **Index Status Tests Fail When the Test Process Is Younger Than About 28 Seconds** (`1zicp-bug index-status-test-process-age`) — 2 ACs completed. Key decisions: Fix the fixtures, not the tolerance
## Watchpoints

- Watchpoint: retired-model cleanup keeps every existing gate; a custom-scope xs copy is removed only with the v1 marker, otherwise reported unowned.
- Follow-up: profile-portable fixtures (validation request 7) are deferred to a separate wave.

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
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: setting `archive_rel` in the shared `unvalidated_record_roots` to make the archive branch fire would silently change the indexer's chunk-tagging fallback; resolved by deriving the archive location locally inside the predicate; strongest-alternative: leave the xs caches in place per the `1v0qz` scope clause, rejected because that clause bounded the supplier request and the operator now asks for xs removal)
- Prepare council seat evidence (2026-09-30): red-team approved all three changes with notes (local archive derivation; marked custom xs copies are set-1 owned), folded in; security-reviewer approved (the secrets-scan exemption is the non-git fallback walk only, parity with live ledgers; removal reuses `_remove_retired_component`).
- Readiness lanes (2026-09-30): round 1 code-reviewer and qa-reviewer blocked on `test_retired_model_residue_census_is_closed` forbidding xs in the cleanup source; release-reviewer approved. Repaired in 1zico (Requirement 3, census amendment, supersession recorded); scoped round 2 by the same lanes approved. Reviewer models: requested opus for all council seats and lanes (judgment work); observed runtime identity unknown.

- **Delivery-phase Wave Council [delivery-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the 1zicp tests would pass even if the 2 s pid-reuse tolerance were deleted, so they prove the flake fixed without pinning the tolerance; recorded as a follow-up, since the gap predates this wave; strongest-alternative: derive retired cache names from model-set history instead of a hand-written allowlist, rejected as broader than this fix; disagreements: none)
- Delivery seat and lane evidence (2026-09-30): red-team approved with mutations reproduced; code, qa, release and security approved (mutations M1 to M4 and four pid-guard mutations killed). Advisory taken: code and test comments cited wave 1zicq, corrected to 1zilw. Full suite: 10200 tests OK. Reviewer models: requested opus for both delivery reviewers; observed runtime identity unknown.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 35 | 713,860 |
| implement | 6 | 45,941 |
| review | 10 | 23,520 |
| **Total** | **51** | **783,321** |

<!-- wave:context-efficiency-state {"generation":52,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":6,"content_source_credit":49172,"derived_artifact_credit":0,"direct_net":45941,"estimated_tokens_saved":45941,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":68,"response_debit":4337,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1174},"plan":{"calls":35,"content_source_credit":773874,"derived_artifact_credit":1089,"direct_net":713860,"estimated_tokens_saved":713860,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2903,"response_debit":62009,"source_credit_count":46,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":10,"content_source_credit":39521,"derived_artifact_credit":1308,"direct_net":23520,"estimated_tokens_saved":23520,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1901,"response_debit":17724,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":51,"content_source_credit":862567,"derived_artifact_credit":2397,"direct_net":783321,"estimated_tokens_saved":783321,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4872,"response_debit":84070,"source_credit_count":59,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7299},"wave_id":"1zilw validation-correctness-fixes"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 3 | 2,532,843 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":2532843,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
