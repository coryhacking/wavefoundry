# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21kbd setup-provider-preflight`
Title: Setup Provider Preflight

## Objective

Operators running setup receive an actionable provider-selection diagnosis before incompatible local model preparation, while their published index remains intact. Reachable qualified Tensorwell avoids local preparation; supported local execution and explicit rebuilds retain their existing authority.

## Changes

Change ID: `21kbc-enh setup-provider-preflight-before-local-warmup`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (setup/provider/indexer/tests), coordinator (documentation)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-26

## Wave Summary

Wave `21kbd` (Setup Provider Preflight) delivered one change: Diagnose setup provider access before incompatible local warmup.

Intent outcome: achieved for the admitted mechanism in controlled execution, independently confirmed by QA after repair. Canonical qualification passed 12,228 tests across 213 files, with 12 existing skips, in 739.352 seconds; all six reviewed file identities remain unchanged. Eight public setup controls show actionable refusal before incompatible or narrowly unverified local preparation, qualified-service preparation avoidance, preserved supported alternatives and unchanged published SQLite state. Repeated selection checks and the direct indexer guard protect later boundaries; guard-removal mutants expose actual unwanted preparation. QA-21KBD-001 corrected the earlier provisional claim: fresh-worker tests initially failed because cleanup removed NumPy; independent code and QA now pass all eight without preload and reproduce the original fault with an in-memory old-behavior mutant. All five delivery lanes approve. Native model execution, the exact historical selection failure and field time savings remain unproven.

**Changes delivered:**

- **Diagnose setup provider access before incompatible local warmup** (`21kbc-enh setup-provider-preflight-before-local-warmup`) — 5 ACs completed. Key decisions: Bound uncertainty refusal to implicit Tensorwell fallback with recognized full provenance and a probe-dependent GPU whose CPU route is INT8; Select bounded early compatibility assessment plus selection diagnostics
## Watchpoints

- Watchpoint: implementation, required review and operator-authorized closure complete.
- Preserve existing precision rules and the final indexer guard; do not silently turn setup into a rebuild.
- The first-run Tensorwell rejection reason is unverified; process restrictions are an inference, not a confirmed transport diagnosis.
- One coupled implementation writer; distinct reviewer questions and bounded probes. No global local-fallback ban.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-21KBD-001 | do_now | no | completed | qa-reviewer, code-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-10-26: Operator authorized closure, commit and push. Retrospective: test cleanup must restore only owned module bindings; whole-cache restoration can unload lazy native imports and an earlier ordered green run can hide the failure. Fresh-worker controls and old-behavior mutants substantiate the repair in maintained tests and typed evidence. The bounded early-refusal policy and prediction-versus-execution distinction are already captured in the plan and maintained setup guidance, so no duplicate memory was added; memory_propose dry-run produced no eligible candidates. Preserved all 30 owned work files with matching hashes at `/private/tmp/wavefoundry-21kbd-retained-ju5_4fk8` before automatic cleanup, including dirty-tree baselines, historical fingerprints, primer, probes and qualification log. Retained files are local supporting history; durable approval authority remains in events.jsonl and the implemented controls remain in tests.

2026-10-25: Intent outcome: achieved for the admitted mechanism in controlled execution, independently confirmed by QA after repair. Canonical qualification passed 12,228 tests across 213 files, with 12 existing skips, in 739.352 seconds; all six reviewed file identities remain unchanged. Eight public setup controls show actionable refusal before incompatible or narrowly unverified local preparation, qualified-service preparation avoidance, preserved supported alternatives and unchanged published SQLite state. Repeated selection checks and the direct indexer guard protect later boundaries; guard-removal mutants expose actual unwanted preparation. QA-21KBD-001 corrected the earlier provisional claim: fresh-worker tests initially failed because cleanup removed NumPy; independent code and QA now pass all eight without preload and reproduce the original fault with an in-memory old-behavior mutant. All five delivery lanes approve. Native model execution, the exact historical selection failure and field time savings remain unproven.

2026-10-25: Prepare passed on review-policy-3c52e00c270245cdc240. Full isolated primer, fixed architecture/security/QA/reality, rotating docs-contract and separate code specialist; unanimous/no findings. Fresh chair anonymized merit before role reattachment; all seats weighed indexer-owned lazy preparation and retained the bounded setup fix. Original red-team closing found no overlooked blocker. Intent fit establishes prospectively; delivery must prove avoided preparation and changed-selection reassessment. Operator implementation instruction acknowledges the proposed product behavior, without granting closure or commit.

2026-10-25: Operator authorized prepare, review and implementation. Full primer selected for provider-selection and persistent-index boundary work; required independent specialist lanes plus fixed architecture/security/QA/reality seats and rotating docs-contract alternative. Requested capable high-reasoning workers for the coupled design/implementation and independent boundary reviews; actual runtime identity unavailable. One implementation writer; no source edits before current readiness authority. Use owned `.wavefoundry/work/21kbd/` for disposable controls.

2026-10-25: Operator requested a new wave for setup selection diagnostics and early compatibility refusal. Planning is grounded in the observed restricted failure and successful host-access retry; no readiness or implementation approval is claimed.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 205 | 1,064,011 |
| implement | 48 | 873,169 |
| review | 181 | 324,125 |
| **Total** | **434** | **2,261,305** |

<!-- wave:context-efficiency-state {"generation":243,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":48,"content_source_credit":944891,"derived_artifact_credit":0,"direct_net":873169,"estimated_tokens_saved":873169,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1870,"response_debit":73412,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3560},"plan":{"calls":205,"content_source_credit":1641761,"derived_artifact_credit":2983,"direct_net":1064011,"estimated_tokens_saved":1064011,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12375,"response_debit":573411,"source_credit_count":87,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5053},"review":{"calls":181,"content_source_credit":820894,"derived_artifact_credit":1489,"direct_net":324125,"estimated_tokens_saved":324125,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17518,"response_debit":484429,"source_credit_count":72,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":434,"content_source_credit":3407546,"derived_artifact_credit":4472,"direct_net":2261305,"estimated_tokens_saved":2261305,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":31763,"response_debit":1131252,"source_credit_count":175,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12302},"wave_id":"21kbd setup-provider-preflight"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 15 | 0 | 9 | 4,454,223 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":4454223,"surfaced_events":15} -->
<!-- wave:exploration-avoided end -->
