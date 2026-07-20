# Decision: Make `_missing_in_venv` version-aware rather than wire a se…

Owner: Engineering
Status: superseded
Last verified: 2026-07-20

Memory ID: `mem-decision-make-missing-in-venv-version-aware-rather-than-wire`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p95u-enh version-aware-dependency-sync:623f3716a49f605a`
Validation: rewrite
Validated by: agent
Action delta: Evaluate dependency specifier satisfaction, not importability alone, whenever setup or upgrade dependency logic changes.
Validation rationale: The central setup probe still carries both install and upgrade, and a presence-only check would strand existing projects on incompatible versions.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-dependency-presence-does-not-prove-version-compatibility`
## Summary

Decision (wave 1p93a): Make `_missing_in_venv` version-aware rather than wire a separate `wf setup`/dep-install step into `wf_upgrade`.. Rationale: The upgrade already calls `ensure_deps` via phase-4 `setup_index.main`; a version-aware check propagates everywhere (setup + upgrade + auto-install) with zero new wiring..

## Evidence

- `1p95u-enh version-aware-dependency-sync`
- `1p93a`

## Targets

- `upgrade_wavefoundry.py`
