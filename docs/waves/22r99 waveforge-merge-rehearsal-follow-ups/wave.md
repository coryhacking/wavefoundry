# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-07
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22r99 waveforge-merge-rehearsal-follow-ups`
Title: Waveforge Merge Rehearsal Follow Ups

## Objective

Downstream distributions can merge Wavefoundry's tree, including the lifecycle and upgrade import path from a zipped framework and a renamed vocabulary, without carrying local divergences for the five points Waveforge found in its merge rehearsal of `2b6b985a`, and Windows operators get recovery commands that paste correctly whatever their path contains. Wavefoundry's own behavior and tool signatures are unchanged.

## Changes

Change ID: `22r98-bug waveforge-merge-rehearsal-follow-ups`
Change Status: `implemented`

## Participants

- Coordinator: root agent
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-07

## Wave Summary

Wave `22r99` (Waveforge Merge Rehearsal Follow Ups) delivered one change: Waveforge merge rehearsal follow-ups. Notable adjustments during implementation: Waveforge merge rehearsal follow-ups: R5: `tests/container_fixture_profile.py` (fork-editable, `{}` default); `create_container` / `close_container` in `tests/server_tools_support.py` resolve the profile at call time and raise on collision; 4 + 13 calls in `test_wave_work_lifecycle.py` and 1 in `ReceiptSnapshotPublicIntegrationTests` converted; `RetainedUpgradePreviewTests` unchanged. `docs/architecture/testing-architecture.md` names the module; CHANGELOG 22r97 bullet revised and four 22r99 bullets added.

Intent outcome: establishes. All five Waveforge merge-rehearsal items are delivered: the zipped lifecycle and upgrade import path, five-quote PowerShell quoting in both quoters, container-neutral work-area wording with a legacy `.gitignore` line, a rules-table baseline pin, and the container fixture profile with all 18 calls converted. Tool signatures are unchanged. Evidence: default suite 12,590 tests / 231 files / 12 skips green after the final repair; code, QA and docs-contract delivery approvals; council-delivery `ev-approval-council-delivery`. Limits: macOS only, alternate profiles not rerun in this wave, PowerShell checked as formatted strings only, `RetainedUpgradePreviewTests` left direct, and other import-time source readers (`index_compatibility`, the server modules, the eval scripts) still cannot load from a zip. Retained in `evidence/`: the red-team primer, council readiness and delivery syntheses, QA's delivery mutant table and `qualification-summary.json`; routine logs stayed in the disposable work area.

**Changes delivered:**

- **Waveforge merge rehearsal follow-ups** (`22r98-bug waveforge-merge-rehearsal-follow-ups`) — 6 ACs completed. Key decisions: Readiness repair cycle 1 for lane findings DC-1, DC-2, QA-1, QA-2 and CR-1: exact wording forms and an anchored census for AC-3; the tracked `.gitignore` re-render and authored prompt copies in Scope; the AC-5 guard predicate, scope and known-bad counts; `RetainedUpgradePreviewTests` left direct; `testing-architecture.md` and the changelog bullets named.; Readiness repairs F1-F11 from the red-team primer, before any approval: the second PowerShell quoter through a shared helper; a test-only fixture profile module with a callable hook and collision check; all 18 fixture calls converted with an AST guard; the 22r97 changelog contradiction; the zip intent narrowed to the lifecycle and upgrade import path with the other import-time readers named; the docstring and comment included in the sweep; a legacy set separate from the block; every rule field pinned; the sweep's files listed; a sources-only zip.
## Watchpoints

- Watchpoint: the uncommitted 2026-11-07 wording sweep is part of this change's scope; seeds need `seed_edit_allowed`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 22r99-code-cr1-ac5-guard-scope | do_now | no | completed | code-reviewer |
| 22r99-docs-dc1-final-wording-unpinned | do_now | no | completed | docs-contract-reviewer |
| 22r99-docs-dc2-self-hosted-gitignore | do_now | no | completed | docs-contract-reviewer |
| 22r99-qa-1-ac3-heading-check-vacuous | do_now | no | completed | qa-reviewer |
| 22r99-qa-2-ac5-ast-check-underspecified | do_now | no | completed | qa-reviewer |
| 22r99-qa-del-posix-asserts-unguarded-on-windows | do_now | no | completed | qa-reviewer |
| 22r99-qa-del-zip-signature-content-unpinned | do_now | no | completed | qa-reviewer |

*Machine review state — 7 findings; current: do_now 7, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-07: Intent outcome: establishes. All five Waveforge merge-rehearsal items are delivered: the zipped lifecycle and upgrade import path, five-quote PowerShell quoting in both quoters, container-neutral work-area wording with a legacy `.gitignore` line, a rules-table baseline pin, and the container fixture profile with all 18 calls converted. Tool signatures are unchanged. Evidence: default suite 12,590 tests / 231 files / 12 skips green after the final repair; code, QA and docs-contract delivery approvals; council-delivery `ev-approval-council-delivery`. Limits: macOS only, alternate profiles not rerun in this wave, PowerShell checked as formatted strings only, `RetainedUpgradePreviewTests` left direct, and other import-time source readers (`index_compatibility`, the server modules, the eval scripts) still cannot load from a zip. Retained in `evidence/`: the red-team primer, council readiness and delivery syntheses, QA's delivery mutant table and `qualification-summary.json`; routine logs stayed in the disposable work area.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 51 | 140,283 |
| implement | 40 | 0 |
| review | 36 | 273,441 |
| **Total** | **127** | **413,724** |

<!-- wave:context-efficiency-state {"generation":121,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":40,"content_source_credit":747,"derived_artifact_credit":459,"direct_net":-5912,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1507,"response_debit":7447,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1836},"plan":{"calls":51,"content_source_credit":279718,"derived_artifact_credit":2405,"direct_net":140283,"estimated_tokens_saved":140283,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":27783,"response_debit":119565,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5508},"review":{"calls":36,"content_source_credit":366406,"derived_artifact_credit":1207,"direct_net":273441,"estimated_tokens_saved":273441,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11628,"response_debit":86320,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":127,"content_source_credit":646871,"derived_artifact_credit":4071,"direct_net":407812,"estimated_tokens_saved":413724,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":40918,"response_debit":213332,"source_credit_count":65,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11120},"wave_id":"22r99 waveforge-merge-rehearsal-follow-ups"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
