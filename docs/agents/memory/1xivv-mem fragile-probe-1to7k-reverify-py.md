# Fragile: probe_1to7k_reverify.py

Owner: Engineering
Status: candidate
Last verified: 2026-09-09

Memory ID: `1xivv-mem fragile-probe-1to7k-reverify-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-09
Updated: 2026-09-09
Source exploration cost: 1297988
Source event: `repeated-repairs:1to7k:probe_1to7k_reverify.py`
Validation: pending

## Summary

probe_1to7k_reverify.py required 3 separate repairs during wave 1to7k; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `same-actor-same-context-nonfresh-reverification-accepted`
- `open-wave-fallback-stage-mismatch-suppressed`
- `sealed-close-focus-clear-failure-is-silent`
- `1to7k`

## Targets

- `probe_1to7k_reverify.py`
