# Repaired defect QA-RV1-2

Owner: Engineering
Status: rejected
Last verified: 2026-09-05

Memory ID: `1x6kq-mem repaired-defect-qa-rv1-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-05
Updated: 2026-09-05
Source exploration cost: 1844619
Source event: `finding:1x6ti:QA-RV1-2`
Validation: reject
Validated by: agent
Action delta: No durable action; the directory-boundary pin is one test and the rule is carried by the rewritten CODE-DEL-1 record.
Validation rationale: QA-RV1-2 is the same test gap as CODE-RV1-1 seen from the QA lane (the boundary-less prefix mutant survived), repaired by the same test; the draft's target is a scratch probe absent from the tree and the lesson is already recorded.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1x6ti: Repair verified.

## Evidence

- `QA-RV1-2`
- `ev-qa-rv1-2-3`
- `1x6ti`

## Targets

- `rv2_qa_1x6ti/probe.py`
