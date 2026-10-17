# Upgrade runner fragility clusters at phase-transition state seams

Owner: Engineering
Status: archived
Last verified: 2026-10-16

Memory ID: `1u0dl-mem upgrade-runner-fragility-clusters-at-phase-transition-state-`
Superseded by: `1u8q3-mem upgrade-runner-phase-playbook`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-07-31
Updated: 2026-08-02
Source exploration cost: 3641306
Source event: `repeated-repairs:1tz6l:upgrade_wavefoundry.py`
Validation: promote
Validated by: agent
Action delta: When editing upgrade_wavefoundry.py near a phase transition, rerun the seam test cluster together, not just the touched phase's tests
Validation rationale: The generated draft states only a repair count and a generic full-suite instruction. All six 1tz6l repairs share a reusable mechanism: they sit on phase-transition state seams, which is what the next editor needs to know. Evidence chain followed in events.jsonl (all six findings terminal with executed reverifications today); current file verified in tree with all six repairs present.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

Archived: 2026-08-02
Archive reason: Superseded by a verified consolidated file playbook after retention review.
Archive path: `docs/agents/memory/archive/1u0dl-mem upgrade-runner-fragility-clusters-at-phase-transition-state-.md`
## Summary

Legacy recovery: this archived 1tz6l evidence describes retired phases and tests, not current instructions: upgrade_wavefoundry.py took 6 independent repairs involving failed_phase attribution across the docs-gate/memory boundary, resume checkpoints (resume-after-gate establishing the memory checkpoint; resume-after-memory accepting retained phases), receipt/attempt-id handoff into Phase 4, dashboard lock authority at quiescence, retired-carrier preflight refusal completeness, and extraction filtering; the original seam cluster was HistoricalMemoryUpgradeGateTests, ResumeAfterGateTests, DetectDashboardLivenessTests, ReviewPolicyReconcilerTests, ExtractFeatureMembersTests.

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
