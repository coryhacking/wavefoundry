# Decision: Keep it a small local helper/inline guard in `indexer.py`;…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-keep-it-a-small-local-helper-inline-guard-in-indexe`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9iw-bug atomic-write-windows-share-retry:36a47dc2f0993804`
Validation: reject
Validated by: agent
Action delta: None; choose the smallest current implementation after inspecting present call sites.
Validation rationale: The local-helper choice was scoped to one historical call site and does not establish a durable constraint.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p9j0): Keep it a small local helper/inline guard in `indexer.py`; no new module or config.. Rationale: Simplest-thing-that-works; single call site; no operator surface warranted for a transient..

## Evidence

- `1p9iw-bug atomic-write-windows-share-retry`
- `1p9j0`

## Targets

- `indexer.py`
