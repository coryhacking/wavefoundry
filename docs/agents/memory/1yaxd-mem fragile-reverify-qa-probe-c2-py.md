# Fragile: reverify-qa/probe_c2.py

Owner: Engineering
Status: rejected
Last verified: 2026-09-17

Memory ID: `1yaxd-mem fragile-reverify-qa-probe-c2-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-17
Updated: 2026-09-17
Source exploration cost: 578663
Source event: `repeated-repairs:1y0gz:reverify-qa/probe_c2.py`
Validation: reject
Validated by: agent
Action delta: No durable action: the target is a reviewer's scratch probe outside the repository, not a framework file
Validation rationale: reverify-qa/probe_c2.py is a session scratchpad artifact under /private/tmp used by a review lane; it is not part of the repository and the two findings it is linked to were repaired in server_impl.py, not in the probe. A fragile-file record pointing at it would be unresolvable.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

reverify-qa/probe_c2.py required 2 separate repairs during wave 1y0gz; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `warm-cache-layout-flip`
- `ambiguous-id-not-universal`
- `1y0gz`

## Targets

- `reverify-qa/probe_c2.py`
