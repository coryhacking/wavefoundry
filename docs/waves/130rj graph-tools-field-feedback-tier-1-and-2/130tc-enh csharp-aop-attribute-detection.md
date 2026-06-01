# C# AOP Attribute Detection — Extend `caller_pattern: "advice"` to C# Method-Boundary Aspects

Change ID: `130tc-enh csharp-aop-attribute-detection`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-01
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Change 6 (`130rj-enh aop-advice-empty-incoming-detection`) shipped advice detection for Java methods annotated with `@Advice.OnMethodEnter` / `@Around` / `@Before` / `@After` etc. — pulled from Aceiss's ByteBuddy/AspectJ codebase. The same architectural shape exists in C#: PostSharp, Castle DynamicProxy, MethodBoundaryAspect, and ASP.NET filters all decorate methods with `[Attribute]`-style markers whose actual invocation is wired at runtime by the AOP framework. Operators investigating those methods see the same misleading symptom as Aceiss reported for Java: empty incoming + a useless `code_references` fallback because the runtime weaving has no C# call sites.

This change extends Change 6's detection to C#. The AST shape differs:

- **Java**: `method_declaration` → `modifiers` (child) → `marker_annotation` / `annotation` (children)
- **C#**: `method_declaration` → `attribute_list` (sibling of `modifiers`) → `attribute` (children)

Both expose a `name` field on each annotation/attribute node. The downstream `caller_pattern: "advice"` detection logic in `code_callhierarchy_response` already reads a generic `annotations` field on the node payload; this change just teaches the graph extractor to populate that field for C# the way it already does for Java, and extends the advice-tail recognition set with the canonical C# attribute names.

## Requirements

1. **`_ts_extract_csharp_attributes` helper** in `graph_indexer.py` walks `method_declaration` / `class_declaration` children for `attribute_list` nodes, iterates each list's `attribute` children, reads the `name` field of each, and returns the names verbatim.
2. **`register_symbol` calls the helper for C#** when `lang_key == "csharp"`, populating the existing `annotations` field on the node payload (same field name Java uses, for downstream parity).
3. **`code_callhierarchy_response` advice-tail set extended** with canonical C# AOP attribute names: `OnEntry`, `OnExit`, `OnSuccess`, `OnException`, `OnMethodBoundaryAspect`, `MethodBoundaryAspect`, `MethodInterceptionAspect`, `OnMethodInvokeAspect`, `AroundAdvice`, `BeforeAdvice`, `AfterAdvice`.
4. **Recovery-hint message is language-aware**: when the matched advice tails include a C# name, the hint cites PostSharp / Castle DynamicProxy and uses `glob='**/*.cs'`; otherwise the existing Java framing remains. The detection branches on the matched tail set, not on the queried symbol's file path (a Java-named symbol querying advice attributes is unusual but the test boundary is the tail set).
5. **Tests** cover: attribute extraction at the graph layer (marker, attribute-with-arguments, multiple-attributes), false-positive guard (method without attributes omits the field), and end-to-end advice-pattern detection through `code_callhierarchy_response` with a C#-tailored recovery hint.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py`: `_ts_extract_csharp_attributes` helper + `register_symbol` extension to invoke it for C#.
- `.wavefoundry/framework/scripts/server_impl.py`: advice-tail set extension with C# attribute names + language-aware recovery hint branching.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`: 4 attribute-extraction tests + 1 end-to-end advice-pattern test.

**Out of scope:**

- F# / VB.NET attribute detection. Defer; .NET ecosystem outside C# is operator-reportable territory.
- `[FilterAttribute]` style ASP.NET filters. Same architectural shape as `[Aspect]` attributes but operators rarely query MVC filters via callhierarchy; defer until operator reports surface the need.
- Castle DynamicProxy `IInterceptor` interfaces (the runtime-interception side of the framework) — those use interface dispatch rather than attribute decoration. Outside the AOP-attribute model this change targets.

## Acceptance Criteria

