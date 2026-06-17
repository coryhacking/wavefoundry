# TS symbol-kind extraction faithfulness (no type-fields-as-function, no garbage symbols)

Change ID: `1p61v-bug ts-symbol-kind-extraction-faithfulness`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p61u graph-layer-map-quality`

## Rationale

teton field re-test (TS/Nx monorepo, framework `1.7.0+p60n`) traced codebase-map entry-point noise to the graph/index layer, not the map generator. Two extraction defects:

1. **TS type/interface members are tagged `kind="function"`.** A pure type-declaration file (`report.types.ts`) returns zero symbols from `code_outline`, yet the graph surfaces its `: string` fields (`run_key`, `updated_at`, `appKey`, `Application`, `ApplicationSource`) as `(function)` nodes. The map's `_kind_tag` is faithful — it renders the kind the graph reports — so the fix must be in extraction: interface `property_signature` / type-alias members / object-type properties are not functions.
2. **Garbage symbols are extracted at all.** The literal keyword `function` becomes a node (`function (function)`), and route segments (`/`) surface as symbols. These are parser artifacts that should never become graph nodes.

teton's assessment: this is the **highest-leverage** fix — correcting symbol-kind extraction cleans the entry-point lists across most areas. It is well-bounded (TS/JS extraction only) and independently shippable.

## Requirements

1. TS/JS interface `property_signature`, type-alias members, and object-type property members must NOT be emitted with `kind="function"`. Emit the accurate kind (field/property/type-member as the extractor's taxonomy allows) or, if no accurate kind is determinable, a kind that is NOT `function` (so the map's `_kind_tag` omits or correctly labels it). A method signature (callable member) remains a method/function.
2. Language keywords (`function`, `const`, route-path literals like `/`, etc.) must never be extracted as symbol nodes.
3. Faithfulness-first: the fix must not silently drop or mislabel legitimate callables (arrow-const functions, method signatures, class methods). No over-correction that zeroes real function nodes.
4. Bump `GRAPH_BUILDER_VERSION` in the same change (node/kind-shape change → consumer graph caches must re-extract). Per framework policy, any extractor change altering node/edge shape bumps the builder version.
5. Generic across all projects; TS/JS scope only (other languages out of scope for this change).

## Scope

**Problem statement:** The TS/JS extractor tags non-callable type members as `function` and emits keyword/route-segment garbage as symbol nodes, polluting graph entry-point lists and the codebase map.

**In scope:**

- `chunker.py` / `graph_indexer.py` TS/JS symbol extraction: interface/type-member kind correctness; keyword/route-segment node suppression.
- `GRAPH_BUILDER_VERSION` bump with a descriptive line.
- Synthetic TS fixtures (pure-type file → zero function nodes; interface with mixed fields + a method → only the method is callable; a file with route literals / keyword tokens → no garbage nodes).
- Validation against the multilang test pack + the downstream TS consumer (teton) as the real-world oracle.

**Out of scope:**

- Clustering granularity, contamination, and name stability (sibling change `1p61w`).
- Non-TS/JS languages.
- The map generator (already faithful; nothing to change there).

## Acceptance Criteria

- [x] AC-1: A pure TS type-declaration fixture (interface + type-alias, no functions) produces ZERO `kind="function"` graph nodes; its members are either accurately kinded or carry a non-`function` kind so `_kind_tag` does not render `(function)`.
- [x] AC-2: An interface mixing data fields and a method signature emits the method as a callable kind and the data fields as non-callable; a real arrow-const/function-declaration fixture still emits its functions (no over-correction / faithfulness regression).
- [x] AC-3: Language keywords (`function`, `const`, …) and route-path literals (`/`) are not emitted as symbol nodes (no `function (function)` / `/ (function)` garbage).
- [x] AC-4: `GRAPH_BUILDER_VERSION` is bumped in this change with a descriptive line; the multilang test pack passes; full suite green.

## Tasks

- [x] Locate the TS/JS member-extraction path in `chunker.py` / `graph_indexer.py` that assigns `function` to interface/type members; correct the kind mapping.
- [x] Suppress keyword/route-segment tokens from becoming symbol nodes.
- [x] Add synthetic TS fixtures + assertions (pure-type → no function nodes; mixed interface; arrow-const faithfulness; keyword/route garbage).
- [x] Bump `GRAPH_BUILDER_VERSION` with a descriptive line.
- [x] Adversarial extraction-faithfulness review (no real callables dropped; no wrong-kind binding) before close.
- [x] Validate against the multilang test pack + teton; regenerate a map and confirm `(function)` no longer appears on type fields.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — note the TS member-kind handling if it documents extractor kind taxonomy; otherwise `N/A` (extraction-internal correctness, no boundary/flow change).

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core defect: type fields shown as functions. |
| AC-2 | required | Faithfulness guard — must not drop/mislabel real callables. |
| AC-3 | required | Removes the garbage-symbol artifacts. |
| AC-4 | required | Version bump is mandatory for node-shape changes; pack must stay green. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | teton p60n re-test: type fields tagged `(function)`; `code_outline` on a pure-type file returns zero symbols while the graph surfaces its fields. Highest-leverage graph-layer fix. | field-feedback memory; `gen_codebase_map.py` `_kind_tag` (faithful) |
| 2026-06-17 | Pinned site via live repro: `_ts_kind_for_definition` (`graph_indexer.py:1825`) defaulted `property_signature` + `type_alias_declaration` to `function`; `_ts_pick_symbol_name` fallback returned the literal `function`/`/` token (`_STOP_TERMS` had no keywords). Fixed both; bumped `GRAPH_BUILDER_VERSION` 30→31. | `graph_indexer.py:28,1825-1838,4978-5010,6392`; `test_graph_indexer.py` (3 new tests) |
| 2026-06-17 | Adversarial faithfulness review caught an over-reach: the name guard's plain-identifier rule would drop legitimate non-identifier symbol names in other languages (C++ `operator==`, Rust operators, Ruby `valid?`/`save!`/`<=>`). Scoped the guard to TS/JS (where the `function`/`/` artifact originates). No real callable dropped. | `graph_indexer.py:6392` lang gate; full suite 3254 OK |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Scope TS/JS only; separate from clustering work. | Different subsystem, different oracle, high-confidence vs the fuzzy clustering tuning. | One combined graph change (rejected — couples a clean fix to a research task). |
| 2026-06-17 | Issue 2 fixed via a construct-agnostic registration-site guard (reject `function`/non-identifier names) rather than pinning the exact anonymous-function grammar path. | The junk `function (function)` node could not be reproduced locally with simple constructs (minified/vendored-specific); a name guard catches it regardless of which path produces it, with zero false-positive risk once gated to TS/JS. | Pin the exact grammar construct (rejected — brittle, and the guard is strictly safer). |
| 2026-06-17 | `public_field_definition` (TS/JS class DATA fields) left at default `function`; only `property_signature` + `type_alias_declaration` re-kinded. | A class field can bind an arrow/function value (`handler = () => {}`) — a real callable. The string-only kind mapper can't distinguish that, so a blanket re-kind would risk dropping a callable; teton's report is specifically `property_signature` + `export type`. Deferred as a minor known gap. | Re-kind at the call site with value inspection (deferred — added surface area beyond the reported defect). |
| 2026-06-17 | Issue 3 (vendored/minified JS + pure-data JSON becoming code nodes / area hubs) routed to sibling `1p61w`. | It is hub/representative selection + community-formation inputs (clustering layer), not symbol-kind extraction. | Handle here (rejected — wrong layer/version constant). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-correction zeroes legitimate callables (arrow-const, method signatures). | Faithfulness AC-2 + adversarial review with a real-callable fixture; validate resolved-share doesn't regress on teton. |
| Can't fully validate without downstream TS fixtures. | teton is the named real-world oracle; multilang pack carries synthetic coverage. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
