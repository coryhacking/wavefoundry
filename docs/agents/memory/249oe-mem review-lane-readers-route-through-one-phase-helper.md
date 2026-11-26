# Review lane readers route through one phase helper

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249oe-mem review-lane-readers-route-through-one-phase-helper`
Kind: `decision`
Confidence: 0.8
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 132912
Supersedes: `1zm66-mem review-lane-readers-route-through-one-phase-helper`
Checked at: 2026-11-26T06:32:42Z
Check note: Delivery and Prepare derive their lanes by phase. Avoid parallel interpretation of project review settings in new callers. Reviewed .wavefoundry/framework/scripts/lifecycle_gate_support.py:1314.
Check flags: none

## Summary

When adding a reader of required project review lanes, call review_policy.project_lanes_for_phase(config, phase) in .wavefoundry/framework/scripts/review_policy.py with an explicit phase (or its root-reading wrapper _project_lanes_for_phase in lifecycle_gate_support.py), never the base roster or a local computation. Why: lanes are phase-scoped (phase_gates.prepare/close.required_lanes); 1zlu1 readiness found independent readers left a readiness-only lane required at Review and Close, and a duplicate implementation-phase reader produced a false required_review_lanes_empty advisory (DEL-1ZLU1-PARENT-SWAP-AND-OVERRIDE-COMPAT). A non-list config raises ProjectLanesConfigError rather than reading as empty.

## Evidence

- `1zlu4-enh phase-scoped-project-review-lanes`
- `DEL-1ZLU1-PARENT-SWAP-AND-OVERRIDE-COMPAT`
- `1zlu1`

## Targets

- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
