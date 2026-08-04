# Imported waves need a manual re-ready; no gate invalidates a receiptless declared wave

Owner: Engineering
Status: active
Last verified: 2026-08-04

Memory ID: `1uejb-mem imported-waves-need-a-manual-re-ready-no-gate-invalidates-a-`
Kind: `decision`
Confidence: 0.9
Created: 2026-08-04
Updated: 2026-08-04
Source exploration cost: 784014
Source event: `decision-log:1uf69-bug noop-policy-migration-invalidates-readied-waves:ef4b568a2e7864c4`
Validation: promote
Validated by: agent
Action delta: When a wave folder is imported from outside the project (copied, restored, or authored by a pre-receipt framework version), run wf_prepare_wave(mode='ready') on it: no upgrade and no lifecycle gate will invalidate its stale review policy, because the receipt-recomputation helper returns early when a declared wave has neither a receipt nor a re-prepare marker.
Validation rationale: The generated draft is a verbatim Decision Log dump carrying wave narrative and both residuals at once. The durable, reusable half is the detection hole: server_impl.py's receipt-recomputation helper short-circuits for declared waves with no receipt and no marker, so nothing automatic ever catches their stale policy and the operator sees no diagnostic. Rewritten to state that mechanism and its one operational remedy; the block-prose residual is wave-local and dropped.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

`_review_policy_receipt_diagnostics` in server_impl.py returns early (no diagnostics at all) when a declared wave has no current policy receipt AND no re-prepare marker, leaving it on historical authority. Before wave 1uf69 the upgrade's unconditional wave sweep incidentally repaired that state every run; since the no-op guard landed, a no-op upgrade no longer does. Consequence: a declared wave imported from another repo, restored from a branch or backup, or authored before the receipt evaluator existed runs its lifecycle on a stale persisted lane roster with no automatic invalidation and no visible diagnostic. Detection is voluntary, and the remedy is the same action either way: wf_prepare_wave(mode='ready'), which mints a current receipt.

## Evidence

- `1uf69-bug noop-policy-migration-invalidates-readied-waves`
- `1uf65`
- `server_impl.py:6962-6968 early return`
- `review_policy_upgrade.py:81 no-op guard`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/review_policy_upgrade.py`
