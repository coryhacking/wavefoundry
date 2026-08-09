# Decision: Readiness correction: do NOT derive the exclusion from the…

Owner: Engineering
Status: superseded
Last verified: 2026-08-07

Memory ID: `1uosp-mem decision-readiness-correction-do-not-derive-the-exclusion-fr`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-07
Updated: 2026-08-07
Source exploration cost: 51887
Source event: `decision-log:1ulr2-bug upgrade-preflight-blocks-on-state-it-owns:78de10052171b26d`
Validation: rewrite
Validated by: agent
Action delta: Before designing a fix that runs during upgrade in a target repo, check whether the module it would depend on actually ships there.
Validation rationale: The drafted candidate records one wave's specific rejection and would not change behavior on a future design. The durable lesson is the check that produced it: an upgrade-time component runs inside the target repository, so it can only import what the pack ships, and `build_pack.py` does not ship. Readiness caught this only because the plan's hardest requirement was tested rather than read. Verified against the current tree: `build_pack.py` is absent from the 1.15.4 zip while `review_policy.py`, `review_policy_reconcile.py`, and `upgrade_wavefoundry.py` are present in both the feature pack and the nested bridge.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1umf9-mem upgrade-time-code-can-only-depend-on-what-the-pack-ships`
## Summary

Decision (wave 1uoq0): Readiness correction: do NOT derive the exclusion from the pack's shipped set. Rationale: The original plan required this and it is not achievable. `build_pack.py` does not ship to target repos (verified absent from the 1.15.4 zip), and `review_policy_reconcile.py` runs at upgrade time inside a target repo, so it cannot import the shipped set. The set is also hardcoded as two local variables rather than a shared constant, and a runtime validator depending on a build tool inverts the layering.

## Evidence

- `1ulr2-bug upgrade-preflight-blocks-on-state-it-owns`
- `1uoq0`

## Targets

- `build_pack.py`
- `review_policy_reconcile.py`
