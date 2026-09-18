# Fragile: reverify4-docs/probe_public.py

Owner: Engineering
Status: rejected
Last verified: 2026-09-17

Memory ID: `1yaxm-mem fragile-reverify4-docs-probe-public-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-17
Updated: 2026-09-17
Source exploration cost: 578663
Source event: `repeated-repairs:1y0gz:reverify4-docs/probe_public.py`
Validation: reject
Validated by: agent
Action delta: No durable action: the target is a reviewer's scratch probe outside the repository
Validation rationale: reverify4-docs/probe_public.py is a session scratchpad artifact used by the cycle-4 docs-contract lane; it is not in the repository, and the linked findings were repaired in server_impl.py and commit_provenance.py.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

reverify4-docs/probe_public.py required 2 separate repairs during wave 1y0gz; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `wave-current-resource-serves-one-twin`
- `commit-provenance-nested-wave-dir`
- `1y0gz`

## Targets

- `reverify4-docs/probe_public.py`
