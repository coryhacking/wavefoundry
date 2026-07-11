# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-11

wave-id: `1sbfi external-supertype-visibility`
Title: External Supertype Visibility

## Objective

Close the field-reported graph blind spot where a class implementing or extending an EXTERNAL supertype is invisible end-to-end: `1sbfh` gives `implements`/`extends` the same external-target treatment `calls` already has (surfaced entries under an include-external gate, always-on suppressed-count signals) plus external-supertype name resolution with the implementor-list blast-radius view. When this wave closes, "what implements this external interface?" is answerable, a class with only-external supertypes no longer reads as "no edges", and the fix ships in 1.12 alongside wave 1rsh9. Operator-directed as pre-1.12 work (2026-07-11).

## Changes

Change ID: `1sbfh-enh external-supertype-visibility-implements-extends`
Change Status: `implemented`

Completed At: 2026-07-11

## Wave Summary

Wave `1sbfi` (External Supertype Visibility) delivered one change: External-Supertype Visibility for `implements`/`extends` (calls-Parity External Handling). Notable adjustments during implementation: External-Supertype Visibility for `implements`/`extends` (calls-Parity External Handling): **Census complete (Req 1 / AC-1) — fixture: 2 Java implementors of an external interface + 1 external extends + a project-internal control.** Boundary evidence: (1) **payload** — external inheritance edges PRESENT (`implements → external::TypeInstrumentation` ×2 EXTRACTED, `extends → external::InstrumentationModule`; project-internal control RECEIVER_RESOLVED), zero `external::` NODES (dangling targets by design); note: an unqualified declaration stays a SIMPLE-name external id even when an import could qualify it — the distinct-id grouping amendment therefore applies to declared-qualified forms, while unqualified same-name externals genuinely share an id at extraction (faithful to "as declared"; qualification-via-import-facts is extraction modeling, out of scope). (2) **graph_query adjacency** — raw `traverse()` follows external inheritance edges BOTH directions, including reverse-BFS FROM `external::TypeInstrumentation` (finds both implementors) — the machinery works; but `resolve_symbol("TypeInstrumentation")` → None (external ids absent from the symbol index), so no query can reach it. (3) **server** — `code_impact(implementor)` correctly shows empty incoming blast radius (impact = dependents; the interface is not a dependent), but NO supertype/external signal is surfaced anywhere, and `code_impact(TypeInstrumentation)` dies at resolution. **Fix layers named:** graph_query `resolve_symbol` external-supertype fallback (project-shadowed, distinct-id grouping) + server-layer external-seed labeling and implementor-side supertype surfacing/counts. **No payload change → no `GRAPH_BUILDER_VERSION` bump; field graphs light up without re-extraction.**.

**Changes delivered:**

- **External-Supertype Visibility for `implements`/`extends` (calls-Parity External Handling)** (`1sbfh-enh external-supertype-visibility-implements-extends`) — 8 ACs completed. Key decisions: Surface existing extraction facts (calls-parity visibility + external-name resolution); no new extraction modeling.; `GRAPH_BUILDER_VERSION` NOT bumped.
## Journal Watchpoints

- Watchpoint (census gate): the Req-1 census BLOCKS implementation — the drop layer is identified on fixture evidence before any fix code is written; the census findings must be recorded in the change doc first.
- Watchpoint (extraction faithfulness): no new resolution guessing, no new edge minting — if edges are dropped at payload emission, the fix is to stop dropping them, never to invent facts. Supertype name fidelity ("qualified exactly as declared") is pinned by test.
- Watchpoint (builder-version discipline): `GRAPH_BUILDER_VERSION` bumps IF AND ONLY IF the emitted payload shape changes; the decision + rationale land in the change doc's Decision Log. An unbumped fix must demonstrate visibility against this repo's EXISTING graph (no re-extract).
- Watchpoint (shadowing rule): external simple-name resolution must never shadow a project symbol — ties resolve to the project node, externals are always labeled external.
- Watchpoint (report cleanliness): `wave_graph_report` main sections stay free of external rows; any report-level signal is a count only.

## Participants

