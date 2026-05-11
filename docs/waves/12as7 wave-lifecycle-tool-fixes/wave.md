# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-08

wave-id: `12as7 wave-lifecycle-tool-fixes`
Title: Wave Lifecycle Tool Fixes

## Objective

Fix wave lifecycle tool bugs in wave-create scaffold and admit placement, and add a single-active-wave guard.

## Changes

Change ID: `12as3-bug wave-create-scaffold-and-admit-placement`
Change Status: `done`

Change ID: `12as6-enh single-active-wave-guard`
Change Status: `done`

Completed At: 2026-05-01

## Wave Summary

Two independent fixes to `server.py` wave-lifecycle tools: `12as3` fixes the `wave_create_wave` scaffold (literal `<date>` placeholder in `Last verified`) and `wave_add_change` section placement (blocks inserted before `## Dependencies` instead of inside `## Changes`); `12as6` adds a single-active-wave guard in `wave_prepare` (`another_wave_active` diagnostic with `wave_pause` recovery), extends `wave_pause` to actually transition wave status from `active` to `paused`, adds a resume path via `wave_prepare` on a paused wave (still honoring the guard), and changes `wave_current` to return all non-closed waves as `data.waves[]` (active first, then planned, then paused; paused entries carry `next_action: "resume_wave"`) — a hard-break envelope change with full in-tree migration. All discovered during `12as1` wave creation and context-switching on 2026-05-01.

## Journal Watchpoints

- **Both changes touch `server.py`** but edit different functions (`create_wave` / `wave_add_change_response` vs `wave_prepare_response`). Safe to parallelize but implement + test independently to keep diffs small.
- **`framework_edit_allowed` guard** must be flipped before any `server.py` edits; restore after. Each change lists the guard flip in its Tasks section.
- **`seed_edit_allowed` guard** required for `12as6` seed edits.
- **No functional dependency on `12as1 design-system-extraction`** — this wave can land first or in parallel; no file collisions.
- **Pre-fix workaround still required.** Until `12as3` ships, new wave scaffolds need manual `Last verified` fix-up and change blocks need manual relocation. This wave's own `wave.md` was hand-patched to land lint-clean — evidence of the bug, not a regression.
- **Single-active-wave guard (`12as6`) is not retroactive.** Existing multi-active-wave states (if any) remain; the guard only fires at the transition.
- **`12as6` scope expanded** to also cover `wave_pause` status transition (`active → paused`) and resume via `wave_prepare` (which still enforces the guard). Without the pause transition the guard's recovery message ("Pause it before preparing") would not actually work — 2026-05-01 operator hit this during `12ahv → 12as1` context-switch and manually edited wave.md.
- **Resume still guarded.** Resuming a paused wave while another wave is active returns the same `another_wave_active` diagnostic. The guard keys on "is any other wave active?", not on the target's current status.
- **`wave_current` breaking envelope change.** `12as6` removes `data.wave` and adds `data.waves[]`. Every in-tree reader (server code, tests, prompts, seeds, AGENTS.md) migrates in the same change. Historical journals and wave records under `docs/agents/journals/**` and `docs/waves/**` remain frozen. An AC-20 grep test asserts the migration is complete.
- **`resume_wave` is a next-action label, not a tool.** Paused entries in `wave_current.data.waves[]` get `next_action: "resume_wave"`; underlying transition is still `wave_prepare(wave_id, mode="create")` on the paused wave. Prompt docs and AGENTS.md document the mapping.

## Review Evidence

Review date: 2026-05-01

- code-reviewer sign-off (12as3, 12as6): approved 2026-05-01.
- qa-reviewer sign-off (12as3, 12as6): approved 2026-05-01. 429/429 framework tests pass.
- architecture-reviewer sign-off (12as3, 12as6): approved 2026-05-01 after two one-line architecture doc updates.
- docs-contract-reviewer sign-off (12as3, 12as6): approved 2026-05-01.


| Lane            | Status | Notes                                                                                                                                                                                                     |
| --------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| code-review     | ✅ pass | **12as3:** helper `_insert_change_block_into_changes_section` is pure, correctly handles legacy / missing-section / empty-section branches. Regex `^## Changes[ \t]*\n` correctly anchored in MULTILINE. **12as6:** all 19 requirements implemented; `_find_other_active_wave` uses path-resolve equality; guard aggregates with lint/garden (no short-circuit); pause status write ordered before handoff write; `wave_current` envelope rewrite preserves drift detection for active entry only. Minor observations noted (`current_status` empty-string edge case on malformed wave.md, weak assertion on lint-accepts-paused — none blocking). |
| qa-review       | ✅ pass | **12as3:** 6 tests cover AC-1 through AC-6 (AC-5 legacy round-trip genuinely exercises the buggy pre-existing layout; not just test-name-level). **12as6:** 21 tests map 1:1 to AC-1 through AC-21 (including AC-11b; AC-6 aggregation and AC-21 `wave_audit` envelope tests added after first qa pass flagged them as missing). `test_no_stale_data_wave_readers_in_source_and_prompts` uses correct `parents[4]` path and actively scans — no longer skipped. 429/429 framework tests pass (zero skips). |
| architecture    | ✅ pass | 12as3 is N/A (pure bug fix, no contract impact). 12as6 required two architecture doc updates: `docs/architecture/current-state.md` (MCP tool table note for `wave_current` envelope, `wave_prepare` guard, `wave_pause` transition) and `docs/architecture/data-and-control-flow.md` (sections 5 and 7 updated). No new ADR required; change doc Decision Logs are authoritative for the lifecycle vocabulary and envelope contract. Domain-map does not enumerate statuses, so no change there. |
| docs-contract   | ✅ pass | `docs/prompts/prepare-wave.prompt.md` — Single-Active-Wave Rule + recovery flow added. `docs/prompts/pause-wave.prompt.md` — rewrote Steps, added status-transition semantics table, resume instructions, paused-in-wave_current note. `AGENTS.md` — added `wave_current` envelope note and single-active-wave rule paragraph. Prompt surface manifest not affected (no new shortcut phrases). Seeds unchanged — tool-envelope details are prompt-doc scope, not seed scope for this change. |


**Overall: PASS** — Wave 12as7 passes all review lanes. Both changes are ready for closure.

## Dependencies

- No external wave dependencies.
- No dependency on `12as1 design-system-extraction` — can land in any order.
