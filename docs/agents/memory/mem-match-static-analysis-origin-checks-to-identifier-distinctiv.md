# Match static-analysis origin checks to identifier distinctiveness

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-match-static-analysis-origin-checks-to-identifier-distinctiv`
Kind: `successful_pattern`
Confidence: 0.95
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1p9q7-enh di-signal-ast-and-language-expansion:01f5decffc4784ba`
Validation: promote
Validated by: agent
Action delta: Choose positive or negative origin checks according to identifier collision risk before emitting framework-specific static-analysis edges.
Validation rationale: The current graph extractor still applies this distinction across multiple sinks, and it prevents both alias under-detection and generic-name overreach.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When extracting framework idioms, use a negative origin check for distinctive canonical names so unbound or aliased idioms can still match unless proven to be an impostor, and require a positive library origin for generic names that are likely to collide.

## Evidence

- `1p9q7-enh di-signal-ast-and-language-expansion`
- `1p9q8`
- `.wavefoundry/framework/scripts/graph_indexer.py:6189`
- `.wavefoundry/framework/scripts/graph_indexer.py:11859`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`

## Targets

- `.wavefoundry/framework/scripts/graph_indexer.py`
