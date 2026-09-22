# Index Handler Module

Change ID: `1ymzm-ref index-handler-module`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-09-21
Wave: `1ymzq handler-module-split-three`

## Rationale

The index build, health and optimize family has fifty-three domain-owned definitions and twelve objects in the implementation inventory. This includes `_audit_build_summary` and `_graph_health_summary` with their moving consumers, the dormant `_epoch_token` and `_lock_is_fresh` without unrelated deletion, and the child-PID trio `_DASHBOARD_CHILD_PIDS`, `_register_dashboard_child_pid` and `_reap_dashboard_child_pids`. The set remains re-exported for dashboard invocation-time access. `_index_inputs_stale` stays with its sole production caller, the monitor policy `_maybe_refresh_if_stale`; `_wrap_upgrade_publication_guard` and `_indexer_module` also stay. Registered tools remain `index_build`, `index_build_status`, `index_health` and `index_optimize` (the last through `_index_optimize_response`). Substrate ownership (`index_state_store`, `index_source_guard`, `indexer`) and the `1yj14` build/CE source-guard interlocks are unchanged.

This change runs LAST in the wave because it introduces the final edit to evaluator membership, after the unused containment bootstrap has established R0's evaluator identity. `_epoch_state` and `_index_freshness_verdict` are on the `code_ask` path and the current direct-response AST closure identifies thirteen family members (a conservative name-unified census, not an exhaustive dynamic-call proof), so `index_handlers.py` joins `PRODUCTION_RETRIEVAL_MODULES` under the `1y0h2` Requirement 9 rule; that edit moves the evaluator's own identity, after which no receipt can be compared with one taken before. The wave record's receipt sequence therefore takes its comparable pair before this change and records this change's after-receipt as the new baseline with the deviation logged, the `1y0h2` Requirement 11 pattern.

Domain ownership decides membership. Outside callers, all kept valid by the rebinding block: `_epoch_state` from `_code_ask_response_body`, `code_search_response`, `docs_search_response`, `_stored_language_names` and three FTS serving helpers (`_fts_serving_verdict`, `_fts_serving_coverage`, `_fts_probed_fetch`); `_index_freshness_verdict` from `_code_ask_response_body`; `_chunk_index_coverage` from `_fts_serving_coverage` and `_state_store_health_summary`; `_index_layer_readiness`, `_index_readiness_overview` and `_check_index_writer_current` from `WaveIndex`; `_trigger_background_index_refresh_for_paths` from eighteen callers (ten lifecycle stayers including `wf_set_handoff_response`, six memory responses that move in `1ymzk`, and the garden and techdocs responses); `_check_index_writer_current` and `_start_background_index_refresh` from the staying monitor policy `_maybe_refresh_if_stale`, so every retrieval-suite patch of those two names around the monitor stays on `server_impl` and stays observed; `_maybe_optimize_index_on_close` from `wf_close_wave_response`; `_audit_index_snapshot` from `wf_audit_response`; `_index_chunk_matching_address` from `wf_map_response`; `_start_background_index_refresh` from `_fts_schedule_heal`; `_index_build_active` from `_parse_finished_build_stats_from_log` (a stayer) and from the movers `_refresh_index_build_stats_from_finished_logs` and `run_index_rebuild`; `_epoch_state`, `_index_rebuilding_response`, `_index_runtime_failure_response` and `_index_optimize_response` from closures; `_graph_refresh_then_recheck`, which has no caller inside `server_impl.py` and is reached as `server_impl._graph_refresh_then_recheck` from `codenav_handlers` and `graph_handlers`, so it moves and the rebinding keeps those attribute reaches valid. Staying helpers reached per call: about thirty, including `_indexer_module`, `_graph_snapshot_module`, `_load_graph_query`, `_mcp_subprocess_run`, `_preferred_python`, `_read_chunker_version`, `_state_store_health_summary`, `_store_build_meta`, `_store_has_completed_build`, `_vector_layer_available`, `_wf_log`, `_response`, `_pid_is_running`, `_reap_state_block`, `_reap_state_diagnostics`, `_parse_finished_build_stats_from_log`, `_annotate_freshness` (search-owned). Index-monitor policy stays with `ImplHandler`: `_maybe_refresh_if_stale`, `_read_monitor_config` and the two `_MONITOR_DEFAULT_*` constants are read only by the monitor and stay together.

