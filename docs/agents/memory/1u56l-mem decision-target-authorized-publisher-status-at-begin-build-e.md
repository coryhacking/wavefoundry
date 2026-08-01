# Decision: Target authorized-publisher status at `begin_build_epoch`,…

Owner: Engineering
Status: superseded
Last verified: 2026-08-01

Memory ID: `1u56l-mem decision-target-authorized-publisher-status-at-begin-build-e`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-01
Updated: 2026-08-01
Source exploration cost: 539855
Source event: `decision-log:1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success:6a407e4a30450334`
Validation: rewrite
Validated by: agent
Action delta: When index publication is refused during an upgrade, repair publisher authorization at begin_build_epoch (three disjuncts: owner pid, staged receipt, value-bound publisher_grant token), never the lock's current_phase; the refusal fires on checkpoint presence at any phase.
Validation rationale: The drafted summary is probe-verified but frozen at the plan stage: it names only the two pre-existing disjuncts (owner pid, staged receipt), while the delivered fix added the third, a value-bound publisher_grant token minted into the checkpoint and matched against WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN in the child env, with the detached background child stripped. A reader following the draft would look for two disjuncts and misread the third as foreign code. Rewritten to the delivered mechanism with the phase-independence fact retained.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1u4qe-mem publisher-authorization-at-begin-build-epoch-is-the-repair-p`
## Summary

Decision (wave 1u44n): Target authorized-publisher status at `begin_build_epoch`, not the lock's `current_phase`. Rationale: Probe-verified: `publication_checkpoint_reason` returns a refusal for any existing checkpoint at any phase, so advancing the phase changes only the message text. Only the `owner` pid or the staged-receipt disjunct at `index_state_store.py:2268-2276` admits a publisher.

## Evidence

- `1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success`
- `1u44n`

## Targets

- `index_state_store.py`
