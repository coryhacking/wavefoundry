# Empty-Section Diagnostic Fields — Distinguish "No Data" from "No Hits"

Change ID: `1316t-enh empty-section-diagnostic-fields`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Aceiss round-trip report on `1.2.1+315o` (2026-06-01): `wave_graph_report.file_hubs` consistently returns `[]` on their codebase. They couldn't tell if it was a real "no file-level fan_out >= 20" result or the section not populating. Empty-list ambiguity is a recurring shape problem on report sections that can legitimately be empty.

The same ambiguity affects:
- `chokepoints` (no functions above the threshold)
- `file_hubs` (no modules above the threshold)
- `orphan_docs` (no doc nodes without `doc_references_code` edges)
- `cross_layer` (no edges crossing layers — empty on project-only queries)
- `betweenness` (already has `betweenness_computed` + `betweenness_skipped_reason` from `130tw`)

`betweenness` got the right shape in wave 130rj. The other sections should match.

## Requirements

1. **Each report section that can legitimately be empty carries a `<section>_candidates_total: int` field** indicating the total candidates considered before filtering. Zero means "no data" (no candidates met the section's structural criteria — e.g., no module nodes have fan_out at all); positive means "candidates existed but none met the threshold" or all were filtered.
2. **Sections covered: `chokepoints`, `file_hubs`, `orphan_docs`, `cross_layer`.** Betweenness already has the diagnostic.
3. **The `<section>_threshold` value (when applicable) is echoed** so operators can read the threshold inline. Chokepoints and file_hubs have an implicit `chokepoint_threshold = 20`. Orphan_docs and cross_layer don't have a threshold; their candidate count tells the story alone.
4. **Tests** cover (a) empty section with zero candidates (e.g., orphan_docs on a graph with no doc nodes); (b) empty section with positive candidates below threshold (e.g., file_hubs with module fan_out 5–19, threshold 20); (c) non-empty section preserves the diagnostic fields.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` and/or `graph_query.py` — diagnostic field emission for the four sections.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — 4 regression tests.

**Out of scope:**

- Adding the diagnostic to per-symbol tools (`code_callhierarchy`, `code_impact`). Those return empty lists meaningfully (no callers, no transitive callees); the empty shape there is already operator-actionable.
- Adding a global `wave_graph_report_diagnostics` object summarizing all empty sections. Per-section fields are clearer for spot reading.
- Surfacing the diagnostic on `wave_graph_report.communities` (always non-empty when the cluster artifact is present; absence handled by existing cluster-not-ready diagnostic).

## Acceptance Criteria

- [x] AC-1: `chokepoints_candidates_total: int` present whenever `chokepoints` is in the response.
- [x] AC-2: `file_hubs_candidates_total: int` present whenever `file_hubs` is in the response.
- [x] AC-3: `orphan_docs_candidates_total: int` present whenever `orphan_docs` is in the response.
- [x] AC-4: `cross_layer_candidates_total: int` present whenever `cross_layer` is in the response.
- [x] AC-5: `chokepoint_threshold` and `file_hubs_threshold` echo the threshold value (default 20).
- [x] AC-6: Zero candidates means no nodes met the section's structural criteria; positive means candidates existed but didn't meet the threshold or were filtered.
- [x] AC-7: 4 regression tests cover the shape; all existing tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Emit diagnostic fields on the four sections
- [x] Add 4 regression tests
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Most-requested in operator field reports |
| AC-2 | required | The Aceiss-reported case |
| AC-3 | required | Parity across legitimately-empty sections |
| AC-4 | required | Parity (cross_layer often empty on project-only queries) |
| AC-5 | required | Threshold echo for inline interpretation |
| AC-6 | required | Semantic clarity: "no data" vs "below threshold" |
| AC-7 | required | Regression coverage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Per-section diagnostic fields (not a global diagnostics object) | Operators reading the response spot-check the relevant section; per-section fields colocate the diagnostic with the data | Global `wave_graph_report_diagnostics` (rejected — adds indirection; operators have to know where to look) |
| 2026-06-01 | `_candidates_total` instead of `_is_empty_because` enum | Numeric count is more informative — operator sees "0 candidates" vs "47 candidates but threshold 20 dropped them all" without an enum's interpretation step | Enum like `"no_data" / "below_threshold" / "filtered_out"` (rejected — pre-decides the operator's interpretation; the count carries more info) |
| 2026-06-01 | Don't extend to per-symbol tools | Per-symbol tools' empty results are operator-actionable signals (no callers → either real or graph extraction missed something). Report sections' empty results are ambiguous in a way per-symbol empties aren't | Apply diagnostic to per-symbol tools (deferred — different semantic problem) |

## Risks

| Risk | Mitigation |
|---|---|
| Adding fields to response shape could break strict consumers | Fields are additive; no removal or rename |
| Operators interpret the count as "this should be non-empty"; could create false alarms | Field is descriptive, not prescriptive. Documentation clarifies the diagnostic interpretation |

## Related Work

- Direct response to Aceiss field feedback on `1.2.1+315o` (Finding 4).
- Mirrors `betweenness_computed` + `betweenness_skipped_reason` from `130tw-enh betweenness-computed-field` for the legitimately-empty case.
- Same wave: companion to `1316j` / `1316l` / `1316n` / `1316p` / `1316r`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
