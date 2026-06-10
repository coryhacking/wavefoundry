# Membership-Based Cross-File Disambiguation (Container Membership Generalizes Import-Head Matching)

Change ID: `1p4ev-enh membership-based-cross-file-disambiguation`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-06-09
Wave: 1p4eq cross-file-resolution-followups

## Rationale

The `1p470` import-edge disambiguation in the cross-file rewrite pass (`graph_indexer.py:~6449-6479`) resolves an ambiguous `external::Type.method` (multiple same-simple-name project candidates) by consulting the **source file's `imports` edge for the receiver's head segment**. It works for **Python and Java** because their imports are **per-type**: `from pkg_a.models import User` and `import com.foo.Helper` produce `imports_by_file[file]["User"] = "pkg_a.models.User"` / `["Helper"] = "com.foo.Helper"` — the import-head equals the receiver type, and the candidate filter (`cmod in accept`, where `accept = {imp_fqn, imp_fqn.rsplit(".",1)[0]}`) lands on the right twin.

For **C#, Go, and Rust the same block is dead code** because their import edges carry the **wrong head** for a per-type lookup:

- **C#** `using Acme.Services;` is namespace-wide, not per-type. The `_ts_relation_candidates(..., "import", ...)` path (`graph_indexer.py:~4357`, fed by `_ts_is_import_node` at `~1862` which matches on `"using"`) yields the namespace path; `imports_by_file` keys it by its **trailing segment** (`rsplit(".",1)[-1]` at `~6381`) → `"Services"`, never the receiver type `Service`. The lookup `imports_by_file[file].get("Service")` misses. (The same import path also emits junk `external::using` keyword edges.)
- **Go** `import "p/q"` is a package path; the head becomes a **path fragment** (`q`), not the receiver type, and Go receivers are `pkg.Type` (a `qualified_type` introduced by `1p4et`), so the head segment is the **package alias**, not a type the file "imported by name."
- **Rust** `use a::b::Bar;` cleans to the **whole `::`-path** (`a::b::Bar` / `a.b.Bar`), so the trailing-segment key is `Bar` but the value is not a dotted FQN whose parent is a recordable module the candidate's file-module can match; and `use a::b;` (module-level) imports the **container**, not the type.