- code-reviewer — query/server-layer changes in `server_impl.py` / `graph_query.py` (+ `graph_indexer.py` only if the census proves a payload-emission drop)
- qa-reviewer — census evidence per boundary; fixture matrix (multi-implementor, dotted-qualified declaration, project/external name collision, distinct-external-id simple-name collision)
- architecture-reviewer — calls-parity convention, shadowing rule, report-surface cleanliness

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-11: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, architecture-reviewer, performance-reviewer; rotating-seat: performance-reviewer; strongest-challenge: the change's premise — "edges are already emitted, the gap is downstream" — could be wrong at the payload-emission boundary, making a query-layer-only fix land on nothing; resolved structurally by the Req-1 census GATE: implementation is blocked until a fixture traces the edge end-to-end (extractor edge map → payload → adjacency → tool response) and the drop layer is proven, with the fix landing wherever the evidence says; strongest-alternative: mint first-class external supertype nodes with inferred package coordinates for richer identity — rejected because the extractor's core discipline is "never guessed" FQN inference, and name-as-declared resolution with the distinct-id grouping amendment answers the field query without inventing facts)
- Council seat notes: reality-checker — load-bearing claims verified against source THIS session: the inheritance pass keeps unresolved supertypes as `external::` targets ("never dropped, never guessed"); the C# correction pass skips externals as inert; `implements`/`extends` are in `graph_query._DEFAULT_IMPACT_RELATIONS` (1p9qa); the external-count machinery exists only on `calls` paths (`server_impl.py:13965/14087`); the sibling field item (corp-TLS) was confirmed already shipped, so this is genuinely the one remaining pre-1.12 item. red-team — beyond the premise challenge, pressed simple-name aggregation: two DIFFERENT external interfaces sharing a simple name must not merge into one phantom blast radius; amendment applied to Req 3/AC-3 (group by exact external id, surface the breakdown). Also pressed the shadowing direction: a project class named like an external supertype must win resolution — pinned in AC-3. qa-reviewer — the census must record evidence at each boundary (not just the conclusion), and the fixture matrix must include multi-implementor, dotted-qualified declarations, the project/external collision, and the distinct-external-id collision; accepted as the tests-docs workstream contract. architecture-reviewer — calls-parity (include-external gate + always-on suppressed counts) is the established UX and the right shape; the report-surface exclusion convention is respected (counts only); the builder-version bump-iff-payload-change rule keeps field repos from needless re-extraction. performance-reviewer (rotating) — external-name resolution adds a bounded lookup over external edge targets (supertype cardinality is small, unlike calls); hierarchy/impact response bloat is bounded by the include-external gate; no hot-path cost when the gate is off. seat_agreement: unanimous; amendment applied in-session before readiness was recorded.
- AC priority: confirmed at prepare as proposed (AC-1..6, 8 required; AC-7 important). Product-owner acknowledgment: operator-directed 2026-07-11 as pre-1.12 work ("doing 3 and 4 before we ship 1.12"; item 3 verified already shipped, so this wave is the remaining scope).

- pre-implementation-review: passed (2026-07-11) — packet complete (single change, council-passed with amendment, lanes rostered); the one pre-mortem risk (fixing the wrong layer) was retired by running the Req-1 census FIRST: live-fixture evidence shows edges survive to payload and adjacency (reverse-BFS from the external id already finds implementors), so the fix is exactly `resolve_symbol` + server surfacing/counts — no payload change, no `GRAPH_BUILDER_VERSION` bump. Ordered lanes: graph_query resolution/summary helpers → server surfacing (impact + callhierarchy) → tests/seeds.

## Review Evidence

- wave-council-delivery: approved (2026-07-11 — moderator: wave-council; adversarial delivery review against code, tests, and the fixture evidence; no blocking findings. **code-reviewer** — the resolution fallback is structurally shadowed (it is the LAST tier of `resolve_symbol`, reachable only after every project tier returned None), the external-supertype index is built once in `__init__` from `implements`/`extends` targets ONLY (external call targets excluded by construction and by test), the `__slots__` addition is minimal, and both server surfaces guard the new index methods with `AttributeError` fallbacks so a stale-loaded module degrades to the old behavior rather than erroring; `graph_indexer.py` has zero edits (extraction faithfulness by construction). **qa-reviewer** — 14 tests across the two layers cover every council-mandated fixture: multi-implementor blast radius (incl. hop-2 dependents), dotted-qualified and exact-id resolution, the project/external name collision (project wins), the distinct-external-id collision (grouped, never merged, exact-id re-query proven), external-call-target exclusion, always-on counts with the include_external gate on callhierarchy, supertype-free nodes staying section-free, and the report-cleanliness regression pin; full suite 4,832 OK bytecode-free; `wave_validate` clean. **architecture-reviewer** — calls-parity holds (same include/count UX consumers know), the bump-iff-payload-change discipline was honored (no bump; the fixture graph extracted pre-fix served the full scenario post-fix with no re-extraction — exactly the field-repo upgrade path), and the seed/spec/architecture docs document the new signals without internal artifact IDs. **red-team** — pressed whether the ambiguity response could mask a genuine project-symbol miss: no — the external branch runs only after project resolution failed AND only when ≥2 distinct external ids match, and the plain not-found path with suggestions is unchanged otherwise; also pressed the `external::super.*`/marker ids leaking into the supertype index — they are `calls`/`imports`-relation targets, never `implements`/`extends`, so the relation filter excludes them by construction. Synthesis verdict: SHIP — the field scenario ("24 implementors of an external interface, invisible") is now answerable end-to-end with zero re-extraction cost.)

- wave-council-readiness: approved 2026-07-11 — prepare council synthesis verdict READY after one amendment (distinct-external-id grouping on simple-name resolution); the census-first gate structurally de-risks the one named unknown (where the edges vanish); extraction faithfulness, shadowing, report cleanliness, and builder-version discipline are pinned as watchpoints and ACs; seats unanimous; full synthesis in Review Checkpoints.
- operator-signoff: approved when operator confirms closure

## Dependencies

- No external wave dependencies. Ships in the 1.12 release together with the already-closed wave `1rsh9`.
