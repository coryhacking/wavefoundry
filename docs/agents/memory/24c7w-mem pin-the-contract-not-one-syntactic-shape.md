# Pin the contract, not one syntactic shape

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24c7w-mem pin-the-contract-not-one-syntactic-shape`
Kind: `failed_attempt`
Confidence: 0.75
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 104280
Supersedes: `1t4o2-mem repaired-defect-fallback-reason-census-still-incomplete`

## Summary

When writing a source pin that keeps a canonical vocabulary's literals out of an emitting module, assert zero quoted occurrences of every value by iterating the contract tuple itself, then plant a quoted literal to watch the pin fail and restore it. A pin that only rejects one shape (fallback_reason = "...") missed call arguments, comparisons and dict values in wave 1seax, and model_unavailable and index_missing stayed out of LEXICAL_FALLBACK_REASONS (test_handlers_consume_the_vocabulary_aliases in .wavefoundry/framework/scripts/tests/test_docs_constants_lint.py is the repaired pin). Supplements 1t4rg-mem a-canonical-constants-module-is-not-single-source-until-emit.

## Evidence

- `fallback-reason-census-still-incomplete`
- `ev-fallback-reason-census-still-incomplete-3`
- `1seax`
- `PublicContractTests.test_handlers_consume_the_vocabulary_aliases`

## Targets

- `.wavefoundry/framework/scripts/tests/test_docs_constants_lint.py`
- `.wavefoundry/framework/scripts/public_contract.py`
