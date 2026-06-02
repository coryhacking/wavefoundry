# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-06-02

wave-id: `1p2q3 field-feedback-round-4`
Title: Field Feedback Round 4 — `code_graph_path` Result Quality

## Objective

Address the single field-validation finding surfaced after wave 131bt closed at 1.3.4+p2q0: `code_graph_path` reports `found: true` with plausible-but-spurious 2-hop paths that route through shared `external::*` nodes (caught exception variables, generic identifiers, stdlib symbols). The "path" doesn't represent any meaningful coupling between the endpoints; BFS bridges them through a low-information shared node and returns the shorter junk path even when a longer real call chain exists.

Reproducer from Aceiss (1.3.4+p2py on the Java agent project):

- `code_graph_path(from="ServletHelper.setSpanAttributesAtEndOfRequest", to="JSON.writeObject", direction="either")` returns a 2-hop path through `external::e` (a caught exception variable), every edge `relation: imports`, `confidence: EXTRACTED`
- `code_impact(symbol="writeObject")` in the same session confirms the real 3-hop call chain (`setSpan → AuthorizationContext.getDetailsAsJson → JSON.toJson → JSON.writeObject`) with all `RECEIVER_RESOLVED` edges
- The shortest-path objective actively prefers the 2-hop junk path over the 3-hop real one

Two distinct concerns in the report:

1. **Structural** — `external::*` nodes are graph shortcuts they shouldn't be. Routing BFS through an unresolved identifier connects unrelated symbols. Highest-leverage single fix.
2. **Operator-facing** — `found: true` is the headline an agent reads first. The disqualifying detail (`relation: imports`, `confidence: EXTRACTED`, `kind: null` bridge node with `source_file: null`) is one level down in `path_edges`. The data model is sound; the default traversal policy and the headline signal need tightening.

This wave admits one bundled change covering four interrelated fixes the field validator proposed in priority order: (1) non-transitive externals in BFS, (2) `relations=["calls"]` default, (3) structural-path diagnostic, (4) `min_confidence` parameter. All four touch the same tool and ship together for narrative coherence.

## Changes

Change ID: `1p2q4-bug code-graph-path-external-bridge-and-result-quality`
Change Status: `planned`

## Wave Summary

(Populated on close.)

## Journal Watchpoints

- **Defaults change is a contract shift.** Item #2 (default `relations=["calls"]`) silently removes paths via `imports`/`defines` from existing callers who used the no-arg form. Backwards-compat path is `relations=None` → explicit full traversal opt-in; document the migration in the change's risk row and in seed-211's `code_graph_path` subsection.
- **Test against the actual failing case.** The Aceiss reproducer (`setSpan → external::e → writeObject`) is the regression-test fixture. Synthesize a project graph with that shape and assert: (a) the spurious 2-hop path is no longer returned; (b) the real 3-hop calls path IS returned when present; (c) `found: false` + suggestions when the endpoints aren't actually connected.
- **External-as-endpoint must still work.** Callers querying `code_graph_path(from="external::FooLib.bar", direction="backward")` ask a legitimate question ("what reaches this external symbol?"). The non-transitive rule applies to intermediate externals only — `current ∉ {from_id, to_id}` is the gate.
- **`fan_in` stdlib noise (companion finding).** The same field report flagged `fan_in` being dominated by `external::String` / `external::contains` / `external::map` / `external::warning` / `external::Date` — not useful "most-called project symbols." Same root cause as #1 (unresolved-identifier nodes graph-shortcutting), but the fix lives in `wave_graph_report.fan_in` filtering, not `code_graph_path`. Tracking as a separate future plan rather than bundling — fan_in's behavior is observably distinct (filterable via existing `exclude_external` parameter) where the graph_path case has no operator-facing workaround.
- **Orphan-docs noise (companion finding).** The report also flagged `{label: "clean", kind: "doc"}` and `{label: "debug", kind: "doc"}` as orphan-docs entries — command-snippet fragments mis-ingested as doc nodes. Doc-extractor data-quality bug, separate from graph_path. File as follow-on plan.

## Review Evidence

(Populated by wave-council-readiness when ready.)

## Prepare Review Evidence

(Populated by per-lane reviewers during prepare.)

## Review Checkpoints

| Checkpoint | When | Outcome |
|---|---|---|
| wave-council-readiness | Before implementation | Pending |
| wave-council-delivery | Before close | Pending |

## Dependencies

- No upstream wave dependencies. Builds on `graph_query.shortest_path` which last shipped in wave 131bt (`131bu`'s confidence tie-break). The tie-break logic introduced in 131bu remains correct and is preserved by this change — the new non-transitive-external check sits before the tie-break in the candidate-expansion path.
- No downstream wave consumers blocked by this change.
- Companion findings deferred to future plans (per Journal Watchpoints): `fan_in` stdlib noise; orphan-docs command-snippet fragments; `_existing_prefixes` regex false-positive on `close-*` filenames (carried over from wave 131bt close-out).
