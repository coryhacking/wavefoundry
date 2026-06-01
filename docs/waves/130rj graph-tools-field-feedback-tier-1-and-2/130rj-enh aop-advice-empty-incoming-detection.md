# AOP/Advice Empty-Incoming Detection — `caller_pattern: "advice"` + Recovery Hint

Change ID: `130rj-enh aop-advice-empty-incoming-detection`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Aceiss field feedback §2.3 / §4.2 documented that when `code_callhierarchy` returns empty incoming for a Java method annotated with `@Advice.OnMethodEnter`, `@Advice.OnMethodExit`, `@Around`, `@Before`, `@After`, `@AfterReturning`, or `@AfterThrowing`, the result is *expected* (the callers are wired at weave time by ByteBuddy/AspectJ — no Java call sites exist). Agents currently have no way to distinguish "this symbol has no callers" from "this symbol's callers are runtime-woven." The existing fallback guidance (use `code_references` when `code_callhierarchy` is empty for Java) is *actively misleading* for advice methods because `code_references` also returns nothing useful.

The seed-180 / seed-211 corrections in `130rj-enh seeds-pattern-library-and-recipes` give agents the right verbal rule. This change adds the API surface so agents can detect the case from the response itself: the `code_callhierarchy` response carries `caller_pattern: "advice"` when the queried method is annotated with one of the recognized advice annotations and incoming is empty. A recovery-hint diagnostic points the agent at the correct fallback (`code_keyword` on the advice class name scoped to instrumentation files).

This requires the graph extractor to track annotation presence on Java method nodes. The current Java extractor walks `method_declaration` and `class_declaration` nodes but does not capture annotation strings. A small extension to `_extract_tree_sitter_artifact` records annotation names on each method node; the response handler reads those when deciding whether to emit `caller_pattern`.

## Requirements

1. **Annotation capture during graph extraction.** When extracting Java `method_declaration` nodes, capture the names of any `marker_annotation` or `annotation` children whose name matches the recognized advice set (`Advice.OnMethodEnter`, `Advice.OnMethodExit`, `Around`, `Before`, `After`, `AfterReturning`, `AfterThrowing` — match by trailing segment so `@org.aspectj.lang.annotation.Around` matches `Around`). Store as `annotations: list[str]` on the node payload.
2. **`code_callhierarchy_response` detects the advice pattern** when:
   - `direction` includes `incoming`
   - `incoming` (after filtering external and dedupe) is empty
   - The resolved `node_id`'s graph node carries any of the recognized advice annotations
