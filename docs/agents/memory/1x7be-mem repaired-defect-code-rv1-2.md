# Repaired defect CODE-RV1-2

Owner: Engineering
Status: rejected
Last verified: 2026-09-05

Memory ID: `1x7be-mem repaired-defect-code-rv1-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-05
Updated: 2026-09-05
Source exploration cost: 1844619
Source event: `finding:1x6ti:CODE-RV1-2`
Validation: reject
Validated by: agent
Action delta: No separate action; the last-published-payload keying is the substance of the rewritten CODE-DEL-1 record.
Validation rationale: CODE-RV1-2 is the second half of the same mechanism as CODE-DEL-1 (the directory-only exemption resurrected dropped edges; the narrowing keyed on the last published payload fixed it); the rewritten CODE-DEL-1 memory records both halves and the shipped predicate. The draft's target is a scratch probe absent from the tree.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1x6ti: Repair verified.

## Evidence

- `CODE-RV1-2`
- `ev-code-rv1-2-3`
- `1x6ti`

## Targets

- `rv2_code_1x6ti/probe_blast.py`
