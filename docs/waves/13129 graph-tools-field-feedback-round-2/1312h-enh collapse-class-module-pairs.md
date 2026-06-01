# `collapse_class_module_pairs: bool` — Aggregate Top-Level Class with Its Containing File

Change ID: `1312h-enh collapse-class-module-pairs`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Solaris field report (2026-06-01) on `1.2.0+312f`: when `StatusBarManager.swift` defines a top-level `class StatusBarManager: ObservableObject`, the indexer mints two distinct graph nodes:

- `path/StatusBarManager.swift` (kind: `module`) — the file node, aggregating all internal helpers
- `path/StatusBarManager.swift::StatusBarManager` (kind: `class`) — the class node

The AppDelegate's `let manager = StatusBarManager(dataModel: dataModel)` resolves to the class init. So `code_callhierarchy(StatusBarManager)` resolved to the class node returns the constructor caller correctly, BUT `code_callhierarchy` resolved to the module node returns empty `incoming` even though it's the same conceptual thing from an architectural-orientation standpoint. Operators investigating "what depends on StatusBarManager?" hit a discovery problem: they query the module name, get an empty answer, conclude no callers exist, and miss the constructor wiring.

The fix is structurally identical to wave 130rj's `collapse_generated_files: bool` mode — a query-time view aggregating two nodes into one for fan_in/fan_out/chokepoints/communities surfaces, without changing the underlying graph schema. Per-symbol tools (`code_callhierarchy`, `code_impact`, `code_callgraph`, `code_graph_path`) deliberately do NOT support the flag — they need the full per-symbol view.

## Approach

For each file node `path/Foo.<ext>` (kind: `module`), check if a sibling class/struct/interface node exists at `path/Foo.<ext>::Foo` (matching the file basename without extension). If yes:

- Aggregate the two nodes into a single virtual node carrying the file path as id but `kind: "class_or_module"` (or keep `module` for backward compat — tbd in implementation).
- Outgoing edges from either source merge with dedup on `(target, relation)`.
- Incoming edges to either target merge with dedup on `(source, relation)`.
- The aggregated node's `label` is the class name.

Detection per language:

- **Swift**: `Foo.swift` containing `class Foo` / `struct Foo` / `actor Foo` / `enum Foo` / `protocol Foo`.
- **Java**: `Foo.java` containing `class Foo` / `interface Foo` / `enum Foo` / `record Foo`. Top-level only.
- **Kotlin**: `Foo.kt` containing `class Foo` / `interface Foo` / `object Foo`. Detection respects the same convention.
- **C#**: `Foo.cs` containing `class Foo` / `interface Foo` / `struct Foo` / `record Foo`. Top-level only (C# allows multiple top-level types per file — only collapse when there's exactly one matching the file basename).

Swift-first scope per Solaris's report. Java/Kotlin/C# collapse runs the same algorithm with language-specific kind detection — gate behind a separate dispatch table so operator-validated languages turn on independently.

## Requirements

1. **New `collapse_class_module_pairs: bool = False` parameter on `wave_graph_report` and dashboard graph-render endpoints.** Default off. Mirrors the `collapse_generated_files` shape.
2. **New `collapse_class_module_view(payload, language_set)` helper in `graph_query.py`** that returns a payload with the aggregated nodes/edges. The original index is not mutated.
3. **Aggregation runs across the language set passed in.** Default language set when the flag is on: `{"swift"}`. Operator can opt into multi-language via a separate `collapse_class_module_languages: list[str] | None` parameter or a constant in the helper. Initial scope: just `{"swift"}` exposed as a constant; extend by operator report.
4. **Per-symbol navigation tools unaffected** — they don't accept the parameter and operate on the unmodified index.
5. **The collapsed node carries `collapsed_pair: true`** so consumers can distinguish aggregated nodes from native single nodes.
6. **MCP wrapper signature exposes the parameter.** Add to `TestMcpWrapperParameterExposure` regression test.
7. **Tests** cover (a) Swift file+class collapse produces one node with merged edges; (b) Java/Kotlin/C# (when enabled in the language set) produce the same; (c) file without matching class is unaffected; (d) class without matching file (rare — e.g. multi-class file) is unaffected; (e) constructor-call routing through the collapsed node attributes incoming correctly; (f) MCP wrapper exposure test.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_query.py` — `collapse_class_module_view` helper + per-language kind detection.
- `.wavefoundry/framework/scripts/server_impl.py` — `collapse_class_module_pairs` parameter on `wave_graph_report_response` + MCP wrapper signature + docstring.
- `.wavefoundry/framework/scripts/dashboard_server.py` and graph-render endpoints — same parameter for visualization parity.
- `.wavefoundry/framework/scripts/tests/test_graph_query.py` + `test_server_tools.py` — 6 regression tests including MCP wrapper exposure.

**Out of scope:**

