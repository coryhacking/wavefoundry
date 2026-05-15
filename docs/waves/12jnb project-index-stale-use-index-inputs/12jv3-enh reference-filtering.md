# Reference Filtering and Structural Prioritization

Change ID: `12jv3-enh reference-filtering`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-14
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

`code_references` is broad and useful, but it mixes real call sites with tests, docs, docstrings, and incidental mentions. The next step is to make the response more actionable by separating call-site signal from supporting mentions and by using structural navigation first for primary languages.

## Requirements

1. `code_references` should be able to prioritize real call sites ahead of tests and documentation mentions.
2. The response should expose typed buckets or an equivalent `reference_kind` field so agents can filter the results.
3. Structural navigation should be used first for primary languages, with text fallback only where structure is unavailable.
4. Existing broad behavior should remain available so no current agent workflow regresses.

## Scope

**Problem statement:** the current reference output is helpful for discovery but noisy for refactors. Agents need a higher-signal way to answer “where is this symbol actually used?” without manually filtering tests and doc mentions.

**In scope:**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py` only if launcher/help text needs updated examples

**Out of scope:**

- Removing the existing broad `code_references` behavior
- Changing `code_definition` semantics
- Adding a new external indexing dependency

## Acceptance Criteria

- `code_references` can separate call sites from tests/docs/other mentions, either via categories or a per-hit `reference_kind`.
- Call sites are ordered ahead of lower-signal mentions by default.
- Structural matching is used for Python and the tree-sitter-backed primary languages first.
- Text fallback remains available for unsupported languages and edge cases.
- Tests cover the high-signal ordering and the filtering behavior.
- Default `code_references` remains evidence-complete when no filters are passed.
- The response includes category counts so agents can gauge signal quality without reading every hit.

## Tasks

- Design the reference classification shape
- Add optional filters for tests/docs/mentions if needed
- Prioritize structural call-site results for primary languages
- Add regressions for noisy short symbols and broad reference searches

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Separating call sites from mentions is the core value-add |
| AC-2 | required | Ordering high-signal results first makes the tool usable without extra filtering |
| AC-3 | required | Structural navigation is the reason to prefer primary-language support |
| AC-4 | required | Fallback coverage keeps the tool usable outside structured languages |
| AC-5 | required | Default responses must stay evidence-complete so the broad mode does not regress |
| AC-6 | important | Category counts make the new response shape easier to interpret quickly |
| AC-7 | required | Regression coverage keeps the ordering and filtering behavior honest |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Over-filtering hides useful evidence | Keep broad mode available and default to inclusion, not exclusion |
| Structural parser gaps create false negatives | Retain text fallback and keep test coverage for unsupported paths |
| Output shape churn breaks agents | Add explicit category fields rather than changing the broad response silently |
