# Repaired defect DF3-sidecar-refusal-recovery-message-dead-end

Owner: Engineering
Status: superseded
Last verified: 2026-07-27

Memory ID: `1topv-mem repaired-defect-df3-sidecar-refusal-recovery-message-dead-en`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-27
Updated: 2026-07-27
Source exploration cost: 741008
Source event: `finding:1tomw:DF3-sidecar-refusal-recovery-message-dead-end`
Validation: rewrite
Validated by: agent
Action delta: When adding or editing a retained failed_phase refusal gate in upgrade_wavefoundry.py, trace the printed recovery instruction to a terminal that actually clears the marker before shipping the message.
Validation rationale: The generated candidate carries only the reverification rationale, not the reusable lesson. The underlying defect is durable: wave 1tomw's review_sidecar_cleanup refusal branch printed re-run the requested phase, but the same gate refused those phases while the marker was retained and no path outside a full-upgrade preflight cleared it, so the instruction looped forever; the working recovery (preflight stale-lock reclamation minting failed_phase None) was only discoverable by tracing. Verified the finding chain in events.jsonl and the current amended message plus its three consistency carriers.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1tn45-mem upgrade-refusal-messages-must-name-a-marker-clearing-recover`
## Summary

Real defect fixed in wave 1tomw: Fresh independent architecture-reviewer context verified the message, carrier consistency, and the working recovery terminal; repair complete, clearing the architecture-reviewer lane.

## Evidence

- `DF3-sidecar-refusal-recovery-message-dead-end`
- `ev-df3-sidecar-refusal-recovery-message-dead-end-3`
- `1tomw`

## Targets

- `upgrade_wavefoundry.py`
