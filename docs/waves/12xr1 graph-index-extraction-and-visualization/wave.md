# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-28

wave-id: `12xr1 graph-index-extraction-and-visualization`
Title: Graph Index Extraction And Visualization

## Objective

Build the deterministic graph extraction pipeline and ship dashboard visualization that validates graph correctness before any query surface is built on top of it.

## Changes

Change ID: `12xsz-feat graph-index-extraction-and-persistence`
Change Status: `complete`

Change ID: `12xs0-feat graph-dashboard-visualization`
Change Status: `complete`

Change ID: `12xsn-enh prepare-council-verdict-enforcement`
Change Status: `complete`

Change ID: `12xtd-enh changed-files-diff-view`
Change Status: `complete`

Change ID: `12xtu-enh index-tile-and-graph-status`
Change Status: `complete`

Change ID: `12xwy-enh graph-community-clustering`
Change Status: `complete`

Change ID: `12xwz-maint leiden-bootstrap-dependencies`
Change Status: `complete`

Change ID: `12xwa-enh graph-step-logging-and-overlap`
Change Status: `complete`

Change ID: `12xz3-change cluster-overview-aggregation`
Change Status: `complete`

Change ID: `12xzf-change cluster-overview-filtering`
Change Status: `complete`

Change ID: `12xzl-change graph-details-dialog-cleanup`
Change Status: `complete`

Change ID: `12xzy-feat graph-overview-navigation-limits`
Change Status: `complete`

Change ID: `12xzz-enh graph-back-navigation-control`
Change Status: `complete`

Change ID: `12y4x-enh graph-tree-sitter-language-coverage`
Change Status: `complete`

Change ID: `12yiz-enh semantic-index-chunk-delta-embedding`
Change Status: `complete`

Change ID: `12yk0-enh timestamped-index-logs`
Change Status: `complete`

Change ID: `12yl7-enh collapse-graph-method-kind`
Change Status: `complete`

Change ID: `12yli-enh anonymized-council-synthesis-and-agreement-score`
Change Status: `complete`

Completed At: 2026-05-29

## Wave Summary

Wave `12xr1` (Graph Index Extraction And Visualization) delivered 18 changes: Graph Index Extraction And Persistence, Graph Dashboard Visualization, Prepare Council Verdict Enforcement, Changed Files Diff View, Index Tile And Graph Status, Graph Community Clustering, Leiden Bootstrap Dependencies, Graph Step Logging And Overlap, Cluster Overview Aggregation, Cluster Overview Filtering, Graph Details Cleanup, Graph Overview Navigation Limits, Graph Back Navigation Control, Graph Tree-Sitter Language Coverage, Semantic Index Chunk Delta Embedding, Timestamped Index Logs, Collapse Graph Method Kind, and Anonymized Council Synthesis and Seat-Agreement Score. Notable adjustments during implementation: Prepare Council Verdict Enforcement: Implemented structured prepare-council gate enforcement, updated the canonical seed/prompt contract, and added targeted tests for happy path, missing verdict, and malformed verdict cases.; Leiden Bootstrap Dependencies: Added as a bootstrap follow-up so Leiden is installed by the canonical setup path instead of relying on pyproject-only metadata.; Graph Details Cleanup: Removed schema/path pills from the graph detail dialog while preserving the count and build-status summary.

**Changes delivered:**

