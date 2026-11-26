# Canonical suite status governs delivery evidence

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24cfc-mem canonical-suite-status-governs-delivery-evidence`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Supersedes: `1t0q0-mem canonical-suite-status-governs-delivery-evidence`
Checked at: 2026-11-26T06:32:45Z
Check note: A focused pass cannot replace a failed canonical receipt. The final-tree qualification in wave 24a51 exercised this distinction again. Reviewed .wavefoundry/framework/scripts/run_tests.py:16.
Check flags: none

## Summary

When recording delivery verification in a wave record, call it green only if the canonical runner (python3 .wavefoundry/framework/scripts/run_tests.py) completed with zero failures. An isolated per-file pass can diagnose a load-sensitive failure but does not erase the failed canonical run: keep the failure in the record, rerun the authoritative command, and report both states. Wave 1sxj7 recorded a green delivery line over a canonical run with one failure (finding delivery-evidence-not-green).

## Evidence

- `1sxj7`
- `delivery-evidence-not-green`
- `ev-delivery-evidence-not-green-3`
- `python3 .wavefoundry/framework/scripts/run_tests.py`

## Targets

- `.wavefoundry/framework/scripts/run_tests.py`
