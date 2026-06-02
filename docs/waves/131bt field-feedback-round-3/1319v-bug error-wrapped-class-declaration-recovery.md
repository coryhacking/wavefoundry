# Recover ERROR-Wrapped Top-Level Class Declarations from Tree-Sitter Parse Failures

Change ID: `1319v-bug error-wrapped-class-declaration-recovery`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 131bt field-feedback-round-3

## Rationale

Solaris field validation surfaced a case where `code_callhierarchy("StatusBarManager", direction="incoming")` returned empty (`external_incoming_count: 0`) despite the source file plainly containing `let manager = StatusBarManager(dataModel: dataModel)` at `AppDelegate.swift:19`. Initial hypothesis (labeled-argument constructors missed by [[1319s]]) was ruled out: synthetic fixtures with `Foo(label: value)` shape produce `CONSTRUCTION_RESOLVED` correctly.

Decisive diagnostic (run by the field validator against the real file, not a synthetic): tree-sitter-swift's grammar fails when a `switch` case body contains a non-declaration statement (e.g., `print("hi")`) followed by a local class declaration (`class Handler {}`) in that order. The parse failure cascades up the AST. In a large file (~3000 lines), the cascade reaches the file's outermost class declaration and wraps the entire `class StatusBarManager` node in `ERROR`. The indexer's `_ts_is_definition_node` gate doesn't match `ERROR`, so `walk_definitions` skips the declaration entirely. No class node registers. The class/module merge (`1316l`/`13190`) can't fire — the basename-match input never arrives. AppDelegate's construction edge emit produces target `external::StatusBarManager`, cross-file resolution finds no project node to bind to (`simple_name_index` empty for this name because the class was never registered), edge stays external — but the StatusBarManager file/module node also doesn't carry the class identity, so `code_callhierarchy("StatusBarManager")` resolves to a `kind: module` node with no incoming construction.

The root grammar bug is in `tree-sitter-swift` and should be filed upstream. The indexer-side fix decouples our graph-builder correctness from waiting on that grammar fix and protects every file with a similar parse-cascade pattern (current and future).

## Approach

Add an ERROR-recovery branch in `walk_definitions` that detects `ERROR` nodes at file/top-level scope whose source-text prefix matches a class declaration. Two independent gates keep the recovery conservative:

1. **Source-text prefix match.** After stripping leading attributes (`@MainActor`, `@available(...)`) and access/`final` modifiers, the prefix must begin with `(class|struct|actor|enum|protocol|interface|object|record|trait)\s+([A-Z]\w*)`. PascalCase required.
2. **`type_identifier` child present.** The ERROR node must contain at least one `type_identifier` named child. Tree-sitter still emits the identifier even when wrapping the declaration in ERROR.

When both fire AND the language is in the recovery allowlist (`{swift, kotlin, scala, java, csharp}` — file-level-type languages), treat the ERROR as a synthetic `class_declaration`: call `register_symbol(name, "class", node, parent_symbol)`, push scope, walk children with the synthesized scope. The basename-match class/module merge fires normally — module node updates to `kind: class`, `collapsed_pair: True`, `simple_name_index[name]` populates. Downstream cross-file resolution of `external::ClassName` rewrites to the file/module node. Construction edge has a target.

The recovery does not attempt to fix the parse — children of the ERROR remain whatever tree-sitter's recovery produced (some elements elevated to top-level by tree-sitter's resync). The class-level node and its identity are what construction-edge attribution needs.

## Requirements

