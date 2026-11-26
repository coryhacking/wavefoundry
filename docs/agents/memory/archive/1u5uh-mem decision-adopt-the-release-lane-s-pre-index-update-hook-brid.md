# Decision: Adopt the release lane's `pre_index_update` hook bridge as…

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1u5uh-mem decision-adopt-the-release-lane-s-pre-index-update-hook-brid`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-01
Updated: 2026-11-25
Source exploration cost: 539855
Source event: `decision-log:1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success:de9adc277363c680`
Validation: promote
Validated by: agent
Action delta: To make an upgrade-BEHAVIOR fix effective on the upgrade that installs it, put the new logic in the new pack's upgrade_extensions hook that the old parent already dispatches before the affected phase; keep it self-contained (stdlib plus module-local, ctx.root only), fail-safe inside the hook body, and idempotent.
Validation rationale: Field-proven the day after delivery: the pg1a-initiated pg5l upgrade published Phase 4a cleanly under the OLD parent because the new pack's pre_index_update bridge established the publisher grant, the first upgrade-behavior fix in three releases to work on its own installing upgrade. The mechanics in the draft are accurate against the tree (zip-borne module load at upgrade_wavefoundry.py:944-984, hook dispatch before Phase 4, shipped since v1.4.0). Target upgrade_wavefoundry.py is where the dispatch lives; the bridge body is in upgrade_extensions.py, both named in the summary.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Checked at: 2026-11-25T16:09:19Z
Check note: Item 7 review: encoded elsewhere. Implemented: upgrade_extensions.py:3568 pre_index_update bridges the publisher grant, the parent calls it (upgrade_wavefoundry.py:6549, 6823, 7234), and tests/test_old_parent_publication.py::OldParentPublicationTests::test_archived_main_and_new_hook_inventory_once_and_do_not_touch_manual_run runs an archived old parent main against the new hooks and asserts the h.
Check flags: target_churn, target_not_canonical
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, encoded in Implemented: upgrade_extensions.py:3568 pre_index_update bridges the publisher grant, the parent calls it (upgrade_wavefoundry.py:6549, 6823, 7234), and tests/test_old_parent_publication.py::OldParentPublicationTests::test_archived_main_and_new_hook_in.
Archive path: `docs/agents/memory/archive/1u5uh-mem decision-adopt-the-release-lane-s-pre-index-update-hook-brid.md`

## Summary

Decision (wave 1u44n): Adopt the release lane's `pre_index_update` hook bridge as an ADDITIVE requirement. Rationale: `upgrade_extensions` is loaded from inside the NEW pack (`upgrade_wavefoundry.py:944-984`) while the parent runner is still old code, and the old parent already calls the hook at `:4274` immediately before the Phase 4 dispatch, so acting there makes the fix effective on the installing upgrade and closes the old-code window for once.

## Evidence

- `1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success`
- `1u44n`

## Targets

- `upgrade_wavefoundry.py`
