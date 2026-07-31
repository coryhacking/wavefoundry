# Fragile: server_impl.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-28

Memory ID: `1tuxx-mem fragile-server-impl-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-28
Updated: 2026-07-28
Source exploration cost: 3365185
Source event: `repeated-repairs:1tsyx:server_impl.py`
Validation: rewrite
Validated by: agent
Action delta: When changing lifecycle gates in server_impl.py, enumerate every public lifecycle entry and verify declared-wave and legacy-wave behavior independently before trusting a green suite.
Validation rationale: Five 1tsyx repair chains touched distinct lifecycle decisions in server_impl.py; the durable risk is cross-surface gate drift, but the generated basename target was ambiguous.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1tuyw-mem lifecycle-gates-in-server-impl-py-require-a-public-entry-cen`
## Summary

server_impl.py required 5 separate repairs during wave 1tsyx; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `ac7-stale-readiness-fix-is-mock-shadowed`
- `legacy-prose-activation-branches-unpinned`
- `council-seat-alignment-degated-on-declared-waves-undocumented`
- `ac4a-ac6-and-ac7-coverage-claims-overstated`
- `agents-md-still-documents-retired-prepare-contract`
- `1tsyx`

## Targets

- `server_impl.py`
