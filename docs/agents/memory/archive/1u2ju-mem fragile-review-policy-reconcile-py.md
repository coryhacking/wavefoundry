# Fragile: review_policy_reconcile.py

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1u2ju-mem fragile-review-policy-reconcile-py`
Superseded by: `24c5k-mem review-policy-reconcile-py-fragile-seams`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-11-25
Source exploration cost: 3641306
Source event: `repeated-repairs:1tz6l:review_policy_reconcile.py`
Validation: promote
Validated by: agent
Action delta: When editing review_policy_reconcile.py, rerun ReviewPolicyReconcilerTests and the sentinel host-permission partition tests; refusals must keep the complete token worklist and replacement previews in one message
Validation rationale: Both 1tz6l repairs to this file concern refusal-output completeness (one-pass worklist with previews; live-docs scan with host-permission separation), and the tests that pin them are named in the reverification records. Evidence chain followed in events.jsonl; current file verified in tree with both repairs present.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Archived: 2026-11-25
Archive reason: Superseded by 24c5k-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1u2ju-mem fragile-review-policy-reconcile-py.md`

## Summary

review_policy_reconcile.py required 2 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `retired-carrier-preflight-hides-complete-recovery-worklist`
- `upgrade-reconciliation-misses-live-guidance-and-misroutes-host-rules`
- `1tz6l`

## Targets

- `review_policy_reconcile.py`
