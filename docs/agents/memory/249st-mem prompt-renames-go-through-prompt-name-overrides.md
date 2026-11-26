# Prompt renames go through PROMPT_NAME_OVERRIDES

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249st-mem prompt-renames-go-through-prompt-name-overrides`
Kind: `decision`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 68624
Supersedes: `1zzsa-mem decision-explicit-override-map-keyed-by-today-s-slug-with-a-`

## Summary

When a distribution renames lifecycle prompts, edit the single-line PROMPT_NAME_OVERRIDES map in .wavefoundry/framework/scripts/vocabulary_profile.py, keyed by the default slug in DEFAULT_PROMPT_NAMES, and never hardcode prompt names in consumers. Why: decision of wave 1zyb4; it matches the fork-edit model of EXTRA_CHANGE_KINDS, a one-line constant works with apply_profile, and explicit names express chains and aliases such as Ready wave.

## Evidence

- `1zxnw-enh vocabulary-derived-prompt-names`
- `1zyb4`

## Targets

- `.wavefoundry/framework/scripts/vocabulary_profile.py`
