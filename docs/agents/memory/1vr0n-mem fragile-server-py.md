# Fragile: server.py

Owner: Engineering
Status: rejected
Last verified: 2026-08-20

Memory ID: `1vr0n-mem fragile-server-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-08-20
Updated: 2026-08-20
Source exploration cost: 1613943
Source event: `repeated-repairs:1vt2q:server.py`
Validation: reject
Validated by: agent
Action delta: No new durable action: the two delivery repairs changed the public spec and canonical seed, not server.py; future reload work is already governed by the existing server-tools and reload-survivor memories.
Validation rationale: Verified the current target and both cited finding chains. ARCH-DEL-RETIRED-VOCAB-SCOPE-001 repaired docs/specs/mcp-tool-surface.md and DOCS-DEL-SEED160-RELOAD-CONTRACT-002 repaired seed 160. Treating those as two server.py repairs would create a false fragile-file history, while existing active memories already require exact state/mutation tests and fresh-process verification for reload-survivor changes.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

server.py required 2 separate repairs during wave 1vt2q; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `ARCH-DEL-RETIRED-VOCAB-SCOPE-001`
- `DOCS-DEL-SEED160-RELOAD-CONTRACT-002`
- `1vt2q`

## Targets

- `server.py`
