# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-28
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z8ox test-and-subprocess-hygiene`
Title: Test And Subprocess Hygiene

## Objective

A test run leaves the repository unchanged, and every timed external command ends its whole process tree on timeout.

## Changes

Change ID: `1z8ov-bug tests-write-only-under-temp-roots`
Change Status: `complete`

Change ID: `1z8ow-bug remaining-timed-calls-end-process-tree`
Change Status: `complete`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-09-29

## Wave Summary

Wave `1z8ox` (Test And Subprocess Hygiene) delivered two changes: Tests Write Only Under Temporary Roots and Remaining Timed Calls End the Process Tree. Notable adjustments during implementation: Tests Write Only Under Temporary Roots: Delivery repair DEL-F1 and DEL-F3. The guard failed runs whenever the framework's own context-efficiency projection rewrote the open `wave.md` mid-run. `repo_state_snapshot` now keeps each wave record's bytes (waves root from `record_paths.unvalidated_record_roots`, record name from `vocabulary_profile.RECORD_FILENAME`, both stdlib-only and imported lazily, with no literal fallback after delivery repair DEL-F4); `_repo_state_changes` tolerates a changed wave record only when `_strip_projected_regions` (legacy markers canonicalized, the `wave:context-efficiency` and `wave:exploration-avoided` regions with their headings and state comments removed, seam whitespace collapsed) gives identical text. Marker constants are pinned against `context_efficiency` and `exploration_avoided`. `.wavefoundry/guard-overrides.json` is compared by SHA-256 content hash. An end-of-run snapshot that cannot be taken now fails the run with the cause (it was silently skipped). New tests in `test_run_tests_repo_guard.py`: `WaveRecordProjectionTests` (projection-only rewrite passes and writes the receipt; projection appending its blocks passes; body edit, edit inside the `wave:review-status` region, and projection plus body edit each fail naming the record; `test_dropping_the_tolerance_fails_the_projection_only_run`; marker and matcher pins), `GuardOverridesHashTests` (2), `GitListingTimeoutTests` (5); fixtures rendered with the real `replace_checkpoint_block` producers. Scratch mutant (tolerance removed from `_repo_state_changes`): the two projection-only tests fail. `test_secrets_prefix_collapse._NoRepoWrites` records the bytes the real `save_exceptions` writes into a temporary root instead of re-serializing. CHANGELOG 1z8ox bullets and the testing-architecture guard paragraph state the tolerance; the retrieval baseline row names `1yxyw-e3` as the former baseline (its `evaluator_identity.source_sha256` `bb129af8...` matches neither HEAD's nor the current `retrieval_eval.py`), and the `test_docs_lint` pin follows. Gapfill: grep and sed read `run_tests.py`, the projection code and the test files for bulk context after `code_*` lookups were loaded, because the edits needed exact surrounding text; Tests Write Only Under Temporary Roots: Post-fix census (AC-2). New clone of HEAD `c490e286` with the current working tree applied (`git diff --binary HEAD` sha256 `89be0718...`, verified identical in the clone; 30 untracked non-ignored files, list sha256 `b826206d...`), index copied without the receipt as below, no MCP server attached. Full run: 9942 tests in 140 files, skipped 16 (the live suite reports 16), and the before/after snapshot of every file, including `.git/`, `.wavefoundry/index/` and ignored files, is identical apart from the receipt and lock. `.wavefoundry/guard-overrides.json` unchanged. Two files failed, neither a write: `test_review_policy` (the same corpus assertion as census 1) and `test_tree_kill_routing`, whose census counted the new timed `git ls-files` call in `run_tests.repo_state_snapshot`; the timeout was removed (a local read that takes no lock), and a per-file re-run in the clone with the final runner of `test_tree_kill_routing` and every file that wrote in census 1 changed nothing and passed; Remaining Timed Calls End the Process Tree: Implemented. `_run_git` and `_git_strip_vars` resolve the helper at call time; 15 modules gained a `_run_tree_kill` resolver (accel_embedder, dashboard_lib, docs_gardener, graph_indexer, graph_quality_eval, indexer, operator_identity, provider_policy, render_platform_surfaces, retrieval_eval, run_secrets_scan, scan_secrets, sqlite_storage_migration, upgrade_protocol, wf_server/server_impl); `graph_indexer._GITIGNORED_PATHS_TIMEOUT_S`; reap guard on `returncode is None` in both branches. Census: EXCLUDED 33 keys (36 calls) to 9 keys (11 calls); ROUTED 16 keys (16 calls) to 48 keys (50 calls); CALLEES 7 to 9, plus `<unnamed>` for a timed call to an unnamed callee. Affected fakes derived by a scratch spy runner (a routed resolver reached while `subprocess.run` or `isolated_run` was faked) over the 75 test files that mention them: shim installed and fake-called assertions added in test_accel_embedder, test_dashboard_server, test_doc_drift, test_operator_identity, test_render_platform_surfaces, test_review_operator_integration, test_sqlite_storage_migration, test_indexer (Windows branch); two test_server_tools isolation guards retargeted to the `Popen` spawn; shim added to test_runtime_advisory and test_memory_backfill so their "must not run" guards still cover routed sites; test_subprocess_util's Windows fake gained `returncode = None`. Scratch mutants: a `poll()` guard fails AC-3b, an unconditional kill fails AC-3, a direct `subprocess_util.run_with_tree_kill` lookup fails AC-5, a plain `isolated_run` resolver fails AC-2, an inline getattr call fails the census, and a helper call or getattr lookup outside `_run_git` fails the store pin. Gapfill: grep and a scratch AST census for the timed-call sites, because `code_pattern` with `**/*.py` skips top-level modules and `server_impl.py` is over 1 MB.

**Changes delivered:**

- **Tests Write Only Under Temporary Roots** (`1z8ov-bug tests-write-only-under-temp-roots`) — 4 ACs completed. Key decisions: Census by tree snapshot in an isolated worktree, plus a static pass; The standing guard covers tracked and non-ignored files plus the gate file; ignored runtime paths are left to the isolated census
- **Remaining Timed Calls End the Process Tree** (`1z8ow-bug remaining-timed-calls-end-process-tree`) — 7 ACs completed. Key decisions: Route git and probe calls too; Route inside `_run_git` rather than at its callers
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-F1 | do_now | no | completed | — |
| DEL-F2 | do_now | no | completed | — |
| DEL-F3 | do_now | no | completed | — |
| DEL-F4 | do_now | no | completed | — |
| DEL-F5 | maybe_later | no | pending | — |

*Machine review state — 5 findings; current: do_now 4, maybe_later 1, dont_do_later 0, not_issue 0*
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
| plan | 87 | 3,854,438 |
| implement | 96 | 2,089,940 |
| review | 35 | 700,952 |
| **Total** | **218** | **6,645,330** |

<!-- wave:context-efficiency-state {"generation":224,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":96,"content_source_credit":2216931,"derived_artifact_credit":0,"direct_net":2089940,"estimated_tokens_saved":2089940,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3466,"response_debit":126593,"source_credit_count":60,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3068},"plan":{"calls":87,"content_source_credit":4004188,"derived_artifact_credit":3128,"direct_net":3854438,"estimated_tokens_saved":3854438,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5431,"response_debit":156660,"source_credit_count":147,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9213},"review":{"calls":35,"content_source_credit":785011,"derived_artifact_credit":3250,"direct_net":700952,"estimated_tokens_saved":700952,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12610,"response_debit":77015,"source_credit_count":64,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":218,"content_source_credit":7006130,"derived_artifact_credit":6378,"direct_net":6645330,"estimated_tokens_saved":6645330,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":21507,"response_debit":360268,"source_credit_count":271,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14597},"wave_id":"1z8ox test-and-subprocess-hygiene"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 8 | 5,134,117 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":8,"estimated_exploration_avoided":5134117,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
