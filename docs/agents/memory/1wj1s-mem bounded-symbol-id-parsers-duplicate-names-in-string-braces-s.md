# Bounded symbol-id parsers: duplicate names, in-string braces, shadowable residue labels, detection order

Owner: Engineering
Status: active
Last verified: 2026-08-27

Memory ID: `1wj1s-mem bounded-symbol-id-parsers-duplicate-names-in-string-braces-s`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-08-27
Updated: 2026-08-27

## Summary

Wave 1wik9 delivery review (CODE-DEL-1, CODE-DEL-2): the first 1wfso GraphQL/proto parsers keyed chunk ids by bare symbol name and counted raw braces, so legal SDL extend blocks silently collapsed in the id-keyed delta planner, braces inside block-string descriptions / proto string defaults / trailing comments corrupted extents and package-qualified paths, a code line ending in a same-line /* */ was misread as the next member's leading comment, a symbol literally named proto or sdl collided with the fixed residue id, and the AsyncAPI-before-OpenAPI YAML check silently dropped OpenAPI units on dual-root-key files (the shipped not-load-bearing comment was falsified by execution). When writing a bounded parser that emits ids from symbol names: give repeat crumbs file-pass ordinals, count braces only on comment-and-string-stripped text, guard comment attachment against code-before-comment lines, put residue ids in a namespace no identifier can produce (a colon), and make every content-detection branch fall through on a miss instead of swallowing the file.

## Evidence

- `CODE-DEL-1`
- `CODE-DEL-2`
- `ev-code-del-1-3`
- `ev-code-del-2-3`
- `test_chunker.SpecFamilyTests.test_graphql_extend_declarations_get_unique_ordinal_ids`
- `test_chunker.SpecFamilyTests.test_family_residue_ids_use_reserved_namespace`
- `test_chunker.SpecFamilyTests.test_dual_root_key_yaml_keeps_openapi_units`

## Targets

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
