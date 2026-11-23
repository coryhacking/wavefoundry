# Chunker ids and guards: prove uniqueness and pins with hostile fixtures

Owner: Engineering
Status: active
Last verified: 2026-11-22

Memory ID: `245u8-mem chunker-ids-and-guards-prove-uniqueness-and-pins-with-hostil`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-11-22
Updated: 2026-11-22
Supersedes: `1wj1s-mem bounded-symbol-id-parsers-duplicate-names-in-string-braces-s`

## Summary

Three chunker.py delivery reviews (waves 1wik9, 1wl7u, 1wl7w) found id-uniqueness or guard tests that looked proven but were not. (1) Ids from symbol names: give repeat names file-pass ordinals, count braces only on comment- and string-stripped text, guard comment attachment against code-before-comment lines, put residue ids in a namespace no identifier can produce (a colon), and make every content-detection branch fall through on a miss (pins: test_graphql_extend_declarations_get_unique_ordinal_ids, test_family_residue_ids_use_reserved_namespace, test_dual_root_key_yaml_keeps_openapi_units). (2) A line-start anchor such as {slug}-L{start} is not unique: same-line siblings share it, so id-collision probes must include the compact one-line form of every markup family before claiming no collision (pin: test_treesitter_html_same_line_siblings_dedupe). (3) A hostile-input test pins a guard only when the guard is the sole deciding condition: build the payload so every downstream fallback would accept it, and prove the pin against a guard-removed mutant (pin: test_escape_aligned_overcap_page_is_refused). Targets: chunker.py and tests/test_chunker.py.

## Evidence

- `consolidated from 1wj1s-mem bounded-symbol-id-parsers-duplicate-names-in-string-braces-s`
- `consolidated from 1wk93-mem line-start-anchored-chunk-ids-are-not-unique-census-probes-n`
- `consolidated from 1wllw-mem a-degenerate-input-test-does-not-pin-a-guard-when-an-earlier`

## Targets

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
