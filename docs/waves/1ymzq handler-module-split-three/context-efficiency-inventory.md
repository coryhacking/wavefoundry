# Context Efficiency Move Inventory

Owner: Engineering
Status: active
Last verified: 2026-09-21

Captured before extraction. Source SHA256: `7235f017c3d120b5ff704b9eec6e5cafed28a269d54abf286ad21da1b7ad59c3`. Inventory is durable evidence, not a Git commit. MCP source navigation preceded AST bulk enumeration.

## Classified set

| Kind | Symbol |
| --- | --- |
| definition | `_read_ce_projection_config` |
| definition | `_pending_ce_generations` |
| definition | `_maybe_project_context_efficiency` |
| definition | `_project_context_efficiency_wave` |
| definition | `_flush_context_efficiency` |
| definition | `project_pending_context_efficiency` |
| definition | `project_pending_context_efficiency_root` |
| definition | `_context_efficiency_state` |
| definition | `wf_context_efficiency_eval_response` |
| definition | `_state_sources_review_evidence` |
| definition | `_state_sources_get_change` |
| definition | `_state_sources_live_waves` |
| definition | `_state_sources_list_plans` |
| definition | `_state_sources_map` |
| definition | `_state_sources_memory_validate` |
| definition | `_state_sources_memory_propose` |
| definition | `_state_sources_memory_views` |
| object | `_CE_PROJECTION_MIN_QUIET_SECONDS` |
| object | `_CE_PROJECTION_DEFAULT_QUIET_SECONDS` |
| object | `_CE_PROJECTION_MAX_QUIET_SECONDS` |
| object | `_CE_PROJECTION_POLL_SECONDS` |
| object | `_STATE_SOURCE_EXTRACTORS` |

## Boundary decisions

The monitor, middleware and registrar remain byte-identical. The three memory source extractors belong to CE and move with its dictionary. `_STATUS_PATTERN` remains root-owned; `list_waves` has no actual moved-family reference. All staying dependencies are read per call. `_maybe_project_context_efficiency` deliberately reads the root re-export of `_read_ce_projection_config` so the real monitor interlock patch remains effective. The publication lock also stays a root call-time read. A TYPE_CHECKING-only import of ImplHandler preserves quoted annotations without a runtime root import.

Direct owner imports: `context_efficiency`, `index_source_guard`, `record_paths`, `lifecycle_gate_support._read_wave_record_text`, `review_evidence.ProjectPublicationUnavailable`.

Staying per-call dependencies: `_STATUS_PATTERN`, `_atomic_replace_text`, `_attempt_focus_state`, `_find_wave_md`, `_focus_clear_write_needed`, `_load_script`, `_response`, `_wave_checkpoint_floor`, `project_state_publication_lock`.

## Root callers and reads

| Symbol | Caller | Pre-move line |
| --- | --- | --- |
| `_CE_PROJECTION_DEFAULT_QUIET_SECONDS` | `_read_ce_projection_config` | 8260 |
| `_CE_PROJECTION_MAX_QUIET_SECONDS` | `_read_ce_projection_config` | 8270 |
| `_CE_PROJECTION_MIN_QUIET_SECONDS` | `_read_ce_projection_config` | 8271 |
| `_CE_PROJECTION_POLL_SECONDS` | `_read_ce_projection_config` | 8273 |
| `_read_ce_projection_config` | `_maybe_project_context_efficiency` | 8297 |
| `_pending_ce_generations` | `_maybe_project_context_efficiency` | 8298 |
| `project_pending_context_efficiency_root` | `_maybe_project_context_efficiency` | 8319 |
| `_project_context_efficiency_wave` | `_flush_context_efficiency` | 20529 |
| `project_pending_context_efficiency_root` | `project_pending_context_efficiency` | 20563 |
| `_project_context_efficiency_wave` | `project_pending_context_efficiency_root` | 20603 |
| `_flush_context_efficiency` | `_lifecycle_context_result` | 21209 |
| `_read_ce_projection_config` | `ImplHandler._start_ce_projection_monitor` | 21419 |
| `_maybe_project_context_efficiency` | `ImplHandler._start_ce_projection_monitor._loop` | 21429 |
| `_read_ce_projection_config` | `ImplHandler.background_monitor_status` | 21461 |
| `_state_sources_review_evidence` | `<module>` | 22042 |
| `_state_sources_memory_validate` | `<module>` | 22043 |
| `_state_sources_memory_propose` | `<module>` | 22044 |
| `_state_sources_get_change` | `<module>` | 22045 |
| `_state_sources_live_waves` | `<module>` | 22046 |
| `_state_sources_live_waves` | `<module>` | 22047 |
| `_state_sources_list_plans` | `<module>` | 22048 |
| `_state_sources_map` | `<module>` | 22049 |
| `_state_sources_memory_views` | `<module>` | 22050 |
| `_state_sources_memory_views` | `<module>` | 22051 |
| `_STATE_SOURCE_EXTRACTORS` | `_wrap_first_party_tool_costs._make.wrapped` | 22159 |
| `_context_efficiency_state` | `register_mcp_surface.wf_current_wave` | 23242 |
| `_flush_context_efficiency` | `register_mcp_surface.wf_pause_wave` | 23642 |
| `wf_context_efficiency_eval_response` | `register_mcp_surface.wf_context_efficiency_eval` | 23735 |
| `_flush_context_efficiency` | `register_mcp_surface.wf_reopen_wave` | 24130 |
| `_context_efficiency_state` | `register_mcp_surface.wf_audit` | 24458 |
| `project_pending_context_efficiency` | `register_mcp_surface.wf_upgrade` | 24718 |

