# Canonical suite status governs delivery evidence

Owner: Engineering
Status: archived
Last verified: 2026-11-22

Memory ID: `1t0q0-mem canonical-suite-status-governs-delivery-evidence`
Superseded by: `24cfc-mem canonical-suite-status-governs-delivery-evidence`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-07-19
Updated: 2026-11-25
Source event: `finding:1sxj7:delivery-evidence-not-green`
Validation: promote
Validated by: agent
Action delta: Do not record delivery verification as green while the canonical isolated-per-file suite has any failure; preserve the failure and rerun the authoritative command after focused diagnosis.
Validation rationale: The recorded delivery line overstated a canonical run containing one failure. The current authoritative rerun is 5,873/5,873 green, making the evidence rule concrete and current.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Archived: 2026-11-25
Archive reason: Superseded by 24cfc-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1t0q0-mem canonical-suite-status-governs-delivery-evidence.md`

## Summary

Record delivery verification as green only when the canonical isolated-per-file runner completes with zero failures. An isolated pass can diagnose a load-sensitive failure, but it does not erase the failed canonical run; rerun the authoritative command and report both states honestly.

## Evidence

- `1sxj7`
- `delivery-evidence-not-green`
- `ev-delivery-evidence-not-green-3`
- `python3 .wavefoundry/framework/scripts/run_tests.py`

## Targets

- `.wavefoundry/framework/scripts/run_tests.py`
- `docs/waves/`
