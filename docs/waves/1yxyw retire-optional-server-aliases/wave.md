# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-25
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yxyw retire-optional-server-aliases`
Title: Retire Optional Server Aliases

## Objective

Retire the ten optional flat server aliases that wave `1yzd0` kept for internal convenience, so `wf_server` modules have one spelling except the two (`server_impl`, `dashboard_handlers`) that installed 1.25/1.26 upgrade runners require.

## Changes

Change ID: `1yxwn-ref retire-optional-flat-server-aliases`
Change Status: `planned`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, release-reviewer, docs-contract-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

## Wave Summary

One refactor: delete ten flat alias files, switch every importer and patch target outside the package to `wf_server.*` names, keep the fixture byte-identical with an evaluator existence check on the implementing path, and amend ADR `1yx4m` and the downstream guidance.

## Watchpoints

- Watchpoint: implementation starts only after wave `1yzd0` closes (operator instruction, 2026-09-25); readiness may complete before that.
- Watchpoint: the evaluator step is its own reviewed, operator-committed step before any alias is removed.
- Watchpoint: `server_impl.py` and `dashboard_handlers.py` stay flat and byte-identical.
- Watchpoint: no pack is cut and no version is tagged from a tree containing wave `1yzd0` without this change; both ship in one release.

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
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| docs-contract-reviewer | pending | no current executed approval | record approval evidence for docs-contract-reviewer |
| release-reviewer | pending | no current executed approval | record approval evidence for release-reviewer |
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
| plan | 18 | 15,885 |
| **Total** | **18** | **15,885** |

<!-- wave:context-efficiency-state {"generation":18,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":18,"content_source_credit":35980,"derived_artifact_credit":1859,"direct_net":15885,"estimated_tokens_saved":15885,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2841,"response_debit":22922,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":18,"content_source_credit":35980,"derived_artifact_credit":1859,"direct_net":15885,"estimated_tokens_saved":15885,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2841,"response_debit":22922,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"wave_id":"1yxyw retire-optional-server-aliases"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
