# No-units rules must not become no-coverage rules; oracles need a fixture per excluded construct

Owner: Engineering
Status: active
Last verified: 2026-08-27

Memory ID: `1wgg5-mem no-units-rules-must-not-become-no-coverage-rules-oracles-nee`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-08-27
Updated: 2026-08-27
Source exploration cost: 368764
Source event: `finding:1wik9:RT-DEL-1`
Validation: promote
Validated by: agent
Action delta: When a format rule says a construct creates no retrieval UNITS (detached comments, options), never let the implementation also drop that construct's TEXT from the residue chunk: unit policy and coverage policy are separate invariants, and the coverage differential must carry a fixture that exercises the excluded construct (license headers) or the hole stays invisible.
Validation rationale: Verified against the current tree: chunk_proto's residue now keeps comment lines (matching the GraphQL sdl: and AsyncAPI spec: residues), the pinned regression test_proto_detached_comments_keep_residue_coverage passes, and the wave's coverage oracle carries the inline detached-license fixture so the class stays exercised. Evidence chain RT-DEL-1 through ev-rt-del-1-3 followed; the finding was demonstrated through the wave's own oracle, which is the durable target.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1wik9 RT-DEL-1: chunk_proto implemented the detached-comments-create-no-units rule by filtering comment lines out of the proto: residue too, so a detached license header on a DETECTED file reached no chunk at all — a coverage-invariant violation the committed differential could not see because no fixture contained a detached comment. Repair: residue keeps comment lines (unit policy unchanged), and the coverage oracle gained inline fixtures for the repaired classes so the frozen golden corpus stays untouched while the hole stays permanently exercised.

## Evidence

- `RT-DEL-1`
- `ev-rt-del-1-3`
- `test_chunker.SpecFamilyTests.test_proto_detached_comments_keep_residue_coverage`

## Targets

- `.wavefoundry/framework/scripts/chunker.py`
- `docs/waves/1wik9 fenced-diagram-and-spec-retrieval/evidence/coverage_differential_1wfso.py`
