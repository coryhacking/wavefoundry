# Decision: Fix the escape at the source AND add `filename=` to the ind…

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-decision-fix-the-escape-at-the-source-and-add-filename-to-th`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9p6-bug python-parse-filename-and-invalid-escape:f02ba5f503bd6609`
Validation: rewrite
Validated by: agent
Action delta: Pass the real path into target-code parser calls and keep a sweep test for warning classes that can otherwise lose file attribution.
Validation rationale: Current chunker and graph paths still rely on filename-aware AST parsing, which materially improves build diagnostics and regression localization.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-give-target-code-parser-failures-their-real-filename`
## Summary

Decision (wave 1p9pe): Fix the escape at the source AND add `filename=` to the indexing-path parses AND add a sweep guard (approach A).. Rationale: Fixes the actual defect, closes the diagnosability gap the operator flagged, and makes the escape class non-regressable. The `filename=` change is tiny and each site has a path readily available (or a trivial optional param)..

## Evidence

- `1p9p6-bug python-parse-filename-and-invalid-escape`
- `1p9pe`

## Targets

- `test_wf_cli.py`
