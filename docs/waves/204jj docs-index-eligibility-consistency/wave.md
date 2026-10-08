# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-07
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `204jj docs-index-eligibility-consistency`
Title: Docs Index Eligibility Consistency

## Objective

Make docs-index eligibility the same on every index launch path, so `wf setup` stops embedding framework test files into the docs table and every later incremental build stops deleting them again; each setup currently re-embeds about 250 test files for nothing and test docstrings pollute docs retrieval.

## Changes

Change ID: `2038p-bug setup-leaks-framework-tests-into-docs-index`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-10-07

## Wave Summary

Wave `204jj` (Docs Index Eligibility Consistency) delivered one change: Setup Leaks Framework Tests Into the Docs Index. Notable adjustments during implementation: Setup Leaks Framework Tests Into the Docs Index: Proposed CHANGELOG bullet (under `## [1.29.0]`, Fixed): "`wf setup` no longer adds framework test files to the documentation index. Setup now resolves include prefixes the same way as every other index build, so setup and incremental refreshes agree on the corpus and a setup that follows a refresh no longer re-embeds unchanged files. A docs-only or code-only setup now gives the graph the same docs and code scope as every other build. The first index build after upgrading removes the framework test-file rows an earlier setup added; this is expected. Wave 204jj / 2038p."; Setup Leaks Framework Tests Into the Docs Index: Implemented (ws-1, ws-2 docs). New stdlib-only `workflow_include_prefixes.py` (`normalize_prefixes`, `coerce_prefix_list`, `read_project_include_prefixes`); `indexer._workflow_project_include_prefixes` and `indexer._normalize_prefixes` delegate to it; setup deleted `_workflow_project_include_prefixes`, `_coerce_prefix_list`, `_merge_project_include_prefixes`, its prefix key constants and every prefix parameter of `_run_indexer` and `build_index`, and reads the "Workflow policy" line through the new module (module-level import of the stdlib module only; no `indexer` import). Caller census as implemented: no `setup_index` launch forwards `--project-include-prefix` (content `all`, `docs`, `code`, `--graph-only`, and the background child, which re-enters setup and reaches the same bare `_run_indexer`); indexer callers, `wf_server/server_impl.py`, `wf_server/index_handlers.py` and the `tests/test_server_tools_lifecycle.py` patch still go through `indexer._workflow_project_include_prefixes`; the only remaining `--project-include-prefix` producer is `indexer.main`'s pass-through for manual and test use. Docstring, help text, fold-test docstring and `docs/architecture/data-and-control-flow.md` items 4 and 9 corrected; CHANGELOG bullet added under `## [1.29.0]` Fixed.; Setup Leaks Framework Tests Into the Docs Index: Probes in a scratch copy of the tree (rsync, fresh `git init`). Unfixed HEAD `setup_index.py` with the new tests: both `SetupLaunchedCorpusParityTests` tests FAIL, the corpus test on the first build ("setup build: framework test rows in chunks_docs", `.../tests/test_tools.py`). Mutant A (restore the union forward for content `all` in `_run_indexer`): killed by both parity tests and the four-mode test (`default`). Mutant B (restore the per-content forward: code list for `code`, docs list for `docs`, union otherwise): killed by both parity tests and all six four-mode subtests. Mutant C (revert `coerce_prefix_list` to the old indexer coercion): killed by `test_non_string_items_are_skipped` (error) and `test_malformed_values_never_raise_or_split_into_characters` (string and dict layer values). Mutant D (restore indexer's own legacy reader instead of delegating): killed by `test_indexer_reader_delegates_to_the_module`. Scratch sources restored and diffed equal to the repository afterwards..

**Changes delivered:**

- **Setup Leaks Framework Tests Into the Docs Index** (`2038p-bug setup-leaks-framework-tests-into-docs-index`) — 12 ACs completed. Key decisions: Selected (a): `setup_index` stops forwarding prefixes and launches the indexer bare on every path.; Do not add (b) in this change.
## Watchpoints

- Watchpoint: run `wf setup` on this repository only after the fix lands (operator direction); it also completes the pending memory backfill run.
- Follow-up: `--include-tests` and `--include-generated` are not persisted, so a later bare incremental undoes them (out of scope).

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
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 61 | 2,129,094 |
| implement | 62 | 187,295 |
| review | 9 | 21,167 |
| **Total** | **132** | **2,337,556** |

<!-- wave:context-efficiency-state {"generation":85,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":62,"content_source_credit":215547,"derived_artifact_credit":274,"direct_net":187295,"estimated_tokens_saved":187295,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3076,"response_debit":27632,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2182},"plan":{"calls":61,"content_source_credit":2243819,"derived_artifact_credit":2168,"direct_net":2129094,"estimated_tokens_saved":2129094,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2984,"response_debit":117714,"source_credit_count":68,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":9,"content_source_credit":35223,"derived_artifact_credit":1244,"direct_net":21167,"estimated_tokens_saved":21167,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1844,"response_debit":15840,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":132,"content_source_credit":2494589,"derived_artifact_credit":3686,"direct_net":2337556,"estimated_tokens_saved":2337556,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7904,"response_debit":161186,"source_credit_count":90,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8371},"wave_id":"204jj docs-index-eligibility-consistency"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
