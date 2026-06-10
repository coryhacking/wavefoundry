# Graph `qualified_index` Leaked Loop Variable (Phantom Cross-File Candidates)

Change ID: `1p4ef-bug graph-qualified-index-leaked-loop-var`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-06-09
Wave: 1p4eq cross-file-resolution-followups

## Rationale

The cross-file rewrite pass in `graph_indexer.py` builds a `qualified_index` (qualified-name → candidate node ids) that the resolver uses to promote `external::Type.method` edges to project nodes **only when the match is unambiguous** (`len(candidates) == 1`). A leaked loop variable injects **phantom candidates** into that index for **collapsed/basename-merged class nodes**, which can inflate a genuinely-unique match to `len(candidates) > 1` — causing the `len == 1` guard to fail and leaving a cross-file call **`external::` (unresolved)** that should have resolved. Because a `RECEIVER_RESOLVED`/`CONSTRUCTION_RESOLVED` edge also *blocks* the simple-name fallback, the suppression is silent: the call simply never binds.

This was found during the `1p47e` cross-file-resolution investigation (3-language deep-dive workflow, 2026-06-09) and **independently verified against source + on the live graph**. It is **pre-existing** (not introduced by `1p470`).

**Severity — scales with collapsed-node count:**
- **Self-host (Python): negligible.** Python's single-dominant-class merge produces only **1** collapsed node here; a replication probe found 8 differing `qualified_index` keys but **0** actual unique→ambiguous suppressions. This is why it did not affect the `1p41o` gate.
- **C# / Swift / Rust / Ruby: potentially significant.** These languages emit **one collapsed (basename-merged) node per class file**, so the leak fires per class and can collide with real qualified names — suppressing cross-file resolution. **This is directly relevant to the in-flight Swift/C# test-pack validation:** some "misses" those teams report may be this bug, not a true resolution gap.

## Root cause

The `qualified_index` build loop (`graph_indexer.py:6322-6351`):

```python
for (file_part, simple), node_id in per_file_simple.items():
    simple_name_index.setdefault(simple, []).append(node_id)
    if "::" in node_id:
        _, qualified = node_id.split("::", 1)          # 6328 — qualified assigned ONLY here
        if qualified and qualified != simple:
            qualified_index.setdefault(qualified, []).append(node_id)
    # ...
    if dotted_module:
        dotted_full = f"{dotted_module}.{qualified}"   # 6341 — qualified READ unconditionally
        qualified_index.setdefault(dotted_full, []).append(node_id)
        parts = dotted_full.split(".")                 # 6347-6351 — fanned across every suffix
        for i in range(1, len(parts)):
            suffix = ".".join(parts[i:])
            if "." in suffix:
                qualified_index.setdefault(suffix, []).append(node_id)
```

For a **collapsed_pair / basename-merged node** (id has **no `::`** — e.g. `src/Worker.cs`, `Sources/Foo.swift`), the `if "::" in node_id` branch is False, so `qualified` is **never reassigned this iteration** and retains the **previous iteration's** value. Line 6341 then builds `dotted_full = f"{this_node_module}.{some_other_node_qualified}"` and registers it (plus every suffix) pointing at *this* collapsed node — a phantom entry under a key the node has nothing to do with.

The existing guard comment at 6324-6326 ("merged Swift class/module nodes have no `::`… skip the qualified_index addition") correctly skips the **direct** add (6330) for no-`::` nodes, but the **dotted-form block (6340-6351) was never given the same handling**.

## Evidence

- **Source inspection:** `qualified` assigned only at 6328; read at 6341 + 6347-6351. Confirmed against the current file.
- **Live-graph replication (self-host):** replicating the loop with vs. without the leak yields 8 differing `qualified_index` keys; with only 1 collapsed node, **0** keys flip a unique match to ambiguous → no self-host harm (matches the clean `1p41o` gate).
- **C# probe (investigation):** two `Service` classes (`Acme.Services` / `Acme.Other`) and a collapsed-class `Worker.cs` calling a typed `svc.Process()` — a phantom `src.Worker.Service.Process` entry inflates `qualified_index['Service.Process']` to 2 candidates, the `len == 1` check fails, and the `RECEIVER_RESOLVED` edge stays `external::Service.Process`. The **unique-type** case (single project `Service`) was *also* suppressed by the same phantom.