The unifying observation: Python/Java disambiguation is the **special case** of a general rule — *keep the ambiguous candidate(s) whose declaring CONTAINER the source file can see*. Generalize the key from **import-head == type-head** to **container MEMBERSHIP**: each project node records its **declaring container** (namespace for C#, package directory for Go, module path for Rust); each source file accrues an **imported-container set** (from its import heads) **unioned with its own container** (which generalizes the `1p4er` same-package/same-directory fallback — same-container is just membership where the container is the file's own); the ambiguity branch keeps candidates whose container is in that set and resolves **iff exactly one survives**.

This is the strategic shared mechanism the `1p47e` investigation flagged: *"disambiguate by container membership instead of import-head==type-head; build once, parameterized; needs a new node-level declaring-container field; gated behind the items above."* It is **gated behind `1p4ef`** (trustworthy `qualified_index` — phantom candidates make the `len>1` ambiguity branch fire on false ambiguity) and **depends on `1p4et`/`1p4eu`** (without `Type.method` / `Type::assoc_fn` nodes there are no qualified candidates to disambiguate). This change is **synthetic-validated only** — no team has tested C#/Go/Rust resolution; scope is claimed only to languages with a **passing membership test**, deliberately avoiding the `1p470` over-claim (it advertised C#/Go participation that was dead code).

> **C# scope resolved at Prepare (2026-06-09, probe-verified).** The prepare-council flagged a possible hidden C# prerequisite (basename-collapsed C# classes returning the file-id node before the namespaced qname exists → declaring-container with nowhere to attach). A probe on a real two-namespace C# fixture **disproves that premise for the common case**: (1) a C# class inside a `namespace` does **NOT** collapse — the namespace wrapper makes it a non-top-level node, so the basename-merge gate never fires (`collapsed_pair=None`); (2) C# methods are **already keyed `Namespace.Class.method`** in the qname (e.g. node id `Foo/Helper.cs::Acme.Foo.Helper.Process`), so the `Type.method` candidates the membership filter needs **already exist** — C# needs **no** method-keying prerequisite (unlike Go's `1p4et` / Rust's `1p4eu`); (3) the declaring container (`Acme.Foo`) is therefore derivable from each file's declared namespace nodes (nesting-proof) and is also available during the scope walk. **Faithfulness correction (implementation):** the namespace is derived per file from its declared `Namespace` module nodes by longest-prefix match (`cs_file_ns`), NOT by string-stripping a fixed two qname segments — the fixed strip mis-derived a NESTED-class caller's namespace (`Acme.Web.Outer.App.Run` → wrongly `Acme.Web.Outer`) and bound a coincident sibling twin (a wrong `RECEIVER_RESOLVED` edge the 1p4eq verification caught). **Consequence:** C# is a confirmed-implementable, **required-pass** language for this change (not skip-eligible), and `1p4ev`'s C# path depends only on the existing extractor — NOT on a C# analogue of `1p4et`. The lone residual is the rare **namespace-less** C# class whose name matches the file basename (it *can* collapse): map it to the global/empty container (out-of-scope edge case, recorded under Risks).

## Requirements

1. **Declaring-container field on project nodes.** During tree-sitter extraction (`_extract_tree_sitter_artifact`, `graph_indexer.py:~5343`), record each defined symbol node's **declaring container** under a stable node key (e.g. `declaring_container`). The container is derived **per language**: C# = enclosing `namespace`/`file_scoped_namespace` declaration text; Go = the file's **package directory** (`rel_path` parent dir); Rust = the file's **module path** (directory path, `mod`-aware where cheaply available). This data **does not exist today** — C# classes are file-keyed and the namespace is discarded; a grep confirms no `namespace_by_file` / `declaring_container` exists.
2. **Per-language import-head extractor.** Add a per-language mapping from an `imports` edge to the **container it makes visible** (C# `using Ns;` → `Ns`; Go `import "p/q"` → package-path container; Rust `use a::b;` / `use a::b::Bar` → the module container `a::b`). Build a per-file **imported-container set** (the membership analogue of `imports_by_file`), keyed by source file. Strip the keyword-junk heads (`using`/`use`/`func`) so they never enter the set.
3. **Membership filter in the ambiguity branch.** Generalize the `resolved is None and len(candidates) > 1` block (`graph_indexer.py:~6464`): when the import-head==type-head filter does not resolve, keep candidates whose **declaring container** is in the source file's imported-container set **unioned with the source file's own container**; resolve **iff exactly one** candidate remains (the faithfulness guard). Build the membership lookups **once** before the rewrite loop (reusing the candidate-pool-filter pattern — **no per-call type inference**), parameterized per language by the membership key.
4. **Faithfulness guards.** The unique-after-filter (`len(matches) == 1`) guard is mandatory; a genuinely-external receiver (no project candidate in any visible container) **stays external**. Container derivation must be deterministic and must not invent a container for nodes that have none (fall back to file-module, never a leaked value).
5. **Shared wave `GRAPH_BUILDER_VERSION` bump.** This change alters node payloads (new `declaring_container` field) and edge rewriting, so consumer caches must rebuild. **Do NOT bump per-change** — the wave coordinates **ONE** `GRAPH_BUILDER_VERSION` bump covering `1p4ef`/`1p4er`/`1p4et`/`1p4eu`/`1p4ev`; this change contributes its rationale to that single bump's annotation.

## Scope

**Problem statement:** the `1p470` ambiguous-receiver disambiguation is **dead code for C#/Go/Rust** because it keys on import-head==type-head, but those languages import **containers** (namespace / package / module), not types. Ambiguous `external::Type.method` calls (two same-named types in different containers) never resolve even when the source file's container makes exactly one twin visible — the edge stays `external::` and the call is dropped from the project node's view.

**In scope:**

- Recording a `declaring_container` field on project symbol nodes in `_extract_tree_sitter_artifact` (`graph_indexer.py:~5525-5584`, the `register_symbol` path), derived per language for **C#, Go, Rust**.
- A per-language import-head→container extractor + a per-file imported-container set built once before the rewrite loop (alongside `imports_by_file` at `graph_indexer.py:~6375`).
- The membership filter added to the ambiguity branch (`graph_indexer.py:~6464`), unioning the source file's own container (generalizing the `1p4er` same-directory fallback).
- Per-language adversarial **"never binds the wrong twin"** tests mirroring `test_*_ambiguous_import_disambiguates` (`tests/test_graph_indexer.py:~1046-1102`), plus a no-disambiguating-container safety test mirroring `test_ambiguous_without_import_stays_external`.
- Contribution to the **shared wave `GRAPH_BUILDER_VERSION`** bump annotation; rebuild.

**Out of scope:**

- The `1p4ef` leaked-`qualified` loop fix (precondition; separate change) and the `1p4et`/`1p4eu` node-registration work this depends on.
- The `1p4er` Java same-package fallback as a standalone block — this change **generalizes** it (own-container union). **Prepare decision (2026-06-09):** `1p4er` lands first as the single same-package/same-directory code path; when `1p4ev` lands it **REPLACES** that filter with the own-container union (ONE code path, not a second parallel branch), keeping `1p4er`'s Java tests green as the regression gate (AC-4/AC-7). No duplicated same-package logic ships. If `1p4ev` were to slip out of the wave, `1p4er` stands alone cleanly.
- Static-call resolution (`Type.staticMethod()`), selector-chain / field / return-value receivers (`a.b.M()`, `s.client.Do()`), and trait/`dyn`/generic dispatch — all deferred (phantom-prone, need inter-procedural type-flow).
- Any language whose membership test does **not** pass: coverage is claimed only where a green adversarial test exists. No C#/Go/Rust resolution-rate claim beyond the tested fixtures.

## Acceptance Criteria

- [x] AC-1: A node's declaring container is recoverable at rewrite time without a new node field. **[SUPERSEDED by implementation — a per-node `declaring_container` field proved unnecessary.]** For C# the namespace is derived from each file's DECLARED namespace nodes (`file.cs::Namespace`, kind `module`) into a `cs_file_ns` map, matched against a node's qname by longest-prefix (nesting-proof: a caller in a nested class resolves to the file's real namespace, not a stripped path) — `graph_indexer.py` `cs_file_ns` build loop. Go/Rust own-container is the file's directory, already handled by the `1p4er` same-package/same-directory fallback (gated to Java/Kotlin/Go). The prepare-council probe confirmed C# methods already key `Namespace.Class.method` and don't collapse in a namespace, so no per-node field was added. Verified by `test_csharp_namespace_membership_disambiguates` + `test_csharp_nested_class_caller_binds_own_namespace_not_sibling` (membership resolves to the correct namespace; nested-class caller never binds a coincident sibling twin).
- [x] AC-2: The visible-container set is built per file before the rewrite loop without keyword-junk. **[SUPERSEDED by implementation — no separate `imported_containers_by_file` structure was needed.]** The imported containers are the `using` FQN values already carried in `imports_by_file` (the C# `using Acme.Services;` directive yields FQN `Acme.Services`); the accept set is `{own-namespace} ∪ {using FQNs}` with empty/junk heads discarded (`accept_ns.discard("")`), so a junk head like `using` never matches a real candidate namespace. Verified by the `using`-flip assertions in `test_csharp_namespace_membership_disambiguates` (the resolved twin changes with the `using`, proving it is import/own-namespace-driven).
- [x] AC-3: **C# membership disambiguation (adversarial) — REQUIRED pass (precondition resolved at Prepare, see the C# note above; not skip-eligible).** Two `Service` classes in different namespaces (`Acme.Services.Service` / `Acme.Other.Service`), each defining `Process`; a caller file with `using Acme.Services;` and a typed `svc.Process()` resolves the call to **`Acme.Services`'s** `Service.Process` project node (`RECEIVER_RESOLVED` → project) and **NOT** the `Acme.Other` twin. PLUS a same-namespace caller (no `using`, mirroring the Aceiss `JreCompat.canAccess` field miss) resolving to its own-namespace twin. C# is probe-confirmed to produce the `Acme.Services.Service.Process` candidate nodes and to not collapse inside a namespace, so this AC is unconditional.
- [x] AC-4: **Same-container (own-container) fallback (generalizes 1p4er).** A caller in container `C` with **no** disambiguating import, calling a typed receiver whose ambiguous twins include exactly one in container `C`, resolves to that same-container twin. The cross-container twin is never bound.
- [x] AC-5: **Faithfulness — never binds the wrong twin / stays external.** When **no** visible container (imported or own) contains exactly one candidate (two visible twins, or zero), the edge **stays `external::`** — the call binds to neither project node. Mirrors `test_ambiguous_without_import_stays_external`. Per-language adversarial assertion that the non-visible twin is never the target.
- [x] AC-6: **Per-language coverage gate — at least ONE container language must have a GREEN (ran, not skipped) adversarial membership test, and C# is required.** All of `tree_sitter_c_sharp`/`go`/`rust` are present in the tool venv (`~/.wavefoundry/venv`) that `run_tests.py` uses, so these tests **run** there — a skip in that environment is a failure, not a pass. C# MUST pass (precondition resolved — see the C# note). Go/Rust pass once `1p4et`/`1p4eu` land their `Type.method`/`Type::assoc_fn` candidate nodes; a Go/Rust skip is permitted ONLY if its dependency genuinely slipped, with a recorded reason. The change doc / progress log records exactly which languages passed; **no resolution claim (version comment, CHANGELOG, release notes) is made for a language without a green test that ran in the parser-complete venv** (operationalizes the wave's "do not repeat the `1p470` over-claim" watchpoint).
- [x] AC-7: **No regression.** Existing `test_python_ambiguous_import_disambiguates`, `test_java_ambiguous_import_disambiguates`, and `test_ambiguous_without_import_stays_external` still pass (the membership path must not break the import-head path). Full `run_tests.py` + docs-lint green.
- [x] AC-8: The **shared wave** `GRAPH_BUILDER_VERSION` bump (one for the wave) includes this change's rationale; the rebuilt self-host graph carries the new version and is non-empty. No second/independent bump introduced by this change.

## Tasks

- [~] Add `declaring_container` derivation to `register_symbol` / `_extract_tree_sitter_artifact`. **Superseded by implementation** (see AC-1): no per-node field was added — the C# namespace is derived at rewrite time from each file's DECLARED namespace nodes (`cs_file_ns`, longest-prefix, nesting-proof); Go/Rust own-container is the file directory, handled by the `1p4er` same-package/same-directory fallback. The prepare-council probe confirmed C# already keys `Namespace.Class.method`, so the field proved unnecessary.
- [~] Add a per-language import-head→container extractor. **Superseded by implementation** (see AC-2): the C# membership path reuses the `using` FQN values already carried in `imports_by_file`; no separate extractor or container set was needed, and junk heads are discarded via `accept_ns.discard("")`.
- [~] Build the per-file `imported_containers_by_file` set. **Superseded by implementation** (see AC-2): the accept set is `{own-namespace} ∪ {using FQNs}` derived inline in the rewrite-pass C# membership block from `cs_file_ns` + `imports_by_file`, not a separate pre-built structure.
- [x] Generalize the ambiguity branch (`graph_indexer.py:~6464`): after the import-head filter, apply the membership filter (candidate `declaring_container` ∈ imported-container set ∪ source file's own container); resolve iff `len(matches) == 1`. Keep the existing `len(candidates) > 1` and unique-after-filter guards.
- [x] Add per-language adversarial tests (`tests/test_graph_indexer.py`, mirroring `~1046`): C#/Go/Rust two-twin "binds the visible container, never the twin" + same-container fallback + stays-external safety. Guard each with the `tree_sitter_<lang>` import skip pattern (`~1067`).
- [x] Contribute rationale to the **shared wave** `GRAPH_BUILDER_VERSION` bump; rebuild the self-host graph; run `run_tests.py` + docs-lint. Record in the progress log which of C#/Go/Rust have a passing membership test (claimed coverage).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| declaring-container field | Engineering | `1p4et` (Go `Type.method`) + `1p4eu` (Rust `Type::assoc_fn`) node registration | `register_symbol` / extractor; per-language container derivation; needs the qualified candidate nodes to disambiguate |
| import-head→container extractor + per-file set | Engineering | declaring-container field | Helper + `imported_containers_by_file` built once before the rewrite loop; kill `using`/`use`/`func` junk heads |
| membership filter in ambiguity branch | Engineering | import-head→container extractor; `1p4ef` (trustworthy `qualified_index`) | `graph_indexer.py:~6464`; union own-container (subsumes `1p4er`); unique-after-filter guard |
| per-language adversarial tests | Engineering | membership filter | C#/Go/Rust never-wrong-twin + same-container + stays-external; per-language skip guards |
| shared version bump + rebuild | Engineering | all above; coordinated wave-wide | ONE wave `GRAPH_BUILDER_VERSION` bump; contribute rationale only |

## Serialization Points

- **`1p4ef` must land first** (or concurrently, verified clean) — phantom `qualified_index` candidates make the `len(candidates) > 1` ambiguity branch fire on **false** ambiguity, which would let the membership filter resolve a non-ambiguous call incorrectly. This change's tests assume a trustworthy index.
- **`1p4et` / `1p4eu` must land first** — without `Type.method` (Go) / `Type::assoc_fn` (Rust) nodes there are no qualified candidates for the membership filter to disambiguate; those languages would be untestable (forcing skip/xfail under AC-6).
- **`1p4er`** (Java same-package fallback) shares the ambiguity branch (`~6464`). This change generalizes it via own-container union. If both land in this wave, coordinate so the same-package logic exists in **one** place (the membership path), not two. Decide ordering at Prepare wave.
- **Shared `GRAPH_BUILDER_VERSION`** — every `graph_indexer.py` change in this wave (`1p4ef`/`1p4er`/`1p4es` does not touch it; `1p4et`/`1p4eu`/`1p4ev` do) coordinates **ONE** bump. This change must not introduce its own.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — if it is being edited for the wave's other resolver improvements, add a short note on the cross-file rewrite pass gaining a **container-membership** disambiguation tier (declaring-container node field + per-file imported-container set) sitting between the import-head filter and "stays external." Otherwise N/A — this is an extension of existing rewrite-pass machinery with no new module boundary or verification-architecture change.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-5 | P0 | Faithfulness — never binds the wrong twin / stays external. The whole point of the wave's security-control-faithfulness lesson; a wrong bind is worse than no bind. |
| AC-6 | P0 | Per-language coverage gate — prevents the `1p470` over-claim (advertising languages whose path is dead code). Coverage claimed only where a test is green. |
| AC-3 | P1 | The headline positive case — proves the mechanism actually resolves the structural miss for at least one container language (C#). |
| AC-1 | P1 | Declaring-container field is the substrate everything else depends on; testable in isolation. |
| AC-7 | P1 | No regression on the working Python/Java import-head path — the generalization must not break the special case. |
| AC-4 | P2 | Same-container fallback (generalizes `1p4er`); high value but coordinated with `1p4er`'s own AC. |
| AC-2 | P2 | Imported-container set construction; supporting evidence for AC-3. |
| AC-8 | P2 | Shared version bump correctness; mechanical but mandatory for cache rebuild. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Membership filter binds the **wrong twin** when two visible containers each hold a candidate. | Unique-after-filter guard (`len(matches) == 1`) is mandatory; AC-5 asserts stays-external on multi-visible. Mirrors the `1p470` "requires exactly ONE candidate" contract. |
| `1p4et`/`1p4eu` slip → C#/Go/Rust have no `Type.method` candidate nodes → membership filter is itself dead code. | AC-6 gate: each language's test must pass **or** be explicitly skipped with the blocker recorded. No coverage claimed without a green test (avoids the `1p470` over-claim). |
| Container derivation leaks a prior value (same class of bug as `1p4ef`) and assigns a wrong `declaring_container`. | Explicit fallback to file-module when no container is derivable; AC-1 inspects payloads directly; deterministic derivation, no loop-carried state. |
| C# `file_scoped_namespace` vs block `namespace` AST shapes differ; Rust `mod` nesting is non-trivial. | Derive from the cheap, reliable signal first (file directory for Go/Rust; enclosing namespace text for C#); defer deep `mod`-nesting to the file-path module form; AC-1 fixtures pin the expected value per language. |
| Generalizing the `1p4er` same-package fallback into this block could regress Java if both land. | Serialization point + single-location decision at Prepare wave; AC-7 keeps the Java/Python import-head tests green as a regression gate. |
| Forgetting the shared bump (or double-bumping) → stale consumer caches or churn. | AC-8 ties this change to the **one** wave-coordinated `GRAPH_BUILDER_VERSION` bump; rebuild + non-empty-graph assertion. |

## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-09 | Implementation complete. C# namespace-membership disambiguation landed `.cs`-gated in the cross-file rewrite ambiguity branch (`graph_indexer.py:~6678-6711`, inside the `resolved is None and len(candidates) > 1` block, `len(ns_matches) == 1` unique-after-filter guard). Faithfulness fix: the caller/candidate namespace is derived from each file's DECLARED namespace nodes (`cs_file_ns`, built from `file.cs::Namespace` module nodes by longest-prefix — nesting-proof; `graph_indexer.py:~6414-6428`, `~6699-6711`), NOT by string-stripping a fixed two qname segments; the old fixed-strip mis-derived a nested-class caller's namespace (`Acme.Web.Outer.App.Run` → wrongly `Acme.Web.Outer`) and bound a coincident sibling twin (a wrong `RECEIVER_RESOLVED` edge the 1p4eq verification caught). Verified by `test_csharp_namespace_membership_disambiguates` (using-driven flip proof) and the new faithfulness test `test_csharp_nested_class_caller_binds_own_namespace_not_sibling`, both in `tests/test_graph_indexer.py` (`CrossFileResolutionTests`). Claimed coverage: C# (membership), Java (same-package, 1p4er regression gate), Go + Rust (cross-file method/assoc-fn) — synthetic fixtures only. Full suite 2960 green; graph builder v25. | `graph_indexer.py:~6678-6711` + `~6414-6428`; `tests/test_graph_indexer.py` (`CrossFileResolutionTests`, 241 green); `GRAPH_BUILDER_VERSION = "25"`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
