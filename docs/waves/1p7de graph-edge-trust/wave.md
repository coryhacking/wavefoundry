# Wave Record

Owner: Engineering
Status: active
Last verified: 2026-06-23

wave-id: `1p7de graph-edge-trust`
Title: Graph Edge Trust

## Objective

Raise the trust of the code graph's edges so the blast-radius / risk surfaces (`code_impact`, `code_risk_score`, `code_callhierarchy`) are accurate on real polyglot repos. Today `EXTRACTED` (name-based, receiver-unresolved) call edges are ~66% (Java) to ~87% (Python) of all `calls` edges, which both under-counts cross-file reach (Python/Swift instance methods resolve same-file only) and over-counts it (Java name collisions). When this closes, blast radius discounts low-trust edges along the whole path, more instance-method calls resolve to the right symbol, and annotation/config string-literal bindings are queryable.

## Changes

Change ID: `1p7df-enh transitive-confidence-propagation`
Change Status: `implemented`

Change ID: `1p7dg-enh cross-file-receiver-resolution`
Change Status: `implementing`

Change ID: `1p7dh-enh string-literal-arg-extraction`
Change Status: `planned`

## Wave Summary

Three graph-quality enhancements, ordered by leverage-per-risk. `1p7df` (query-layer, no re-extraction) propagates per-edge confidence transitively through `graph_impact`'s BFS so multi-hop blast radius stops leaking `EXTRACTED`-edge weight — reusing `code_graph_path`'s proven weighted-cost model. `1p7dg` (extractor) **extends the mature per-language receiver-type resolvers** (tree-sitter-only, builder v32) to the still-unresolved call-site shapes a **measurement spike shows have real per-language headroom** — gated per language with a real-graph lift bar, no uniform cross-language promise; the durable fix that lowers the `EXTRACTED` fraction where it pays. `1p7dh` (extractor) captures string-literal arguments on annotations + a declared set of binding call sites to emit advice-registration and config-key→reader edges, unlocking the AOP and config-cross-reference answer classes two consumers needed. Every change is value-gated with before/after attribution on the real consumer graphs; the two extractor changes get the adversarial faithfulness review.

## Journal Watchpoints

