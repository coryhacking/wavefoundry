# Upgrade phase steps that can install must be stubbed module-wide in tests

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bc9-mem upgrade-phase-steps-that-can-install-must-be-stubbed-module-`
Kind: `failed_attempt`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 413440
Supersedes: `1zfii-mem repaired-defect-del-phase4-tests-reach-installer`

## Summary

When an upgrade phase gains a step that can install packages or touch the shared tool venv, stub its metadata read module-wide in .wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py (setUpModule, as it now patches setup_readiness._dependencies) and prove the stub with a control run on an empty WAVEFOUNDRY_TOOL_VENV. Why: in wave 1zfd9 the Phase 4 tests silently reached the real installer and the network: 0 installer calls with the stub, 16 without it on an empty tool venv (DEL-PHASE4-TESTS-REACH-INSTALLER, reverification ev-del-phase4-tests-reach-installer-3).

## Evidence

- `DEL-PHASE4-TESTS-REACH-INSTALLER`
- `ev-del-phase4-tests-reach-installer-3`
- `1zfd9`

## Targets

- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
