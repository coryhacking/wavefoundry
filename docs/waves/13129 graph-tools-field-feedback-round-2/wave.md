# Wave Record

Owner: Engineering
Status: closed
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
Change Status: `implemented`

Change ID: `1312d-enh file-hubs-section-split`
Change Status: `implemented`

Change ID: `1312f-enh module-fan-out-semantics-doc-and-test`
Change Status: `implemented`

Change ID: `1312h-enh collapse-class-module-pairs`
Change Status: `implemented`

Change ID: `1312j-enh large-community-advisory`
Change Status: `implemented`

Change ID: `1312l-enh graph-builder-java-receiver-type-attribution`
Change Status: `implemented`

Change ID: `1316j-enh fix-module-simple-name-extraction`
Change Status: `implemented`

Change ID: `1316l-enh graph-builder-swift-class-module-merge`
Change Status: `implemented`

Change ID: `1316n-enh graph-rebuild-discoverability-and-health`
Change Status: `implemented`

Change ID: `1316p-enh external-name-collision-stdlib-allowlist`
Change Status: `implemented`

Change ID: `1316r-enh stable-community-identifier`
Change Status: `implemented`

Change ID: `1316t-enh empty-section-diagnostic-fields`
Change Status: `implemented`

Change ID: `13190-enh class-module-merge-multi-language`
Change Status: `implemented`

Change ID: `13192-enh stdlib-allowlist-multi-language`
Change Status: `implemented`

Change ID: `13194-enh receiver-type-kotlin-and-csharp`
Change Status: `implemented`

Change ID: `13196-enh class-module-merge-extended-languages`
Change Status: `implemented`

Change ID: `13198-enh stdlib-allowlist-extended-languages`
Change Status: `implemented`

Change ID: `1319a-enh receiver-type-go-rust-scala`
Change Status: `implemented`

Change ID: `1319g-enh receiver-type-swift`
Change Status: `implemented`

Change ID: `1319i-enh class-module-merge-rust-snake-to-pascal`
Change Status: `implemented`

Change ID: `1319k-enh class-module-merge-ruby-snake-to-pascal`
Change Status: `implemented`

Completed At: 2026-06-01

## Wave Summary

Wave `13129 graph-tools-field-feedback-round-2` (Graph Tools — Field Feedback Round 2) delivered 21 changes: Decompose `name_collision_count` into `same_name_node_count` + `cross_file_collision` + `external_name_collision_count`, Split `file_hubs` Section Out of `chokepoints` on `wave_graph_report`, Document and Test `kind:"module"` Fan-Out Semantics, `collapse_class_module_pairs: bool` — Aggregate Top-Level Class with Its Containing File, `large_community_advisory` Diagnostic on `code_graph_community` >200 Nodes, Graph-Builder Java Receiver-Type Attribution — Eliminate Phantom Edges at Index Time, Fix Module-Node `same_name_node_count` — Extract Basename, Not Extension, Graph-Builder Swift Class/Module Merge — Unify File+Top-Level-Class at Index Time, Graph Rebuild Discoverability — Health Breakdown, Build Counts, Last-Built Timestamp, Fix `external_name_collision_count` — Stdlib Allowlist for the Java Common Case, Stable Community Identifier — Survive Graph Rebuilds via Hub-Anchor, Empty-Section Diagnostic Fields — Distinguish "No Data" from "No Hits", Class/Module Merge — Extend to Java, Kotlin, C#, Stdlib Allowlist — Extend to C#, Kotlin, Swift, Python, Receiver-Type Resolution — Extend to Kotlin and C#, Class/Module Merge — Extend to JS, TS, Scala, PHP, Stdlib Allowlist — Extend to JS, TS, Go, Rust, Scala, PHP, Ruby, Receiver-Type Resolution — Extend to Go, Rust, Scala, Receiver-Type Resolution — Extend to Swift, Class/Module Merge — Extend to Rust (Snake-to-Pascal Convention), and Class/Module Merge — Extend to Ruby (Snake-to-Pascal Convention).

**Changes delivered:**

