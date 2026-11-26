# review_policy_reconcile.py fragile seams

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24c5k-mem review-policy-reconcile-py-fragile-seams`
Kind: `fragile_file`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 3641306
Supersedes: `1u2ju-mem fragile-review-policy-reconcile-py`
Checked at: 2026-11-26T06:32:45Z
Check note: Policy reconciliation has several reasons and managed replacements. Review all matching refusals and the owner of each replacement. Reviewed .wavefoundry/framework/scripts/review_policy_reconcile.py:503.
Check flags: none

## Summary

When editing .wavefoundry/framework/scripts/review_policy_reconcile.py, check the two seams that broke in wave 1tz6l: one refusal must list every matching retired token, carrier line and recovery instruction before any mutation (finding retired-carrier-preflight-hides-complete-recovery-worklist), and reconciliation must surface every live match with replacement guidance from KNOWN_SECTION_REPLACEMENTS while host-local allow rules stay out of the reconciliation list (finding upgrade-reconciliation-misses-live-guidance-and-misroutes-host-rules). Test with a carrier holding more than one retired token.

## Evidence

- `1tz6l`
- `retired-carrier-preflight-hides-complete-recovery-worklist`
- `upgrade-reconciliation-misses-live-guidance-and-misroutes-host-rules`

## Targets

- `.wavefoundry/framework/scripts/review_policy_reconcile.py`
