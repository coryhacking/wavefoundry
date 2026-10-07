# Decision: Coordinator: move `parse_readme` and `offline_problems` int…

Owner: Engineering
Status: active
Last verified: 2026-10-07

Memory ID: `2016a-mem decision-coordinator-move-parse-readme-and-offline-problems-`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 97308
Source event: `decision-log:1zxnt-maint correctness-and-test-hygiene-round:57de01b21a7c6e30`
Validation: promote
Validated by: agent
Action delta: Offline vendored-script checks belong in the shipped vendored_integrity module; the network verifier stays source-repo only and imports it.
Validation rationale: vendored_integrity.py ships (build_pack keeps it), verify_vendored_scripts is excluded and re-exports; wf_audit uses the shipped module.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Decision (wave 1zyb2): Coordinator: move `parse_readme` and `offline_problems` into a shipped `vendored_integrity.py`; the network check stays in the excluded script, which imports the shipped module. `wf_audit` uses the shipped module, uncached.. Rationale: The requester is a distribution; `unavailable` everywhere would defeat the finding. Hashing 1.7 MB costs milliseconds..

## Evidence

- `1zxnt-maint correctness-and-test-hygiene-round`
- `1zyb2`

## Targets

- `vendored_integrity.py`