- **Decompose `name_collision_count` into `same_name_node_count` + `cross_file_collision` + `external_name_collision_count`** (`1312b-enh decompose-name-collision-count`) — 8 ACs completed. Key decisions: Keep `name_collision_count` as deprecated alias for one release; `cross_file_collision: bool` rather than `distinct_file_count: int`
- **Split `file_hubs` Section Out of `chokepoints` on `wave_graph_report`** (`1312d-enh file-hubs-section-split`) — 8 ACs completed. Key decisions: Split `file_hubs` out rather than default-excluding modules from chokepoints; Keep `fan_in` / `fan_out` as combined views; only split `chokepoints`
- **Document and Test `kind:"module"` Fan-Out Semantics** (`1312f-enh module-fan-out-semantics-doc-and-test`) — 4 ACs completed. Key decisions: Doc + test rather than introducing per-relation breakout; Lock the exact count in a unit test
- **`collapse_class_module_pairs: bool` — Aggregate Top-Level Class with Its Containing File** (`1312h-enh collapse-class-module-pairs`) — 9 ACs completed. Key decisions: Query-time view, not graph-builder change; Swift-first scope; Java/Kotlin/C# extension operator-validated
- **`large_community_advisory` Diagnostic on `code_graph_community` >200 Nodes** (`1312j-enh large-community-advisory`) — 8 ACs completed. Key decisions: Fixed thresholds (<50 / 50–200 / 200+); Advisory + pagination_hint both surface on large communities
- **Graph-Builder Java Receiver-Type Attribution — Eliminate Phantom Edges at Index Time** (`1312l-enh graph-builder-java-receiver-type-attribution`) — 9 ACs completed. Key decisions: Move resolution to graph builder, not per-tool filter; Preserve `code_callhierarchy_response` query-time filter as no-op
- **Fix Module-Node `same_name_node_count` — Extract Basename, Not Extension** (`1316j-enh fix-module-simple-name-extraction`) — 7 ACs completed. Key decisions: Extract basename without extension for module nodes; Single helper consumed by all three loops + collision-fields
- **Graph-Builder Swift Class/Module Merge — Unify File+Top-Level-Class at Index Time** (`1316l-enh graph-builder-swift-class-module-merge`) — 9 ACs completed. Key decisions: Merge at index time, not just at query time (mirrors 1312l pattern); File id wins the merge (not the class id)
- **Graph Rebuild Discoverability — Health Breakdown, Build Counts, Last-Built Timestamp** (`1316n-enh graph-rebuild-discoverability-and-health`) — 7 ACs completed. Key decisions: Surface graph state on every wave_index_build response (not just content='graph'); Explicit notice callout when content is not 'graph'
- **Fix `external_name_collision_count` — Stdlib Allowlist for the Java Common Case** (`1316p-enh external-name-collision-stdlib-allowlist`) — 7 ACs completed. Key decisions: Allowlist over rejected-receiver-resolution residue tracking; Java-only allowlist initially
- **Stable Community Identifier — Survive Graph Rebuilds via Hub-Anchor** (`1316r-enh stable-community-identifier`) — 9 ACs completed. Key decisions: Hub-anchor (node_id) over guaranteed-stable Leiden numbering; Keep `community_id` alongside `hub_node_id`
- **Empty-Section Diagnostic Fields — Distinguish "No Data" from "No Hits"** (`1316t-enh empty-section-diagnostic-fields`) — 7 ACs completed. Key decisions: Per-section diagnostic fields (not a global diagnostics object); `_candidates_total` instead of `_is_empty_because` enum
- **Class/Module Merge — Extend to Java, Kotlin, C#** (`13190-enh class-module-merge-multi-language`) — 9 ACs completed. Key decisions: Extend now via operator direction rather than deferring per the 1316l out-of-scope; Multi-top-level file: matching type merges, others remain separate
- **Stdlib Allowlist — Extend to C#, Kotlin, Swift, Python** (`13192-enh stdlib-allowlist-multi-language`) — 8 ACs completed. Key decisions: Per-language dispatch by source_file extension; Kotlin inherits Java common names + adds Kotlin-specific extensions
- **Receiver-Type Resolution — Extend to Kotlin and C#** (`13194-enh receiver-type-kotlin-and-csharp`) — 8 ACs completed. Key decisions: Extend now via operator direction; Conservative coverage: defer var, nullable, extension functions, generics
- **Class/Module Merge — Extend to JS, TS, Scala, PHP** (`13196-enh class-module-merge-extended-languages`) — 5 ACs completed. Key decisions: Skip Go/Rust/Ruby; TypeScript includes `type` and `enum`
- **Stdlib Allowlist — Extend to JS, TS, Go, Rust, Scala, PHP, Ruby** (`13198-enh stdlib-allowlist-extended-languages`) — 5 ACs completed. Key decisions: TS inherits JS list + framework patterns; Scala inherits Java common names
- **Receiver-Type Resolution — Extend to Go, Rust, Scala** (`1319a-enh receiver-type-go-rust-scala`) — 7 ACs completed. Key decisions: Extend via operator direction; Skip JS, TS, Ruby, PHP for receiver-type
- **Receiver-Type Resolution — Extend to Swift** (`1319g-enh receiver-type-swift`) — 6 ACs completed. Key decisions: Add Swift now — earlier deferral wasn't justified; Conservative coverage (no inference)
- **Class/Module Merge — Extend to Rust (Snake-to-Pascal Convention)** (`1319i-enh class-module-merge-rust-snake-to-pascal`) — 7 ACs completed. Key decisions: Try both snake-derived PascalCase AND literal basename
- **Class/Module Merge — Extend to Ruby (Snake-to-Pascal Convention)** (`1319k-enh class-module-merge-ruby-snake-to-pascal`) — 6 ACs completed. Key decisions: Include `module` kind; Reuse the snake-to-Pascal transformation from `1319i`
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

