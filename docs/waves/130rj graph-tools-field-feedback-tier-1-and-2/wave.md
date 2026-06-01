# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-31

wave-id: `130rj graph-tools-field-feedback-tier-1-and-2`
Title: Graph Tools — Field Feedback Tier 1 + Tier 2

## Objective

Ship the high-leverage, low/medium-effort improvements identified by two independent operator field reports on the graph code-navigation tools shipped in waves 130et / 130ol / 130qf (`1.1.0+30qh`):

- **Solaris (Swift)** — used the tools end-to-end for a bug investigation and observed that the seeds describe each tool in isolation but never teach the chains that actually answer agent question types. Proposed 7 question-type recipes (bug investigation, refactor, analogue-first feature, impact analysis, edge cases, cross-cutting, anti-patterns) plus reviewer-side recipes for seeds 213/214/221.
- **Aceiss (Java/ByteBuddy)** — found tool-shape inconsistencies (community label vs ID mismatch, missing pagination on `code_graph_community`, no per-hop attribution on `code_impact`) plus generated-code distortions (javacc/ANTLR-generated parsers dominating betweenness, contaminating communities, polluting fan_in) plus AOP/advice empty-incoming gap (advice methods have no Java call sites; falling back to `code_references` actively misleads agents).

Convergent observation across both: the graph tools *work*, but the seeds optimize for tool discoverability when they should also optimize for pattern discoverability, and the index doesn't classify language-specific structural noise.

## Changes

Change ID: `130rj-enh seeds-pattern-library-and-recipes`
Change Status: `implemented`

Change ID: `130rj-enh graph-tool-shape-consistency`
Change Status: `implemented`

Change ID: `130rj-enh code-ask-seed-tightening`
Change Status: `implemented`

Change ID: `130rj-enh generated-code-classifier-and-filters`
Change Status: `implemented`

Change ID: `130rj-enh aop-advice-empty-incoming-detection`
Change Status: `implemented`

Change ID: `130r7-bug java-method-reference-call-sites`
Change Status: `implemented`

Change ID: `130su-enh generated-code-collapse-mode`
Change Status: `implemented`

Change ID: `130tc-enh csharp-aop-attribute-detection`
Change Status: `implemented`

Change ID: `130tc-enh kotlin-reference-resolution`
Change Status: `implemented`

Change ID: `130tw-enh fan-in-name-collision-hint-and-seed-note`
Change Status: `implemented`

Change ID: `130tw-enh betweenness-computed-field`
Change Status: `implemented`

Change ID: `130tw-enh large-community-pagination`
Change Status: `implemented`

Change ID: `130tw-enh exclude-external-from-graph-report`
Change Status: `implemented`

Change ID: `130tw-enh java-receiver-type-resolution`
Change Status: `implemented`

Completed At: 2026-06-01

## Wave Summary

Wave `130rj` (Graph Tools — Field Feedback Tier 1 + Tier 2) delivered 14 changes: Seeds — Question-Type Pattern Library + Reviewer Recipes + AOP/Latency Footguns, Graph Tool Response Shape — Community ID Dual Return, Pagination, Per-Hop Attribution, Community Overview, `code_ask` — Tighten Seed Guidance Instead of Adding API Surface for a Misuse Case, Generated-Code Classifier + `exclude_generated` Filter + `generated_node_fraction` Per Community, AOP/Advice Empty-Incoming Detection — `caller_pattern: "advice"` + Recovery Hint, Java `method_reference` Nodes Are Not Classified as `call_sites` (Aceiss §1.2), Generated-Code Collapse Mode — File-as-Black-Box View for Architectural / Visualization Use, C# AOP Attribute Detection — Extend `caller_pattern: "advice"` to C# Method-Boundary Aspects, Kotlin Reference Resolution — Enable Tree-Sitter-Backed Identifier Reference Extraction for Kotlin, Fan-In Name-Collision Hint and Seed Note — Surface Simple-Name Attribution Risk on Common Method Names, `betweenness_computed` Field on `wave_graph_report` — Distinguish "Empty Section" from "Computation Disabled", Large Community Pagination — Return First 50 Members with `total_member_count` and Page Hint, `exclude_external` Parameter on `wave_graph_report` — Filter External Library Calls from Architectural Rankings, and Java Receiver-Type Resolution — Filter False Cross-Class Callers on Method Name Matches.

