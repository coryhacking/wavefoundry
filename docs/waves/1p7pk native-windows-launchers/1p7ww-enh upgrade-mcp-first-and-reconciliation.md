# MCP-first upgrade routing + minor-bump reconciliation recommendation

Change ID: `1p7ww-enh upgrade-mcp-first-and-reconciliation`
Change Status: `implementing`
Owner: Engineering
Status: planned
Last verified: 2026-06-25
Wave: `1p7pk native-windows-launchers`

## Rationale

Field feedback from real 1.9.0 upgrades surfaced two gaps in the **upgrade guidance** (the launcher mechanics themselves are fine):

1. **Agents default to a manual upgrade instead of the MCP tool.** The upgrade seed `160-upgrade-wavefoundry.prompt.md` (and its rendered `docs/prompts/upgrade-wavefoundry.prompt.md`) is a ~477-line *manual* procedure (unzip → `render_platform_surfaces` → `prune_framework` → reconcile → regenerate → docs gate → reload). `wave_upgrade` is mentioned only as a **parenthetical aside** in a step-0 sub-bullet and the reload step — there is no leading "when MCP is attached, drive this with `wave_upgrade()`" directive (the parity rule AGENTS.md gives for docs-lint: "prefer MCP over shell launchers"). And **`wave_upgrade`/`wave_upgrade_status` are absent from AGENTS.md's "Available tools" list** and `wave_upgrade_status` has no `docs/specs/mcp-tool-surface.md` entry — so they are not discoverable. An agent handed a long written procedure follows the procedure.

2. **A minor-version bump should recommend a reconciliation step, and agents didn't.** The mechanical reconciliation IS automatic — but only when `wave_upgrade()` runs its phases (prune pack-removed files like the nine retired `bin/*` wrappers via the MANIFEST diff; re-render surfaces → `bin/wf`; re-heal the `python` symlink). So an agent that went **manual** (gap 1) and skipped the prune/render phases leaves stale wrappers and unreconciled surfaces — exactly the observed symptom. The only thing the guidance flags as minor-bump-specific is the (recommend-only) Framework Config Review; there is **no minor-bump reconciliation recommendation** and no version-gated "these local surfaces referenced the changed/retired framework surface — reconcile them" callout.

Gap 1 is largely the root cause of gap 2: route agents to `wave_upgrade()` and the mechanical reconciliation happens automatically; then add an explicit minor-bump reconciliation recommendation for the local-surface part agents must still judge.

## Requirements

