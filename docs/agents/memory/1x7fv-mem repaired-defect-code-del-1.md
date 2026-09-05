# Repaired defect CODE-DEL-1

Owner: Engineering
Status: rejected
Last verified: 2026-09-05

Memory ID: `1x7fv-mem repaired-defect-code-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-05
Updated: 2026-09-05
Source exploration cost: 1844619
Source event: `finding:1x6ti:CODE-DEL-1`
Validation: reject
Validated by: agent
Action delta: The draft's targets are scratch probes absent from the tree, so it cannot be rewritten in place; the durable lesson (the outage exemption is keyed on the last published payload, never on the directory alone) is recorded as a hand-authored fragile-file memory on graph_indexer.py.
Validation rationale: Real defect, wrong carrier: the generated record names scratchpad probes as targets and the tool refuses a rewrite whose original targets are not in the tree. The verified mechanism (a node-less file under an unreadable directory has no store row; the shipped _edge_servable keeps such an edge only when its triple is in the last published payload) is written as its own record.
Evidence verified: true
Current target verified: false
Canonical overlap: none
## Summary

Real defect fixed in wave 1x6ti: Repair verified; the clause's own locality and its resurrection window are raised as CODE-RV1-1 and CODE-RV1-2.

## Evidence

- `CODE-DEL-1`
- `ev-code-del-1-3`
- `1x6ti`

## Targets

- `scratchpad/dl_code_1x6ti/probe_q2b.py`
- `scratchpad/rv1_code_1x6ti/mutantA.py`
- `indexer.py`
