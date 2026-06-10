# Same-Package / Same-Directory Receiver Disambiguation

Change ID: `1p4er-enh same-package-receiver-disambiguation`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-06-09
Wave: 1p4eq cross-file-resolution-followups

## Rationale

The `1p470` cross-file rewrite-pass disambiguation (`graph_indexer.py:~6464`) resolves an ambiguous `external::Type.method` (where the receiver's simple name maps to **multiple** same-named project candidates) by keying on the **source file's `imports` edge** for the receiver head: `imports_by_file[src_file][head]`. This is correct when the receiver type is brought into scope by an **explicit import**, but it is **dead** for **same-package receivers** — types that the language makes visible **without** an `import` (Java/C#/Kotlin same-package, also same-directory Go/Swift). For those call sites `imports_by_file[src_file]` has no entry for `head`, the `if imp_fqn:` guard at `6468` is False, nothing disambiguates, and the edge stays `external::Type.method`.

This is the **headline field finding** from the `1.6.0+p4ea` test pack (Aceiss/Java, 2026-06-09, ranked HIGH). `JreCompat.canAccess` exists on **two** same-named classes — `el.javax.JreCompat` and `el.apache.util.JreCompat` — with 9 instance-receiver call sites. The `el.javax` callers reference the **same-package** `JreCompat` with **no import** (same-package types are visible in Java without one). The `1p470` import disambiguation finds nothing, both candidates survive, the `len(candidates) > 1 / matches==1` path never resolves, and the edge stays `external::JreCompat.canAccess` — so `code_impact` on the real `JreCompat.canAccess` node reports `total_found: 0` (the call is dropped from the project node's incoming view). **Unique-name** methods on the same twins (`isExported`) resolve fine; the gap is specific to the **ambiguous-by-simple-name + no-import** intersection.

The fix is an **explicit single-type import > same-package** resolution order — exactly what `javac`/`csc`/`kotlinc` do. When no import disambiguates, prefer the ambiguous candidate(s) whose **defining file lives in the source file's own package directory**; if exactly one remains, resolve. This subsumes naturally into the `1p4ev` membership mechanism (same-package is just membership where the container is the file's own), but it ships **standalone** — it reads only the candidate node ids and the source id, with **no dependency** on the per-language import-head substrate that `1p4ev` cleans up. Scope is claimed **only** to Java, which is what the regression test exercises.

## Requirements

1. In the rewrite-pass disambiguation block (`graph_indexer.py:~6464`, the `if resolved is None and len(candidates) > 1:` branch), after the existing import-based disambiguation fails to resolve, add a **same-directory / same-package fallback**: among the `candidates`, keep those whose **defining file's directory** equals the **source file's directory**; if exactly one candidate remains, set `resolved` to it.
2. The fallback must fire **only** when the import-based path left `resolved is None` (explicit import wins over same-package — never override an import match) and must require the same-directory filter to leave **exactly one** candidate (an ambiguous receiver with two same-package twins, or none in-directory, stays `external::` — never guess).
3. Use the **same directory-derivation** as the existing block: `src_file = src.split("::", 1)[0]`, candidate file `cand.split("::", 1)[0]`, compare on `os.path.dirname(...)` (or the equivalent path-prefix already used at `6474-6475` for `cmod`). No new node-level field is introduced (that is `1p4ev`'s "declaring container").
4. Bump `GRAPH_BUILDER_VERSION` (`graph_indexer.py:28`, currently `"24"`) — this change alters rewrite-pass output (more `external::*` edges promote to project nodes), so consumer caches must rebuild. **Do not** bump per-change: this wave coordinates **one** shared bump across all `graph_indexer.py` changes (`1p4ef`, `1p4et`, `1p4eu`, `1p4ev`, this change).
5. A regression test modeled on `test_java_ambiguous_import_disambiguates`: two same-named classes in different packages, plus a **same-package** caller **without** an import, resolving `recv.method()` to the **same-package** twin, with a negative assertion that the **other** twin is not bound.

## Scope

**Problem statement:** the `1p470` ambiguous-receiver disambiguation only fires for receivers brought into scope by an explicit `imports` edge. Same-package / same-directory receivers (visible without an import in Java/C#/Kotlin, and by directory in Go/Swift) leave `imports_by_file[src_file][head]` empty, so an ambiguous `external::Type.method` is never disambiguated and the call is dropped (`code_impact total_found: 0` for `JreCompat.canAccess`).

**In scope:**

- A same-directory/same-package fallback added to the `if resolved is None and len(candidates) > 1:` block at `graph_indexer.py:~6464`, ordered **after** the import path (explicit import > same-package), requiring a **unique** in-directory survivor.
- The shared-wave `GRAPH_BUILDER_VERSION` bump (coordinated once for the wave) + self-host graph rebuild.
- A Java regression test (two-package twins + same-package importless caller) plus a negative (does not bind the non-same-package twin), and a no-guess safety case (two same-package twins → stays external).

**Out of scope:**

- **Static-receiver** calls (`JreCompat.getInstance()`) — static-call resolution is a separate path; not addressed here.
- Generalizing the fallback to **arbitrary container membership** (namespace/package/module across directories) — that is `1p4ev` (membership-based disambiguation), which this change feeds into but does not implement. Coverage is **not** claimed for C#/Go/Rust here (no test exercises them in this change); only Java is tested and claimed.
- The leaked-`qualified` `qualified_index` phantom fix (`1p4ef`) — a **precondition** for trustworthy `len(candidates)` counts but a separate change; this change assumes `1p4ef` has landed so `candidates` is not phantom-inflated.

## Acceptance Criteria

- [x] AC-1: In the rewrite pass, when `resolved is None and len(candidates) > 1` and the import-based disambiguation does not resolve, the same-directory fallback keeps candidates whose defining file shares the **source file's directory**; if exactly one survives, the edge resolves to it. Unit-verified by inspecting the resolved `calls` edge target.
- [x] AC-2: Regression fixture (Java) — `el/javax/JreCompat.java` (`package el.javax`) and `el/apache/util/JreCompat.java` (`package el.apache.util`) both define `JreCompat.canAccess`; a same-package caller in `el/javax/Foo.java` (`package el.javax`, **no `import`**) calls `jc.canAccess()` — asserts the call edge resolves to `el/javax/JreCompat.java::JreCompat.canAccess` (the same-package twin) and **NOT** to `el/apache/util/JreCompat.java::JreCompat.canAccess`.
- [x] AC-3: Safety/no-guess — two `JreCompat` twins both in the **same directory** as the caller (constructed degenerate case), or a caller in a directory containing **neither** twin, leaves the ambiguous call `external::` (the filter does not leave exactly one in-directory candidate → no resolution). Asserts neither project node is bound.
- [x] AC-4: No regression — `test_java_ambiguous_import_disambiguates` and `test_ambiguous_without_import_stays_external` still pass (explicit import still wins; bare-no-import ambiguous still stays external); full `run_tests.py` + docs-lint green.
- [x] AC-5: `GRAPH_BUILDER_VERSION` is bumped (once, coordinated for the wave) and the rebuilt self-host graph carries the new version and is non-empty.

## Tasks

- [x] Add the same-directory fallback inside the `if resolved is None and len(candidates) > 1:` block (`graph_indexer.py:~6464`), **after** the existing `imp_fqn` import path leaves `resolved is None`: derive `src_dir = os.path.dirname(src_file)`, filter `candidates` to those whose `cand.split("::", 1)[0]` directory equals `src_dir`, and if exactly one survives set `resolved`. Reuse `src_file` already computed at `6465`.
- [x] Add the Java regression test (two-package twins + same-package importless caller) modeled on `test_java_ambiguous_import_disambiguates` (`tests/test_graph_indexer.py:~1064`), with the positive (resolves to same-package twin), the negative (does not bind the other twin), and the no-guess safety case (AC-3).
- [x] Bump `GRAPH_BUILDER_VERSION` (`graph_indexer.py:28`) as the wave's shared bump (do not double-bump if another `1p4eq` change already moved it in the same landing); rebuild the self-host graph; run `run_tests.py` + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| same-package-fallback | Engineering | `1p4ef` (precondition: trustworthy `candidates` counts) | `graph_indexer.py:~6464` rewrite-pass block; same-dir filter after import path |
| regression-test | Engineering | same-package-fallback | Java twins + importless same-package caller; positive + negative + no-guess |
| version-bump + rebuild | Engineering | same-package-fallback | Shared wave `GRAPH_BUILDER_VERSION` bump (coordinate — ONE bump for the wave) |

## Serialization Points

- `graph_indexer.py:28` `GRAPH_BUILDER_VERSION` — **one** bump for the entire `1p4eq` wave; this change must not bump independently of `1p4ef`/`1p4et`/`1p4eu`/`1p4ev`. Whichever change lands last (or a dedicated wave-close step) owns the final bump value and the rebuild.
- `graph_indexer.py:~6449-6479` rewrite-pass disambiguation block — shared with `1p4ev` (membership disambiguation, which generalizes this same-package case) and adjacent to `1p4ef`'s `qualified_index` build loop (`~6322-6351`). Land `1p4ef` first so `len(candidates)` is phantom-free; coordinate edits to this block with `1p4ev` to avoid a merge conflict on the same lines.

## Affected Architecture Docs

N/A — an additive resolution-order fallback within existing rewrite-pass machinery; no module boundary, control-flow, or verification-architecture change. (If `docs/architecture/graph-index-system.md` is being edited for the wave's other improvements, a one-line note on the explicit-import > same-package disambiguation order would fit there.)

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-2 | P0 | The literal field-reported miss (`JreCompat.canAccess`, `code_impact total_found: 0`); resolving it is the change's reason to exist. |
| AC-1 | P0 | The mechanism AC-2 depends on; without the same-dir filter resolving uniquely there is no fix. |
| AC-3 | P1 | No-guess safety — the fallback must never bind when the in-directory filter is non-unique; prevents a new phantom class. |
| AC-4 | P1 | Regression guard — explicit import must still win and bare-ambiguous must still stay external; the change is additive, not a reorder of existing wins. |
| AC-5 | P1 | Cache-correctness — rewrite output changed; stale consumer caches would mask the fix. Coordinated as the wave's single bump. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Same-directory match over-resolves when two twins coincidentally share the caller's directory | Require the filter to leave **exactly one** in-directory candidate; non-unique → stays `external::` (AC-3 asserts this). |
| Fallback overrides a correct explicit-import resolution | Ordered strictly **after** the `imp_fqn` path and gated on `resolved is None`; AC-4 (`test_java_ambiguous_import_disambiguates`) proves explicit import still wins. |
| `len(candidates)` inflated by the `1p4ef` leaked-`qualified` phantom makes `> 1` fire spuriously | Depends on `1p4ef` landing first (precondition workstream); the filter still requires a real unique in-directory survivor, so a phantom candidate in another directory does not cause a false bind. |
| Directory comparison brittle across path separators / nested same-named packages | Reuse the established `cand.split("::", 1)[0]` + path normalization already used at `~6474-6475`; compare normalized `dirname`s, not raw strings. |
| Double `GRAPH_BUILDER_VERSION` bump if multiple wave changes each bump | Wave coordinates ONE bump (Serialization Points); this change defers to the shared bump rather than bumping independently. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-09 | Implementation complete. Same-package / same-directory fallback added to the cross-file rewrite-pass disambiguation block (`graph_indexer.py:6647-6677`, "Wave 1p4er: same-package / same-directory fallback"), ordered after the import path and gated on `resolved is None` + a unique in-directory survivor. 1p4eq faithfulness fix: the fallback is now LANGUAGE-GATED to Java/Kotlin/Go (`.java/.kt/.kts/.go`, `graph_indexer.py:6668`) — Python/JS/TS/Rust require an explicit import so same-directory confers no visibility, and C# uses the `.cs`-gated namespace-membership block instead (a same-dir C# file can be a different namespace). New regression test `test_python_same_dir_unimported_receiver_stays_external` (CrossFileResolutionTests) asserts a Python same-dir unimported receiver stays `external::`. ACs verified via `test_java_same_package_ambiguous_receiver_disambiguates` + `test_same_package_fallback_no_colocated_candidate_stays_external` (CrossFileResolutionTests); no-regression via `test_java_ambiguous_import_disambiguates` + `test_ambiguous_without_import_stays_external`. Note: AC-2's caller fixture is named `Caller.java` in the test (doc prose says `Foo.java`); behavior and assertions match. Full suite 2960 green; graph builder v25. | `graph_indexer.py:6647-6677` (fallback) + `:6668` (lang gate) + `:28` (GRAPH_BUILDER_VERSION="25"); `tests/test_graph_indexer.py` CrossFileResolutionTests: `test_java_same_package_ambiguous_receiver_disambiguates`, `test_same_package_fallback_no_colocated_candidate_stays_external`, `test_python_same_dir_unimported_receiver_stays_external`, `test_java_ambiguous_import_disambiguates`, `test_ambiguous_without_import_stays_external` — all pass; self-host graphs carry `builder_version: 25` (non-empty). |
