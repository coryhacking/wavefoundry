# External-Supertype Visibility for `implements`/`extends` (calls-Parity External Handling)

Change ID: `1sbfh-enh external-supertype-visibility-implements-extends`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-11
Wave: TBD

## Rationale

Field-reported 2026-07-06 (Java OpenTelemetry instrumentation codebase, post-1.11.0; standing log `docs/references/wavefoundry-graph-tools-feedback.md`): a class that `implements` an **external** interface is invisible to the graph tools. `code_impact` on `TypeInstrumentation` (an OTel interface implemented by 24 classes in that repo) resolves no node; querying from the implementor side shows **zero** `implements`/`extends` edges even though the source literally declares them — and, unlike `calls`, there is no `external_*_count` suppressed-signal, so nothing tells the consumer a real relationship exists. Project-internal inheritance is clean (30/30 `RECEIVER_RESOLVED` on the same repo), so this is specifically the external-target half.

Pre-planning exploration (2026-07-11, verified against source) sharpened the mechanism: the **extractor already emits** inheritance edges to external supertypes — the inheritance pass keeps an unresolved supertype as `external::<Name>` "qualified exactly as declared — never dropped, never guessed" (`graph_indexer.py`, `_INHERITANCE_RELATIONS` block), and the C# relation-correction pass explicitly skips external targets as "inert: both relations traverse identically". `implements`/`extends` are also already in the default impact traversal (`graph_query._DEFAULT_IMPACT_RELATIONS`, wave 1p9qa). The gap is downstream of extraction:

1. **Query/server-layer asymmetry:** the external-target machinery (`external_outgoing_count`/`external_incoming_count`, `include_external` gating) exists only on the `calls`-relation paths in `server_impl.py`; external inheritance targets are neither surfaced nor counted anywhere.
2. **External-name resolution:** `external::TypeInstrumentation` is not resolvable by simple name, so the most valuable query — "what implements this external interface?" (the cross-module blast-radius view) — cannot even start.

One open unknown is named rather than guessed (Requirement 1): whether `external::` inheritance edges survive from the extractor's edge map into the **emitted graph payload** and through `graph_query`'s adjacency, or are dropped at one of those boundaries. The fix lands wherever the drop actually is; the requirements below define the observable behavior either way.

## Requirements

