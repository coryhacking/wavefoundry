# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-10-16
review-evidence-source: events.jsonl

review-policy-reprepare-required: false

wave-id: `20st7 release-profile-fixture-isolation`
Title: Release Profile Fixture Isolation

## Objective

Repair release-profile fixture assumptions without changing shipped guards or skipping coverage. Make private temporary-pack aliases and distribution-aware hook tests meaningful under shipped, renamed and declared profiles before official 1.32.0 qualification.

## Changes

Change ID: `20rvq-bug release-profile-fixture-isolation`
Change Status: `planned`

## Participants

- Coordinator: Coordinator
- Write-owning roles: Coordinator implementer after current readiness
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer, release-reviewer
- Required review lanes: none

## Wave Summary

One bounded test-only repair change, 20rvq, covering four existing test files. Current state is planned only: no code edits, readiness approval, implementation or delivery verdict is asserted.

## Watchpoints

- Watchpoint: preserve production guards, default byte parity, declaration-dependent permission checks and explicit positive/negative controls. No extra profile skips.
- Watchpoint: full qualification follows settled edits and runs sequentially. The two incomplete indexer workers and TechDocs child-result failures are not accepted exceptions; timing investigation remains deferred.
- Follow-up: the complete repair scope supersedes the earlier single-file waiver question. Normal readiness or an explicit named waiver is required before repository test edits.
- Watchpoint: operator closure is not authorized; 20tpp remains paused.

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
| council-readiness | pending | no current executed approval | record approval evidence for council-readiness |
| council-delivery | pending | no current executed approval | record approval evidence for council-delivery |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 33 | 156,286 |
| **Total** | **33** | **156,286** |

<!-- wave:context-efficiency-state {"generation":2,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":33,"content_source_credit":209397,"derived_artifact_credit":1146,"direct_net":156286,"estimated_tokens_saved":156286,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":791,"response_debit":54724,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1258}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":33,"content_source_credit":209397,"derived_artifact_credit":1146,"direct_net":156286,"estimated_tokens_saved":156286,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":791,"response_debit":54724,"source_credit_count":11,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1258},"wave_id":"20st7 release-profile-fixture-isolation"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->

## Review Checkpoints

- 2026-10-16: Consolidated release-blocker plan only. Independent readiness and delivery reviews have not run. No blocking gate or test failure was waived.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-16 | Default passed 11,867 tests/200 files/12 skips in 779.246s. Second completed 197 passing files and three failed/incomplete files; declared completed 195 passing and five failed/incomplete files. Both indexer workers exceeded 600 seconds; deterministic report comparison refuses incomplete qualification. No 1.32.0 archive, tag or GitHub release was created. | Existing ignored release-1.32.0 qualification reports; /private/tmp/release-1.32.0-{default,second,declared}-final.log |