1. **MCP-first routing.** `seed-160` and the rendered `docs/prompts/upgrade-wavefoundry.prompt.md` **lead** with: "When the Wavefoundry MCP is attached, drive the upgrade with `wave_upgrade()` (poll/inspect with `wave_upgrade_status`); the manual sequence below is the **no-MCP CLI fallback** (`wf upgrade`)." Reframe the manual steps as "what the tool does for you / the fallback", mirroring AGENTS.md's "prefer MCP over shell launchers" parity for docs validation.
2. **Tool discoverability.** Add `wave_upgrade` + `wave_upgrade_status` to the "Available tools" list in `AGENTS.md` and `CLAUDE.md`; add a `wave_upgrade_status` entry to `docs/specs/mcp-tool-surface.md` (it exists in `server_impl.py` but is undocumented in the spec) — including when to call it (lock-state inspection before reload/restart).
3. **Minor-bump reconciliation recommendation.** The upgrade surfaces a reconciliation recommendation on **major/minor** bumps (a sibling to the existing `_config_review_recommendation_lines()` / `_is_major_or_minor_upgrade()` line in `upgrade_wavefoundry.py`): recommend a reconciliation pass — verify local surfaces/docs that referenced changed or **retired** framework surfaces are reconciled (e.g. 1.9.0's `bin/*` → `wf` cutover). `seed-160` + the prompt also instruct the agent to run/recommend it. Patch bumps do not surface it (parity with the config-review gate).
4. **Seed-first.** The behavior lives in `seed-160` (the canonical source) so target repos pick it up on their next upgrade; the rendered prompt is regenerated, not hand-drifted.

## Scope

**Problem statement:** The upgrade guidance doesn't route agents to `wave_upgrade()` (so they hand-roll a manual upgrade and skip its automatic reconciliation), and it never recommends a minor-bump reconciliation pass.

**In scope:**

- `seed-160-upgrade-wavefoundry.prompt.md` (gated seed edit) — MCP-first lead + the minor-bump reconciliation callout; regenerate the rendered prompt.
- `AGENTS.md` / `CLAUDE.md` tool lists + `docs/specs/mcp-tool-surface.md` `wave_upgrade_status` entry.
- `upgrade_wavefoundry.py` — the major/minor reconciliation recommendation line (reuse `_is_major_or_minor_upgrade`).
- Tests: the reconciliation recommendation fires on minor/major but not patch; a content check that the upgrade prompt/seed leads with the `wave_upgrade()` directive; seed→rendered parity.

**Out of scope:**

- The mechanical reconciliation itself (prune/render/symlink-heal) — already correct in `wave_upgrade()`'s phases.
- Changing `wave_upgrade`'s phase model or adding a dry-run.
- The `1p7pk` launcher mechanics (shipped).

**Depends on:** the `1p7tz` `wf` cutover (the 1.9.0 reconciliation example references `wf`).

## Acceptance Criteria

- [x] AC-1: `seed-160` + the rendered `docs/prompts/upgrade-wavefoundry.prompt.md` open the execution flow with an MCP-first directive — "when MCP is attached, run `wave_upgrade()`/`wave_upgrade_status`; the manual sequence is the no-MCP `wf upgrade` fallback." Verified by a content check. — `test_shipped_reference_docs.UpgradeMcpFirstGuidanceTests`.
- [x] AC-2: `wave_upgrade` + `wave_upgrade_status` appear in the `AGENTS.md` "Available tools" list; `docs/specs/mcp-tool-surface.md` has a `wave_upgrade_status` entry. (CLAUDE.md is a thin pointer that `@import`s AGENTS.md and has no standalone tools list — the authoritative list it imports is updated.) Verified by a content check.
- [x] AC-3: `upgrade_wavefoundry.py` surfaces a reconciliation recommendation on a major/minor bump (gated by `_is_major_or_minor_upgrade`), NOT on a patch; `seed-160`/the prompt instruct the agent to act on it. — `_reconciliation_recommendation_lines`; `test_upgrade_wavefoundry.ReconciliationRecommendationTests` (minor/major present, patch/downgrade/same/unparseable absent).
- [x] AC-4: the rendered prompt carries the same MCP-first + reconciliation directives as `seed-160` (the two are parallel-maintained — there is no automatic seed→prompt renderer; parity cross-checked by the content test); framework tests bytecode-free; `wave_validate`/`docs-lint` clean.

## Tasks

- [x] Open `seed_edit_allowed`; edit `seed-160` (MCP-first lead + minor-bump reconciliation callout); close the gate after.
- [x] Add `wave_upgrade`/`wave_upgrade_status` to the `AGENTS.md` tool list; add the `wave_upgrade_status` spec entry. (CLAUDE.md has no standalone tools list — it imports AGENTS.md.)
- [x] Add the major/minor reconciliation recommendation line to `upgrade_wavefoundry.py` (reuse `_is_major_or_minor_upgrade`).
- [x] Apply the same MCP-first + reconciliation directives to `docs/prompts/upgrade-wavefoundry.prompt.md` (parallel-maintained self-host surface; no auto seed→prompt renderer).
- [x] Tests (recommendation minor/major-gated; MCP-first content check; seed↔prompt parity) bytecode-free.
- [x] Changelog bullet.

## Agent Execution Graph


| Workstream    | Owner       | Depends On | Notes                                            |
| ------------- | ----------- | ---------- | ------------------------------------------------ |
| seed+prompt   | implementer | —          | MCP-first lead + minor-bump reconciliation       |
| tool-surface  | implementer | —          | AGENTS/CLAUDE tool lists + spec `wave_upgrade_status` |
| recommend     | implementer | —          | `upgrade_wavefoundry.py` major/minor line        |
| tests         | implementer | recommend  | gated recommendation + content/parity checks     |


## Serialization Points

- Late-admitted into the OPEN `1p7pk` (operator-directed, before shipping 1.9.0). Its review is the wave's pre-close review.

## Affected Architecture Docs

- Guidance/tool-surface only; no boundary/flow change. Confirm at close.

## AC Priority

(Proposed; confirmed at close.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The MCP-first routing is the fix for the manual-upgrade gap. |
| AC-2 | important | Discoverability — agents can't prefer a tool they don't see listed. |
| AC-3 | required  | The reconciliation recommendation is the fix for the second gap. |
| AC-4 | required  | No seed→render drift; test-locked, bytecode-free. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-25 | Drafted from 1.9.0-upgrade field feedback: agents nearly went manual (stopped, ran `wave_upgrade()`); no agent recommended a minor-bump reconciliation. Diagnosis: `seed-160` mentions `wave_upgrade` only as an aside + it's absent from the AGENTS.md tool list; the only minor-gated guidance is the config-review recommendation. | guru diagnosis of `seed-160`/`docs/prompts/upgrade-wavefoundry.prompt.md`/`upgrade_wavefoundry.py` `_config_review_recommendation_lines`/`_is_major_or_minor_upgrade` |
| 2026-06-25 | Implemented (admitted into OPEN wave 1p7pk; late-admitted). `seed-160` (gated edit) + `docs/prompts/upgrade-wavefoundry.prompt.md` now LEAD with an MCP-first `wave_upgrade()`/`wave_upgrade_status()` directive; the manual sequence is relabeled the no-MCP `wf upgrade` fallback (kept, not deleted). Added the minor-bump reconciliation callout to both. `_reconciliation_recommendation_lines` added to `upgrade_wavefoundry.py` (sibling of `_config_review_recommendation_lines`, same `_is_major_or_minor_upgrade` gate; names the 1.9.0 bin/*→wf example), wired into the operator summary; also fixed the stale `bin/docs-lint`/`upgrade-wavefoundry --…` lines in that summary to `wf …`. `wave_upgrade`/`wave_upgrade_status` added to the AGENTS.md tool list; `wave_upgrade_status` documented in `docs/specs/mcp-tool-surface.md` (when-to-call: lock-state inspection before reload/restart). Changelog `[Unreleased]` bullets added. Tests: `ReconciliationRecommendationTests` (minor/major present, patch/downgrade/same/unparseable absent) + `UpgradeMcpFirstGuidanceTests` (MCP-first lead in both surfaces, fallback retained, reconciliation callout, tool-list/spec presence, directive leads the procedure). Full parallel suite green; docs-lint clean; gates closed. | `seed-160`; `docs/prompts/upgrade-wavefoundry.prompt.md`; `upgrade_wavefoundry._reconciliation_recommendation_lines`; `AGENTS.md`/`docs/specs/mcp-tool-surface.md`; `test_upgrade_wavefoundry.ReconciliationRecommendationTests`; `test_shipped_reference_docs.UpgradeMcpFirstGuidanceTests` |
| 2026-06-25 | Pre-close review minor: the reconciliation recommendation's GATE was tested but its WIRING into `_print_operator_summary` was not. Added wiring tests asserting the `Reconciliation recommended` line (and its sibling `Config review recommended`) actually appear in the rendered operator summary on a minor bump, are absent on a patch bump, and are suppressed on a failed phase. | `test_upgrade_wavefoundry.ReconciliationRecommendationTests.test_reconciliation_line_wired_into_operator_summary_on_minor_bump` (+ `_on_patch_bump` / `_on_failed_phase`) |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-25 | Fix in the guidance (seed-first) + a recommend-only reconciliation line, not new automatic upgrade behavior | The mechanical reconciliation is already automatic in `wave_upgrade()`; the gap is routing + recommendation. Seed-first ships it to target repos on upgrade. | Force a reconciliation phase in the script — rejected (it's already done by the phases; the gap is agents not calling the tool). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Reframing the seed could lose the manual fallback CLI hosts rely on | Keep the full manual sequence as the explicitly-labeled "no-MCP fallback (`wf upgrade`)"; only re-prioritize, don't delete. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