Module-level objects that move with re-export: `BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS`, `CLOSE_OPTIMIZE_BLOAT_RATIO`, the mutable `_BACKGROUND_BUILD_PIDS` and `_FRESHNESS_CACHE` (no staying function rebinds either; tests mutate them in place through `server_impl`, so identity is preserved by re-export), `_FRESHNESS_TTL_SECONDS`, the three `_FRESHNESS_*` verdict constants, `_FTS_DAMAGE_REASONS` (also read by two FTS stayers), `_INDEX_BUILD_VERIFY_POLL_INTERVAL_SECONDS`, `_DASHBOARD_CHILD_PIDS` and `BACKGROUND_INDEX_LOCK_STALE_SECONDS` (used by retained `_lock_is_fresh`). `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` is assigned on `server_impl` by the shared `load_server()` fixture and five test sites to collapse the verify window, and `run_index_rebuild` reads it as a module global, so the moved function reads `server_impl._INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` at call time, the named exception this wave uses for patched constants; without it every build in the retrieval suite silently waits the real window. The `_REASON_*` names are not standalone constants: five are tuple-unpacked from `_LEXICAL_FALLBACK_REASONS` in one statement, and the family reads three of them (`_REASON_INDEX_MISSING`, `_REASON_INDEX_NOT_READY`, `_REASON_QUERY_FAILED`) alongside search, audit, seed and FTS readers; the unpack stays in `server_impl.py` and the moved code reads each as `server_impl._REASON_<name>` per call.

## Requirements

1. The committed inventory classifies the fifty-three definitions and twelve objects, records the current direct-response reachability closure (joins; thirteen named members, with the conservative AST limitations recorded), every caller, every patch site and every source-text anchor.
2. A new `.wavefoundry/framework/scripts/index_handlers.py` receives the classified set. Closures stay byte-identical; `server_impl.py` rebinds through one module-top block; the module never imports `server_impl` at module top nor another handler module at any scope, reaches staying helpers and the shared constants per call, joins the purge list, and is imported by public name.
3. Patch transparency: the inventory enumerates patch CALLS, not `with` blocks (a block that patches two names is two sites), and repoints every moved-to-moved call to `index_handlers.<name>`; the counts below are block counts from planning and the raw call count in the retrieval module alone is about forty-six, plus the `_background_refresh_active` and `_start_background_index_refresh` patches that sit around `_start_background_index_refresh` or `_trigger_background_index_refresh_for_paths` rather than around the monitor, which are moved-to-moved and must be classified per site. By test file: `test_server_tools_retrieval.py` (`_index_is_up_to_date` around `run_index_rebuild` and `index_build_response`, thirteen blocks; `run_index_rebuild` around `_index_optimize_response` and `_maybe_optimize_index_on_close`, five; `_close_optimize_enabled` and `_index_table_bloat_ratios` around close-time optimize, nine; `_index_build_lock_info` and `_background_build_status` around `index_health_response`, four; `_epoch_state` around `_index_freshness_verdict`, five), `test_indexer.py` (`_index_is_up_to_date`, `_index_build_active`, two), `test_index_optimize_contract.py` (two), `test_sqlite_serving.py` (two), `test_dashboard_server.py` and `test_server_tools.py` (`_background_refresh_active` and `_reap_background_build_pids` around `_start_background_index_refresh`, three; an inert patch here spawns a real indexer). Sites patching a moved name around a staying caller stay observed and are listed as such (everything around `_maybe_refresh_if_stale`, `_chunk_index_coverage` around the FTS and health helpers, `_start_background_index_refresh` around `_fts_schedule_heal`, `_audit_index_snapshot` around `wf_audit_response`, `_maybe_optimize_index_on_close` around `wf_close_wave_response`). Source-text anchors: `test_server_tools_retrieval.py` locates `def index_health_response(` in `server_impl.py` text (repointed with a per-anchor source map) and pins `_index_freshness_verdict` inside `code_ask_response`'s source (survives, the call stays); `test_server_tools.py` reads `inspect.getsource` of `_start_background_index_refresh` through the rebinding (survives).
4. `retrieval_eval.PRODUCTION_RETRIEVAL_MODULES` gains `index_handlers.py`; a sibling of `test_codenav_edit_moves_production_identity` copies the moved file independently of the allowlist and proves an edit moves the production identity; the standing-baseline references in `docs/contributing/review-and-evals.md` (Standing artifact) and `docs/architecture/testing-architecture.md` are repointed to this wave's final receipt, and `test_docs_lint.py`'s `EvaluatorEditBaselinePolicyPinTests`, which pins the literal `retrieval-quality-post-1wybs.json` in both documents, is updated in the same change. Wave `1ymzk`'s memory change repoints the same two references without naming that pin; the operator has been told, and if `1ymzk` lands first the pin already reads whatever it left, so this change edits the pin from that state.
5. The `1yj14` tests retain their existing assertions and behavior coverage. `test_build_epoch_recovery.py`, `test_index_build_retry.py` and `test_index_source_guard.py` pass unmodified. In `test_index_optimize_contract.py`, only the two moved-to-moved mock targets in `OptimizeResultContractTests._failed_optimize` (`_close_optimize_enabled` and `_index_table_bloat_ratios`) move to `index_handlers`; every assertion and the real optimize producer remain unchanged. All but one `test_index_build_retry` case and the optimize-contract module exercise the substrate, so they are weak evidence for the move itself; the response-level evidence is the golden fixture, `test_server_tools_retrieval.py`'s index build, health, status and optimize tests, and the identity assertions.
6. Tests: a `FAMILIES` entry under the tool-to-response map (`index_optimize: _index_optimize_response`); full-classified-set AST assertion; identity assertions for every re-exported name and both mutable objects; reload-proof entry; the production-identity sibling; the existing index, retrieval, FTS, lifecycle and close-time optimize tests pass with only the listed edits.
7. Receipts: after this change the wave's final receipt is recorded under the moved evaluator identity as the new baseline, with the deviation recorded per the wave record.

