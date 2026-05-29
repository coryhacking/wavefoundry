# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-05-27

wave-id: `12xr3 graph-augmentation-promotion`
Title: Graph Augmentation Promotion

## Objective

Promote graph augmentation from opt-in to the default behavior of existing MCP tools, after production validation of the graph query surface confirms the graph layer is stable and results are high quality.

## Changes

Change ID: `12xs5-feat graph-augmentation-promotion`
Change Status: `planned`

## Wave Summary

Flips the default for the `graph` parameter on `code_keyword`, `code_search`, `code_definition`, and `code_references` from `false` to `true`. This wave is conditional — it must not open until the graph query surface wave has run in production long enough to confirm that graph neighbor results are accurate, non-noisy, and do not degrade existing search quality. Explicit operator sign-off is required as the opening gate.

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

- operator-signoff: <approved when operator confirms closure>
- production-validation-signoff: <explicit confirmation that Phase 2 graph results are stable and non-noisy>

## Dependencies

- Depends on wave `12xr2 graph-query-surface` being closed and validated in production use before this wave opens.
- Do not open on wave close alone — requires explicit production-validation sign-off.
