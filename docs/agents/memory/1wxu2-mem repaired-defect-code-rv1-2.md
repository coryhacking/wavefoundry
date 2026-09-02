# Repaired defect CODE-RV1-2

Owner: Engineering
Status: active
Last verified: 2026-09-02

Memory ID: `1wxu2-mem repaired-defect-code-rv1-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-02
Updated: 2026-09-02
Source exploration cost: 2790236
Source event: `finding:1wpif:CODE-RV1-2`
Validation: promote
Validated by: agent
Action delta: In a framework test module, obtain the server module through the module's own loader rather than a bare import, so each class resolves its own dependency and runs standalone.
Validation rationale: Followed the three ledger records and checked the file, which exists and is part of this wave. The defect is precise and reproducible: a bare import in setUp resolved only because an earlier test in the same module had already pushed the scripts root onto the path, so running one class or one test in isolation failed at import. Seven sites were converted to the module's own loader, an independent lane confirmed all seven run standalone with no bare import left in the file, and it found one residual instance elsewhere that was repaired in a later cycle. The lesson generalizes to any test module that depends on a loader side effect.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
## Summary

Real defect fixed in wave 1wpif: The named file is exhaustively repaired and independently verified; the residual site outside it is CODE-RV2-2, repaired in cycle 3.

## Evidence

- `CODE-RV1-2`
- `ev-code-rv1-2-3`
- `1wpif`

## Targets

- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
