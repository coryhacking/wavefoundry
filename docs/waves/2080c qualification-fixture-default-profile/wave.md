# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2080c qualification-fixture-default-profile`
Title: Qualification Fixture Default Profile

## Objective

Restore known-default nested qualification fixtures under distribution profile runs without weakening assertions.

## Changes

Change ID: `2080b-bug qualification-fixture-default-profile`
Change Status: `implemented`

## Participants

- Coordinator: root
- Write-owning roles: implementer/root
- Requested review lanes: code-reviewer, qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-10

## Wave Summary

Wave `2080c` (Qualification Fixture Default Profile) delivered one change: Isolate qualification fixtures from the outer profile.

**Changes delivered:**

- **Isolate qualification fixtures from the outer profile** (`2080b-bug qualification-fixture-default-profile`) — 3 ACs completed. Key decisions: Use existing shipped-default helper on scratch modules
## Watchpoints

- Watchpoint: no performance-budget change or skip waiver. Implement before 2071o activation; full package qualification follows both waves.

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
| plan | 147 | 625,674 |
| implement | 37 | 593,770 |
| review | 11 | 234,608 |
| **Total** | **195** | **1,454,052** |

<!-- wave:context-efficiency-state {"generation":71,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":37,"content_source_credit":725839,"derived_artifact_credit":0,"direct_net":593770,"estimated_tokens_saved":593770,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1063,"response_debit":132458,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1452},"plan":{"calls":147,"content_source_credit":1062725,"derived_artifact_credit":1579,"direct_net":625674,"estimated_tokens_saved":625674,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7484,"response_debit":434951,"source_credit_count":51,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":11,"content_source_credit":246067,"derived_artifact_credit":1147,"direct_net":234608,"estimated_tokens_saved":234608,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":184,"response_debit":15278,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":195,"content_source_credit":2034631,"derived_artifact_credit":2726,"direct_net":1454052,"estimated_tokens_saved":1454052,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8731,"response_debit":582687,"source_credit_count":65,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8113},"wave_id":"2080c qualification-fixture-default-profile"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 2 | 2,164,808 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":2164808,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

Chair declares lightweight primer for a test-only scratch initialization, with bounded real nested runner controls. Independent code/QA review and council synthesis use fresh contexts, available inherited model (observed settings unknown), 10-minute budget. Evidence stays in this summary and typed ledger; transient probes stay in /private/tmp.

### Readiness and implementation — 2026-10-10

Root isolated red-team primer and fresh architecture rotating seat approve the bounded fixture plan; independent code/QA judgments confirm exact failures and helper refusal. Actual second worker19tests2fail; scratch runtime defaults and canonical source hashes verified. Strongest alternative inherited-profile counts would remove the known-default oracle, so retain exact assertions. Current typed approvals and Prepare-ready succeeded before activation. Root is single writer for the one test file; declarations intentionally remain outside the vocabulary/layout reset.

### Implementation verification — 2026-10-10

Only four setup/import lines added; every assertion unchanged. Default, second and declared selected workers each pass19tests/0skips. Temporary removal of initialization recreates both original failures through actual second-profile runner; canonical hash unchanged. All3ACs and2implementation tasks complete. Independent delivery and fresh full qualification pending. Pause here to free the OPEN slot for2071o; package awaits both. No closure, commit or push of this new wave authorized by its current implementation task.

### Independent delivery allocation — 2026-10-10

Fresh separate code/QA reviewers assess the one-file repair; requested gpt-6.1-sol/medium for the small bounded fixture diff, observed runtime unknown. Reviewed Git object `ac4440ce42308595b472d1ee3f916ae9b7a631f0`, 5-minute budget, targeted tests per mutant and whole-file only for survivors. Fresh full canonical qualification follows2071o source freeze before final delivery claims; fixture path remains frozen while unrelated graph implementation proceeds. No new evidence folder.

### Independent scoped delivery results — 2026-10-10

Fresh separate code and QA contexts found no scope defect; approvals remain provisional until fresh full qualification. Code independently passes19-test second worker/0skips15.569s and confirms all76 assertion AST nodes match HEAD. QA independently passes default19/0skips14.978s, second19/0skips15.733s, declared19/0skips15.039s; all3required AC rows have direct evidence. Each independently deletes initialization in a disposable edited second-profile copy and targets the two original CLI tests:2tests2exact failures `(3,3)!=(4,1)` and `0!=2`, no skips. Canonical fixture Git object remains `ac4440ce42308595b472d1ee3f916ae9b7a631f0`; profile modules unchanged. Helper canonical-target refusal independently verified. Five integrity flags true; code/QA contexts `2080c-delivery-code-independent-20261010-root-2080c_delivery_code` and `2080c-delivery-qa-independent-20261010`. No source edit or permanent per-seat artifact; final full gate is coordinator-owned.

### Final delivery qualification — 2026-10-10

Coordinator-owned isolated default passes all12,134tests/181files/13skips783.834s, including the19-test qualification worker. Framework hash `18b0ce1a6f18c334f04ee059d8a587ce7a30ab39d158da9178d4124b9dc763ea` matches the working checkout and unchanged fixture. Genuine runner receipt copied byte-for-byte after matching hashes; it attests framework inputs, not unrelated live project-doc edits. Both fresh independent code/QA approvals are recorded; typed continuation requires only operator-signoff. All3ACs/3tasks met, change implemented and wave remains paused for closure. Profile runs remain packaging checks. No new memory candidate: this bounded fixture correction is preserved by canonical tests and existing lifecycle guidance.

### Local pack qualification complete — 2026-10-10

Fresh isolated default passes 12,134 tests/181 files/12 skips (1244.080s); second 12,126/181/28 (1253.143s); declared 12,134/181/12 (1254.164s). Both exact comparators pass: second adds 16 explicitly marked default-only skips, declared matches baseline IDs/reasons. Framework hash `c8d6a4134e202a505142cdd7ac3958048682eec85fad6207da27ac3671ffc88e` stayed unchanged through the build and genuine receipt/stamp copyback. Local `1.29.0+pvqp` pack, SHA-256 `775f1f1536040424b8f413af6ca476043d876a2bcb702cf9258b00febeed14f4`, has verified source/changelog bytes, generated protocol/inventory and outer/inner CRC. Current details are in [local pack report](../../reports/local-pack-1.29.0-test-build.md); raw reports remain ignored and logs temporary. Earlier qualification identities remain historical rather than current proof. All admitted work and independent delivery reviews remain complete; wave paused for operator closure. Native Windows is unqualified; no close, commit, push or publication.
