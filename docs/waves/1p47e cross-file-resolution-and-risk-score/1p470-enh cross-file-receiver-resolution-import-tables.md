# Cross-File Receiver Resolution via Per-Language Import Tables

Change ID: `1p470-enh cross-file-receiver-resolution-import-tables`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-06-09

> **Implementation pivot (2026-06-09, operator-directed).** The shipped mechanism differs from the original plan below; the AC text is being reconciled at close. Two changes: **(1)** the **Python lazy-loader return-type inference** — originally *deferred* (see Scope "Out of scope" + Decision Log 2026-06-08) — was brought **in scope** at the operator's explicit direction ("fix the lazy loader option for python"); it is what actually closes this repo's headline `from_root`-has-0-edges hole (now **12** in-edges). **(2)** Cross-file ambiguous-receiver resolution shipped as a **single language-agnostic disambiguation in the post-build rewrite pass** (uses the already-emitted `imports` edges to pick the right same-named candidate), **not** per-language `import_targets` threading — because measurement showed unambiguous cross-file already resolves (only **376 of 5,027** unresolved edges even share a name with a project symbol; **0** were ambiguous-project-import cases on the self-host), so the marginal value of per-resolver threading was ~nil. **Verified coverage is Python + Java** (the two with passing disambiguation tests). The mechanism is language-agnostic *by construction*, but per the follow-on `docs/plans/1p4ef` it does **not yet fire for C#/Go/Rust** — their import edges carry the wrong head (namespace/package/path fragments, not the receiver type), so the import-key lookup misses; that import-head fix is tracked in `1p4ef`. (Earlier drafts of this doc claimed "covers Java/Kotlin/C#/Go at once" — corrected at close: only Python + Java are exercised today.) Architecture-doc extension (`graph-index-system.md`) is **deferred** per operator ("defer extending the document path").
Wave: 1p47e cross-file-resolution-and-risk-score

## Rationale

The call graph systematically **fails to emit `calls` edges for cross-file method invocations** (`Type.method()` / `obj.method()` where the receiver type is defined in another file). On the self-hosted index, **87% of `calls` edges are intra-file `EXTRACTED`** (9,456 of 10,826); only ~13% are resolved (`RECEIVER_RESOLVED` 1,319 + `CONSTRUCTION_RESOLVED` 51). Concrete proof: `GraphQueryIndex.from_root`, called from dozens of sites across `server_impl.py`, has **0 `calls` in-edges** and `graph_impact` returns `affected_files = 0` for it.