- wave-council-readiness: approved — 2026-06-01. Inline council with red-team, code-reviewer, qa-reviewer, performance-reviewer (rotating seat for 1312l graph-builder cost), reality-checker, and docs-contract-reviewer stances reviewing all six admitted change docs (1312b decompose-name-collision-count; 1312d file-hubs-section-split; 1312f module-fan-out-semantics-doc-and-test; 1312h collapse-class-module-pairs; 1312j large-community-advisory; 1312l graph-builder-java-receiver-type-attribution). Strongest challenge: 1312l refactor risk on the existing wave-130rj receiver-type unit tests (9 tests anchored to imports from `server_impl.py`); mitigated by AC-1 requiring the existing tests to pass after the shared-module refactor before builder integration is added. Strongest alternative considered: split 1312l into refactor (1312l-a) + integration (1312l-b); rejected because refactor has no value without integration and split adds audit-trail noise without reducing risk. Implementation order recommendation: 1312f → 1312j → 1312d → 1312b → 1312h → 1312l (diagnostic-layer before source-of-truth). Three action items tracked: (1) explicit regression test for wave-130rj `TestJavaReceiverTypeResolution` + `TestExtractJavaOwnerClassFromNodeId` post-1312l-refactor; (2) release-notes call-out for 1312l `GRAPH_BUILDER_VERSION` bump and one-time graph rebuild on upgrade; (3) operator-signoff and wave-council-delivery required at close. **PASS** — no blocking concerns; implementation proceeds in the recommended order.
- operator-signoff: <approved when operator confirms closure>

## Prepare Review Evidence

- code-reviewer: approved — 2026-06-01. Reviewed all six admitted change docs at council. Six changes, scope discipline holds. 1312f / 1312j / 1312d are small/medium additive surfaces; 1312b decomposes a field shape with deprecated alias preserving backward compat; 1312h mirrors the proven `collapse_generated_files` pattern; 1312l is the largest piece (shared-module refactor + builder integration + `GRAPH_BUILDER_VERSION` bump) and the AC contract gates the refactor on existing tests passing before integration is added. No findings ≥ medium severity.
- qa-reviewer: approved — 2026-06-01. ~26 new regression tests across the wave with explicit AC coverage per change. Coverage gap noted: 1312l doesn't explicitly call out a regression test for the existing wave-130rj receiver-type unit tests post-refactor — tracked as wave-level action item (council action item 1). No blocking gaps.

## Dependencies

- No external wave dependencies. Built on top of wave 130rj (1.2.0+312f) which shipped the per-tool receiver-type filter that this wave promotes to the graph builder layer; the `name_collision_count` field that this wave decomposes; and the `pagination_hint` on `code_graph_community` that this wave complements with `large_community_advisory`.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-01: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: performance-reviewer for 1312l graph-builder cost; strongest-challenge: 1312l shared-module refactor risk on existing wave-130rj receiver-type unit tests — silent regression if import paths drift during the move; mitigated by AC-1 test gate requiring all 9 existing tests pass before builder integration is added; strongest-alternative: split 1312l into refactor (no behavior change) + integration (with builder hookup) — rejected because the refactor has no value without integration and split adds audit-trail noise without reducing actual risk; the test-gate mitigation handles the same failure mode at lower process cost)
