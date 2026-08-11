# Repaired defect 1v0r0-f9-fallback-toctou-top-symlink-follow

Owner: Engineering
Status: rejected
Last verified: 2026-08-11

Memory ID: `1v111-mem repaired-defect-1v0r0-f9-fallback-toctou-top-symlink-follow`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-11
Updated: 2026-08-11
Source exploration cost: 4038148
Source event: `finding:1v0r0:1v0r0-f9-fallback-toctou-top-symlink-follow`
Validation: reject
Validated by: agent
Action delta: No separate action: active memory 1uz3q consolidates the no-follow fallback lesson against the actual implementation and owning tests.
Validation rationale: The F9 evidence was followed. The generated target reverify_probe.py is a transient/nonexistent probe rather than a current repository owner; the durable symlink/junction deletion lesson is now captured once in active memory 1uz3q with upgrade_wavefoundry.py and its tests as targets.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1v0r0: The F9 defect is closed; independently reverified by a fresh red-team context; both blocking lanes (red-team, security) now concur

## Evidence

- `1v0r0-f9-fallback-toctou-top-symlink-follow`
- `ev-1v0r0-f9-fallback-toctou-top-symlink-follow-4`
- `1v0r0`

## Targets

- `reverify_probe.py`
