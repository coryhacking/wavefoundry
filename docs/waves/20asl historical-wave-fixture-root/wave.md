# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20asl historical-wave-fixture-root`
Title: Historical Wave Fixture Root

## Objective

Restore execution of the existing historical-wave signoff fixture from any working directory, so local package qualification does not report a false missing-corpus skip.

## Changes

Change ID: `208v6-bug historical-wave-fixture-root`
Change Status: `implemented`

## Participants

- Coordinator: root
- Write-owning roles: implementer/root
- Requested review lanes: code-reviewer, qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-10

## Wave Summary

Wave `20asl` (Historical Wave Fixture Root) delivered one change: Anchor the historical-wave fixture to its own checkout. Notable adjustments during implementation: Anchor the historical-wave fixture to its own checkout: One-line repair implemented. Current decorated method passes from worker cwd; independent code lane observes all three actual reads and six unchanged comparisons from both cwd values. Separate council/operator withdrawals fail original assertions; absence and renamed marker skip explicitly; restoring old root exposes the false available-corpus skip. Existing class 2 tests/0 skips. No redundant new test or permanent evidence folder.; Anchor the historical-wave fixture to its own checkout: Fresh isolated second-profile qualification passes: 12,126 tests across all 181 files, 28 skips, 1253.143s, exit 0. Exact comparator passes with 12 baseline skips and 16 explicitly marked default-only extras; no reason exception. Together with both independent withdrawal/absence controls, this completes AC-2. Declared-profile qualification remains a package gate, not an unexecuted claim of these scoped controls.

**Changes delivered:**

- **Anchor the historical-wave fixture to its own checkout** (`208v6-bug historical-wave-fixture-root`) — 3 ACs completed. Key decisions: Anchor this fixture to its own test file
## Watchpoints

- Watchpoint: no local comparison exception is approved. Implementation follows current readiness and activation; qualified source snapshot is refreshed only after reviewers stop.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 14 | 1,097 |
| implement | 10 | 216,289 |
| review | 536 | 1,869,751 |
| **Total** | **560** | **2,087,137** |

<!-- wave:context-efficiency-state {"generation":592,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":10,"content_source_credit":220359,"derived_artifact_credit":0,"direct_net":216289,"estimated_tokens_saved":216289,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":351,"response_debit":5463,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1744},"plan":{"calls":14,"content_source_credit":17939,"derived_artifact_credit":792,"direct_net":1097,"estimated_tokens_saved":1097,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4854,"response_debit":16585,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":536,"content_source_credit":3250301,"derived_artifact_credit":496,"direct_net":1869751,"estimated_tokens_saved":1869751,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20089,"response_debit":1363813,"source_credit_count":136,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":560,"content_source_credit":3488599,"derived_artifact_credit":1288,"direct_net":2087137,"estimated_tokens_saved":2087137,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25294,"response_debit":1385861,"source_credit_count":152,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8405},"wave_id":"20asl historical-wave-fixture-root"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 54 | 0 | 38 | 16,991,543 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":38,"estimated_exploration_avoided":16991543,"surfaced_events":54} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

### Delivery result — 2026-10-10

PASS, no findings from separate fresh code and QA contexts. Each executes the actual decorated method, observes three real record reads and six unchanged assertions from worker and unrelated cwd, rejects independent council/operator withdrawals and the old-root false skip, and retains intentional missing-corpus/profile skips. Both run the existing two-test class with zero skips. Requested reviewer model `gpt-6.1-sol` medium; observed runtime identity unknown. Neither lane claims a full suite or real copied-profile run; coordinator qualification supplies fresh default 12,134 tests/181 files/12 skips and second 12,126/181/28, with exact second comparison PASS (16 explicit default-only extras). All ACs/tasks complete; typed delivery approvals recorded, only operator-signoff pending. Declared profile and package build continue separately against the same frozen framework hash `c8d6a4134e202a505142cdd7ac3958048682eec85fad6207da27ac3671ffc88e`.

No new memory candidate: the durable lesson is already covered by canonical fixture-isolation and evidence-integrity guidance. No permanent evidence folder was added; the named lifecycle method and this record retain the result, with raw controls and logs in temporary storage.

### Readiness allocation — 2026-10-10

Chair declares lightweight primer for one bounded test-only cwd lookup. Separate fresh primer then fixed architecture/code, security, QA/reality seats and rotating release seat address the strongest challenge before a fresh chair synthesis. Reviewer model requested gpt-6.1-sol/medium, observed settings unknown; five-minute budget per context. Review scope is the admitted208v6 plan and current named method, not the unrelated new waves. No new evidence folder; temporary outputs and probes remain outside the repository.

### Readiness result — 2026-10-10

PASS, no findings. Lightweight adversarial primer challenged vacuous green results; architecture/code, security/release (rotating), and QA/reality formed three disclosed combined contexts, with a fourth fresh chair. Candidate controls execute all three records and six assertions from both cwd values, reject independent lane withdrawals and preserve honest absence/profile skips. Chair independently reproduces the original false skip and verifies the proposed root. Worker-root protocol was rejected as broader than needed. Typed current code, QA and council readiness approvals recorded; Prepare ready passed. Feasibility evidence does not claim implementation or package qualification. Permanent evidence is this record and the named lifecycle test; raw captures remain temporary.

### Local pack qualification complete — 2026-10-10

Fresh isolated default passes 12,134 tests/181 files/12 skips (1244.080s); second 12,126/181/28 (1253.143s); declared 12,134/181/12 (1254.164s). Both exact comparators pass: second adds 16 explicitly marked default-only skips, declared matches baseline IDs/reasons. Framework hash `c8d6a4134e202a505142cdd7ac3958048682eec85fad6207da27ac3671ffc88e` stayed unchanged through the build and genuine receipt/stamp copyback. Local `1.29.0+pvqp` pack, SHA-256 `775f1f1536040424b8f413af6ca476043d876a2bcb702cf9258b00febeed14f4`, has verified source/changelog bytes, generated protocol/inventory and outer/inner CRC. Current details are in [local pack report](../../reports/local-pack-1.29.0-test-build.md); raw reports remain ignored and logs temporary. Earlier qualification identities remain historical rather than current proof. All admitted work and independent delivery reviews remain complete; wave paused for operator closure. Native Windows is unqualified; no close, commit, push or publication.