## Requirements

1. In the `qualified_index` build loop, `qualified` (used by the dotted-form index and its suffix fan-out) must always reflect the **current** node — no leak from a prior iteration. For a collapsed/no-`::` node, the dotted form must use the node's own label (which equals `simple`).
2. Bump `GRAPH_BUILDER_VERSION` in the same change (the fix alters `qualified_index` contents → consumer caches must rebuild).
3. A regression test proving a collapsed-class node no longer injects a phantom candidate, and the unique-type cross-file call resolves.

## Scope

**Problem statement:** a leaked loop variable poisons `qualified_index` with phantom candidates for collapsed/basename-merged nodes, silently suppressing cross-file `Type.method` resolution for C#/Swift/Rust/Ruby (and any basename-merge language).

**In scope:**

- The loop fix at `graph_indexer.py:~6327-6351`.
- The `GRAPH_BUILDER_VERSION` bump + graph rebuild.
- A regression test (collapsed-class phantom + a no-regression assertion on an existing collapsed-language cross-file test).

**Out of scope:**

- The broader per-language resolution improvements (Go method keying, Rust associated-fns, membership-based disambiguation) — separate changes, candidates for the **same** follow-on wave; see **Related** below.

## Acceptance Criteria

- [x] AC-1: For a collapsed_pair / no-`::` node, the dotted-form `qualified_index` entry is derived from the node's **own** label (`simple`), not a leaked prior-iteration `qualified` — no phantom `{this_module}.{unrelated_qualified}` key is registered. Verified by a unit test inspecting `qualified_index` contents.
- [x] AC-2: Regression fixture — two files: a collapsed-class `Worker.<ext>` whose method calls a typed receiver `svc.Process()` (svc: `Service`) and a `Service.<ext>` defining `Service.Process` — asserts (a) `qualified_index['Service.Process']` (or the dotted form) has **exactly 1** candidate and (b) the call edge resolves to the real `Service.Process` project node (`RECEIVER_RESOLVED` → project), not `external::`.
- [x] AC-3: No regression — an existing collapsed-language cross-file test (Swift class/module merge, e.g. `test_swift_cross_file_navigation_call`) still resolves; full `run_tests.py` + docs-lint green.
- [x] AC-4: `GRAPH_BUILDER_VERSION` bumped in the same change; rebuilt graph carries the new version and is non-empty.

## Tasks

