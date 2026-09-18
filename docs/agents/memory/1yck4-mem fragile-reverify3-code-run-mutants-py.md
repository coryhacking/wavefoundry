# Fragile: reverify3-code/run_mutants.py

Owner: Engineering
Status: rejected
Last verified: 2026-09-17

Memory ID: `1yck4-mem fragile-reverify3-code-run-mutants-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-17
Updated: 2026-09-17
Source exploration cost: 578663
Source event: `repeated-repairs:1y0gz:reverify3-code/run_mutants.py`
Validation: reject
Validated by: agent
Action delta: No durable action: the target is a reviewer's scratch mutant driver outside the repository
Validation rationale: reverify3-code/run_mutants.py is a session scratchpad artifact used by the cycle-3 code-reviewer lane; it is not in the repository, and the linked findings were repaired in server_impl.py, record_paths.py, and wave_validators.py.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

reverify3-code/run_mutants.py required 2 separate repairs during wave 1y0gz; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `plans-cache-layout-key`
- `cycle2-adjacent-gaps`
- `1y0gz`

## Targets

- `reverify3-code/run_mutants.py`
