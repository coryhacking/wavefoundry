# Overload Self-Edge Misreads as Recursion

Change ID: `1p2td-bug overload-self-edge-misreads-as-recursion`
Change Status: `implemented`
Owner: Engineering
Status: in-progress
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

When a method has multiple overloads sharing one qualified name, the graph merges them into a single node keyed on that qname (per-file). A call from one overload to another then renders as a `calls` self-edge on the merged node — the edge is real and correctly attributed `RECEIVER_RESOLVED`, but the self-loop framing can mislead consumers into reading it as recursion.

Reproduction from javaagent / Solaris (Swift, `AutomationController.calculateScheduledTime`): a 3-param convenience overload's body is a single forwarding call to a 4-param implementation overload. `code_impact(symbol="calculateScheduledTime", max_hops=2)` returns an edge whose `source == target` (`AutomationController.calculateScheduledTime → AutomationController.calculateScheduledTime`). The edge is correct; the consumer-visible framing isn't.

The same shape appears in every overloading language. Java/C#/Kotlin/Swift/Scala/C++ all permit multiple declarations under one qname distinguished by signature; the framework's per-file qname-keyed node merge applies to all of them. A bare self-edge says nothing about whether the call resolves to the enclosing overload (recursion) or a different overload (forwarding).

The interpretation problem is real for downstream reviewers. seed-211's recipes use `code_impact` and `code_callhierarchy` self-edges as a "this function recurses" signal. On overload-rich codebases that signal is unreliable today.

A purely-cosmetic fix (doc note saying "self-edges on overloaded methods are usually overload-forwarding") is available, but the correct fix is to surface the distinction structurally on the edge itself. Then reviewer recipes can trust the data without operator knowledge of which symbols happen to be overloaded.

## Approach

The distinction lives on the **edge**, not the node — keeping the node-merge behavior intact (caller aggregation via "who calls this name" is the right default for `code_callhierarchy`).

**Mechanism — purely syntactic, no full type-checker required:**

1. At extraction time, capture a per-overload **parameter signature** for every definition that lands on a node which other overloads will merge into.
2. Track the **enclosing overload's signature** through the call walker so the source side of a self-edge knows which overload it came from.
3. At the call site, extract a **call signature** (arg labels for Swift; arg count + named-arg labels for the rest).
4. When the call edge would be a self-edge (`source == target`), compare:
   - `call_signature == enclosing_signature` → `self_edge_kind: "recursion"`
   - `call_signature` matches a *different* overload registered on the same node → `self_edge_kind: "overload_forwarding"`
   - Otherwise (no signature data, or same-arity-different-types overload ambiguity) → `self_edge_kind: "unknown"`
5. Stash the per-overload signature list on the merged node payload as `param_signatures` so consumers can read the overload set directly.

**Cross-language signature shape:**

| Language | Signature form | Rationale |
|---|---|---|
| Swift | Argument labels (`base:offset:customTime:`) | Native syntax — disambiguates the common convenience-wrapper case |
| Java | Argument count + ordered modifier tags (`arity:3`) | Positional language; arity is the cheapest reliable signal |
| Kotlin | Arity + named-arg labels when present (`arity:3` or `arity:3,name:value:`) | Mixed positional + named |
| C# | Arity + named-arg labels when present (`arity:3` or `arity:3,name:value:`) | Mixed positional + named |
| Scala | Arity + named-arg labels when present | Mixed positional + named |
| C++ | Arity (`arity:3`) | Positional only |

Same-arity-different-types overloads (`f(x: Int)` vs `f(x: String)`) cannot be distinguished without type-checking the argument expressions. The correct behavior in that case is `self_edge_kind: "unknown"` — explicit honest-uncertainty is strictly better than today's silent "every overload-forward looks like recursion."

The framework's existing receiver-type resolver could in principle resolve argument types and disambiguate the ambiguous overloads. We do not pursue that here because (a) the convenience-wrapper case is the overwhelmingly common one and arity alone handles it, and (b) plumbing the type resolver into call-arg disambiguation is a separate, larger change.

## Requirements

