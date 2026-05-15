# Non-Call-Site Reference Splits

Change ID: `12jv6-enh non-call-site-reference-splits`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The current reference buckets are correct, but `other` is still a catch-all for definitions, imports, and generic mentions. Splitting those cases would make `code_references` more useful for refactors and dependency tracing without changing the existing broad evidence-complete contract.

## Requirements

1. Non-call-site references should be split into more specific buckets.
2. At minimum, the tool should distinguish definitions, imports, and generic mentions where the source language allows it.
3. The broad response must remain evidence-complete and preserve call-site / doc / test behavior.
4. Existing filters and ordering semantics must continue to work.

## Scope

**Problem statement:** users can already tell whether a hit is a call site, doc, or test, but the remaining `other` bucket is too coarse for mixed-language repos.

**In scope:**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

**Out of scope:**

- Changing the `code_references(limit=...)` contract
- Changing `code_definition`
- Altering tree-sitter or indexer behavior outside of reference classification

## Acceptance Criteria

- Definitions, imports, and generic mentions are separated where possible.
- The result shape remains backward-compatible for call sites, docs, and tests.
- Ordering still prioritizes call sites first.
- Tests cover at least one symbol with imports, definitions, and mentions in the same repo.

## Tasks

- Split the `other` bucket into finer-grained non-call-site categories
- Update `code_references` aggregation and response fields
- Add regression coverage for a mixed-category symbol

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The bucket split is the core of the improvement |
| AC-2 | required | Backward compatibility prevents regression for agents already using the API |
| AC-3 | required | Call-site ordering is still the primary signal contract |
| AC-4 | required | Regression coverage keeps the new classifier honest |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Fine-grained classification becomes language-specific and inconsistent | Keep the new split additive and preserve the existing broad fields |
| More buckets make the payload harder to scan | Keep call sites first and preserve the existing top-level counts |
| Definitions and imports are difficult to distinguish in some languages | Classify only where language structure is reliable; fall back to generic mentions otherwise |
