# Decision: Confirmed value against Waveforge's real fork, not just the…

Owner: Engineering
Status: rejected
Last verified: 2026-09-19

Memory ID: `1yex4-mem decision-confirmed-value-against-waveforge-s-real-fork-not-j`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-19
Updated: 2026-09-19
Source exploration cost: 384402
Source event: `decision-log:1y0be-ref tool-registry-and-wrapper-chain:153b7aea794714c9`
Validation: reject
Validated by: agent
Action delta: No durable action: this was a planning-time value assessment of shared function names with the Waveforge fork, recorded in docs/reports/waveforge-fork-audit.md.
Validation rationale: The candidate records a justification for doing the wave, not a rule that changes a future action, and part of it has already drifted (_read_workflow_config moved to lifecycle_gate_support.py in wave 1y0h0). The fork audit report is the canonical home.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1y0h1): Confirmed value against Waveforge's real fork, not just theory. Rationale: `register_mcp_surface`, `_ensure_no_extra_args`, `_load_script`, and `_read_workflow_config` are name-identical (2026-09-19: `_read_workflow_config` has since moved to `lifecycle_gate_support.py` with wave `1y0h0`, and `server_impl` imports it from there) (verified by AST function-name extraction, `docs/reports/waveforge-fork-audit.md`) across Wavefoundry's and Waveforge's independently-diverged `server_impl.py` files. This wave's improvements to those specific functions reach Waveforge automatically on their next merge, with zero rework on either side — the three `_wrap_*` wrappers and the individual `wf_*_response` lifecycle handlers are not shared, so this wave's benefit is concentrated exactly where the registry/middleware work lives.

## Evidence

- `1y0be-ref tool-registry-and-wrapper-chain`
- `1y0h1`

## Targets

- `lifecycle_gate_support.py`
- `server_impl.py`
