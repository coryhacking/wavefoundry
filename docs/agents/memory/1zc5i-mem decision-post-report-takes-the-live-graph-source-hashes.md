# Decision: Post report takes the live graph-source hashes

Owner: Engineering
Status: rejected
Last verified: 2026-09-29

Memory ID: `1zc5i-mem decision-post-report-takes-the-live-graph-source-hashes`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 164401
Source event: `decision-log:1za2x-debt graph-quality-probe-tree-kill-remeasure:7d04716b645d9d20`
Validation: reject
Validated by: agent
Action delta: No durable action beyond the documented procedure in testing-architecture.md, which says post production hashes follow the live graph sources.
Validation rationale: The re-measure procedure and its allowed field changes are recorded in docs/architecture/testing-architecture.md; a memory would duplicate it.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 1za2y): Post report takes the live graph-source hashes. Rationale: Commits `3433fb03`, `8545c4f9` and `24513060` edited `graph_indexer.py` and `graph_query.py` after the post report was measured at `5a30d7a5`, so a post measured from the live scripts (Requirement 2) cannot keep those two hashes (Requirement 3). The post report describes the production that ships; every measured number is unchanged, and `test_the_shipped_post_report_still_matches_a_fresh_run` already requires that.

## Evidence

- `1za2x-debt graph-quality-probe-tree-kill-remeasure`
- `1za2y`

## Targets

- `graph_indexer.py`
- `graph_query.py`