**Changes delivered:**

- **Seeds — Question-Type Pattern Library + Reviewer Recipes + AOP/Latency Footguns** (`130rj-enh seeds-pattern-library-and-recipes`) — 12 ACs completed. Key decisions: Land patterns in existing seeds (180/211/213/214/221), not a new `code-graph-patterns.md`; Describe patterns at the "shape" level (tool name + arg semantics) rather than at the API level
- **Graph Tool Response Shape — Community ID Dual Return, Pagination, Per-Hop Attribution, Community Overview** (`130rj-enh graph-tool-shape-consistency`) — 8 ACs completed. Key decisions: Dual-return (`community` + `community_id`) instead of case-insensitive label-as-input; Keep legacy `node_count` as alias for `returned_count`
- **`code_ask` — Tighten Seed Guidance Instead of Adding API Surface for a Misuse Case** (`130rj-enh code-ask-seed-tightening`) — 4 ACs completed. Key decisions: Drop `fast_mode` API surface; Tighten seed language to remove "check rerank_ms" hedge
- **Generated-Code Classifier + `exclude_generated` Filter + `generated_node_fraction` Per Community** (`130rj-enh generated-code-classifier-and-filters`) — 14 ACs completed. Key decisions: Heuristic suppression (`generated_node_fraction > 0.4`) instead of two-layer Leiden; Default `exclude_generated=False`
- **AOP/Advice Empty-Incoming Detection — `caller_pattern: "advice"` + Recovery Hint** (`130rj-enh aop-advice-empty-incoming-detection`) — 8 ACs completed. Key decisions: Match annotations by trailing segment (`Around` matches `org.aspectj.lang.annotation.Around`); Only emit `caller_pattern: "advice"` when incoming is empty
- **Java `method_reference` Nodes Are Not Classified as `call_sites` (Aceiss §1.2)** (`130r7-bug java-method-reference-call-sites`) — 6 ACs completed. Key decisions: Fix the classification, not add `line_available: false` flag; Diagnose via grammar inspection before adding multiple languages
- **Generated-Code Collapse Mode — File-as-Black-Box View for Architectural / Visualization Use** (`130su-enh generated-code-collapse-mode`) — 8 ACs completed. Key decisions: Opt-in (`collapse_generated_files=False` default), not default-on; Query-time collapse over persistent index change
- **C# AOP Attribute Detection — Extend `caller_pattern: "advice"` to C# Method-Boundary Aspects** (`130tc-enh csharp-aop-attribute-detection`) — 5 ACs completed. Key decisions: Reuse the existing `annotations` node field for C# attributes; Branch recovery hint on matched-tail set, not on file extension
- **Kotlin Reference Resolution — Enable Tree-Sitter-Backed Identifier Reference Extraction for Kotlin** (`130tc-enh kotlin-reference-resolution`) — 7 ACs completed. Key decisions: Exclude `property_declaration` from Kotlin's definition parents; Use a single `{"identifier"}` set for Kotlin's identifier node types rather than splitting into property_identifier / type_identifier
- **Fan-In Name-Collision Hint and Seed Note — Surface Simple-Name Attribution Risk on Common Method Names** (`130tw-enh fan-in-name-collision-hint-and-seed-note`) — 7 ACs completed. Key decisions: Observability + seed note rather than auto-suppression; Compute the map per-request, not at index time
- **`betweenness_computed` Field on `wave_graph_report` — Distinguish "Empty Section" from "Computation Disabled"** (`130tw-enh betweenness-computed-field`) — 5 ACs completed. Key decisions: Add observable `betweenness_computed` field rather than user-facing override; Use an enum string for `betweenness_skipped_reason`
- **Large Community Pagination — Return First 50 Members with `total_member_count` and Page Hint** (`130tw-enh large-community-pagination`) — 7 ACs completed. Key decisions: Default `limit=50`; Offset pagination over cursor
- **`exclude_external` Parameter on `wave_graph_report` — Filter External Library Calls from Architectural Rankings** (`130tw-enh exclude-external-from-graph-report`) — 6 ACs completed. Key decisions: Separate `exclude_external` flag rather than overloading `exclude_generated`; Default `False`
- **Java Receiver-Type Resolution — Filter False Cross-Class Callers on Method Name Matches** (`130tw-enh java-receiver-type-resolution`) — 9 ACs completed. Key decisions: Resolution instead of diagnostic warning; Bias toward including uncertain matches
## Acceptance Criteria

