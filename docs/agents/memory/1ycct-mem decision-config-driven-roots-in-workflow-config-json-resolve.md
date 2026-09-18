# Decision: Config-driven roots in `workflow-config.json`, resolved by…

Owner: Engineering
Status: superseded
Last verified: 2026-09-17

Memory ID: `1ycct-mem decision-config-driven-roots-in-workflow-config-json-resolve`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-17
Updated: 2026-09-17
Source exploration cost: 578663
Source event: `decision-log:1y042-enh record-roots-config-and-resolver:a8e20667877520c3`
Validation: rewrite
Validated by: agent
Action delta: Do not read record roots from workflow-config; edit the constants in record_paths.py at merge time and keep validation fail-closed there
Validation rationale: The generated candidate captures the SUPERSEDED cycle-1 decision (config-driven roots). The operator redirected the design during delivery review on 2026-09-17: roots are fork-editable module constants (WAVES_ROOT, PLANS_ROOT, NESTED, MAX_DEPTH) in record_paths.py, nothing is read from configuration, and the ADR 1yb8v records why (a runtime-dynamic layout needed input validation, cache invalidation, and lint-corpus following, which produced three review findings). Verified against record_paths.py and the ADR on the current tree.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1ybvy-mem decision-record-roots-are-fork-editable-constants-in-record-`
## Summary

Decision (wave 1y0gz): Config-driven roots in `workflow-config.json`, resolved by one stdlib module. Rationale: Waveforge already commits that file; no repository code is imported by the server; matches the recorded config-over-plugin stance and the `index_paths.py` pattern.

## Evidence

- `1y042-enh record-roots-config-and-resolver`
- `1y0gz`

## Targets

- `index_paths.py`