1. Per-overload parameter signatures are extracted at definition time for Swift, Java, Kotlin, C#, Scala, C++.
2. The set of signatures for a merged node is preserved across the per-file qname merge (no signature data is lost when the second overload registers under the same node_id).
3. `walk_calls` tracks the enclosing overload's signature in scope so call edges know which overload is the source.
4. Call sites carry a derived signature for matching: Swift label-fingerprint; other languages arity-fingerprint (with optional named-arg labels appended where present).
5. When `source_id == target_id` on a `calls` edge, the edge gains a `self_edge_kind` field whose value is one of: `"recursion"`, `"overload_forwarding"`, `"unknown"`.
6. The merged node payload carries `param_signatures: [<sig>, …]` listing every overload's signature (deduped and sorted for stable serialization).
7. No behavior change on non-overloaded methods: a self-edge on a node with only one registered signature is `"recursion"` (the enclosing-overload check succeeds trivially).
8. Languages without overloading (Python, JavaScript, Go, Rust, PHP) do not gain the field; current self-edge behavior unchanged (Python self-edges always read as recursion, correctly).
9. `code_impact`, `code_callhierarchy`, `code_callgraph`, `code_graph_path` responses pass the new edge field through unchanged — no special handling at the tool layer.
10. seed-211 documents the new `self_edge_kind` semantics so reviewer recipes can use it.

## Scope

**Problem statement:** Self-edges on per-file qname-merged overload nodes are indistinguishable from recursion in today's graph. Reviewer recipes that interpret `code_impact` / `code_callhierarchy` self-edges as a "this function recurses" signal are unreliable on overload-rich codebases.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — per-language `_extract_param_signature(node, source_bytes)` helpers for Swift, Java, Kotlin, C#, Scala, C++; per-call `_extract_call_signature(call_node, source_bytes, lang_key)` helper; walker scope tracking; self-edge tagging at emission; `param_signatures` field on merged nodes
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — per-language fixtures covering the Swift `base:offset:` case, Java arity case, C#/Kotlin named-arg cases, recursion-on-non-overloaded base case, unknown-case (same-arity different-types)
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — note the new `self_edge_kind` field and how reviewer recipes should consume it
- `.wavefoundry/framework/scripts/graph_query.py` — no change needed (edge fields pass through unchanged); verify

**Out of scope:**

- Type-inference disambiguation of same-arity-different-types overloads. `"unknown"` is the right answer there; closing that gap is a separate larger change that would require routing the receiver-type resolver into argument expressions.
- Signature-keyed graph nodes (fragmenting overloads into separate nodes). Explicit non-goal per the field report — name-merging is the correct default for caller aggregation, so the fix lives at the edge layer.
- TypeScript / JavaScript overload coverage. TypeScript has overload signatures + one implementation; in practice all overload calls dispatch to the same implementation body, so the call_target resolver already collapses correctly. JS lacks overloading entirely. No change for those languages.

## Acceptance Criteria

