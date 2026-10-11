# Use stored call sites in call hierarchy

Change ID: `2073s-bug hierarchy-call-site-provenance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-10
Wave: 2071o graph-query-provenance

## Rationale

Tensorwell's incoming hierarchy for qualification.rs::collect reports the iterator .collect() at line 1224, although the canonical stored edge identifies the free collect invocation at line 1240. The upstream scratch probe reproduces the same failure: persisted line 3 becomes served line 2. code_callhierarchy_response drops edge call_sites in _attach_edge_trust and then rescans a bare label without a verified caller-end boundary. The earlier callgraph repair already consumes stored provenance; this change repairs the distinct hierarchy response.

The operator now authorizes preparation, review and implementation, including broader supported-language coverage. Closure remains operator-owned.

## Requirements

1. Both incoming and outgoing project call edges use persisted, edge-specific call_sites as location authority. Preserve all structurally valid sites in an additive call_sites field, with one deterministic representative in the existing singular call_site. Incoming line/snippet follow that representative; outgoing top-level line remains the callee definition line and snippet remains null, as the current public contract requires. Keep one relationship per graph edge; invocation multiplicity must not inflate edge counts.

2. A site is admissible only when it belongs to that edge's caller source file and its coordinates are structurally valid. Order valid sites by source file, start byte when available, line and column; deterministically deduplicate identical coordinates. Preserve graph relation, confidence, target identity and byte/line coordinates.

3. Source text is optional presentation. A missing or changed file must not replace persisted coordinates with a guessed occurrence. Attach a bounded snippet only when indexed source identity establishes that the recorded source version is current; if source identity cannot establish freshness, omit the snippet and retain coordinates explicitly as indexed provenance. Missing or malformed provenance produces call_sites: [], call_site: null and no incoming precise line/snippet; outgoing definition fields remain unchanged. Do not rescan a bare name to fabricate a location.

4. Preserve incoming/outgoing direction, context_depth, include_tests/external filtering and the existing legacy Java receiver filter. Any legacy name scan retained solely for that filter must not become location authority. Existing graph schemas and source-freshness contracts remain unchanged. If existing artifacts cannot prove snippet freshness, nullable snippets are the accepted compatible outcome.

5. Capture edge-specific coordinates during ordinary Python AST and shared tree-sitter extraction for supported call-expression paths, preserving them through resolution, merging and graph publication. Preserve Rust occurrence-sensitive resolution. Increment the graph builder version so existing non-Rust extraction records regenerate under the normal refresh path. No eager repository rebuild or additional upgrade scan is introduced.

6. Verify the supported-language registry and report coverage by parser/call-expression family. Config/markup formats need not gain invented callable relationships. A parser fallback that cannot establish caller ownership, including the JavaScript regex fallback, must keep locations unknown. Document this limit and distinguish language support from exercised syntax.

## Scope

**Problem statement:** Use stored call sites in call hierarchy to repair the confirmed behavior described above.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `.wavefoundry/framework/scripts/wf_server/graph_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/graph-index-system.md`

**Out of scope:** New parsing or resolution modes, graph schema redesign, eager rebuilds or additional upgrade work, source freshness guarantees, changing relationship cardinality, unrelated callgraph refactoring and fallback caller-ownership repair.

## Acceptance Criteria

- [x] AC-1: Incoming and outgoing served hierarchy edges identify their own stored invocations when unrelated receivers or a free function share the label, including a prior macro call. Oracle: isolated canonical graph publication plus actual public response and independently identified source expressions.
- [x] AC-2: Multiple distinct stored occurrences remain visible in call_sites while singular fields select the same deterministic representative and relationship counts remain unchanged. Oracle: shuffled/duplicate stored-site inputs and response comparisons.
- [x] AC-3: Missing, malformed, wrong-file or stale source/provenance never yields a newly guessed precise site or an unjustified snippet. Oracle: independent negative fixtures with absent source, changed source, adjacent non-caller functions and same-line occurrences.
- [x] AC-4: Existing Java legacy filtering and graph trust, direction, test/external and context contracts remain valid. Oracle: served-path regressions and known-bad controls that remove edge-specific provenance selection.

- [x] AC-5: Real Python AST and supported tree-sitter call-expression paths retain exact call coordinates from extraction through canonical publication to both served hierarchy directions, including repeated and same-name calls. Oracle: a registry-derived syntax-family matrix, source-expression coordinates independently specified, unchanged target/trust/count controls and incremental builder-version invalidation.
- [x] AC-6: Missing parsers and degraded/fallback extraction do not manufacture precise locations where caller ownership is unproven; the supported registry and exercised coverage/limits are documented. Oracle: explicit fallback fixtures with real emitted edges and served unknown fields, plus config/markup no-call controls.

## Tasks

- [x] Add served-path or scanner regression coverage reproducing the confirmed defects with realistic adjacent controls.
- [x] Implement only the admitted requirements and preserve the stated compatibility boundaries.
- [x] Run affected tests and selected known-bad controls; record actual AC evidence as each completes.
- [x] Complete independent delivery review and applicable framework qualification before proposing closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Repair | implementer | Current typed readiness and implementation authorization | Single writer for shared modules |
| Verification | required reviewer lanes | Frozen implementation | Fresh independent contexts |
| Integration | wave-coordinator | Verified repair | Reconcile scope, ACs and full qualification |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/graph_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/graph-index-system.md`

