# Repaired defect windows-handoff-uses-pythonw

Owner: Engineering
Status: superseded
Last verified: 2026-07-30

Memory ID: `1ty3x-mem repaired-defect-windows-handoff-uses-pythonw`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-30
Updated: 2026-07-30
Source exploration cost: 1297806
Source event: `finding:1tz6l:windows-handoff-uses-pythonw`
Validation: rewrite
Validated by: agent
Action delta: Before changing Windows upgrade handoff, verify pythonw-to-console resolution through the public post_preflight path and keep normal interpreter controls.
Validation rationale: The source finding is durable, but the generated draft was too generic or targeted only the test carrier; this rewrite states the reusable mechanism and verified implementation targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1twwb-mem windows-detached-upgrade-handoff-must-use-a-console-interpre`
## Summary

Real defect fixed in wave 1tz6l: The required-AC defect was valid and the bounded repair was independently verified.

## Evidence

- `windows-handoff-uses-pythonw`
- `ev-windows-handoff-uses-pythonw-5`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/upgrade_extensions.py`
