# Every telemetry event counts as a tool call

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24brn-mem every-telemetry-event-counts-as-a-tool-call`
Kind: `decision`
Confidence: 0.8
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 102695
Supersedes: `1zo9f-mem every-telemetry-event-counts-as-a-tool-call`
Checked at: 2026-11-26T06:32:44Z
Check note: The context-efficiency counter includes telemetry calls. Adding an event changes the observed stage count. Reviewed .wavefoundry/framework/scripts/wf_server/server_impl.py:19036.
Check flags: none

## Summary

When adding a telemetry event on an existing tool path, expect it to raise the stage's Tool calls: .wavefoundry/framework/scripts/context_efficiency.py counts calls as COUNT(*) over telemetry_event for the wave and stage. Record extra events only when they carry cost, as the override cost path in wf_server/server_impl.py does with 'if delta > 0'. Why: 1zls8 readiness found a zero-delta override cost event would double Tool calls for every delegating override; marking events as non-calls would need a schema column and a filter in every consumer.

## Evidence

- `1zltz-enh override-response-cost-recording`
- `1zls8`

## Targets

- `.wavefoundry/framework/scripts/context_efficiency.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
