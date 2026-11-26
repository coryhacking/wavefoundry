# Prepare an imported open wave that has no review-policy receipt

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24f1q-mem prepare-an-imported-open-wave-that-has-no-review-policy-rece`
Kind: `decision`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 784014
Action delta: When importing or restoring an in-flight declared wave, inspect its receipt. If it has neither a receipt nor a re-Prepare marker, run wf_prepare_wave in ready mode before relying on the lane roster.
Validation rationale: Checked the early return in lifecycle_gate_support and the no-op guard in review_policy_upgrade.
Supersedes: `1uejb-mem imported-waves-need-a-manual-re-ready-no-gate-invalidates-a-`

## Summary

An open typed wave without a policy receipt or re-Prepare marker can retain historical review authority. The decision lives in lifecycle_gate_support._review_policy_receipt_diagnostics. A no-op policy migration does not mark the wave for re-Prepare.

## Evidence

- `docs/waves/1uf65 integrity-checks-guidance/1uf69-bug noop-policy-migration-invalidates-readied-waves.md`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/review_policy_upgrade.py`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/review_policy_upgrade.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