## Affected Architecture Docs

docs/architecture/graph-index-system.md; docs/specs/mcp-tool-surface.md.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Incoming and outgoing served hierarchy edges identify their own stored invocations when unrelated receivers or a free function share the label, including a prior macro call |
| AC-2 | required | Multiple distinct stored occurrences remain visible in call_sites while singular fields select the same deterministic representative and relationship counts remain unchanged |
| AC-3 | required | Missing, malformed, wrong-file or stale source/provenance never yields a newly guessed precise site or an unjustified snippet |
| AC-4 | required | Existing Java legacy filtering and graph trust, direction, test/external and context contracts remain valid |
| AC-5 | required | Correct locations require provenance producers outside Rust, not only a shared response repair |
| AC-6 | required | Honest degraded behavior avoids precise-looking but unproven fallback locations |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-10 | Repair1 frozen:1175affected-module tests/0skips,105final quality/0skips;10qualified mutants killed. Runtime/requirements and historical originals unchanged. | Exact parity/source-byte/Kotlin controls and new11path fingerprint summarized in wave.md; independent rechecks pending |
| 2026-10-10 | First delivery council withholds qualification for current fixture/report drift and a false architecture mechanism paragraph. Typed cycle1 repair starts; admitted requirements unchanged. | Bounded five-path repair, fresh affected-lane review, then quiet full suite |
| 2026-10-10 | The Session Handoff section preserves the original planning checkpoint; current implementation/qualification status is in this Progress Log, wave.md and docs/agents/session-handoff.md. No admitted requirement changed. | Preserve current review-policy receipt; completion markers are bookkeeping only |
| 2026-10-10 | Behavioral ACs verified on frozen implementation: final58focused tests/0skips8.581s;13disposable mutants killed. Full qualification and independent delivery remain pending. | Canonical CallProvenanceExtractionTests, PythonPhysicalLineProvenanceTests, TestPersistedCallProvenance, RustContainingSymbolLookupTests and TestRustContainingImpact; mutation table in wave.md |
| 2026-10-10 | Readback: persist exact invocation UTF-8 coordinates in ordinary Python AST/shared tree-sitter calls, preserve merge/publication and Rust per-occurrence resolution, and present those sites in both hierarchy directions. Earlier unrelated collect sites currently win; afterwards the stored expression is authoritative. Preserve outgoing definition fields/trust/counts/legacy Java filter, plural occurrences and nullable unproven snippets. AC-1–AC-6; graph_indexer.py/graph_handlers.py, focused tests and two contract docs. Normal builder bump only; no eager upgrade scan, new parsing mode or fallback ownership claim. | Current typed readiness; actual source/extraction/publication/public-handler known-bad controls |
| 2026-10-09 | Plan only. Current defect mechanisms exercised by the finite upstream scratch probe; no repaired behavior claimed. Downstream cost measurements are attributed, with upstream identity verification only for the named profile. | Wave baseline captures; updated Tensorwell diagnostic report |
| 2026-10-09 | Optional Review plan resolves contract branches from source and accepted summary ADR: stored provenance, nullable unproven snippets, compatible singular fields; bounded scope/work and reporting state; preserve producer protocol. No unresolved operator choice or implementation authorization inferred. | Requirements and Decision Log |

## Decision Log

| Date | Decision | Reason and alternatives |
| --- | --- | --- |
| 2026-10-09 | Original narrow pre-plan choice | Selected stored-edge provenance with an additive plural field. This assumed stored provenance existed outside Rust; the 2026-10-10 scope probes corrected that assumption. |
| 2026-10-10 | Broaden ordinary producers under operator direction | Actual extraction/publication/served probes reproduce wrong locations in Python, JavaScript, C++, Go, Java and Rust; C also loses multiple invocation sites. Retain the existing schema and normal builder-version invalidation. Rejected consumer-only unknown locations for all non-Rust calls because it would not deliver accurate navigation. Keep unproven regex fallback locations unknown. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A small historical reproducer misses a related supported input | Use the derived contract classes and adjacent controls in ACs, not only the reported line/path |
| Bounds or missing evidence appear as successful absence | Preserve explicit unknown/incomplete states and make negative controls non-vacuous |
| A compatibility repair widens into unrelated redesign | Keep scope explicit; return material contradictions to planning |

## Session Handoff

Scope revised for broader language coverage; re-Prepare and independent readiness review are required before implementation. Implementation/delivery ACs remain unchecked. See `docs/agents/session-handoff.md`.
