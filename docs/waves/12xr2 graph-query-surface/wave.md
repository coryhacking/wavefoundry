# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-05-27

wave-id: `12xr2 graph-query-surface`
Title: Graph Query Surface

## Objective

Ship new standalone MCP graph query tools and define the opt-in augmentation API for existing tools, backed by the validated graph index from the previous wave.

## Changes

Change ID: `12xs4-feat graph-query-surface`
Change Status: `planned`

## Wave Summary

Adds `code_impact` and `code_callgraph` MCP tools for structural graph traversal, a `wave_graph_report` command for structural summaries (top callers, orphan docs, high-fan-out nodes), and a union view that composes project and framework graphs at query time for cross-layer traversal. Defines a `graph=true` opt-in parameter on `code_keyword`, `code_search`, `code_definition`, and `code_references` that returns graph neighbor results as a clearly labeled supplemental section. Default output of all existing tools is unchanged.

## Acceptance Criteria

- `code_impact(symbol)` returns files and symbols that would be affected by changing the given symbol, traversing the graph up to a configurable hop limit
- `code_callgraph(symbol)` returns direct callers and callees, with optional depth expansion
- `wave_graph_report` returns a structural summary: top callers by fan-in, orphan doc pages (no graph edges), high-fan-out nodes, and cross-layer references
- Union view: `load_union()` composes `project-graph.json` and `framework-graph.json` via `networkx.compose()`; nodes tagged by `layer` attribute; used at query time only, not persisted; safe below ~50k combined nodes
- `graph=true` parameter accepted by `code_keyword`, `code_search`, `code_definition`, `code_references`; when set, supplemental graph neighbor section appended after existing output; clearly labeled and non-breaking
- Default behavior (`graph=false`) of all existing tools is byte-for-byte identical to pre-wave behavior
- All new tools have unit tests; augmentation tests cover both `graph=true` and `graph=false` paths

## Journal Watchpoints

- `framework_edit_allowed` gate required before editing any MCP server tool or framework script
- The `graph=true` augmentation must never appear in default tool output — this is a hard constraint; the upgrade path to default requires a separate wave with explicit sign-off
- Verify union view memory footprint is acceptable before shipping; if `networkx.compose()` cost shows up in profiling, document and file a follow-up

## Review Evidence

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Depends on wave `12xr1 graph-index-extraction-and-visualization` being closed and graph files validated via dashboard visualization before this wave opens.
