# Go Cross-File Method Resolution (`Type.method` Keying + `qualified_type` Receivers)

Change ID: `1p4et-enh go-cross-file-method-resolution`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-06-09
Wave: 1p4eq cross-file-resolution-followups

## Rationale

Go cross-file method resolution is the keystone of the follow-on wave: it is a precondition for `1p4ev`'s Go membership-based disambiguation, and **every other Go fix is inert without it** (per the `1p47e` investigation ranking in the `1p4ef` plan, Related section). The `1p47e` 3-language deep-dive found Go method resolution fails at two distinct points, both verified against source:

1. **Methods are not keyed by receiver type.** Go `method_declaration` nodes register through the generic `walk_definitions` → `register_symbol` path (`graph_indexer.py:5676-5683`, `register_symbol:5525`). The qname is `".".join([*scope_names, name])` (`:5681`). Because Go methods are **top-level siblings** of their type (not lexically nested inside it like Java/C#), `scope_names` is empty, so a method `func (h Helper) Process()` registers as **qname `Process`, id `file::Process`** — never `Helper.Process`. Meanwhile `_resolve_go_call_target` (`:2653`) builds `qualified = f"{receiver_type}.{method_name}"` → `Helper.Process` (`:2675`) and probes `symbol_lookup[qualified]` (`:2676`). That key **never exists**, so the probe **always misses** and the call falls through to `external::Helper.Process` (`:2678`). The receiver resolver works; the symbol table it queries is mis-keyed. As a secondary harm, two same-method-name types in one file (`func (a Alpha) Run()` + `func (b Beta) Run()`) both register id `file::Run` and **collide to one node** in `simple_names`/`symbol_lookup`, losing one definition entirely.

2. **`qualified_type` receivers return `None`.** The dominant cross-package shape is `var h foo.Helper; h.Process()`. `_resolve_go_receiver_type` (`:2625`) → `_resolve_go_identifier_type` (`:2608`) → `_search_go_declarations_in_scope` (`:2555`) walks `var_spec`/`parameter_declaration` children but only recognizes `type_identifier` and `pointer_type` (`:2569`, `:2589`). A `var_spec` whose type is `qualified_type` (`foo.Helper`) or `pointer_type→qualified_type` (`*foo.Helper`) is **never matched** — `type_child` stays None and the function returns None (`:2605`), so `receiver_type` is None and `_resolve_go_call_target` returns None (`:2673-2674`), dropping the call before it can resolve.

This change is **synthetic-validated only — no team tested Go** in the `1.6.0+p4ea` test pack — so scope coverage is claimed strictly to the synthetic tests below (a deliberate correction of the `1p470` over-claim, where C#/Go/Rust were declared resolved without passing tests).

## Requirements

1. Go `method_declaration` nodes must register with qname `Type.method` (receiver type prepended), where `Type` is the simple type from the method's receiver `parameter_list` (handling pointer receivers `*Helper`). The node **label** stays the bare method name; the id becomes `file::Type.method`. This flows into `symbol_lookup` and (via the cross-file rewrite pass) `qualified_index` automatically, so `_resolve_go_call_target`'s existing `f"{receiver_type}.{method_name}"` probe matches without changing the resolver's probe shape.
2. Two same-method-name Go types in one file (`Alpha.Run` + `Beta.Run`) must register as **two distinct nodes** (`file::Alpha.Run`, `file::Beta.Run`), not collide to one `file::Run`.
3. `_search_go_declarations_in_scope` must resolve `qualified_type` receivers (`var h foo.Helper`) and pointer-to-qualified (`var h *foo.Helper`) by returning the **trailing `type_identifier`** of the `qualified_type` (the local simple type name, e.g. `Helper`), so the `var h foo.Helper; h.Process()` cross-package shape yields `receiver_type=Helper`.
4. The shared wave `GRAPH_BUILDER_VERSION` bump covers this change (Go method ids change shape: `file::Process` → `file::Helper.Process` — a node-shape change that invalidates consumer caches). **Do NOT bump per-change** — the wave coordinates ONE bump across all `graph_indexer.py` changes; this change contributes its rationale line to that single bump.
5. Coverage claims are scoped to **Go only** and only to behaviors with a passing synthetic test. No claim is made about cross-package resolution that requires membership disambiguation (that is `1p4ev`, which depends on this change).

## Scope

**Problem statement:** Go method calls do not resolve cross-file because (a) methods register under their bare name, so the `Type.method` key the resolver probes never exists (and same-named methods collide), and (b) the scope resolver ignores `qualified_type` receivers, the dominant cross-package shape — together leaving idiomatic Go method calls stuck at `external::Type.method`.

**In scope:**

- Receiver-type keying for Go `method_declaration` registration in `walk_definitions` (`graph_indexer.py:~5676-5683`): a Go-specific qname adjustment that prepends the receiver type. Implemented via a new small helper `_go_method_receiver_type(method_decl_node, source_bytes)` that extracts the receiver type from the method's own receiver `parameter_list` (mirroring the extraction in `_find_enclosing_go_method_receiver_type:2524`, but taking the `method_declaration` node directly rather than walking up from a call site).
- `qualified_type` (and `pointer_type→qualified_type`) receiver handling in `_search_go_declarations_in_scope` (`graph_indexer.py:~2569`, `~2589`) for both `var_spec` and `parameter_declaration`, returning the trailing `type_identifier`.
- The shared-wave `GRAPH_BUILDER_VERSION` bump rationale line (node-shape change) — landed once for the wave.
- Synthetic regression tests: a cross-file Go method call resolving to the project node; a same-method-name no-collision assertion; a `var h foo.Helper` qualified-receiver test.

**Out of scope:**

- Membership-based cross-package disambiguation for Go (`1p4ev` — depends on this change). This change makes the `Type.method` key exist; resolving across packages when the type is ambiguous is `1p4ev`'s job.
- Go import-substrate hygiene / import-head extractor cleanup (folded into `1p4ev`'s per-language import-head work).
- Selector-chain / field / return-value receivers (`s.client.Do()`, `getThing().M()`), `:=` short-var-from-function-return type inference, and static-style `pkg.Func()` package-function calls — all deferred (require inter-procedural type-flow; phantom-prone per all three `1p47e` analyses).
- C#, Rust, Java, and all other languages — unaffected by this change.

## Acceptance Criteria

- [x] AC-1: A Go `method_declaration` `func (h Helper) Process()` registers as node id `<file>::Helper.Process` with label `Process` and kind `function`; `symbol_lookup` contains key `Helper.Process` → that id. Pointer receiver `func (h *Helper) Process()` registers identically (`Helper.Process`, not `*Helper.Process`). Verified by a unit test inspecting `nodes` + `symbol_lookup` (via a built graph payload).
- [x] AC-2: Cross-file resolution — two files, `a.go` defines `func (h Helper) Process() int` (type `Helper` defined in `a.go`), `b.go` has a function that does `var h Helper; h.Process()`. The call edge from the `b.go` caller resolves to `a.go::Helper.Process` at `RECEIVER_RESOLVED` confidence, **not** `external::Helper.Process`. Verified via the `_assert_cross_file` harness (or an inline equivalent for the `var h Helper` body shape).
- [x] AC-3: No collision — a single file with `func (a Alpha) Run()` and `func (b Beta) Run()` produces **two** distinct project nodes (`file::Alpha.Run` and `file::Beta.Run`); neither is dropped. Verified by asserting both ids exist in `nodes`.
- [x] AC-4: `qualified_type` receiver — `var h foo.Helper; h.Process()` resolves: `_search_go_declarations_in_scope` returns `Helper` (the trailing `type_identifier`) for `h`, so `_resolve_go_receiver_type` yields `Helper` and the call resolves to the project `Helper.Process` node (with `Helper.Process` present in `symbol_lookup`). Pointer-to-qualified `var h *foo.Helper` resolves identically. Verified by a unit test (resolver-level or full-graph). [SUPERSEDED by 1p4eq faithfulness fix: now returns package-qualified `foo.Helper` and resolves by candidate package-dir; returning bare `Helper` was the wrong-twin bug.]
- [x] AC-5: No regression — existing Go tests `test_go_cross_file_call_resolves_to_project_node` (bare cross-file `Foo()` function call), `test_go_builtins_stay_external_when_called`, and the Go keyword-leak assertion (`graph_indexer` tests ~790-836) still pass; full `run_tests.py` + docs-lint green.
- [x] AC-6: `GRAPH_BUILDER_VERSION` is bumped exactly once for the wave (this change contributes the Go node-shape-change rationale line); the rebuilt self-host graph carries the new version and is non-empty.

## Tasks

- [x] Add `_go_method_receiver_type(method_decl_node, source_bytes)` helper near the Go resolvers (`graph_indexer.py:~2524`), extracting the receiver type from the `method_declaration`'s first `parameter_list` (handle `pointer_type→type_identifier`); return `None` if no receiver type.
- [x] In `walk_definitions`, after computing `name`/`qname` for a definition (`:5677-5681`), add a Go-specific branch: when `lang_key == "go"` and `node_type == "method_declaration"` and `scope_names` is empty, prepend the receiver type — `qname = f"{recv}.{name}"` when `_go_method_receiver_type` returns a type. Leave plain `function_declaration` (no receiver) unchanged. Confirm `label` (`register_symbol:5560`, `qname.rsplit(".", 1)[-1]`) correctly yields the bare method name.
- [x] Extend `_search_go_declarations_in_scope` (`:2569`, `:2589`): accept `qualified_type` in the `type_child` match for both `var_spec` and `parameter_declaration`; when `type_child` is `qualified_type` (or `pointer_type→qualified_type`), return the trailing `type_identifier`. Mirror the existing pointer-unwrap branch (`:2575-2578`, `:2595-2598`).
- [x] Add the three synthetic tests (AC-2 cross-file method call, AC-3 same-name no-collision, AC-4 `var h foo.Helper`) to `test_graph_indexer.py`, guarded by `tree_sitter_go` import skip (matching `:792`).
- [x] Contribute the Go node-shape-change rationale to the shared-wave `GRAPH_BUILDER_VERSION` bump; rebuild the self-host graph; run `run_tests.py` + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| go-method-keying | Engineering | — | `_go_method_receiver_type` helper + `walk_definitions` Go method branch (`graph_indexer.py:~2524`, `~5677-5683`); changes node id shape `file::Process` → `file::Type.method` |
| go-qualified-receiver | Engineering | — | `_search_go_declarations_in_scope` `qualified_type` handling (`graph_indexer.py:~2569`, `~2589`); independent of keying but both needed for AC-4 |
| regression-tests | Engineering | go-method-keying, go-qualified-receiver | AC-2/3/4 synthetic tests in `test_graph_indexer.py`; AC-5 no-regression on existing Go tests |
| version-bump + rebuild | Engineering | go-method-keying, go-qualified-receiver | Contributes Go rationale to the **single** shared-wave `GRAPH_BUILDER_VERSION` bump; rebuild self-host graph |

## Serialization Points

- `GRAPH_BUILDER_VERSION` (`graph_indexer.py:28`) is a **wave-shared** serialization point: this change, `1p4ef`, `1p4et`, `1p4eu`, and `1p4ev` all alter graph contents/shape — the wave coordinates **one** bump. Do not bump independently; land the bump last, after all wave `graph_indexer.py` changes merge.
- `walk_definitions` registration path (`:5676-5696`) and `register_symbol` (`:5525`) are touched by the Go-keying branch; coordinate with any other wave change that edits the same registration block.
- `_search_go_declarations_in_scope` (`:2555`) is shared between this change's receiver-resolution path and `1p4ev`'s Go membership work — land this change first (`1p4ev` depends on it).
- The cross-file rewrite pass `qualified_index` (`:6322-6351`) consumes the new `Type.method` ids; verify after `1p4ef`'s leaked-`qualified` fix lands (the phantom-candidate fix is a trust precondition for the `len == 1` guard that promotes these ids).

## Affected Architecture Docs

N/A — this is a correctness/coverage improvement to existing per-language receiver-resolution and symbol-registration machinery; no module boundary, control-flow, or verification-architecture change. (If `docs/architecture/graph-index-system.md` is being edited for the wave's other improvements, a one-line note that Go methods are keyed `Type.method` — unlike the lexically-nested keying of Java/C# — would fit, since Go's top-level-method shape is the reason the generic path mis-keys.)

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | P0 | The keystone — without `Type.method` keying the resolver probe never matches; all downstream Go resolution and `1p4ev` membership depend on it. |
| AC-2 | P0 | The headline behavior: idiomatic cross-file Go method call resolves to a project node. Proves AC-1 end-to-end. |
| AC-3 | P0 | Same-name collision silently drops a definition (data loss); the keying change must demonstrably fix it, not just mask it. |
| AC-4 | P1 | The dominant cross-package shape (`var h foo.Helper`). High-value but distinct from keying; resolution of the ambiguous cross-package case is `1p4ev`, so this AC asserts the resolver returns the right local type, not full cross-package binding. |
| AC-5 | P0 | No-regression gate on the existing passing Go tests — the node-shape change is invasive enough to break bare-function resolution if mis-scoped. |
| AC-6 | P0 | Cache-correctness — without the shared bump, consumers read stale `file::Process` ids and resolution silently regresses on upgrade (per the framework's graph-builder-version-bump guardrail). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Go-keying branch leaks into non-method Go definitions (`function_declaration`, types) or other languages, mis-prefixing qnames. | Gate strictly on `lang_key == "go"` AND `node_type == "method_declaration"` AND empty `scope_names`; `_go_method_receiver_type` returns `None` for receiver-less nodes → fall back to bare name. AC-5 regression test on `test_go_cross_file_call_resolves_to_project_node` (a `function_declaration`) confirms bare functions are untouched. |
| Node-shape change (`file::Process` → `file::Helper.Process`) breaks consumers that key on the old bare-method id, or `_simple_name` / `simple_names` behavior shifts. | `label` (`register_symbol:5560`) still yields the bare method name via `rsplit(".",1)[-1]`, so display/search surfaces are unchanged; `simple` registered in `simple_names` is the `Type.method` simple form, which is exactly what enables the no-collision fix (AC-3). Shared `GRAPH_BUILDER_VERSION` bump forces a full rebuild so no consumer reads mixed-shape ids. |
| `qualified_type` handling over-matches (e.g. picks the package identifier `foo` instead of the type `Helper`, or mis-handles `pointer_type→qualified_type`). | Return the **trailing** `type_identifier` of the `qualified_type` (the last identifier is the type; the leading one is the package). AC-4 asserts `Helper` (not `foo`) for both `foo.Helper` and `*foo.Helper`; mirror the existing pointer-unwrap pattern (`:2575-2578`). [1p4eq faithfulness fix: the package is now PRESERVED by design — `_go_simple_type_name` returns `foo.Helper`, and the rewrite pass resolves by the candidate's package directory; dropping the package bound a co-located cross-package twin.] |
| Over-claiming Go cross-package resolution beyond what tests prove (the `1p470` failure mode). | Scope coverage explicitly to Go and to AC-1–AC-4 synthetic tests; cross-package ambiguous resolution is left to `1p4ev` and not claimed here. The `var h foo.Helper` test uses a single same-named project type so the resolution is unambiguous without membership disambiguation. [1p4eq faithfulness fix: the package qualifier is now PRESERVED by design — cross-package resolution binds only the candidate whose package directory matches `foo` and stays external otherwise.] |
| Phantom `qualified_index` candidates (the `1p4ef` bug) suppress the newly-keyed `Type.method` resolution via the `len == 1` guard. | Sequence after `1p4ef` (precondition); the no-regression rebuild + AC-2 run on the post-`1p4ef` tree confirms the new ids resolve through a clean `qualified_index`. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-09 | Implementation complete. Go `method_declaration` keyed `Type.method` via the `walk_definitions` Go branch (`graph_indexer.py:5794-5797`) + `_go_method_node_receiver_type` (`:2593`); `_go_simple_type_name` (`:2555`) now package-PRESERVING (`qualified_type` → `foo.Helper`) and `_search_go_declarations_in_scope` (`:2624,:2640`) infers qualified-receiver types. AC-4 SUPERSEDED by the 1p4eq adversarial-verification faithfulness fix: the resolver no longer drops the package to bare `Helper` (which bound a co-located cross-package twin — wrong RECEIVER_RESOLVED edge); it returns `foo.Helper` and a new Go block in the cross-file rewrite pass (`:6589-6615`) resolves by the candidate's package directory, staying external when no project package matches. | Tests `test_go_cross_package_method_resolves`, `test_go_same_method_name_types_do_not_collide`, plus faithfulness tests `test_go_qualified_receiver_binds_named_package_not_colocated_twin` + `test_go_qualified_receiver_unknown_package_stays_external` (CrossFileResolutionTests); AC-5 regressions `test_go_cross_file_call_resolves_to_project_node` + `test_go_builtins_stay_external_when_called` green. Full suite 2960 tests OK; graph builder version=25 (one consolidated wave bump). |
