# Callee Names Come From the AST Leaf, Not the Callee Text

Change ID: `1xtns-bug callee-name-from-ast-leaf-for-chained-and-arrow-receivers`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-09-14
Wave: 1xtnr call-edge-target-integrity

## Rationale

While probing the receiver-candidate defect planned in `1xtnq`, the same probe over all fourteen tree-sitter code profiles on builder 51 exposed a second, independent defect in the generic call fallback: the callee candidate is derived from the raw text of the whole callee expression, and `_ts_clean_name` (`graph_indexer.py:3131-3153`) keeps only the first run matching `[A-Za-z_][A-Za-z0-9_.$:#/\-]*`. Any character outside that class cuts the name off before the invoked member is reached, and the `-` inside the class swallows half of an arrow operator. Measured on builder 51 (`_ts_clean_name` then `_ts_resolve_target` with empty tables):

| Callee text | Candidate today | Correct callee | Grammars affected |
| --- | --- | --- | --- |
| `b.subject().authenticatedUser` | `b.subject` | `authenticatedUser` | TS, JS, Go, Rust, Scala, C#, C, C++ |
| `e->getKey` | `e-` | `getKey` | C, C++, PHP |
| `$b->subject()->authenticatedUser` | `b-` | `authenticatedUser` | PHP |
| `foo?.bar` | `foo` | `bar` | TS, JS, C# (`x?.Y`) |
| `x!.y` | `x` | `y` | TS |
| `obj.method<T>` | `obj.method` | `obj.method` (correct by luck; generics follow the name) | TS |

The consequences are two-sided. The outer member of every chained call is **lost** as an edge, and in its place the inner call's name is emitted a second time, so `b.subject().authenticatedUser()` emits the inner candidate twice and no outer candidate. The edge map deduplicates identical keys, so persisted graphs may hold only one inner edge. Arrow and optional-chain receivers yield the receiver base (`foo`, `x`), which is the `1xtnq` family again by a different route, or a garbage token (`e-`, `b-`, `this-`) that mints a phantom `external::e-` node. Java, Kotlin, Swift, Ruby and Objective-C are not affected because their grammars expose the member name as a direct field of the call node, or because the positional extractor already walks to the rightmost identifier.

Every affected grammar exposes the invoked member as a named field on the callee expression, so the repair needs no text parsing: TS/JS `member_expression.property`; Go `selector_expression.field`; Rust `field_expression.field` and `scoped_identifier.name`; Scala `field_expression.field`; C# `member_access_expression.name` and `member_binding_expression.name` under `conditional_access_expression`; C and C++ `field_expression.field` and `qualified_identifier.name`; PHP `member_call_expression.name` and `scoped_call_expression.name`. The module already has `_ts_extract_callee_recursive`, which walks navigation nodes to the rightmost identifier for the positional path (Swift, Kotlin); the field-name path never uses it.

Local census on this repository (Python and JS): zero `calls` edges target an `external::...-` truncation, so the arrow class is invisible here. The chained-call class is present on this repository's JS and on every consumer graph in Go, Rust, Scala, C#, C, C++ and PHP.

## Requirements

