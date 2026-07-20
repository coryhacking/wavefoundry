# Dependency presence does not prove version compatibility

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-dependency-presence-does-not-prove-version-compatibility`
Kind: `dependency_gotcha`
Confidence: 0.95
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1p95u-enh version-aware-dependency-sync:623f3716a49f605a`
Validation: promote
Validated by: agent
Action delta: Evaluate dependency specifier satisfaction, not importability alone, whenever setup or upgrade dependency logic changes.
Validation rationale: The central setup probe still carries both install and upgrade, and a presence-only check would strand existing projects on incompatible versions.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When changing setup or upgrade dependencies, treat a package as missing when its installed version violates the declared specifier, not only when its import fails; keep the check in the shared setup dependency path so fresh installs and upgrades converge.

## Evidence

- `1p95u-enh version-aware-dependency-sync`
- `1p93a`
- `.wavefoundry/framework/scripts/setup_index.py:275`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py:46`

## Targets

- `.wavefoundry/framework/scripts/setup_index.py`
