# Repaired defect QA-DEL-1

Owner: Engineering
Status: superseded
Last verified: 2026-09-19

Memory ID: `1ydpo-mem repaired-defect-qa-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-19
Updated: 2026-09-19
Source exploration cost: 384402
Source event: `finding:1y0h1:QA-DEL-1`
Validation: rewrite
Validated by: agent
Action delta: Before writing a decision record's account of the prior state, grep HEAD docs and tests for what already guarded the behavior, and state those guards rather than asserting it was undocumented.
Validation rationale: The generated summary is reverification boilerplate. The real lesson from QA-DEL-1: the 1y0h1 decision record claimed the wrapper order was documented only in a comment, but at HEAD docs/contributing/build-and-verification.md stated it and the 1y0do WrapperOrderTests and RosterRuntimeParityTests pinned order and parity; the claim was written from recollection and blocked delivery.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1yg3q-mem verify-a-decision-record-s-prior-state-claims-against-head`
## Summary

Real defect fixed in wave 1y0h1: The original reproduction no longer contradicts the record; qa-reviewer clears itself.

## Evidence

- `QA-DEL-1`
- `ev-qa-del-1-3`
- `1y0h1`

## Targets

- `tests/test_tool_surface_golden.py`
