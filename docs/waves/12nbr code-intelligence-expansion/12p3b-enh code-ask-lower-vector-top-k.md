# `code_ask` should use a smaller candidate window

Change ID: `12p3b-enh code-ask-lower-vector-top-k`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-17
Wave: 12nbr code-intelligence-expansion

## Rationale

Field measurements show that `code_ask` latency is dominated by reranking rather than vector fetch. The current 40/60 candidate windows are larger than necessary for the observed queries. Reducing the base candidate pool should lower rerank cost without changing the retrieval pipeline or the existing question-type-aware behavior.

## Requirements

1. Reduce the default `VECTOR_TOP_K` candidate window from 40 to 30.
2. Reduce the explanatory `VECTOR_TOP_K_EXPLANATORY` candidate window from 60 to 50.
3. Keep the existing rerank, second-hop, and partition behavior unchanged.
4. Update the public architecture/spec docs and tests to match the new constants.

## Scope

**Problem statement:** the current `code_ask` candidate windows are larger than necessary for the observed latency profile, making reranking the dominant cost.

**In scope:**

- `server.py`
- `test_server_tools.py`
- `docs/architecture/search-architecture.md`

**Out of scope:**

- Changing the reranker model
- Changing the second-hop expansion behavior
- Changing the `code_ask` response schema

## Acceptance Criteria

- AC-1: `VECTOR_TOP_K` is 30.
- AC-2: `VECTOR_TOP_K_EXPLANATORY` is 50.
- AC-3: `search_combined()` uses the smaller windows for the corresponding question types.
- AC-4: Tests and docs reflect the new candidate windows.

## Required Review Lanes

- `code-reviewer` — required (framework script change)
- `qa-reviewer` — required (behavioral retrieval tuning)

## Tasks

- Update the module-level constants in `server.py`.
- Update tests that pin the constants or candidate-window behavior.
- Refresh the architecture doc description of the candidate windows and tradeoff.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`

## AC Priority

| AC   | Priority | Rationale |
| ---- | --------- | --------- |
| AC-1 | required | Default path should use the smaller pool |
| AC-2 | required | Explanatory path should also shrink consistently |
| AC-3 | required | Confirms the active query path uses the tuned constants |
| AC-4 | important | Keeps docs and tests aligned with the code |
