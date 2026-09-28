# Chunk metadata changes: keep the hash constant and exempt rechunk from the registry skip

Owner: Engineering
Status: active
Last verified: 2026-09-28

Memory ID: `1z75t-mem chunk-metadata-changes-keep-the-hash-constant-and-exempt-rec`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-09-28
Updated: 2026-09-28
Source exploration cost: 102181
Source event: `repeated-repairs:1z8tz:tests/test_chunk_tags.py`
Validation: promote
Validated by: agent
Action delta: Before changing stored chunk metadata, keep _chunk_hash's payload constant, exempt rechunk paths from the registry skip, bump CHUNKER_VERSION, and pin the hash to a HEAD-computed digest.
Validation rationale: Readiness found the naive plan (exclude tags from the hash) would write no tags while AC-3 passed; delivery found the hash shape unpinned (a dropped key would re-embed the corpus undetected). The drafted fragile-file summary carried no actionable lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

indexer._chunk_hash keys embedding reuse AND the registry fast path. Adding or changing stored chunk metadata (e.g. tags) inside the hash re-embeds every affected chunk; dropping a key from the payload changes every stored hash and re-embeds the corpus; leaving the hash unchanged makes the registry fast path skip every file on a CHUNKER bump, so the metadata is never written. Pattern that works (wave 1z8tz): keep the payload byte-identical (constant value), add the stale paths to _skip_exempt on rechunk so the delta planner's _row_metadata_matches_current rewrites rows with their existing vectors, bump CHUNKER_VERSION (not WALKER_VERSION), pin _chunk_hash to a literal digest computed from HEAD, and assert BOTH zero encoder calls and the stored metadata after a real upgrade build.

## Evidence

- `chunk-tag-test-coverage-gaps`
- `tag-prefix-matching-edges`
- `1z8tz`

## Targets

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_chunk_tags.py`
