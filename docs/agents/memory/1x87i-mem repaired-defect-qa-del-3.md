# Repaired defect QA-DEL-3

Owner: Engineering
Status: rejected
Last verified: 2026-09-05

Memory ID: `1x87i-mem repaired-defect-qa-del-3`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-05
Updated: 2026-09-05
Source exploration cost: 1844619
Source event: `finding:1x6ti:QA-DEL-3`
Validation: reject
Validated by: agent
Action delta: The draft's target is a scratch probe absent from the tree, so it cannot be rewritten in place; the durable lesson (a meta reader validates every entry with no coercion and no default) is recorded as a hand-authored memory on index_state_store.py.
Validation rationale: Real defect, wrong carrier: the generated record names a scratchpad probe as its target and the tool refuses a rewrite whose original target is not in the tree. The verified mechanism (reap_state_for_index gating every per-table value through _is_count and reading an entry-less record as none) is written as its own record.
Evidence verified: true
Current target verified: false
Canonical overlap: none
## Summary

Real defect fixed in wave 1x6ti: Repair verified; the looseness is tightened under QA-RV1-3.

## Evidence

- `QA-DEL-3`
- `ev-qa-del-3-3`
- `1x6ti`

## Targets

- `rv1_qa_1x6ti/probe_reap.py`
