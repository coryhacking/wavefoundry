# Decision: Adopt the release lane's `pre_index_update` hook bridge as…

Owner: Engineering
Status: active
Last verified: 2026-08-01

Memory ID: `1u5uh-mem decision-adopt-the-release-lane-s-pre-index-update-hook-brid`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-01
Updated: 2026-08-01
Source exploration cost: 539855
Source event: `decision-log:1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success:de9adc277363c680`
Validation: promote
Validated by: agent
Action delta: To make an upgrade-BEHAVIOR fix effective on the upgrade that installs it, put the new logic in the new pack's upgrade_extensions hook that the old parent already dispatches before the affected phase; keep it self-contained (stdlib plus module-local, ctx.root only), fail-safe inside the hook body, and idempotent.
Validation rationale: Field-proven the day after delivery: the pg1a-initiated pg5l upgrade published Phase 4a cleanly under the OLD parent because the new pack's pre_index_update bridge established the publisher grant, the first upgrade-behavior fix in three releases to work on its own installing upgrade. The mechanics in the draft are accurate against the tree (zip-borne module load at upgrade_wavefoundry.py:944-984, hook dispatch before Phase 4, shipped since v1.4.0). Target upgrade_wavefoundry.py is where the dispatch lives; the bridge body is in upgrade_extensions.py, both named in the summary.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
## Summary

Decision (wave 1u44n): Adopt the release lane's `pre_index_update` hook bridge as an ADDITIVE requirement. Rationale: `upgrade_extensions` is loaded from inside the NEW pack (`upgrade_wavefoundry.py:944-984`) while the parent runner is still old code, and the old parent already calls the hook at `:4274` immediately before the Phase 4 dispatch, so acting there makes the fix effective on the installing upgrade and closes the old-code window for once.

## Evidence

- `1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success`
- `1u44n`

## Targets

- `upgrade_wavefoundry.py`
