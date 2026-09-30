# Fragile: server.py

Owner: Engineering
Status: rejected
Last verified: 2026-09-29

Memory ID: `1zclj-mem fragile-server-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 771446
Source event: `repeated-repairs:1zfd9:server.py`
Validation: reject
Validated by: agent
Action delta: None; no action follows from this candidate.
Validation rationale: Misattributed: DEL-LOCK-PATH-ADVISORIES was repaired in setup_index.py (lock path resolution and OSError handling), not server.py; DEL-STARTUP-ENTRY-UNTESTED added tests and one publish-order fix. Two unrelated repairs do not make server.py fragile.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

server.py required 2 separate repairs during wave 1zfd9; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `DEL-STARTUP-ENTRY-UNTESTED`
- `DEL-LOCK-PATH-ADVISORIES`
- `1zfd9`

## Targets

- `server.py`
