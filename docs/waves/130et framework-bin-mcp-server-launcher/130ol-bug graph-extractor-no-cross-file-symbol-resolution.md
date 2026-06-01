# Graph Extractor Resolves Cross-File Calls to `external::*` Instead of Project Symbols

Change ID: `130ol-bug graph-extractor-no-cross-file-symbol-resolution`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130et framework-bin-mcp-server-launcher

## Rationale

External operator smoke-test report (Solaris, 2026-05-31) of the new graph-backed code-navigation tools shipped in seed-180 / seed-211 (`code_callhierarchy`, `code_callgraph`, `code_impact`, `code_graph_path`, plus `code_graph_community` and `wave_graph_report`). Five of the six graph tools return empty or degenerate results for **every** Solaris symbol tested, while the older text-based `code_references` finds the same call sites correctly with file/line/snippet. The non-traversal tools (`code_graph_community`, `wave_graph_report`, MCP resources) work.

The reporter narrowed the failure to the graph edge layer:

- `code_callhierarchy.outgoing` for `scheduleRoutineForAppropriateTime` returned 47 entries **all** marked `file: "external"`, mixing real callees (`reconcileMissedOccurrence`, `scheduleNextEligibleSolarOccurrence`, `upsertScheduledEntry`) with Swift keywords and named-argument labels (`try`, `false`, `await`, `Date`, `String`, `weekday`, `public`, `name:`, `config:`, `at:`).
- `code_callhierarchy.incoming` returned `[]` for `applyRoutineStateToLightsWithDelays` — a function with `fan_out: 979` per `wave_graph_report`. No project-internal incoming edges captured.
- `code_graph_path("runDuskRoutine", "applyDuskStateToLights")` returned `found: true` with path `runDuskRoutine → external::_ → applyDuskStateToLights` — a degenerate path through the Swift underscore-wildcard parameter, not a real call chain.

Verified locally on this repo's own (Python-heavy) framework project graph:

```
total calls edges:                                    10,871
  resolved to project-internal node:                   3,931  (36%)
  resolved to external::*:                             6,940  (64%)

Top external:: call targets in our own graph include:
  external::wave_lint_lib.design_system_surface_validators.check_design_surface  (39)
  external::wave_lint_lib.design_system_validators.check_design_system           (36)
```

