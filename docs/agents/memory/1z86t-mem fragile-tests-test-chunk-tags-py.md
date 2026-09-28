# Fragile: tests/test_chunk_tags.py

Owner: Engineering
Status: superseded
Last verified: 2026-09-28

Memory ID: `1z86t-mem fragile-tests-test-chunk-tags-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-28
Updated: 2026-09-28
Source exploration cost: 102181
Source event: `repeated-repairs:1z8tz:tests/test_chunk_tags.py`
Validation: rewrite
Validated by: agent
Action delta: Before changing stored chunk metadata, keep _chunk_hash's payload constant, exempt rechunk paths from the registry skip, bump CHUNKER_VERSION, and pin the hash to a HEAD-computed digest.
Validation rationale: Readiness found the naive plan (exclude tags from the hash) would write no tags while AC-3 passed; delivery found the hash shape unpinned (a dropped key would re-embed the corpus undetected). The drafted fragile-file summary carried no actionable lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1z75t-mem chunk-metadata-changes-keep-the-hash-constant-and-exempt-rec`

## Summary

tests/test_chunk_tags.py required 2 separate repairs during wave 1z8tz; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `tag-prefix-matching-edges`
- `chunk-tag-test-coverage-gaps`
- `1z8tz`

## Targets

- `tests/test_chunk_tags.py`
