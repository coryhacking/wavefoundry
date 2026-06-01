# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-06-01

wave-id: `13129 graph-tools-field-feedback-round-2`
Title: Graph Tools — Field Feedback Round 2

## Objective

Ship the round-2 follow-on improvements identified by two independent operator field reports on the graph tools shipped in wave 130rj (`1.2.0+312f`):

- **Solaris (Swift, 2026-06-01)** — investigated `StatusBarManager (module)` with `fan_out: 77` flagged by `name_collision_count: 72`. Found the count was 100% same-file aggregation noise (nested types, closure-scope helpers) — the diagnostic conflated same-file with cross-file collisions. Proposed: decompose `name_collision_count`; split `file_hubs` out of `chokepoints`; doc + lock `kind:"module"` `count` semantics; `collapse_class_module_pairs: bool` query-time view (Swift-first); `large_community_advisory` diagnostic for 200+-node communities with hub recovery hint.
- **Aceiss (Java, 2026-06-01)** — discovered `code_impact` and `code_callhierarchy` return contradictory answers on the same symbol (`writeObject`: 19 vs 2 callers) because wave 130rj's receiver-type fix was a per-tool filter, not a graph-builder change. Also reported `name_collision_count` misses external collisions (the common Java case — `writeObject`, `run`, `close`, `equals`). Proposed: promote receiver-type resolution to the graph builder (one fix for all consumers); extend `name_collision_count` decomposition with `external_name_collision_count`.

Convergent observation: the round-1 wave (130rj) added the right diagnostics but at the wrong layer — diagnostics on top of a graph that still carries phantom edges. This wave moves receiver-type resolution to the source of truth (the graph builder) and decomposes the collision diagnostic so both reports' signals surface.

## Changes

Change ID: `1312b-enh decompose-name-collision-count`
Change Status: `planned`

Change ID: `1312d-enh file-hubs-section-split`
Change Status: `planned`

Change ID: `1312f-enh module-fan-out-semantics-doc-and-test`
Change Status: `planned`

Change ID: `1312h-enh collapse-class-module-pairs`
Change Status: `planned`

Change ID: `1312j-enh large-community-advisory`
Change Status: `planned`

Change ID: `1312l-enh graph-builder-java-receiver-type-attribution`
Change Status: `planned`

## Wave Summary

Six-change wave addressing convergent Solaris (Swift) + Aceiss (Java) field feedback on `1.2.0+312f`. Five changes are server/query-layer enhancements (decompose collision count; split file_hubs from chokepoints; doc + lock module fan_out semantics; class/module collapse view Swift-first; large-community advisory diagnostic). The sixth change (1312l) promotes wave 130rj's per-tool receiver-type filter to the graph builder layer — eliminates phantom Java edges at index time, fixes `code_impact` / `wave_graph_report.fan_in` / any future graph-consuming tool in one stroke, and bumps `GRAPH_BUILDER_VERSION`.

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required for all server_impl.py / graph_indexer.py / graph_query.py changes. Open and close per editing burst.
- **Watchpoint:** `seed_edit_allowed` gate required for seed-211 updates (changes 1312b and 1312j). Pair gate open/close with the doc edit.
- **Watchpoint:** Change 1312l bumps `GRAPH_BUILDER_VERSION`. Coordinate with any in-flight changes that touch the graph builder; the bump invalidates cached graphs and forces re-extraction on next `wave_index_build`. Operators upgrading from `1.2.0+312f` will see a one-time graph rebuild — call this out in release notes.
- **Watchpoint:** Change 1312b deprecates (but preserves) the `name_collision_count` field from wave 130rj. The alias stays for one release; the deprecation note in the docstring is the only follow-up signal — track removal for wave round-3 or later.
- **Watchpoint:** Change 1312h (class/module collapse) is Swift-first. Java / Kotlin / C# extensions are deliberately out of scope; operator-validation-driven. Do not pre-emptively enable other languages.
- **Watchpoint:** Implementation order recommendation — easy → hard: 1312f (doc + test) → 1312j (advisory diagnostic) → 1312d (section split) → 1312b (decompose collision fields) → 1312h (class/module collapse) → 1312l (graph-builder receiver-type). Land the diagnostic-layer changes (1312b, 1312j) before the source-of-truth fix (1312l) so the new fields reflect the cleaned-up graph on first build.
- **Watchpoint:** Change 1312l requires shared-module refactor of the receiver-type resolution helpers currently in `server_impl.py`. The existing 9 unit tests in `TestJavaReceiverTypeResolution` and `TestExtractJavaOwnerClassFromNodeId` may need import-path adjustment post-refactor.
- **Blocking pre-implementation:** wave council readiness review pending before any implementation begins. Operator confirmed: review-first, then implement.

## Review Evidence

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.
