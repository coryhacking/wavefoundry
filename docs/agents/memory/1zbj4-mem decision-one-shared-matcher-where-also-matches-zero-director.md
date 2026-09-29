# Decision: One shared matcher where `**/` also matches zero directorie…

Owner: Engineering
Status: rejected
Last verified: 2026-09-29

Memory ID: `1zbj4-mem decision-one-shared-matcher-where-also-matches-zero-director`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 164401
Source event: `decision-log:1z9ya-bug code-tool-glob-double-star-skips-top-level:d826714e8ac06c0f`
Validation: reject
Validated by: agent
Action delta: No durable action: the glob rule is stated in the spec's Glob filters paragraph and pinned by test_navigation_glob.
Validation rationale: Duplicates the spec and tests; drafted target dir/*.py is not a file.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 1za2y): One shared matcher where `**/` also matches zero directories, keeping every current match. Rationale: Fixes the defect without changing any glob that works today.

## Evidence

- `1z9ya-bug code-tool-glob-double-star-skips-top-level`
- `1za2y`

## Targets

- `dir/*.py`
