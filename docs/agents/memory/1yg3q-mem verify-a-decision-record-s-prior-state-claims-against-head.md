# Verify a decision record's prior-state claims against HEAD

Owner: Engineering
Status: active
Last verified: 2026-09-19

Memory ID: `1yg3q-mem verify-a-decision-record-s-prior-state-claims-against-head`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-09-19
Updated: 2026-09-19
Source exploration cost: 384402
Source event: `finding:1y0h1:QA-DEL-1`
Validation: promote
Validated by: agent
Action delta: Before writing a decision record's account of the prior state, grep HEAD docs and tests for what already guarded the behavior, and state those guards rather than asserting it was undocumented.
Validation rationale: The generated summary is reverification boilerplate. The real lesson from QA-DEL-1: the 1y0h1 decision record claimed the wrapper order was documented only in a comment, but at HEAD docs/contributing/build-and-verification.md stated it and the 1y0do WrapperOrderTests and RosterRuntimeParityTests pinned order and parity; the claim was written from recollection and blocked delivery.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1y0h1's decision record said the MCP wrapper order was documented only in a comment before the wave; at HEAD it was already stated in docs/contributing/build-and-verification.md and pinned by the 1y0do WrapperOrderTests and RosterRuntimeParityTests, and qa-reviewer blocked delivery on the false sentence. When a record describes what existed before a change, grep HEAD docs and tests for existing guards (git grep over docs, test names) and name them; "only", "never" and "undocumented" are census claims that need a search.

## Evidence

- `QA-DEL-1`
- `ev-qa-del-1`
- `ev-qa-del-1-3`
- `1y0h1`

## Targets

- `docs/architecture/decisions/1ye5y-adr flat-sibling-tool-registry.md`
- `docs/contributing/build-and-verification.md`
- `.wavefoundry/framework/scripts/tests/test_tool_surface_golden.py`
