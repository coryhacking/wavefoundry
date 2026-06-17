# Codebase map: vendored / third-party axis (javaagent 1b)

Change ID: `1p64t-enh map-vendored-axis`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p61u graph-layer-map-quality`

## Rationale

`1p61w`'s generated-code exclusion (1a) shipped and works, but the javaagent p64p re-eval showed it barely moved signal/noise: the dominant noise is **hand-vendored, not generated** (an Apache/Jakarta EL implementation — ~51% of files, 11 of 22 areas). `generated_node_fraction` is 0 for vendored-but-not-generated code, so there is no signal to exclude it. teton corroborates: vendored `prism.js` / `otel.cjs` still land in a `libs/utils` area. The graph has a generated axis but no **vendored** axis.

The fix is an explicit vendored signal the map consumes to drop vendored-dominated communities from the primary tier (mirroring the generated treatment) and surface them in a collapsed appendix — keeping them indexed/searchable via `code_*` while removing them from orientation.

## Requirements

1. **Two explicit vendored signals (operator-selected), no name heuristics:** (a) a `vendored_paths` glob array in `docs/repo-profile.json` (e.g. `["**/instrumentation/el/**", "**/*.cjs"]`); (b) `.gitattributes` `linguist-vendored=true` patterns (the ecosystem-standard marker, pairing with the existing `linguist-generated` handling). A node is vendored when its `source_file` matches either.
2. **Exclude vendored-dominated communities from the primary area tier** when their vendored-node fraction exceeds the threshold (0.4, same as generated), and **surface a collapsed "Vendored / third-party" footer** with the omitted count + sample (never a silent drop; still `code_*`-searchable).
3. **Faithfulness — explicit signals only.** A first-party file that merely *looks* library-ish (e.g. a `bootstrap/.../JSON.java` carrying a product copyright) is NEVER excluded unless its path matches a configured glob or it is marked `linguist-vendored`. No name/heuristic exclusion.
4. **Generator-only, generic, fail-safe.** Implemented in `gen_codebase_map.py` (mirrors the generated-axis path); no `GRAPH_BUILDER_VERSION` / `CLUSTER_BUILDER_VERSION` bump. Missing/empty `repo-profile.json` and absent `.gitattributes` are a safe no-op (zero vendored nodes).

## Scope

**In scope (`gen_codebase_map.py`):**

- Read `docs/repo-profile.json` `vendored_paths` globs + `.gitattributes` `linguist-vendored` patterns (reuse the gitattributes pattern shape `graph_indexer` already parses for `linguist-generated`).
- A `_vendored_fraction(node_ids)` mirroring `_generated_fraction`; exclude communities over the threshold from the area tier; collapsed "Vendored / third-party" footer (count + sample) alongside the generated-omitted footer.
- Fixtures: a vendored-dominated community (via glob and via `linguist-vendored`) excluded; a same-size first-party community kept; a product file not matching any signal never excluded.

**Out of scope:**

- A graph-layer `vendored` node tag / `vendored_node_fraction` in the cluster artifact (would let `wave_graph_report` exclude vendored too, but forces a graph+cluster re-extract across all consumers for a map-orientation concern — deferred; can be promoted later if other consumers need it).
- Minified-by-heuristic detection (no explicit marker) — covered only when the repo lists the path/marker (faithfulness over heuristics).

## Acceptance Criteria

- [x] AC-1: A community whose nodes match `repo-profile.json` `vendored_paths` above the threshold is excluded from the primary area tier; a same-size first-party community at the same size is still selected. A `.gitattributes linguist-vendored` match excludes equivalently.
- [x] AC-2: The omitted vendored communities are surfaced in a collapsed "Vendored / third-party" footer (count + sample), never silently dropped; they remain present in the graph (searchable).
- [x] AC-3: Anti-over-exclusion — a first-party file whose name looks library-ish but matches no configured glob / marker is never excluded. Missing `repo-profile.json` / `.gitattributes` is a safe no-op. Generator-only (no version bumps); regenerated map + full suite + docs-lint clean.

## Tasks

- [x] Read `repo-profile.json` `vendored_paths` globs + `.gitattributes linguist-vendored` patterns (fail-safe); match node `source_file`s.
- [x] `_vendored_fraction` + exclude vendored-dominated communities from the area tier (mirror generated); collapsed "Vendored / third-party" footer.
- [x] Fixtures (glob, linguist-vendored, anti-over-exclusion, missing-config no-op).
- [x] Regenerate map; full suite + docs-lint.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — note `repo-profile.json` `vendored_paths` as a map area-selection signal if it documents the map contract; otherwise `N/A`.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The fix for the dominant javaagent defect — exclude vendored-dominated areas. |
| AC-2 | required | Honest omission, not a silent drop; vendored code stays searchable. |
| AC-3 | required | Faithfulness — never exclude first-party product; safe with no config. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | javaagent p64p re-eval: 1a (generated) shipped but vendored EL (hand-vendored, `generated_node_fraction`=0) still dominates (11/22 areas). teton: `prism.js`/`otel.cjs` still in a code area. Operator: pull the vendored axis in now; signals = `repo-profile.json vendored_paths` + `.gitattributes linguist-vendored`. | field-feedback memory |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Generator-only vendored axis (read signals at map time), not a graph-layer `vendored` tag. | Vendored exclusion is a map-orientation concern; a graph/cluster tag would force a re-extract across all consumers. Promote to graph layer later only if other consumers need `exclude_vendored`. | Graph-layer `vendored` tag + `vendored_node_fraction` (deferred — heavier, 2 version bumps). |
| 2026-06-17 | Explicit path/marker signals only; no minified-by-name heuristic. | Faithfulness — a product file must never be excluded by a name lookalike (e.g. `JSON.java` with a product copyright). | Heuristic minified detection (rejected — lookalike risk). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A repo with no `repo-profile.json` / `.gitattributes` gets no benefit. | Safe no-op; the generated axis + per-module floor still apply. Vendored exclusion is opt-in by design (explicit signal). |
| Over-exclusion of product code. | Explicit glob/marker only; AC-3 anti-over-exclusion fixture; collapsed footer keeps omissions visible. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
