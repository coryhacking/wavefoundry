# Fragile: upgrade_wavefoundry.py

Owner: Engineering
Status: rejected
Last verified: 2026-08-11

Memory ID: `1v09g-mem fragile-upgrade-wavefoundry-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-08-11
Updated: 2026-08-11
Source exploration cost: 4038148
Source event: `repeated-repairs:1v0r0:upgrade_wavefoundry.py`
Validation: reject
Validated by: agent
Action delta: No new action: the active upgrade-runner phase-transition playbook already requires seam-focused verification for this fragile file.
Validation rationale: The F1/F2 evidence was followed and the current upgrade cleanup implementation/tests were checked. This generated record merely says to run the full suite after two repairs, while active memory 1u8q3 already gives the more specific durable action for upgrade_wavefoundry.py and its phase/state seams.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

upgrade_wavefoundry.py required 2 separate repairs during wave 1v0r0; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `1v0r0-f1-windows-cleanup-wedge`
- `1v0r0-f2-cleanup-retry-clears-failure-without-success`
- `1v0r0`

## Targets

- `upgrade_wavefoundry.py`