- **Graph Index Extraction And Persistence** (`12xsz-feat graph-index-extraction-and-persistence`) — 7 ACs completed. Key decisions: --------; Keep graph extraction inside the existing rebuild loop rather than adding a second scan.
- **Graph Dashboard Visualization** (`12xs0-feat graph-dashboard-visualization`) — 6 ACs completed. Key decisions: --------; Keep visualization separate from extraction.
- **Prepare Council Verdict Enforcement** (`12xsn-enh prepare-council-verdict-enforcement`) — 6 ACs completed. Key decisions: --------; Require a structured council verdict rather than a substring marker.
- **Changed Files Diff View** (`12xtd-enh changed-files-diff-view`) — 7 ACs completed. Key decisions: ----------; No loading state in `DiffDialog`
- **Index Tile And Graph Status** (`12xtu-enh index-tile-and-graph-status`) — 9 ACs completed. Key decisions: --------; Rename the tile to "Index" instead of adding a second metric tile.
- **Graph Community Clustering** (`12xwy-enh graph-community-clustering`) — 6 ACs completed. Key decisions: --------; Keep clustering as a derived pass over persisted graph files.
- **Leiden Bootstrap Dependencies** (`12xwz-maint leiden-bootstrap-dependencies`) — 3 ACs completed
- **Graph Step Logging And Overlap** (`12xwa-enh graph-step-logging-and-overlap`) — 4 ACs completed
- **Cluster Overview Aggregation** (`12xz3-change cluster-overview-aggregation`) — 4 ACs completed. Key decisions: Use the persisted cluster metadata to build an aggregated community overview in the dashboard client.
- **Cluster Overview Filtering** (`12xzf-change cluster-overview-filtering`) — 3 ACs completed. Key decisions: Suppress the ungrouped bucket from the default overview when real communities exist.
- **Graph Details Cleanup** (`12xzl-change graph-details-dialog-cleanup`) — 3 ACs completed. Key decisions: Remove the graph schema and graph path pills from the details dialog.
- **Graph Overview Navigation Limits** (`12xzy-feat graph-overview-navigation-limits`) — 8 ACs completed. Key decisions: Keep the community layer, but cap and rank it by relevance and make drilldown single-community only.
- **Graph Back Navigation Control** (`12xzz-enh graph-back-navigation-control`) — 4 ACs completed. Key decisions: Use a unified back control that clears all current graph selections and returns to overview.
- **Graph Tree-Sitter Language Coverage** (`12y4x-enh graph-tree-sitter-language-coverage`) — 5 ACs completed. Key decisions: --------; Treat this as a follow-on change rather than reopening the completed baseline extraction change.
- **Semantic Index Chunk Delta Embedding** (`12yiz-enh semantic-index-chunk-delta-embedding`) — 12 ACs completed. Key decisions: --------; Use the existing LanceDB rows as the source of truth for current chunks during incremental updates.
- **Timestamped Index Logs** (`12yk0-enh timestamped-index-logs`) — 6 ACs completed. Key decisions: --------; Use `.wavefoundry/logs/`, the existing canonical log directory.
- **Collapse Graph Method Kind** (`12yl7-enh collapse-graph-method-kind`) — 4 ACs completed. Key decisions: --------; Collapse `method` into `function` instead of preserving both kinds.
- **Anonymized Council Synthesis and Seat-Agreement Score** (`12yli-enh anonymized-council-synthesis-and-agreement-score`) — 7 ACs completed. Key decisions: --------; Adopt anonymized synthesis + aggregate score on the single model
## Acceptance Criteria

- `graph_indexer.extract_file()` runs inside `indexer.py`'s existing file loop alongside the chunker; no second filesystem walk
- `project-graph.json` and `framework-graph.json` are written on every full rebuild and updated incrementally on partial rebuilds
- graph files carry a schema version and builder version so incompatible extractor changes force a clean rebuild
- Graph schema ships with `EXTRACTED`, `AMBIGUOUS`, and `INFERRED` confidence fields from day one; doc-to-code edges via grep use `AMBIGUOUS`
- persisted graph relations are directional (`source` -> `target`) and may be projected for visualization, but the stored graph remains canonical
- Stable symbol ID scheme: `{relative_path}::{qualified_name}`; no ambiguity across files with same symbol names
- Incremental invalidation: changed file re-extraction removes stale outgoing edges; reverse index propagates invalidation to files with incoming edges from changed symbols
- Deletion contract: file re-extraction with empty result removes all prior edges; file removal from project cleans the per-file cache and reverse index entries
- Dashboard graph view renders project graph with force-directed layout, node coloring by kind, edge labels by relation, and filter controls for kind/relation/file
- `/api/graph` endpoint is layer-selectable (`project` or `framework`) and returns schema-versioned graph data from the dashboard server
- Community overview suppresses the ungrouped bucket by default, ranks communities by relevance, and keeps only one organizational layer on screen at a time
- Unit tests cover: node/edge extraction correctness, incremental cache behavior, deletion cleanup, reverse index consistency, graph schema versioning, and dashboard API contract

