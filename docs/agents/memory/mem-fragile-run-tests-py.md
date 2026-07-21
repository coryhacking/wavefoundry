# Fragile: run_tests.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-20

Memory ID: `mem-fragile-run-tests-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-20
Updated: 2026-07-20
Source exploration cost: 92526
Source event: `repeated-repairs:1t3ek:run_tests.py`
Validation: rewrite
Validated by: agent
Action delta: Before editing the context-efficiency instrumentation in server_impl.py (cost wrapper, artifact/state extractors, retrieval censuses), verify field names against the canonical response builders and confirm with a live post-reload probe, not hand-modeled fixtures.
Validation rationale: The drafted candidate misattributed the repair target: its three evidence findings repaired the credit instrumentation in server_impl.py (per-artifact floor, replay identity, risk_score request completeness), and run_tests.py appears only as the verification command inside command_or_fixture strings. The underlying fragile-area signal is real, on the wrong file.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-fragile-server-impl-py-context-efficiency-instrumentation`
## Summary

run_tests.py required 3 separate repairs during wave 1t3ek; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `artifact-credit-floors-aggregate-not-per-artifact`
- `artifact-replay-uuid-event-ids-recredit`
- `risk-score-request-arguments-incomplete`
- `1t3ek`

## Targets

- `run_tests.py`