- Seeds 180/211 carry a question-type pattern library (bug investigation → consequence/callers/catalog; refactor → caller-shape/cross-community check; analogue-first → community drilldown; impact analysis → `include_tests=true/false` diff; edge cases → outgoing-helper traversal; cross-cutting → community + cross-layer; anti-patterns) plus the AOP advice fallback rule and the `code_ask` latency note (`130rj-enh seeds-pattern-library-and-recipes`).
- Seeds 213/214/221 carry reviewer-side graph recipes that inform the fix-now-vs-follow-on decision (code-reviewer: count incoming + same-community; architecture-reviewer: cross-community span; security-reviewer: production blast radius via `include_tests=false`) (`130rj-enh seeds-pattern-library-and-recipes`).
- Every server tool that returns a `community: "<label>"` field also returns `community_id: "project:cN"` alongside, eliminating the failed-call recovery dance (`130rj-enh graph-tool-shape-consistency`).
- `code_graph_community` accepts `limit` and `offset` and returns `total_node_count` and `has_more` so communities over ~50 nodes are usable inline (`130rj-enh graph-tool-shape-consistency`).
- `code_impact` adds `hop: N` to each `affected` entry so agents can distinguish direct (hop=1) from transitive (hop>1) breakage (`130rj-enh graph-tool-shape-consistency`).
- `wave_graph_report` gains a `communities` section listing top communities by `node_count` with `community_id`, `label`, `hub` (top-degree member); eliminates the per-community discovery dance (`130rj-enh graph-tool-shape-consistency`).
- `code_ask` gains a `fast_mode: bool = False` parameter that skips the cross-encoder reranker (RRF fallback). Seed guidance documents the `rerank_ms > 5000` threshold for switching to direct tools (`130rj-enh code-ask-seed-tightening`).
- In-file generation markers for **Java** (javacc `Generated By:JJTree`, ANTLR `Generated from`, protobuf `DO NOT EDIT`, `@Generated`, `@javax.annotation.Generated`, `@jakarta.annotation.Generated`) and **C#** (`<auto-generated>` / `<auto-generated/>` canonical Roslyn / T4 / source-generator marker, `[GeneratedCode]` attribute) plus path heuristics (`generated-sources/`, `build/generated/`, `generated/`, C#-specific `Service References/`, `Connected Services/`, and C# filename suffixes `.designer.cs`, `.g.cs`, `.g.i.cs`) plus `.gitattributes linguist-generated=true` tag classified files. Nodes from those files carry `generated: true`. Multi-language coverage beyond Java + C# (Go, TypeScript/JS, Rust, Swift, Kotlin, Python) is deferred to a follow-up change once operator validation confirms the architecture (`130rj-enh generated-code-classifier-and-filters`).
- `wave_graph_report` and `code_graph_community` accept `exclude_generated: bool = False`. `code_graph_community` returns `generated_node_fraction: float` per community. `wave_graph_report.betweenness` emits a `betweenness_dominated_by_generated: true` warning when >50% of top-N betweenness nodes are tagged generated (`130rj-enh generated-code-classifier-and-filters`).
- AOP/advice empty-incoming detection: when `code_callhierarchy` returns empty incoming AND the queried method's class/method has any of `@Advice.OnMethodEnter`, `@Advice.OnMethodExit`, `@Around`, `@Before`, `@After`, `@AfterReturning`, `@AfterThrowing` annotations, the response carries `caller_pattern: "advice"` with a recovery hint pointing at `TypeInstrumentation.transform()` / `@Aspect` pointcut searches. Seeds 180/211 carry the explicit "do not fall back to `code_references` for advice methods" rule (`130rj-enh aop-advice-empty-incoming-detection`).
- Java method references (`Foo::bar`, `this::bar`) classified as `call_sites`. `_TS_CALL_PARENT_TYPES["java"]` extended to include `method_reference`. Closes Aceiss §1.2's `line: null, snippet: null` symptom on Java incoming entries. Kotlin `callable_reference` added under the same fix if grammar inspection confirms the shape (`130r7`).
- `wave_graph_report` and dashboard graph-render endpoints gain `collapse_generated_files: bool = False` parameter. When True, each generated file is represented by one file-node; internal edges within generated files are dropped; cross-boundary edges have generated endpoints rewritten to file-nodes. Preserves "X calls into ELParser" topology without 330 internal parser nodes inflating visualizations. Opt-in per query; per-symbol navigation tools unchanged (`130su`).
- C# AOP attribute detection: `_ts_extract_csharp_attributes` walks `attribute_list` children of `method_declaration` / `class_declaration` nodes and populates the same `annotations` field Java uses. Advice-tail detection set in `code_callhierarchy_response` extended with PostSharp / Castle DynamicProxy / MethodBoundaryAspect attribute names (`OnEntry`, `OnExit`, `OnMethodBoundaryAspect`, `MethodInterceptionAspect`, etc.). Recovery-hint message is language-aware: when matched tails include C# names, the hint cites PostSharp / Castle and uses `glob='**/*.cs'` (`130tc-enh csharp-aop-attribute-detection`).
- Kotlin reference resolution enabled end-to-end: `_TREE_SITTER_REFERENCE_LANGS` + `_TREE_SITTER_DEFINITION_LANGS` add `"kotlin"`; `_TS_IDENTIFIER_NODE_TYPES["kotlin"] = {"identifier"}`; `_TS_DEFINITION_PARENT_TYPES["kotlin"]` covers class/object/interface/function/constructor (intentionally excludes `property_declaration` to match wave 130qf's variable-binding-scope rule); `_TS_IMPORT_PARENT_TYPES["kotlin"] = {"import_header"}`. Completes the deferral from 130r7 (`130tc-enh kotlin-reference-resolution`).
- AOP advice recovery hint converted from a `data["advice_recovery_hint"]` field to a structured `advice_pattern_detected` diagnostic per Change 6's original AC-3 contract (in-wave correction of implementation-phase review note).
- `GRAPH_BUILDER_VERSION` bumped (10 → 12) so existing graph caches re-extract with the new `generated` tag and annotation tracking (Java + C#) on upgrade.
- All existing tests continue to pass. New regression tests cover: generated-file classification end-to-end with javacc/ANTLR/protobuf headers; `exclude_generated` filter behavior; community label-vs-id dual return; pagination; per-hop attribution; AOP detection on a synthetic Java fixture; Java method-reference call-site attribution.

## Journal Watchpoints

- **Watchpoint:** `seed_edit_allowed` gate required before editing seeds 180/211/213/214/221. Open and close around each editing burst, not for the whole wave.
- **Watchpoint:** `framework_edit_allowed` gate required for all server_impl.py / graph_indexer.py / graph_cluster.py changes.
- **Watchpoint:** Generated-code classifier touches the indexer's file walk — verify no false positives on hand-written files with the word "generated" in a docstring or filename (e.g. `code_generator.py`). Path/header heuristics must be strict.
- **Watchpoint:** AOP annotation tracking requires extending the tree-sitter Java extraction to capture decorator/annotation strings on `method_declaration` nodes. Verify the annotation text travels through to the node payload.
- **Diagnosed in-wave:** Java incoming line/snippet bug (Aceiss §1.2) traced to `method_reference` nodes missing from `_TS_CALL_PARENT_TYPES["java"]`. Reproducer + fix in change `130r7-bug java-method-reference-call-sites`.

## Coordinator

- `wave-coordinator`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| implementer | implement | All five changes |
| code-reviewer | review | Tool-shape consistency, generated-code classifier, AOP detection |
| qa-reviewer | review | Regression coverage for each new field/parameter; synthetic Java fixture for AOP |

## Review Evidence

- wave-council-readiness: approved — 2026-05-31. Inline council with red-team, code-reviewer, performance-reviewer, qa-reviewer stances reviewing all six admitted change docs (130rj-enh seeds-pattern-library-and-recipes [implemented]; 130rj-enh graph-tool-shape-consistency [implemented]; 130rj-enh code-ask-fast-mode [implemented, revised per Aceiss clarification: dropped `fast_mode` API surface, scope collapsed to seed-text tightening]; 130rj-enh generated-code-classifier-and-filters; 130rj-enh aop-advice-empty-incoming-detection; 130r7-bug java-method-reference-call-sites). Strongest challenge: Change 5 (generated-code classifier) is the largest scope piece and its in-file header classifier failure modes are silently consequential downstream — mitigated by AC-1 + AC-4 positive/negative test pairing. Implementation order recommendation: Change 2 → Change 4 → 130r7 → Change 6 → Change 5 (Changes 1, 2, 4 already implemented). Six action items tracked: (1) Change 2 tests per AC-7; (2) MCP wrapper-layer regression tests for every new parameter (lesson from 130ol); (3) `GRAPH_BUILDER_VERSION` coordination between Changes 5 and 6; (4) operator-signoff and wave-council-delivery for close; (5) seed-shipped-first noted for retro; (6) implementation order respected. **PASS** — no blocking concerns; implementation proceeds.
- operator-signoff: <approved when operator confirms closure>

## Prepare Review Evidence

- code-reviewer: approved — 2026-05-31. Reviewed all six admitted change docs and the in-flight Change 2 edits at council. `_load_cluster_lookup_with_ids` additive, tuple-unpack with `(None, None)` default safe, `graph_impact` BFS rewrite preserves edge dedupe semantics, pagination clamps + legacy alias correct. Generated-code classifier scope (Change 5) is the largest single piece; AC pairing ensures false-positive guard. No findings ≥ medium severity.
- qa-reviewer: approved — 2026-05-31. Regression coverage plan reviewed per change. Each change carries explicit AC coverage. Coverage gap noted: MCP wrapper-layer regression tests for new parameters (lesson from wave 130ol); tracked as wave-level action item. No blocking gaps.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-05-31: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: Change 5 (generated-code classifier) is the largest single piece and its in-file header classifier false-positive failure modes are silently consequential downstream — operators receive incorrect `generated: true` tags into fan_in/fan_out/communities/betweenness if the classifier misclassifies handwritten code; strongest-alternative: split Change 5 into Change-5a (classifier + tag only) + Change-5b (filters + warning) shipping sequentially — rejected because classifier-without-filters has no observable behavior, mitigation is AC-1/AC-4 positive/negative test pairing on `code_generator.py`-shaped negative cases + operator-reportable failure modes captured in the change's risk table)
- **In-wave scope addition** — 2026-05-31: `130su-enh generated-code-collapse-mode` added per operator direction during implementation. Consumes the same `generated: true` tag Change 5 produces — companion mode (filter-noise vs collapse-hairball over one classification). No new classifier failure modes introduced; council's strongest-challenge applies equally to both changes. Mid-wave scope expansion logged here per stage-gate hygiene; full council re-review not warranted (architectural shape unchanged; new change adds a query-time view, not a new index pass).

## Dependencies

- No external wave dependencies. Built on top of wave 130et (130eu/130f9/130nf/130o2/130o3/130ol/130qf) which shipped the graph extractor foundation.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
