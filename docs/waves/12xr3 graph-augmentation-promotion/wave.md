# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-31

wave-id: `12xr3 graph-augmentation-promotion`
Title: Graph Augmentation Promotion

## Objective

Promote graph augmentation from opt-in to the default behavior of existing MCP tools, after production validation of the graph query surface confirms the graph layer is stable and results are high quality.

## Changes

Change ID: `12xs5-feat graph-augmentation-promotion`
Change Status: `implemented`

Change ID: `13006-enh bidirectional-graph-path-search`
Change Status: `implemented`

Change ID: `1301h-enh graph-driven-code-definition-narrowing`
Change Status: `implemented`

Completed At: 2026-05-30

## Wave Summary

Wave `12xr3` (Graph Augmentation Promotion) delivered 3 changes: Graph Augmentation Promotion, Bidirectional Graph Path Search, and Graph-driven `code_definition` File Narrowing.

**Changes delivered:**

- **Graph Augmentation Promotion** (`12xs5-feat graph-augmentation-promotion`) — 8 ACs completed. Key decisions: Flip default on all four tools in a single change rather than tool-by-tool; Invert the existing `GraphQueryGoldenDefaultTests` rather than delete
- **Bidirectional Graph Path Search** (`13006-enh bidirectional-graph-path-search`) — 7 ACs completed. Key decisions: Naive symmetric BFS (walk `_out` + `_in` from start, single visited set); Default `direction="forward"` preserves pre-change behavior
- **Graph-driven `code_definition` File Narrowing** (`1301h-enh graph-driven-code-definition-narrowing`) — 7 ACs completed. Key decisions: Narrow file set via graph then run existing scanners; Candidate collection uses `label == symbol`, `id.endswith(::symbol)`, and `symbol in label`
## Acceptance Criteria

- `code_keyword`, `code_search`, `code_definition`, `code_references` return graph neighbor results by default with no `graph=true` parameter required
- `graph=false` is accepted and correctly suppresses graph output for callers that opt out
- No regression in existing tool output when a queried symbol has no graph edges
- Promotion validated against at least one real project query session confirming graph results improve rather than distract

## Journal Watchpoints

- **Conditional wave**: do not open without explicit operator sign-off confirming Phase 2 production validation is complete
- Opening trigger is validation of results quality, not just wave close — do not open on wave close alone
- **Watchpoint:** keep this wave blocked until the query-surface wave has been validated in production and graph neighbor results are confirmed stable and non-noisy.
- If graph quality issues are found during Phase 2 validation, keep this wave closed and fix in the query surface wave first
- After promotion, monitor `code_keyword` and `code_search` result quality for any degradation

## Review Evidence

- wave-council-readiness: approved — 2026-05-30; single-change wave with a one-line code surface (flip `graph: bool = False` → `graph: bool = True` on four MCP tool signatures); risk profile is low because the augmentation code path is unchanged, opt-out is preserved, and the change is gated behind the operator's production-validation signoff. No additional council seats required — scope does not warrant full-tier council. Inline readiness review: (a) the wave's hard conditional gate (production validation) is released via operator signoff below; (b) the change doc captures requirements, ACs, tasks, and risks completely; (c) the augmentation surface was reviewed in wave `12xr2` close-review; this wave only flips the entry-point default. Admissible for implementation.
- production-validation-signoff: approved — 2026-05-30; operator validated graph augmentation against real query sessions across `code_keyword`, `code_search`, `code_definition`, `code_references`; confirmed neighbor results are accurate and additive, not noisy or distracting. Conditional gate (Phase 2) released.
- wave-council-delivery: approved — 2026-05-30; inline close-review with red-team and security-reviewer covering three admitted changes (12xs5 default flip, 13006 bidirectional path search, 1301h graph-driven definition narrowing). Red-team: response-size cap unchanged, opt-out preserved with wrapper-helper test coverage, bidirectional BFS deterministic with visited-set sharing and max_hops cap, advisory-degraded variant of 1301h preserves existing test contract. Security: read-only at MCP wire; sync graph refresh in 1301h bounded by existing `_index_build_lock`. Measured impact: 175–234× speedup on cold `code_definition` calls (42s → ~200ms); 188× on definitive-not-found (54s → 151ms). PASS.
- operator-signoff: approved — 2026-05-30; operator authorized the default flip in 12xs5, the bidirectional path search in 13006, and the graph-driven definition narrowing in 1301h (including the close-review pivot from fail-fast to advisory-degraded after the test-suite impact was scoped). Confirmed wave is closure-ready after final task-marker audit.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-05-30: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: high-frequency tool response size could push past MCP budgets after default-on augmentation; strongest-alternative: leave default opt-in and only flip per-tool after per-tool budget validation — rejected because `graph_limit=5` cap is unchanged and operator validation covered the four tools holistically with the same cap)

## Dependencies

- Depends on wave `12xr2 graph-query-surface` being closed and validated in production use before this wave opens.
- Do not open on wave close alone — requires explicit production-validation sign-off.
