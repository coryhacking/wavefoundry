# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-24
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yyoj extension-prefix-and-inert-config`
Title: Extension Prefix And Inert Config

## Objective

Let distribution extension tools use core prefixes such as wf_ while keeping name-collision refusal, and warn operators who edit inert record-layout config keys. Both come from Waveforge RFC section 10.

## Changes

Change ID: `1yxl8-enh extension-tools-allow-core-prefixes`
Change Status: `implemented`

Change ID: `1yygb-maint warn-inert-record-layout-config`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-09-24

## Wave Summary

Wave `1yyoj` (Extension Prefix And Inert Config) delivered two changes: Extension Tools May Use Core Prefixes and Warn on Inert Record-Layout Config Keys. Notable adjustments during implementation: Extension Tools May Use Core Prefixes: Readiness primer (no blockers): added Requirement 5 / AC-4 refusing new tools named in core name-keyed sets, a new positive fixture instead of converting overlap fixtures, server_impl in serialization points, spec notes on wf_help grouping; Extension Tools May Use Core Prefixes: Implemented: overlap and core-prefixed-tier refusals removed from declaration_problems; `_reserved_tool_name_collections` refuses new tools named in the seven reserved collections; new fixtures core_prefix_new_tool (served, tiered, wrapped, allowlisted), reserved_retired_name, reserved_collection_name; census test with 7 reserved and 18 non-behavior collections (the census found WORKFLOW_REQUIRED_KEYS in wave_lint_lib, classified non-behavior); spec, changelog; 23 extension tests OK; mutants in evidence/mutants.py killed. Gapfill: code reads by shell over anchors verified in readiness; Extension Tools May Use Core Prefixes: Delivery repair DEL-CENSUS-COVERAGE (red-team and docs-contract): census widened to assignments derived from a classified collection (8 derived collections classified), membership invariant keeps reserved collections to served core or retired names, spec, testing-architecture and docstring narrowed to the actual predicate, ADR 1yb8v warning-scope clause, `InertRecordLayoutConfigTests` made standalone; mutants: derived collection and reserved-gains-unserved-name killed, unserved-only collection a documented survivor.

**Changes delivered:**

- **Extension Tools May Use Core Prefixes** (`1yxl8-enh extension-tools-allow-core-prefixes`) — 4 ACs completed. Key decisions: Allow extension prefixes that overlap core prefixes; keep same-name refusal; recommend distribution-specific prefixes
- **Warn on Inert Record-Layout Config Keys** (`1yygb-maint warn-inert-record-layout-config`) — 3 ACs completed. Key decisions: Advisory warning, no automatic removal from targets
## Watchpoints

- Watchpoint: undeclared reuse of an existing tool name must stay refused after the prefix guard is removed.
- Watchpoint: the new lint check is advisory only and never rewrites a target's config.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-CENSUS-COVERAGE | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 19 | 5,166 |
| implement | 35 | 0 |
| review | 13 | 62,512 |
| **Total** | **67** | **67,678** |

<!-- wave:context-efficiency-state {"generation":64,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":35,"content_source_credit":495,"derived_artifact_credit":136,"direct_net":-5815,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1492,"response_debit":7446,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2492},"plan":{"calls":19,"content_source_credit":21042,"derived_artifact_credit":3586,"direct_net":5166,"estimated_tokens_saved":5166,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1969,"response_debit":21302,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":13,"content_source_credit":91694,"derived_artifact_credit":1515,"direct_net":62512,"estimated_tokens_saved":62512,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4118,"response_debit":28895,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":67,"content_source_credit":113231,"derived_artifact_credit":5237,"direct_net":61863,"estimated_tokens_saved":67678,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7579,"response_debit":57643,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8617},"wave_id":"1yyoj extension-prefix-and-inert-config"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
