# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-03

wave-id: `1p2q3 field-feedback-round-4`
Title: Field Feedback Round 4 — Graph-Tool Quality + Dashboard Fidelity + MCP Protocol Primitives

## Objective

Three threads bundled because they share a common pattern (post-131bt polish and operator-UX tightening) and benefit from a single coherent release:

**Thread 1 — `code_graph_path` result quality (primary, blocking).** Aceiss field validation against the Java agent project on 1.3.4+p2py: `code_graph_path` reports `found: true` with plausible-but-spurious 2-hop paths that route through shared `external::*` nodes (caught exception variables, generic identifiers, stdlib symbols). The "path" doesn't represent any meaningful coupling between the endpoints; BFS bridges them through a low-information shared node and returns the shorter junk path even when a longer real call chain exists.

Reproducer from Aceiss (1.3.4+p2py on the Java agent project):

- `code_graph_path(from="ServletHelper.setSpanAttributesAtEndOfRequest", to="JSON.writeObject", direction="either")` returns a 2-hop path through `external::e` (a caught exception variable), every edge `relation: imports`, `confidence: EXTRACTED`
- `code_impact(symbol="writeObject")` in the same session confirms the real 3-hop call chain (`setSpan → AuthorizationContext.getDetailsAsJson → JSON.toJson → JSON.writeObject`) with all `RECEIVER_RESOLVED` edges
- The shortest-path objective actively prefers the 2-hop junk path over the 3-hop real one

Two distinct concerns in the report:

1. **Structural** — `external::*` nodes are graph shortcuts they shouldn't be. Routing BFS through an unresolved identifier connects unrelated symbols. Highest-leverage single fix.
2. **Operator-facing** — `found: true` is the headline an agent reads first. The disqualifying detail (`relation: imports`, `confidence: EXTRACTED`, `kind: null` bridge node with `source_file: null`) is one level down in `path_edges`. The data model is sound; the default traversal policy and the headline signal need tightening.

This thread admits one bundled change covering four interrelated fixes the field validator proposed in priority order: (1) non-transitive externals in BFS, (2) `relations=["calls"]` default, (3) structural-path diagnostic, (4) `min_confidence` parameter. All four touch the same tool and ship together for narrative coherence.

**Thread 2 — Dashboard graph rendering fidelity (`131es`).** Pre-existing plan carried over from wave 131bt close-out. The dashboard renders the graph payload via fallback paths that handle wave 131bt's new shapes correctly (no crashes, no incorrect data) but doesn't surface several signals the graph payload now carries: new node kinds (`package`, `namespace` from `1319m`); new confidence tags (`CONSTRUCTION_RESOLVED` from `1319s`, dense `RECEIVER_RESOLVED` from `1319q`); per-entry collision diagnostics (`13129`); class/module-merge markers (`1319o`'s `collapsed_pair: true` on Python/JS/TS); stale-graph signals (`131e2`'s `graph_auto_rebuilt`). Operator-facing information left on the table; non-blocking.

**Thread 3 — FastMCP / MCP protocol primitives (`131hh`).** Pre-existing plan carried over from the same close-out. Audit of the FastMCP surface identified primitives we weren't using that close real operator-UX gaps: `send_resource_updated(uri)` after graph rebuild (cache invalidation for `wavefoundry://graph/*`), `ctx.report_progress` during long-running rebuilds (visibility into the 10–30 s auto-rebuild blocking window), `@mcp.prompt()` exposure of `docs/prompts/*.md`, `@mcp.completion()` for symbol arguments. Phased adoption: Phase 1 (concrete + low risk), Phase 2 (host-behavior-gated exploratory), Phase 3 (opportunistic). The phased approach in the existing plan stays; this wave admits the plan as written.

