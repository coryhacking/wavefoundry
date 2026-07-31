# Fragile: upgrade_wavefoundry.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-31

Memory ID: `1u1hw-mem fragile-upgrade-wavefoundry-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 3641306
Source event: `repeated-repairs:1tz6l:upgrade_wavefoundry.py`
Validation: rewrite
Validated by: agent
Action delta: When editing upgrade_wavefoundry.py near a phase transition, rerun the seam test cluster together, not just the touched phase's tests
Validation rationale: The generated draft states only a repair count and a generic full-suite instruction. All six 1tz6l repairs share a reusable mechanism: they sit on phase-transition state seams, which is what the next editor needs to know. Evidence chain followed in events.jsonl (all six findings terminal with executed reverifications today); current file verified in tree with all six repairs present.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1u0dl-mem upgrade-runner-fragility-clusters-at-phase-transition-state-`
## Summary

upgrade_wavefoundry.py required 6 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `retired-carrier-preflight-hides-complete-recovery-worklist`
- `upgrade-renders-policy-gate-without-required-baselines`
- `memory-id-rename-and-gate-resume-deadlock`
- `memory-pause-masquerades-as-docs-failure`
- `upgrade-reconciliation-misses-live-guidance-and-misroutes-host-rules`
- `dashboard-quiescence-plan-contradicts-held-lock`
- `1tz6l`

## Targets

- `upgrade_wavefoundry.py`