1. **Structural leaf, not text.** In `_ts_relation_candidates` for `relation="call"` in code mode, when the callee field (`function`, `callee`) holds a member-like expression, the callee candidate SHALL be derived from that expression's member-name FIELD (`property` for TS/JS, `field` for Go, Rust, Scala, C and C++, `name` for C# `member_access_expression` and `member_binding_expression`, PHP `member_call_expression` and `scoped_call_expression`, and C++ `qualified_identifier`), not from `_ts_clean_name` over the expression's text. `_ts_extract_callee_recursive` is the fallback only for callee shapes with no member-name field, and before it can serve that role `property_identifier` SHALL join `_TS_IDENTIFIER_TYPES` and C# `conditional_access_expression`/`member_binding_expression` SHALL join `_TS_NAVIGATION_TYPES`; today the walker returns `e` for TS `e.getKey`, `None` for `this.children[0].getValue` and `x` for C# `x?.Y`, so it must not be the primary path. Because widening `_TS_IDENTIFIER_TYPES` also touches the Swift/Kotlin positional path, AC-4 pins those grammars too. The candidate for `b.subject().authenticatedUser()` is `authenticatedUser`; for `e->getKey()` it is `getKey`; for `foo?.bar()` it is `bar`; for `x!.y()` it is `y`; for a subscript receiver `children[0].getValue()` (Go, Rust, C#, C, C++, TS `this.children[0].getValue()`) and Scala `children(0).getValue()` it is `getValue`, never the base `children`. This change owns every shape where the callee TEXT carries an intervening segment; `1xtnq` owns the `object`-field receiver candidate and the Swift bracket refusal.
2. **Plain identifier paths keep their qualifier.** When the callee expression is a pure dotted or scoped identifier path with no intervening call, subscript, arrow, optional-chain, non-null or type-argument node (`a.b.c()`, `ns::fn()`, `A::stat()`, `ClassName.staticMethod()`), the candidate SHALL remain exactly what builder 51 produces, so qualified `symbol_lookup` binds and import-alias binds are untouched. The builder-51 literals, captured before the first edit, are: TS `C.m()` gives `['C.m']`; C++ `ns::fn()` gives `['ns::fn']`; Rust `a::b::c()` gives `['a::b::c']`; C# `Cls.Method()` gives `['Cls.Method']`; Go `pkg.Fn()` gives `['pkg.Fn']`; PHP `A::stat()` already gives the leaf `['stat']` (the grammar exposes `name` directly) and stays so; Java `Cls.method()` gives `['method', 'Cls']` on 51 and `['method']` after `1xtnq` removes the `object` candidate. The rule reduces to the leaf only where a non-identifier segment intervenes, and the pure-path test SHALL be structural, walking the callee expression's `object`/`value`/`argument` chain by node type and inspecting the anonymous `?.` and `!` tokens (a TS `foo?.bar` member expression has a plain-identifier object and only the anonymous `optional_chain` child reveals the segment), never a second regex over the callee text; `_ts_node_text` is decoded at most once per candidate.
3. **One candidate per call node.** A call node SHALL yield exactly one callee candidate on this path (the `1xtnq` receiver rule removes the `object`-field candidate; this change removes the text-derived duplicate), so `b.subject().authenticatedUser()` produces one `subject` edge from the inner call node and one `authenticatedUser` edge from the outer.
4. **No phantom external nodes from operators.** No `calls` edge SHALL target an `external::` id that ends in `-` or contains `->`, `?.`, `!.`, `(`, `[` or `<`. The finalize invariant introduced by `1xtnq` Requirement 5 SHALL be extended with this predicate and its own count, `malformed_external_call_targets_dropped`, expected zero. Unlike the non-callable count, which reports and keeps, this predicate DROPS the edge: an `external::` id ending in `-` or carrying an operator is not a symbol and can never be a true target, so keeping it would only mint a phantom node. Both counters and both dispositions are documented side by side in the finalize paragraph of `graph-index-system.md`.
5. **Confidence stays honest.** A leaf-derived candidate is a receiver-bearing call whose receiver type the per-language resolver did not establish, so under `1xtnq` Requirement 3 it binds at `EXTRACTED` when the bare name is unique in the project and stays `external::<leaf>` otherwise. This change adds no promotion, and preserves the `1xtnq` receiver-unknown provenance so later exact-name cross-file rebinding cannot restore a higher confidence.
6. **Census and version.** The two-sided census from `1xtnq` Requirement 7 SHALL add, per language on the fixtures and on this repository's JS: chained-call outer-member edges present (before: 0 expected; after: one per outer call), duplicate inner-call candidate emissions measured before edge-key deduplication (before: one extra emission per fixture chain; after: 0), and malformed external targets (before and after). This change ships in the same builder-version bump as `1xtnq` (`52`) and adds its own line to the constant's in-code history; it does not bump separately.

## Scope

**Problem statement:** The generic call fallback names the callee from the raw callee text, so any call, subscript, arrow, optional-chain or non-null segment before the invoked member cuts the name off, losing the outer call of every chain and minting garbage external targets from arrow operators.

**In scope:**

