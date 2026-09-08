# Repaired defect RED-RDY-CLOSE-1

Owner: Engineering
Status: superseded
Last verified: 2026-09-07

Memory ID: `1xfpy-mem repaired-defect-red-rdy-close-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-07
Updated: 2026-09-07
Source exploration cost: 2181430
Source event: `finding:1xdlx:RED-RDY-CLOSE-1`
Validation: rewrite
Validated by: agent
Action delta: During Close wave, keep session-handoff truthful as active and awaiting closure through review and dry-run; write the idle/last-closed form only after wf_close_wave succeeds.
Validation rationale: RED-RDY-CLOSE-1 proved that pre-writing a closed/idle handoff contradicts the authoritative implementing wave and can misroute the next session. The generated target docs_lint.py is inaccurate; the durable targets are the close workflow and session handoff. This supplements the closure checklist by making the mutation order explicit.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1xhix-mem write-the-idle-handoff-only-after-the-close-mutation-succeed`
## Summary

Real defect fixed in wave 1xdlx: The bounded repair fully resolves the premature closure claim while preserving truthful pre-close state.

## Evidence

- `RED-RDY-CLOSE-1`
- `ev-red-rdy-close-1-3`
- `1xdlx`

## Targets

- `docs_lint.py`
