# Session Handoff

Owner: wave-coordinator
Status: active
Last verified: 2026-05-29

## Active Wave

**Wave:** `12xr2 graph-query-surface`  
**Status:** active — pre-implementation review **passed** 2026-05-29; ready for **Implement wave** (first code edit)  
**Changes (all planned):**
- `12z48-bug stale-index-build-lock-cleanup` — stale `index-build.lock` cleanup after dead PIDs
- `12z4a-bug test-file-detection-case-conventions` — fixed-community classifiers + multi-language test detection
- `12xs4-feat graph-query-surface` — `graph_query.py`, `code_impact` symbol mode, `code_callgraph`, `wave_graph_report`, `graph=true` augmentation
- `12ynp-enh graph-dependency-injection-wiring` — DI wiring extraction from graph
- `12yro-enh graph-visualization-navigation-overhaul` — dashboard graph navigation overhaul

**Implementation order:** `12z48` → `12z4a` → `12xs4` → `12ynp` → `12yro`

**Next:** **Implement wave** — open `framework_edit_allowed` gate before framework script edits; follow serialization order above.

## Last Closed Wave

**Wave:** `12xr1 graph-index-extraction` — shipped 2026-05-29 (commit `60cc21a`, Wavefoundry 1.1.0+2z2x)

## Open Questions / Deferred Decisions

- Uncommitted local work: `graph_cluster.py` Documentation fixed community (`CLUSTER_BUILDER_VERSION=7`) — not admitted to 12xr2; may belong in a follow-on change.
- Stale `index-build.lock` from post-edit hook overlap — manual cleanup may still be needed until `12z48` lands.

## Current Session

**Stage-gate waiver (operator-approved, 2026-05-29):** Indexer centralization (`indexer.py` self-reads `docs/workflow-config.json`) — committed in `60cc21a`, outside current wave.
