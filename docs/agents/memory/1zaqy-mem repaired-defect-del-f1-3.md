# Repaired defect DEL-F1

Owner: Engineering
Status: superseded
Last verified: 2026-09-29

Memory ID: `1zaqy-mem repaired-defect-del-f1-3`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 164401
Source event: `finding:1za2y:DEL-F1`
Validation: rewrite
Validated by: agent
Action delta: Before narrowing any pid liveness check on background-build.pid, check who stamps the file: wf setup and wf update-indexes stamp the wf_cli.py process pid.
Validation rationale: DEL-F1 was a regression found only in delivery: the new builder-only predicate called a live wf setup completed because setup_index.main runs in-process in wf_cli.py and pre-stamps its own pid. Tests had been rewritten to a setup_index.py-shaped process, fitting the predicate instead of the system.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zb26-mem background-build-pid-can-hold-the-wf-cli-pid-not-a-builder`

## Summary

Real defect fixed in wave 1za2y: Resolved.

## Evidence

- `DEL-F1`
- `ev-del-f1-3`
- `1za2y`

## Targets

- `.wavefoundry/framework/scripts/wf_server/index_handlers.py`
