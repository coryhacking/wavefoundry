# Handler Extraction Inventory

Owner: Engineering
Status: active
Last verified: 2026-09-20

Source: `server_impl.py` at `8941bede3ccf7357639e6510d0f9b0ea22cd4c34`. Independently derived with live MCP reads, AST and exact-reference census before the move. The semantic index reported stale/incomplete enumeration; it was not used as a complete census.

| Definition | Callers / used by | Classification |
| --- | --- | --- |
| `_BetweennessUnsupportedForCollapsedView` | `_wf_graph_report_response_pinned` | move:graph |
| `_annotate_java_call_sites_with_receiver_type` | `_scan_call_sites_in_file` | move:graph |
| `_apply_keyword_limit` | `code_keyword_response` | move:codenav |
| `_apply_reference_filters` | `code_references_response` | move:codenav |
| `_attach_auto_rebuild_diag` | `code_callhierarchy_response`, `_code_impact_graph_response`, `code_risk_score_response`, `code_callgraph_response`, `_wf_graph_report_response_pinned`, `code_graph_path_response`, `_code_graph_community_response_pinned` | move:graph |
| `_bracket_depth` | `_take_balanced_value`, `code_constants_response` | move:codenav |
| `_code_graph_community_response_pinned` | `code_graph_community_response` | move:graph |
| `_code_impact_graph_response` | `code_impact_response` | move:graph |
| `_code_impact_heuristic_response` | `code_impact_response` | move:graph |
| `_css_definitions` | `code_definition_response` | move:codenav |
| `_dedupe_navigation_results` | `code_definition_response`, `code_references_response` | move:codenav |
| `_definition_match_kind` | `_python_definitions`, `_treesitter_definition_results`, `_regex_definitions`, `_css_definitions` | move:codenav |
| `_definition_sort_key` | `code_definition_response` | move:codenav |
| `_edit_governance_for_path` | `code_read_response` | move:codenav |
| `_extract_const_value` | `code_constants_response` | move:codenav |
| `_extract_java_owner_class_from_node_id` | `code_callhierarchy_response` | move:graph |
| `_find_node_at_line` | `_find_node_at_line`, `_structural_for_range` | move:codenav |
| `_find_smallest_containing_ts_node` | `_find_smallest_containing_ts_node`, `_structural_for_range` | move:codenav |
| `_first_call_site_at_or_after` | `code_callhierarchy_response`, `code_callgraph_response` | move:graph |
| `_graph_auto_rebuild_diagnostic` | `_attach_auto_rebuild_diag` | move:graph |
| `_graph_constant_reader_refs` | `code_references_response` | move:codenav |
| `_graph_definition_candidate_files` | `code_definition_response` | move:codenav |
| `_graph_references_candidate_files` | `code_references_response` | move:codenav |
| `_graph_refresh_and_resolve` | `code_callhierarchy_response`, `_code_impact_graph_response`, `code_callgraph_response` | move:graph |
| `_graph_unavailable_fields` | `code_callhierarchy_response`, `_code_impact_graph_response`, `code_risk_score_response`, `code_callgraph_response`, `_wf_graph_report_response_pinned`, `code_graph_path_response` | move:graph |
| `_hover_python` | `code_hover_response` | move:codenav |
| `_hover_regex` | `code_hover_response` | move:codenav |
| `_hover_treesitter` | `code_hover_response` | move:codenav |
| `_innermost_symbol` | `_hover_python`, `_hover_treesitter` | move:codenav |
| `_keyword_fallback_definitions` | `code_definition_response`, `code_references_response` | move:codenav |
| `_load_cluster_lookup_with_ids` | `code_callhierarchy_response`, `_code_impact_graph_response` | move:graph |
| `_marker_regions_in_range` | `code_read_response` | move:codenav |
| `_match_import_to_target` | `_code_impact_heuristic_response` | move:graph |
| `_outline_python` | `code_outline_response`, `_hover_python` | move:codenav |
| `_outline_regex_tier` | `code_outline_response`, `_hover_regex` | move:codenav |
| `_outline_treesitter` | `code_outline_response`, `_hover_treesitter` | move:codenav |
| `_outline_ts_name` | `_outline_treesitter` | move:codenav |
| `_python_definitions` | `code_definition_response` | move:codenav |
| `_python_references` | `code_references_response` | move:codenav |
| `_reference_bucket` | `_reference_counts`, `_apply_reference_filters`, `code_references_response` | move:codenav |
| `_reference_counts` | `code_references_response` | move:codenav |
| `_reference_detail_counts` | `code_references_response` | move:codenav |
| `_reference_sort_key` | `_apply_reference_filters` | move:codenav |
| `_regex_definitions` | `code_definition_response` | move:codenav |
| `_resolve_java_receiver_type` | `_annotate_java_call_sites_with_receiver_type` | move:graph |
| `_scan_all_call_sites_in_file` | `code_callhierarchy_response`, `code_callgraph_response` | move:graph |
| `_scan_call_sites_in_file` | `code_callhierarchy_response` | move:graph |
| `_sql_schema_doc_mention_refs` | `code_references_response` | move:codenav |
| `_sql_schema_retry_symbol` | `_sql_schema_doc_mention_refs`, `code_definition_response`, `code_references_response` | move:codenav |
| `_string_literal_end` | `_bracket_depth`, `_take_balanced_value` | move:codenav |
| `_strip_leading_comment_lines` | `_extract_const_value` | move:codenav |
| `_structural_for_range` | `code_read_response` | move:codenav |
| `_structural_python_ast` | `_structural_for_range` | move:codenav |
| `_suggest_near_communities` | `_code_graph_community_response_pinned` | move:graph |
| `_take_balanced_value` | `_extract_const_value` | move:codenav |
| `_treesitter_definition_results` | `code_definition_response` | move:codenav |
| `_ts_node_name` | `_structural_for_range` | move:codenav |
| `_wf_graph_report_response_pinned` | `wf_graph_report_response` | move:graph |
| `code_callgraph_response` | `register_mcp_surface` | move:graph |
| `code_callhierarchy_response` | `register_mcp_surface` | move:graph |
| `code_commit_provenance_response` | `register_mcp_surface` | move:codenav |
| `code_constants_response` | `register_mcp_surface` | move:codenav |
| `code_definition_response` | `register_mcp_surface` | move:codenav |
| `code_dependencies_response` | `register_mcp_surface` | move:codenav |
| `code_graph_community_response` | `register_mcp_surface` | move:graph |
| `code_graph_path_response` | `register_mcp_surface` | move:graph |
| `code_hover_response` | `register_mcp_surface` | move:codenav |
| `code_impact_response` | `register_mcp_surface` | move:graph |
| `code_keyword_response` | `WaveIndex`, `_code_ask_response_body`, `register_mcp_surface` | move:codenav |
| `code_lexical_response` | `register_mcp_surface` | move:codenav |
| `code_list_files_response` | `register_mcp_surface` | move:codenav |
| `code_outline_response` | `register_mcp_surface` | move:codenav |
| `code_pattern_response` | `register_mcp_surface` | move:codenav |
| `code_read_response` | `register_mcp_surface` | move:codenav |
| `code_references_response` | `register_mcp_surface` | move:codenav |
| `code_risk_score_response` | `register_mcp_surface` | move:graph |
| `wf_graph_report_response` | `register_mcp_surface` | move:graph |

Shared path/ignore walkers, loaders, parser/reference/snapshot helpers and response diagnostics stay in the composition root; moved functions resolve retained globals through a function-local public `server_impl` import. All 19 response names remain aliases there. Private-helper tests follow the defining module. Constants stay with their current owner. No moved definition has global/nonlocal writes, decorators or nonliteral defaults.

The evaluator reaches lexical and keyword through measured tools and outline/constants directly for anchor resolution; only codenav joins its production fingerprint. The sole moved corpus anchor is `agentic-calibration-lexical-backfill` / `code_lexical_response`. The two content anchors stay in `run_index_rebuild` and `wf_audit_response`.

Source-sensitive tests: mixed-table fusion needs a per-anchor source map; edge-trust hierarchy count needs the relocated function source and retains its two-branch assertion; lexical honesty still inspects the rebound function. Dynamic response patches continue through server aliases. Tests of moved private helpers must target their defining module.

Limit: current AST/name/reference census plus inspected computed-name sites; not a proof against arbitrary runtime reflection.