- Callee-candidate derivation from the member-name field for TS, JS, Go, Rust, Scala, C#, C, C++ and PHP, with a fixture per grammar for chained, arrow, optional-chain and non-null receivers.
- The pure-path preservation rule and its positive fixtures (`Class.method()`, `ns::fn()`, `A::stat()`).
- The malformed-external-target predicate in the finalize invariant.
- Census columns, in-code version history line, architecture and tool-surface doc updates, CHANGELOG line.

**Out of scope:**

- Typing the receiver of a chained or subscripted call (return type of the inner call, element type of the array); the leaf binds by bare name only.
- The receiver-as-candidate defect, kind gate, promotion gate, Java scope walk and `code_callhierarchy` shape; all `1xtnq`.
- `_ts_clean_name` itself for import candidates and non-call relations; the `-` in its character class exists for package specifiers (`@scope/my-pkg`) and is not changed.
- Ruby `call`/`method_call`/`command`, Kotlin, Swift and Objective-C, which already extract the member name.

## Acceptance Criteria

- [x] AC-1: On fixtures for TS, JS, Go, Rust, Scala, C#, C, C++ and PHP holding `b.subject().authenticatedUser()`, the built graph carries one `subject` edge and one `authenticatedUser` edge from the enclosing function, with no duplicate `subject` edge; on fixtures for Go, Rust, C#, C, C++, Scala and TS holding a subscript receiver `children[0].getValue()` (Scala `children(0).getValue()`), the `getValue` edge is present at `EXTRACTED` and no `calls` edge targets `children`.
- [x] AC-2: On C, C++ and PHP fixtures holding `e->getKey()` and `$b->subject()->authenticatedUser()`, no edge targets an `external::` id ending in `-`, and the `getKey` and `authenticatedUser` edges are present.
- [x] AC-3: On TS/JS fixtures holding `foo?.bar()` and `x!.y()`, and a C# fixture holding `x?.Y()`, the edges target `bar`, `y` and `Y`, not `foo`, `x`.
- [x] AC-4: Pure identifier paths are unchanged: a `_call_candidates` test helper mirroring the existing `_import_candidates` pins the Requirement 2 literal list for TS, C++, Rust, C#, Go, PHP and Java (post-`1xtnq` `['method']`), plus the Swift and Kotlin positional candidates for `helper()` and `e.getKey()`, and the fixtures' binds match builder 51.
- [x] AC-5: The finalize invariant reports `malformed_external_call_targets_dropped` as zero on every fixture and on this repository's rebuilt graph, and a mutation test that restores text-derived arrow candidates proves a non-zero count is dropped and reported; a separate deletion mutant proves the malformed-target guard is necessary.
- [x] AC-6: Every leaf-derived edge on the fixtures carries `EXTRACTED` unless a per-language resolver established the receiver; no `RECEIVER_RESOLVED` edge in the fixture graphs originates from this path.
- [x] AC-7: The census records outer-member edges, duplicate inner candidate emissions and malformed targets before and after, per language; candidate duplication is measured at extraction before deduplication, while unique persisted edges and target counts are re-derived from SQL predicates; this change's own suites and every test it adds pass, the documents this change authors or edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the before-side census columns (outer-member edges, duplicate inner edges, malformed external targets) to the `1xtnq` census run and record them before the first edit.
- [x] Route callee candidates through the member-name field of the callee expression when it is not a structurally pure identifier path; add `property_identifier` to `_TS_IDENTIFIER_TYPES` and the two C# conditional-access types to `_TS_NAVIGATION_TYPES` so `_ts_extract_callee_recursive` is a correct fallback; keep the text path for pure paths.
- [x] Add a `_call_candidates` helper beside `_import_candidates` and record the Requirement 2 builder-51 literals in the Progress Log before the first edit.
- [x] Add per-grammar fixtures for chained, arrow, optional-chain, non-null and subscript receivers, plus the pure-path positive controls pinned through `_call_candidates`.
- [x] Extend the finalize invariant with the malformed-external-target predicate and `malformed_external_call_targets_dropped`, with the AC-5 mutation test.
- [x] Add this change's line to the `GRAPH_BUILDER_VERSION` in-code history under the shared `52` bump.
- [x] Update `docs/architecture/graph-index-system.md` (Call Edge Extraction: callee-name derivation rule) and the CHANGELOG `Unreleased` line shared with `1xtnq`.
- [x] Record the after-side census.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Candidate derivation | implementer | `1xtnq` binding repair | Same function, `_ts_relation_candidates`; lands after the receiver rule |
| Invariant extension | implementer | `1xtnq` finalize invariant | Adds a second predicate and count |
| Census and fidelity | qa-reviewer | Candidate derivation | AC-4 before/after pin, AC-5 mutation, AC-7 census |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `docs/architecture/graph-index-system.md`

