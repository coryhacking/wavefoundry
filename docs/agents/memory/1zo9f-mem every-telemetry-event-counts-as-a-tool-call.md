# Every telemetry event counts as a tool call

Owner: Engineering
Status: active
Last verified: 2026-10-03

Memory ID: `1zo9f-mem every-telemetry-event-counts-as-a-tool-call`
Kind: `decision`
Confidence: 0.8
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 102695
Source event: `decision-log:1zltz-enh override-response-cost-recording:46d131fd1338c533`
Validation: promote
Validated by: agent
Action delta: Before adding a telemetry event on an existing tool path, check that stage counts are COUNT(*) over telemetry_event and that the event will not inflate Tool calls.
Validation rationale: 1zls8 readiness found a zero-delta override cost event would double Tool calls for every delegating override, because context_efficiency counts events. The durable rule is the counting semantics.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

context_efficiency counts stage tool calls as COUNT(*) over telemetry_event, so any extra event on a tool path raises Tool calls. Override cost deltas are therefore recorded only when the delta is above zero (a non-delegating override records once); marking events as non-calls would need a schema column and a filter in every consumer.

## Evidence

- `1zltz-enh override-response-cost-recording`
- `1zls8`

## Targets

- `context_efficiency.py`
- `wf_server/server_impl.py`
