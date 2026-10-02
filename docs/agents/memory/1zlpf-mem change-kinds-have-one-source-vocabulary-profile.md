# Change kinds have one source: vocabulary_profile

Owner: Engineering
Status: active
Last verified: 2026-10-01

Memory ID: `1zlpf-mem change-kinds-have-one-source-vocabulary-profile`
Kind: `decision`
Confidence: 0.9
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 308945
Source event: `decision-log:1zimp-enh declared-extra-change-kinds:0bd2124c4acd944b`
Validation: promote
Validated by: agent
Action delta: Add or read change kinds only through vocabulary_profile (CORE_CHANGE_KINDS, EXTRA_CHANGE_KINDS, CHANGE_KINDS); never hardcode a kind list, a census test fails on one.
Validation rationale: The decision holds in the tree (vocabulary_profile owns CORE/EXTRA/CHANGE_KINDS; lint constants, lifecycle_id KIND_CHOICES and server derive from it; KindCensusTests guards it). The generated candidate wrongly targets mcp_tool_extensions.py, which holds no kind state.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Decision (wave 1zimf): change kinds live only in vocabulary_profile (CORE_CHANGE_KINDS fixed, EXTRA_CHANGE_KINDS distribution-declared, CHANGE_KINDS derived), validated at import with fullmatch and reserved tokens wave, mem, sec, adr, jrnl. Docs-lint patterns, VALID_CHANGE_KINDS and lifecycle_id KIND_CHOICES derive from it; KindCensusTests fails on any hardcoded kind list in scripts or dashboard JS.

## Evidence

- `1zimp-enh declared-extra-change-kinds`
- `1zimf`

## Targets

- `vocabulary_profile.py`
- `lifecycle_id.py`
- `wave_lint_lib/constants.py`