## Scope

**Problem statement:** the index family is the largest remaining self-contained family, its substrate is already modular, and its responses are the last thing keeping index behavior inside the monolith.

**In scope:** inventory, module, rebinding block with re-exports, purge entry, the named call-time reads, the listed repoints, evaluator membership with its identity test and the three baseline-reference edits, tests, CHANGELOG bullet, architecture doc lines.

**Out of scope:** any change to build, health, optimize or refresh behavior; `index_state_store`, `index_source_guard`, `indexer`; the upgrade publication guard; index-monitor policy on `ImplHandler`; the FTS serving helpers, `_annotate_freshness` and `_state_store_health_summary`, which stay with search.

## Acceptance Criteria

- [x] AC-1: Every classified definition and object lives in `index_handlers.py` and not in `server_impl.py`; the named stayers remain; the full-set AST tests prove it.
- [x] AC-2: The four tools are byte-identical to the golden fixture; every re-exported name and both mutable objects pass their identity assertions.
- [x] AC-3: Purge entry and module-top import present; reload tests and the parameterized proof pass; the manifest lists the module.
- [x] AC-4: The `1yj14` substrate tests pass unmodified, except the two explicitly named optimize-contract mock-owner changes in Requirement 5 with assertions unchanged; the listed patch sites are repointed and the two source-text anchors handled; the named existing test modules pass with no other edit.
- [x] AC-5: `index_handlers.py` is in `PRODUCTION_RETRIEVAL_MODULES` with the identity test passing; the three baseline references and their lint pin are updated; the final receipt is recorded as the new baseline with the deviation logged.
- [x] AC-6: The change's own suites and every test it adds pass, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Commit the inventory including the closure, the patch-site list by file and the source-text anchors.
- [x] Create the module, move the classified set, add the rebinding block, the call-time reads and the purge entry; run the golden fixture and the index test modules.
- [x] Repoint the listed sites; add the `FAMILIES` entry, full-set assertion, identity assertions and reload-proof entry.
- [x] Join the evaluator list, add the identity sibling, update the three baseline references and the lint pin.
- [x] Record the final receipt as the new baseline; architecture doc lines; CHANGELOG bullet; framework suite last; required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| index-inventory | implementer | upgrade-move and the mid-wave after-receipt | Last change; the comparable pair is closed before it starts. |
| index-move | implementer | index-inventory | One owner for `server_impl.py`, the module and `retrieval_eval.py`. |
| independent-review | required reviewers | index-move | Fresh contexts; interlock tests, golden fixture, identity tests. |

## Serialization Points

- `.wavefoundry/framework/scripts/index_handlers.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/retrieval_eval.py`
- `.wavefoundry/framework/scripts/tests/test_handler_modules.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `docs/architecture/current-state.md`
- `docs/architecture/domain-map.md`
- `docs/architecture/testing-architecture.md`
- `docs/contributing/review-and-evals.md`
- `docs/reports/`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/domain-map.md` gain the module; `docs/architecture/testing-architecture.md` (standing baseline row) and `docs/contributing/review-and-evals.md` (Standing artifact) are repointed to the final receipt.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The move is the change. |
| AC-2 | required | Public surface and process state must survive. |
| AC-3 | required | A missed purge entry serves stale code after reload. |
| AC-4 | required | `1yj14` fixed a wedged-epoch defect; about forty sites would go inert otherwise. |
| AC-5 | required | Production retrieval identity moves and must be recorded honestly. |
| AC-6 | required | Change-local correctness. |

