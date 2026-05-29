# Graph Index Extraction And Persistence

Change ID: `12xsz-feat graph-index-extraction-and-persistence`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The semantic index already answers retrieval questions like "what is this thing" and "where is it mentioned". It does not answer structural questions well enough: what calls what, what imports what, which docs point at which code, or what the blast radius is when a symbol changes. The first wave adds a persistent graph layer to cover that gap while keeping the semantic index intact.

The reference implementation is Graphify, but only as a shape guide. Wavefoundry will borrow the pipeline separation, provenance discipline, and export/report idea. It will not copy Graphify's multimodal ingest or LLM-assisted baseline extraction.

## Requirements

1. Build graph extraction inside the existing `indexer.py` rebuild flow, not as a second filesystem walk.
2. Emit `project-graph.json` and `framework-graph.json` alongside every rebuild so graph state stays aligned with the semantic index layers.
3. Keep graph extraction deterministic in the baseline: AST/import analysis for code, symbol-name matching for doc-to-code references, and no LLM calls.
4. Include provenance on every edge. The baseline schema must distinguish deterministic edges from heuristic ones so later waves can add semantic augmentation without changing the shape.
5. Store the canonical graph as a directed graph (`source` -> `target`) because `calls`, `imports`, and `references` are directional relations. Any undirected projection is a derived view for later analysis or visualization, not the persisted source of truth.
6. Version the graph schema and graph builder state in the persisted artifact so extractor changes can force a full rebuild the same way the semantic index uses `walker_version` and chunker/model versions.
7. Maintain incremental correctness for adds, edits, renames, moves, and deletions with a per-file cache and reverse dependency index.
8. Add tests for node/edge extraction, cache invalidation, deletion cleanup, graph schema versioning, and graph file persistence.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py`
- a new `graph_indexer.py` helper under `.wavefoundry/framework/scripts/`
- `project-graph.json` and `framework-graph.json`
- tests for graph extraction and persistence

**Out of scope:**

- query tools
- graph augmentation of existing MCP search tools
- semantic or LLM-derived graph edges in the baseline
- dashboard polish beyond validation of the graph shape

## Graphify Reference Implementation

Graphify is a good reference because it separates detection, extraction, build, analysis, visualization, and serving into distinct modules. The relevant modules and what they do:

| Graphify module | What it does | Wavefoundry takeaway |
| --- | --- | --- |
| [`graphify/__main__.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/__main__.py) | CLI orchestration and host integration (`install`, `claude`, `vscode`, `hook`, `benchmark`) | Keep host integration separate from the graph pipeline; do not bury orchestration in the extractor |
| [`graphify/detect.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/detect.py) | Detects files and classifies them before extraction | Wavefoundry should not add a second repo walk; `indexer.py` already has the file list |
| [`graphify/extract.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/extract.py) | Extracts structure from source, using tree-sitter for code and semantic extraction for unstructured inputs | Wavefoundry phase 1 should stay deterministic: AST/import analysis for code, symbol matching for docs |
| [`graphify/build.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/build.py) | Assembles extracted data into the persistent graph | Mirror this as a separate graph assembly step, but keep it inside the existing rebuild pipeline |
| [`graphify/cluster.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/cluster.py) | Community detection / grouping | Defer this; phase 1 only needs persistent graph edges and traversal-ready structure |
| [`graphify/analyze.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/analyze.py) | Centrality and cross-community analysis | Good source for the later graph report wave, not the first extraction wave |
| [`graphify/callflow_html.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/callflow_html.py) | Exports call-flow and architecture visualizations | Relevant later as the presentation pattern, but not part of this wave |
| [`graphify/serve.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/serve.py) | MCP graph serving | Relevant later if graph queries become a first-class MCP surface |
| [`graphify/watch.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/watch.py) | Rebuild/watch automation | A useful reference for future graph refresh automation, but not required for phase 1 |

Graphify also documents the graph artifact shape as a persistent `graph.json` plus report output. That is the right conceptual model for Wavefoundry, but Wavefoundry will keep two physical graph files aligned to the existing index layers rather than one monolithic graph.

