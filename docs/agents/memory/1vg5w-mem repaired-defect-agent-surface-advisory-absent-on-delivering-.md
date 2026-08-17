# Repaired defect agent-surface-advisory-absent-on-delivering-upgrade

Owner: Engineering
Status: rejected
Last verified: 2026-08-16

Memory ID: `1vg5w-mem repaired-defect-agent-surface-advisory-absent-on-delivering-`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-16
Updated: 2026-08-16
Source exploration cost: 256624
Source event: `finding:1vgep:agent-surface-advisory-absent-on-delivering-upgrade`
Validation: reject
Validated by: agent
Action delta: No separate durable action: this finding's premise was false and its lesson (cleanup and the operator summary run from the extracted runner; do not hook them for the delivering upgrade) is already carried by 1vjt5-mem, which cites this finding as evidence.
Validation rationale: The candidate summarizes a finding whose premise (pre-upgrade runner prints the summary) was falsified by execution; its only durable content is the corrected mechanism, which 1vjt5-mem states with the falsification method and cites this finding id. A second record would duplicate it and its target list points at a scratch probe path that does not exist in the repo.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1vgep: The delivering upgrade does report the advisory (verified by execution), so the finding's requirement is met; the redundant hook is handled as its own finding so the ledger records both the false premise and its correction.

## Evidence

- `agent-surface-advisory-absent-on-delivering-upgrade`
- `ev-agent-surface-advisory-absent-on-delivering-upgr-3`
- `1vgep`

## Targets

- `reverify-1vgep-code/probe_dup.py`
- `upgrade_wavefoundry.py`
