# Repaired defect MODEL-BOM-1

Owner: Engineering
Status: rejected
Last verified: 2026-09-21

Memory ID: `1yk7h-mem repaired-defect-model-bom-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-21
Updated: 2026-09-21
Source exploration cost: 741011
Source event: `finding:1ycrj:MODEL-BOM-1`
Validation: reject
Validated by: agent
Action delta: No separate durable instruction is needed: the required BOM behavior is encoded in the full-render regression matrices.
Validation rationale: Followed MODEL-BOM-1 and its code/QA reverification; inspected the corrected delimiter and valid/malformed BOM matrices. The proposed target tmp/1ycrj-bom-qa-probe.py is not a repository file. Promoting would preserve a disposable probe location and duplicate tested AC-2 behavior without changing a future action.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1ycrj: The narrow delimiter recognition repair satisfies AC2/AC3 for BOM fixtures; known-bad restoration demonstrably rejected.

## Evidence

- `MODEL-BOM-1`
- `ev-model-bom-1-4`
- `1ycrj`

## Targets

- `tmp/1ycrj-bom-qa-probe.py`