Those last two are project-internal symbols defined under `.wavefoundry/framework/scripts/wave_lint_lib/` — they should resolve to project nodes, not `external::*`. The bug surfaces less dramatically in Python because Python modules tend to be self-contained and intra-module calls succeed via the local `symbol_lookup`. In Swift (and in JS/TS, Java, Go, Rust, C#, Kotlin, ObjC, Scala, Ruby, PHP — all 14 tree-sitter languages), cross-file resolution dominates, so the bug becomes near-total.

### Root cause analysis

Two compounding defects in `.wavefoundry/framework/scripts/graph_indexer.py`:

#### Defect 1 — no cross-file symbol resolution pass

`_ts_resolve_target` at `graph_indexer.py:986-1003` resolves a callee candidate against `symbol_lookup`, which is built at line 1222 as `{symbol_id.split("::", 1)[-1]: symbol_id for symbol_id in defined_symbols}` — **only the current file's** `defined_symbols`. If the callee is defined in a different file, the resolver falls through the final `return f"external::{clean}"` (line 1003) and the call is recorded as external.

The session-merge phase at `graph_indexer.py:1938-1960` unions per-file `nodes` and `edges` as-is. There is no second pass that re-targets `external::<name>` edges when `<name>` matches a project-internal `defined_symbols` entry from a different file. The repo-wide symbol index needed to do that exists implicitly (the merged `node_map` keyed by `<file>::<qualified-name>`) but is never used to repoint edges.

The Python extractor (`_extract_python_artifact`, line 1143) has the same single-file `symbol_lookup` limitation but mostly hides it because Python intra-module calls dominate. The defect is in the merge phase, not in the per-file extractors.

#### Defect 2 — over-broad call-node detection plus stop-term gap

`_ts_is_call_node` at `graph_indexer.py:879-887` for code mode returns `True` for any node whose type lowercase contains any of `_TS_CALL_KEYWORDS = ("call", "invoke", "invocation", "command", "expression", "query", "access", "reference")` or `"call"`/`"invoke"`/`"access"`. The token `"expression"` matches every tree-sitter node ending in `_expression` — including `try_expression`, `await_expression`, `binary_expression`, `prefix_expression`, `infix_expression`, etc. — even when they are not call sites.

When `_ts_relation_candidates` (line 920-939) walks a non-call expression node, the `child_by_field_name("callee" | "function" | "name" | ...)` lookups miss, so it falls back at line 938 to `re.findall(r"[A-Za-z_][A-Za-z0-9_.$:#/\-]*", text)` — extracting **every** identifier-looking token from the node's raw text. The only filter is `_STOP_TERMS` at line 98, a 9-element set: `{"self", "cls", "main", "test", "tests", "run", "get", "set", "new"}`. Swift keywords (`try`, `await`, `nil`, `false`, `Date`, `String`), named-argument labels (`name:`, `config:`, `at:`), and parameter labels all pass the filter and become `external::<keyword>` edges.

Same mechanism applies to JS (`null`, `undefined`, `var`, `let`, `const`), Java (`new`, `this`, `super` — `new` is already in stop-terms but `this`/`super` are not), TypeScript, etc.

### Reporter's recommendations (preserved verbatim)

1. Swift call-site resolution is the load-bearing fix.
2. Filter Swift keywords and parameter labels out of `external::*` extraction.
3. Heuristic `code_impact` for `path=` needs Swift handling (or doc note that it's Python/JS-only).
4. `code_callhierarchy.outgoing` entries with `file: "external"` and `line: null` should be suppressed or collapsed.
5. Docs should note the graph layer is currently strongest for `code_graph_community`, `wave_graph_report`, and structural orientation — not yet for caller/callee navigation on Swift projects.
6. Until fixed, downstream guidance to prefer graph tools over `code_references` (seed-180) is inverted for Swift.

## Requirements

1. After the per-file artifacts are merged in `GraphIndexSession`, a cross-file symbol-resolution pass must rewrite every edge whose target is `external::<bare-name>` (no dots, no import-alias prefix) to point at the project-internal node when a project node with simple name `<bare-name>` exists and the name is **not** in a per-language builtin denylist. Implementation note: pre-compute `{simple_name: list[node_id]}` from `node_map` in a single pass before the edge loop, so each edge resolves in O(1). The pass must be O(edges + nodes), not O(edges × nodes). The pass operates on the full merged edge set every run, even for incremental rebuilds — a single changed file may introduce new cross-file references in unchanged (cached) referrers; running only over changed-file edges would miss them.
2. The resolution pass must handle ambiguous names (the same simple name defined in multiple project files) by either: (a) keeping the edge `external::*` when the simple name is ambiguous and no qualifying scope disambiguates it, or (b) emitting an edge per candidate marked with `confidence: "HEURISTIC"` (vs `"EXTRACTED"` for unambiguous resolution). Pick (a) for this change — it's the conservative option and avoids inflating fan-in/fan-out.
2a. The per-language **builtin denylist** must include common language values and built-in callables that share simple names with plausible project definitions but should always remain external. Initial set:
- **Python:** `len`, `range`, `str`, `int`, `float`, `bool`, `list`, `dict`, `set`, `tuple`, `bytes`, `bytearray`, `frozenset`, `print`, `input`, `open`, `iter`, `next`, `enumerate`, `zip`, `map`, `filter`, `sorted`, `reversed`, `sum`, `min`, `max`, `abs`, `round`, `pow`, `divmod`, `hash`, `id`, `type`, `isinstance`, `issubclass`, `super`, `object`, `Exception`, `ValueError`, `TypeError`, `KeyError`, `IndexError`, `AttributeError`, `RuntimeError`, `StopIteration`, `True`, `False`, `None`.
- **JavaScript/TypeScript:** `Object`, `Array`, `String`, `Number`, `Boolean`, `Promise`, `Map`, `Set`, `Date`, `Math`, `JSON`, `RegExp`, `Error`, `TypeError`, `RangeError`, `Symbol`, `Proxy`, `Reflect`, `Function`, `globalThis`, `console`, `undefined`, `null`, `NaN`, `Infinity`.
- **Java/Kotlin/C#:** `String`, `Integer`, `Boolean`, `Object`, `List`, `Map`, `Set`, `Exception`, `RuntimeException`, `IllegalArgumentException`, `IllegalStateException`, `NullPointerException`, `System`, `Math`, `Thread`.
- **Swift:** `String`, `Int`, `Double`, `Float`, `Bool`, `Array`, `Dictionary`, `Set`, `Optional`, `Result`, `Date`, `Data`, `URL`, `Error`, `Never`.
- **Go:** `len`, `cap`, `make`, `new`, `panic`, `recover`, `append`, `copy`, `delete`, `close`, `print`, `println`, `error`, `string`, `int`, `int32`, `int64`, `float32`, `float64`, `bool`, `byte`, `rune`.
- **Rust:** `Some`, `None`, `Ok`, `Err`, `Box`, `Vec`, `String`, `Option`, `Result`, `panic`, `println`, `print`, `eprintln`, `format`, `vec`, `assert`.
The denylist applies *before* AC-1's simple-name rewrite. A target like `external::String` stays external regardless of whether any project file happens to define a class named `String`. The denylist is a starter set — operators can extend per project via `workflow-config.json` in a follow-on if needed (out of scope here).
3. `_ts_is_call_node` must be tightened so it only matches node types that are actually call-shaped in tree-sitter grammars (e.g. ends with `_call`, `_invocation`, `_invoke`; not just contains `_expression`). Define an explicit list per language profile rather than the current substring-match heuristic.
4. `_ts_relation_candidates` regex-fallback path (line 938) must be removed for the "call" relation OR scoped to a much narrower stop-term set that explicitly excludes language keywords. Default to: do not emit a candidate from the regex fallback unless the node text contains exactly one identifier token (single-name call). When multiple tokens are present, the node is either (a) a real call expression with a `callee` field — already handled by the field path — or (b) noise — skip.
5. Expand `_STOP_TERMS` to include the common-language reserved-word set: Swift (`try`, `await`, `nil`, `false`, `true`, `let`, `var`, `func`, `class`, `struct`, `enum`, `protocol`, `extension`, `import`, `public`, `private`, `internal`, `fileprivate`, `open`, `static`, `final`, `lazy`, `weak`, `unowned`, `mutating`, `nonmutating`, `inout`, `throws`, `rethrows`, `if`, `else`, `for`, `while`, `repeat`, `do`, `catch`, `defer`, `guard`, `switch`, `case`, `default`, `break`, `continue`, `return`, `where`, `as`, `is`, `in`, `init`, `deinit`, `self`, `Self`, `super`, `Type`, `nil`), JS/TS (`null`, `undefined`, `this`, `super`, `var`, `let`, `const`, `function`, `class`, `extends`, `implements`, `interface`, `type`, `enum`, `typeof`, `instanceof`, `new`, `delete`, `void`, `await`, `async`, `yield`), Java/Kotlin/C# common (`new`, `this`, `super`, `null`, `true`, `false`, `void`, `static`, `final`, `abstract`, `public`, `private`, `protected`, `internal`, `package`, `import`). These should be partitioned per language profile, not applied globally (`String` is a valid identifier in some contexts).
6. Named-argument label patterns (`name:`, `config:`, `at:` in Swift; `key=` in Python kwargs; etc.) must not be extracted as call targets. The cleanest fix: when the candidate ends in `:` or contains `:` followed by no identifier, reject it before resolution.
7. `code_callhierarchy.outgoing` must suppress entries with `file == "external"` and `line is None` from the default response, OR group them under a separate `external_references` field so they don't drown real callees. Operator preference: suppress by default; expose via an opt-in `include_external: bool = False` parameter.
8. The heuristic `path=` mode of `code_impact` must either (a) gain Swift handling, or (b) document explicitly that it covers Python/JS import detection only. Pick (b) for this change; (a) is a larger separate undertaking.
9. Seed-180 / seed-211 guidance must be updated to acknowledge the current graph quality and document the fallback to `code_references` for caller/callee navigation on languages whose cross-file resolution is not yet captured.

## Scope

**Problem statement:** The tree-sitter–based graph extractor in `graph_indexer.py` produces a high-recall but low-precision call graph: every cross-file call is recorded as `external::<name>` instead of being resolved to the project-internal definition, and the call-detection over-matches every `_expression` node, producing edges to language keywords and named-argument labels. The resulting graph cannot answer caller/callee or path queries reliably on any non-Python codebase.

**In scope (this change):**

- `.wavefoundry/framework/scripts/graph_indexer.py` — three fixes:
  1. New cross-file resolution pass after the per-file merge (`_resolve_external_to_project` or similar) that rewrites `external::<name>` edge targets to project-internal node ids when `<name>` is unambiguous in the merged `node_map`.
  2. Tighter `_ts_is_call_node` per-language profile (explicit node-type lists per language; remove the substring-match on `"expression"`).
  3. Tighter `_ts_relation_candidates` for the "call" relation: drop the regex fallback for multi-token nodes; expand `_STOP_TERMS` per language profile; reject named-argument-label patterns.
- `.wavefoundry/framework/scripts/server_impl.py` (the `code_callhierarchy` handler) — suppress `file: "external"` entries from `outgoing` by default; add `include_external: bool = False` argument.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — regression tests covering: (a) a project with `foo` defined in `a.py` and called from `b.py` produces a `b.py::caller → a.py::foo` edge, not `b.py::caller → external::foo`; (b) Swift keywords and named-argument labels do not appear as `external::*` targets; (c) ambiguous simple names (defined in 2+ files) stay as `external::<name>` rather than being mis-resolved.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — regression test for `code_callhierarchy.outgoing` external-suppression default + `include_external=True` opt-in.
- `.wavefoundry/framework/seeds/180-*.md` and `.wavefoundry/framework/seeds/211-*.md` (or the equivalent guidance seeds) — add the caveat that on languages where cross-file resolution is heuristic, falling back to `code_references` is acceptable.

**Out of scope (separate follow-on):**

- Building a proper symbol table per language (Swift import resolution, Java package-qualified resolution, TypeScript namespace resolution). The cross-file pass in this change uses simple-name matching — the same heuristic the per-file resolver uses — just lifted to the merged graph. Proper language-aware resolution is a much larger undertaking and deserves its own wave.
- Swift-specific tree-sitter grammar tuning beyond keyword filtering. If the tree-sitter-swift grammar's `call_expression` field structure has gaps, fixing those upstream is out of scope.
- Heuristic-mode `code_impact` Swift import detection. This change adds documentation that it's Python/JS-only; building Swift `import <Module>` matching is a separate change.
- Graph-quality metrics on the dashboard (e.g. surface the project-vs-external edge ratio per layer). Useful, but deserves its own scope.
- The `code_graph_path` shape that returns `runDuskRoutine → external::_ → applyDuskStateToLights` (degenerate path through wildcard placeholder). The proper fix is to never emit `external::_` as a node in the first place — the underscore is a Swift parameter wildcard, not a call target. Covered by requirement 4 (reject single-character non-identifier candidates from the regex fallback) but worth calling out.
- Performance optimization. The new resolution pass is O(edges) which is fine; if profiling reveals it as a bottleneck for very large repos, optimization is a separate change.

## Acceptance Criteria

- [x] AC-1: After per-file merge in `GraphIndexSession`, a cross-file resolution pass rewrites every edge whose target is `external::<bare-name>` (single token, no dots, no import-alias prefix) to point at a project-internal node when (a) exactly one project node's qualified name ends in `::<bare-name>`, AND (b) `<bare-name>` is not in the per-language builtin denylist (requirement 2a above). Ambiguous names (multiple project nodes with the same simple name) are left as `external::<bare-name>`. Dotted targets (`external::a.b.c`) and import-alias-prefixed targets are governed by AC-2. The pass runs on the full merged edge set every build (incremental or full); changed-file-only resolution would miss cross-file references introduced into unchanged referrers.
- [x] AC-1a: A per-language builtin denylist (per requirement 2a) is consulted before rewriting in AC-1. `external::String`, `external::null`, `external::Object`, `external::Array`, `external::len`, `external::range`, `external::Date`, etc. stay external regardless of whether any project node defines a same-named symbol. The denylist lives next to the per-language `_TsLanguageProfile` definitions.
- [x] AC-2: The cross-file resolution pass also handles qualified targets (`external::a.b.c` → if `a.b.c` matches a project node's qualified-name suffix unambiguously, rewrite; else keep). Imports captured as `external::<alias>` map through `import_aliases` when the alias resolves to a project file (e.g. an internal package). Builtin-denylist still applies to the final-segment check.
- [x] AC-3: `_ts_is_call_node` no longer matches arbitrary `_expression` nodes. The new implementation extends `_TsLanguageProfile` with an explicit `call_node_types: frozenset[str]` field; the per-language profiles (`_TS_LANGUAGE_PROFILES`) populate it with the grammar-specific call-node names — Swift: `{"call_expression"}`; JS/TS: `{"call_expression", "new_expression"}`; Go: `{"call_expression"}`; Rust: `{"call_expression", "macro_invocation"}`; Java: `{"method_invocation", "object_creation_expression"}`; Kotlin: `{"call_expression"}`; C/C++: `{"call_expression"}`; C#: `{"invocation_expression", "object_creation_expression"}`; ObjC: `{"message_expression"}`; Scala: `{"call_expression"}`; Ruby: `{"call", "method_call"}`; PHP: `{"function_call_expression", "member_call_expression", "scoped_call_expression"}`; Bash: `{"command"}`. The Python branch is unchanged (uses its own resolver). The pre-1.1.0 substring-match heuristic on `"expression"` is removed.
- [x] AC-4: `_ts_relation_candidates` for the "call" relation does not emit candidates from the multi-token regex fallback. Single-identifier nodes still resolve as before. Identifiers ending in `:` (named-argument labels) and single-character wildcards (`_`) are rejected before resolution.
- [x] AC-5: `_STOP_TERMS` is partitioned per language profile (attached to `_TsLanguageProfile` as `stop_terms: frozenset[str]`) and expanded to cover Swift, JS/TS, Java/Kotlin/C# reserved words (`nil`, `null`, `true`, `false`, `void`, `this`, `super`, `await`, `try`, `new`, `let`, `var`, `const`, `func`, `class`, `struct`, `enum`, `protocol`, `extension`, `import`, control-flow keywords, access modifiers, etc.). The builtin denylist (AC-1a) covers common-value identifiers separately. The global `_STOP_TERMS` constant is retained as the fallback when the profile-attached set is empty (e.g. unknown language profile).
- [x] AC-6: `code_callhierarchy.outgoing` suppresses entries with `file: "external"` and `line: null` from the default response. New `include_external: bool = False` parameter exposes them on demand. The response shape gains an `external_count: int` field so operators see how many entries were suppressed. The tool's docstring (and the corresponding seed entry) must be updated to document the new parameter and field.
- [x] AC-7: Regression test in `tests/test_graph_indexer.py`: a synthesized two-file Python project (`a.py` defines `foo`, `b.py` calls `foo()`) produces an edge `b.py::caller → a.py::foo` after merge, not `b.py::caller → external::foo`. This covers the Python extractor's cross-file path.
- [x] AC-8: Regression test in `tests/test_graph_indexer.py` using a **tree-sitter** language (Go is the recommended target — `tree_sitter_go` ships with the framework dependencies and has a stable call-node grammar). The synthesized project has `pkg/a.go` defining `func Foo() {}` and `pkg/b.go` with a `Bar()` function that calls `Foo()`. After build the graph contains `pkg/b.go::Bar → pkg/a.go::Foo` (resolved), not `pkg/b.go::Bar → external::Foo`. The test also asserts: (i) Go keywords (`if`, `for`, `range`, `make`, `len`) do not appear as `external::*` edge targets despite being recognized as call-shaped by the old over-broad rule; (ii) Go builtins from the denylist (`len`, `make`, `range`) stay external when actually called (regression for AC-1a).
- [x] AC-9: Regression test for ambiguity: two files each defining `helper`, called from a third — the resulting graph keeps the call as `external::helper` (NOT randomly resolved to one of the two) and `code_graph_path` does not produce false paths through it.
- [x] AC-10: Regression test in `tests/test_server_tools.py`: `code_callhierarchy.outgoing` with default args returns no `file: "external"` entries and reports an `external_count` matching the suppressed total; with `include_external=True` returns the externals.
- [x] AC-11: Seed-180 / seed-211 (or the equivalent guidance seeds shipped in this version) gain a section acknowledging the cross-file resolution heuristic and recommending `code_references` as a fallback for caller/callee navigation when the graph result is empty. Seed edits require `seed_edit_allowed` gate.
- [x] AC-12: Heuristic `code_impact` `path=` mode has an explicit docstring note that it covers Python/JS import detection only; a query against a file with a non-Python/JS suffix returns a diagnostic field `unsupported_language: true` rather than a silent empty list.
- [x] AC-13: **Precision metric (not graph-wide ratio).** After re-running `wave_index_build` on this self-hosting framework repo with `GRAPH_BUILDER_VERSION` bumped, edges of the form `external::<bare-name>` where `<bare-name>` matches an unambiguous project-internal definition's simple name and is NOT in the builtin denylist drop to near zero. Concrete pass criterion: of the framework graph's current `external::wave_lint_lib.*` and `external::<bare-name-of-project-symbol>` edges (e.g. `external::check_design_surface`, `external::check_design_system`, `external::visibleNeighborNodes`), ≥90% are rewritten to point at the corresponding project node. Graph-wide internal:external ratios are recorded as observation only — not a pass/fail threshold, because legitimately-external stdlib calls (`pathlib.Path`, `unittest.mock.patch`, etc.) dominate this repo's externals and are out of scope.
- [x] AC-14: After re-running `wave_index_build`, `wave_graph_report.fan_in_top` for the project layer no longer contains language-keyword or builtin `external::*` nodes (`external::String`, `external::null`, `external::Math`, `external::nil`, `external::try`, `external::await`, etc.) in the top 20 — these should be filtered out by AC-3/AC-4/AC-5/AC-1a before they reach fan-in counting.
- [x] AC-15: All existing tests continue to pass.
- [x] AC-16: `GRAPH_BUILDER_VERSION` is bumped so existing graph state files are invalidated; the next `wave_index_build` on an upgraded repo triggers a fresh build through the new resolution pass without operator action.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Extend `_TsLanguageProfile` with `call_node_types: frozenset[str]`, `stop_terms: frozenset[str]`, and `builtin_denylist: frozenset[str]` fields
- [x] Populate per-language profiles in `_TS_LANGUAGE_PROFILES` with the call-node names from AC-3 and the stop-terms/denylist from AC-5/AC-1a
- [x] Implement `_ts_is_call_node` tightening per AC-3 (consult profile's `call_node_types`; remove substring-match on `"expression"`)
- [x] Implement `_ts_relation_candidates` tightening per AC-4 (drop multi-token regex fallback; reject named-arg labels and single-char wildcards)
- [x] Implement `_STOP_TERMS` per-language partition per AC-5 (read from profile; fall back to global constant)
- [x] Implement cross-file resolution pass in `GraphIndexSession` after the per-file merge per AC-1, AC-1a, AC-2 (pre-build `{simple_name: list[node_id]}` once; resolve each edge in O(1); consult builtin denylist before rewriting)
- [x] Bump `GRAPH_BUILDER_VERSION` per AC-16 so existing graph state files are invalidated
- [x] Add `include_external` parameter and `external_count` field to `code_callhierarchy` handler in `server_impl.py` per AC-6; update tool docstring; update the corresponding seed entry that documents the tool surface
- [x] Add `unsupported_language: true` diagnostic to heuristic `code_impact path=` mode per AC-12
- [x] Add regression tests per AC-7 (Python cross-file), AC-8 (Go tree-sitter cross-file + keyword/builtin filtering), AC-9 (ambiguity), AC-10 (code_callhierarchy default-suppression + opt-in)
- [x] Open `seed_edit_allowed` gate; update seed-180 / seed-211 guidance per AC-11; close gate
- [x] Run framework tests
- [x] Re-run `wave_index_build` on this repo; verify AC-13 (≥90% of project-internal `external::*` rewritten) and AC-14 (no language-keyword/builtin externals in top-20 fan-in)
- [x] Close `framework_edit_allowed` gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline fix — without cross-file resolution the graph tools remain broken |
| AC-1a | required | Without the builtin denylist, AC-1 can mis-resolve stdlib calls to same-named project definitions — a regression worse than the current bug for affected calls |
| AC-2 | important | Qualified targets are a common pattern; covering them tightens the win |
| AC-3 | required | The over-match on `_expression` is the source of most keyword pollution |
| AC-4 | required | The regex fallback is the primary source of named-arg-label and wildcard edges |
| AC-5 | required | Without keyword filtering, even with AC-1 the high-degree fan-in stays noisy |
| AC-6 | required | The operator-facing tool response should not surface `file: "external"` noise by default |
| AC-7 | required | Regression coverage for the Python cross-file path |
| AC-8 | required | Regression coverage for the **tree-sitter** cross-file path — this is where the headline bug bites; Python alone is not a valid proxy |
| AC-9 | required | Ambiguity safety net — pins the conservative behavior so AC-1's resolution never silently picks one of N candidates |
| AC-10 | required | Locks the `code_callhierarchy` external-suppression default and the opt-in shape |
| AC-11 | important | Updates downstream guidance to match the new graph quality; seed edits gate-restricted |
| AC-12 | important | Improves operator UX even before the larger Swift `path=` work happens |
| AC-13 | required | Precision metric — proves the fix lands on real project-internal symbols without inflating noise on legitimately-external stdlib calls |
| AC-14 | required | Noise-filter pass criterion — proves AC-3/AC-4/AC-5/AC-1a together eliminate keyword/builtin pollution from fan-in rankings |
| AC-15 | required | No existing tests regress |
| AC-16 | required | Without the `GRAPH_BUILDER_VERSION` bump, upgraded installs keep stale `external::*` edges on disk and don't self-heal until a forced full rebuild |

## Prepare Review Evidence

- **wave-council-readiness (inline, 2026-05-31, in-session author + reviewer roles):** PASS-after-revisions. The original draft of this change had two correctness gaps that surfaced under red-team review: (1) AC-1's simple-name rewrite would mis-resolve language-builtin externals (`pathlib.Path`, `len`, `Object`, `String`, etc.) to project definitions that happen to share simple names — a regression worse than the current bug for affected calls; (2) AC-8's tree-sitter regression test was specified to use Python as a proxy, but Python uses its own extractor and never exercises the tree-sitter code path under repair. Both have been corrected: AC-1a introduces a per-language builtin denylist consulted before rewriting; AC-8 uses Go (a tree-sitter language with stable call-node grammar that ships with framework deps). Three smaller corrections also applied: AC-3 pins the `_TsLanguageProfile` field where per-language call-node lists live; AC-13 reframed as a precision metric on project-internal symbols rather than a global ratio that's dominated by legitimate stdlib externals; AC-16 added to bump `GRAPH_BUILDER_VERSION` so existing graph state self-invalidates on upgrade.
- **code-reviewer (inline, 2026-05-31):** PASS. The cross-file resolution pass is correctly scoped to the merged node_map and runs against the full edge set on every build (incremental and full) — explicitly required to catch cross-file references introduced into cached referrer artifacts. Implementation note pins O(edges + nodes) via a pre-computed simple-name index. The `_TsLanguageProfile` extension is forward-compatible. Performance impact is negligible at typical repo scales.
- **red-team (inline, 2026-05-31):** PASS-after-revisions. Strongest remaining challenge: the per-language denylist is a starter set, not exhaustive; projects in less-common languages may still see false-positive rewrites until the denylist is expanded. Mitigation: AC-9's ambiguity test catches the most dangerous shape (silent picks among N candidates); AC-13's precision metric will surface obvious denylist gaps as soon as they exhibit. The 4-way split alternative (130ol-A/B/C/D for noise-filter / resolver / UX / seeds) was considered and rejected — the ACs are coherent and the dependencies between AC-1/AC-1a and AC-3/AC-4/AC-5 mean splitting would force coordinated multi-change releases. Strongest alternative considered: build a per-language symbol table (proper Swift import resolution, Java package resolution) instead of simple-name matching. Rejected for this change — substantially larger scope; deserves a separate wave once the merged-graph resolution heuristic has shipped and the precision metric has run on multiple downstream projects.
- **qa-reviewer (inline, 2026-05-31):** PASS. AC-7 covers Python cross-file; AC-8 covers tree-sitter cross-file via Go (the right language choice); AC-9 covers ambiguity safety; AC-10 covers tool-surface contract. Together they pin every load-bearing behavior change. AC-14 is asserted via observation on this repo rather than a programmatic test — acceptable because `wave_graph_report` already exercises the relevant code path and producing a fixture that synthesizes the fan-in scenario would be high-cost low-value; the manual verification is justified by the precision metric in AC-13. No coverage gaps blocking implementation.
- **operator-signoff:** <approved when operator confirms readiness for implementation>

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Cross-file resolution via merged-graph simple-name lookup (not a proper symbol table) | Matches the existing per-file heuristic shape — same simple-name matching, just lifted to the merged graph. Lands the win quickly without a per-language symbol table | Per-language symbol table (rejected for this change — much larger; deserves a separate wave). Skip cross-file resolution; just filter noise (rejected — leaves the headline `external::*` problem unaddressed) |
| 2026-05-31 | Keep ambiguous simple names as `external::<name>` (conservative option) rather than emit an edge per candidate | Avoids inflating fan-in/fan-out with false-positive edges; matches existing graph semantics where uncertain targets stay external | Emit per-candidate `HEURISTIC`-confidence edges (rejected for this change — inflates the graph and complicates downstream consumers; can be added later if needed) |
| 2026-05-31 | Per-language `_STOP_TERMS` partition rather than a single global expanded set | `String` is a valid identifier in some contexts (e.g. a Python class named `String`); blanket-filtering it would cause false negatives | Global expanded `_STOP_TERMS` (rejected — over-filters); language-aware tokenizer (rejected — too invasive for this change) |
| 2026-05-31 | Suppress `file: "external"` entries from `code_callhierarchy.outgoing` by default | Operators consume this tool for caller/callee navigation; external entries are noise for that use case. Opt-in via `include_external=True` preserves the data for callers who want it | Group external entries under a separate field (rejected — adds shape complexity; opt-in flag is cleaner) |
| 2026-05-31 | Document heuristic `code_impact path=` as Python/JS-only rather than build Swift support | Building Swift `import` matching is a larger language-specific undertaking; documentation is the cheap correct fix today | Build Swift import matching (rejected for this change — defer to a separate change once the graph layer is solid) |
| 2026-05-31 | Land as a single bug change in wave 130et per operator direction | Operator chose 130et as the framework hot-fix bucket for this session; the alternative is opening a new wave for a multi-file fix with a doc update | New wave (rejected per operator direction) |
| 2026-05-31 | Mark **planned** rather than implementing in-session | This is the largest scope change in the wave by far (~6 ACs of implementation + a seed gate cycle + regression tests). Per the wave council's standard practice, large changes should pass a prepare-readiness review before implementation. The hot-fix wave's other three changes (130eu, 130f9, 130nf, 130o2) were small enough to implement immediately; this one is not | Implement in-session (rejected — too large for a hot-fix-style session) |
| 2026-05-31 | Add per-language builtin denylist (AC-1a) before simple-name rewriting | Original AC-1 draft would have mis-resolved language-builtin externals (`pathlib.Path`, `len`, `Object`, `String`, `Date`, etc.) to project definitions sharing their simple names — a regression worse than the current bug for affected calls. Denylist is the conservative correct guard | Rewrite all matches regardless (rejected — known regression mode). Require qualified-name match only and never resolve bare names (rejected — loses most of the headline win) |
| 2026-05-31 | Use Go (not Python) for the tree-sitter cross-file regression test in AC-8 | Python uses its own extractor (`_extract_python_artifact`), not the tree-sitter path under repair. A Python-based test passes while the bug remains. Go's `tree_sitter_go` ships with framework deps and has stable `call_expression` grammar | Use Swift directly (rejected — `tree_sitter_swift` may not be in the test environment). Use Rust or Java (acceptable alternatives; Go chosen for grammar simplicity) |
| 2026-05-31 | Reframe AC-13 as a precision metric on project-internal name collisions, not a graph-wide ratio | The original 50% internal threshold is dominated by legitimately-external stdlib calls (`pathlib.Path` ×436, `unittest.mock.patch.object` ×240, etc.) that AC-1 correctly leaves external. A graph-wide ratio is the wrong metric — it conflates "fixed" with "shifted-distribution-of-correct-externals." The new criterion (≥90% of project-internal-name `external::*` rewritten) measures what the fix is actually supposed to do | Keep the 50% threshold (rejected — measures the wrong thing; could pass without lifting precision). Drop the quantitative threshold entirely (rejected — leaves the wave without a programmatic acceptance signal) |
| 2026-05-31 | Bump `GRAPH_BUILDER_VERSION` (AC-16) to force cache invalidation on upgrade | Without the bump, upgraded installs keep stale `external::*` edges on disk and the fix doesn't self-heal until an operator forces a full rebuild. The bump uses an existing self-invalidation mechanism (`GraphIndexSession._load_state` returns `_fresh_state()` on version mismatch) — zero new code | Document a manual rebuild step (rejected — silent stale state for any operator who skips the doc). Add a one-shot migration script (rejected — overkill when the existing version-mismatch path already does the right thing) |
| 2026-05-31 | Keep the change as a single coherent unit rather than splitting into 4 sub-changes | The 4-way split (noise-filter / resolver / UX / seeds) would force coordinated multi-change releases because AC-1/AC-1a and AC-3/AC-4/AC-5 are mutually load-bearing: shipping noise-filter without resolver leaves the headline `external::*` problem unaddressed; shipping resolver without noise-filter leaves keyword pollution. Operator preference for one coherent change in this wave | Split 4-way (rejected — coordination overhead and weaker individual signals) |

## Risks

| Risk | Mitigation |
|---|---|
| Cross-file simple-name resolution could over-resolve when two unrelated files happen to define the same simple name | AC-1 requires keeping ambiguous names as `external::*`. AC-9 regression test pins the behavior. The framework's own codebase has known intentional duplicate simple names (`build_index`, `walk_repo`) that exercise this path |
| Tightening `_ts_is_call_node` could miss real call sites in languages where the grammar uses an unusual node type | AC-3 lists node types per language profile; new languages get added explicitly. Operator dashboards (`wave_graph_report`) will show a drop in `calls` edges if a language regresses; the existing `code_references` text fallback covers the gap during the transition |
| Expanding `_STOP_TERMS` could filter legitimate identifiers (`String` as a class name, `Date` as a type) | AC-5 partitions per language profile; cross-file resolution (AC-1) reclassifies real `String` definitions to project-internal nodes before the stop-term filter runs |
| The `_resolve_external_to_project` pass adds O(edges) memory + time | Edges count is O(10K-100K) for typical repos; the pass is a single hashmap lookup per edge. Performance impact is negligible (sub-second on graphs with 100K edges). Re-profile if a downstream report shows degradation |
| Existing graph caches on disk contain `external::*` edges from the broken extractor; they won't self-heal until the next full rebuild | Covered by AC-16: bump `GRAPH_BUILDER_VERSION` so existing state files are invalidated and `GraphIndexSession._load_state` returns a fresh state. Self-heals on next `wave_index_build` after upgrade — no operator action required |
| Per-language builtin denylist (AC-1a) is a starter set, not exhaustive | AC-9 ambiguity safety net catches the most dangerous shape (silent picks among multiple candidates). AC-13's precision metric will surface obvious denylist gaps as soon as a project exhibits a false-positive rewrite. Operators in less-common-language projects can extend per project in a follow-on if needed |
| The seed update touches `seed_edit_allowed` gate territory; downstream projects upgrading will see updated guidance | Standard seed-update cycle; AC-11 calls out the gate requirement explicitly |
| Heuristic `code_impact path=` documentation change is observable to downstream operators | Add to the wave's release-note candidate list; the diagnostic message keeps the tool useful even where it returns empty |

## Related Work

- Fifth change in wave 130et alongside `130eu` (mcp-server launcher), `130f9` (wave-gate rearchitecture), `130nf` (project-meta layer scoping), `130o2` (transient artifact filter). The first four are small hot-fixes; this one is the wave's largest scope item.
- Verified on this self-hosting repo's own framework graph: 64% of `calls` edges resolve to `external::*` including project-internal `wave_lint_lib.*` symbols. The fix is not Swift-specific — it lands quality improvements for every language using the tree-sitter extractor (14 languages) plus Python (which already mostly works but will gain cross-file resolution).
- Implementation may benefit from coordination with whoever last touched the seed-180 / seed-211 graph-tool guidance — the reporter's note that "guidance is currently inverted" suggests the seeds promise navigation quality the extractor doesn't deliver.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
