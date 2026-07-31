# Windows detached upgrade handoff must use a console interpreter

Owner: Engineering
Status: active
Last verified: 2026-07-30

Memory ID: `1twwb-mem windows-detached-upgrade-handoff-must-use-a-console-interpre`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-07-30
Updated: 2026-07-30
Source exploration cost: 1297806
Source event: `finding:1tz6l:windows-handoff-uses-pythonw`
Validation: promote
Validated by: agent
Action delta: Before changing Windows upgrade handoff, verify pythonw-to-console resolution through the public post_preflight path and keep normal interpreter controls.
Validation rationale: The source finding is durable, but the generated draft was too generic or targeted only the test carrier; this rewrite states the reusable mechanism and verified implementation targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Reusing sys.executable can propagate pythonw.exe into a detached upgrade child, which has no console stdio contract. Resolve pythonw.exe to its console sibling for the handoff while leaving normal interpreters unchanged, and verify the public post_preflight callsite rather than only the helper.

## Evidence

- `windows-handoff-uses-pythonw`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`
