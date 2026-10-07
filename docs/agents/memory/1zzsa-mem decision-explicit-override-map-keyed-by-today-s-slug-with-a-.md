# Decision: Explicit override map keyed by today's slug, with a fixed d…

Owner: Engineering
Status: active
Last verified: 2026-10-07

Memory ID: `1zzsa-mem decision-explicit-override-map-keyed-by-today-s-slug-with-a-`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 68624
Source event: `decision-log:1zxnw-enh vocabulary-derived-prompt-names:aba8c8c7bd4618a5`
Validation: promote
Validated by: agent
Action delta: Rename lifecycle prompts for a distribution by editing the single-line PROMPT_NAME_OVERRIDES map keyed by default slug; never hardcode prompt names in consumers.
Validation rationale: vocabulary_profile.PROMPT_NAME_OVERRIDES and DEFAULT_PROMPT_NAMES exist and all named consumers derive from them.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Decision (wave 1zyb4): Explicit override map keyed by today's slug, with a fixed default table and an empty single-line override constant.. Rationale: Matches the fork-edit model of `vocabulary_profile.py` and `EXTRA_CHANGE_KINDS`; a one-line constant works with `apply_profile`; explicit names express chains and aliases such as Ready wave..

## Evidence

- `1zxnw-enh vocabulary-derived-prompt-names`
- `1zyb4`

## Targets

- `vocabulary_profile.py`