- [x] Fix the loop: add `else: qualified = simple` after the `if "::" in node_id:` block (or gate the dotted-form block 6340-6351 to use `simple` for non-`::` nodes) — `graph_indexer.py:~6327`.
- [x] Add the two-file collapsed-class regression test (a basename-merge language; C# or Swift).
- [x] Bump `GRAPH_BUILDER_VERSION`; rebuild the self-host graph; run `run_tests.py` + docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| loop-fix | Engineering | — | `graph_indexer.py` qualified_index build loop; one-line `else` |
| version-bump + rebuild | Engineering | loop-fix | `GRAPH_BUILDER_VERSION`; one bump covers the change |
| regression-test | Engineering | loop-fix | collapsed-class phantom + no-regression on Swift merge |


## Serialization Points

- `graph_indexer.py` `qualified_index` build loop (`~6322-6351`) and the adjacent `1p470` disambiguation block (`~6464`) — coordinate the version bump if landed alongside any other `graph_indexer.py` change in the follow-on wave.

## Affected Architecture Docs

N/A — a correctness fix to existing rewrite-pass machinery; no module boundary, control-flow, or verification-architecture change. (If `docs/architecture/graph-index-system.md` is being edited anyway for the follow-on improvements, a one-line note on collapsed-node `qualified_index` handling would fit.)

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core correctness fix — `qualified` must reflect the current node for collapsed/no-`::` nodes; without it the phantom candidates persist and the precondition this change exists to provide is not delivered. |
| AC-2 | required | The regression fixture is the proof the fix works — a collapsed-class node no longer injects a phantom candidate and the previously-suppressed unique cross-file call resolves. |
| AC-3 | required | No-regression on an existing collapsed-language cross-file test (Swift class/module merge) — guards the suffix-fan-out path the fix touches. |
| AC-4 | required | The `GRAPH_BUILDER_VERSION` bump (shared wave bump) is mandatory — the fix alters `qualified_index` contents, so consumer caches must rebuild or the change is invisible. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The fix changes `qualified_index` contents, altering cross-file resolution for collapsed/basename-merge-heavy projects (C#/Swift/Rust/Ruby). | This is the intended, more-correct behavior (it *un*-suppresses real edges); the shared `GRAPH_BUILDER_VERSION` bump forces a clean rebuild, and AC-2/AC-3 pin both the new resolution and no-regression. |
| The `else: qualified = simple` edge case if `simple` is empty. | The existing `if not simple: continue` guard (`graph_indexer.py:~6316`) already skips empty-simple nodes before the loop body, so `qualified` is never set from an empty `simple`. |
| Interaction with the sibling `1p4er`/`1p4ev` disambiguation in the same `graph_indexer.py` region (`~6464`). | `1p4ef` lands first (precondition) and only touches the index-build loop (`~6322-6351`), not the disambiguation block; the shared-file serialization watchpoint sequences the edits. |

## Related — follow-on wave scope (validated by the 1.6.0+p4ea test pack)

### Test-pack validation (2026-06-09) — 3 teams: Java (Aceiss), Swift (Solaris), JS/TS (Teton)

**Strong validation overall.** `code_risk_score` PASSED on all three, top-ranked symbols matching team intuition, and the formula behaved exactly as designed: blast radius correctly outweighs degree (Teton: `hasErrorAlreadyBeenCaught` blast 80 / fan_in 3 ranked **above** `rethrowRequestError` blast 28 / fan_in 20; Solaris: `DaylightManager.getSunTimes` correctly ranked LOW despite high degree because its blast radius is 1), `fan_out` confirmed surfaced-not-folded (Aceiss: `JSON.writeObject` fan_out 99 / fan_in 2 ranked below `JSON.toJson`), and guardrails (`over_candidate_cap`, empty-scope) + B4 cross-tool consistency all PASS. Cross-file resolution resolves well on unambiguous + import-disambiguated cases (Teton 100% `RECEIVER_RESOLVED` on a project-internal cross-file util; Aceiss cross-module RR; Solaris cross-target RR). No misses on Swift or TS.

**New findings to fold into the follow-up wave:**

1. **[HIGH — real observed miss; the headline team finding] Same-package ambiguous-receiver gap (Aceiss/Java).** When two same-named classes in different packages both define a method, and the call site uses the **same-package** twin **without an import** (`JreCompat.canAccess` — exists on both `el.javax.JreCompat` and `el.apache.util.JreCompat`; 9 instance-receiver call sites; `el.javax` callers use the same-package twin with no import), the `1p470` disambiguation cannot fire — it keys on `imports_by_file[src_file][type-head]`, which is empty for same-package receivers (Java makes same-package types visible without an `import`). The edge stays `external::JreCompat.canAccess` and the call is dropped from the project node's view (`code_impact` → `total_found: 0`). Unique-name methods on the same twins (`isExported`) resolve fine. **Fix:** add a **same-package / same-directory fallback** to the disambiguation block (`graph_indexer.py:~6464`): when no import disambiguates and exactly one ambiguous candidate lives in the **source file's own package directory**, prefer it (matches Java/C#/Kotlin resolution order — explicit single-type import > same-package). Resolves both packages' call sites to the correct twin. Generalize into the membership-disambiguation mechanism (same-container is just membership where the container is the file's own). Effort small-medium, risk low. **Most important team-found item.** (Static-receiver `JreCompat.getInstance()` stays out of scope — static-call resolution is separate.)

2. **[MEDIUM — `code_impact` ergonomics, not the new tools] `code_impact` `edges` array not bounded by `max_results` (Teton).** On a high-fan-in symbol (`rethrowError`, 754 edges) the response reached 226,918 chars and blew the tool token cap; `max_results` capped `affected` (to 12) but **not** `edges` (the size driver). Add an edges cap / summary mode so high-blast-radius symbols are usable inline. `code_risk_score` is unaffected (it returns counts, not edge lists).

3. **[LOW — cosmetic] `code_impact` graph-mode top-level `resolved: null` (Teton).** Came back `null` despite a populated `node_id` + 754 edges + 12 affected; per schema it should be `true`. Set it from node resolution so it can be trusted as a resolution gate.

4. **[LOW — ergonomic] `wave_index_build_status(layer='code')` errors (Solaris).** The code index lives under the `project` layer; the `content='code'` vs `layer='code'` distinction trips users. The error message is clear/self-correcting — consider aliasing `code`→`project` or a sharper hint.

### Cross-language resolver improvements (1p47e investigation — synthetic only; no team tested C#/Go/Rust resolution)

From the `1p47e` 3-language investigation (full per-language detail in the workflow transcript `wf_516511cb-52c`). The same three structural failures recur across C#/Go/Rust; the fixes mostly reduce to a few reusable mechanisms. **This bug (`1p4ef`) is the recommended lead item** — it is the trust precondition for any further disambiguation (phantom candidates make the `len == 1` guard unreliable everywhere).

**Recurring failures:** (1) methods not keyed by receiver type (Go registers bare `Process`, so `Helper.Process` never exists to match); (2) import edges carry the wrong head (namespace/package/path fragments + keyword junk like `external::using` / `external::func` / `external::use`), so the `1p470` import-disambiguation is **dead code** for C#/Go/Rust; (3) resolvers miss idiomatic shapes (Rust `Type::assoc_fn()`, Go `var h foo.Helper`, C# `var x = new T()`).

| Candidate | Lang | Value / Effort / Risk | Note |
| --- | --- | --- | --- |
| **`1p4ef` — leaked-`qualified` fix** (this doc) | shared (C#/Swift/Rust/Ruby) | high / small / low | Lead item; precondition for the rest |
| Register Go methods as `Type.method` | Go | high / medium / medium | Keystone — every other Go fix is inert without it |
| Resolve Rust `Type::assoc_fn()` (generalize the existing `::`-split) | Rust | high / small / low | Biggest single Rust miss; reuses the dotted qualified-index path |
| Handle Go `qualified_type` receivers (`var h foo.Helper`) | Go | high / small / low | Most common cross-package shape; pair with Go keying |
| Infer Rust `let x = Bar{..}` / `Bar::new()` binding types | Rust | high / medium / medium | Upgrades head from variable → type |
| **Membership-based disambiguation** (generalize `1p470`) | shared | high / medium-large / medium | The strategic one — disambiguate by container membership (namespace / package-dir / module) instead of import-head==type-head. Build **once**, parameterized. Needs a new node-level "declaring container" field. Gated behind the items above. |
| Import-substrate hygiene (clean C#/Go/Rust import extractors; kill junk edges) | per-lang | medium / medium / medium | Enabler for membership disambiguation; **low ROI unless landed *with* it** — bundle, don't sequence |
| C# `this.M()`/`base.M()` dead-code fix; C# `var x = new T()` type inference | C# | medium / small-medium / low | Opportunistic |

**Deferred (all three analyses agreed):** trait/`dyn`/generic dispatch (Rust); selector-chain / field / return / index receivers (`a.b.M()`, `s.client.Do()`); `:=` / `let x = func()` from arbitrary function returns (but *constructor* sub-cases are cheap and in-scope). These require real inter-procedural type-flow inference and are phantom-prone.

## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-09 | Found during the `1p47e` cross-file investigation workflow; verified against source (`graph_indexer.py:6341` reads `qualified` assigned only at 6328) and on the live graph (8 phantom keys / 1 collapsed node / 0 self-host suppressions; C# probe showed unique + ambiguous `Service.Process` both left `external::`). Written up as a `docs/plans/` entry for a follow-on wave, recommended as the lead item. | Workflow `wf_516511cb-52c`; self-host replication probe; source inspection. |
| 2026-06-09 | Implementation complete. Loop fix landed as the `else: qualified = simple` branch for collapsed/no-`::` nodes (`graph_indexer.py:6461-6470`), so the dotted-form index (`graph_indexer.py:6480-6491`) uses the current node's own label. Regression proven by `test_collapsed_class_node_does_not_suppress_resolution` (C# two-file fixture; resolves to `Service.cs::Service.Process`, not `external::`) and no-regression by `test_swift_cross_file_navigation_call`, both in `tests/test_graph_indexer.py` (`CrossFileResolutionTests`). Full suite 2960 green; graph builder v25. | `graph_indexer.py:6461-6470`; `tests/test_graph_indexer.py` (241 green); `GRAPH_BUILDER_VERSION = "25"`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
