# Decision: The journal descriptor walk stays local to `upgrade_extensi…

Owner: Engineering
Status: rejected
Last verified: 2026-10-07

Memory ID: `1zz90-mem decision-the-journal-descriptor-walk-stays-local-to-upgrade-`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 63001
Source event: `decision-log:1zxns-bug change-id-and-path-containment:ce05ca2449d7cf73`
Validation: reject
Validated by: agent
Action delta: No durable action: the rationale was a scheduling constraint with a sibling wave, not a design rule.
Validation rationale: The reason given (wave A editing runtime_lock at the same time) is transient; nothing in the current tree requires the walk to stay local.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Decision (wave 1zxo0): The journal descriptor walk stays local to `upgrade_extensions.py`.. Rationale: Wave A is editing `runtime_lock.py`, and the upgrade extension runs pack-loaded..

## Evidence

- `1zxns-bug change-id-and-path-containment`
- `1zxo0`

## Targets

- `upgrade_extensions.py`
- `runtime_lock.py`
