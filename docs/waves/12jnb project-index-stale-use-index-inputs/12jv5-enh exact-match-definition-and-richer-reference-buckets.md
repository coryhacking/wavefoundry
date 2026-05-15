# Exact Match Definition Ranking and Richer Reference Buckets

Change ID: `12jv5-enh exact-match-definition-and-richer-reference-buckets`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The new symbol-navigation path is working, but the Java agent report exposed two refinements that would make it more reliable for mixed repos:

1. `code_definition` can surface partial matches alongside the intended symbol, which is useful for discovery but noisy when the caller wants the exact symbol first.
2. `code_references` currently groups non-call-site evidence into a single `other` bucket, which hides useful distinctions like imports, declarations, and generic mentions.

## Requirements

1. `code_definition` should prioritize exact symbol matches ahead of partial matches for the same query.
2. `code_definition` should preserve broad fallback discovery, but make exact matches the first result when they exist.
3. `code_references` should split non-call-site references into finer buckets so callers can tell imports/definitions/mentions apart.
4. The default broad response must remain evidence-complete; no existing call-site, test, or doc evidence should disappear unless a filter explicitly excludes it.

## Scope

**Problem statement:** the current navigation contract is correct but not yet as precise as it could be for agents doing refactors or validation in mixed repositories.

**In scope:**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

**Out of scope:**

- Changing tree-sitter coverage or the semantic index pipeline
- Removing broad discovery behavior from either tool
- Reworking the `code_references(limit=...)` contract

## Acceptance Criteria

- Exact definition matches appear first when a symbol has both exact and partial matches.
- The broad fallback still returns additional matches when no exact definition is found.
- `code_references` exposes finer-grained non-call-site buckets while keeping the broad result set intact.
- Tests cover at least one exact-match-vs-partial-match case and one non-call-site bucket split case.

## Tasks

- Rank exact symbol definitions ahead of partial matches
- Split the `other` reference bucket into more precise categories
- Add regressions for exact-match precedence and bucket separation

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Exact matches are the primary reliability improvement |
| AC-2 | required | Broad fallback must remain available for discovery |
| AC-3 | required | Finer buckets improve signal without reducing evidence |
| AC-4 | required | Regression coverage prevents the refactor from drifting |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Exact-match ranking suppresses useful discovery matches | Keep partial matches after exact matches instead of removing them |
| More buckets increases response complexity | Preserve the current broad contract and make the extra buckets additive |
| Bucket names drift from classifiers | Add regression coverage for the new bucket labels and ordering |