## Journal Watchpoints

- `framework_edit_allowed` gate required before editing `indexer.py`, `chunker.py`, or any framework script
- Dashboard changes (JS, CSS, Python server) require the gate as well; open once, close after all dashboard edits are complete
- Do not modify default output of any existing MCP tool in this wave — graph index is additive only
- Visualization is in this wave to validate graph correctness, not for production polish; defer advanced UX to a later wave
- Graph navigation limits remain additive: keep the community overview useful, but avoid surfacing overly broad clusters or mixed organizational layers in the default view

## Review Evidence

- wave-council-readiness: approved — wave 1 is split into deterministic graph extraction/persistence and dashboard validation; the scope is additive, Graphify references are documented, and default MCP output remains unchanged. 2026-05-27.
- wave-council-readiness: approved-with-conditions (moderator: council-moderator — 12yli admitted; full-tier primer; conditions folded into change doc: two-tier non-waiver guard (Req 8/AC-7), benefit reframed as anchoring-reduction hypothesis, default-vs-opt-in resolved to default. 2026-05-28).
- wave-council-delivery: approved (2026-05-28) — delivery review verdict was `pass-with-conditions` (seat_agreement: unanimous accepted-with-concerns; max_severity: high). All raised concerns were addressed before closure; see the delivery Review Checkpoint below. Re-verified by full framework suite (1768 tests OK).
- operator-signoff: approved (2026-05-29) — operator authorized closure after delivery concerns were addressed.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-05-28: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: the new semantic chunk-delta change can silently corrupt retrieval if reused vectors are paired with stale row metadata or mixed old/new LanceDB schemas; strongest-alternative: keep file-level replacement and accept slower updates until graph work closes)
  - Strongest challenge: the graph extraction change adds a second graph artifact to the rebuild pipeline, so incremental invalidation and deletion handling must stay correct under rename/move churn.
  - Best alternative considered: defer dashboard validation until the later query wave and ship extraction only.
  - Council verdict: keep wave 1 split into extraction/persistence plus dashboard validation, because the two changes are mechanically separate but depend on the same persisted graph files and the dashboard is the right validation surface for first release.
  - No blocking contradictions remain in the admitted scope.
- **Prepare-phase Wave Council [prepare-council] — 2026-05-28: PASS** (moderator: council-moderator; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: anonymized synthesis could strip the lane identity that gives a blocking required-lane finding its authority, letting it be merit-weighted below blocking and silently diluting a required gate; strongest-alternative: gate the new behavior behind an opt-in `wave_council_policy` flag for safer per-repo rollout instead of changing the default protocol)
  - Scope reviewed: newly admitted `12yli-enh anonymized-council-synthesis-and-agreement-score` (single-model anonymized council synthesis + seat-agreement/severity aggregate). Prior 17 changes are complete and were covered by the 2026-05-28 standard-tier verdict above.
  - Seat convergence: all Phase 2 seats returned approved-with-notes; no blockers. Dominant condition (primer + security + architecture): resolve the anonymization-vs-non-waiver tension in seed wording before implementation.
  - reality-checker: on a single model, anonymization is an anchoring-reduction hypothesis, not measured decorrelation — the change must not over-claim.
  - Conditions folded into the change doc: Requirement 8 + AC-7 (two-tier identity handling preserving non-waiver), Rationale reframed as hypothesis, default-vs-opt-in decision recorded (resolved to default protocol change; opt-in alternative captured in Decision Log).
  - Verdict: PASS with conditions — `12yli` is admissible for implementation; conditions are recorded and reversible.