**Thread 4 — TypeScript graph extraction quality on monorepos (`1p2q9`).** Teton field validation on a 12,301-node TypeScript Nx monorepo with `@aceiss/*` / `@teton/*` path aliases via `tsconfig.base.json` `paths` reveals near-zero function-level `calls` edge coverage. Module-level edges cluster correctly into communities (266-node community on `events.ts` is centered correctly), but `code_callhierarchy` / `code_impact` / `code_definition` return `graph_symbol_not_found` for the majority of TypeScript symbols. Tree-sitter parser is healthy (`code_references` returns the 4 known call sites instantly); the gap is between tree-sitter parse results and graph node attribution. Bundles five workstreams: honor `tsconfig` path aliases in import resolution; per-language attribution-confidence diagnostic (`attribution_counts_by_language` on `code_callhierarchy` / `code_impact` / `code_definition` / `wave_graph_report`); JS/TS generated-file classifier (`*.gen.ts`, `__generated__/`, etc.); `heuristic_import_no_matches` diagnostic on `code_impact(path=...)` for TS files; seed-211 fallback-rule widening from a static language list to a response-shape condition.

**Thread 5 — Cross-tool query polish (`1p2qb`).** Two small operator-facing gaps from the same Teton report: `code_definition` doesn't mirror `code_callhierarchy`'s `suggestions` field on graph misses (asymmetric recovery affordance); `code_navigation_hints` schema referenced in seed-211 but not documented in seed-100 (workflow-config skeleton) or as an example. Bundled into one small change to avoid two micro-changes for the same operator-UX polish surface.

