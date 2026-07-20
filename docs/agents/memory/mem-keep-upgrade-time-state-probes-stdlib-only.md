# Keep upgrade-time state probes stdlib-only

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-keep-upgrade-time-state-probes-stdlib-only`
Kind: `dependency_gotcha`
Confidence: 0.95
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1rvfx-bug upgrade-graph-version-transition-log:6cbe53f749f757c2`
Validation: promote
Validated by: agent
Action delta: Use a small local stdlib probe when upgrade logic must inspect pre-extraction state; do not import replaceable or heavy framework modules.
Validation rationale: Upgrade executes across a framework replacement boundary, and the current implementation explicitly preserves an import-light, fail-safe probe for that reason.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When upgrade logic reads pre-extraction state, use a small stdlib-only local probe instead of importing framework modules that may be heavy or replaced during extraction; keep non-authoritative version probes fail-safe.

## Evidence

- `1rvfx-bug upgrade-graph-version-transition-log`
- `1rvfy`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py:642`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py:3056`

## Targets

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
