# Repaired defect lint-validators-own-walk

Owner: Engineering
Status: rejected
Last verified: 2026-09-17

Memory ID: `1yciw-mem repaired-defect-lint-validators-own-walk`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-17
Updated: 2026-09-17
Source exploration cost: 578663
Source event: `finding:1y0gz:lint-validators-own-walk`
Validation: reject
Validated by: agent
Action delta: No durable action from this record: its target is a reviewer scratch probe; the rule that wave discovery goes only through record_paths.discover_wave_dirs is stated in docs/architecture/layering-rules.md and pinned by the nested-divergence lint test
Validation rationale: The generated record targets reverify-arch/probe_divergence.py, a session scratchpad artifact not present in the tree. The repair lives in wave_validators._wave_record_docs/_wave_record_files, the hook template, commit_provenance._wave_dir_for_id, and _state_sources_memory_propose, each routed through discover_wave_dirs and pinned; the layering-rules sentence carries the rule.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1y0gz: Repaired; the session-capture hook's flat iterdir is routed through discover_wave_dirs in the follow-on repair batch so the layering sentence is literally true

## Evidence

- `lint-validators-own-walk`
- `ev-lint-validators-own-walk-3`
- `1y0gz`

## Targets

- `reverify-arch/probe_divergence.py`
