# Index Handler Inventory

Owner: Engineering
Status: active
Last verified: 2026-09-21

Pre-extraction inventory SHA256 of server source: `480bd4a46551ccd1a0442c18c858d3e0f587ef09566b77babb883b0ee35067c8`. Lines are pre-extraction coordinates; regenerate the computational inventory against the latest source before applying. The inventory is durable evidence, not a Git commit.

## Classified set

53 definitions: `_index_layer_readiness`, `_index_readiness_overview`, `_audit_build_summary`, `_audit_index_snapshot`, `_background_build_status`, `_background_build_progress`, `_index_dir_for_layer`, `_epoch_token`, `_epoch_state`, `_index_freshness_verdict`, `_index_rebuilding_response`, `_index_runtime_failure_response`, `_read_index_rebuild_stats`, `_index_is_up_to_date`, `_index_build_state_path`, `_clear_index_build_state`, `_index_build_log_path`, `_project_background_build_log_path`, `_index_build_stats_path`, `_graph_health_summary`, `_chunk_index_coverage`, `_read_index_build_stats_file`, `_write_index_build_stats_file`, `_refresh_index_build_stats_from_finished_log`, `_refresh_index_build_stats_from_finished_logs`, `_index_build_active`, `_check_index_writer_current`, `run_index_rebuild`, `_index_chunk_matching_address`, `_background_refresh_state_path`, `_indexable_refresh_path`, `_load_background_refresh_state`, `_lock_is_fresh`, `_background_refresh_active`, `_index_builder_cmdline_targets_root`, `_register_background_build_pid`, `_reap_background_build_pids`, `_register_dashboard_child_pid`, `_reap_dashboard_child_pids`, `_start_background_index_refresh`, `_trigger_background_index_refresh_for_paths`, `_index_dir_size`, `_close_optimize_enabled`, `_index_table_bloat_ratios`, `_sqlite_maintenance_failure`, `_maybe_optimize_index_on_close`, `index_health_response`, `_index_optimize_response`, `index_build_response`, `_index_build_lock_info`, `index_build_status_response`, `_index_build_status_response_inner`, `_graph_refresh_then_recheck`.

12 objects: `BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS`, `CLOSE_OPTIMIZE_BLOAT_RATIO`, `_BACKGROUND_BUILD_PIDS`, `_DASHBOARD_CHILD_PIDS`, `_FRESHNESS_CACHE`, `_FRESHNESS_TTL_SECONDS`, `_FRESHNESS_CURRENT`, `_FRESHNESS_STALE`, `_FRESHNESS_UNKNOWN`, `_FTS_DAMAGE_REASONS`, `_INDEX_BUILD_VERIFY_POLL_INTERVAL_SECONDS`, `BACKGROUND_INDEX_LOCK_STALE_SECONDS`.

Stayer: `_index_inputs_stale`, whose sole production caller is the staying monitor `_maybe_refresh_if_stale`. Dormant helpers remain owned by the extracted family; no dead-code deletion is included.

## Measured reach

Conservative AST name-unified closure across server_impl,codenav_handlers,graph_handlers (including methods/nested funcs); attribute collisions remain possible; no arbitrary dynamic _load_script expansion.

Roots: `code_ask_response`, `code_lexical_response`, `code_search_response`, `docs_search_response`.

13 members: `_background_refresh_active`, `_background_refresh_state_path`, `_check_index_writer_current`, `_chunk_index_coverage`, `_epoch_state`, `_index_build_lock_info`, `_index_builder_cmdline_targets_root`, `_index_freshness_verdict`, `_load_background_refresh_state`, `_reap_background_build_pids`, `_reap_dashboard_child_pids`, `_register_background_build_pid`, `_start_background_index_refresh`.

13 current direct-response reachable names suffice to justify membership. Do not force the historical16 count. Registered closures additionally use rebuilding/runtime-failure responses, but evaluator _call_public_path invokes direct response functions, not registrations. Closure is conservative and membership need only one validated supported path.

## Patch and shared-state contracts

