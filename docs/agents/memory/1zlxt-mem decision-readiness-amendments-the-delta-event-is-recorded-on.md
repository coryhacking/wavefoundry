# Decision: Readiness amendments: the delta event is recorded only when…

Owner: Engineering
Status: superseded
Last verified: 2026-10-03

Memory ID: `1zlxt-mem decision-readiness-amendments-the-delta-event-is-recorded-on`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 102695
Source event: `decision-log:1zltz-enh override-response-cost-recording:46d131fd1338c533`
Validation: rewrite
Validated by: agent
Action delta: Before adding a telemetry event on an existing tool path, check that stage counts are COUNT(*) over telemetry_event and that the event will not inflate Tool calls.
Validation rationale: 1zls8 readiness found a zero-delta override cost event would double Tool calls for every delegating override, because context_efficiency counts events. The durable rule is the counting semantics.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zo9f-mem every-telemetry-event-counts-as-a-tool-call`

## Summary

Decision (wave 1zls8): Readiness amendments: the delta event is recorded only when the delta is greater than 0 (a non-delegating override records its request and full response as the single event; a zero delta records nothing), and a delegating override that adds fields counts as two events in **Tool calls**, pinned by AC-9; only exempt cores add to the scope; the `ContextVar` is captured at wrapper build time; `core_handler` must be called on the calling thread; `_EXTENSION_OVERRIDE_DELTAS` is named and cleared at install start and on install failure; AC-10 executes the guard half of Requirement 6; the threat-model row is updated. Rationale: Readiness review findings B1, N7 and N8. `context_efficiency.py` counts stage calls as `COUNT(*)` over `telemetry_event`, so a zero-delta event per call doubled **Tool calls** for every delegating override. Counting two events only when the override really added response bytes needs no telemetry schema or query change; marking delta events would need a new `telemetry_event` column and a filter in every consumer that counts events, for a low-priority accounting gap.

## Evidence

- `1zltz-enh override-response-cost-recording`
- `1zls8`

## Targets

- `context_efficiency.py`
