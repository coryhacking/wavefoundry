# Decision: Defer the four `review_policy_reconcile.py` region strings…

Owner: Engineering
Status: rejected
Last verified: 2026-10-07

Memory ID: `1zyxk-mem decision-defer-the-four-review-policy-reconcile-py-region-st`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 68624
Source event: `decision-log:1zxnx-enh neutral-council-signoff-keys:7e8d3a0eb2de427b`
Validation: reject
Validated by: agent
Action delta: No durable action: the deferral is tracked as planned work in follow-up change 200xx.
Validation rationale: A time-bound deferral, not a lasting rule; the follow-up wave's change doc owns it.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Decision (wave 1zyb4): Defer the four `review_policy_reconcile.py` region strings to the retire-alias follow-up (coordinator decision).. Rationale: Editing them is a carrier change, which marks every open or readied target wave for re-Prepare at upgrade; the old key there stays valid because reads accept both and writes convert..

## Evidence

- `1zxnx-enh neutral-council-signoff-keys`
- `1zyb4`

## Targets

- `review_policy_reconcile.py`
