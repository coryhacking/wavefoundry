# Fragile: server_impl.py context-efficiency instrumentation

Owner: Engineering
Status: active
Last verified: 2026-07-20

Memory ID: `mem-fragile-server-impl-py-context-efficiency-instrumentation`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-07-20
Updated: 2026-07-20
Source event: `repeated-repairs:1t3ek:run_tests.py`
Validation: promote
Validated by: agent
Action delta: Before editing the context-efficiency instrumentation in server_impl.py (cost wrapper, artifact/state extractors, retrieval censuses), verify field names against the canonical response builders and confirm with a live post-reload probe, not hand-modeled fixtures.
Validation rationale: The drafted candidate misattributed the repair target: its three evidence findings repaired the credit instrumentation in server_impl.py (per-artifact floor, replay identity, risk_score request completeness), and run_tests.py appears only as the verification command inside command_or_fixture strings. The underlying fragile-area signal is real, on the wrong file.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

The credit instrumentation in server_impl.py (cost wrapper, artifact and state-source extractors, retrieval censuses) was repaired four times during wave 1t3ek: a hover census read the wrong envelope field, credit floored on the artifact aggregate instead of per artifact, replayed artifact calls re-credited under uuid event ids, and code_risk_score recorded an incomplete request. Common failure mode: hand-modeled response shapes and aggregate shortcuts that hermetic fixtures echo. Verify against canonical response builders and a live post-reload probe before trusting edits here.

## Evidence

- `hover-census-keys-path-but-envelope-names-file`
- `artifact-credit-floors-aggregate-not-per-artifact`
- `artifact-replay-uuid-event-ids-recredit`
- `risk-score-request-arguments-incomplete`
- `1t3ek`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
