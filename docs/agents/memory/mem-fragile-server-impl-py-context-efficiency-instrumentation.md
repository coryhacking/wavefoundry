# Fragile: server_impl.py context-efficiency instrumentation

Owner: Engineering
Status: active
Last verified: 2026-07-21

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

FIFTH repair (wave 1t59p, 2026-07-21): the 1t3ek per-artifact-floor repair itself left the artifact extractors' early returns int-typed while the wrapper began iterating them; the observational recorder swallowed the TypeError and silently dropped the ENTIRE debit row for every non-create `wf_review_evidence` response since 1t3ek. Caught only by a live post-reload row census (a control tool recorded; the target did not). Corollary to the action delta: an observational wrapper that swallows failures converts type mismatches into silently missing data — pin the producer/consumer type contract with a test that evaluates the consumer's exact expression against every real envelope shape.

The credit instrumentation in server_impl.py (cost wrapper, artifact and state-source extractors, retrieval censuses) was repaired four times during wave 1t3ek: a hover census read the wrong envelope field, credit floored on the artifact aggregate instead of per artifact, replayed artifact calls re-credited under uuid event ids, and code_risk_score recorded an incomplete request. Common failure mode: hand-modeled response shapes and aggregate shortcuts that hermetic fixtures echo. Verify against canonical response builders and a live post-reload probe before trusting edits here.

## Evidence

- `hover-census-keys-path-but-envelope-names-file`
- `artifact-credit-floors-aggregate-not-per-artifact`
- `artifact-replay-uuid-event-ids-recredit`
- `risk-score-request-arguments-incomplete`
- `1t3ek`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
