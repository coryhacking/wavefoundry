# Decision: Provisioning is a **code script** (compute in `lifecycle_id…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-provisioning-is-a-code-script-compute-in-lifecycle-`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9pt-enh collision-resistant-lifecycle-ids-daily-entropy:9aafccccc72a2dcf`
Validation: reject
Validated by: agent
Action delta: None; use the current lifecycle ID script and rendered install or upgrade contracts.
Validation rationale: Machine-owned lifecycle provisioning is now canonical executable behavior, so a memory would duplicate the source of truth.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p9q0): Provisioning is a **code script** (compute in `lifecycle_id.py`, orchestrate `materialize_lifecycle_policy` in `upgrade_wavefoundry.py`), called by the seeds — NOT agent prose.. Rationale: Operator directive + prepare-council F2: today provisioning is agent-driven (`seed-011` `random.randint`, `seed-160` `2020` backfill), untestable and RNG. A script makes AC-4/AC-7 unit-testable, deterministic, idempotent, and atomic; the secrets Phase-2b materialization is the precedent..

## Evidence

- `1p9pt-enh collision-resistant-lifecycle-ids-daily-entropy`
- `1p9q0`

## Targets

- `lifecycle_id.py`
- `upgrade_wavefoundry.py`
