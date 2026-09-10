# Decision: AC-1 test shape: injection of the captured identity (the al…

Owner: Engineering
Status: candidate
Last verified: 2026-09-09

Memory ID: `1xkpj-mem decision-ac-1-test-shape-injection-of-the-captured-identity-`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-09
Updated: 2026-09-09
Source exploration cost: 818447
Source event: `decision-log:1u2ay-bug server-runner-version-never-distinguishes-stale-runner:3c87c60838c7e12b`
Validation: pending

## Summary

Decision (wave 1u2b0): AC-1 test shape: injection of the captured identity (the allowed alternative), not a fresh-subprocess MCP probe. Rationale: The comparison seam is exactly the (identity, runner_files) pair `server.py` records at launch; injecting it over temp copies of the real runner files exercises the same code path deterministically and lets both stale directions and both files be covered without subprocess flake.

## Evidence

- `1u2ay-bug server-runner-version-never-distinguishes-stale-runner`
- `1u2b0`

## Targets

- `server.py`