3. **Response emits `caller_pattern: "advice"`** and a diagnostic with `code: "advice_pattern_detected"` and a recovery-hint message: `"The queried method is annotated as AOP advice (@Advice.OnMethodEnter/@Around/etc.). Callers are wired at weave time and have no Java call sites. Search for the registration: code_keyword(queries=[<advice_class_name>], glob='**/*Instrumentation*.java')"`.
4. **No false positives**: only emit `caller_pattern: "advice"` when incoming is empty. A method that IS an advice method AND has Java callers (rare, but possible if the advice is also invoked directly) gets normal incoming + no `caller_pattern` flag.
5. **No regressions**: Python / non-Java symbols never carry `caller_pattern`. Java methods without advice annotations don't carry it. The field is omitted from the response when not applicable.
6. **Regression tests** cover: synthetic Java fixture with an advice-annotated method that has no callers → response carries `caller_pattern: "advice"` + diagnostic; synthetic Java fixture with an advice-annotated method that DOES have a Java caller → no `caller_pattern` flag (just normal incoming).
7. **`GRAPH_BUILDER_VERSION` bump** so existing graph caches re-extract with annotation tracking. (Shared bump with `130rj-enh generated-code-classifier-and-filters` if landing in the same session.)

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py`:
  - Java `method_declaration` extraction extended to capture annotation strings.
  - Constant `_JAVA_ADVICE_ANNOTATION_TAILS` (frozen set of trailing segments).
  - Annotation list attached to node payload as `annotations: list[str]`.
  - `GRAPH_BUILDER_VERSION` bump (shared with companion change if in-session).
- `.wavefoundry/framework/scripts/server_impl.py`:
  - `code_callhierarchy_response` reads the resolved node's `annotations` field and detects the advice pattern when incoming is empty.
  - Emits `caller_pattern: "advice"` and the recovery diagnostic.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`:
  - Regression test: Java method annotation extraction (`@Advice.OnMethodEnter void onEnter() { ... }` → node carries `annotations: ["Advice.OnMethodEnter"]`).
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`:
  - Regression test: synthetic Java fixture with advice method + no callers → `caller_pattern: "advice"`.
  - Regression test: synthetic Java fixture with advice method + one Java caller → no `caller_pattern` flag.
  - Regression test: non-advice Java method with empty incoming → no `caller_pattern` flag.

**Out of scope:**

- AspectJ-specific annotations beyond the canonical set (`@Pointcut`, `@DeclareParents`, etc.). Defer — the recognized set covers the dominant ByteBuddy + AspectJ + Spring AOP shapes.
- New tool `code_advice_sites` to find advice registration sites directly (Aceiss §3.1 / Tier 3 — separate future wave).
- Non-Java AOP frameworks (Kotlin Around-style, Python decorators that wire at runtime). Defer — Java/ByteBuddy is the canonical case.

## Acceptance Criteria

- [x] AC-1: Java `method_declaration` extraction captures annotation tails matching `_JAVA_ADVICE_ANNOTATION_TAILS = frozenset({"Advice.OnMethodEnter", "Advice.OnMethodExit", "Around", "Before", "After", "AfterReturning", "AfterThrowing"})`. Match is by the last dotted segment of the annotation name (handles `@org.aspectj.lang.annotation.Around` ↔ `@Around`).
- [x] AC-2: Captured annotations land on the graph node as `annotations: list[str]`. Nodes with no advice annotations omit the field (or carry `annotations: []`).
- [x] AC-3: `code_callhierarchy_response` reads the resolved node's annotations. When `incoming` is empty AND the resolved node has any annotation in the advice set, response emits `caller_pattern: "advice"` and a diagnostic of code `advice_pattern_detected` with a recovery-hint message pointing at `code_keyword` scoped to instrumentation files.
- [x] AC-4: When `incoming` is non-empty, no `caller_pattern` flag is emitted (even on advice methods).
- [x] AC-5: Non-advice Java methods with empty incoming get no `caller_pattern` flag.
- [x] AC-6: Python and other non-Java symbols never carry `caller_pattern`.
- [x] AC-7: `GRAPH_BUILDER_VERSION` bumped so existing graphs re-extract with the annotation tracking.
- [x] AC-8: All existing framework tests pass. New regression tests cover annotation extraction + the three `caller_pattern` scenarios above.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Inspect tree-sitter-java grammar to confirm the AST node names for annotations on method declarations
- [x] Add `_JAVA_ADVICE_ANNOTATION_TAILS` constant
- [x] Extend Java `method_declaration` extraction to capture matching annotation tails
- [x] Attach `annotations` field to node payload
- [x] Bump `GRAPH_BUILDER_VERSION`
- [x] Update `code_callhierarchy_response` to detect the advice pattern and emit `caller_pattern` + diagnostic
- [x] Add regression tests for annotation extraction
- [x] Add regression tests for the three response scenarios (empty incoming + advice, non-empty incoming + advice, empty incoming + non-advice)
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The annotation classifier — must match all canonical advice annotations |
| AC-2 | required | The propagation to node payload — without it AC-3 can't fire |
| AC-3 | required | The headline response signal Aceiss requested |
| AC-4 | required | Defensive: no false positives when callers exist |
| AC-5 | required | Defensive: no false positives on non-advice methods |
| AC-6 | required | No regression on other languages |
| AC-7 | required | Cache invalidation so the new tracking surfaces on upgrade |
| AC-8 | required | Regression coverage + no existing-test regressions |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Match annotations by trailing segment (`Around` matches `org.aspectj.lang.annotation.Around`) | Annotations in Java can be fully-qualified or imported. The canonical advice set is unambiguous by tail (no other common Java annotation is named `OnMethodEnter`) | Match full-qualified names (rejected — requires import-resolution logic to be useful) |
| 2026-05-31 | Only emit `caller_pattern: "advice"` when incoming is empty | If callers exist, the agent gets normal navigation evidence. The pattern flag is specifically for the "graph correctly shows empty, but it's not empty in the runtime sense" case | Always emit the flag on advice methods (rejected — operators investigating an advice method that DOES have a direct caller want to see the caller, not be redirected to instrumentation files) |
| 2026-05-31 | Recovery hint uses `code_keyword` scoped to `**/*Instrumentation*.java` | The Java/ByteBuddy convention is `<Name>InstrumentationModule.java` / `<Name>Instrumentation.java`. The glob captures the dominant project-naming pattern; operators with different conventions still get the advice-class name and can adapt | Recovery hint uses `**/*.java` (rejected — too noisy in large repos). Recovery hint names a specific tool surface (`code_advice_sites`) that doesn't exist yet (deferred to Tier 3) |
| 2026-05-31 | Capture annotations only on Java method nodes for now | The canonical case is Java + ByteBuddy + AspectJ. Spring AOP also uses `@Around`/`@Before`/`@After` on Java methods so it's covered. Other languages' AOP frameworks deserve separate analysis before adding | Capture annotations on all languages (rejected — broader scope, low signal-to-noise outside Java) |

## Risks

| Risk | Mitigation |
|---|---|
| Annotation extraction adds index-time cost on Java files | Per-method overhead is one annotation-list scan; negligible compared to existing extraction work |
| The fixed annotation set ages out if new AOP frameworks introduce different names | The constant is easy to extend; operator-reported gaps trigger additions in future changes |
| False positives if a non-AOP Java codebase happens to use `@Around` for an unrelated purpose | The flag only fires on empty incoming — if the annotation is truly unrelated AOP and the method has callers, the flag doesn't fire. If incoming is empty for a non-AOP `@Around`, the agent gets a recovery hint pointing at instrumentation files — they'll find nothing there and fall through to the existing reference fallback. Cost is one wasted lookup; benefit on actual ByteBuddy codebases is significant |
| Aceiss codebases may use annotations not in the canonical set (custom `@Advisor`-style) | Out-of-scope for this change. If Aceiss reports a specific custom annotation in follow-up testing, add it in a small follow-up change |

## Related Work

- Companion to `130rj-enh seeds-pattern-library-and-recipes` (seed-side rule: "AOP advice exception: don't fall back to code_references"). The seeds carry the rule; this change carries the API surface so agents can detect the case from the response.
- Aceiss §3.1 proposes a new `code_advice_sites` tool. This change closes the symptom (empty incoming + misleading fallback); the new tool would be a more powerful follow-up that returns registration sites directly. Tier 3 follow-up wave.
- Same wave: `130rj-enh graph-tool-shape-consistency`, `130rj-enh code-ask-fast-mode`, `130rj-enh generated-code-classifier-and-filters`, `130r7-bug java-method-reference-call-sites`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
