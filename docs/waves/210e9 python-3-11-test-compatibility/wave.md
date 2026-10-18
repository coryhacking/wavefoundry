# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-18
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `210e9 python-3-11-test-compatibility`
Title: Python 3 11 Test Compatibility

## Objective

The framework test suite runs green on Python 3.11, the supported minimum, as Waveforge reported it does not. Four test files used Python 3.12 or 3.13 behaviour; this wave fixes them with test-only edits.

## Changes

Change ID: `20zvz-bug python-3-11-compatibility`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-18

## Wave Summary

Wave `210e9` (Python 3 11 Test Compatibility) delivered one change: Framework tests run on Python 3.11. Notable adjustments during implementation: Framework tests run on Python 3.11: Implemented under `framework_edit_allowed`. The four files pass under 3.11.17 and 3.14.8. AC-1: the whole suite under 3.11 with the shipped pins ran 11901 tests; the only failure is the environmental `test_mcp_tool_registry::test_reload_rebuilds_the_registry_from_fresh_code`, and `test_storage_upgrade_resume` passes with `lancedb==0.33.0`. Against the 1.32.0 release default report (12 skips) the 3.11 run has one extra skip: `test_server_tools_retrieval.MaybeRefreshIfStaleTests.test_completed_registered_child_is_reaped_before_refresh_decision`, reason "requires waitid with WNOWAIT to preserve child wait status". `os.waitid` reached macOS only in Python 3.13, and no product code calls it, so this is a capability skip. AC-2: in a git-initialised scratch copy with a `git add`ed `probe_bad.py` holding `"\d"`, under 3.11 the HEAD sweep passed and the new sweep failed with `probe_bad.py:1: invalid escape sequence '\d'`. AC-3: whole suite `--no-cache` under 3.14 ran 11901 tests, OK, with a fresh green receipt. Delivery: code and QA lanes approved after scratch mutants: inline filter reverted (sweep vacuous on 3.11), `-W` flag dropped, advisory patch dropped, argv patch back inside the `with` (3.11 SyntaxError), `filename=` dropped in chunker and graph indexer, and an extra precondition stderr line; each was caught. Gapfill: shell and scratch copies, because the checks needed a second interpreter and uncommitted files.

**Changes delivered:**

- **Framework tests run on Python 3.11** (`20zvz-bug python-3-11-compatibility`) — 3 ACs completed. Key decisions: Fix the tests and add no new mechanism.; Readiness review folded in: the sweep's inline filter named, `-W` only on 3.11, the skip comparison in AC-1, the AC-2 old-versus-new probe, the inferred registry classification, and the two 20-block functions in Risks.
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

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
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 12 | 0 |
| implement | 14 | 0 |
| review | 10 | 16,132 |
| **Total** | **36** | **16,132** |

<!-- wave:context-efficiency-state {"generation":35,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":14,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2374,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":453,"response_debit":2403,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":482},"plan":{"calls":12,"content_source_credit":10457,"derived_artifact_credit":2015,"direct_net":-11,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1696,"response_debit":15055,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4268},"review":{"calls":10,"content_source_credit":28368,"derived_artifact_credit":1151,"direct_net":16132,"estimated_tokens_saved":16132,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2184,"response_debit":14257,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3054}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":36,"content_source_credit":38825,"derived_artifact_credit":3166,"direct_net":13747,"estimated_tokens_saved":16132,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4333,"response_debit":31715,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7804},"wave_id":"210e9 python-3-11-test-compatibility"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