## Progress Log

Final delivery checkpoint (2026-09-22): all required lanes and Council approved unchanged reviewed source; R2 baseline independently verified including index AC-5. Full 9,508-test receipt current. Evidence: `evidence/qa-final.md`, `evidence/council-final.md`, `retrieval-evidence.md`. Earlier pending checkpoints are historical and resolved.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Implementation inventory corrects the planning count to 53 definitions, 12 objects and 13 direct-response closure members. Domain ownership preserves dormant helpers and leaves the monitor-only helper in place. Requirement 5 and AC-4 reconcile the two optimize mock-owner moves with unchanged assertions. These are scope census and fixture-location corrections, not behavior changes. | index-handler-inventory.md; current direct-response closure and patch-call census. |
| 2026-09-21 | Planned after a census: 49 definitions, four tools, two mutable caches, outside callers on the measured `code_ask` path. | AST census of `server_impl.py`; `retrieval_eval.TOOLS`. |
| 2026-09-21 | Readiness round: moved to last in the wave because its evaluator-list edit moves evaluator identity; about forty moved-to-moved patch sites listed; `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` becomes a call-time read because the shared fixture assigns it on the server; index-monitor policy and its constants stay with `ImplHandler`; outside-caller list completed (sixteen members on the measured closure); `_reap_dashboard_child_pids` joins the family; the `test_docs_lint.py` baseline pin named; the `1yj14` tests characterized as substrate-level. | Readiness review in this wave directory. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Move the whole family including members reached by search and lifecycle. | Domain ownership; the rebinding block keeps every reach valid. | Split out only the four response functions; strands the substrate-facing helpers. |
| 2026-09-21 | Last in the wave; final receipt becomes the new baseline. | After the pre-R0 containment bootstrap, this change introduces the next evaluator identity boundary; taking R1 first preserves the comparable adoption window. | Second in the wave (first draft); made the whole pair incomparable. |
| 2026-09-21 | Index-monitor policy stays with `ImplHandler`. | `_maybe_refresh_if_stale`, `_read_monitor_config` and their constants are read only by the monitor thread. | Move them with the family; splits a policy from its only reader. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A patch site is missed and a test spawns a real indexer or waits the real verify window. | The inventory lists every site by file and range; the call-time read for the timeout constant covers the fixture. |
| The baseline reference lint pin is missed. | Named in Requirement 4; `1ymzk` is told it owes the same edit. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.


Implementation readback: move the classified 53 functions and 12 objects without changing behavior; preserve public registration and monitor policy. R1 passed against R0 before this move. Gapfill: exact AST inventories and patch-call classification require source parsing beyond indexed retrieval.

Fixture-anchor repair: the full golden anchor resolver detected `_reap_dashboard_child_pids` still targeting server_impl.py. Repointed that one declaration path to index_handlers.py; query, symbol, relevance grade and tool selection are unchanged. R2 records the new fixture identity as well as evaluator membership; R0/R1 already completed before this edit.

The content-anchor check additionally identified the build-lock error string in its moved owner. That one path also moves to index_handlers.py; the expected text and grading are unchanged. A complete corpus-anchor census found no other stale content anchors.

Computational checkpoint: all 111 moved definitions normalize to baseline ASTs; register_mcp_surface, ImplHandler and middleware are byte-identical. Handler module suite: 13 passed, tool golden: 13 passed, registry: 27 passed; generated-manifest and scratch-reload proofs passed. Index identity inclusion mutation is killed; see mutant-evidence.md. Full suite is running; no independent delivery approval claimed.

Full-suite repair: the first 9,508-test run found only stale source-location checks in test_server_tools_lifecycle and test_record_layout_census. Repointed the index-health source anchor and the two comment/docstring allowlist filenames to their new owners; all original assertions and stale-entry checks remain. Targeted controls pass; full suite rerun started.

Full-suite checkpoint: 9,508 tests across 121 files passed, 12 skips, 311.927 seconds. All revised source anchors and mock-owner paths are covered by this run. R2 capture is next; delivery review remains pending.

Operator handoff decision: leave R2 pending. AC-5 remains unmet until the final after receipt is recorded; staged baseline references are not evidence that it exists. Framework implementation and computational verification are complete, but the receipt/review task stays open.