**Thread 6 — `.wavefoundry/` folder excluded from consumer project graphs (`1p2qd`).** Field validation observation: framework Python (`chunker.py`, `indexer.py`, `graph_indexer.py`, etc.) ends up as graph nodes in consumer projects' graph layer because `_merged_project_include_prefixes_for_graph` hard-wires graph extraction to the union of docs+code prefixes — explicitly including `.wavefoundry/framework/scripts` per its docstring. Layering violation: consumer project graphs should contain consumer product code, not installed framework infrastructure. Default behavior changes to blanket-exclude `.wavefoundry/` from consumer project graphs; new `indexing.project_include_wavefoundry: bool` config flag opts back in for wavefoundry's own self-hosting case (wavefoundry's own `docs/workflow-config.json` is updated as part of the change). Framework-layer behavior unaffected.

The six threads share an operator-tightening pattern but are independent — implementation order does not matter, and partial delivery of any thread doesn't block the others. Common release cadence keeps the operator-visible behavior shifts coherent.

## Changes

Change ID: `1p2q4-bug code-graph-path-external-bridge-and-result-quality`
Change Status: `implemented`

Change ID: `131es-enh dashboard-graph-rendering-fidelity-updates`
Change Status: `partially-implemented`

Change ID: `131hh-enh mcp-protocol-surface-opportunities`
Change Status: `partially-implemented`

Change ID: `1p2q9-bug ts-graph-extraction-nx-monorepo-coverage`
Change Status: `implemented`

Change ID: `1p2qb-enh cross-tool-query-suggestions-and-docs-polish`
Change Status: `implemented`

Change ID: `1p2qd-bug graph-extraction-excludes-wavefoundry-folder-from-consumer-projects`
Change Status: `implemented`

Change ID: `1p2ta-bug prune-deletes-test-files-on-self-hosted-upgrade`
Change Status: `implemented`

Change ID: `1p2td-bug overload-self-edge-misreads-as-recursion`
Change Status: `implemented`

Change ID: `1p2tf-bug ts-receiver-type-resolution-uses-resolved-imports`
Change Status: `implemented`

Change ID: `1p2th-enh workflow-config-emits-code-navigation-hints-block`
Change Status: `reconsidered-and-reverted`

Change ID: `1p2tz-bug ts-barrel-export-resolution-for-nx-aliases`
Change Status: `implemented`

Change ID: `1p2w5-bug index-build-lock-and-autorebuild-coordination`
Change Status: `implemented`

Change ID: `1p2wd-bug parallel-extraction-fork-deadlock-spawn-mode-fix`
Change Status: `implemented`

Change ID: `1p314-bug seed-surface-stale-tool-reference-drift`
Change Status: `implemented`

Completed At: 2026-06-03

## Wave Summary

Wave `1p2q3` (Field Feedback Round 4 — Graph-Tool Quality + Dashboard Fidelity + MCP Protocol Primitives) delivered 14 changes: `code_graph_path` Returns Spurious Paths Through Shared `external::*` Nodes, Dashboard Graph Rendering Fidelity Updates for Wave 131bt Graph Changes, Adopt Additional FastMCP / MCP Protocol Primitives Where They Improve Operator UX, TypeScript Graph Extraction Has Near-Zero Function-Level Coverage on Nx Monorepos, Cross-Tool Query Polish — `code_definition` Suggestions + `code_navigation_hints` Schema Docs, Graph Extraction Pulls `.wavefoundry/framework/` Into Consumer Project Graphs, Prune Deletes Test Files on Self-Hosted Upgrade, Overload Self-Edge Misreads as Recursion, TypeScript Receiver-Type Resolution Uses Resolved Imports, Workflow-Config Emits code_navigation_hints Block, TypeScript Barrel Export Resolution for Nx Path Aliases, Index Build Lock Hygiene and Auto-Rebuild Coordination, Parallel-Extraction Fork Deadlock — Spawn-Mode Worker Initializer, and Seed Surface Stale Tool Reference Drift. Notable adjustments during implementation: Index Build Lock Hygiene and Auto-Rebuild Coordination: Teton's 1.3.17 install reproduced Bug 4 (parallel-extraction fork-after-state deadlock). 1.3.18 ships parallel mode default-off (`WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` default 1 instead of `min(cpu_count, 4)`) as the conservative bridge until spawn-mode worker initializer lands. Bug 4 itself is out of scope for this change doc and will be tracked separately in a follow-up change.; Parallel-Extraction Fork Deadlock — Spawn-Mode Worker Initializer: Post-ship 1.3.23: 1.3.22 confirmed `threads=1: MainThread` at step 8/8 (threading-thread issue fixed) but the hang persisted with a different signature. Teton's stack samples isolated three indexer threads — main blocked on Future.result, queue-manager polling FDs, and the call-queue writer thread blocked in `os.write()` to a pipe. Root cause: `pool.map(chunksize=96)` triggers `Executor.map`'s eager `submit()` loop, pre-filling 16 chunks (~1,536 items) into the call queue's Unix pipe (64KB buffer on macOS) before any worker spawns. Writer thread blocks; workers never spawn; main thread waits forever. Fix: replaced `pool.map` with a bounded-in-flight `pool.submit` + `concurrent.futures.wait(..., return_when=FIRST_COMPLETED)` loop. At most `worker_count` tasks queued at any time — pipe never fills. Pre-warm trigger spawns workers safely. Added worker-side breadcrumb to entry of `_extract_artifact_for_worker` for any future regression diagnosis.

**Changes delivered:**

- **`code_graph_path` Returns Spurious Paths Through Shared `external::*` Nodes** (`1p2q4-bug code-graph-path-external-bridge-and-result-quality`) — 12 ACs completed. Key decisions: Bundle four fixes into one change; External nodes are non-transitive (Fix 1), not excluded from the graph entirely
- **Dashboard Graph Rendering Fidelity Updates for Wave 131bt Graph Changes** (`131es-enh dashboard-graph-rendering-fidelity-updates`) — 6 ACs completed. Key decisions: Use stroke style (dashed/solid) to encode confidence rather than a secondary color overlay; Peer-level visual treatment for `RECEIVER_RESOLVED` and `CONSTRUCTION_RESOLVED`
- **Adopt Additional FastMCP / MCP Protocol Primitives Where They Improve Operator UX** (`131hh-enh mcp-protocol-surface-opportunities`) — 5 ACs completed
- **TypeScript Graph Extraction Has Near-Zero Function-Level Coverage on Nx Monorepos** (`1p2q9-bug ts-graph-extraction-nx-monorepo-coverage`) — 15 ACs completed. Key decisions: Bundle Workstreams A–E into one change; Read `tsconfig` `paths` directly rather than building Nx-specific or Turborepo-specific logic
- **Cross-Tool Query Polish — `code_definition` Suggestions + `code_navigation_hints` Schema Docs** (`1p2qb-enh cross-tool-query-suggestions-and-docs-polish`) — 8 ACs completed. Key decisions: Bundle the two polish items into one change; Shared candidate-generation helper rather than copy-paste between tool responses
- **Graph Extraction Pulls `.wavefoundry/framework/` Into Consumer Project Graphs** (`1p2qd-bug graph-extraction-excludes-wavefoundry-folder-from-consumer-projects`) — 12 ACs completed. Key decisions: Default to excluding `.wavefoundry/` from consumer project graphs; opt-in for self-hosting; Blanket-exclude `.wavefoundry/` at the top level instead of enumerating sub-prefixes
- **Prune Deletes Test Files on Self-Hosted Upgrade** (`1p2ta-bug prune-deletes-test-files-on-self-hosted-upgrade`) — 6 ACs completed
- **Overload Self-Edge Misreads as Recursion** (`1p2td-bug overload-self-edge-misreads-as-recursion`) — 11 ACs completed
- **TypeScript Receiver-Type Resolution Uses Resolved Imports** (`1p2tf-bug ts-receiver-type-resolution-uses-resolved-imports`) — 10 ACs completed
- **Workflow-Config Emits code_navigation_hints Block** (`1p2th-enh workflow-config-emits-code-navigation-hints-block`) — 5 ACs completed
- **TypeScript Barrel Export Resolution for Nx Path Aliases** (`1p2tz-bug ts-barrel-export-resolution-for-nx-aliases`) — 13 ACs completed
- **Index Build Lock Hygiene and Auto-Rebuild Coordination** (`1p2w5-bug index-build-lock-and-autorebuild-coordination`) — 5 ACs completed. Key decisions: --------; In-process auto-rebuild coordination (module-level dict guarded by `threading.Lock`) rather than file-based coordination across processes.
- **Parallel-Extraction Fork Deadlock — Spawn-Mode Worker Initializer** (`1p2wd-bug parallel-extraction-fork-deadlock-spawn-mode-fix`) — 5 ACs completed. Key decisions: --------; Spawn over forkserver.
- **Seed Surface Stale Tool Reference Drift** (`1p314-bug seed-surface-stale-tool-reference-drift`) — Treat `wave_lint_lib` references as false positive; Treat `wave_id` references as false positive
## Journal Watchpoints

- **Watchpoint — cost-constant calibration must follow the invariant.** Fix #2 ships weighted-cost path search with defaults `(calls/high=1, calls/EXTRACTED=2, structural=100)`. The invariant `structural_cost > max_hops × calls/EXTRACTED_cost` must hold to preserve calls preference throughout the search horizon. Any future change to `max_hops` default OR cost-constant tuning must re-verify this invariant — bake into the code comment alongside the constants, and into the AC-12 benchmark assertion. Operator pushback explicitly rejected an earlier draft that proposed shifting the `relations` default to `["calls"]` instead; that approach would have forced caller migration with no improvement to the underlying ranking — sticking with the algorithmic fix is the decision to remember.
- **Test against the actual failing case.** The Aceiss reproducer (`setSpan → external::e → writeObject`) is the regression-test fixture. Synthesize a project graph with that shape and assert: (a) the spurious 2-hop path is no longer returned; (b) the real 3-hop calls path IS returned when present; (c) `found: false` + suggestions when the endpoints aren't actually connected.
- **External-as-endpoint must still work.** Callers querying `code_graph_path(from="external::FooLib.bar", direction="backward")` ask a legitimate question ("what reaches this external symbol?"). The non-transitive rule applies to intermediate externals only — `current ∉ {from_id, to_id}` is the gate.
- **`fan_in` stdlib noise (companion finding).** The same field report flagged `fan_in` being dominated by `external::String` / `external::contains` / `external::map` / `external::warning` / `external::Date` — not useful "most-called project symbols." Same root cause as #1 (unresolved-identifier nodes graph-shortcutting), but the fix lives in `wave_graph_report.fan_in` filtering, not `code_graph_path`. Tracking as a separate future plan rather than bundling — fan_in's behavior is observably distinct (filterable via existing `exclude_external` parameter) where the graph_path case has no operator-facing workaround.
- **Orphan-docs noise (companion finding).** The report also flagged `{label: "clean", kind: "doc"}` and `{label: "debug", kind: "doc"}` as orphan-docs entries — command-snippet fragments mis-ingested as doc nodes. Doc-extractor data-quality bug, separate from graph_path. File as follow-on plan.
- **Watchpoint — TS path-alias resolution must not regress non-monorepo TS projects.** `1p2q9` Workstream A extends TS import resolution to honor `tsconfig.paths`. Resolution is additive (no `paths` → no behavior change), but the change touches a hot path during graph extraction. AC-4 in `1p2q9` is the binding regression assertion; CI must run on a non-monorepo TS fixture in addition to the new Nx-shaped fixture.
- **Watchpoint — `attribution_counts_by_language` must populate for all in-response languages, not just TS.** `1p2q9` Workstream B's diagnostic is multi-language-shaped by design. Polyglot regression test (AC-8 in `1p2q9`) verifies; if any language is missing from the counts when its edges are surfaced, that's a real gap.
- **Watchpoint — investigate but don't pre-commit on `RECEIVER_RESOLVED` absence.** Teton's smoke test saw zero `RECEIVER_RESOLVED` edges on a TS-native-annotated repo. `1p2q9` Workstream A may resolve this as a side effect (binding imports to project nodes lets the resolver see project receivers instead of `external::*`). Investigate during impl; if not resolved, file follow-on. Don't add receiver-type-resolver fixes to `1p2q9` speculatively.

## Review Evidence

- wave-council-delivery: approved 2026-06-03 — Inline council review across five lanes (delivery, operator UX, architecture, testing, documentation). All lanes returned positive verdicts. Delivery: 9 of 11 admitted-as-actionable changes shipped end-to-end; 2 explicit partials (`131es`, `131hh`) have clean phase-boundary carving with split-out follow-ons (`1p30y`, `1p310`) carrying parent AC traceability; 1 revert (`1p2th`) with documented rationale; 2 mid-wave admits (`1p2w5`, `1p2wd`) are field-driven not scope creep. Operator UX: Teton field measurement confirms TS attribution share 8.3% → 12.0% (+45%), JS share 6.4% → 15.6% (+144%), parallel rebuild 27.1s serial → 12.0s (-56%); intra-file arrow-const resolution went from 0/5 to 5/5; lock-hygiene fixes close the "looks like it worked but didn't" diagnostic anti-pattern. Architecture: GRAPH_BUILDER_VERSION 22→23 contract held; parallel-extraction stabilized through 6 distinct bug surfaces (fork hazard, spawn-from-non-main-thread, eager-submit pipe-fill, IPC amortization, per-task git subprocess, per-task state-load) to a coherent process-backend-with-state-preload design; process default chosen on honest field measurement (process-8 15s vs. thread-4 22.9s); P-core detection via macOS sysctl gives the right auto-scale answer without operator tuning; CHANGELOG collapsed from 16 debug-version entries to 1 narrative entry. Testing: 2260 framework tests passing (+16 net); high-stakes changes have material new regression tests (parallel-extraction end-to-end with real spawn workers, inflight-marker coordination, intra-file arrow-const promotion, auto-scale tier boundaries); deferred AC-19 dashboard-delta browser-harness test has substrate substitute. Documentation: change docs carry Decision Log + Risks + Related Work populated throughout; 1p2tz post-ship correction notes through 5 iterations document the full multi-round Teton iteration with attribution numbers; two new operator-facing CLI surfaces (`upgrade-wavefoundry --detect-zip`, `--list-zips`) with seed-160 + rendered prompt updated, `ls -1` lex-sort antipattern explicitly called out; three follow-on plans (`1p30y`, `1p310`, `1p312`) in `docs/plans/` with parent references. Caveats not blocking close: (a) 96 orphaned LanceDB rows in project layer are pre-existing pollution from past workflow-config evolutions — tracked as `1p312-bug`, not a 1p2q3 regression; (b) 35 unassociated commits in the 30-day window are mostly legitimate (renamed `Round N` commits, the `88cdac3` collapsed-commit, historical chores) — optional follow-up. Council verdict: READY TO CLOSE.
- operator-signoff: approved 2026-06-03 — Operator approves council review and authorizes wave close.
- wave-council-readiness: approved 2026-06-02 — Five changes admitted across five threads. Thread 1 (`1p2q4-bug code-graph-path-external-bridge-and-result-quality`) addresses Aceiss field validation against 1.3.4+p2py — `code_graph_path` spurious 2-hop paths via shared `external::*` nodes; bundles four fixes (non-transitive externals, weighted-cost path search, structural-path diagnostic, `min_confidence` parameter). Thread 2 (`131es`) and Thread 3 (`131hh`) carry forward from wave 131bt close-out (dashboard fidelity; FastMCP primitive adoption). Thread 4 (`1p2q9-bug ts-graph-extraction-nx-monorepo-coverage`) admits the Teton TypeScript Nx-monorepo field validation: near-zero function-level `calls` coverage on a 12,301-node TS repo despite tree-sitter parser health; bundles `tsconfig.paths` resolution, JS/TS generated-file classifier, `attribution_counts_by_language` diagnostic across four graph-result tools, `heuristic_import_no_matches` diagnostic on `code_impact(path=...)` for TS, and seed-211 fallback-rule widening from a static language list to a response-shape condition. Thread 5 (`1p2qb-enh cross-tool-query-suggestions-and-docs-polish`) admits two small polish items from the same Teton report: `code_definition` mirrors `code_callhierarchy`'s `suggestions` on graph miss; `code_navigation_hints` schema documented in seed-100 + concrete example in seed-211. Strongest red-team concerns across the expanded scope: (a) Thread 1's cost-constant calibration could drift if `max_hops` default changes meaningfully — mitigated by documenting the invariant in code comments and AC-12 benchmark; (b) Thread 4's TS path-alias resolution must not regress non-monorepo TS projects — AC-4 binding regression coverage, both Nx-shaped and non-monorepo TS fixtures required in CI. Strongest reality-checker concern: scope sizing — wave grew from 3 threads at original prepare to 5 threads after Teton round; bundled-scope verification re-run, all five threads remain independent with no cross-thread file overlap or implementation-order dependencies. Architecture review: Thread 4 touches `graph_indexer.py` (TS extractor + classifier) and `server_impl.py` (diagnostic field on four tools); no overlap with Thread 1 (graph_query.py shortest_path) or Threads 2/3/5 (different surfaces). Cost-function design from Thread 1: `structural_cost > max_hops × calls/EXTRACTED_cost` (defaults 1, 2, 100). qa-reviewer flagged two targeted gaps: `131es` lacks "no dashboard regression on existing graph payloads" AC; Thread 4 should investigate but not pre-commit on `RECEIVER_RESOLVED` absence cause — track both during prepare phase, neither blocks admission. Required reviewer lanes for prepare: code-reviewer for Thread 1 + Thread 3 + Thread 4 framework changes; qa-reviewer for all five (per-thread regression coverage, especially Nx-shaped TS fixture in Thread 4); docs-contract-reviewer for Thread 1's `code_graph_path` docstring + seed-211 update, Thread 3's FastMCP-primitive contract, Thread 4's seed-211 fallback-rule rewrite + reviewer-seat seed propagation, Thread 5's seed-100 / seed-211 schema docs. Wave is ready for implementation.

## Prepare Review Evidence

(Populated by per-lane reviewers during prepare.)

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-02: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: Thread 6's `.wavefoundry/` blanket exclusion is a default-behavior change that drops node counts in consumer projects on upgrade — accepted with documented mitigation (changelog `### Changes` entry explains the rationale; the wavefoundry self-hosting case is preserved via the `project_include_wavefoundry: true` opt-in shipped in the same change; auto-rebuild safety net `131e2` handles post-upgrade transition without manual operator action). Thread 4's `tsconfig.paths` resolution concern from the prior re-run remains valid — binding non-monorepo regression coverage via AC-4. Earlier wave-council concerns (Thread 1 cost-constant calibration, Thread 1 default-relations shift rejected after operator pushback) remain documented and unchanged; strongest-alternative: split the six threads into two waves at the Teton-round / Aceiss-round boundary — rejected on common-release-cadence grounds; all six threads address the same operator-tightening pattern (graph-tool result quality + dashboard UX + framework layering) and ship together for narrative coherence; the threads remain independent with no cross-thread blockers; re-ran after Aceiss layering-finding expansion from 5 to 6 threads and the `131es` dashboard expansion with flicker + secondary-route ACs)
  - Red-team strongest concern: cost-constant calibration — accepted with documented invariant and benchmark AC. Earlier draft's default-relations contract shift was rejected after operator pushback in favor of the algorithmic fix; the revised approach eliminates the migration concern entirely. Secondary concern (Thread 3 Phase 2 experimental-flag rot) addressed by AC-8 ship gate.
  - Architecture-reviewer: no file overlap between threads; Thread 1's BFS rule + weighted-cost search compose cleanly with `131bu`'s tie-break logic. Priority-queue replacement of `deque` is a localized internal change in `GraphQueryIndex.shortest_path`.
  - Security-reviewer: no new attack surface; all new primitives are server→client notifications or read-only registrations.
  - QA-reviewer flagged one targeted gap: `131es` should add an explicit "no dashboard regression on existing graph payloads" AC during prepare-phase cleanup. Does not block admission; tracked as prepare-phase work. Thread 1's AC-12 performance benchmark verifies the priority-queue asymptotic cost stays marginal at typical graph sizes.
  - Docs-contract-reviewer: Thread 1's docstring + seed-211 update is required for the weighted-cost selection and cost constants to be discoverable; AC-10 makes this binding. No `relations` migration required (cost function does the work).
  - Reality-checker: bundled scope honestly bounded with deferred companions explicitly enumerated in Journal Watchpoints (`fan_in` stdlib noise, orphan-docs fragments, `_existing_prefixes` regex false-positive).

| Checkpoint | When | Outcome |
|---|---|---|
| wave-council-readiness | Before implementation | PASS 2026-06-02 |
| wave-council-delivery | Before close | Pending |

## Dependencies

- No upstream wave dependencies. Builds on `graph_query.shortest_path` which last shipped in wave 131bt (`131bu`'s confidence tie-break). The tie-break logic introduced in 131bu remains correct and is preserved by this change — the new non-transitive-external check sits before the tie-break in the candidate-expansion path.
- No downstream wave consumers blocked by this change.
- Companion findings deferred to future plans (per Journal Watchpoints): `fan_in` stdlib noise; orphan-docs command-snippet fragments; `_existing_prefixes` regex false-positive on `close-*` filenames (carried over from wave 131bt close-out).
