# Java `method_reference` Nodes Are Not Classified as `call_sites` (Aceiss §1.2)

Change ID: `130r7-bug java-method-reference-call-sites`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Aceiss field feedback §1.2 reported that `code_callhierarchy` returns `line: null, snippet: null` for Java incoming (caller) edges while Python and JS/TS callers include line and snippet. The report attributed the symptom to a Java extractor inconsistency and suggested either wiring Java through the same pipeline as Python or adding an explicit `line_available: false` flag.

Reproducer + diagnosis (2026-05-31): the bug is concrete and language-specific to Java 8+ method-reference syntax (`Helper::process`, `this::process`, `ClassName::staticMethod`).

In `_tree_sitter_reference_kind` at `server_impl.py:8420-8430`, the algorithm walks up the AST from the identifier node looking for an ancestor whose type is in `_TS_CALL_PARENT_TYPES[lang]`. For Java this set is `{"method_invocation", "object_creation_expression"}`.

For `h.process()` (traditional method invocation):
- Identifier `process` → parent `method_invocation` ✓ → classified as `call_sites`.

For `Helper::process` (method reference):
- Identifier `process` → parent `method_reference` ✗ → falls through → classified as `mention`.

`_scan_call_sites_in_file` filters references by `reference_kind == "call_sites"`, so method-reference call sites are dropped. The incoming entry survives with `line: null, snippet: null` because the attribution loop (`code_callhierarchy_response` lines 9230–9245) never finds a matching ref for that caller.

