# Wave Record

Owner: Engineering
Status: active
Last verified: 2026-05-02

wave-id: `12br9 code-search-language-filter`
Title: Code Search Language Filter

## Changes

Change ID: `12br9-bug code-search-language-filter-mismatch`
Change Status: `planned`

Change ID: `12br9-enh code-search-language-extension-normalization`
Change Status: `planned`

Change ID: `1297p-feat embedding-model-ane-eval`
Change Status: `planned`

Change ID: `12bre-enh code-search-language-categories`
Change Status: `planned`

## Wave Summary

Fixes the code search language filter — chunkers were storing raw file extensions (`tsx`, `ts`, `sh`) instead of canonical language names (`typescript`, `shell`), causing `code_search(language="typescript")` to return no results. Also adds extension normalization to the query path so callers can pass either form, surfaces `language_extensions` in responses, and updates the embedding model evaluation plan to include code-specific model candidates.

## Journal Watchpoints

- Index rebuild required after this wave ships — existing indexes have stale language tags in code chunks.
- The embedding evaluation plan (`1297p-feat`) is admitted for tracking only; implementation is deferred until the benchmark harness is in place.

## Dependencies

- No external wave dependencies.
