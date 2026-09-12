# Repaired defect PERF-CURRENT-1

Owner: Engineering
Status: rejected
Last verified: 2026-09-11

Memory ID: `1xppo-mem repaired-defect-perf-current-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-11
Updated: 2026-09-11
Source exploration cost: 2519546
Source event: `finding:1xny6:PERF-CURRENT-1`
Validation: reject
Validated by: agent
Action delta: Replace this generated probe-target record with a correctly targeted timing lesson.
Validation rationale: The generated targets are disposable /tmp probes misread as repository files; they do not exist in the tree. Current production and test anchors were verified independently. The rewrite API refused because it validates missing original targets before corrected targets, so preserve this rejection and write the correctly anchored lesson separately.
Evidence verified: true
Current target verified: false
Canonical overlap: none
## Summary

Real defect fixed in wave 1xny6: Executed controls detect original timing defect; repaired positive controls pass.

## Evidence

- `PERF-CURRENT-1`
- `ev-perf-current-1-3`
- `1xny6`

## Targets

- `tmp/1xny6-perf-production-mutant.py`
- `tmp/1xny6-perf-timing-mutant.py`