- **Sequencing watchpoint (do the cheap win first):** `1p7df` is query-layer (no `GRAPH_BUILDER_VERSION` bump, no consumer re-extraction) and independent — land it first to ship accuracy on existing graphs. `1p7dg` + `1p7dh` are extractor changes that **share a single coordinated `GRAPH_BUILDER_VERSION` bump** so consumers re-extract **once**, not twice — this coordination is **blocking**: do not let each bump independently.
- **Value-gate watchpoint (avoid a no-op):** every change carries a before/after attribution gate measured on the real multi-language consumer pack (Swift/solaris, Java, RDS), not synthetic fixtures — `code_risk_score` (`1p41o`) was gated out for degenerating to a fan-in proxy on the real graph; ship only on demonstrated improvement. For `1p7dg` this runs **up front as a measurement spike** (per-language recoverable-headroom report) that *scopes* the work, plus a per-language lift bar that *ships* it — not a post-hoc check.
- **No uniform cross-language promise (interrogation watchpoint):** the extractor is tree-sitter-bounded (no LSP/type system) and each language needs its own mechanism; the codebase already over-claimed once — v24 advertised a disambiguation as "language-agnostic" and self-corrected to "Python + Java only". `1p7dg`/`1p7dh` are scoped **per language by data**: a language near its syntactic ceiling (Python/JS without annotations) or without the construct (Go/Rust/C have no annotations) is **dropped with the data recorded, not forced**. The established **unique-match-or-stay-`EXTRACTED`** faithfulness rule (which already caught Go/C# wrong-twin over-resolution) is reused, not relaxed.
- **Faithfulness watchpoint (binding changes):** `1p7dg` (receiver bindings) and `1p7dh` (literal-derived bindings) are exactly the silent-narrowing / wrong-twin / zeroed-edge / plausible-but-wrong defect classes the adversarial faithfulness review exists to catch (`1p4hi`). Run it with an external oracle (a language server / compiler resolution sample) before close — green tests are not sufficient.
- **Foundation-before-tools follow-up:** the new query-tool surface (`code_advice_sites`, a config-key cross-reference tool) that the `1p7dh` edges enable is a **deferred follow-on**, not in this wave — get the edges correct + faithfulness-reviewed first; a tool over wrong edges is worse than no tool.
- **Conservative-resolve guard:** `1p7dg` must resolve-or-stay-`EXTRACTED` (never a wrong binding); discounting (`1p7df`) is fractional, never exclusion — both avoid trading the under-count for over-trust.

## Review Evidence

- wave-council-readiness: approved (READY) — prepare-council passed 2026-06-22 after a rigorous operator-requested interrogation (moderator: wave-council; primer-depth: deep; seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer; fixed-seat: red-team; rotating-seat: reality-checker (cross-language feasibility)). Scope: 3 graph-edge-trust changes — `1p7df` transitive confidence propagation (query-layer), `1p7dg` cross-file receiver-resolution coverage (extractor), `1p7dh` string-literal arg extraction (extractor). The interrogation, grounded in the `graph_indexer.py` v32 history, found the original framing over-claimed uniform cross-language receiver resolution — the documented trap (v24 self-corrected "language-agnostic" to Python+Java only; Go/C# wrong-twin over-resolution caught by prior faithfulness review) — and that the extractor is tree-sitter-bounded (no LSP/type system), so accuracy is language- and shape-uneven. Addressed in the change docs: `1p7df` is language-agnostic + query-layer + proven (ready, lands first); `1p7dg` reframed from "build" to **extend the existing per-language resolvers** with a **measurement spike FIRST** (per-language recoverable-headroom report on the consumer pack) gating scope, a per-language lift bar gating shipping, reuse of the unique-match-or-stay-`EXTRACTED` rule, and no uniform cross-language promise (a language near its syntactic ceiling is dropped with data); `1p7dh` scoped **per language/framework** (annotations are Java/Kotlin/C#/Python/TS, not Go/Rust/C), value-gated per edge type. Conditions into implement: spike before any `1p7dg` extractor edit; per-language lift bars (drop, do not force); shared single `GRAPH_BUILDER_VERSION` bump for `1p7dg`+`1p7dh`; external-oracle faithfulness review for both binding changes; `1p7df` first. Strongest alternative: defer `1p7dh` to a follow-on (heaviest; value via a deferred tool) — overridden by operator direction to keep all three, mitigated by per-language scoping + value-gating. Faithfulness REQUIRED for `1p7dg`/`1p7dh` (binding changes — wrong-twin/silent-narrowing class); N/A for `1p7df` (no binding change). Local-only; no detection/data change.
- operator-signoff: approved when operator confirms closure

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-22: PASS** (moderator: wave-council; primer-depth: deep; seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer; fixed-seat: red-team; rotating-seat: reality-checker (cross-language feasibility); revised-at-interrogation: yes; scope: `1p7de` graph-edge-trust, 3 changes — `1p7df` transitive confidence (query-layer), `1p7dg` receiver-resolution (extractor), `1p7dh` string-literal-args (extractor); strongest-challenge: the original plan over-claimed uniform cross-language receiver resolution — the documented v32 trap (v24 "language-agnostic" self-corrected to Python+Java; Go/C# wrong-twin over-resolution), and the extractor is tree-sitter-bounded (no LSP) so accuracy is language/shape-uneven — REVISED to address: `1p7dg` reframed to extend-existing-resolvers + measurement-spike-FIRST + per-language lift gate + unique-match faithfulness + no-uniform-promise, `1p7dh` scoped per-language/framework + value-gated, `1p7df` ready as-is and lands first; strongest-alternative: defer `1p7dh` — overridden by operator (kept + scoped); conditions-into-implement: spike before any `1p7dg` extractor edit, per-language lift bars (drop don't force), shared single `GRAPH_BUILDER_VERSION` bump, external-oracle faithfulness review for both binding changes, `1p7df` first; faithfulness REQUIRED for `1p7dg`/`1p7dh`, N/A for `1p7df`)

## Dependencies

- No external wave dependencies. Builds on the shipped graph-extraction + confidence-weighting work (`130rj`/`130tw`/`1312l` receiver resolution; `1p5l4`/`p5l8` immediate-hop confidence weighting; `1p4hi`/`1p4ls` constant nodes).
