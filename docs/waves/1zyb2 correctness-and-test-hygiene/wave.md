# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zyb2 correctness-and-test-hygiene`
Title: Correctness And Test Hygiene

## Objective

Make fence detection linear without changing its output, share one documented history-folder exclusion, ship the offline vendored-script integrity check and report it from `wf_audit`, and fix two test-isolation gaps.

## Changes

Change ID: `1zxnt-maint correctness-and-test-hygiene-round`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-10-07

## Wave Summary

Wave `1zyb2` (Correctness And Test Hygiene) delivered one change: Correctness and Test Hygiene Round: Linear Fence Scan, One History-Path Constant, Archive-Aware Journal Tests, Vendored-Script Audit Finding. Notable adjustments during implementation: Correctness and Test Hygiene Round: Linear Fence Scan, One History-Path Constant, Archive-Aware Journal Tests, Vendored-Script Audit Finding: R5 (AC-7): archive-aware `_make_wave` and the divergent-archive test pass; patching `record_paths.discover_archive_dirs` to read the live `RECORD_FILENAME` fails it. R7 (AC-8): `apply_base_declaration(self)` added; `test_server_tools_retrieval.py` green.; Correctness and Test Hygiene Round: Linear Fence Scan, One History-Path Constant, Archive-Aware Journal Tests, Vendored-Script Audit Finding: Full scratch suite run 1 found `history_paths` missing from the server reload eviction set (`test_lifecycle_gates_structure.py`, 7 failures); added it beside `change_doc_checklist` in `server_impl`, file green (15 tests). The `run_tests.py`-last receipt in the repository is the coordinator's step.; Correctness and Test Hygiene Round: Linear Fence Scan, One History-Path Constant, Archive-Aware Journal Tests, Vendored-Script Audit Finding: Delivery repair DEL-3: removed the `_SharedCapModule` module-class swap from `verify_vendored_scripts` (and the unused `types` import); the cap lives only in `vendored_integrity`, which the network `verify` reads at call time through `read_vendored_file`. Test cap patches retargeted to `vendored_integrity`; the class-swap pin in `test_vendored_integrity` removed; a new test proves `verify` honors the patched `vendored_integrity` cap.

**Changes delivered:**

- **Correctness and Test Hygiene Round: Linear Fence Scan, One History-Path Constant, Archive-Aware Journal Tests, Vendored-Script Audit Finding** (`1zxnt-maint correctness-and-test-hygiene-round`) — 14 ACs completed. Key decisions: The shared constant lives in a new stdlib-only `history_paths.py`, not `record_paths.py`.; One constant `("journals", "snapshots")` applied to all nine sites; per-site extras (`memory`, `personas`, `reports`) stay local.
## Watchpoints

- Watchpoint: sequencing and shared files below; follow-up items go to later waves, not this one.
- Third of five sequential waves; depends on 1zxo0's containment in `offline_problems`, which this wave moves verbatim.
- Shares `upgrade_extensions.py`, `server_impl.py` and tests with other waves.
- Follow-up (delivery re-verification, low): pin the two vendored registry messages against echo; the source-repo network verifier still prints raw README fields; the row-path check does not refuse Unicode format characters; a dry-run upgrade preview from a pre-1.5.0 target reports the role-backfill preview as an error because the old tree has no `history_paths`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | — |
| DEL-2 | do_now | no | pending | — |
| DEL-3 | do_now | no | pending | — |
| DEL-4 | do_now | no | pending | — |
| DEL-5 | do_now | no | pending | — |

*Machine review state — 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 21 | 14,120 |
| implement | 8 | 32,602 |
| review | 17 | 144,462 |
| **Total** | **46** | **191,184** |

<!-- wave:context-efficiency-state {"generation":46,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":8,"content_source_credit":47732,"derived_artifact_credit":1516,"direct_net":32602,"estimated_tokens_saved":32602,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1814,"response_debit":14832,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":21,"content_source_credit":41191,"derived_artifact_credit":1800,"direct_net":14120,"estimated_tokens_saved":14120,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2211,"response_debit":33169,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6509},"review":{"calls":17,"content_source_credit":189700,"derived_artifact_credit":1523,"direct_net":144462,"estimated_tokens_saved":144462,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5701,"response_debit":43444,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":46,"content_source_credit":278623,"derived_artifact_credit":4839,"direct_net":191184,"estimated_tokens_saved":191184,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9726,"response_debit":91445,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8893},"wave_id":"1zyb2 correctness-and-test-hygiene"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