- Multi-class-per-file aggregation (Java inner classes, Kotlin companion objects). Only top-level class matching file basename.
- Static graph-builder change to merge class+module at index time. The collapse runs as a query-time view, preserving the unmodified graph for per-symbol tools.
- Per-symbol tool support. Deliberate — they need the full view.
- Automatic detection of "this file is a class" via content scan. Detection is purely name-matching: file basename equals top-level type name.

## Acceptance Criteria

- [ ] AC-1: `wave_graph_report` accepts `collapse_class_module_pairs: bool = False`. Echo in response.
- [ ] AC-2: When True for a Swift fixture, `Foo.swift` + `Foo.swift::Foo` aggregate to one node with merged incoming/outgoing edges.
- [ ] AC-3: Aggregated node carries `collapsed_pair: true` and the class name as label.
- [ ] AC-4: Per-symbol tools (`code_callhierarchy`, `code_impact`, `code_callgraph`, `code_graph_path`) deliberately do NOT accept the parameter.
- [ ] AC-5: Files without a matching top-level class are unaffected (file node preserved as-is).
- [ ] AC-6: MCP wrapper exposes `collapse_class_module_pairs` — regression test in `TestMcpWrapperParameterExposure`.
- [ ] AC-7: Dashboard graph-render endpoints accept the same parameter for visualization parity.
- [ ] AC-8: 6 regression tests cover the matrix.
- [ ] AC-9: All existing tests continue to pass.

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Implement `collapse_class_module_view` helper in graph_query.py
- [ ] Wire into `wave_graph_report_response`
- [ ] Update MCP wrapper signature + docstring
- [ ] Wire into dashboard graph-render endpoints
- [ ] Add 6 regression tests
- [ ] Update `TestMcpWrapperParameterExposure`
- [ ] Run framework tests
- [ ] Close gate
- [ ] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Surface contract |
| AC-2 | required | The headline aggregation |
| AC-3 | required | Consumer-visible discriminator |
| AC-4 | required | Boundary discipline — per-symbol tools must not collapse |
| AC-5 | required | No collateral damage to unmatched files |
| AC-6 | required | MCP wrapper exposure — lesson from wave 130ol/130rj |
| AC-7 | required | Dashboard parity |
| AC-8 | required | Regression coverage |
| AC-9 | required | No existing regressions |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Query-time view, not graph-builder change | Identical pattern to `collapse_generated_files`. Preserves the underlying graph for per-symbol tools that need full resolution. Avoids `GRAPH_BUILDER_VERSION` bump and cache invalidation | Builder-time merge (rejected — breaks per-symbol tools' class vs module resolution) |
| 2026-06-01 | Swift-first scope; Java/Kotlin/C# extension operator-validated | Solaris reported on Swift specifically. The other languages have the same name-convention pattern but vary in edge cases (Java inner classes, Kotlin companion objects). Ship the validated case first | Cover all four languages at admission (rejected — Solaris's evidence is Swift-only; other languages need their own operator validation cycle) |
| 2026-06-01 | Name-match detection only (file basename == top-level type name) | Cheap, unambiguous, no AST scan needed during collapse. Misses some cases (e.g. Swift `Foo.swift` with `class FooManager`) but those aren't the dominant pattern | AST-scan to detect "this file is dominated by one type" (deferred — adds complexity for edge cases not yet operator-reported) |
| 2026-06-01 | Top-level only; don't collapse nested types | Nested types are intentionally separate nodes — they ARE separate entities. Only the top-level type's identity is conceptually fused with the file's | Collapse all single-type files (rejected — semantic over-reach) |
| 2026-06-01 | Default off | Backward compat. Existing operators reading class vs module as separate entries continue to | Default on for Swift (rejected — silent behavior change; opt-in is safer) |

## Risks

| Risk | Mitigation |
|---|---|
| Aggregation hides cases where the class and file legitimately differ in scope (e.g., file-level extensions adding methods to other types) | Default off; operators opt in. The collapsed view is for architectural orientation; full view stays available |
| Per-symbol tools' resolution diverges from the report's view, confusing operators who switch between them | Documentation makes the distinction explicit: collapse is a report-time view. Per-symbol tools see the underlying graph |
| Multi-class files (common in C#, occasional in Java) trigger no-op behavior silently | AC-5 ensures unmatched files pass through unchanged. Doc the boundary |
| Java/Kotlin/C# enablement later surfaces edge cases (anonymous inner classes, Kotlin `companion object Foo` collisions) | Language-set parameter scoping keeps each language's enablement independent; reverting one language doesn't affect others |

## Related Work

- Direct response to Solaris field feedback on `1.2.0+312f` (suggestion #2).
- Structurally mirrors wave 130rj's `130su-enh generated-code-collapse-mode` — same view-not-modification pattern, different aggregation rule.
- Companion to `01-decompose-name-collision-count` — collapsed nodes' `same_name_node_count` reflects the post-collapse uniqueness.
- Companion to `02-file-hubs-section-split` — when collapse is on, the file_hubs section's entries change shape (file+class aggregate appears as one entry, not two).

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