- [x] AC-1: `_ts_extract_csharp_attributes` returns a list of attribute names from `method_declaration`'s `attribute_list` children. Single attribute, multiple attributes, and attributes-with-arguments all produce the bare name.
- [x] AC-2: When `lang_key == "csharp"`, `register_symbol` calls the helper and attaches the result as `node_map[node_id]["annotations"]` (same field name as Java for downstream parity).
- [x] AC-3: `code_callhierarchy_response` advice-tail set includes the 11 C# AOP attribute names listed in Requirement 3.
- [x] AC-4: Recovery hint branches on whether matched tails include any C# names. C# case cites PostSharp / Castle DynamicProxy and uses `glob='**/*.cs'`; Java case is unchanged.
- [x] AC-5: New tests cover attribute extraction (4 cases) + end-to-end advice-pattern detection (1 case). All existing tests continue to pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `_ts_extract_csharp_attributes` to `graph_indexer.py`
- [x] Update `register_symbol` to populate `annotations` for C#
- [x] Extend advice-tail set in `code_callhierarchy_response`
- [x] Add language-aware recovery-hint branching
- [x] Add 5 regression tests
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Attribute extraction is the foundation; without it AC-2 has nothing to attach |
| AC-2 | required | Graph-layer tag propagation; without it the server-layer detection has no input |
| AC-3 | required | The detection trigger set — the headline operator-facing change |
| AC-4 | required | Language-aware recovery hint is the actually-useful guidance; Java-framed hint on a C# project would be misleading |
| AC-5 | required | Regression coverage + no existing-test regressions |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Reuse the existing `annotations` node field for C# attributes | Same downstream consumer (advice-pattern detection) reads the field; using one name for both languages avoids a parallel `attributes` field. Slight terminology stretch (C# calls them "attributes" not "annotations") but the field name is internal-only | Add a parallel `attributes` field for C# (rejected — duplicates the same data flow with a parallel field name; complicates downstream consumers) |
| 2026-06-01 | Branch recovery hint on matched-tail set, not on file extension | The matched tails are the actual signal of which framework the operator is using. File extension is an indirect proxy. If a C# attribute somehow ended up on a `.java` file (impossible in practice but defensively), the hint would still match the framework operators actually use | Branch on `.cs` vs `.java` in source_file (rejected — indirect; the tail set is the authoritative signal) |
| 2026-06-01 | Land as separate change `130tc` in the same wave rather than amending Change 6 | Stage-gate hygiene: Change 6's scope and AC contract were Java-only; adding C# is a new scope dimension. Operator direction confirms in-wave addition is preferred for this kind of paired-language extension | Amend Change 6's ACs (rejected — change-doc rewrite confuses the audit trail; new doc captures the new scope clearly) |

## Risks

| Risk | Mitigation |
|---|---|
| The C# advice-tail set may miss framework-specific attributes (e.g. PostSharp's `[OnMethodBoundaryAspect]` is canonical but a project might use a custom `[MyCompanyAspect]` subclass) | The set is operator-extensible per project via a follow-up if reports surface; the canonical set covers the dominant frameworks at change time |
| Recovery-hint branching by matched-tail set could fire the Java hint on a C# method with non-canonical attribute names (e.g. someone writes `[Around("...")]` in C#) | `Around` is in BOTH sets (Java and C#); the branching detects ANY C# name, so a method with `[Around]` AND `[OnMethodBoundaryAspect]` would correctly fire the C# hint. The pathological case (a C# method with only Java-style names) is rare; the Java framing would still tell the operator about runtime-weave callers, just with the wrong framework citation |
| Attribute extraction adds index-time cost for C# files | Per-method cost is one `attribute_list` walk — same shape as Java's `modifiers` walk. Negligible |

## Related Work

- Extends `130rj-enh aop-advice-empty-incoming-detection` (Change 6) to C#. Both use the same `annotations` node field and the same advice-pattern-detection block in `code_callhierarchy_response`.
- Same wave: Changes 1, 2, 4, 5, 5b, 6, 130r7, and `130tc-enh kotlin-reference-resolution` (companion language extension; both 130tc changes share the lifecycle prefix because they were authored in the same time bucket).

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
