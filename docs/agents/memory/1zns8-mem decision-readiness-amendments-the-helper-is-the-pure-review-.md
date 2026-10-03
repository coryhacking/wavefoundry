# Decision: Readiness amendments: the helper is the pure `review_policy…

Owner: Engineering
Status: superseded
Last verified: 2026-10-03

Memory ID: `1zns8-mem decision-readiness-amendments-the-helper-is-the-pure-review-`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 132912
Source event: `decision-log:1zlu4-enh phase-scoped-project-review-lanes:d37071aa8c93cee2`
Validation: rewrite
Validated by: agent
Action delta: A new reader of required review lanes must call review_policy.project_lanes_for_phase with an explicit phase, not read the base roster.
Validation rationale: 1zlu1 readiness found multiple independent lane readers; without routing them through one phase-aware helper a readiness-only lane stayed required at Review and Close, and delivery review later found a duplicate implementation-phase reader that drove a false advisory.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zm66-mem review-lane-readers-route-through-one-phase-helper`

## Summary

Decision (wave 1zlu1): Readiness amendments: the helper is the pure `review_policy.project_lanes_for_phase(config, phase)` beside `normalize_phase_gates`, with a root-reading wrapper in `lifecycle_gate_support.py`; `required_review_status_keys` calls the pure helper so `review_policy_upgrade.py`'s `config_override` is honoured; AC-3 patches the pure helper; unifying the loaders changes `review_evidence`'s `str()` coercion of non-string entries to the gates' drop rule (B3); every `_extract_required_review_lanes` caller and the `review_evidence` regex parser are enumerated with the roster each reads and the census predicate widened to them, so a readiness-only lane does not stay required at Review and Close (B4); AC-4 adds the deleted-delivery-line case, and a non-list value raises a typed config error (no sentinel) that `_audit_harness_coverage` catches so `wf_audit` does not crash (N7, raise chosen at readiness because a sentinel can be mistaken for an empty roster, the fail-open this change removes); `review_policy_reconcile.py` carrier prose joins the docs census (N10); `docs/architecture/current-state.md` added to tasks and ACs (N11). Rationale: Readiness review findings, 2026-10-02. Operator decisions above are unchanged.

## Evidence

- `1zlu4-enh phase-scoped-project-review-lanes`
- `1zlu1`

## Targets

- `lifecycle_gate_support.py`
- `review_policy_upgrade.py`
- `review_policy_reconcile.py`
