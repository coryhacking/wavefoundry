# Validate setup readiness against canonical producers

Owner: Engineering
Status: active
Last verified: 2026-11-26

Memory ID: `1y5tz-mem validate-setup-readiness-against-canonical-producers`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-09-15
Updated: 2026-11-26
Source exploration cost: 1110645
Source event: `finding:1y3og:SETUP-SURFACE-001`
Validation: promote
Validated by: agent
Action delta: Test readiness consumers with actual renderer output and actual setup parser continuations before accepting a ready/recovery contract.
Validation rationale: Verified linked typed finding and final observer/tests. Generated summary is generic and CLI target indirect; replace with demonstrated producer/consumer lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Checked at: 2026-11-26T06:32:40Z
Check note: The setup readiness suite drives canonical options through continuation. Matching only argument-parser fixtures misses supported launchers. Reviewed .wavefoundry/framework/scripts/tests/test_setup_readiness.py:750.
Check flags: none

## Summary

A separate readiness grammar rejected all five canonical MCP renderer entries and supported setup continuation flags. Share setup_requirements.parse_args with the producer; test actual renderers twice for convergence, including Junie config-relative paths and Cursor cwd. Handcrafted consumer fixtures alone missed these contract mismatches.

## Evidence

- `1y3og`
- `SETUP-SURFACE-001`
- `SETUP-ARGS-003`

## Targets

- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/setup_requirements.py`
- `.wavefoundry/framework/scripts/tests/test_setup_readiness.py`
