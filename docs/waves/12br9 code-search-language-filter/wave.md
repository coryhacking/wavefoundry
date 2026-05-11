# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-03

wave-id: `12br9 code-search-language-filter`
Title: Code Search Language Filter

## Objective

Fix code search language filter mismatches, normalize language extensions, add language categories, and evaluate embedding model ANE performance.

## Changes

Change ID: `12br9-bug code-search-language-filter-mismatch`
Change Status: `implemented`

Change ID: `12br9-enh code-search-language-extension-normalization`
Change Status: `implemented`

Change ID: `1297p-feat embedding-model-ane-eval`
Change Status: `implemented`

Change ID: `12bre-enh code-search-language-categories`
Change Status: `implemented`

Completed At: 2026-05-03

## Wave Summary

Fixes the code search language filter — chunkers were storing raw file extensions (`tsx`, `ts`, `sh`) instead of canonical language names (`typescript`, `shell`), causing `code_search(language="typescript")` to return no results. Also adds extension normalization to the query path so callers can pass either form, surfaces `language_extensions` in responses, and updates the embedding model evaluation plan to include code-specific model candidates.

## Journal Watchpoints

- Index rebuild required after this wave ships — existing indexes have stale language tags in code chunks.
- The embedding evaluation plan (`1297p-feat`) is admitted for tracking only; implementation is deferred until the benchmark harness is in place.

## Review Evidence

- Code and architecture review completed 2026-05-03 by Cory Hacking. All findings addressed: chunker ext map completed, cross-map consistency test fixed, CoreML provider removed, sorted batching, bge-base adopted, ADR authored, arch docs updated, index rebuilt. 742 tests passing.

## Dependencies

- No external wave dependencies.