## Acceptance Criteria

- [x] AC-1: Graph extraction runs inside the existing `indexer.py` rebuild path alongside chunking and embedding, without a second repository walk.
- [x] AC-2: `project-graph.json` and `framework-graph.json` are written on every rebuild and updated incrementally when only a subset of files changes.
- [x] AC-3: Graph edges include provenance, with deterministic baseline edges separated from heuristic edges.
- [x] AC-4: Stable node IDs are derived from file path plus qualified symbol name so same-named symbols in different files do not collide.
- [x] AC-5: File deletion, rename, and symbol move scenarios invalidate stale outgoing and incoming graph edges correctly.
- [x] AC-6: The persisted graph format records a schema version and builder version so incompatible extractor changes force a clean rebuild.
- [x] AC-7: Tests cover extraction correctness, invalidation behavior, deletion cleanup, graph schema versioning, and graph file persistence.

## Tasks

- [x] Add `graph_indexer.py` with a deterministic extraction API and per-file cache format.
- [x] Integrate graph extraction into `indexer.py`'s existing file loop.
- [x] Persist `project-graph.json` and `framework-graph.json` on rebuild.
- [x] Add graph schema/version metadata and rebuild invalidation behavior.
- [x] Add tests for extraction, cache invalidation, deletion cleanup, graph schema versioning, and graph file persistence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| graph extraction | implementer | — | Build deterministic nodes/edges during the existing index walk |
| graph persistence | implementer | graph extraction | Write per-layer graph files and maintain incremental cache consistency |
| tests | qa-reviewer | all implementation | Verify graph extraction, invalidation, deletion, and graph file persistence |

## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` should describe the new graph sidecar in the rebuild pipeline. If the graph schema proves durable, `docs/architecture/search-architecture.md` may later document graph-assisted retrieval semantics.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevents a second filesystem pass and keeps rebuild cost bounded |
| AC-2 | required | Graph state must stay aligned with the index layers |
| AC-3 | required | Future query waves need a stable provenance contract |
| AC-4 | required | Prevents collisions across files and layers |
| AC-5 | required | Keeps the graph correct under normal repo churn |
| AC-6 | required | Prevents regressions in the extraction and persistence pipeline |
| AC-7 | required | Graph schema/versioning must be covered by tests so incompatible artifacts do not linger |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-27 | Drafted from the Graphify review and the Wavefoundry indexer shape. | `graphify/__main__.py`, `graphify/detect.py`, `graphify/extract.py`, `graphify/build.py`, `graphify/cluster.py`, `graphify/analyze.py`, `graphify/callflow_html.py`, `graphify/serve.py`, `graphify/watch.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-27 | Keep graph extraction inside the existing rebuild loop rather than adding a second scan. | `indexer.py` already owns the file walk and rebuild lifecycle, so a second pass would duplicate I/O and complicate invalidation. | Add a separate graph discovery stage like Graphify's `detect.py` — rejected for phase 1 |
| 2026-05-27 | Keep the baseline deterministic. | Graphify's multimodal pipeline is useful, but Wavefoundry phase 1 only needs code/doc structure, not semantic inference. | Introduce LLM-derived graph edges in the first wave — deferred |
| 2026-05-27 | Make the persisted graph schema/versioned and directional. | The graph will carry directional structural relations and must force a clean rebuild when extraction semantics change, mirroring the semantic index's versioned rebuild contract. | Keep an undirected graph or omit schema versioning — rejected because it obscures relation meaning and makes cache drift harder to detect |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A graph cache can drift from the semantic index if invalidation is incomplete | Store per-file graph data and a reverse dependency index so deletions and symbol moves can propagate cleanly |
| Graph extraction could slow rebuilds if it parses files twice | Reuse the existing rebuild loop and benchmark the cost; keep the first wave deterministic and simple |
| A graph schema change could leave stale graph files on disk | Record schema/builder versions in the graph artifact and force a full rebuild on mismatch |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
