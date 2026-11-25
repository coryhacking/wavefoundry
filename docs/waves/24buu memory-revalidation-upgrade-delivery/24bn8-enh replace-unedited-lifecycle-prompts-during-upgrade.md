# Replace unedited lifecycle prompts during upgrade

Spec ID: `24bn8-enh replace-unedited-lifecycle-prompts-during-upgrade`
Spec Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-24
Wave: 24buu memory-revalidation-upgrade-delivery

## Rationale

Before extraction, upgrade compares each project-owned lifecycle prompt and template with the previous and incoming install baselines (`render_agent_surfaces.lifecycle_baseline_drift`, run by the incoming renderer) and stores the findings in the upgrade lock (`upgrade_wavefoundry._lifecycle_baseline_findings`). When the local copy matches the previous template, it reports `upstream_changed_local_matches_previous` with the action "overwrite: Replace the unedited local copy with the incoming template" (`_BASELINE_ACTIONS`), but writes nothing.

The 24buu upgrade rehearsal (`.wavefoundry/work/24buu/upgrade-rehearsal.md`, items 4 to 6) upgraded a 1.51.0 installation and found:

1. Five unedited prompts reported but not replaced: implement-wave, memory-review, close-wave, close-spec and explain. The upgraded memory-review and close-wave prompts carry no `check_note` rule.
2. The same prompts still name the retired tools `wf_close_change` and `wf_get_change`, ten times in all.
3. `docs/plans/plan-template.md` reported as locally edited ("merge ... by hand") although it was unedited. The red-team primer (`.wavefoundry/work/24buu/readiness/red-team.md`, F4) executed the comparison: `_comparable_baseline` already normalizes the `Last verified:` date, and the real difference is that the previous template is materialized with the incoming vocabulary, so its `Change ID:` and `Change Status:` lines become `Spec ID:` and `Spec Status:` (`vocabulary_profile.localize_template`) while the unedited local copy keeps the 1.51.0 labels.

Two prompts in the set, implement-wave and close-wave, carry renderer-owned `wavefoundry:review-policy` marker regions, so a raw template write would drop them (F6).

## Product Intent

**Beneficiaries:** operators who upgrade, and the agents that follow the project's prompts afterwards.

**Before:** after upgrading, unedited prompts keep old guidance and retired tool names until someone overwrites them by hand, and an unedited plan template asks for a hand merge.

**After:** upgrade replaces every prompt and template that is unedited relative to its previous baseline, keeping the project's `Last verified:` date and every renderer-owned region, before the docs gate and the index run, and reports what it replaced. Only copies the project actually edited are left for the agent merge.

**Boundaries:** upgrade never overwrites a locally edited copy, an unknown-baseline copy, or a copy that changed after the comparison. Replacement is the action the report already prescribes.

AC-1 and AC-3 establish the intent.

## Requirements

1. **Comparison digest.** When the comparison classifies a destination `upstream_changed_local_matches_previous`, the stored finding records a digest of the local copy's comparable form (the form `_comparable_baseline` produces).
2. **Previous-label matching.** The comparison also matches the local copy against the previous template materialized with the shipped labels it was installed with (the identity localization), so an unedited copy installed under the earlier labels classifies `upstream_changed_local_matches_previous`. Shipped header-label lines are compared in a normalized form the same way the date already is.
3. **Replacement in the render child.** The Phase 1 surface render child, which runs the freshly extracted code on every upgrade path and runs before the docs gate and the index, replaces each such destination when its current comparable-form digest equals the recorded one. It runs only when the upgrade lock holds captured lifecycle findings, so `wf setup` and `wf_sync_surfaces` never replace anything. The replaced paths are saved in the upgrade lock, so the cleanup summary reports them even when cleanup runs in another process. The written content is the incoming materialized template with the local `Last verified:` date, after which the same render pass renders the renderer-owned regions for that destination, so the result equals what a fresh install's render produces with that date. The write is atomic, through the contained-write helpers, preserving line endings. The finding is reported as `replaced`.
4. **Skips.** A destination that is a symlink, resolves outside the checkout, or whose digest differs from the recorded one is not written and keeps its finding.
5. **Other classifications.** Every other classification is unchanged and writes nothing.
6. **Guidance.** Seed 160's section "Lifecycle baseline drift report" and the same section of `docs/prompts/upgrade-wavefoundry.prompt.md` are revised in place, keeping the heading: upgrade replaces unedited copies itself, and the agent merge applies to every copy it leaves in place. The sentences describing overwrite as a manual delete-and-re-render, and "The report leaves the files and exit status unchanged", are replaced, as are the code strings that say "report only; project copies preserved" for this classification. Change `24but-enh deliver-memory-revalidation-through-upgrade` keeps its agent merge of the keep rule for edited memory-review and close-wave prompts.
7. **Platform behavior.** The write uses the framework's atomic replace and line-ending helpers, so Windows, macOS, Linux and WSL2 behave the same.

