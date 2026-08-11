# Repaired defect 1v0r0-f10-fallback-junction-traversal

Owner: Engineering
Status: rejected
Last verified: 2026-08-11

Memory ID: `1uzpx-mem repaired-defect-1v0r0-f10-fallback-junction-traversal`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-11
Updated: 2026-08-11
Source exploration cost: 4038148
Source event: `finding:1v0r0:1v0r0-f10-fallback-junction-traversal`
Validation: reject
Validated by: agent
Action delta: No separate action: active memory 1uz3q consolidates the no-follow fallback lesson against the actual implementation and owning tests.
Validation rationale: The F10 evidence was followed. The generated target probe_f9_f10.py is a transient/nonexistent probe rather than a current repository owner; the durable symlink/junction deletion lesson is now captured once in active memory 1uz3q with upgrade_wavefoundry.py and its tests as targets.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1v0r0: Junction traversal closed; independently reverified by a fresh security context with a scandir non-invocation spy

## Evidence

- `1v0r0-f10-fallback-junction-traversal`
- `ev-1v0r0-f10-fallback-junction-traversal-4`
- `1v0r0`

## Targets

- `probe_f9_f10.py`
