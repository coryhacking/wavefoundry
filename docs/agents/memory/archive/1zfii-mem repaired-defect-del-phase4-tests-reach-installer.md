# Repaired defect DEL-PHASE4-TESTS-REACH-INSTALLER

Owner: Engineering
Status: archived
Last verified: 2026-09-29

Memory ID: `1zfii-mem repaired-defect-del-phase4-tests-reach-installer`
Superseded by: `24bc9-mem upgrade-phase-steps-that-can-install-must-be-stubbed-module-`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-29
Updated: 2026-11-25
Source exploration cost: 413440
Source event: `finding:1zfd9:DEL-PHASE4-TESTS-REACH-INSTALLER`
Validation: promote
Validated by: agent
Action delta: When an upgrade phase gains a step that can install packages or touch the shared tool venv, stub its metadata read module-wide in test_upgrade_wavefoundry.py (setUpModule) and prove it with a control run on an empty WAVEFOUNDRY_TOOL_VENV; otherwise Phase 4 tests silently reach the real installer and the network.
Validation rationale: Verified in 1zfd9: with the stub 0 installer calls, without it 16 on an empty tool venv (reverification ev-del-phase4-tests-reach-installer-3).
Evidence verified: true
Current target verified: true
Canonical overlap: none
Archived: 2026-11-25
Archive reason: Superseded by 24bc9-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1zfii-mem repaired-defect-del-phase4-tests-reach-installer.md`

## Summary

Real defect fixed in wave 1zfd9: Resolved

## Evidence

- `DEL-PHASE4-TESTS-REACH-INSTALLER`
- `ev-del-phase4-tests-reach-installer-3`
- `1zfd9`

## Targets

- `tests/test_upgrade_wavefoundry.py`