## Affected Architecture Docs

- `docs/architecture/graph-index-system.md` — Call Edge Extraction gains the callee-name derivation rule (member-leaf when a non-identifier segment intervenes, full path otherwise).
- `docs/specs/mcp-tool-surface.md` — N/A; no tool shape changes.
- `docs/architecture/data-and-control-flow.md` — N/A; no ownership or flow boundary moves.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reproduced outer-member loss across eight grammars. |
| AC-2 | required | Phantom external nodes from arrow operators. |
| AC-3 | required | Optional-chain and non-null receivers are the same family. |
| AC-4 | required | Qualified binds must not regress; this is the recall-safety control. |
| AC-5 | required | The invariant must be proven to fire. |
| AC-6 | required | No new promotion sneaks in under a recall fix. |
| AC-7 | required | A recall repair must show what it added and what it kept. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-14 | Readback and Observe: operator authorized resuming shipped work for verification and closure. Luna passed 61 focused tests; independent Astra passed 13 controls and killed receiver/kind-gate mutants. Call/citation seams unchanged from prior approved delivery. Consumer 127/57 follow-up received through operator reports: non-callable targets 127 to zero; false receiver binds removed or explicitly EXTRACTED; correct call_site locations. This is reported evidence, not a fresh consumer run. | delivery-review.json closure_verification_20260914; current 9,008-test framework receipt. |
| 2026-09-12 | Implementation complete. Final suite: 8,939 tests, 88 modules, 12 documented skips, 270.943 seconds; green receipt hash independently recomputed and matched. Docs validation and diff whitespace checks pass. Live MCP verifies callee definitions, nested caller snippets and external null values. Graph builder 52 published at generation 1347. Framework edit gate closed; formal delivery review remains next. | implementation-evidence.json final_suite, live_callhierarchy_smoke and final_runtime. |
| 2026-09-12 | Final census: all 15 profiles pass; all nine pure paths and seven opaque/parenthesized-call controls pass. Duplicate inner emissions removed in eight profiles; fixture reads/defines unchanged. Live builder 52 has zero non-callable/malformed targets; callable-target edges 20,223 to 20,301. All 39 removed edges are attributed (one helper call moved into its nested declared function; 38 external hints follow changed candidates in unchanged JS). Consumer 127/57 re-derivation remains pending. Candidate helper benchmark: 2.933 us before, 2.646 us after; this is not whole-build timing. | implementation-evidence.json census_final, comparison, after, final_dispatch_probes and candidate_hotpath_benchmark. |
| 2026-09-12 | Observe: full suite passed 8,938 tests with 12 documented skips. Independent live candidate census then caught two additional JavaScript regressions: IIFE body traversal and lost super calls. Thought: confine the new leaf derivation to member expressions and preserve opaque-call behavior, then rerun final validation. | implementation-evidence.json full_suite_before_final_callee_repair; final census repair evidence follows. |
| 2026-09-12 | Observe: graph implementation complete. Twenty-one focused regressions pass; thirteen omission mutants are detected. Broad graph (549) and incremental (58) suites passed before final narrow repairs; final full suite is running. Independent switch repair recheck passed six tests and its deletion mutant. | implementation-evidence.json graph_implementation and graph_checkpoint_final; tests/test_graph_call_integrity.py. |
| 2026-09-12 | Observe: independent unchanged-corpus comparison detected all three Bash calls lost despite valid parsing; other profiles removed the expected malformed/duplicate targets and pure-path controls passed. Reflect: a no-receiver language still needs nonempty emitted-edge positive controls. Thought: restore the Bash candidate wrapper path and rerun the exact comparison before final publication. | QA comparison.json; module to run, run to helper, helper to echo baseline edges. |
| 2026-09-12 | Readback: derive the outer called member from the AST, preserving pure-path candidates and avoiding duplicate inner-call candidates across fifteen grammars. Thought: apply after 1xtnq receiver gates in graph_indexer, verify candidate and persisted populations separately, and share the single builder-52 refresh. | Current readiness approvals; implementation-evidence.json baseline. |
| 2026-09-12 | Thought: capture before-side evidence before any source edit. Observe: all 15 profiles parse, Java false field targets and PHP/C/C++ malformed targets reproduced; pure-path literals and pre-dedup candidates recorded. Consumer re-derivation remains pending. | `implementation-evidence.json` baseline; builder 51 SHA 7bd82d93b5d053730fcf476bb7b8cdeef866eeb8d4eea71b461d0ea677771149. |
| 2026-09-12 | Operator authorized the full-plan-review repair: measure duplicate candidate emission before deduplication, keep SQL counts for unique persisted edges, and preserve receiver-unknown provenance through final resolution. | `plan-review.json` PR-01 and PR-05. |
| 2026-09-12 | Repaired after the code-reviewer and performance-reviewer lanes (CR-6, PR-4, PR-5): the member-name field is the primary derivation and `_ts_extract_callee_recursive` only a fallback after `property_identifier` and the C# conditional-access types are added to its sets; the pure-path test is structural and inspects anonymous `?.`/`!` tokens; text decoded once per candidate. Measured 1.30 us per call node structural versus 1.17 us text baseline. | Lane probes: walker returns `e`, `None`, `x` on the TS and C# shapes today. |
| 2026-09-12 | Repaired after the prepare council: subscript receivers for text-derived grammars moved here from `1xtnq` (architecture seat), builder-51 candidate literals recorded with PHP already leaf-only and Java's post-`1xtnq` shape (qa seat), and a `_call_candidates` pin helper named. | Seat probe literals listed in Requirement 2. |
| 2026-09-12 | Planned from the `1xtnq` cross-language probe; mechanism confirmed in `_ts_clean_name` and the per-grammar callee AST shapes. | Probe over `_ts_clean_name` / `_ts_resolve_target` and named-field dumps of every affected grammar's callee node on builder 51. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-12 | Derive the callee from the member-name field only when a non-identifier segment intervenes; keep the text path for pure identifier paths. | Pure paths are how qualified binds (`Class.method`, `ns::fn`) and import-alias heads reach `_ts_resolve_target` today, and `_simple_name` deliberately splits at the first dot to avoid over-binding nested leaves; touching that path risks the three regressions its comment records. The leaf rule is needed only where text derivation is already wrong. | **Always take the leaf:** simplest, but drops the qualifier on `Class.method()` and reroutes every qualified bind through the bare-name path, which the `_simple_name` comment shows over-binds. **Patch `_ts_clean_name` to skip `->`, `?.`, `!.` and parenthesised segments:** text surgery that still cannot see a subscript or a nested call boundary, and the `-` in its class is load-bearing for package specifiers. **Type the inner call and resolve the outer member on its return type:** correct but general inference, out of scope for both changes. |
| 2026-09-12 | Share the `52` builder bump with `1xtnq` rather than bump separately. | Both land in one wave on the same extraction path; one re-extraction for consumers. | **Separate bump to 53:** two forced re-extractions for the same wave. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A grammar's member node is not in `_TS_NAVIGATION_TYPES`, so the leaf walk returns the receiver base instead of the member. | One fixture per affected grammar, asserting the exact candidate; the AC-4 pure-path pin catches the inverse regression. |
| The new outer-member edges are bare-name binds and could hit a same-named unrelated project symbol. | They bind at `EXTRACTED` only (AC-6) and the `1xtnq` kind gate refuses non-callable targets; the census reports them as a distinct column. |
| Ordering against `1xtnq` in the same function. | Serialized in the execution graph: this lands after the receiver rule, on the same `_ts_relation_candidates` body. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
