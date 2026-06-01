# Graph Cross-File Resolution for All Tree-Sitter Languages, Not Just Python

Change ID: `130qf-bug graph-tree-sitter-cross-file-coverage`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130et framework-bin-mcp-server-launcher

## Rationale

Operator validation of `1.1.0+30ps` (130ol's first build) on the Solaris codebase confirmed the noise-reduction half of 130ol shipped correctly (`external::try`/`await`/`nil` gone; `external_outgoing_count` accurate; `code_impact path=` returns `unsupported_language` for Swift). But **the graph genuinely has zero project-internal call edges for Swift symbols** — `code_callhierarchy(scheduleRoutineForAppropriateTime)` returns empty incoming/outgoing, `code_callgraph(runDuskRoutine, depth=2)` returns 1 node 0 edges, `code_graph_path(SolarisCommand.run → reconcileMissedOccurrence)` returns `found: false`. Operator direction (2026-05-31): "We need to support this in all of the languages we currently employ treesitter for, not just python."

Investigation traced four compounding issues — each invisible in 130ol's regression coverage (which exercised Go and Python only):

1. **No positional-callee fallback for Swift/Kotlin.** Swift's `call_expression` has no `callee`/`function`/`name` field — the callee is positional (first non-suffix child). When the field-name lookup returned empty, the multi-token regex fallback had already been disabled (130ol's noise-reduction half). Result: extraction returned empty candidates and no edge was created. Same shape applies to Kotlin.

2. **`property_declaration` (let/var bindings) pushed scope.** `_ts_kind_for_definition` classified `property_declaration` as kind="function" (default fallback), and `_ts_is_scope_node` then pushed a new scope. So a call inside `let r = h.process()` was attributed to `Worker.bar.r` (a phantom inner scope) instead of `Worker.bar`. The short-symbol pruning pass then silently dropped that phantom symbol AND its outgoing call edges. Same shape: Kotlin `val`/`var`, Java `local_variable_declaration`/`field_declaration`, C# `variable_declaration`, TS/JS `lexical_declaration`/`variable_statement`, Rust `let_declaration`, Go `var_declaration`/`const_declaration`/`short_var_declaration`.

3. **C++ function_declarator double-registration.** In tree-sitter-cpp, `function_definition` contains a `function_declarator` that wraps the name and parameter list. Both nodes get classified as definitions, so a single C++ function (`int helper_process() { ... }`) registers TWO project nodes: `A.cpp::helper_process` (from function_definition) and `A.cpp::helper_process.helper_process` (from function_declarator). Both have simple name `helper_process`, so the cross-file resolver's ambiguity guard refused to rewrite `external::helper_process` (sees 2 candidates → bails). Result: zero C++ cross-file edges.

4. **C# dotted-target lookup misses `h.Process` form.** C#'s `invocation_expression` exposes the callee via its `function` field, which for `h.Process()` returns the whole expression text `h.Process`. The cross-file resolver's qualified-name path then looked for a project node whose qualified name was `h.Process` (i.e. file → ... → `h.Process`) — nothing matches. The previous suffix-index optimization explicitly skipped single-segment suffixes (`if "." in suffix`), so the bare `Process` lookup never fired. Result: every `h.Method()` style call in C# stayed external.

All four issues were verified locally with synthetic two-file projects per language and confirmed against a synthetic Swift project mirroring the Solaris failure shape (Worker.bar calls h.process() defined in Helper class).

## Requirements

