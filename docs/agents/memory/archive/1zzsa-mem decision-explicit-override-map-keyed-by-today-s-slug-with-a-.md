# Decision: Explicit override map keyed by today's slug, with a fixed d…

Owner: Engineering
Status: archived
Last verified: 2026-10-07

Memory ID: `1zzsa-mem decision-explicit-override-map-keyed-by-today-s-slug-with-a-`
Superseded by: `249st-mem prompt-renames-go-through-prompt-name-overrides`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-11-25
Source exploration cost: 68624
Source event: `decision-log:1zxnw-enh vocabulary-derived-prompt-names:aba8c8c7bd4618a5`
Validation: promote
Validated by: agent
Action delta: Rename lifecycle prompts for a distribution by editing the single-line PROMPT_NAME_OVERRIDES map keyed by default slug; never hardcode prompt names in consumers.
Validation rationale: vocabulary_profile.PROMPT_NAME_OVERRIDES and DEFAULT_PROMPT_NAMES exist and all named consumers derive from them.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Archived: 2026-11-25
Archive reason: Superseded by 249st-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1zzsa-mem decision-explicit-override-map-keyed-by-today-s-slug-with-a-.md`

## Summary

Decision (wave 1zyb4): Explicit override map keyed by today's slug, with a fixed default table and an empty single-line override constant.. Rationale: Matches the fork-edit model of `vocabulary_profile.py` and `EXTRA_CHANGE_KINDS`; a one-line constant works with `apply_profile`; explicit names express chains and aliases such as Ready wave..

## Evidence

- `1zxnw-enh vocabulary-derived-prompt-names`
- `1zyb4`

## Targets

- `vocabulary_profile.py`