## Cross-file references and test anchors

AST/name references are a bounded mechanical census, not a claim that every matching test string executes a caller. Moved-to-moved patch sites are the two projector patches in test_server_context_efficiency. Its projector source read and focus-caller census are the two source anchors. Existing index_source_guard patches remain unchanged. Parent-owned handler-module tests gain the CE family/full-set/identity/reload coverage and reclassify the three memory extractors.

| File | Line | Symbol |
| --- | --- | --- |
| `.wavefoundry/framework/scripts/project_context_efficiency.py` | 21 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/project_context_efficiency.py` | 21 | `project_pending_context_efficiency_root` |
| `.wavefoundry/framework/scripts/server.py` | 598 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_handler_modules.py` | 94 | `_state_sources_memory_validate` |
| `.wavefoundry/framework/scripts/tests/test_handler_modules.py` | 94 | `_state_sources_memory_propose` |
| `.wavefoundry/framework/scripts/tests/test_handler_modules.py` | 95 | `_state_sources_memory_views` |
| `.wavefoundry/framework/scripts/tests/test_index_source_guard.py` | 37 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_index_source_guard.py` | 65 | `_read_ce_projection_config` |
| `.wavefoundry/framework/scripts/tests/test_index_source_guard.py` | 146 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_index_source_guard.py` | 200 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_memory_records.py` | 3840 | `_flush_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_memory_records.py` | 3861 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_record_layout_nested.py` | 329 | `_state_sources_memory_propose` |
| `.wavefoundry/framework/scripts/tests/test_record_layout_nested.py` | 336 | `_state_sources_memory_propose` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 268 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 272 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 313 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 361 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 398 | `_maybe_project_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 399 | `_maybe_project_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 400 | `_maybe_project_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 444 | `_maybe_project_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 446 | `_maybe_project_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 447 | `_maybe_project_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 448 | `_maybe_project_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 486 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 504 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 523 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 523 | `project_pending_context_efficiency_root` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 567 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 573 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 631 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 663 | `_maybe_project_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 691 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 694 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 694 | `project_pending_context_efficiency_root` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 708 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 711 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 711 | `project_pending_context_efficiency_root` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 867 | `wf_context_efficiency_eval_response` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 882 | `wf_context_efficiency_eval_response` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 891 | `wf_context_efficiency_eval_response` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 941 | `wf_context_efficiency_eval_response` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 989 | `wf_context_efficiency_eval_response` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 994 | `wf_context_efficiency_eval_response` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 999 | `wf_context_efficiency_eval_response` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 1017 | `wf_context_efficiency_eval_response` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 1038 | `wf_context_efficiency_eval_response` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 1112 | `_context_efficiency_state` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 2939 | `project_pending_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 3003 | `_context_efficiency_state` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 3042 | `_flush_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 3157 | `_context_efficiency_state` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 3242 | `_flush_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 3383 | `_flush_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 3451 | `_flush_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 3504 | `_flush_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 3507 | `_flush_context_efficiency` |
| `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py` | 4222 | `_project_context_efficiency_wave` |
| `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py` | 5505 | `_state_sources_review_evidence` |
| `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py` | 5513 | `_state_sources_review_evidence` |
| `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py` | 5519 | `_state_sources_review_evidence` |
| `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py` | 3570 | `_read_ce_projection_config` |
| `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py` | 3577 | `_read_ce_projection_config` |
| `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py` | 3584 | `_read_ce_projection_config` |
| `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py` | 3591 | `_read_ce_projection_config` |
| `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py` | 3600 | `_read_ce_projection_config` |

## Implementation verification

All seventeen moved definitions match the pre-move HEAD AST after stripping only inserted local server imports and documented server_impl attribute qualification. Generator also proved register_mcp_surface, ImplHandler and _wrap_first_party_tool_costs byte-identical at extraction. No source edits to existing interlock tests. The four named CE test anchors changed; CE handler import follows server import so it references the post-purge module. Focused runs: 113 server/guard/lifecycle tests and 381 core/platform/memory tests passed with no skips. Whole-suite receipt and coordinator-owned golden/reload family tests remain pending.
