# Decision: Accept two residuals: the pre-policy-wave seam (server_impl…

Owner: Engineering
Status: superseded
Last verified: 2026-08-04

Memory ID: `1ud35-mem decision-accept-two-residuals-the-pre-policy-wave-seam-serve`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-04
Updated: 2026-08-04
Source exploration cost: 784014
Source event: `decision-log:1uf69-bug noop-policy-migration-invalidates-readied-waves:ef4b568a2e7864c4`
Validation: rewrite
Validated by: agent
Action delta: When a wave folder is imported from outside the project (copied, restored, or authored by a pre-receipt framework version), run wf_prepare_wave(mode='ready') on it: no upgrade and no lifecycle gate will invalidate its stale review policy, because the receipt-recomputation helper returns early when a declared wave has neither a receipt nor a re-prepare marker.
Validation rationale: The generated draft is a verbatim Decision Log dump carrying wave narrative and both residuals at once. The durable, reusable half is the detection hole: server_impl.py's receipt-recomputation helper short-circuits for declared waves with no receipt and no marker, so nothing automatic ever catches their stale policy and the operator sees no diagnostic. Rewritten to state that mechanism and its one operational remedy; the block-prose residual is wave-local and dropped.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1uejb-mem imported-waves-need-a-manual-re-ready-no-gate-invalidates-a-`
## Summary

Decision (wave 1uf65): Accept two residuals: the pre-policy-wave seam (server_impl.py:6965) and the block-prose replay asymmetry. Rationale: For receipt-BEARING waves, receipt/evaluator recomputation at each lifecycle gate is the surviving invalidation mechanism. It is NOT for the narrow population residual (a) names: `server_impl.py:6962-6968` returns early exactly when the receipt is None and no marker is present, so a declared wave imported from outside the project gets no automatic invalidation and no diagnostic, and detection is voluntary. Operational note: run `wf_prepare_wave(mode='ready')` on any wave folder imported from outside the project. Block prose is agent guidance, not wave review semantics.

## Evidence

- `1uf69-bug noop-policy-migration-invalidates-readied-waves`
- `1uf65`

## Targets

- `server_impl.py`