1. Top-level `ERROR` nodes are inspected for class-declaration prefix shape during `walk_definitions`.
2. Recovery fires only when both prefix-match AND `type_identifier`-child gates pass.
3. Recovery is scoped to file-level (no nested ERROR recovery — methods inside an already-recovered class continue via the standard child walk).
4. Recovery is scoped to `{swift, kotlin, scala, java, csharp}` — languages with strong file-level-type convention. Python/JS/TS are excluded to avoid over-recovering ERROR nodes whose prefix happens to start with `class`.
5. The recovered class triggers the basename-match class/module merge identically to a successful `class_declaration` parse — same module-node mutation (`label`, `kind`, `collapsed_pair`), same `simple_names` registration, same `defined_symbols` append.
6. `GRAPH_BUILDER_VERSION` bumps 15 → 16 so existing graphs auto-rebuild on first query post-upgrade (via [[131e2]]'s stale-graph rebuild safety net).
7. Unit tests cover the recovery helper's logic directly (the prefix regex + child-presence check) since tree-sitter grammar versions shift between releases and a parse-trigger fixture today could parse cleanly later.

## Scope

**Problem statement:** Files with class bodies containing certain tree-sitter-swift parse-failure patterns (confirmed minimal: statement-then-local-class within a `switch` case body) cause the parser to wrap the outermost class declaration in ERROR when the failure cascade reaches the top level. The indexer skips ERROR nodes, never registers the class, and the class/module merge can't fire — breaking cross-file construction-edge attribution to that class.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — `_ts_recover_error_class` helper + integration into `walk_definitions`.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — unit tests for the recovery helper + end-to-end regression integrating against a synthetic Swift file using the minimal parse-failure trigger.
- `GRAPH_BUILDER_VERSION` bump 15 → 16.

**Out of scope:**

- Fixing the tree-sitter-swift grammar bug itself (separate upstream concern at `tree-sitter-swift` repository).
- Recovery of ERROR-wrapped function declarations, property declarations, or other non-class definitions. The recovery is targeted at the class-level identity that downstream construction-edge attribution depends on; other definition kinds aren't load-bearing in the same way.
- Recovery in Python/JS/TS where file-level type declarations are less load-bearing and the false-positive risk on `class`-prefix ERROR nodes is higher.
- Reverse-engineering the body content from the ERROR node's children. The recovery establishes class identity; children walk through their natural fragmented form.

## Acceptance Criteria

- [x] AC-1: `_ts_recover_error_class` returns `(name, "class")` for ERROR nodes whose prefix matches `@MainActor class StatusBarManager: ObservableObject` shape AND contains a `type_identifier` child.
- [x] AC-2: Recovery handles all keyword variants — `class`, `struct`, `actor`, `enum`, `protocol`, `interface`, `object`, `record`, `trait`.
- [x] AC-3: Recovery strips multiple leading modifiers (`@MainActor public final class Foo`).
- [x] AC-4: Recovery strips attributes with arguments (`@available(macOS 13.0, *) class Foo`).
- [x] AC-5: Recovery rejects ERROR nodes whose prefix doesn't start with a class keyword (`let metaclass = ...` style false positives stay rejected).
- [x] AC-6: Recovery rejects ERROR nodes with lowercase identifiers (`class foo {}`) — PascalCase invariant.
- [x] AC-7: Recovery rejects non-ERROR nodes — only fires on `node_type == "ERROR"`.
- [x] AC-8: Recovery rejects ERROR nodes lacking a `type_identifier` child — second independent gate against false positives.
- [x] AC-9: Recovery is scoped to `{swift, kotlin, scala, java, csharp}`; Python and JS/TS skip.
- [x] AC-10: `walk_definitions` invokes recovery at file-level scope (`not scope_names`) only, not on nested ERROR nodes.
- [x] AC-11: A recovered class triggers the class/module merge — module node `kind` becomes `class`, `collapsed_pair` becomes `True`, `simple_name_index[name]` populates with the file id.
- [x] AC-12: `GRAPH_BUILDER_VERSION` bumped 15 → 16.
- [x] AC-13: End-to-end regression test confirms a Swift file with the confirmed minimal parse-failure trigger (switch case body: `print("hi")` then `class Handler {}`) still produces a construction edge from a cross-file `StatusBarManager()` caller to the merged module node.
- [x] AC-14: All existing 2160 framework tests pass without modification.
- [x] AC-15 *(1.3.2)*: Recovery predicate accepts `simple_identifier` and `identifier` child kinds alongside `type_identifier` — tree-sitter-swift's grammar-recovery state emits the class-name node as `simple_identifier` rather than `type_identifier`; 1.3.1's predicate accepted only `type_identifier` and silently missed every production ERROR-wrapped class.
- [x] AC-16 *(1.3.2)*: Recovery uses identifier-child-text matching the recovered name as the second gate, replacing the prior child-kind-presence-only check. Keeps false-positive surface narrow even with the broader child-kind acceptance.
- [x] AC-17 *(1.3.2)*: `GRAPH_BUILDER_VERSION` bumped 16 → 17 so existing 1.3.1 graphs (which already auto-rebuilt to v16 but didn't activate recovery) auto-rebuild on first query post-1.3.2-upgrade.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Implement `_ts_recover_error_class` helper in `graph_indexer.py`
- [x] Integrate recovery into `walk_definitions` at file-level scope
- [x] Bump `GRAPH_BUILDER_VERSION` 15 → 16
- [x] Add unit tests covering the recovery helper's prefix regex + child-presence logic
- [x] Add end-to-end regression test using the minimal parse-failure trigger
- [x] Run framework tests
- [x] Close framework gate; mark change `implemented`
- [x] Repackage; field-verify against Solaris reproducer

## Affected Architecture Docs

- N/A — this change strengthens the existing graph-builder definition-walk against a grammar-recovery edge case; no architectural boundary or data flow change. The recovery is internal to `walk_definitions` and produces the same downstream graph shape as a successful parse.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core recovery trigger |
| AC-2 | required | Keyword coverage across supported languages |
| AC-3 | required | Modifier-prefix handling |
| AC-4 | required | Attribute-with-arguments handling |
| AC-5 | required | False-positive containment — prefix match |
| AC-6 | required | False-positive containment — PascalCase |
| AC-7 | required | False-positive containment — ERROR-only |
| AC-8 | required | False-positive containment — type_identifier child |
| AC-9 | required | Language scope — minimize false-positive surface |
| AC-10 | required | Scope discipline — file-level only |
| AC-11 | required | Downstream merge fires — construction-edge attribution survives |
| AC-12 | required | Auto-rebuild on upgrade — operators get the fix without manual rebuild |
| AC-13 | required | Regression test against the confirmed failure pattern |
| AC-14 | required | No baseline regression |
| AC-15 | required | 1.3.2 — broader child-kind acceptance (production failure mode) |
| AC-16 | required | 1.3.2 — false-positive narrowing via name-match-to-child-text |
| AC-17 | required | 1.3.2 — version bump for auto-rebuild on existing 1.3.1 graphs |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Recover via source-text prefix pattern + `type_identifier` child presence | Two independent gates keep false-positive surface narrow; either gate alone would over-recover or under-recover. The prefix regex catches class-shape; the `type_identifier` child confirms tree-sitter saw a real name there | Single-gate approaches (rejected — prefix-only over-recovers on `class`-as-identifier; child-only under-recovers when no class shape is present); whole-AST scan for class definitions in ERROR-wrapped content (rejected — heavy, brittle against grammar shifts) |
| 2026-06-01 | Scope recovery to `{swift, kotlin, scala, java, csharp}` | These languages have strong file-level-type convention — most files name a class matching the file basename, so the recovery's merge path is well-tested. Python and JS/TS have looser conventions (multiple top-level classes, varied basename relationships) where recovery's false-positive surface is wider and the merge-path benefit narrower | Recover for all languages (rejected — wider false-positive risk without clear benefit); recover for Swift only (rejected — same grammar-cascade pattern appears in Kotlin/Scala/Java/C# when their grammars hit equivalent parse-failure cascades, and the gate logic is language-agnostic) |
| 2026-06-01 | File-level recovery only (not nested) | The construction-edge bug specifically requires the file-level class identity to be registered so the class/module merge can fire and `simple_name_index` populates. Methods and nested classes inside an already-recovered class continue via the standard child walk. Adding nested recovery would broaden false-positive surface without clear benefit | Recurse recovery into nested ERROR nodes (rejected — methods inside the class body do continue to be walked via the recovered class's child loop; nested ERROR recovery would broaden surface without measurable benefit) |
| 2026-06-01 | Don't attempt to repair the parse beyond identifying the class | Tree-sitter's recovery produces fragmented children; trying to repair the body would require reimplementing grammar logic. The class identity is what construction-edge attribution needs; body content survives in its fragmented form, walked via the recovered scope | Repair the parse by re-parsing the ERROR's source with a permissive fallback (rejected — heavy; permissive fallback grammars don't exist for all five languages); skip the body entirely (rejected — the body's method declarations are still useful for receiver-type resolution and other downstream tools) |
| 2026-06-01 | Unit tests cover the recovery helper directly; end-to-end test uses the minimal parse-failure trigger | Tree-sitter grammar behavior shifts between versions — a parse-trigger fixture today could parse cleanly after a `tree_sitter_swift` bump. The helper-level unit tests pin the recovery logic permanently. The end-to-end test pins the bug class via a confirmed minimal trigger that demonstrates parse failure inside a class body still permits construction-edge resolution | End-to-end-only (rejected — fragile against grammar version shifts); unit-only (rejected — no demonstration of downstream pipeline integration) |
| 2026-06-01 | File a separate upstream issue at `tree-sitter-swift` for the switch-case-body grammar bug | The grammar bug is a real defect (statement-then-local-class in a switch case body should parse cleanly). Upstream fix benefits everyone using the grammar. Our indexer-side fix decouples our correctness from upstream timing | Wait for upstream fix without indexer-side change (rejected — leaves the construction-edge bug live for affected projects); fix only in our fork of the grammar (rejected — fragments the grammar ecosystem) |

## Risks

| Risk | Mitigation |
|---|---|
| False positive: ERROR node whose prefix happens to start with `class` and contains a `type_identifier` child but isn't actually a class declaration | Two independent gates (prefix-match + type_identifier child); PascalCase requirement on the identifier; language allowlist; conservative keyword set. Unit tests cover the false-positive cases explicitly (`let metaclass = ...`, `class foo {}`) |
| Tree-sitter grammar bumps change the AST shape and the recovery's `type_identifier` child check fails | Unit tests pin the helper logic against mocked AST nodes — independent of grammar version. End-to-end test will fail loudly if grammar shifts break the test's parse-failure trigger; that's a signal to revisit |
| Recovered class's children include malformed body content | The class identity is what matters for construction-edge attribution; downstream consumers (cross-file resolution, code_callhierarchy, code_impact) work off the class node, not the body content. Body content's fragmented form remains queryable via the file/module node's child walk |
| Operators on the older `GRAPH_BUILDER_VERSION=15` graphs don't see the fix until they rebuild | [[131e2]]'s synchronous auto-rebuild on first query handles this — the version bump 15 → 16 triggers an auto-rebuild on the first graph-reading tool call after the upgrade. No manual `wave_index_build` required |
| Upstream `tree-sitter-swift` fixes the grammar bug and the recovery becomes dead code | The recovery is conservative and inexpensive (~one regex match per ERROR node at top level). Leaving it in place even after the upstream fix protects against other parse-failure cascades that aren't the specific switch-case-body trigger. Code comment documents the grammar context for future revisitation |

## Related Work

- Direct follow-on to [[1319s]] (cross-language construction-call edges to class node). The 1319s construction-detector logic is correct; this change ensures the class node it routes edges to is actually registered when tree-sitter wraps the declaration in ERROR.
- Companion to [[131e2]] (stale-graph auto-rebuild on query) — the `GRAPH_BUILDER_VERSION` bump 15 → 16 is auto-handled on the first query after upgrade.
- Field validation feedback from Solaris (Swift) — see field-validator messages in this wave's session handoff for the diagnostic narrative and the file artifact that surfaced the bug.
- Upstream grammar bug to be filed at `tree-sitter-swift` repository: statement-then-local-class within a `switch` case body causes parse cascade.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
