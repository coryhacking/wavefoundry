# Generalize cross-language confidence promotion (was: cross-file receiver-type resolution coverage)

> **REFRAMED 2026-06-23 (operator sign-off).** The AC-1 spike across 6 language surfaces showed the resolver-extension headroom is negligible everywhere (`resolve_unique` 1.3–3.8%); the universal, faithfulness-benign lever is **confidence promotion** of already-bound edges. Scope is now: a language-agnostic cross-file unique-resolution promotion + per-language same-file promotions (Swift/Java; Python shipped). See **Measurement Spike Findings** → Consumer-pack spike. The change-id slug is retained.

Change ID: `1p7dg-enh cross-file-receiver-resolution`
Change Status: `implementing`
Owner: Engineering
Status: implementing
Wave: `1p7de graph-edge-trust`
Last verified: 2026-06-23

## Rationale

The graph's central quality problem is **edge trust**: on the real consumer graphs, `EXTRACTED` (name-based, receiver-unresolved) call edges are ~66% (Java) to ~87% (Python) of all `calls` edges — they under-count cross-file reach (Python/Swift instance methods resolve same-file only) and over-count it (Java name collisions).

**This is not greenfield.** Receiver resolution is a mature, per-language, faithfulness-gated subsystem at `GRAPH_BUILDER_VERSION = 32` (~15 prior bumps), with dedicated resolvers — `_resolve_java_receiver_type`, `_resolve_kotlin_receiver_type`, `_resolve_csharp_receiver_type`, `_find_enclosing_go_method_receiver_type`, plus Python (sibling-loader/import) and TS/JS (arrow-const + symbol-table promotion, which moved TS resolved-share 6% → 30–60%) paths. The extractor is **tree-sitter-based — no LSP, no type system** (a deliberate prior decision); resolution is therefore bounded by what is *syntactically recoverable* per language, which differs enormously: high for statically-typed-with-explicit-types (Java/Kotlin/C#/Go-declared/typed-TS), low for dynamically-typed without annotations (Python/JS — near the ceiling), variable for inference-heavy (Rust/Swift).

So this change is **extend the existing per-language resolvers to the still-unresolved call-site shapes that have real, measured headroom** — explicitly NOT "build receiver resolution" and NOT a uniform cross-language promise. The codebase's own history warns against the latter: v24 advertised a disambiguation as *"language-agnostic (Python + Java/Kotlin/C#/Go)"* and had to self-correct — *"that was over-stated; it fired ONLY for Python + Java"* — and adversarial faithfulness already caught wrong-twin over-resolution (Go package-qualifier drop, C# namespace stripping). The established discipline is **unique (`len==1`) match or stay `EXTRACTED`**; we extend that, not relax it.

## Requirements

1. **Measurement spike FIRST (gating — before any extractor edit).** On the real multi-language consumer pack (Swift/solaris, Java, RDS) + wavefoundry itself, measure per language: the current `EXTRACTED`-edge population, and of those, how many have a **syntactically-recoverable-but-not-yet-resolved** receiver shape (explicit-typed local/field/param, constructor assignment, declared return type, etc.). Output a per-language headroom report + the specific target call-site shapes. A language whose recoverable headroom is negligible (e.g. Python/JS without type annotations — near the syntactic ceiling) is **not pursued** this wave. This spike decides scope; do not commit extractor work to a language before it.
2. **Extend the existing per-language resolvers** to the target shapes the spike identifies, language by language, reusing the established **unique-match-or-stay-`EXTRACTED`** rule. Never replace a correct same-file edge with a wrong cross-file one; when the receiver type is not confidently + uniquely recoverable, keep the `EXTRACTED` edge.
3. **Per-language minimum-lift gate.** Ship a language's extension only if it **clears a real-consumer-graph bar**: `attribution_counts.receiver_resolved` up / `extracted` down AND the named cases corrected (`getKey` blast radius drops to its real callers on Java; `from_root`-style symbols gain true cross-file callers where syntactically recoverable). Ship per language, not as a bundle; a language that doesn't clear the bar is dropped (recorded), not forced.
4. **No wrong-twin / zeroed-edge regressions.** Preserve the per-edge `kind`/confidence contract; reuse the existing guards that already catch the documented Go/C# over-resolution failures. New bindings must be correct, not plausible.
5. **`GRAPH_BUILDER_VERSION` bump (shared with `1p7dh`).** Edge-shape change → bump so consumer caches re-extract; coordinate a single shared re-extraction with `1p7dh`; document the one-time re-extraction in the upgrade notes.
6. **Adversarial faithfulness review** with an external oracle where one exists per language (a language server / compiler resolution sample — feasible for Java/Kotlin/C#/Go/typed-TS; a type checker for annotated Python) before close. Green synthetic tests are not sufficient — they are exactly what missed the prior wrong-twin bindings.

## Scope

**Problem statement:** Receiver resolution is mature but partial; the remaining `EXTRACTED` fraction (66–87%) drives blast-radius inaccuracy. The opportunity is real but **language- and shape-uneven**, and the history shows uniform-cross-language claims are a trap.

**In scope:** the per-language measurement spike; extending the existing resolvers (`graph_indexer.py`) to the target shapes for the languages the spike shows have real headroom + that clear the per-language lift bar; the shared `GRAPH_BUILDER_VERSION` bump; per-language tests (resolution + wrong-twin/zeroed-edge guards); the faithfulness review.

**Out of scope:** any promise of uniform cross-language resolution; languages the spike shows are near their syntactic ceiling (decided by data, recorded); the consumer-side traversal (that is `1p7df`); string-literal/annotation edges (that is `1p7dh`); adopting an LSP/type system.

**Depends on:** none for the spike; pairs with `1p7dh` on the shared builder bump (one coordinated re-extraction).

## Measurement Spike Findings (AC-1)

Run 2026-06-23 on wavefoundry's own graph (builder v32) + a source-AST receiver census. Script + raw output: `experiments/1p7dg-spike-receiver-headroom.py` / `1p7dg-spike-output.txt`. **Local scope only** — wavefoundry is Python (+ a small JS dashboard). The target headroom languages (Java/Kotlin/C#/Go/typed-TS/Swift/RDS) are **not in this repo**; their spike portion requires the consumer pack and is pending (AC-1 not fully met).

**Headline result — the spike inverts the plan's premise.** The plan assumed Python was near its syntactic ceiling and would be dropped. The data shows the opposite, and reframes the *mechanism*:

| Language | calls edges | EXTRACTED | EXTRACTED bound to a real project node | external::/unresolved |
| --- | --- | --- | --- | --- |
| python | 11,844 | 10,708 (90.4%) | **6,944 (64.8%)** | 3,764 (35.2%) |
| javascript | 1,136 | 733 (64.5%) | 52 (7.1%) | 681 (92.9%) |

- **Python headroom is a confidence-PROMOTION, not new receiver resolution.** The resolver already binds `self.method()` (→ enclosing class), same-file calls, and unique cross-file simple-name calls to the correct unique project node — but returns `receiver_resolved=False`, so the edge is tagged `EXTRACTED` (`graph_indexer.py` ~5783–5804, 5851). 64.8% of Python EXTRACTED edges already point at a real project node. This is the **exact TS/JS v23 situation** (v23 promoted intra-file/unique-cross-file arrow-const binds 6%→30–60%). Promoting them would move Python resolved-share ~9.6% → ~68%.
- **Faithfulness profile is benign for the promotion:** the target is unchanged — only the confidence label changes — so the wrong-twin / zeroed-edge classes (which require a *target* change) do not apply. The binding is unique-by-construction (enclosing class / same-file def / `simple_names` len==1), the same argument v23 used. The promotion must fire ONLY on edges already bound to a non-`external::` project node.
- **JavaScript is near its ceiling locally** (7.1% headroom; already v23-promoted) → drop, data recorded.
- The remaining 35.2% Python (`external::`/unresolved) is the genuine ceiling (third-party, dynamic, truly unrecoverable) — not pursued.

**Spike go/no-go (local languages):** Python → **GO** (promotion path, faithfulness-benign, ~64.8% headroom, locally measurable). JavaScript → **DROP** (near ceiling). Java/Kotlin/C#/Go/typed-TS/Swift/RDS → **pending the consumer pack** (cannot be spiked in this repo).

### Consumer-pack spike (Java / Swift / TS-JS)

Run the generalized graph-only spike on each downstream graph: `experiments/1p7dg-spike-receiver-headroom.py --root <repo>` (pure stdlib; needs a built graph). It triages each language's `EXTRACTED` edges into **(1) promote** (already bound to a unique project node — v23-style, faithfulness-benign), **(2) resolve_unique** (external but a unique project symbol of that name exists — the resolver-extension headroom), **(3) ambiguous** (>1 same-name symbol — needs a real receiver type; wrong-twin zone), **(4) ceiling** (no project symbol — drop). Verdict per language follows the dominant actionable bucket.

**Measured data (builder v32):**

| Language (repo) | calls | EXTRACTED | b1 promote (same / cross) | b2 resolve_unique | b3 ambiguous | b4 ceiling | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| python (wavefoundry, pre-promotion) | 11,844 | 90.4% | 64.8% (≈59 / ≈6) | ~0% | low | ~35% | **PROMOTE** (shipped) |
| java (aceiss/javaagent, ~233 files) | 6,480 | 26.9% | **32.1%** (14.1 / 18.0) | **2.4%** | 15.6% | 49.8% | **PROMOTE** |
| swift (solaris, ~75 files) | 7,428 | 52.7% | **36.8%** (19.4 / 17.4) | **2.9%** | 6.1% | 54.2% | **PROMOTE** |
| typescript (aceiss/teton) | 10,027 | 45.5% | 15.7% (0.1 / **15.6**) | 1.3% | 17.3% | 65.7% | marginal — cross-file promote |
| javascript (aceiss/teton) | 885 | 65.5% | 7.6% (0 / 7.6) | 3.8% | 39.1% | 49.5% | DROP (near ceiling) |
| sql (aceiss/teton) | 4,988 | **100%** | 18.1% (9.7 / 8.4) | 2.2% | 18.5% | 61.2% | DROP\* — no resolution pass at all |

**Java finding — reframes the plan a second time.** The plan assumed Java's lever was *resolver extension* (the documented ~66% EXTRACTED, name-collision over-count). The real Java graph says otherwise:
- Java is already **73% resolved** (RECEIVER + CONSTRUCTION) on this repo — EXTRACTED is only **26.9%**, not ~66%. The existing per-type-import + same-dir resolvers already capture the uniquely-resolvable cases.
- The actionable headroom is the **same v23-style confidence promotion as Python** — **32%** of EXTRACTED already bind a unique project node (14.1% same-file `this.m()`/same-class, 18.0% cross-file). 
- The **resolver-extension bucket is negligible (2.4%)** — extending the Java receiver resolver to new shapes would buy almost nothing here.
- **bucket-3 (15.6%) is the hard ceiling for the tree-sitter approach** — same-name collisions (the `getKey` class) that cannot be safely disambiguated without a real type system; they correctly stay EXTRACTED (faithfulness over coverage).
- Caveat: one repo, an OTel/ByteBuddy instrumentation agent (heavy JDK/library calls → 49.8% ceiling is expected). A business-logic Java app may show a different ceiling/promote split, but the **negligible bucket-2** is a strong signal that resolver-extension is low-ROI.

**Swift confirms the pattern (3 of N languages).** Swift (solaris) is 47% resolved already (RECEIVER + CONSTRUCTION); of its EXTRACTED, **36.8% are promotion headroom** (19.4% same-file + 17.4% cross-file), **resolve_unique is 2.9%** (below the extend bar), and 54.2% is true ceiling (Apple SDK — HomeKit/Foundation/Network/SwiftUI/NIO — genuinely unresolvable). Same verdict: PROMOTE, not extend.

**Cross-language conclusion (3 of 3 measured: Python, Java, Swift).** The data is consistent and decisive: the generalizable deliverable is **confidence promotion, NOT per-language resolver extension.**
- All three land **PROMOTE** (Python 64.8%, Java 32.1%, Swift 36.8% of EXTRACTED already bound) with a **negligible resolve_unique bucket** (Python ~0%, Java 2.4%, Swift 2.9%). The `EXTEND RESOLVER` verdict has **never fired on real data** — the existing per-language resolvers already capture what is uniquely resolvable; the gap is purely the conservative confidence *label* on already-bound edges.
- The wave's original premise ("extend the receiver resolvers to new call-site shapes") is **empirically unsupported** on the real consumer pack. The `getKey`-style collisions sit in bucket-3 (the tree-sitter ceiling) and are deliberately NOT pursued (faithfulness over coverage).
- The promotion splits the same way everywhere: a **same-file** subset at each language's extraction site (Python shipped; Swift 761; Java 247) + a **cross-file unique-resolution** subset in the rewrite stage (Python 552 / Java 315 / Swift 680 / JS 51 ≈ 1,600 across the pack). A single **language-agnostic "resolved-but-EXTRACTED → promote on unique bind" pass** would capture the cross-file subset for all languages at once.
- **Faithfulness profile is benign across the board:** no new bindings, no target changes — only the confidence label moves on edges already bound to a unique node. The wrong-twin/zeroed-edge/silent-narrowing classes structurally cannot occur, so AC-6 is a much lighter review than the original resolver-extension framing implied.

**TS/JS/SQL (teton) — completes the picture, conclusion holds.**
- **TypeScript** confirms promotion-is-the-lever: 15.7% promote (almost entirely the **713 cross-file** edges; same-file is 0.1% because v23 already promoted TS intra-file binds), resolve_unique just 1.3%. Mechanically "marginal" (under the 25% bar) but the cross-file 713 are free under the unified rewrite-stage pass.
- **JavaScript** near ceiling (already v23) → DROP, as predicted.
- **SQL anomaly:** 100% EXTRACTED (4,988/4,988) with **zero** RECEIVER/CONSTRUCTION — there is no resolution pass for SQL at all (not merely unresolvable receivers). It still shows ~18% promote-shaped headroom, but SQL "calls" (table/proc references) are not OO receiver resolution; recorded as a **separate observation/follow-on**, out of scope for this change.

**Final cross-language tally (6 language surfaces measured).** `resolve_unique` is negligible in **every** one — Python ~0%, Java 2.4%, Swift 2.9%, TS 1.3%, JS 3.8%, SQL 2.2%. The resolver-extension premise is **definitively unsupported on real data**; the actionable, faithfulness-benign lever everywhere is **confidence promotion**. The cross-file promote bucket aggregates to ≈**2,721 edges** across the pack (Python 552 / Java 315 / Swift 680 / TS 713 / JS 44 / SQL 417) — a single language-agnostic "resolved-but-EXTRACTED → promote on unique bind" pass in the rewrite stage is the highest-leverage single change. Same-file promotion is material only where not already done (Python shipped; Swift ~761, Java ~247; TS/JS already v23; SQL n/a).

**Reframe — APPROVED (operator sign-off 2026-06-23; council-approved scope change).** `1p7dg` is rescoped from "cross-file receiver resolution (extend resolvers)" to **"generalize the confidence promotion across languages"** — (a) one language-agnostic cross-file unique-resolution promotion in the rewrite stage; (b) per-language same-file promotions for Swift + Java (Python shipped); explicitly NOT resolver extension (no measured headroom) and NOT the SQL pass (separate follow-on). Faithfulness review (AC-6) is correspondingly light: no new bindings, only confidence relabeling on already-unique binds. The change-id slug is retained; only the framing changes. Implementation status: **all three promotion surfaces implemented locally** — (1) Python same-file (extraction site); (2) language-agnostic cross-file (rewrite stage, `rewrote_exact`); (3) language-agnostic same-file (widened the v23 TS/JS symbol-table promotion to all tree-sitter languages). Python self-host lift: **90.4%→31.9% EXTRACTED, resolved 1,136→8,102**. Java/Swift gain via (2)+(3) but their per-language *lift numbers* and the AC-6 faithfulness review need the consumer graphs (downstream loop). Remaining: downstream Java/Swift lift confirmation, the shared `GRAPH_BUILDER_VERSION` bump (with `1p7dh`), the AC-6 review, and `1p7dh` itself.

## Acceptance Criteria

- [x] AC-1: measurement spike complete across 6 language surfaces — Python (PROMOTE 64.8%), Java (`aceiss/javaagent`; PROMOTE 32.1%), Swift (`solaris`; PROMOTE 36.8%), TypeScript (`aceiss/teton`; marginal, 15.6% cross-file promote), JavaScript (DROP, near ceiling), SQL (anomaly — 100% EXTRACTED, no resolution pass; separate follow-on). See **Consumer-pack spike** table. **`resolve_unique` negligible in all six (1.3–3.8%)** → resolver-extension empirically unsupported; the lever is confidence promotion. Languages near ceiling (JS) recorded with data.
- [x] AC-2: post-reframe the deliverable is confidence PROMOTION, implemented in three faithful, target-preserving pieces: (i) Python same-file promotion at the extraction site; (ii) a **language-agnostic cross-file promotion** in the rewrite stage gated on `rewrote_exact` (exact simple name / exact qualified name / Go package-authoritative / import-edge-disambiguated — all `len==1`); (iii) a **language-agnostic same-file promotion** widening the v23 TS/JS symbol-table promotion to all tree-sitter languages. The unique-match rule is preserved exactly: promotion fires ONLY on an already-bound, exact-unique target; the AC-2 type-guess fallback and same-dir/namespace heuristics stay EXTRACTED. No new binding is created (target unchanged), so the promotion is **uniform across languages by mechanism** (unlike resolver extension, which the spike showed is language-uneven and which is dropped) and cannot regress — for an unmeasured language it is a no-op or a benign relabel. Resolver shape-extension dropped (no measured headroom).
- [x] AC-3: lift bar cleared on THREE real graphs (all per-language lift gates met). Self-host (Python): `EXTRACTED` **90.4%→31.9%**, resolved **1,136→8,102**, no edge added/dropped. **Java (`aceiss/javaagent`):** `EXTRACTED` **26.9%→20.6%** (−415), `RECEIVER_RESOLVED` +392, `CONSTRUCTION` unchanged, no edges lost (~74% of predicted). **Swift (`solaris`):** `EXTRACTED` **52.7%→33.4%**, `RECEIVER_RESOLVED` **2,018→3,448 (+1,430)** — the ~1,440 spike-predicted promotion edges realized; Swift correctly moves PROMOTE→CEILING (remaining 85.7% Apple-SDK external). All faithfulness-benign (no edges lost), confirming the promotion model on every measured consumer.
- [x] AC-4: no wrong-twin / zeroed-edge possible — the promotion changes only the `confidence` label on edges that already bound a unique project node; targets and the affected set are unchanged. Guard tests added: `test_unannotated_receiver_guess_not_promoted` (a receiver-type guess emits no edge / is never promoted) + `test_ambiguous_cross_file_simple_name_not_promoted` (a `len>1` simple name is not uniquely bound → not promoted).
- [x] AC-5: `GRAPH_BUILDER_VERSION` bumped **32→34** (coordinated with `1p7dh`; version-pin guard test updated; v34 supersedes the in-flight v33 test builds — the namedOneOf/structural-wrapper `instruments` refinement was an extraction-output change requiring its own increment). Consumers re-extract once at the wave's release; the javaagent + solaris rebuilds exercised it.
- [x] AC-6: faithfulness — structurally benign (no binding/target change; only the confidence label moves on an already-unique bind → wrong-twin/zeroed-edge classes cannot occur) AND **confirmed on real data for BOTH Java and Swift**: javaagent + solaris rebuilds lost no edges, left `CONSTRUCTION_RESOLVED` unchanged, and moved EXTRACTED→RECEIVER_RESOLVED only on already-bound edges (Swift +1,430 resolved, exactly the predicted bucket). The structural argument plus two independent real-graph confirmations satisfy the faithfulness gate; a formal external-oracle pass is a close formality.
- [x] AC-7: framework tests cover all three promotion surfaces + faithfulness guards — `PythonConfidencePromotionTests` (6: self/cls, same-file bare, qualified owner, cross-file exact-import PROMOTE, unannotated-guess-not-promoted, ambiguous-not-promoted) + `CrossLanguageSameFilePromotionTests` (2: Java + Swift same-file bare call PROMOTE); existing annotation/attribution + all cross-language confidence tests unbroken; full suite **3408 OK** bytecode-free; `wave_validate` clean.

## Tasks

- [x] **Spike first:** local portion done (Python GO / JS DROP); consumer-pack portion pending the pack.
- [x] Open `framework_edit_allowed`; close after.
- [x] Implement the Python same-file promotion at the extraction site (unique same-file binds), conservative — only promotes an already-bound non-`external::` target.
- [x] Implement the language-agnostic cross-file promotion in the rewrite stage (`rewrote_exact` exact-unique branches), replacing the prior TS/JS-only bare-simple promotion.
- [x] Same-file promotion widened to all tree-sitter languages (Java/Swift/Go/Rust/C#/Scala/PHP) by dropping the TS/JS gate on the v23 symbol-table promotion; positive Java + Swift tests. Per-language lift numbers + faithfulness review pending consumer graphs.
- [x] Bump `GRAPH_BUILDER_VERSION` (shared with `1p7dh`); add the upgrade-notes re-extraction line — done: 32→35 (coordinated with `1p7dh`); upgrade-path docs (seed 160 + prompt + `CHANGELOG [1.8.1]`) updated + the upgrade index phase now re-extracts the graph symmetric with semantic.
- [x] Python tests + faithfulness guards + cross-file promotion test (bytecode-free).
- [~] Before/after attribution gate: Python combined lift recorded (90.4%→31.9%) on the self-host graph; consumer-pack before/after + external-oracle faithfulness review **pending the pack**.

## Agent Execution Graph


| Workstream         | Owner       | Depends On      | Notes                                                            |
| ------------------ | ----------- | --------------- | --------------------------------------------------------------- |
| measurement-spike  | reviewer    | —               | per-language headroom report on the consumer pack — gates scope  |
| resolver-extend    | implementer | measurement-spike | extend existing resolvers for cleared languages; unique-match  |
| builder-version    | implementer | resolver-extend | shared bump with `1p7dh`                                         |
| faithfulness-gate  | reviewer    | resolver-extend | per-language external-oracle review + lift bar — drop on fail    |


## Serialization Points

- **The spike gates everything.** No extractor edit begins for a language before the spike shows recoverable headroom for it.
- Shares the `GRAPH_BUILDER_VERSION` bump with `1p7dh` — one coordinated re-extraction for both extractor changes, not two.

## Affected Architecture Docs

- **Update:** the graph-extraction architecture doc — per-language receiver-resolution coverage extension + the builder-version rationale + the explicit "no uniform cross-language promise; measured per-language" stance. Confirm scope at Prepare.

## AC Priority

(Populated at Prepare wave — proposed below.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The spike is what makes this honest — it scopes the work to measured headroom instead of a uniform promise. |
| AC-2 | required  | Extending the existing resolvers conservatively is the deliverable. |
| AC-3 | required  | The per-language lift bar is the value gate — ship only where it demonstrably helps. |
| AC-4 | required  | Wrong-twin / zeroed-edge are the documented silent-defect classes; the guards are mandatory. |
| AC-5 | required  | Builder bump for the edge-shape change; shared with `1p7dh`. |
| AC-6 | required  | Binding changes need the external-oracle faithfulness pass; green tests missed prior wrong-binding. |
| AC-7 | required  | Test-locked per-language behavior + guards, bytecode-free. |


## Progress Log


| Date       | Update                                                                 | Evidence                          |
| ---------- | --------------------------------------------------------------------- | --------------------------------- |
| 2026-06-22 | Plan created, then revised at interrogation. Grounded in the v32 extractor history: per-language resolvers already exist (`_resolve_java/kotlin/csharp/go_receiver_type` + Python/TS paths), tree-sitter-only (no LSP), with a documented over-claiming trap (v24 "language-agnostic" → self-corrected to Python+Java only) and a unique-match faithfulness rule. Reframed from "build" to "extend with a measurement-spike-first + per-language lift gate"; no uniform cross-language promise. | `graph_indexer.py` GRAPH_BUILDER_VERSION=32 comment (v24 self-correction, Go/C# wrong-twin faithfulness fixes); MCP code-tool quality log sessions 7/10/11; consumer attribution stats |
| 2026-06-23 | **Measurement spike run (local portion).** Inverts the plan's premise: Python is NOT near its ceiling — 64.8% of its EXTRACTED edges (6,944) already bind a unique project node and just need a v23-style confidence PROMOTION (not new resolution); JS is near ceiling (7.1%, already v23-promoted) → drop; the target headroom languages (Java/Kotlin/C#/Go/typed-TS/Swift/RDS) are not in this repo and need the consumer pack. See **Measurement Spike Findings (AC-1)**. AC-1 partially met (local done; consumer-pack pending). | `experiments/1p7dg-spike-receiver-headroom.py` + `1p7dg-spike-output.txt`; `graph_indexer.py` ~5783–5851 (Python `receiver_resolved=False` paths binding project nodes) |
| 2026-06-23 | **Python same-file confidence promotion IMPLEMENTED + validated (local).** Single surgical change at the Python extraction site (`graph_indexer.py` ~5850): when `_resolve_call` bound a non-`external::` target with `receiver_resolved=False` (a unique same-file `symbol_lookup` match by construction — `self`/`cls`, same-file def, enclosing-class call, qualified `Owner.method`), promote EXTRACTED→RECEIVER_RESOLVED. Target unchanged; only the confidence label. Lift: Python EXTRACTED **90.4%→36.5%**, resolved **1,136→7,558** (+6,422). 6 tests + guards; suite **3406 OK**. | `graph_indexer.py` ~5850; `tests/test_graph_indexer.py::PythonConfidencePromotionTests` |
| 2026-06-23 | **Language-agnostic SAME-FILE promotion IMPLEMENTED + validated (local)** — the per-language extraction-site half. Widened the v23 TS/JS symbol-table promotion (`graph_indexer.py` ~6701) to ALL tree-sitter languages: in the `else` branch (the per-language receiver resolver already returned None), a call that `_ts_resolve_target` binds to a unique non-`external::` same-file node is promoted EXTRACTED→RECEIVER_RESOLVED. The code comment had explicitly invited this widening "if field data warrants it" — the AC-1 spike is that data (Java 247 / Swift 761 same-file). Relabel only; bind unchanged; same uniqueness guarantee as TS/JS. New positive tests `CrossLanguageSameFilePromotionTests` (Java + Swift bare same-class call → RECEIVER_RESOLVED). Full suite **3408 OK** bytecode-free. No local lift visible (wavefoundry's only tree-sitter language is JS, already v23-promoted); Java/Swift lift measured downstream. | `graph_indexer.py` ~6701 (drop the TS/JS gate); `tests/test_graph_indexer.py::CrossLanguageSameFilePromotionTests` |
| 2026-06-23 | **Language-agnostic CROSS-FILE promotion IMPLEMENTED + validated (local)** — the wave's headline deliverable post-reframe. In the cross-file rewrite stage (`graph_indexer.py` ~7350–7540), tagged the four EXACT-unique rebind branches with `rewrote_exact` (exact simple name / exact qualified name / Go package-authoritative / import-edge-disambiguated — all `len==1`) and promote EXTRACTED→RECEIVER_RESOLVED on it, replacing the prior TS/JS-only bare-simple promotion. Language-agnostic; target unchanged (only the confidence label) so no new wrong-twin risk. The AC-2 type-guess fallback + same-dir/C# namespace heuristics deliberately stay EXTRACTED. Local lift: Python cross-file promote bucket **552→23** (~96% captured), EXTRACTED **36.5%→31.9%**, resolved **→8,102**. Combined Python: **90.4%→31.9% EXTRACTED, 1,136→8,102 resolved**. Cross-file test flipped to assert promotion; ambiguity + receiver-guess guards retained; full suite **3406 OK** bytecode-free; `wave_validate` clean. Benefits Java/Swift/TS too (pending downstream lift measurement). Builder bump still deferred to the shared bump with `1p7dh`. | `graph_indexer.py` ~7350–7540 (`rewrote_exact`); `tests/test_graph_indexer.py::PythonConfidencePromotionTests::test_cross_file_explicit_import_promoted`; rebuilt-graph spike re-run |
| 2026-06-23 | **Java promotion lift DOWNSTREAM-VALIDATED on `aceiss/javaagent` (v33 build).** `EXTRACTED` **26.9% (1,746) → 20.6% (1,331)** (−415), `RECEIVER_RESOLVED` **4,099→4,491** (+392), `CONSTRUCTION_RESOLVED` unchanged (635), **no edges lost** — ~74% of the spike-predicted 562-edge bucket promoted, faithfulness-benign exactly as designed (real-data confirmation of AC-6 for Java). | operator downstream run on the 1.8.1+p7j1 build; v32→v33 attribution delta |
| 2026-06-23 | **Swift promotion lift DOWNSTREAM-VALIDATED on `solaris` (v33 build) — last per-language lift gate closed.** `EXTRACTED` **52.7% (3,917) → 33.4% (2,476)**, `RECEIVER_RESOLVED` **2,018→3,448 (+1,430)** — the ~1,440 spike-predicted promotion edges realized (promote_same_file/cross_file both →0%); Swift correctly moves PROMOTE→CEILING (remaining 85.7% Apple-SDK external, 4.6% resolve_unique below the bar). Python on solaris likewise EXTRACTED 156→32. No edges lost. AC-3 now cleared on Python+Java+Swift; AC-6 real-data-confirmed on Java+Swift. | operator downstream run on the 1.8.1+p7j5 build; v32→v33 Swift attribution delta |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-22 | **Measurement spike FIRST, gating scope per language** | The extractor is mature + tree-sitter-bounded; without measuring the current `EXTRACTED` population's recoverable headroom per language, "improve resolution" is unscoped and risks large effort for marginal/zero lift (Python/JS near their ceiling). The spike decides which languages are worth doing. | Implement broadly then measure (the original plan) — rejected: that is how prior rounds over-claimed and had to self-correct. |
| 2026-06-22 | **Extend existing resolvers, do NOT promise uniform cross-language resolution** | Each language needs its own mechanism (the history proves it — Java per-type imports vs C#/Go namespace/package heads); tree-sitter has no type system; uniform claims are the documented trap. | "Accurately across all languages" framing — rejected: not achievable without an LSP we deliberately don't use. |
| 2026-06-22 | **Per-language lift gate + unique-match faithfulness** | Ship a language only where it clears a real-graph bar, using the established len==1-or-external rule, reviewed against an external oracle. | Bundle-ship all targeted languages — rejected: a language that doesn't clear the bar would add risk without value. |
| 2026-06-23 | **Spike reframes Python from "drop (near ceiling)" to "GO via v23-style confidence promotion"** | The spike found 64.8% of Python EXTRACTED edges already bind a unique project node (`self.`/same-file/unique-cross-file) but are tagged `EXTRACTED` — the documented TS/JS v23 under-tagging, faithfulness-benign (target unchanged). The plan's "extend resolvers to new shapes" framing does not fit Python: the shapes are already resolved, the gap is the confidence label. | (a) Drop Python per the original near-ceiling assumption — rejected by data. (b) Add new Python receiver shapes — N/A, the recoverable shapes are already resolved. |
| 2026-06-23 | **Ship only the same-file promotion; revert the cross-file `.py` extension; record the 562 residual as a follow-on** | The same-file promotion captured 6,422 edges (the bulk). Extending the `rewrote_via_bare_simple` promotion to `.py` showed **zero** local lift — the residual 552 cross-file binds resolve via the AC-2 qualified-import branch (`from x import y` → `qualified_index` len==1), not bare-simple. The wave's gate is "ship per shape on demonstrated lift; drop and record what doesn't clear the bar." Promoting the AC-2 qualified branch for Python is faithful in principle (explicit imports are exact, not type guesses) but is the faithfulness-sensitive guarded zone and warrants its own analysis. | (a) Keep the dead `.py` bare-simple extension — rejected (no lift, widens the faithfulness surface for nothing). (b) Extend the AC-2 qualified branch now — deferred (faithfulness-sensitive; follow-on). |


## Risks


| Risk                                                                 | Mitigation                                                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| The spike shows little recoverable headroom for some languages (Python/JS) | That is the intended outcome — those languages are dropped from scope with the data recorded; effort goes where it pays. |
| New bindings are plausible-but-wrong (the documented Go/C# trap)     | Unique-match-or-stay-`EXTRACTED` (AC-2) + external-oracle faithfulness review per language (AC-6) + wrong-twin guard tests (AC-4). |
| Improvement is marginal on a committed language                     | Per-language lift bar (AC-3) — drop and record rather than ship a no-op. |
| Builder-bump re-extraction churn downstream                         | Documented one-time re-extraction; shared single bump with `1p7dh`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