Named call-time root reads: `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS`, `_REASON_INDEX_MISSING`, `_REASON_INDEX_NOT_READY`, `_REASON_QUERY_FAILED`.

In index_handlers.py import INDEX_FRESHNESS_STATES as _INDEX_FRESHNESS_STATES from public_contract and keep the original three-name tuple assignment verbatim. Leave LEXICAL_FALLBACK_REASONS/SEARCH_MODES imports and tuple assignments in server_impl. Re-export _FRESHNESS_CURRENT/_STALE/_UNKNOWN; do not convert them to independently duplicated literals or change types.

Patch census contains 127 calls, including fixture/module-scope calls; a patch block is not the counting unit. Final census covers every AST patch call in tests including fixture helpers and module scope. Classification uses the exact qualified containing function and stops at separately mocked callees; targeted source reads resolve callback/public seams. One public no-build guard is strengthened to patch both root and index-handler namespaces. Exact snippets and qualified owners protect application from line drift. Source pins and timeout assignments are separately inventoried.

The optimize-contract fixture changes only the owner of its `_close_optimize_enabled` and `_index_table_bloat_ratios` mocks. Its existing assertions, real producer and failure semantics remain intact. R0/R1 comparison remains pending at preparation of this artifact; R2 must be a NEW baseline after evaluator membership changes, not a comparison across that identity boundary.

## Patch-call inventory

