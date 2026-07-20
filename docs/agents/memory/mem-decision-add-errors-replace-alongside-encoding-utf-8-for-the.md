# Decision: Add `errors="replace"` alongside `encoding="utf-8"` for the…

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-decision-add-errors-replace-alongside-encoding-utf-8-for-the`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9iy-bug dev-test-infra-windows-hardening:6698822b47133610`
Validation: rewrite
Validated by: agent
Action delta: Use tolerant UTF-8 decoding at framework subprocess-capture boundaries so diagnostic bytes cannot crash the orchestrator.
Validation rationale: The behavior has since become a shared subprocess utility contract, confirming the lesson while changing its current target.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-subprocess-diagnostics-must-not-fail-utf-8-decoding`
## Summary

Decision (wave 1p9j0): Add `errors="replace"` alongside `encoding="utf-8"` for the `run_tests.py` capture.. Rationale: Matches the existing timeout-branch replace-decode (`:235`–`:236`); a stray byte must never crash the runner..

## Evidence

- `1p9iy-bug dev-test-infra-windows-hardening`
- `1p9j0`

## Targets

- `run_tests.py`
