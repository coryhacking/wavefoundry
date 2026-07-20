# Give target-code parser failures their real filename

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-give-target-code-parser-failures-their-real-filename`
Kind: `successful_pattern`
Confidence: 0.9
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1p9p6-bug python-parse-filename-and-invalid-escape:f02ba5f503bd6609`
Validation: promote
Validated by: agent
Action delta: Pass the real path into target-code parser calls and keep a sweep test for warning classes that can otherwise lose file attribution.
Validation rationale: Current chunker and graph paths still rely on filename-aware AST parsing, which materially improves build diagnostics and regression localization.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When parsing target Python during indexing or chunking, pass the repository-relative filename into ast.parse and fix warning-producing source at its origin; pair the fix with a sweep guard so invalid escapes or parse diagnostics cannot regress into pathless build noise.

## Evidence

- `1p9p6-bug python-parse-filename-and-invalid-escape`
- `1p9pe`
- `.wavefoundry/framework/scripts/chunker.py:516`
- `.wavefoundry/framework/scripts/graph_indexer.py:10805`

## Targets

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/graph_indexer.py`