This bites hardest on AOP/Java/ByteBuddy codebases (Aceiss's exact case) because instrumentation declarations heavily use method references (`agentBuilder.advice(Method::onEnter, advice_class)` patterns).

The Aceiss-suggested fallback (`line_available: false` flag) is a useful diagnostic surface but doesn't actually fix the bug — the correct fix is to recognize method references as call sites. The same pattern applies to other languages with method-reference / member-function-pointer syntax (Kotlin `::`, Scala `_`, C# `nameof`/method group).

## Requirements

1. `_TS_CALL_PARENT_TYPES["java"]` expanded to include `method_reference` so identifiers nested in `Foo::bar` resolve as `call_sites`.
2. Same treatment for other languages whose grammars expose a method-reference / function-reference shape:
   - **Kotlin**: `callable_reference` (e.g. `String::length`).
   - **Scala**: `partial_application` if exposed (rare in practice); deferred unless tested fixture surfaces a concrete case.
   - **C#**: `name_of_expression`, `member_access_expression` already covered by existing `invocation_expression` ancestors; verify and add only if a concrete gap is found.
3. Tree-sitter AST inspection of each language's method-reference grammar before adding to the set, so the change doesn't over-broaden classification (e.g. matching identifiers in unrelated `*_reference` nodes).
4. Regression test in `test_server_tools.py` that synthesizes a two-file Java project with a method reference (`Helper::process`) and asserts the incoming entry carries non-null `line` and `snippet`.
5. Confirm Python and JS/TS behavior is unchanged (those paths use different extractors / don't hit this code).

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py`:
  - `_TS_CALL_PARENT_TYPES["java"]` gains `method_reference`.
  - `_TS_CALL_PARENT_TYPES["kotlin"]` gains `callable_reference` if a tree-sitter-kotlin inspection confirms the grammar uses that node name.
  - Inspection (and addition if applicable) for C# / Scala / others surveyed in the diagnosis.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`:
  - New regression test for Java method-reference call-site attribution (uses tree-sitter-java; skips if unavailable in test env).
  - Optional Kotlin parallel test if `callable_reference` is added (skips if `tree_sitter_kotlin` unavailable).

**Out of scope:**

- Adding `line_available: false` to incoming entries when attribution genuinely can't find a line. Defer — the method-reference fix resolves Aceiss's reported symptom; a fallback diagnostic field can be added in a follow-up wave if other shapes of attribution failure surface.
- General audit of every language's reference-kind classification. The reproducer scopes Java + Kotlin; broader audit lands in a separate change if other operators surface gaps.
- Changes to the attribution algorithm in `code_callhierarchy_response`'s incoming branch (the algorithm is correct given correctly-classified refs).

## Acceptance Criteria

- [x] AC-1: `_TS_CALL_PARENT_TYPES["java"]` includes `method_reference`. A synthetic two-file Java project where caller B uses `Helper::process` (method reference) — and that's the ONLY way it references `process` — returns non-null `line` and `snippet` on the incoming entry for the `process` symbol.
- [x] AC-2: Tree-sitter-kotlin inspection performed at implementation time (2026-05-31): Kotlin's grammar exposes `callable_reference` for `String::length` / `::myFn` / `this::handle` patterns. Adding it to `_TS_CALL_PARENT_TYPES["kotlin"]` is dead-code without first adding Kotlin to `_TREE_SITTER_REFERENCE_LANGS` + `_TS_IDENTIFIER_NODE_TYPES` + `_TS_DEFINITION_PARENT_TYPES` (Kotlin tree-sitter reference resolution is not currently enabled at all). Deferred to a separate follow-up that activates Kotlin reference resolution end-to-end; documented in the `_TS_CALL_PARENT_TYPES` comment so the parallel addition is obvious when the broader Kotlin work lands.
- [x] AC-3: Existing Java traditional-call attribution (`h.process()` style) continues to work — no regression.
- [x] AC-4: Python and JS/TS attribution paths unchanged (verified by existing tests continuing to pass).
- [x] AC-5: New regression test in `test_server_tools.py` exercises a Java method-reference fixture end-to-end through `code_callhierarchy_response`.
- [x] AC-6: All existing framework tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `method_reference` to `_TS_CALL_PARENT_TYPES["java"]`
- [x] Inspect tree-sitter-kotlin grammar; add `callable_reference` (or equivalent) to `_TS_CALL_PARENT_TYPES["kotlin"]` if confirmed
- [x] Survey C# / Scala / other tree-sitter languages for analogous method-reference shapes; add only if a concrete reproducer shape exists
- [x] Add regression test for Java method-reference call-site attribution
- [x] Optional Kotlin regression test if AC-2 added a Kotlin entry
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline Java fix that closes Aceiss §1.2 |
| AC-2 | important | Kotlin has the same syntax pattern; preemptive coverage prevents the same bug surfacing later |
| AC-3 | required | No regression on existing traditional-call paths |
| AC-4 | required | No regression on other languages |
| AC-5 | required | Regression coverage for the load-bearing fix |
| AC-6 | required | No existing tests regress |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Fix the classification, not add `line_available: false` flag | The method-reference fix actually resolves the reported symptom (caller becomes attributable). A diagnostic-only flag would let agents know "no line available" without changing the underlying gap — operators still couldn't find the call site | Add `line_available: false` as a fallback (deferred — does not address the root cause, retains the original friction) |
| 2026-05-31 | Diagnose via grammar inspection before adding multiple languages | The tree-sitter grammar for each language uses different node names for method-reference syntax. Adding the wrong name silently produces no-op coverage; verifying via AST dump confirms the right name | Add suspected node names by analogy to other grammars (rejected — error-prone) |
| 2026-05-31 | Defer attribution-algorithm changes | The current attribution algorithm correctly handles the call sites it sees. The bug is in *which* AST nodes get classified as call sites, not in how they're attributed once classified. Touching the algorithm broadens the change without benefit | Rewrite attribution to fall back to "any line in the caller function" when no specific call site is found (deferred — would mask future classification gaps instead of fixing them) |

## Risks

| Risk | Mitigation |
|---|---|
| Adding `method_reference` could over-broaden classification, treating non-call identifiers nested in references as call sites | The `method_reference` AST node specifically contains the method-name identifier; both children are intentional call targets. The expansion is narrow and safe |
| Kotlin / other languages may have method-reference node types that differ from Java's `method_reference` and aren't added in this change | AC-2 explicitly inspects each grammar before adding. The change ships Java first; other languages follow if their grammars confirm the same shape |
| Aceiss's reported symptom could have multiple causes; this change might fix the dominant case but leave residual failure modes | The reproducer (in this change doc's Rationale) maps exactly to method references. If other failure modes surface in their follow-up validation, they get scoped as additional bugs in separate changes |

## Related Work

- Wave 130rj sibling changes: tool-shape consistency (community_id, pagination, hop attribution, community overview), code_ask fast_mode, generated-code classifier, AOP/advice empty-incoming detection, seed updates.
- The AOP/advice change (`130rj-enh aop-advice-empty-incoming-detection`) handles the genuine-empty case for advice-annotated methods. This change handles the case where Java methods DO have callers but the call-site classifier missed the syntax.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
