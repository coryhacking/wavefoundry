# Decision: Upgrade cleanup in `upgrade_wavefoundry.py` (code); install…

Owner: Engineering
Status: rejected
Last verified: 2026-07-20

Memory ID: `mem-decision-upgrade-cleanup-in-upgrade-wavefoundry-py-code-inst`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1rxyi-bug cleanup-root-install-bootstrap-file:363bb11eca1ec0bc`
Validation: reject
Validated by: agent
Action delta: None; use the current scripted upgrade path and rendered install instructions as the authorities for lifecycle placement.
Validation rationale: The old code-versus-seed placement decision is fully embodied in current lifecycle surfaces and adds no independent next-action guidance.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1rycd): Upgrade cleanup in `upgrade_wavefoundry.py` (code); install cleanup as a seed-012 step.. Rationale: Upgrade has a mechanical script (MCP `wf_upgrade` + `wf upgrade` CLI both run it) so code makes it automatic; install is agent-driven with no finalizing script, so a seed step is the right home..

## Evidence

- `1rxyi-bug cleanup-root-install-bootstrap-file`
- `1rycd`

## Targets

- `upgrade_wavefoundry.py`
