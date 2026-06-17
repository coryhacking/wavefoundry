# Codebase map: area name ↔ Responsibility consistency

Change ID: `1p60q-bug map-name-responsibility-consistency`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-16
Last verified: 2026-06-16
Wave: `1p5x8 large-codebase-map`

## Rationale

Downstream field re-test (teton, TS/Nx monorepo, framework `1.7.0+p60n`) traced each residual codebase-map defect to its layer. All but one are graph/index-layer (chunker symbol-kind extraction, clustering granularity/stability, edge-driven contamination) — **out of scope here** (a separate graph-extractor wave with a `GRAPH_BUILDER_VERSION` bump + extraction-faithfulness review).

The **lone generator-owned** defect is a regression this wave introduced: in `gen_codebase_map.py`, the tiered-label work made the area **name** directory-first (`_finalize`, ~`:662-663`), but **Responsibility** still falls back to the graph-derived `cluster_label` — an arbitrary high-fan-in symbol (`:765`, `responsibility = cluster_label or name`). The result: in 14 of 24 areas the header name (`packages`, `lambdas`) and the stated Responsibility (`logger`, `BackendApi`) **disagree**, reading as broken/inconsistent. This is purely the generator pairing a directory-derived name with an unrelated symbol-derived responsibility.

## Requirements

1. Area `name` and `Responsibility` must never present two contradicting derivations. When there is no authoritative Tier-2 (`AGENTS.md`) responsibility, the Responsibility must be derived consistently with the name (same basis), never an unrelated graph `cluster_label` symbol.
2. Preserve the Tier-2 path: when the area's `representative_path/AGENTS.md` supplies a first content line, it remains the authoritative Responsibility (richest signal; unchanged).
3. Preserve the existing-good case: when the name itself is derived from `cluster_label`/dominant-token/central-symbol (no usable directory segment), Responsibility may continue to use that same basis (already consistent with the name).
4. Deterministic: the Responsibility derivation must be a pure function of the area's persisted inputs (no new nondeterminism); name *stability* across rebuilds remains a graph-layer concern (clustering) and is explicitly out of scope.
5. Generic + framework-script change (applies to every project's map); no project-specific content.

## Scope

**Problem statement:** Generator pairs a directory-derived area name with a symbol-derived Responsibility, so the two disagree in ~14/24 areas.

**In scope:**

- `gen_codebase_map.py` `_finalize`: make the no-`AGENTS.md` Responsibility consistent with the chosen name (track whether the name came from the directory segment; when it did, do not echo an unrelated `cluster_label`).
- A regression test asserting name/Responsibility consistency for a directory-named area with a competing `cluster_label`.
- Regenerate `docs/references/codebase-map.md`.

**Out of scope:**

- All graph/index-layer defects (TS type-field-as-`function`, garbage `function (function)` / route-segment symbols, cross-area contamination, typings fragmentation, name instability across rebuilds) — Bucket B, separate graph-extractor wave.
- Render-shape changes (omitting the Responsibility line, etc.).

## Acceptance Criteria

- [x] AC-1: In `gen_codebase_map.py` `_finalize`, when the area name is derived from the representative directory segment and no `AGENTS.md` first line exists, `responsibility` is consistent with `name` (not an unrelated `cluster_label` symbol). The Tier-2 `AGENTS.md` path and the name-from-`cluster_label` path are unchanged.
- [x] AC-2: A regression test constructs an area whose directory segment and dominant `cluster_label` differ and asserts the rendered name and Responsibility do not present two contradicting derivations; full suite green.

## Tasks

- [x] Track the name-derivation source in `_finalize` (directory segment vs cluster_label/token/central).
- [x] Make the no-`AGENTS.md` `responsibility` consistent with the name when the name is directory-derived.
- [x] Add the regression test (directory name vs competing cluster label).
- [x] Regenerate `docs/references/codebase-map.md`; docs-lint clean; run full suite.

## Affected Architecture Docs

N/A — confined to the codebase-map generator's label derivation; no boundary, flow, or verification-architecture impact.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The named generator-owned regression; the fix itself. |
| AC-2 | required | Locks the consistency invariant against future label-derivation changes. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | teton p60n re-test: layer-traced residual defects; lone generator-owned bug = name↔Responsibility mismatch (14/24 areas). | `gen_codebase_map.py:662-663,765` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Fix only the generator-owned mismatch in this wave; defer all graph/index-layer defects to a separate graph-extractor wave. | Graph-layer fixes need a `GRAPH_BUILDER_VERSION` bump, the multilang pack, and a faithfulness review, and can't be validated without downstream TS fixtures. | Fold everything in now (rejected — scope + version-bump risk). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Making Responsibility equal the name in the no-context case reads as redundant. | Acceptable + honest vs the contradictory state; the richer signal remains the Tier-2 `AGENTS.md` path, which is preserved. Render-shape changes are out of scope. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
