# Fragile: review_policy_reconcile.py

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u2ju-mem fragile-review-policy-reconcile-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 3641306
Source event: `repeated-repairs:1tz6l:review_policy_reconcile.py`
Validation: promote
Validated by: agent
Action delta: When editing review_policy_reconcile.py, rerun ReviewPolicyReconcilerTests and the sentinel host-permission partition tests; refusals must keep the complete token worklist and replacement previews in one message
Validation rationale: Both 1tz6l repairs to this file concern refusal-output completeness (one-pass worklist with previews; live-docs scan with host-permission separation), and the tests that pin them are named in the reverification records. Evidence chain followed in events.jsonl; current file verified in tree with both repairs present.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

review_policy_reconcile.py required 2 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `retired-carrier-preflight-hides-complete-recovery-worklist`
- `upgrade-reconciliation-misses-live-guidance-and-misroutes-host-rules`
- `1tz6l`

## Targets

- `review_policy_reconcile.py`