## Scope

**Problem statement:** upgrade reports, but does not perform, the safe replacement of unedited prompts and templates, and misclassifies an unedited plan template.

**In scope:** the digest, previous-label matching, the replacement in the render child, summary lines, seed 160 and its self-hosted copy, tests and a changelog entry.

**Out of scope:**

- Merging locally edited copies; that stays the agent's job (`24but-enh deliver-memory-revalidation-through-upgrade` adds the keep-rule merge for two of them).
- Retired-tool references in edited copies, which stay reconciliation findings.

## Acceptance Criteria

- [x] AC-1: On an upgrade fixture where implement-wave, memory-review, close-wave, close-spec and explain are byte-identical to the 1.51.0 shipped copies as installed, after the Phase 1 render child each equals a fresh install's render of the incoming template with the fixture's `Last verified:` date, including the review-policy region in implement-wave and close-wave; memory-review and close-wave contain `check_note`; none of the five names `wf_close_change` or `wf_get_change`; and the summary lists five `replaced` paths. Known bad: today's code leaves all five unchanged.
- [x] AC-2: A prompt with one local edit is left byte-identical and still reported `upstream_changed_local_differs_from_previous`.
- [x] AC-3: An unedited `docs/plans/plan-template.md` with the 1.51.0 bytes as installed (labels `Change ID:` and `Change Status:`, a materialized date) is classified `upstream_changed_local_matches_previous`, replaced, and keeps its original date. Known bad: today it is reported `upstream_changed_local_differs_from_previous`.
- [x] AC-4: A destination that is a symlink, or whose content changes between the comparison and the render child, is not written and keeps its finding.
- [x] AC-5: A second upgrade with the same pack writes nothing and reports no `replaced` path.
- [x] AC-6: Seed 160's "Lifecycle baseline drift report" section and its self-hosted copy state requirement 6 and no longer contain "The report leaves the files and exit status unchanged"; a text test pins the new text and the absence of the old sentence (known bad: today's section). `CHANGELOG.md` has an `[Unreleased]` entry naming this wave and change.
- [x] AC-7: A destination classified `baseline_unknown`, and one classified `upstream_unchanged_local_differs`, are left byte-identical and keep their findings.
- [x] AC-8: Running the render child with no upgrade lock (as `wf setup` does) on the AC-1 fixture writes no prompt file.

## Tasks

- [x] `render_agent_surfaces.py`: the digest in the finding, previous-label matching, and the replacement with region rendering.
- [x] `render_platform_surfaces.py` and `upgrade_wavefoundry.py`: run the replacement in the Phase 1 render child from the lock's findings, and add `replaced` to the summary.
- [x] Tests in `tests/test_lifecycle_baseline_drift.py` (using the 1.51.0 shipped bytes) and an upgrade fixture case.
- [x] Seed 160 (under `seed_edit_allowed`) and its self-hosted copy; text pin; changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| compare | implementer | — | Requirements 1 and 2, AC-3 |
| replace | implementer | compare | Requirements 3 to 5, AC-1, AC-2, AC-4, AC-5 |
| guidance | implementer | — | AC-6 |

## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_baseline_drift.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/architecture/data-and-control-flow.md`
- The root `CHANGELOG.md` entry.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` section "Upgrade lifecycle baseline drift": it says upgrade leaves project-owned destination bytes unchanged, describes the finding shape and the manual overwrite procedure; all three change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The operator-visible outcome. |
| AC-2 | required | Local edits are never lost. |
| AC-3 | required | Removes the false hand-merge. |
| AC-4 | required | Safe writes. |
| AC-5 | required | Idempotence. |
| AC-6 | required | Guidance and release notes. |
| AC-7 | important | Unknown baselines are never overwritten. |
| AC-8 | required | Setup never replaces project files. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned from the 24buu upgrade rehearsal. | `.wavefoundry/work/24buu/upgrade-rehearsal.md` items 4 to 6 |
| 2026-11-24 | Revised before readiness approval from the red-team primer: the plan-template cause is label localization, not the date (F4); replacement keeps renderer-owned regions, checks a recorded digest and runs in the Phase 1 render child before the docs gate and index (F6); AC-5 reworded (F12). | `.wavefoundry/work/24buu/readiness/red-team.md` |
| 2026-11-24 | Bounded readiness repair (cycle 1) for QA-7, AR-2, AR-3, DC-1 and DC-4: replacement runs only with captured lock findings and records replaced paths in the lock; unknown-baseline and setup cases tested; the seed section and code strings are revised in place; the architecture doc is named. | `.wavefoundry/work/24buu/readiness/repair-1.md` |
| 2026-11-24 | Readback: implement the captured three-way decision in the extracted Phase 1 renderer before docs validation. Keep all edited targets and preserve the original materialized date. | Gapfill: inspected the v1.51.0 distribution and targeted source lines to verify the pre-extraction handoff and the old runner’s render arguments. |
| 2026-11-24 | Implemented all eight criteria. Phase 1 checks the captured comparable digest and current file identity, publishes atomically with original line endings and date, regenerates owned regions and records replacements for cleanup. The merge action identifies the incoming baseline for edited memory-review and close-wave prompts. | The integration test compares six historical templates from the v1.51.0 release with a fresh install and rechecks an identical upgrade. A separate test checks both incoming merge paths using the installing hook. Native Windows follows the contained helper’s path checks; execution here used macOS. |
| 2026-11-24 | Verified the code in 23 direct focused tests. All 23 also passed in the canonical default worker, whose guard detected concurrent edits to other wave files. The earlier 21-test default and second-profile runs passed cleanly; final qualification is the wave-wide run. The line-ending writer census and full docs validation passed. | Six scratch mutations failed their named tests: skipping Phase 1 or the old-label comparison failed the v1.51.0 fixture; dropping the digest check failed the late edit fixture; dropping protected paths failed edited-region preservation; omitting the line-ending merge failed the CRLF check; dropping the baseline path failed the installing-hop merge check. Logs under `.wavefoundry/work/24buu/impl/24bn8/`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Plan this in wave 24buu. | Operator: "Make sure that the upgrade installs everything correctly with as little intervention as possible." | — |
| 2026-11-24 | Selected: perform the prescribed overwrite in the Phase 1 render child for copies whose recorded digest still matches, rendering the owned regions. Efficacy: replaying the rehearsal, all five prompts and the plan template would be replaced before the docs gate and index, removing every retired-tool reference and adding the keep rule with no agent step. It controls the outcome; it cannot help an edited copy, which keeps the agent merge. | Planner default. | Replace in cleanup: runs after the docs gate and index, and on the 1.51.0 CLI path only after a manual step. Re-render prompts unconditionally: loses project edits. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A project relied on an old prompt without editing it. | The copy matched a shipped template; the summary lists each replacement and git shows the diff. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