- pre-implementation-review: passed (2026-05-28) — Pre-mortem highest risk: the rendered self-hosted surfaces (`docs/agents/council-moderator.md`, `docs/prompts/council-review.prompt.md`) are NOT mechanically re-rendered by `render_platform_surfaces.py`/`render_agent_surfaces.py` (those cover hooks/MCP/bin/guru regions only) and have already diverged from seeds 215/230. Mitigation: edit canonical seeds (215, 007, 230) as source of truth, then manually sync the two self-hosted surfaces; run framework tests + docs-lint to catch any seed-content assertions. Builder lane: `implementer` (cross-cutting prompt/seed edit). Scope limited to `12yli`; prior 17 changes complete.
- **Delivery-phase Wave Council [delivery-council] — 2026-05-28: PASS** (verdict `pass-with-conditions` → all conditions resolved; seat_agreement: unanimous; max_severity: high). Findings raised and their resolutions:
  - **[BLOCKING — resolved] Incremental graph retained stale edges to deleted/renamed targets.** `graph_indexer.finalize()` did not prune edges whose endpoint node was removed, violating AC (incremental invalidation / deletion contract). Fix: `finalize()` now computes `removed_paths` (prior-state files absent from `current_paths`) and `removed_symbols` (defs that vanished from re-extracted files) and prunes any edge whose source/target is a removed path or removed symbol — covering deletion, file rename, and within-file symbol rename for surviving (unchanged) referrers. `GRAPH_BUILDER_VERSION` bumped `2`→`3` to force a clean rebuild of existing graphs. Tests: `test_deleting_referenced_code_file_prunes_unchanged_doc_edges`, `test_renaming_code_file_prunes_stale_old_path_edges`, `test_builder_version_bump_discards_stale_state`.
  - **[SHOULD-FIX — resolved] `AMBIGUOUS` confidence was never emitted.** Doc-to-code grep edges used `INFERRED`, contradicting AC "doc-to-code edges via grep use `AMBIGUOUS`". Fix: `doc_references_code` edges now emit `AMBIGUOUS`; explicit markdown-link `doc_references_doc` edges remain `EXTRACTED`. Test: `test_doc_to_code_edges_use_ambiguous_confidence`.
  - **[MEDIUM — resolved] Community overview ignored the relation filter.** `_buildCommunityOverviewGraph` received `selectedRelations` but never applied it. Fix: aggregated cross-community edges now skip relations outside `selectedRelations`, matching the per-node graph filter. Test asserts the guard in `dashboard.js`.
  - **[LOW — resolved] chunk_hash homogeneity gap.** `_plan_lance_delta_rows` only guarded against a missing `chunk_hash` *key*, not a present-but-empty value. Fix: table-wide preflight now forces a full table rebuild when any existing row lacks a usable (non-blank) `chunk_hash`. Tests: `test_missing_chunk_hash_key_forces_full_rebuild`, `test_empty_chunk_hash_value_forces_full_rebuild`.
  - **[LOW — resolved] Dead code + missing fallback diagnostic.** Removed unused `graph_cluster._build_clusters`; removed dead `BREADCRUMB_VISIBLE` and demoted the never-switched `layer` state to a constant in `GraphPanel` (framework-layer visualization deferred to the visualization/navigation overhaul). Added an explicit verbose "Leiden backend unavailable → label-propagation" fallback log. Tests: `test_update_graph_clusters_logs_label_propagation_fallback`, `test_api_graph_rejects_unsupported_layer`.

## Dependencies

- No external wave dependencies.
- Wave `12xr2 graph-query-surface` must not open until this wave is closed and graph files are validated via dashboard visualization.
