# Decision: Park as its own plan rather than repair inside wave `1x6ti`.

Owner: Engineering
Status: rejected
Last verified: 2026-09-06

Memory ID: `1xcb3-mem decision-park-as-its-own-plan-rather-than-repair-inside-wave`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-06
Updated: 2026-09-06
Source exploration cost: 3033705
Source event: `decision-log:1x81x-bug oversized-table-row-wrap-emits-header-only-chunk:27ab14a9b0e1374f`
Validation: reject
Validated by: agent
Action delta: No durable future action: the choice only records why this defect was moved out of the already-scoped wave 1x6ti.
Validation rationale: The cited decision and current chunker target are verified, but the lesson is wave-specific scheduling history rather than a reusable technical or operator rule. The repaired defect classes are already preserved in typed review evidence and regression tests.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

Decision (wave 1xa00): Park as its own plan rather than repair inside wave `1x6ti`.. Rationale: `chunker.py` is outside that wave's review targets and the fix moves `CHUNKER_VERSION`..

## Evidence

- `1x81x-bug oversized-table-row-wrap-emits-header-only-chunk`
- `1xa00`

## Targets

- `chunker.py`
