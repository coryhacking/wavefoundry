# Write the idle handoff only after the close mutation succeeds

Owner: Engineering
Status: active
Last verified: 2026-09-07

Memory ID: `1xhix-mem write-the-idle-handoff-only-after-the-close-mutation-succeed`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-09-07
Updated: 2026-09-07
Source exploration cost: 2181430
Source event: `finding:1xdlx:RED-RDY-CLOSE-1`
Validation: promote
Validated by: agent
Action delta: During Close wave, keep session-handoff truthful as active and awaiting closure through review and dry-run; write the idle/last-closed form only after wf_close_wave succeeds.
Validation rationale: RED-RDY-CLOSE-1 proved that pre-writing a closed/idle handoff contradicts the authoritative implementing wave and can misroute the next session. The generated target docs_lint.py is inaccurate; the durable targets are the close workflow and session handoff. This supplements the closure checklist by making the mutation order explicit.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

A Close wave review must not claim the wave is closed, idle, or operator-authorized in session-handoff while wave.md remains implementing. Keep the pre-close handoff active and pending; after wf_close_wave succeeds, update the handoff to the last-closed idle form.

## Evidence

- `RED-RDY-CLOSE-1`
- `ev-red-rdy-close-1-3`
- `1xdlx`

## Targets

- `docs/prompts/close-wave.prompt.md`
- `docs/agents/session-handoff.md`
