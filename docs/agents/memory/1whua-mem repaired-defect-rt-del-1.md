# Repaired defect RT-DEL-1

Owner: Engineering
Status: superseded
Last verified: 2026-08-27

Memory ID: `1whua-mem repaired-defect-rt-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-27
Updated: 2026-08-27
Source exploration cost: 368764
Source event: `finding:1wik9:RT-DEL-1`
Validation: rewrite
Validated by: agent
Action delta: When a format rule says a construct creates no retrieval UNITS (detached comments, options), never let the implementation also drop that construct's TEXT from the residue chunk: unit policy and coverage policy are separate invariants, and the coverage differential must carry a fixture that exercises the excluded construct (license headers) or the hole stays invisible.
Validation rationale: Verified against the current tree: chunk_proto's residue now keeps comment lines (matching the GraphQL sdl: and AsyncAPI spec: residues), the pinned regression test_proto_detached_comments_keep_residue_coverage passes, and the wave's coverage oracle carries the inline detached-license fixture so the class stays exercised. Evidence chain RT-DEL-1 through ev-rt-del-1-3 followed; the finding was demonstrated through the wave's own oracle, which is the durable target.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1wgg5-mem no-units-rules-must-not-become-no-coverage-rules-oracles-nee`
## Summary

Real defect fixed in wave 1wik9: repair verified complete by an independent fresh context; Requirement 4 (no units for detached comments) and Requirement 7 (coverage kept) now hold together, matching the sibling formats

## Evidence

- `RT-DEL-1`
- `ev-rt-del-1-3`
- `1wik9`

## Targets

- `evidence/coverage_differential_1wfso.py`
