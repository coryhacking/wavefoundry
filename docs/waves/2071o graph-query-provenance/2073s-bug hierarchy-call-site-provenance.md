# Use stored call sites in call hierarchy

Change ID: `2073s-bug hierarchy-call-site-provenance`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-10-09
Wave: 2071o graph-query-provenance

## Rationale

Tensorwell's incoming hierarchy for qualification.rs::collect reports the iterator .collect() at line 1224, although the canonical stored edge identifies the free collect invocation at line 1240. The upstream scratch probe reproduces the same failure: persisted line 3 becomes served line 2. code_callhierarchy_response drops edge call_sites in _attach_edge_trust and then rescans a bare label without a verified caller-end boundary. The earlier callgraph repair already consumes stored provenance; this change repairs the distinct hierarchy response.

The operator requested Plan, Prepare and Review only. No implementation, activation, closure, commit, push or package build is authorized by this request.

## Requirements

1. Both incoming and outgoing project call edges use persisted, edge-specific call_sites as location authority. Preserve all structurally valid sites in an additive call_sites field, with one deterministic representative in the existing singular call_site. Incoming line/snippet follow that representative; outgoing top-level line remains the callee definition line and snippet remains null, as the current public contract requires. Keep one relationship per graph edge; invocation multiplicity must not inflate edge counts.

2. A site is admissible only when it belongs to that edge's caller source file and its coordinates are structurally valid. Order valid sites by source file, start byte when available, line and column; deterministically deduplicate identical coordinates. Preserve graph relation, confidence, target identity and byte/line coordinates.

3. Source text is optional presentation. A missing or changed file must not replace persisted coordinates with a guessed occurrence. Attach a bounded snippet only when indexed source identity establishes that the recorded source version is current; if source identity cannot establish freshness, omit the snippet and retain coordinates explicitly as indexed provenance. Missing or malformed provenance produces call_sites: [], call_site: null and no incoming precise line/snippet; outgoing definition fields remain unchanged. Do not rescan a bare name to fabricate a location.

4. Preserve incoming/outgoing direction, context_depth, include_tests/external filtering and the existing legacy Java receiver filter. Any legacy name scan retained solely for that filter must not become location authority. No graph rebuild or extraction/schema change is required. If existing artifacts cannot prove snippet freshness, nullable snippets are the accepted compatible outcome; do not expand this repair into new extraction metadata.

## Scope

**Problem statement:** Use stored call sites in call hierarchy to repair the confirmed behavior described above.

**In scope:**

- `.wavefoundry/framework/scripts/wf_server/graph_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/graph-index-system.md`

**Out of scope:** Extraction/resolution changes, graph rebuilding, source freshness guarantees, changing relationship cardinality, unrelated callgraph refactoring, and implementation during this request.

## Acceptance Criteria

- [ ] AC-1: Incoming and outgoing served hierarchy edges identify their own stored invocations when unrelated receivers or a free function share the label, including a prior macro call. Oracle: isolated canonical graph publication plus actual public response and independently identified source expressions.
- [ ] AC-2: Multiple distinct stored occurrences remain visible in call_sites while singular fields select the same deterministic representative and relationship counts remain unchanged. Oracle: shuffled/duplicate stored-site inputs and response comparisons.
- [ ] AC-3: Missing, malformed, wrong-file or stale source/provenance never yields a newly guessed precise site or an unjustified snippet. Oracle: independent negative fixtures with absent source, changed source, adjacent non-caller functions and same-line occurrences.
- [ ] AC-4: Existing Java legacy filtering and graph trust, direction, test/external and context contracts remain valid. Oracle: served-path regressions and known-bad controls that remove edge-specific provenance selection.

## Tasks

- [ ] Add served-path or scanner regression coverage reproducing the confirmed defects with realistic adjacent controls.
- [ ] Implement only the admitted requirements and preserve the stated compatibility boundaries.
- [ ] Run affected tests and selected known-bad controls; record actual AC evidence as each completes.
- [ ] Complete independent delivery review and applicable framework qualification before proposing closure.

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

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | Plan only. Current defect mechanisms exercised by the finite upstream scratch probe; no repaired behavior claimed. Downstream cost measurements are attributed, with upstream identity verification only for the named profile. | Wave baseline captures; updated Tensorwell diagnostic report |
| 2026-10-09 | Optional Review plan resolves contract branches from source and accepted summary ADR: stored provenance, nullable unproven snippets, compatible singular fields; bounded scope/work and reporting state; preserve producer protocol. No unresolved operator choice or implementation authorization inferred. | Requirements and Decision Log |

## Decision Log

| Date | Decision | Reason and alternatives |
| --- | --- | --- |
| 2026-10-09 | Divergent pre-plan choice | Selected stored-edge provenance with an additive plural field and compatible singular representative. Rejected a more elaborate receiver-aware rescan: still invents a location from current text and loses extraction identity. Rejected a graph format/reindex migration: current stored edges already contain the required sites. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A small historical reproducer misses a related supported input | Use the derived contract classes and adjacent controls in ACs, not only the reported line/path |
| Bounds or missing evidence appear as successful absence | Preserve explicit unknown/incomplete states and make negative controls non-vacuous |
| A compatibility repair widens into unrelated redesign | Keep scope explicit; return material contradictions to planning |

## Session Handoff

Planned only. Readiness evidence belongs to the wave's typed ledger; implementation/delivery ACs remain unchecked. See `docs/agents/session-handoff.md`.
