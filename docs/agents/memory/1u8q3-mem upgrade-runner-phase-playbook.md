# Upgrade runner phase-transition playbook

Owner: Engineering
Status: active
Last verified: 2026-08-02

Memory ID: `1u8q3-mem upgrade-runner-phase-playbook`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-08-02
Updated: 2026-08-02

## Summary

When editing upgrade_wavefoundry.py, treat phase-transition state and the old-code window as one review unit: exercise the seam test cluster across docs, memory, resume, cleanup, and summary/consent handoff; behavior that must ship on its installing upgrade must run from a fresh-process phase, with required state carried through the upgrade lock rather than a module global.

## Evidence

- `1u0dl-mem`
- `1u551-mem`

## Targets

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
