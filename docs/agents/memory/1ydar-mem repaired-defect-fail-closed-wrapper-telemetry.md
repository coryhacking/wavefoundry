# Repaired defect fail-closed-wrapper-telemetry

Owner: Engineering
Status: rejected
Last verified: 2026-09-17

Memory ID: `1ydar-mem repaired-defect-fail-closed-wrapper-telemetry`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-17
Updated: 2026-09-17
Source exploration cost: 578663
Source event: `finding:1y0gz:fail-closed-wrapper-telemetry`
Validation: reject
Validated by: agent
Action delta: No durable action from this record: its target is a reviewer scratch probe; the lesson (test structured refusals through the registered tool callables because wrapper telemetry re-resolves the wave) is pinned by test_record_layout_lifecycle.WrapperFailClosedTests and recorded in the 1y042 Progress Log
Validation rationale: The generated record targets probe_getchange.py, a session scratchpad artifact not present in the tree. The repair lives in server_impl._lifecycle_context_result and _record_tracking_context catching RecordLayoutInvalid and AmbiguousWaveId beside ValueError, pinned by WrapperFailClosedTests on the registered callables.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1y0gz: Repaired

## Evidence

- `fail-closed-wrapper-telemetry`
- `ev-fail-closed-wrapper-telemetry-3`
- `1y0gz`

## Targets

- `probe_getchange.py`
