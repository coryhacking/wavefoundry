# Upgrade refusal messages must name a marker-clearing recovery

Owner: Engineering
Status: active
Last verified: 2026-07-27

Memory ID: `1tn45-mem upgrade-refusal-messages-must-name-a-marker-clearing-recover`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-07-27
Updated: 2026-07-27
Source exploration cost: 741008
Source event: `finding:1tomw:DF3-sidecar-refusal-recovery-message-dead-end`
Validation: promote
Validated by: agent
Action delta: When adding or editing a retained failed_phase refusal gate in upgrade_wavefoundry.py, trace the printed recovery instruction to a terminal that actually clears the marker before shipping the message.
Validation rationale: The generated candidate carries only the reverification rationale, not the reusable lesson. The underlying defect is durable: wave 1tomw's review_sidecar_cleanup refusal branch printed re-run the requested phase, but the same gate refused those phases while the marker was retained and no path outside a full-upgrade preflight cleared it, so the instruction looped forever; the working recovery (preflight stale-lock reclamation minting failed_phase None) was only discoverable by tracing. Verified the finding chain in events.jsonl and the current amended message plus its three consistency carriers.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1tomw delivery review: the review_sidecar_cleanup refusal branch in _unrecovered_review_or_docs_gate told operators to re-run the requested phase, but that gate refuses every publication verb while failed_phase is retained and nothing on those paths clears the marker; only a full-upgrade re-run does (preflight stale-lock reclamation, then write_upgrade_lock mints failed_phase None). When a gate retains a failed_phase marker, trace the printed recovery instruction to a terminal that verifiably clears it, and keep the wording consistent across the gate message, phase_cleanup, _finalize_failed_upgrade, and the MCP tool-surface spec.

## Evidence

- `DF3-sidecar-refusal-recovery-message-dead-end`
- `ev-df3-sidecar-refusal-recovery-message-dead-end-3`
- `1tomw`

## Targets

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
