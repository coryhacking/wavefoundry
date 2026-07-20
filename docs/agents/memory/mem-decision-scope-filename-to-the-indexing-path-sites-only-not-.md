# Decision: Scope `filename=` to the indexing-path sites only, not ever…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-scope-filename-to-the-indexing-path-sites-only-not-`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9p6-bug python-parse-filename-and-invalid-escape:d5ca400b55c815e6`
Validation: reject
Validated by: agent
Action delta: None; the rewritten filename-aware parser memory captures the durable action without preserving an old call-site census.
Validation rationale: This scope decision is an intermediate implementation boundary and duplicates the consolidated parser-diagnostics lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p9pe): Scope `filename=` to the indexing-path sites only, not every `ast.parse` in the tree.. Rationale: Those three sites produced the observed build-log noise and parse target-repo code at scale; the `server_impl.py` navigation/outline sites are a separate, non-build concern and some already pass `filename=`..

## Evidence

- `1p9p6-bug python-parse-filename-and-invalid-escape`
- `1p9pe`

## Targets

- `server_impl.py`
