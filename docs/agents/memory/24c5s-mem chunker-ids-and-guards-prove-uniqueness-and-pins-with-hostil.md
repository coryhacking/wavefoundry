# Chunker ids and guards: prove uniqueness and pins with hostile inputs

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24c5s-mem chunker-ids-and-guards-prove-uniqueness-and-pins-with-hostil`
Kind: `failed_attempt`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `245u8-mem chunker-ids-and-guards-prove-uniqueness-and-pins-with-hostil`

## Summary

When changing chunk id generation or a hostile-input guard in .wavefoundry/framework/scripts/chunker.py, prove uniqueness and pins against hostile inputs before claiming them: (1) give repeated symbol names file-pass ordinals, count braces only on comment- and string-stripped text, guard comment attachment against code-before-comment lines, put residue ids in a namespace no identifier can produce (a colon), and make every content-detection branch fall through on a miss; (2) a line-start anchor such as {slug}-L{start} is not unique, so collision probes must include the compact one-line form of every markup family; (3) a hostile-input test pins a guard only when the guard is the sole deciding condition, so build payloads every downstream fallback would accept and prove the pin against a guard-removed mutant. Why: three delivery reviews (waves 1wik9, 1wl7u, 1wl7w) found tests that looked proven but were not. Pins in tests/test_chunker.py: test_graphql_extend_declarations_get_unique_ordinal_ids, test_family_residue_ids_use_reserved_namespace, test_dual_root_key_yaml_keeps_openapi_units, test_treesitter_html_same_line_siblings_dedupe, test_escape_aligned_overcap_page_is_refused.

## Evidence

- `consolidated from 1wj1s-mem bounded-symbol-id-parsers-duplicate-names-in-string-braces-s`
- `consolidated from 1wk93-mem line-start-anchored-chunk-ids-are-not-unique-census-probes-n`
- `consolidated from 1wllw-mem a-degenerate-input-test-does-not-pin-a-guard-when-an-earlier`

## Targets

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