| File | Owner | Target | Classification |
| --- | --- | --- |
| `tests/test_dashboard_server.py` | `DashboardChildReapTests.test_index_refresh_sweeps_dashboard_children` | `_reap_dashboard_child_pids` | repoint-to-index_handlers |
| `tests/test_dashboard_server.py` | `DashboardChildReapTests.test_index_refresh_sweeps_dashboard_children` | `_background_refresh_active` | repoint-to-index_handlers |
| `tests/test_dashboard_server.py` | `DashboardChildReapTests.test_open_does_not_report_zombie_as_serving` | `_reap_dashboard_child_pids` | keep-server_impl |
| `tests/test_dashboard_server.py` | `DashboardChildReapTests.test_start_registers_spawned_dashboard_pid` | `_reap_dashboard_child_pids` | keep-server_impl |
| `tests/test_fts_query_honesty.py` | `ProbedServingTests.test_serving_error_probes_once_types_failure_and_schedules_at_most_once` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_fts_query_honesty.py` | `ProbedServingTests.test_query_path_performs_no_store_writes` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_fts_query_honesty.py` | `ProbedServingTests.test_heal_marker_suppresses_a_second_heal_within_the_same_epoch` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_fts_query_honesty.py` | `ProbedServingTests.test_substitution_after_a_warmed_read_is_detected_at_the_next_epoch_transition` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_fts_query_honesty.py` | `ProbedServingTests.test_the_hybrid_halves_request_no_coverage_at_the_chokepoint` | `_chunk_index_coverage` | keep-server_impl |
| `tests/test_fts_query_honesty.py` | `ProbedServingTests.test_health_exposes_parity_and_the_epoch_cached_verdict` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_graph_snapshot_readers.py` | `GraphFailureRecoveryTests.test_storage_faults_survive_public_consumers_with_both_caches_and_recover` | `index_build_response` | patch-both-namespaces |
| `tests/test_handler_modules.py` | `HandlerResponseTests.setUp` | `index_build_response` | keep-server_impl |
| `tests/test_index_optimize_contract.py` | `OptimizeResultContractTests._failed_optimize` | `_close_optimize_enabled` | repoint-to-index_handlers |
| `tests/test_index_optimize_contract.py` | `OptimizeResultContractTests._failed_optimize` | `_index_table_bloat_ratios` | repoint-to-index_handlers |
| `tests/test_indexer.py` | `ExplicitPrecisionRebuildTests._check_mcp_consumer` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_indexer.py` | `ExplicitPrecisionRebuildTests._check_mcp_consumer` | `_index_build_active` | repoint-to-index_handlers |
| `tests/test_indexer.py` | `ExplicitPrecisionRebuildTests._check_mcp_consumer` | `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` | keep-server_impl-call-time-read |
| `tests/test_lifecycle_golden.py` | `capture._run` | `_maybe_optimize_index_on_close` | keep-server_impl |
| `tests/test_memory_backfill.py` | `HistoricalMemoryBackfillTests.test_public_batch_creates_candidate_then_validation_releases_gate` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_memory_backfill.py` | `HistoricalMemoryBackfillTests.test_public_batch_creates_candidate_then_validation_releases_gate` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_phase_gates.py` | `PhaseGateTests.test_close_passes_with_real_delivery_approvals` | `_maybe_optimize_index_on_close` | keep-server_impl |
| `tests/test_retrieval_candidate_generation.py` | `ColdEpochHybridCostTests.test_first_hybrid_call_in_an_epoch_runs_no_state_probe` | `_chunk_index_coverage` | keep-server_impl |
| `tests/test_server_tools.py` | `PreferredPythonSubprocessTests.test_background_index_refresh_prefers_tool_venv_python` | `_background_refresh_active` | repoint-to-index_handlers |
| `tests/test_server_tools.py` | `TechdocsBaselineToolTests._call` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools.py` | `TechdocsBaselineToolTests.test_registered_tool_is_mutating_and_locks_only_on_run` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools.py` | `UpgradePublicationWrapperContractTests.test_background_index_launcher_is_quiet_during_upgrade` | `_reap_background_build_pids` | repoint-to-index_handlers |
| `tests/test_server_tools_lifecycle.py` | `WaveLifecycleMutationTests.test_wave_add_and_remove_change` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveLifecycleMutationTests.test_wave_add_and_remove_change` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveLifecycleMutationTests.test_typed_review_evidence_tool_previews_then_writes_lightweight_run` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveLifecycleMutationTests.test_wf_prepare_wave_repairs_staged_doc_when_wave_copy_missing` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveLifecycleMutationTests.test_wf_prepare_wave_create_regenerates_codebase_map` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveLifecycleMutationTests.test_wf_review_wave_reports_ok_when_lint_passes` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `GardenDocsIndexRefreshTriggerTests._garden` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveAuditTests.test_healthy_state_returns_ready_true` | `_audit_index_snapshot` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveAuditTests.test_agent_surface_integrity_advisory_rides_the_audit_envelope` | `_audit_index_snapshot` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveAuditTests.test_lint_fail_path` | `_audit_index_snapshot` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveAuditTests.test_advisory_lint_warning_is_rendered_non_blocking_at_the_audit_gate` | `_audit_index_snapshot` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveAuditTests.test_index_absent_path` | `_audit_index_snapshot` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveAuditTests.test_no_active_wave_path` | `_audit_index_snapshot` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveAuditTests.test_no_agent_role_docs_advisory_when_agents_dir_empty` | `_audit_index_snapshot` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveAuditTests.test_no_agent_role_docs_advisory_absent_when_role_docs_present` | `_audit_index_snapshot` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WfAuditBoundedIndexSnapshotTests.test_snapshot_ready_from_metadata_only` | `_audit_build_summary` | repoint-to-index_handlers |
| `tests/test_server_tools_lifecycle.py` | `WfAuditBoundedIndexSnapshotTests.test_snapshot_flags_missing_code_layer_from_configuration` | `_audit_build_summary` | repoint-to-index_handlers |
| `tests/test_server_tools_lifecycle.py` | `WfAuditBoundedIndexSnapshotTests.test_chunker_mismatch_reported_not_conflated_with_freshness` | `_audit_build_summary` | repoint-to-index_handlers |
| `tests/test_server_tools_lifecycle.py` | `WaveCouncilPolicyTests._run_prepare` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `WaveCouncilPolicyTests.test_an_advisory_plus_a_blocker_does_not_publish` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `TypedExclusiveGateDerivationTests._patched` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `TypedExclusiveGateDerivationTests.test_failed_docs_gate_publishes_no_new_roster_receipt_or_projection` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `LegacyProseGateParityTests._run` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `LegacyProseGateParityTests.test_advisory_lint_warning_never_blocks_review_or_close` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_lifecycle.py` | `LegacyProseGateParityTests.test_a_lint_crash_without_a_verdict_blocks_every_gate` | `_trigger_background_index_refresh_for_paths` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.setUp` | `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` | keep-server_impl-call-time-read |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests._run` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_full_flag_propagates` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_index_scope_reflects_full_flag` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_project_all_rebuild_uses_setup_index_script` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_project_code_rebuild_does_not_forward_prefixes_indexer_self_reads` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_up_to_date_returns_without_spawning` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_full_bypasses_up_to_date_check` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_subprocess_early_exit_with_lock_busy_surfaces_failure` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_stats_written_when_previous_log_has_done_marker` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_stats_not_written_when_no_done_marker` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_stats_not_written_when_no_previous_log` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_notice_includes_timing_estimate_when_stats_available` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `RunIndexRebuildTests.test_notice_has_no_timing_estimate_when_no_stats` | `_index_is_up_to_date` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `WaveIndexBuildResponseTests.test_spawn_invalidates_cache` | `run_index_rebuild` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `WaveIndexBuildResponseTests.test_up_to_date_does_not_invalidate_cache` | `run_index_rebuild` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `WaveIndexBuildResponseTests.test_already_running_returns_diagnostic` | `run_index_rebuild` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `WaveIndexHealthTests.test_background_code_build_running_emits_advisory` | `_background_build_status` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `WaveIndexHealthTests.test_background_code_build_completed_no_advisory` | `_background_build_status` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `WaveIndexHealthTests.test_background_code_build_none_no_advisory` | `_background_build_status` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `BackgroundRefreshActiveTests.test_authoritative_held_build_lock_prevents_refresh` | `_index_build_lock_info` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `MaybeRefreshIfStaleTests.test_stale_and_idle_triggers_refresh` | `_background_refresh_active` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `MaybeRefreshIfStaleTests.test_stale_and_idle_triggers_refresh` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `MaybeRefreshIfStaleTests.test_fresh_does_not_trigger` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `MaybeRefreshIfStaleTests.test_already_active_does_not_trigger_second_build` | `_background_refresh_active` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `MaybeRefreshIfStaleTests.test_already_active_does_not_trigger_second_build` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `MaybeRefreshIfStaleTests.test_completed_registered_child_is_reaped_before_refresh_decision` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `MaybeRefreshIfStaleTests.test_reload_empty_registry_rejects_unrelated_persisted_pid_and_refreshes` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `MaybeRefreshIfStaleTests.test_unavailable_pid_classifier_fails_safe_without_spawn` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `CodeAskTests.test_index_freshness_envelope_carries_verdict_states` | `_index_freshness_verdict` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `TestGraphRefreshThenRecheck.setUp` | `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` | keep-server_impl-call-time-read |
| `tests/test_server_tools_retrieval.py` | `TestGraphRefreshThenRecheck.test_recheck_returns_none_when_refresh_raises` | `index_build_response` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `TestGraphToolRefreshOnMiss._assert_refresh_invoked_once` | `index_build_response` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `TestGraphRefreshAndResolve.setUp` | `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` | keep-server_impl-call-time-read |
| `tests/test_server_tools_retrieval.py` | `TestGraphRefreshAndResolve.test_returns_none_tuple_when_refresh_raises` | `index_build_response` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `FreshnessCacheAxesTests.test_ttl_axis_detects_edit_with_generation_unchanged` | `_epoch_state` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `FreshnessCacheAxesTests.test_epoch_axis_refreshes_immediately_on_build_transition` | `_epoch_state` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `FreshnessCacheAxesTests.test_epoch_axis_refreshes_immediately_on_build_transition` | `_epoch_state` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `FreshnessCacheAxesTests.test_unknown_states_pass_through` | `_epoch_state` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `FreshnessCacheAxesTests.test_helper_exception_reads_unknown` | `_epoch_state` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `IndexBuildLockStatusTests.test_health_flags_interrupted_build` | `_index_build_lock_info` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `IndexOptimizeToolTests.test_optimize_tier3_spawns_rebuild` | `run_index_rebuild` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `IndexOptimizeToolTests.test_optimize_tier3_no_rebuild_when_disabled` | `run_index_rebuild` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_returned_maintenance_failure_preserved_by_close_and_optimize` | `_close_optimize_enabled` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_returned_maintenance_failure_preserved_by_close_and_optimize` | `_index_table_bloat_ratios` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_returned_maintenance_failure_preserved_by_close_and_optimize` | `run_index_rebuild` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_returned_maintenance_failure_preserved_by_close_and_optimize` | `run_index_rebuild` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_fires_on_bloated_table_and_reports_reclaim` | `_close_optimize_enabled` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_fires_on_bloated_table_and_reports_reclaim` | `_index_table_bloat_ratios` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_noop_when_no_table_bloated` | `_close_optimize_enabled` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_noop_when_no_table_bloated` | `_index_table_bloat_ratios` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_kill_switch_disables_even_when_bloated` | `_close_optimize_enabled` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_kill_switch_disables_even_when_bloated` | `_index_table_bloat_ratios` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_skips_when_build_lock_held` | `_close_optimize_enabled` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_skips_when_build_lock_held` | `_index_table_bloat_ratios` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_optimize_error_is_swallowed_and_reported` | `_close_optimize_enabled` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_optimize_error_is_swallowed_and_reported` | `_index_table_bloat_ratios` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_needs_rebuild_is_deferred_never_spawned` | `_close_optimize_enabled` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_needs_rebuild_is_deferred_never_spawned` | `_index_table_bloat_ratios` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_needs_rebuild_is_deferred_never_spawned` | `run_index_rebuild` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `CloseTimeOptimizeTests.test_never_raises_on_internal_failure` | `_close_optimize_enabled` | repoint-to-index_handlers |
| `tests/test_server_tools_retrieval.py` | `StalenessMonitorQuietPeriodTests.test_active_refresh_returns_false` | `_background_refresh_active` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `StalenessMonitorQuietPeriodTests.test_defers_while_pending_marker_fresh` | `_background_refresh_active` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `StalenessMonitorQuietPeriodTests.test_defers_while_pending_marker_fresh` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `StalenessMonitorQuietPeriodTests.test_defers_after_recent_build` | `_background_refresh_active` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `StalenessMonitorQuietPeriodTests.test_defers_after_recent_build` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `StalenessMonitorQuietPeriodTests.test_fires_when_quiet_and_stale` | `_background_refresh_active` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `StalenessMonitorQuietPeriodTests.test_fires_when_quiet_and_stale` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `StalenessMonitorQuietPeriodTests.test_fires_when_no_marker_and_no_build` | `_background_refresh_active` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `StalenessMonitorQuietPeriodTests.test_fires_when_no_marker_and_no_build` | `_start_background_index_refresh` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `DriftWorklistAuditSurfaceTests.test_evaluation_stale_is_field_distinguishable_and_never_blocks_ready._with_audit_ready` | `_audit_index_snapshot` | keep-server_impl |
| `tests/test_server_tools_retrieval.py` | `ReapStateSurfaceTests._unheld_lock` | `_index_build_lock_info` | repoint-to-index_handlers |
| `tests/test_setup_readiness_integration.py` | `SharedAssessmentTests.test_registered_health_returns_shared_assessment_before_monitor_snapshot` | `index_health_response` | keep-server_impl |
| `tests/test_sqlite_serving.py` | `SQLiteServingTests.test_coverage_uses_vector_rows_without_legacy_alias` | `_chunk_index_coverage` | keep-server_impl |
| `tests/test_sqlite_serving.py` | `SQLiteServingTests.test_registered_health_actions_match_condition_and_preserve_corruption` | `_index_build_lock_info` | repoint-to-index_handlers |
| `tests/test_sqlite_serving.py` | `SQLiteServingTests.test_registered_health_actions_match_condition_and_preserve_corruption` | `_background_build_status` | repoint-to-index_handlers |
