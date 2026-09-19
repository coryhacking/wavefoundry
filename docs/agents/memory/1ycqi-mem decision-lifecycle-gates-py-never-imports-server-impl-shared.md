# Decision: `lifecycle_gates.py` never imports `server_impl`; shared he…

Owner: Engineering
Status: active
Last verified: 2026-09-18

Memory ID: `1ycqi-mem decision-lifecycle-gates-py-never-imports-server-impl-shared`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-18
Updated: 2026-09-18
Source exploration cost: 426027
Source event: `decision-log:1y044-ref extract-lifecycle-gate-units:24df42a6523c5763`
Validation: promote
Validated by: agent
Action delta: When extracting units out of server_impl, move the helpers they reach into a sibling support module and bind them as module attributes rather than from-imports, and keep the producers of any orchestrator-computed context data in that same support module, because a helper that calls back into server_impl makes the no-import rule unachievable.
Validation rationale: Evidence followed: the decision row in 1y044 and the landed modules. Current target verified: both new modules exist, and the architecture delivery lane confirmed by AST inventory that neither imports server_impl at any scope, that the gates module uses only attribute access with zero from-imports, and that the support module imports neither sibling. The round-4 correction the record captures is the load-bearing part: the receipt-diagnostics helper calls both policy producers, so leaving those producers in server_impl would have forced the forbidden import. techdocs_audit_lib.py exists and documents the same convention, so the cited precedent resolves.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
## Summary

Decision (wave 1y0h0): `lifecycle_gates.py` never imports `server_impl`; shared helpers move with the units into `lifecycle_gate_support.py`, and the orchestrator-computed policy data (`council_brief`, `policy_state`, `policy_state_errors`) arrives on the context as data, never as callables (round-2 correction of the earlier "passed as callables" wording). Round 4: the producers `_prepare_policy_state` and `_build_prepare_council_brief` move to the support module too, because `_review_policy_receipt_diagnostics` calls them; the orchestrator calls them through the support module. Rationale: Keeps the module importable and testable in isolation and hot-reload safe, following the `techdocs_audit_lib.py` rule; a data-only context is what AC-6 can enforce mechanically.

## Evidence

- `1y044-ref extract-lifecycle-gate-units`
- `1y0h0`

## Targets

- `lifecycle_gates.py`
- `lifecycle_gate_support.py`
- `techdocs_audit_lib.py`
