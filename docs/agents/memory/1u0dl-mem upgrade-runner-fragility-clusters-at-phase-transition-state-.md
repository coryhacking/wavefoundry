# Upgrade runner fragility clusters at phase-transition state seams

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u0dl-mem upgrade-runner-fragility-clusters-at-phase-transition-state-`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 3641306
Source event: `repeated-repairs:1tz6l:upgrade_wavefoundry.py`
Validation: promote
Validated by: agent
Action delta: When editing upgrade_wavefoundry.py near a phase transition, rerun the seam test cluster together, not just the touched phase's tests
Validation rationale: The generated draft states only a repair count and a generic full-suite instruction. All six 1tz6l repairs share a reusable mechanism: they sit on phase-transition state seams, which is what the next editor needs to know. Evidence chain followed in events.jsonl (all six findings terminal with executed reverifications today); current file verified in tree with all six repairs present.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

upgrade_wavefoundry.py took 6 independent repairs in wave 1tz6l, and all six sit on phase-transition state: failed_phase attribution across the docs-gate/memory boundary, resume checkpoints (resume-after-gate must establish the memory checkpoint; resume-after-memory must accept retained phases), receipt/attempt-id handoff into Phase 4, dashboard lock authority at quiescence, retired-carrier preflight refusal completeness, and extraction filtering. Edits near any phase seam should rerun the seam cluster together: HistoricalMemoryUpgradeGateTests, ResumeAfterGateTests, DetectDashboardLivenessTests, ReviewPolicyReconcilerTests, ExtractFeatureMembersTests.

## Evidence

- `retired-carrier-preflight-hides-complete-recovery-worklist`
- `upgrade-renders-policy-gate-without-required-baselines`
- `memory-id-rename-and-gate-resume-deadlock`
- `memory-pause-masquerades-as-docs-failure`
- `upgrade-reconciliation-misses-live-guidance-and-misroutes-host-rules`
- `dashboard-quiescence-plan-contradicts-held-lock`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
