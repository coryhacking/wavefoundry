# Wavefoundry graph-tools field feedback

Owner: Engineering
Status: active
Last verified: 2026-07-06

A standing log of field observations about the code-graph tools (`code_impact`, `code_callhierarchy`, `code_callgraph`, `code_graph_path`, `code_risk_score`, `wave_graph_report`, …) gathered from real target-repo smoke tests. Findings here are candidates for a graph-extractor enhancement wave (cf. the prior `graph-tools-field-feedback` rounds: `130rj`, `13129`, `1p41l`). Not defects unless noted — most are modeling gaps or missing signals.

---

## 2026-07-06 — External-target `implements`/`extends` have no graph modeling (unlike `calls`)

**Repo:** a Java OpenTelemetry / instrumentation codebase (Shopizer / SailPoint / JDBC instrumentation modules; an EL-parser `Node` interface). **Framework:** post-1.11.0 upgrade (GRAPH_BUILDER_VERSION 43).

**Project-internal interface resolution — clean pass.** `code_impact(symbol="Node", max_hops=2)` on the EL parser's `Node` interface resolved the full hierarchy: `SimpleNode implements Node` plus all 29 `Ast*` subclasses' `extends SimpleNode` edges — **30/30 edges, 100% RECEIVER_RESOLVED**. Deep interface-through-inheritance resolution works correctly.

**External-interface `implements`/`extends` — no edge at all (the gap).**
- `TypeInstrumentation` (OTel's interface, implemented by 24 classes across this repo's instrumentation modules) does **not** resolve as a graph node by name.
- Querying from the implementor side finds **zero `implements` edges** even though the source literally declares `implements TypeInstrumentation`. Verified on three separate implementors — `ShopizerSecurityInstrumentation`, `SailPointSecurityInstrumentation`, `JdbcDriverInstrumentation` — all show 0 edges for `implements`/`extends`/`imports` when the target is external. Same result for `extends InstrumentationModule` (also an external OTel class).
- Operator checked `graph_indexer.py`: there is **no external-target handling code path for `implements`/`extends` at all** — unlike `calls` edges, which have an explicit external-attribution bucket (`external_outgoing_count` / `external_incoming_count`, with `RECEIVER_RESOLVED` / `CONSTRUCTION_RESOLVED` / `EXTRACTED` tiers).

**Why it matters:** a consumer running `code_impact` / `code_callhierarchy` on a class that implements an external interface sees **nothing** — no edge, and (unlike `calls`) not even an "N external suppressed" count. So there is no signal that a real `implements` relationship exists at all. This mirrors past feedback-round findings where a relation lacked external-target modeling.

**Not a regression** from the 1.11.0 upgrade — `implements`/`extends` simply have never had external-target modeling, in contrast to `calls`.

**Candidate fix direction:** give `implements`/`extends` the same external-target treatment `calls` already has — mint/resolve `external::<FQN>` supertype nodes (or at minimum surface an `external_implements_count` / suppressed-count signal) so a class-implementing-an-external-interface is visible in blast-radius and hierarchy queries. Sizing + design belongs in a graph-extractor enhancement wave, not a hotfix.
