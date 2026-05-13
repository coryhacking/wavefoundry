# MCP: Preserve Mixed-Language Symbol Navigation Results

Change ID: `12jqm-bug mixed-language-navigation-aggregation`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The expanded symbol-navigation layer now supports Python, tree-sitter-backed Java/C#/JavaScript/TypeScript, and regex/text fallback for additional languages. But the current aggregation logic still suppresses valid fallback results from other languages whenever a tree-sitter-backed language returns any match. That breaks the broader multi-language contract by truncating mixed-language answers to the first matching navigation path.

## Requirements

1. `code_definition` must return mixed-language definition results when the same symbol exists across tree-sitter-backed and fallback languages.
2. `code_references` must return mixed-language reference results when the same symbol exists across tree-sitter-backed and fallback languages.
3. Tree-sitter-backed languages must still prefer structural results over duplicate fallback matches for the same file/line.
4. The wave review evidence must reflect the full admitted scope of the active wave, not only the original dashboard stale-detector fix.
5. Verification must pass.

## Scope

**Problem statement:** the current navigation aggregation path still behaves like a winner-take-all search, even though the tool surface now claims multi-language symbol lookup.

**In scope:**

- `.wavefoundry/framework/scripts/server.py`
  - Aggregate tree-sitter and fallback navigation results across languages
  - Deduplicate overlapping hits while preferring stronger structural methods
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
  - Add regressions for mixed-language definitions and references
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`
  - Refresh review evidence so the readiness approval covers all admitted changes

**Out of scope:**

- LSP-grade cross-language semantic resolution
- New language support beyond the existing surface

## Acceptance Criteria

- AC-1: `code_definition` returns both tree-sitter-backed and fallback-language matches for a symbol that exists in multiple languages.
- AC-2: `code_references` returns both tree-sitter-backed and fallback-language matches for a symbol that exists in multiple languages.
- AC-3: Duplicate hits for the same file/line are deduplicated in favor of the stronger structural method.
- AC-4: The wave’s review evidence explicitly covers the full admitted scope.
- AC-5: Verification passes.

## Tasks

- Fix mixed-language definition aggregation
- Fix mixed-language reference aggregation
- Add regressions for mixed-language aggregation
- Refresh wave review evidence to full-scope wording
- Run targeted and full verification

## Affected Architecture Docs

N/A - behavior correction and wave-record review-trace fix.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core correctness issue in the multi-language navigation contract |
| AC-2 | required | References must not lag definitions |
| AC-3 | required | Avoid duplicate/noisy output while broadening aggregation |
| AC-4 | required | Wave closure evidence must match actual admitted scope |
| AC-5 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-12 | Change doc created after wave review found mixed-language navigation truncation and stale narrow-scope readiness wording in the active wave record. | `.wavefoundry/framework/scripts/server.py`; `.wavefoundry/framework/scripts/tests/test_server_tools.py`; `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md` |
| 2026-05-12 | Aggregated tree-sitter and fallback navigation results across languages, deduplicated overlapping hits while preserving stronger structural methods, added mixed-language regressions, and refreshed the wave review evidence to cover the full admitted scope. | `.wavefoundry/framework/scripts/server.py`; `.wavefoundry/framework/scripts/tests/test_server_tools.py`; `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`; `python3 -B .wavefoundry/framework/scripts/run_tests.py`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-12 | Aggregate results across navigation methods and deduplicate by location rather than suppressing whole fallback classes | Preserves the advertised multi-language contract while still preferring stronger structural hits | Keep winner-take-all precedence by method (rejected: drops valid matches from other languages) |

## Risks

| Risk | Mitigation |
|------|------------|
| Aggregating all methods could produce duplicate or noisy results | Deduplicate by stable location/name keys and prefer structural methods |
| Refreshing review evidence could overstate coverage again | Explicitly enumerate the admitted changes covered by the refreshed approval line |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
