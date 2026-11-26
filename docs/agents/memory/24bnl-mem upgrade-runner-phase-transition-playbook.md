# Upgrade runner phase-transition playbook

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bnl-mem upgrade-runner-phase-transition-playbook`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1u8q3-mem upgrade-runner-phase-playbook`

## Summary

When editing .wavefoundry/framework/scripts/upgrade_wavefoundry.py, review phase-transition state and the old-code window as one unit: exercise the seam test cluster across docs, memory, resume, cleanup and summary/consent handoff, run any behavior that must take effect on its installing upgrade from a fresh-process phase or a new-pack hook the old parent already calls, and carry required state through .wavefoundry/upgrade-in-progress.json rather than a module global. The installing upgrade runs the OLD parent runner, so parent-only code does not run until the next upgrade (old-parent hook calls at upgrade_wavefoundry.py _run_hook('pre_index_update'); tests/test_old_parent_publication.py).

## Evidence

- `1u0dl-mem upgrade-runner-fragility-clusters-at-phase-transition-state-`
- `1u551-mem`
- `.wavefoundry/framework/scripts/tests/test_old_parent_publication.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`

## Targets

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
