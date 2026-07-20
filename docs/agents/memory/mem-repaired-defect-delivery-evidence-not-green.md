# Repaired defect delivery-evidence-not-green

Owner: Engineering
Status: superseded
Last verified: 2026-07-19

Memory ID: `mem-repaired-defect-delivery-evidence-not-green`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-19
Updated: 2026-07-19
Source exploration cost: 1764640
Source event: `finding:1sxj7:delivery-evidence-not-green`
Validation: rewrite
Validated by: agent
Action delta: Do not record delivery verification as green while the canonical isolated-per-file suite has any failure; preserve the failure and rerun the authoritative command after focused diagnosis.
Validation rationale: The recorded delivery line overstated a canonical run containing one failure. The current authoritative rerun is 5,873/5,873 green, making the evidence rule concrete and current.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `mem-canonical-suite-status-governs-delivery-evidence`
## Summary

Real defect fixed in wave 1sxj7: Independent QA verified the repaired behavior with executable evidence.

## Evidence

- `delivery-evidence-not-green`
- `ev-delivery-evidence-not-green-3`
- `1sxj7`

## Targets

- `.wavefoundry/framework/scripts/run_tests.py`