Why it matters — this is the **through-line for two surfaces**:
- **`code_impact` / `graph_impact` under-report cross-file blast radius** for any method whose callers live in other files. The "what breaks if I change X?" answer is a floor, not a true measure. `guru.md:286` already warns that an empty `code_impact` ≠ no callers — this generalizes it (even *non-empty* results undercount).
- It **gated out `code_risk_score`** (`1p41o`, this wave's `1p41l`): its `affected_file_count` term was flat across 46% of modules and the composite collapsed to a `fan_in` degree proxy on 81% of modules (AC-8 NO-GO). The score cannot be non-degenerate until cross-file reach actually varies.

This is a **known, previously-deferred problem with a proven in-repo fix pattern.** Receiver resolution was built incrementally across 7 waves (`130tw` → `1312l` → `13194` → `1319a` → `1319g` → `1319q` → `1p2tf`). **Full cross-file import-table resolution was explicitly deferred in `1312l` as a "major scope expansion"** (the 85% solution of local-declaration matching was chosen). **TypeScript/JavaScript already got the real fix** (wave `1p2tf`): a per-file `import_targets` map (`graph_indexer.py:5297`, populated at `:5534-5561`) threaded into `_resolve_ts_call_target` (`:3741-3789`) resolves imported receivers to project nodes **at index time**. This change replicates that proven pattern for the languages where it is tractable.

## Requirements

1. **Replicate the `import_targets` pattern for the HIGH-feasibility statically-typed languages — Java, Kotlin, C#, Go.** Each already has a per-file receiver resolver that reads local type declarations (`graph_indexer.py:2062-2101` Java, `:2162-2247` Kotlin, `:2379-2516` C#, `:2524-2678` Go) and already emits `imports` edges (so import statements are parsed — `:4857-4886`). Thread a per-file `import-name → project-node-id` map into each resolver so that when a receiver's type is **imported from another project file**, the `Type.method` call resolves to the project node at index time (`RECEIVER_RESOLVED`), rather than falling to an `external::Type.method` stub that only the post-build rewrite pass can promote — and only when the name is globally unambiguous (`:6278-6365`, `len(candidates)==1`).
2. **Python static imports.** `import_aliases` is already built from `from module import Foo` (`graph_indexer.py:4867-4886`). Thread it into `CallCollector._resolve_call` (`:5001-5042`) so `Foo.method()` / annotated `x: Foo` (where `Foo` is statically imported from a project module) resolves cross-file. The seam is the two-level attribute branch at `:5037-5041`, which today only handles `import_aliases`-backed roots for module-attribute access.
3. **Mandatory `GRAPH_BUILDER_VERSION` bump** (`graph_indexer.py:28`, currently `"23"`) **in the same change** — this alters edge shape (new resolved cross-file `calls` edges), and a mismatch triggers the full synchronous auto-rebuild at load (`graph_query.py:98-243`). Per the framework rule, any extractor change that changes node/edge shape must bump the constant in the same commit so consumer caches actually rebuild.
4. **Update the negative-assertion tests that legitimately flip**, and keep the ones that should not. `test_graph_indexer.py` asserts no `RECEIVER_RESOLVED` for *unannotated* receivers (`:1509-1516` TS, `:1551-1559` Python, `:1577-1590` JS). Only the cases that become resolvable (imported-and-typed receivers) should flip, with the new positive behavior explicitly verified; genuinely-unannotated/inferred receivers stay negative.
5. **Re-run `code_risk_score`'s AC-8 as a downstream validation gate** once Phase 1 lands. With cross-file edges present, `affected_file_count` should vary; if the AC-8 Spearman gate now passes (ρ ≤ ~0.95, non-degenerate), `1p41o` becomes re-admittable. This change does **not** re-implement `code_risk_score` — it unblocks it.

## Scope

**Problem statement:** receiver resolution is intra-file only for every language except TS/JS (each resolver's `symbol_lookup` is built solely from the current file's `defined_symbols` — `graph_indexer.py:4900` Python, `:5168` JS-fallback, `:5256-5265` tree-sitter). Cross-file `Type.method()` calls therefore emit no resolved edge, leaving the call graph blind to cross-file reach.

**In scope (phased — see Agent Execution Graph):**

- **Phase 1 (HIGH feasibility):** import-table cross-file resolution for **Java, Kotlin, C#, Go** — replicating the `1p2tf` TS pattern. Highest coverage (covers the dominant `pkg.Func()` / `Type.method()` cross-file call shape in typed codebases).
- **Phase 2 (Python static imports):** thread `import_aliases` into the Python cross-file class→method resolution for the `from X import Foo; Foo.method()` and annotated-import shapes.
- The `GRAPH_BUILDER_VERSION` bump, consumer-impact verification, test updates, and the `code_risk_score` AC-8 re-run.

**Out of scope (deferred residuals — each its own later change/wave if demanded):**

- **Python lazy-loader / call-return-type inference** — the `gq = _load_graph_query()` (unannotated `ast.Assign`) → `gq.GraphQueryIndex.from_root()` shape that produces the `from_root`-has-0-edges case. `_resolve_call` returns `(None, False)` and emits no stub at all (`:5037-5041`); resolving it needs call-return-type inference, a heavier mechanism than import-table threading. (This repo's own `server_impl.py` uses this lazy-loader style, so the literal `from_root` example is in the *deferred* bucket — the *dominant* static-import pattern is the Phase-1/2 win.)
- **Rust trait-method dispatch** (needs impl-block resolution / type inference), **C/C++** (no classes / header-impl split — deferred in `1319a`), **Ruby Sorbet** (narrow adoption — deferred in `1319q`), **TS type inference without annotation** (`let foo = new Foo()` — "we don't reimplement TSC", `1319q`). Rust `Type::method()` associated-fn, Scala, PHP `use`-statement resolution are MEDIUM-feasibility and may fold into Phase 1+ later but are not committed here.
- Any change to the post-build cross-file rewrite pass semantics (`:6278-6365`) beyond what import-table resolution makes redundant.

## Acceptance Criteria

- [x] AC-1: A `Type.method()` call whose receiver type is **imported from another project file** and is **ambiguous by simple name** (a same-named class in another package) resolves to the correct project method node, picked by the source file's `import`. **Satisfied via the language-agnostic rewrite-pass disambiguation** (see the Implementation Pivot note — *not* per-resolver `import_targets` threading): `test_java_ambiguous_import_disambiguates` verifies `App` importing `com.foo.Helper` resolves to `com/foo/Helper.java`, not the `com.bar` twin. (Unambiguous cross-file `Type.method()` already resolved pre-change via the existing rewrite pass.)
- [x] AC-2: Python ambiguous cross-file resolution works (`test_python_ambiguous_import_disambiguates`: `app` importing `pkg_a.models.User` resolves `u.save()` to `pkg_a`, not the `pkg_b` twin). **The unannotated-lazy-loader shape is now RESOLVED** — the original out-of-scope deferral was **reversed at operator direction** (2026-06-09). `gq = _load_graph_query()` (→ `_load_script("graph_query")`) and direct `v = _load_script("mod")` bind `v.Class.method()` / `v.func()` / inline `_load_X().func()` to the loaded module's symbols (`test_python_lazy_loader_*`), closing this repo's `from_root`-has-0-edges hole (**0→12** in-edges). `test_ambiguous_without_import_stays_external` pins that disambiguation never *guesses* without an import.
- [x] AC-3: `GRAPH_BUILDER_VERSION` is bumped **from `"23"` to `"24"`** in the same change; a stale on-disk graph triggers the full auto-rebuild (`graph_query.py:199-205`), and a rebuild-success assertion confirms the rebuilt graph carries `"24"` (and is non-empty: node/edge counts ≥ the pre-rebuild baseline). Verified the constant changed and the payload/state carry the new version.
- [x] AC-4: Consumer safety under a denser graph — no token-cap regressions: `code_callhierarchy` (uncapped lists) and `code_callgraph` (depth>1 combinatorial) on a high-fan-in cross-file symbol stay within the response budget; betweenness still computes below the 10k-node skip (`graph_query.py:1419-1425`). Spot-checked on the self-hosted graph post-rebuild.
- [x] AC-5: The flipped negative-assertion tests (`test_graph_indexer.py:1509-1516`/`:1551-1559`/`:1577-1590` — only the imported-and-typed cases) are updated to assert the new resolved behavior; genuinely-unannotated negatives remain. New positive cross-file tests added per language.
- [x] AC-6: `run_tests.py` + docs-lint green. The `test_graph_query.py` in-memory `FIXTURE_GRAPH` tests are unaffected (they use synthetic edges).
- [x] AC-7: **Downstream validation — re-run `code_risk_score` AC-8 as the `1p47e` stage gate.** Run it after the **FULL `1p470` lands (Phase 1 typed-language *and* Phase 2 Python resolution)** and the graph rebuilds — the gate's sample is this repo's modules, which are Python-heavy, so the cross-file blast-radius signal they gain comes from **Phase 2**; measuring after Phase 1 only would under-read it. Sample **≥10 real modules spanning low/medium/high fan-in**. Two-part condition, evaluated by `1p41o` AC-8: **(a) PRECONDITION** — `affected_file_count` must be **non-degenerate** (coefficient of variation ≥ 0.3 across the sample; the `1p41l` NO-GO baseline had it flat in 46%) — if still near-constant, FAIL FAST → re-defer `1p41o`; **(b)** if non-degenerate, compute Spearman ρ(risk, fan_in) and apply AC-8's pass-condition. Record the sampled module list, per-module `affected_file_count`, the computed CoV, and ρ (pre- and post-fallback) as auditable gate evidence. This change ships regardless; AC-7 is the measurement, not a ship-gate for `1p470` itself.

## Tasks

> **These tasks reflect the pre-pivot `import_targets` plan.** The shipped work took the rewrite-pass disambiguation + lazy-loader approach instead (see the Implementation Pivot note); actual work and verification live in the reconciled Acceptance Criteria and the Progress Log. The first two tasks (per-resolver `import_targets` seam/threading) were intentionally **not** done — the rewrite-pass approach made them unnecessary. The `docs/architecture/graph-index-system.md` update is **DEFERRED** per operator ("defer the document path").

- [~] ~~Extract the TS `import_targets` mechanism into a reusable per-language import-table seam.~~ *(superseded — rewrite-pass disambiguation approach)*
- [~] ~~Phase 1: wire import-table resolution into the Java/Kotlin/C#/Go receiver resolvers.~~ *(superseded — one language-agnostic rewrite-pass disambiguation covers all of them via the already-emitted import edges)*
- [~] ~~Phase 2: thread `import_aliases` into Python `CallCollector._resolve_call`.~~ *(superseded — Python cross-file disambiguation handled in the rewrite pass; lazy-loader return-type inference added in the extractor instead)*
- [x] Bump `GRAPH_BUILDER_VERSION` (23→24); rebuild; verify auto-rebuild path.
- [x] Update negative tests + add per-language cross-file positive tests. *(negatives correctly stay negative; 6 new positive/disambiguation/lazy-loader tests added — suite 2936→2946 green)*
- [x] Run the `code_risk_score` AC-8 harness on the rebuilt graph; record the go/no-go for `1p41o`. *(PASS — pooled ρ=0.796 / CoV=0.981; recorded in `1p41o` AC-8 + Progress Log)*
- [~] Update `docs/architecture/graph-index-system.md` + `docs/specs/mcp-tool-surface.md`. *(`mcp-tool-surface.md` updated via `1p41o`; `graph-index-system.md` cross-file-resolution extension DEFERRED per operator — "defer the document path")*

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| import-table seam (generalize 1p2tf) | Engineering | — | reusable per-language map; the structural core |
| Phase 1: Java/Kotlin/C#/Go resolvers | Engineering | import-table seam | likely one change per language (precedent: 1312l/13194/1319a) |
| Phase 2: Python static-import resolution | Engineering | import-table seam | `import_aliases` already built |
| version bump + rebuild + consumer-safety | Engineering | Phase 1, Phase 2 | one `GRAPH_BUILDER_VERSION` bump covers all phases in a wave |
| test flips + code_risk_score AC-8 re-run | Engineering | version bump | downstream validation; informs 1p41o re-admission |


## Serialization Points

- `.wavefoundry/framework/scripts/graph_indexer.py` — all per-language resolvers + the shared `GRAPH_BUILDER_VERSION` constant live here; sequence per-language edits and bump the version **once** for the whole wave (not once per language) to avoid redundant rebuilds.
- The post-build cross-file rewrite pass (`:6278-6365`) interacts with the new index-time resolution — ensure no double-resolution (a now-resolved edge must not also be re-promoted). Coordinate the two.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — update the receiver-resolution / confidence-model description to reflect cross-file import-table resolution (currently documents intra-file-only). No new module boundary; the extractor's resolution stage gains an import-table input. `docs/specs/mcp-tool-surface.md` confidence notes may need a one-line update.

## AC Priority


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | Phase-1 core capability — cross-file `Type.method()` resolution for Java/Kotlin/C#/Go is the wave's enabling deliverable. |
| AC-2 | required   | The Python half of cross-file resolution; the explicit unannotated-lazy-loader boundary keeps scope honest. |
| AC-3 | required   | Version-bump invariant — without the `GRAPH_BUILDER_VERSION` bump, stale on-disk graphs never rebuild and the new edges never appear. |
| AC-4 | required   | Consumer-safety regression gate — a denser graph must not blow `code_callhierarchy`/`code_callgraph` token budgets or the betweenness skip. |
| AC-5 | required   | Test correctness — the flipped negatives plus new positive cross-file tests are what prove the resolution behavior. |
| AC-6 | required   | Suite + docs-lint green is the baseline regression gate. |
| AC-7 | required   | The stage-gate measurement (≡ `1p41o` AC-8) — the go/no-go that decides whether `1p41o` proceeds; the wave's headline decision. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Scoped from a grounded investigation (3-agent workflow over `graph_indexer.py` + wave history). Captured the exact resolution seam, per-language feasibility table, prior-art timeline, consumer-impact matrix, and the `GRAPH_BUILDER_VERSION` obligation. Not yet admitted to a wave. | Investigation findings + `project_mcp_code_tool_quality_log` session-7 entry; `1p41o` gate-out evidence in its (deferred) change doc. |
| 2026-06-09 | **Gate baseline re-measured (pre-implementation).** The `1p41l` NO-GO was on an older, sparser graph; the live graph had already improved (1,332 `RECEIVER_RESOLVED` edges, 27% flat not 46%). On n=1200 self-host symbols: CoV(afc)=0.65 (precondition PASS), ρ(direct risk,fan_in)=0.93 ≤ 0.95 (PASS), ρ(rank-norm fallback)=0.91. **Gate already passed before any 1p470 work** — the premise that cross-file resolution was *required* to unblock `1p41o` no longer held. | Inline measurement via `GraphQueryIndex.graph_impact` + manual CoV/Spearman over 1200 function/method nodes. |
| 2026-06-09 | **Implemented (operator-directed pivot — see header).** (a) **Lazy-loader return-type inference** in the Python extractor (`graph_indexer.py`): recognizes the sibling-script loader idiom `def _load_X(): return _load_script("mod")` + direct `v = _load_script("mod")`, tracks loader-assigned module vars, and resolves `v.Class.method()` / `v.func()` / inline `_load_X().func()` to the loaded module's symbols. (b) **Language-agnostic import-disambiguation** in the cross-file rewrite pass: an ambiguous `external::Type.method` is filtered to the candidate whose defining module matches the SOURCE FILE's `imports` edge for `Type`. (c) `GRAPH_BUILDER_VERSION` `23`→`24`; graph rebuilt. 6 new tests; full suite **2936 green**. | `from_root` 0→**12** in-edges (graph_query.py symbols total 66, was ~0); synthetic Python+Java disambiguation tests resolve to the imported twin, not the other; `test_ambiguous_without_import_stays_external` proves no over-resolution. |
| 2026-06-09 | **AC-7 stage gate RE-RUN on the rebuilt v24 graph → PASS.** n=1200 self-host function/method symbols: CoV(affected_file_count)=**0.652** (≥0.30 precondition PASS); Spearman ρ(risk, fan_in)=**0.9203** direct / **0.9083** rank-norm fallback (both ≤0.95). The lazy-loader edges *improved* the margin (ρ 0.931→0.920) by adding blast-radius variance. `1p41o` is **GO**. | Re-measurement on `project-graph.json` (builder_version=24, 7230 nodes / 21059 edges). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | **Phase the work: typed langs (Java/Kotlin/C#/Go) + Python static imports first; defer lazy-loader/trait-dispatch/header-split/Sorbet residuals.** | The dominant cross-file call pattern (static imports + statically-knowable receiver types) is the high-coverage, low-risk win and reuses the proven `1p2tf` `import_targets` pattern; the residuals each need a distinct, heavier mechanism (call-return-type inference, trait resolution, header parsing) with diminishing returns. | One mega-change covering all languages (rejected — large, risky, mixes tractable + hard); skip and keep `code_risk_score` permanently deferred (rejected — this also fixes a real `code_impact` limitation independent of the tool). |
| 2026-06-08 | Replicate the TS `import_targets` mechanism rather than invent a new resolver. | It is the proven, shipped pattern (`1p2tf`) for exactly this problem; import statements for the Phase-1 langs are already parsed (imports edges exist), so the marginal work is threading a map, not new parsing. | Rely on the post-build cross-file rewrite pass alone (rejected — it only promotes globally-unambiguous names, so it misses collision-heavy real codebases); full type-inference pass (rejected — reimplementing each language's type checker). |
| 2026-06-08 | The literal `from_root`-has-0-edges example is in the **deferred** bucket. | It is the unannotated lazy-module-loader shape needing call-return-type inference, not the import-table case; honesty about this prevents over-promising that Phase 1 fixes this repo's own headline example. | Frame Phase 1 as fixing `from_root` (rejected — inaccurate; it fixes the dominant static-import pattern, of which `from_root`'s repo uses a non-static variant). |
| 2026-06-09 | **REVERSED the lazy-loader deferral; built it, scoped to the sibling-script loader idiom (`_load_script("mod")`).** | Operator directed it explicitly ("fix the lazy loader option for python"), and it is the *actual* self-host blast-radius hole — gate-relevant and the only change that adds self-host edges. The "heavier call-return-type inference" feared in 2026-06-08 was unnecessary: the idiom is a recognizable closed-form pattern (return `_load_script("<literal>")`), not general type inference. Harmless for consumer projects that don't use the idiom (the recognizer simply never fires). | General return-type inference (rejected — large, unneeded for this pattern); leave deferred (rejected — operator-directed and it is the gate-relevant hole). |
| 2026-06-09 | **Cross-file disambiguation via the post-build rewrite pass, NOT per-language `import_targets` threading.** | Measurement: of 5,027 unresolved `external::` calls-edges on the self-host, 4,651 are genuinely external (stdlib) and **0** were ambiguous-project-import cases — unambiguous cross-file already resolves via the existing rewrite pass. A single import-edge-based disambiguation in that pass — language-agnostic by construction, **verified for Python + Java** (C#/Go/Rust need the `1p4ef` import-head fix before it fires there) — with far less surface than threading a map through 5 resolvers, and reuses the `imports` edges every extractor already emits. | Per-language `import_targets` threading (rejected — 5× the surface for ~nil marginal self-host value; the rewrite pass already had the project-wide symbol view the disambiguation needs). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Graph densification (more cross-file edges) widens `code_impact` blast radius, shifts fan_in/fan_out/chokepoint/betweenness rankings, and creates new shortest paths. | Mostly *desirable* (that's the point), but verify no token-cap blowouts (AC-4) and re-baseline `wave_graph_report` expectations; betweenness centrality shifts are expected and correct. |
| Double-resolution: an edge resolved at index time AND re-promoted by the post-build rewrite pass. | Audit the rewrite pass interaction (Serialization Points); the pass already skips non-`external::` targets (`:6280`), so index-time-resolved edges should be inert to it — verify. |
| Per-language import-statement grammar variance (Java `import a.b.C;`, Kotlin `import a.b.C`, C# `using`, Go `import "p/q"` with alias). | Each is tree-sitter-parseable and imports edges already exist; build the name→node map from the existing import extraction rather than re-parsing. |
| Missing the version bump → consumers read stale cached graphs with mixed edge shapes. | AC-3 makes the bump a required, same-change obligation; the framework rule + the auto-rebuild path enforce it. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
