# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20gz3 uv-release-bootstrap`
Title: Uv Release Bootstrap

## Objective

Refresh the official 1.29.0 bootstrap to uv 0.12.17 and its verified wheel inventory while preserving existing uv installations. Qualify the changed release source and build the official feature/model artifacts.

## Changes

Change ID: `20gz2-maint refresh-uv-release-bootstrap`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (coordinator only)
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-14

## Wave Summary

Wave `20gz3` (Uv Release Bootstrap) delivered one change: Refresh the uv bootstrap pin for release.

**Changes delivered:**

- **Refresh the uv bootstrap pin for release** (`20gz2-maint refresh-uv-release-bootstrap`) — 2 ACs completed. Key decisions: Refresh only the exact bootstrap pin and its full wheel hashes
## Watchpoints

- Watchpoint: do not force-upgrade an existing uv or change setup control flow.
- Finish source edits before qualification; run packaging profiles sequentially.
- Native Windows execution remains outside this macOS qualification.
- Required reviewers use fresh contexts and temporary evidence; no permanent evidence folder.
- Allocation: coordinator owns the small constant edit; independent review contexts use gpt-6.1-sol/high for scoped checks and synthesis. Requested model settings are recorded; actual runtime identity is unavailable unless the host reports it.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 153 | 215,401 |
| implement | 137 | 0 |
| review | 44 | 128,787 |
| **Total** | **334** | **344,188** |

<!-- wave:context-efficiency-state {"generation":221,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":137,"content_source_credit":312015,"derived_artifact_credit":0,"direct_net":-67597,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3955,"response_debit":378593,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2936},"plan":{"calls":153,"content_source_credit":806756,"derived_artifact_credit":1937,"direct_net":215401,"estimated_tokens_saved":215401,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25418,"response_debit":574377,"source_credit_count":61,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6503},"review":{"calls":44,"content_source_credit":269596,"derived_artifact_credit":1260,"direct_net":128787,"estimated_tokens_saved":128787,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4642,"response_debit":140358,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":334,"content_source_credit":1388367,"derived_artifact_credit":3197,"direct_net":276591,"estimated_tokens_saved":344188,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":34015,"response_debit":1093328,"source_credit_count":108,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12370},"wave_id":"20gz3 uv-release-bootstrap"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 4 | 435,017 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":435017,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Publication (2026-10-12): operator explicitly authorized commit, push and GitHub release. Source `f8537e1a` and release stamp `d20ed5f4` are pushed; tag `v1.29.0` resolves to the latter. Official [1.29.0 release](https://github.com/coryhacking/wavefoundry/releases/tag/v1.29.0) is public with both assets and the two qualification exceptions disclosed. Final feature `wavefoundry-1.29.0.pw75.zip` SHA256 `1faa86e3c5615c2ba5e6c21af18e536b15e74e92ea54e894cc5b772cdbab2bb7`; model asset SHA256 `3a7cfb7b14ff5c60d00dc24819b7bddb5a6beacdb9d79c38ead476e49b82cc7d`. GitHub sizes/digests match local files; CRC, all 248 source counterparts and all 15 model hashes pass. Candidate-to-release content differences are limited to VERSION and upgrade-protocol build metadata, including nested bridge payloads. The paused lifecycle status is unchanged.

- Delivery (2026-10-12): code, security, QA, release and council approvals recorded; no findings remain. Final QA/release/chair checks inspected the actual archives and current qualification metadata without rerunning tests. Default qualification is green (12,402 tests, 185 files, 12 skips); the complete red second/declared reports remain explicitly deferred for this release under AC-3. Follow-up 20h6q owns the combined log-tail assertion; no timing conclusion is claimed under concurrent load. The original full council roster and adversarial primer remain the review basis; the final artifact pass was scoped to QA, release and chair. Wave remains paused pending operator closure.
- Artifacts: feature `wavefoundry-1.29.0.pw6p.zip`, SHA256 `e766964f6334d33a5db1ed7e0365aed6087114563145dda365ca16acb80bea5a`; models `wavefoundry-models-3.zip`, SHA256 `c3de8d60e8dd55dd6c357f8256af4748a90b089ec92d6c677671b22c56030142`. Verified CRC, safe unique paths, 248 exact source counterparts, stamped version/changelog, 18 pinned uv wheel hashes, 15 model hashes and license notices. Native Windows execution is not claimed. These candidate checks preceded the final publication recorded above.

- Readiness: full adversarial primer followed by independent architecture-reviewer, security-reviewer, qa-reviewer and reality-checker fixed seats; rotating release-reviewer and separate code-reviewer. Council unanimously approved after an anonymous merits pass and fixed-seat consideration of the release alternative. No blockers or material disagreements. Exact registry comparison, real binary exercise and sequential final-source qualification remain delivery obligations; native Windows execution is not claimed.

## Progress Log

- 2026-10-14: Operator authorized closing all six paused waves, committing/pushing and a local 1.31.0 pack, with timing investigation still deferred and one shared default qualification run. That run completed 11,671 tests / 187 files / 12 skips in 884.077s, exit 1: test_tensorwell_client.ClientTests.test_cli_exact_child_timeout_bounded_capture expected the oversized-output ValueError but the child wait reached its deadline and raised TimeoutError. The projection-timing file passed. Source-only independent triage does not establish a capture-cap defect or a harmless scheduling flake; final QA remains unproven. All 60 reviewed source hashes stayed unchanged. No retry or profile run followed the failed default; no current green receipt, closure or new pack is claimed. Compact report remains in ignored cache (close-pack-1.31-default.json); routine log remains temporary. Existing source reviews and terminal repairs stand. Memory proposals add no action beyond canonical tests/guidance, so none were selected; folders retain only wave/change records and typed ledgers.
