# Change kinds have one source: vocabulary_profile

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24cdf-mem change-kinds-have-one-source-vocabulary-profile`
Kind: `decision`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 308945
Supersedes: `1zlpf-mem change-kinds-have-one-source-vocabulary-profile`
Checked at: 2026-11-26T06:32:45Z
Check note: The vocabulary module splits fixed and extension kinds. New consumers must consult the declaration instead of assuming the shipped list. Reviewed .wavefoundry/framework/scripts/vocabulary_profile.py:16.
Check flags: none

## Summary

When adding, retiring or reading a change kind, go through .wavefoundry/framework/scripts/vocabulary_profile.py (CORE_CHANGE_KINDS fixed, EXTRA_CHANGE_KINDS distribution-declared, CHANGE_KINDS derived, RETIRED_CHANGE_KINDS and MINTABLE_CHANGE_KINDS) and never hardcode a kind list. Why: decision of wave 1zimf; lifecycle_id.KIND_CHOICES and the docs-lint patterns in wave_lint_lib/constants.py derive from it, EXTRA_CHANGE_KINDS is validated at import with reserved tokens, and tests/test_change_kinds.py KindCensusTests.test_no_kind_list_outside_the_profile fails on a hardcoded list in scripts or dashboard assets.

## Evidence

- `1zimp-enh declared-extra-change-kinds`
- `1zimf`
- `test_change_kinds.KindCensusTests.test_no_kind_list_outside_the_profile`

## Targets

- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/lifecycle_id.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/scripts/tests/test_change_kinds.py`
