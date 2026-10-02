# Decision: Declare extra kinds in `vocabulary_profile.py`, with the co…

Owner: Engineering
Status: superseded
Last verified: 2026-10-01

Memory ID: `1zl1e-mem decision-declare-extra-kinds-in-vocabulary-profile-py-with-t`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 308945
Source event: `decision-log:1zimp-enh declared-extra-change-kinds:0bd2124c4acd944b`
Validation: rewrite
Validated by: agent
Action delta: Add or read change kinds only through vocabulary_profile (CORE_CHANGE_KINDS, EXTRA_CHANGE_KINDS, CHANGE_KINDS); never hardcode a kind list, a census test fails on one.
Validation rationale: The decision holds in the tree (vocabulary_profile owns CORE/EXTRA/CHANGE_KINDS; lint constants, lifecycle_id KIND_CHOICES and server derive from it; KindCensusTests guards it). The generated candidate wrongly targets mcp_tool_extensions.py, which holds no kind state.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1zlpf-mem change-kinds-have-one-source-vocabulary-profile`

## Summary

Decision (wave 1zimf): Declare extra kinds in `vocabulary_profile.py`, with the core kinds moved there as the single source. Rationale: The kind token is record grammar; the profile is the distribution-edited, import-validated, fail-closed home for record grammar, is already imported by lint constants and the server, and is covered by the test profile assets.

## Evidence

- `1zimp-enh declared-extra-change-kinds`
- `1zimf`

## Targets

- `vocabulary_profile.py`
- `mcp_tool_extensions.py`