1. **Mechanism census first (reality-check gate):** build a minimal fixture (Java class `implements` an external interface + `extends` an external class; C# equivalent) and trace the edge end-to-end — extractor edge map → emitted payload → `graph_query` load/adjacency → `code_impact`/`code_callhierarchy` response — recording exactly where external inheritance targets currently vanish. The census result is recorded in this doc BEFORE the fix is implemented and determines which layer(s) change.
2. **Implementor-side visibility (calls parity):** `code_impact` and `code_callhierarchy` on a class with external supertypes surface them — external supertype entries appear when `include_external` (or the tool's equivalent) is set, and a suppressed-count signal (`external_implements_count`/`external_extends_count`, or the relation-labeled equivalent of the existing `external_outgoing_count` convention) is ALWAYS present when external supertypes were omitted. Zero-signal invisibility is the defect being closed.
3. **External-interface-side resolution:** querying an external supertype by simple name (e.g. `code_impact(symbol="TypeInstrumentation")`) resolves when at least one project class declares it as a supertype, and returns the implementor/subtype list (the blast-radius view: all project classes with `implements`/`extends` edges to that external target), clearly labeled external (never conflated with a project node). Resolution covers the declared-name forms the extractor preserves (simple and dotted/qualified). **Readiness-council amendment (2026-07-11):** when a simple name matches MULTIPLE distinct external ids (e.g. two packages' `Node` declared with different qualifications), the response groups by exact external id and surfaces the distinct-target breakdown — never a silently merged implementor list.
4. **No extraction-semantics change:** supertype names stay "qualified exactly as declared — never dropped, never guessed"; no new resolution guessing, no new edge minting beyond what extraction already emits. If the census (Req 1) shows the payload/adjacency drops external inheritance edges, the fix is to STOP dropping them (surfacing existing facts), not to invent new ones.
5. **`GRAPH_BUILDER_VERSION` discipline:** bump ONLY if the emitted payload shape changes (per the standing convention); a pure query/server-layer fix requires no bump and field graphs light up without re-extraction. The decision and rationale are recorded in the Decision Log.
6. **Report surfaces stay external-clean:** `wave_graph_report` keeps excluding external targets from its main sections; if a summary signal is added there, it is a count, not external node rows.
7. **Language coverage matches extraction:** the visibility applies wherever inheritance edges are extracted today (Java + C# emitters; the C# positional-relation convention for external bases is respected). No new language extraction ships in this change.
8. **Graph-tool docs/seeds:** the seeds/tool descriptions that document the `calls` external buckets gain the inheritance-relation equivalents, so consumers know the signal exists (seed-first discipline; no wavefoundry-internal IDs in shipped seeds).

## Scope

**Problem statement:** External-target `implements`/`extends` relationships are extracted but invisible end-to-end — no edges surfaced, no node resolution from the external side, and no suppressed-count signal — unlike `calls`, which has explicit external-attribution machinery.

**In scope:**

- The Req-1 census fixture + recorded findings.
- Query/server-layer external handling for inheritance relations (`code_impact`, `code_callhierarchy`; `code_graph_path`/`code_risk_score` only if the census shows they share the dropped path).
- External-supertype simple/qualified-name resolution with the implementor-list view.
- Suppressed-count signals per Req 2.
- Payload/adjacency fix if (and only where) the census shows edges are dropped.
- Tests: fixture-based end-to-end (Java + C#), counts, external-side resolution, include/exclude gating, report-surface exclusion; a re-verification mirroring the field report's shape (multiple implementors of one external interface).
- Seed/doc updates per Req 8.

**Out of scope:**

- New extraction modeling (Kotlin/other-language supertype emission, FQN inference for unimported supertypes, resolving externals to package coordinates).
- Any `calls`-path behavior change.
- The dependency-graph `imports` external handling (already has its own conventions).

## Acceptance Criteria

- [x] AC-1: The census is recorded in this doc: the exact layer(s) where external inheritance edges currently vanish, with fixture evidence at each boundary (extractor edge map, payload, adjacency, tool response). — Progress Log 2026-07-11: edges survive to the payload and adjacency; the drops are `resolve_symbol` (external ids unindexed) and the server surfacing/count layer; no payload change needed.
- [x] AC-2: On the fixture, `code_impact`/`code_callhierarchy` from the implementor side surface external supertypes under the include-external gate and ALWAYS report the suppressed-count signal when externals are omitted; a class with only-external supertypes no longer reads as "no edges". — `supertype_summary` → `supertypes` response section (impact: always included, supertype cardinality is tiny; callhierarchy: external list gated on `include_external`, counts always present); `ExternalSupertypeServerTests::test_impact_on_implementor_surfaces_supertypes` / `test_callhierarchy_supertypes_respect_include_external_gate` / `test_supertype_free_symbol_has_no_supertypes_section`; `ExternalSupertypeVisibilityTests` summary tests.
- [x] AC-3: On the fixture, querying the external supertype by name returns the implementor/subtype list, labeled external; a name that matches both a project node and an external supertype resolves to the project node (externals never shadow project symbols); a simple name matching multiple distinct external ids returns them grouped by exact id, never merged (council amendment). — `resolve_symbol` external fallback (LAST tier, structurally shadowed) + `external_supertype_matches`/`external_supertype_group`; `code_impact` external seed labeled (`external_target`/`external_name`) with implementor blast radius, ambiguity → `external_candidates` breakdown + `external_supertype_ambiguous` diagnostic; tests: simple-name/qualified/exact-id resolution, `test_project_symbol_shadows_external_supertype`, `test_distinct_external_ids_sharing_a_simple_name_stay_unmerged`, `test_impact_ambiguous_external_name_returns_grouped_breakdown` (incl. exact-id re-query), `test_graph_impact_from_external_interface_returns_implementors` (hop-2 dependents included).
- [x] AC-4: Extraction output is byte-identical for the fixture unless the census proved a payload-layer drop (in which case the only change is that previously-dropped edges now survive); supertype name fidelity ("as declared") is pinned by test. — the census proved NO payload-layer drop, and `graph_indexer.py` has ZERO edits this change (git diff empty); external CALL targets are excluded from supertype resolution by test (`test_external_call_targets_are_not_supertype_resolvable`); as-declared name forms (simple + dotted) are pinned by the resolution tests.
- [x] AC-5: `GRAPH_BUILDER_VERSION` is bumped if and only if the payload shape changed, with the Decision Log entry; when unbumped, a live query against this repo's existing graph (no re-extract) demonstrates the new visibility. — NOT bumped (pure query/server-layer change; Decision Log 2026-07-11); live demo: the census fixture repo's graph was extracted with builder v43 BEFORE the fix and served the full scenario AFTER it with no re-extraction (resolution, labeled external seed, implementor blast radius, gated supertypes).
- [x] AC-6: `wave_graph_report` main sections remain free of external rows (regression-pinned). — `test_report_main_sections_stay_free_of_external_rows` on a fixture whose graph carries external supertype edges.
- [x] AC-7: Seeds/tool descriptions document the inheritance external signals (no internal artifact IDs); docs validation passes. — `code_impact`/`code_callhierarchy` tool docstrings gained the `supertypes`/`external_target`/`external_candidates` field docs; seeds 211 (Guru) and 180 (implement-feature) extended where the calls external buckets were already documented (rationale stated inline, no internal IDs); `wave_validate` clean.
- [x] AC-8: Full framework tests run bytecode-free and docs validation passes. — full suite 4,832 tests OK bytecode-free (run_tests.py, 2026-07-11); `wave_validate` clean.

## Tasks

- [x] Build the Java + C# external-supertype fixture; run the end-to-end census; record findings (Req 1 gate). — census recorded in the Progress Log (Java live-repo census 2026-07-11; the C# positional-convention case joins the test fixtures in implementation).
- [x] Implement the layer fix(es) the census names (payload/adjacency survival and/or server-layer surfacing). — census proved no payload drop; fixes are `graph_query` (external-supertype index in `__init__`, `resolve_symbol` last-tier fallback, `external_supertype_matches`/`external_supertype_group`/`supertype_summary`) + `server_impl` surfacing.
- [x] Add external inheritance counts + include-external gating to `code_impact`/`code_callhierarchy` (calls parity). — `supertypes` sections with always-on counts; callhierarchy gates the external list on `include_external`.
- [x] Implement external-supertype name resolution + implementor-list view, project-shadowing rule included. — resolution fallback + labeled external impact seed + grouped ambiguity response.
- [x] Decide + record the `GRAPH_BUILDER_VERSION` question per the census outcome. — no bump (Decision Log 2026-07-11).
- [x] Tests per AC-2..AC-6; re-verify the field scenario shape (multiple implementors, one external interface). — 9 graph_query tests (`ExternalSupertypeVisibilityTests`) + 5 server tests (`ExternalSupertypeServerTests`); the census fixture IS the field shape (2 implementors, 1 external interface, external extends).
- [x] Seed/tool-description updates (Req 8). — tool docstrings + seeds 211/180 (seed gate opened/closed around the edits).
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`. — full suite 4,832 tests OK bytecode-free (run_tests.py, 2026-07-11); `wave_validate` clean.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census | implementer | — | Fixture + end-to-end trace; gates everything |
| surfacing | implementer | census | Counts, gating, hierarchy/impact parity |
| resolution | implementer | census | External-name lookup + implementor list |
| tests-docs | qa-reviewer | surfacing, resolution | Fixtures, pins, seeds, validation |


## Serialization Points

- The Req-1 census blocks implementation — the fix layer is chosen on evidence, not hypothesis.
- The `GRAPH_BUILDER_VERSION` decision blocks completion (bump-iff-payload-change, recorded).

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md` — external-target handling parity across relations.
- `docs/specs/mcp-tool-surface.md` — `code_impact`/`code_callhierarchy` external inheritance signals.
- `docs/references/wavefoundry-graph-tools-feedback.md` — mark the 2026-07-06 finding addressed.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The census is the design gate — fixing the wrong layer wastes the wave. |
| AC-2 | required | The reported defect: zero-signal invisibility from the implementor side. |
| AC-3 | required | The blast-radius query the field consumer actually wanted. |
| AC-4 | required | Extraction faithfulness is the graph's core discipline. |
| AC-5 | required | Version discipline determines whether field repos need re-extraction. |
| AC-6 | required | Report-surface cleanliness is an established convention. |
| AC-7 | important | Discoverability; the signal is useless if undocumented. |
| AC-8 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-11 | Drafted from the 2026-07-06 field report (external `implements`/`extends` invisible, unlike `calls`), operator-directed as pre-1.12 work. Pre-planning exploration verified: extraction KEEPS external supertype targets (`external::` form, never dropped) and `implements`/`extends` are in the default impact traversal — so the gap is payload-emission and/or query/server-layer, pinned by the Req-1 census. The companion field item (corp-TLS cluster) was found already shipped (uv scrub in 1.9.7; launcher CA coverage in 1.10.0), so this is the single remaining pre-1.12 wave. | `docs/references/wavefoundry-graph-tools-feedback.md` (2026-07-06 entry); `graph_indexer.py` inheritance-relations block + C# correction-pass external skip; `graph_query.py:32` default impact relations; `server_impl.py:13965/14087` calls-only external counts. |
| 2026-07-11 | **Census complete (Req 1 / AC-1) — fixture: 2 Java implementors of an external interface + 1 external extends + a project-internal control.** Boundary evidence: (1) **payload** — external inheritance edges PRESENT (`implements → external::TypeInstrumentation` ×2 EXTRACTED, `extends → external::InstrumentationModule`; project-internal control RECEIVER_RESOLVED), zero `external::` NODES (dangling targets by design); note: an unqualified declaration stays a SIMPLE-name external id even when an import could qualify it — the distinct-id grouping amendment therefore applies to declared-qualified forms, while unqualified same-name externals genuinely share an id at extraction (faithful to "as declared"; qualification-via-import-facts is extraction modeling, out of scope). (2) **graph_query adjacency** — raw `traverse()` follows external inheritance edges BOTH directions, including reverse-BFS FROM `external::TypeInstrumentation` (finds both implementors) — the machinery works; but `resolve_symbol("TypeInstrumentation")` → None (external ids absent from the symbol index), so no query can reach it. (3) **server** — `code_impact(implementor)` correctly shows empty incoming blast radius (impact = dependents; the interface is not a dependent), but NO supertype/external signal is surfaced anywhere, and `code_impact(TypeInstrumentation)` dies at resolution. **Fix layers named:** graph_query `resolve_symbol` external-supertype fallback (project-shadowed, distinct-id grouping) + server-layer external-seed labeling and implementor-side supertype surfacing/counts. **No payload change → no `GRAPH_BUILDER_VERSION` bump; field graphs light up without re-extraction.** | Fixture census transcripts (payload edge dump; traverse both directions; resolve_symbol None; graph_impact empty affected with edges reachable). |
| 2026-07-11 | Implemented: `graph_query` external-supertype index (`__slots__` extended), last-tier `resolve_symbol` fallback (project-shadowed by construction), `external_supertype_matches`/`external_supertype_group` (distinct-id breakdown per the council amendment), `supertype_summary`; `server_impl` — `code_impact` external-seed labeling + `external_candidates` ambiguity response + `supertypes` section; `code_callhierarchy` `supertypes` with `include_external` gating and always-on counts; tool docstrings + seeds 211/180. End-to-end verified on the census fixture (graph extracted pre-fix, builder v43, no re-extract): `code_impact(TypeInstrumentation)` → labeled external seed, both implementors affected; implementor-side supertypes with counts; shadowing and grouping proven. 14 new tests. | `graph_query.py`, `server_impl.py`, seeds 211/180; `ExternalSupertypeVisibilityTests` (9), `ExternalSupertypeServerTests` (5); fixture end-to-end transcript. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-11 | Surface existing extraction facts (calls-parity visibility + external-name resolution); no new extraction modeling. | The extractor already emits the edges faithfully; the invisibility is downstream. Surfacing is low-risk and matches the `calls` precedent consumers already understand; extraction changes would need a builder-version bump + field re-extraction for no added truth. | **Mint first-class external supertype nodes with package coordinates:** weakness — requires FQN inference the extractor deliberately refuses (never guessed); deferred unless the census shows name-only resolution is insufficient. **Counts only (no external-side resolution):** weakness — leaves the highest-value query (implementors of an external interface) unanswerable. |
| 2026-07-11 | `GRAPH_BUILDER_VERSION` NOT bumped. | The census proved the payload already carries the external inheritance edges — this change touches only `graph_query`/`server_impl` (query/read layer), so the emitted payload shape is unchanged and field graphs light up on upgrade without re-extraction. | **Precautionary bump:** weakness — forces a full graph re-extract on every field repo for a change that reads existing data. |
| 2026-07-11 | `code_impact` includes the `supertypes` section unconditionally; `code_callhierarchy` gates the external entry list on its existing `include_external` param (counts always on). | Supertype cardinality is tiny (a class declares few supertypes), so impact's always-on section costs nothing; callhierarchy already owns the include_external convention, so the gate follows the tool's established UX. | **Gate both:** weakness — impact has no include_external param today; adding one for a 1–3 entry list is API noise. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The census reveals edges are dropped at payload emission — fixing that changes payload shape and forces a `GRAPH_BUILDER_VERSION` bump + field re-extract | Acceptable and handled by the standing upgrade machinery (upgrade re-extracts on builder-version advance); Req 5 makes the decision explicit either way. |
| External simple-name resolution collides with project symbols | Project-shadowing rule (AC-3): externals never shadow project nodes; ties resolve to project. |
| Surfacing externals bloats hierarchy/impact responses | include-external gating + always-on counts mirror the proven `calls` UX; report surfaces stay external-clean (AC-6). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
