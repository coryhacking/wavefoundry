# Publisher authorization at begin_build_epoch is the repair point, never the phase value

Owner: Engineering
Status: active
Last verified: 2026-08-01

Memory ID: `1u4qe-mem publisher-authorization-at-begin-build-epoch-is-the-repair-p`
Kind: `decision`
Confidence: 0.8
Created: 2026-08-01
Updated: 2026-08-01
Source exploration cost: 539855
Source event: `decision-log:1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success:6a407e4a30450334`
Validation: promote
Validated by: agent
Action delta: When index publication is refused during an upgrade, repair publisher authorization at begin_build_epoch (three disjuncts: owner pid, staged receipt, value-bound publisher_grant token), never the lock's current_phase; the refusal fires on checkpoint presence at any phase.
Validation rationale: The drafted summary is probe-verified but frozen at the plan stage: it names only the two pre-existing disjuncts (owner pid, staged receipt), while the delivered fix added the third, a value-bound publisher_grant token minted into the checkpoint and matched against WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN in the child env, with the detached background child stripped. A reader following the draft would look for two disjuncts and misread the third as foreign code. Rewritten to the delivered mechanism with the phase-independence fact retained.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1u44n, probe-verified twice: publication_checkpoint_reason refuses index_build for ANY existing upgrade checkpoint at ANY current_phase value, so advancing the phase changes only the refusal text. Admission happens only through the disjuncts in index_state_store.begin_build_epoch, which after 1u44n are three: owner pid (checkpoint pid equals caller pid), staged upgrade child (non-empty WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT, memory path), and the value-bound publisher grant (env WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN exactly matching the checkpoint's recorded publisher_grant; minted per run, stripped from detached background children, dies with the checkpoint). Any future refusal repair targets these disjuncts; changing the lock's current_phase is a refuted design.

## Evidence

- `1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success`
- `1u44n`
- `index_state_store.py begin_build_epoch disjuncts`
- `code-lane refutation probe and delivery probes 2026-07-31 and 2026-08-01`

## Targets

- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/publication_control.py`
