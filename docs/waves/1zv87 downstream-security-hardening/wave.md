# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zv87 downstream-security-hardening`
Title: Downstream Security Hardening

## Objective

Close the four security issues the Waveforge maintainers reported privately against `fdd8de15` before 1.29.0 ships: the journal migration must never follow links out of the repository, code readers must not release framework locks, setup must not run a repository-planted `uv`, and `wf_close_change` must not probe paths from an unchecked id. The journal migration also becomes profile-aware with a public entry point.

## Changes

Change ID: `1zuq5-bug journal-migration-follows-links`
Change Status: `implemented`

Change ID: `1zuq6-enh profile-aware-journal-migration`
Change Status: `implemented`
Depends On: `1zuq5-bug journal-migration-follows-links`

Change ID: `1zuq7-bug code-readers-release-lifecycle-locks`
Change Status: `implemented`

Change ID: `1zv84-bug setup-uv-lookup-trusts-repo`
Change Status: `implemented`

Change ID: `1zv85-bug close-change-path-oracle`
Change Status: `implemented`

## Participants

- Coordinator: wave-council
- Write-owning roles: implementer
- Requested review lanes: security-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-05

## Wave Summary

Wave `1zv87` (Downstream Security Hardening) delivered 5 changes: The Journal Migration Follows Links Out Of The Repository, A Profile-Aware Journal Migration With A Public Entry Point, Code Readers Can Release The Framework's Runtime Locks, Setup's uv Lookup Can Pick A uv From The Repository, and Lifecycle Tools Build Paths From An Unchecked Change Id. Notable adjustments during implementation: Lifecycle Tools Build Paths From An Unchecked Change Id: Readiness review folded in: `wf_mark_ac` and `wf_mark_task` write through the same unchecked path (reproduced in scratch); shared shape check and admission check added.

**Changes delivered:**

- **The Journal Migration Follows Links Out Of The Repository** (`1zuq5-bug journal-migration-follows-links`) — 6 ACs completed. Key decisions: Leave unsafe journals in place and list them, rather than failing the upgrade
- **A Profile-Aware Journal Migration With A Public Entry Point** (`1zuq6-enh profile-aware-journal-migration`) — 6 ACs completed. Key decisions: Keep the private name as the post-extract caller
- **Code Readers Can Release The Framework's Runtime Locks** (`1zuq7-bug code-readers-release-lifecycle-locks`) — 5 ACs completed. Key decisions: Guard the readers, not the lock type
- **Setup's uv Lookup Can Pick A uv From The Repository** (`1zv84-bug setup-uv-lookup-trusts-repo`) — 5 ACs completed. Key decisions: Keep a trusted PATH `uv` ahead of the bootstrap
- **Lifecycle Tools Build Paths From An Unchecked Change Id** (`1zv85-bug close-change-path-oracle`) — 6 ACs completed. Key decisions: Shape check plus gate skip
## Watchpoints

- Watchpoint: framework edits need `framework_edit_allowed`, the seed 210 edit needs `seed_edit_allowed`; full suites in scratch copies, receipt run last in the repo.
- Watchpoint: `1zuq6` edits the same function as `1zuq5`; implement in order.
- Follow-up: publishing a security advisory for S1 (affects 1.15.0 to 1.28.0) is the operator's decision.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | — |
| DEL-2 | do_now | no | completed | — |
| DEL-3 | do_now | no | completed | — |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 27 | 34,047 |
| implement | 10 | 35,118 |
| review | 25 | 305,710 |
| **Total** | **62** | **374,875** |

<!-- wave:context-efficiency-state {"generation":57,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":10,"content_source_credit":47623,"derived_artifact_credit":1495,"direct_net":35118,"estimated_tokens_saved":35118,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1676,"response_debit":12324,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":27,"content_source_credit":50629,"derived_artifact_credit":8716,"direct_net":34047,"estimated_tokens_saved":34047,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2585,"response_debit":31926,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9213},"review":{"calls":25,"content_source_credit":365229,"derived_artifact_credit":2993,"direct_net":305710,"estimated_tokens_saved":305710,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7959,"response_debit":56869,"source_credit_count":44,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":62,"content_source_credit":463481,"derived_artifact_credit":13204,"direct_net":374875,"estimated_tokens_saved":374875,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12220,"response_debit":101119,"source_credit_count":72,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11529},"wave_id":"1zv87 downstream-security-hardening"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