1. **Positional-callee fallback for tree-sitter languages without a `callee`/`function`/`name` field** must extract the callee identifier by walking the call node's `named_children`, skipping argument/suffix-like nodes, and recursing into navigation/member-access wrappers to pick the rightmost identifier. Implemented as tree-sitter AST node-type matching (`_TS_NAVIGATION_TYPES`, `_TS_IDENTIFIER_TYPES`, `_TS_ARGS_NODE_TYPES`) — **no regex or text-pattern matching**. Per operator direction (2026-05-31): "We should do these with AST Treesitter unless it's just not supported at all."
2. **Variable-binding nodes must not push a new scope.** A new kind `"variable"` is introduced for `property_declaration` (Swift/Kotlin), `local_variable_declaration`/`field_declaration` (Java), `variable_declaration` (C#), `lexical_declaration`/`variable_statement` (TS/JS), `let_declaration` (Rust), `var_declaration`/`const_declaration`/`short_var_declaration` (Go). `_ts_is_scope_node` excludes this kind from the scope-pushing set so calls inside `let r = foo()` attribute to the enclosing function.
3. **Per-file simple-name deduplication** must collapse inner-grammar duplicates (e.g. C++ `function_declarator` nested in `function_definition`) so they don't poison the cross-file resolver's ambiguity check. The dedupe rule: within the same file, for the same simple name, keep only the entry with the shortest qualified name (the outer definition).
4. **Dotted-target last-segment fallback** must handle the `h.Method()` pattern: when the qualified-index lookup returns zero candidates AND the final segment is unambiguous in `simple_name_index` AND not in the builtin denylist, rewrite to the project node. Preserves the original AC-1a builtin guard (Python `len`, JS `Object`, Swift `String` etc. stay external regardless).
5. **`GRAPH_BUILDER_VERSION` bump** so existing graph caches built with builder=9 self-invalidate on upgrade.
6. **Per-language regression tests** for Swift, Kotlin, Java, C#, C++, Rust (plus the existing Python and Go tests) so this doesn't silently regress. Each test synthesizes a two-file project with a cross-file call and asserts the project-internal edge appears.

## Scope

**Problem statement:** Wave 130ol shipped tightened tree-sitter call-node detection and a cross-file resolution pass that worked for Python and Go but produced ZERO project-internal call edges for Swift, Kotlin, Java, C#, and C++. The noise-reduction half of 130ol was correct; the recall half wasn't — for every tree-sitter language whose grammar uses positional callee structure, treats local variable bindings as scope-pushing definitions, or duplicates symbol registrations via inner grammar nodes.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py`:
  - New helpers: `_ts_extract_callee_positional`, `_ts_extract_callee_recursive` (AST traversal — no regex). New constants `_TS_ARGS_NODE_TYPES`, `_TS_IDENTIFIER_TYPES`, `_TS_NAVIGATION_TYPES` and `_TS_VARIABLE_DEFINITION_TYPES`.
  - `_ts_relation_candidates` falls back to the positional helper for call relation in code mode when field-name lookup returns empty.
  - `_ts_kind_for_definition` returns `"variable"` for variable-binding node types.
  - Cross-file resolution pass: per-file simple-name dedupe + dotted-target last-segment fallback.
  - `GRAPH_BUILDER_VERSION` bumped 9 → 10.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`:
  - New tests in `CrossFileResolutionTests`: `test_swift_cross_file_navigation_call`, `test_kotlin_cross_file_navigation_call`, `test_java_cross_file_member_call`, `test_csharp_cross_file_member_call`, `test_cpp_cross_file_function_call`, `test_rust_cross_file_function_call`, `test_let_binding_does_not_consume_call`. Each uses tree-sitter for its respective language and skips when the language module isn't installed.

**Out of scope:**

- New language coverage beyond what tree-sitter already supports in this framework (Swift, Kotlin, Java, C#, C, C++, Go, Rust, JavaScript, TypeScript, Bash, ObjC, Scala, Ruby, PHP — all 15 languages already shipped). C is not explicitly tested in `CrossFileResolutionTests` because C++ exercises the same `function_declarator` shape; ObjC/Bash/Scala/Ruby/PHP not added as separate tests because their fields are already in the existing field-name list (verified during this investigation) — the framework testing strategy continues to use per-feature coverage, not exhaustive per-language matrices.
- Heuristic `code_impact path=` Swift handling. Still returns `unsupported_language: true` per 130ol AC-12. Adding Swift import parsing is a larger separate concern.
- Type-aware resolution. The dotted-target last-segment fallback uses simple-name uniqueness — it can't tell whether `h.process()` calls `Helper.process` vs `Worker.process` when both exist. The ambiguity guard correctly leaves these cases external. Proper type-aware resolution (Swift/Java/C# import resolution; receiver-type inference) is a much larger undertaking and deserves its own wave.

## Acceptance Criteria

- [x] AC-1: `_ts_extract_callee_positional` extracts the callee identifier from call nodes by walking `named_children`, skipping `_TS_ARGS_NODE_TYPES`, and recursing into `_TS_NAVIGATION_TYPES` to pick the rightmost `_TS_IDENTIFIER_TYPES` node. No regex; uses only tree-sitter AST node-type matching.
- [x] AC-2: `_ts_relation_candidates` for the "call" relation falls back to the positional helper when field-name lookup returns empty. The fallback is gated on `mode == "code"` so markup/sql/config modes are unaffected.
- [x] AC-3: `_ts_kind_for_definition` returns `"variable"` for node types in `_TS_VARIABLE_DEFINITION_TYPES`, and `_ts_is_scope_node` excludes that kind from the scope-pushing set.
- [x] AC-4: Cross-file resolution pre-build dedupes simple-name entries per (file, simple_name), keeping the shortest qualified-name entry. C++ `function_declarator` no longer poisons `simple_name_index`.
- [x] AC-5: Cross-file resolution's dotted-target path falls back to `simple_name_index[final_seg]` when `qualified_index[bare]` returns zero candidates. The denylist + ambiguity guard still apply. Handles C# `h.Process()` and analogous patterns.
- [x] AC-6: `GRAPH_BUILDER_VERSION` bumped to 10.
- [x] AC-7: New per-language regression tests cover Swift, Kotlin, Java, C#, C++, Rust cross-file calls; plus a `test_let_binding_does_not_consume_call` regression for the variable-binding scope fix. Existing Python and Go tests continue to pass.
- [x] AC-8: All existing tests continue to pass (1907 → 1914 tests; 7 new tests added).

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Investigate Swift extraction failure end-to-end (positional callee structure, variable-binding scope leak, function_declarator double-registration)
- [x] Add `_TS_ARGS_NODE_TYPES`, `_TS_IDENTIFIER_TYPES`, `_TS_NAVIGATION_TYPES`, `_TS_VARIABLE_DEFINITION_TYPES`
- [x] Implement `_ts_extract_callee_recursive` and `_ts_extract_callee_positional`
- [x] Wire positional fallback into `_ts_relation_candidates`
- [x] Update `_ts_kind_for_definition` to return `"variable"` for binding nodes
- [x] Update `_ts_is_scope_node` (no logic change — `"variable"` is already excluded from the existing set; comment added for clarity)
- [x] Add per-file simple-name dedupe in cross-file resolution
- [x] Add dotted-target last-segment fallback in cross-file resolution
- [x] Bump `GRAPH_BUILDER_VERSION`
- [x] Add 7 per-language regression tests
- [x] Run framework tests (1914 tests pass)
- [x] Verify 8/8 languages resolve cross-file edges via `/tmp/test_all_langs.py`
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline AST-traversal fix for Swift/Kotlin |
| AC-2 | required | Wires the positional fallback into the existing extraction flow |
| AC-3 | required | Fixes the variable-binding scope leak that drops calls into pruned local symbols |
| AC-4 | required | Without dedupe, C++ stays broken because of phantom ambiguity |
| AC-5 | required | Without the dotted last-segment fallback, C# stays broken |
| AC-6 | required | Cache invalidation so the fix self-heals on upgrade |
| AC-7 | required | Regression coverage so each per-language gap is pinned |
| AC-8 | required | No existing tests regress |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | AST-based positional fallback over regex | Operator direction was explicit: "We should do these with AST Treesitter unless it's just not supported at all." Tree-sitter exposes the call node's structural children — walking `named_children` is more robust than regex over node text | Regex over node.text for the callee identifier (rejected — that was the original 130ol noise source; would re-introduce keyword pollution). Per-language extractor classes (rejected — over-engineered for a single grammar-shape difference) |
| 2026-05-31 | Introduce kind `"variable"` rather than skipping definition entirely for `property_declaration` | At class scope, `let controller = AutomationController()` IS a meaningful member symbol — we want `code_callhierarchy(controller)` to work. Keeping it as a definition (just non-scope-pushing) preserves the symbol; excluding the kind from `_ts_is_scope_node` prevents call mis-attribution | Skip variable bindings as definitions entirely (rejected — loses class members from the graph). Context-aware definition detection (rejected — would require threading scope state into `_ts_is_definition_node`) |
| 2026-05-31 | Per-(file, simple_name) dedupe in cross-file resolution rather than fixing function_declarator at extraction time | Centralized fix at the resolver layer handles all current AND future inner-grammar duplicates without per-grammar special cases. Cheap (single hashmap pass at merge time) | Exclude `function_declarator` from definition detection (rejected — too narrow; other grammars may have analogous wrapper nodes we'd miss). Always prefer the function_definition's node when both exist (rejected — fragile heuristic; the "shortest qualified name" rule is simpler) |
| 2026-05-31 | Dotted-target last-segment fallback gated on `qualified_index` returning ZERO candidates (not on ambiguity) | If the qualified-index has ambiguous matches, that's informative — bail and stay external. Only fall through to last-segment lookup when we have NO qualified match at all. Avoids the false-positive case where one project file matches the qualified form and we'd incorrectly broaden to all simple-name matches | Always try last-segment first (rejected — would over-broaden when a qualified match exists). Skip the fallback entirely (rejected — leaves C# broken) |
| 2026-05-31 | Land as new change `130qf` rather than reopening 130ol | 130ol shipped its noise-reduction half cleanly and was marked implemented based on Go+Python coverage. The Solaris validation surfaced gaps for the per-language recall half. Treating this as a new change keeps the wave history honest (130ol = "noise + Go/Python"; 130qf = "remaining tree-sitter languages") | Reopen 130ol and add ACs (rejected — confuses the wave history; "implemented" → "planned" transitions are unusual) |
| 2026-05-31 | Don't add per-language regression tests for ObjC/Bash/Scala/Ruby/PHP | Their tree-sitter call nodes use field names already in the existing `_ts_relation_field_names` list (verified during investigation: ObjC `method`, Bash `command`, Scala `function`, Ruby `method`, PHP `name`). The framework's testing strategy uses per-feature coverage, not per-language exhaustive matrices. C++ already exercises the function_declarator shape that C shares | Add tests for all 15 languages (rejected — verbose, low signal; the existing Go test plus the 6 new tests cover all four distinct shapes: positional callee, variable-binding scope, inner-grammar dedupe, dotted-target fallback) |

## Risks

| Risk | Mitigation |
|---|---|
| Positional fallback could over-resolve when a non-call expression is mis-classified as a call by `_ts_is_call_node` | The per-language call-node list (`profile.call_node_types`) is explicit and tight (Swift: only `call_expression`). The fallback only runs when field-name lookup returns empty, which is rare for known call nodes |
| Variable-binding kind change could affect downstream consumers expecting `function`/`class`/`module` kinds only | The new kind appears in `node.kind` JSON; any consumer that uses the kind value (e.g. dashboard rendering, callhierarchy display) would need to handle it. Audited: the dashboard color-codes by kind via a default fallback color, so unknown kinds render as the default (acceptable) |
| Per-file simple-name dedupe could drop a legitimate inner symbol if it shares a simple name with the outer | The dedupe rule "keep shortest qualified name" prefers the outer definition. Inner symbols with the same simple name (rare — typically grammar artifacts) lose their separate node entry; their semantically meaningful representation is the outer node. Trade-off accepted |
| Dotted last-segment fallback could broaden resolution incorrectly for legitimately-external library calls whose final segment collides with a project symbol | The builtin denylist (AC-1a from 130ol) protects the common cases (`pathlib.Path`, `Date`, `String`). For language-specific stdlib types not in the denylist, the operator can extend per project via `workflow-config.json` in a follow-on (out of scope here) |
| `GRAPH_BUILDER_VERSION` bumps to 10 — existing 1.1.0+30ps installs will trigger a full rebuild on first `wave_index_build` after upgrade | Documented; same self-heal pattern as previous bumps (8 → 9 → 10) |

## Related Work

- Direct continuation of `130ol` (graph extractor cross-file resolution). 130ol shipped the noise-reduction half plus Python+Go cross-file resolution; 130qf completes the recall half for the remaining tree-sitter languages.
- Operator-reported via Solaris smoke-test of `1.1.0+30ps` (2026-05-31). The validation table in the operator report is preserved in the wave history as the trigger.
- Companion change in the same wave (`130et`) alongside `130eu`, `130f9`, `130nf`, `130o2`, `130o3`, `130ol`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