- [x] AC-1: `_extract_param_signature` helpers exist for Swift, Java, Kotlin, C#, Scala, C++; each returns a stable string given the same definition AST.
- [x] AC-2: For a Swift convenience-wrapper overload (`f(a, b)` body calls `f(a, b, c)`), the emitted self-edge carries `self_edge_kind: "overload_forwarding"`.
- [x] AC-3: For a Swift recursive call (`f(a, b)` body calls `f(a, b)` with the same labels), the emitted self-edge carries `self_edge_kind: "recursion"`.
- [x] AC-4: For a Java method whose body calls a different-arity overload of the same name, the emitted self-edge carries `self_edge_kind: "overload_forwarding"`.
- [x] AC-5: For a Java method whose body calls itself recursively, the emitted self-edge carries `self_edge_kind: "recursion"`.
- [x] AC-6: For a same-arity-different-types overload pair (`f(x: Int)` vs `f(x: String)` in Kotlin/Scala/C#), the emitted self-edge carries `self_edge_kind: "unknown"` rather than guessing.
- [x] AC-7: For a non-overloaded Python or JavaScript method, no `self_edge_kind` field is emitted on self-edges (current behavior unchanged).
- [x] AC-8: Merged node payload carries `param_signatures: [<sig>, …]` listing every overload's signature, deduplicated and sorted.
- [x] AC-9: `code_impact`, `code_callhierarchy`, `code_callgraph`, `code_graph_path` responses surface the new edge field unchanged. **Post-ship correction (2026-06-02 javaagent field validation on 1.3.7+p2th):** `code_callhierarchy`'s `outgoing` / `incoming` entries are constructed via `_node_entry(target_id)` which reads the *target node* — the edge's `self_edge_kind` metadata was lost in this construction, so consumers reading `outgoing`/`incoming` lists did not see the classification. Fixed by propagating `e["self_edge_kind"]` from the underlying edge into the entry dict on both branches; covered by `test_self_edge_kind_propagates_to_outgoing_entry` and `test_self_edge_kind_propagates_to_incoming_entry` in `test_server_tools.py`.
- [x] AC-10: seed-211 documents the `self_edge_kind` semantics with a one-line note in the response-shape interpretation section.
- [x] AC-11: All existing 2,200 framework tests pass without modification.

## Tasks

- [x] Open `framework_edit_allowed` gate (verify still open)
- [x] Add per-language `_extract_param_signature(node, source_bytes)` helpers — Swift first, then Java, Kotlin, C#, Scala, C++
- [x] Add `_extract_call_signature(call_node, source_bytes, lang_key)` helper
- [x] Add `overload_signatures: dict[str, set[str]]` accumulator + per-file plumbing in `_extract_tree_sitter_artifact`
- [x] Track `scope_signatures` parallel to `scope_symbols` in `walk_calls`
- [x] At call emission: detect self-edges; compute call signature; compare against scope signature; tag edge `evidence.self_edge_kind`
- [x] Surface `param_signatures` on the merged node payload (sorted, deduped)
- [x] Open `seed_edit_allowed` gate; update seed-211; close gate
- [x] Add regression tests per AC-2 through AC-8
- [x] Run framework tests
- [x] Close framework gate; mark change `implemented`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| signature-extractors | Engineering | — | Per-language helpers; can land per-language incrementally |
| walker-scope-tracking | Engineering | signature-extractors | Threads scope_signatures through walk_calls |
| edge-tagging | Engineering | walker-scope-tracking | Self-edge detection + classification at emission |
| node-param-signatures | Engineering | signature-extractors | Surface signatures on merged node payload |
| seed-211 | Engineering | edge-tagging | Documentation, blocked on the field shape being stable |
| tests | Engineering | edge-tagging, node-param-signatures | Per-language regression coverage |

## Serialization Points

- `_extract_tree_sitter_artifact` is the integration point — all per-language code paths flow through it. The `overload_signatures` dict and the `scope_signatures` stack must be threaded consistently across the definition walker and the call walker before any language ships its tagging logic.

## Affected Architecture Docs

N/A — the change is confined to the per-file extractor and its produced edge payload. No boundary, flow, or verification-architecture change. Edge shape is purely additive (new optional field on a subset of edges).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Per-language extractors are the foundation; without them no tagging works |
| AC-2 | required | Swift convenience-wrapper case is the field-reported reproducer |
| AC-3 | required | Recursion baseline must distinguish cleanly from overload-forwarding |
| AC-4 | required | Java arity-based fingerprint must work — Java is the highest-volume overloading language in field codebases |
| AC-5 | required | Same Java baseline check for recursion |
| AC-6 | required | Honest "unknown" is the explicit design choice; must verify it lands rather than a wrong guess |
| AC-7 | required | No regression on non-overloading languages |
| AC-8 | important | Operator-visible signature list on the merged node enables manual disambiguation |
| AC-9 | required | Tool-layer pass-through — no special handling needed |
| AC-10 | required | Reviewer recipes need the documented semantics to use the field correctly |
| AC-11 | required | No baseline regression |

## Related Work

- Field-feedback report from javaagent / Solaris team (2026-06-02 follow-up).
- The "node-merge by qname" behavior originates from [[1316l]] / [[1319o]] (class/module merge + `collapsed_pair`). This change adds edge-level disambiguation without touching the merge logic itself.
- Pairs with [[1p2tf]] (TS receiver-type resolution via imports) in the same wave round — both improve attribution honesty at the call-edge layer for different language families.

## Risks

| Risk | Mitigation |
|---|---|
| Argument-label extraction in tree-sitter differs subtly per language (Swift exposes labels as field-names on `value_argument`; C#/Kotlin expose them as `simple_name :` pairs) | Per-language extractors + per-language tests cover the variants explicitly; if a language's tree-sitter grammar changes shape on an SDK bump, the test fixtures catch the regression |
| Same-arity-different-types overloads landing as `"unknown"` could be perceived as a regression by consumers who expected a definitive answer | The change doc explicitly frames `"unknown"` as the honest answer; seed-211 notes the case so reviewer recipes don't read `"unknown"` as a coverage gap |
| Scope_signatures threading adds complexity to walk_calls | Reviewed against existing walker patterns; the additional list runs parallel to scope_symbols and follows the same push/pop discipline |
