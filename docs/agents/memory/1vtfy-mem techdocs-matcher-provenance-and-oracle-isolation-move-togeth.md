# TechDocs matcher provenance and oracle isolation move together

Owner: Engineering
Status: active
Last verified: 2026-08-20

Memory ID: `1vtfy-mem techdocs-matcher-provenance-and-oracle-isolation-move-togeth`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-08-20
Updated: 2026-08-20
Source exploration cost: 3060087
Source event: `finding:1vry5:ARCH-DEL-1`
Validation: promote
Validated by: agent
Action delta: After any TechDocs matcher edit, refresh the load-bearing cost comment and retained module hash last, and verify the pinned MkDocs/pathspec oracle remains test-only, excluded from packages, and absent from runtime imports.
Validation rationale: ARCH-DEL-1 showed that correct matcher code can still ship with a stale source carrier and stale retained-artifact provenance. Current targets confirm the corrected historical/delivered wording, exact module hash binding, source-only oracle placement, and scripts/tests package exclusion. The generated candidate was truncated and omitted the oracle/testing-architecture target, so a rewrite is more durable and actionable.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

A matcher repair is incomplete if its load-bearing cost comment or retained module hash still describes pre-repair bytes, or if the pinned MkDocs/pathspec oracle leaks into runtime/package dependencies. Refresh provenance after the final matcher edit and verify the oracle stays under excluded tests.

## Evidence

- `ARCH-DEL-1`
- `ev-arch-del-1-3`
- `1vry5`

## Targets

- `.wavefoundry/framework/scripts/techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `docs/architecture/testing-architecture.md`
