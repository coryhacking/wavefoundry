# Publisher authorization at begin_build_epoch is the repair point, never the phase value

Owner: Engineering
Status: active
Last verified: 2026-10-16

Memory ID: `1u4qe-mem publisher-authorization-at-begin-build-epoch-is-the-repair-p`
Kind: `decision`
Confidence: 0.8
Created: 2026-08-01
Updated: 2026-10-16
Source exploration cost: 539855
Source event: `decision-log:1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success:6a407e4a30450334`
Validation: promote
Validated by: agent
Action delta: When index publication is refused during an upgrade, inspect owner-pid or value-bound publisher_grant authorization at begin_build_epoch, never change the lock's current_phase to bypass it; checkpoint presence blocks an unrelated publisher at every phase.
Validation rationale: The drafted summary is probe-verified but frozen at the plan stage: it names only the two pre-existing disjuncts (owner pid, staged receipt), while the delivered fix added the third, a value-bound publisher_grant token minted into the checkpoint and matched against WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN in the child env, with the detached background child stripped. A reader following the draft would look for two disjuncts and misread the third as foreign code. Rewritten to the delivered mechanism with the phase-independence fact retained.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1u44n established that publication_checkpoint_reason refuses an unrelated index_build for an existing upgrade checkpoint at every current_phase value; advancing the phase changes only the refusal text. Current-target correction in wave 20t73: index_state_store.begin_build_epoch admits the checkpoint owner pid or a value-bound publisher grant (WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN exactly matching the checkpoint's publisher_grant; minted per run, stripped from detached background children, and invalid when the checkpoint is removed). The staged-receipt authority is removed. A refusal repair must address publisher authorization, never change current_phase to bypass it. The validation rationale and evidence below retain the original 1u44n history.

## Evidence

- `1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success`
- `1u44n`
- `index_state_store.py begin_build_epoch disjuncts`
- `code-lane refutation probe and delivery probes 2026-07-31 and 2026-08-01`

## Targets

- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/publication_control.py`
