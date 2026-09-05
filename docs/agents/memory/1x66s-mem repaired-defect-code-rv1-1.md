# Repaired defect CODE-RV1-1

Owner: Engineering
Status: rejected
Last verified: 2026-09-05

Memory ID: `1x66s-mem repaired-defect-code-rv1-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-05
Updated: 2026-09-05
Source exploration cost: 1844619
Source event: `finding:1x6ti:CODE-RV1-1`
Validation: reject
Validated by: agent
Action delta: No durable action beyond the test that now pins the clause's locality and boundary; the reusable lesson is carried by the rewritten CODE-DEL-1 record.
Validation rationale: A test-gap finding (the repair clause's locality and directory boundary were unpinned) repaired by one test in DanglingEndpointFilterTests; the draft's target is a scratch probe that is not in the tree, and the durable rule (any change to the filter predicate needs locality, boundary and non-resurrection tests) is stated in the rewritten CODE-DEL-1 memory.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1x6ti: Repair verified.

## Evidence

- `CODE-RV1-1`
- `ev-code-rv1-1-3`
- `1x6ti`

## Targets

- `probe_blast.py`
