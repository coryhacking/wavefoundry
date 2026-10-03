# Review lane readers route through one phase helper

Owner: Engineering
Status: active
Last verified: 2026-10-03

Memory ID: `1zm66-mem review-lane-readers-route-through-one-phase-helper`
Kind: `decision`
Confidence: 0.8
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 132912
Source event: `decision-log:1zlu4-enh phase-scoped-project-review-lanes:d37071aa8c93cee2`
Validation: promote
Validated by: agent
Action delta: A new reader of required review lanes must call review_policy.project_lanes_for_phase with an explicit phase, not read the base roster.
Validation rationale: 1zlu1 readiness found multiple independent lane readers; without routing them through one phase-aware helper a readiness-only lane stayed required at Review and Close, and delivery review later found a duplicate implementation-phase reader that drove a false advisory.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Project review lanes are phase-scoped (phase_gates.prepare/close.required_lanes). Every reader goes through review_policy.project_lanes_for_phase(config, phase) (pure; honours config_override) or its root-reading wrapper in lifecycle_gate_support; a non-list config raises ProjectLanesConfigError rather than reading as empty. Implementation-phase review reads the shared delivery roster; a second local roster computation produced a false required_review_lanes_empty advisory.

## Evidence

- `1zlu4-enh phase-scoped-project-review-lanes`
- `DEL-1ZLU1-PARENT-SWAP-AND-OVERRIDE-COMPAT`
- `1zlu1`

## Targets

- `review_policy.py`
- `lifecycle_gate_support.py`
- `review_evidence.py`
- `wf_server/server_impl.py`
