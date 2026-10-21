# Report Lifecycle Baseline and Plan-Template Drift at Upgrade

Change ID: `21512-enh lifecycle-baseline-drift-report`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-20
Wave: 215a9 distribution-followup-vocabulary-and-baseline-drift

## Rationale

A downstream distribution refreshing to v1.34.0 reported that changed lifecycle templates never reach existing repositories (their Y7). Verified at `3d21af8e`:

- `reconcile_lifecycle_prompt_baselines` (`.wavefoundry/framework/scripts/render_agent_surfaces.py:4296-4321`) and `reconcile_scaffold_baselines` (`:4344-4359`) skip any destination that already exists.
- Between v1.32.0 and v1.34.0 six of the eight `install/lifecycle-prompts/` templates and `install/plan-template.md` changed (Intent outcome, Objective, Readback and Product Intent guidance; a new `## Product Intent` section).
- `wf_new_*` scaffolds from the target's own `docs/plans/plan-template.md` when it exists (`wf_server/server_impl.py:9393-9395`), so existing targets keep creating change docs without the new section.
- No upgrade step compares these files. The upgrade extracts the new framework in place (`upgrade_wavefoundry.py:6555`), so the previously shipped templates exist only before extraction; `_compute_seed_diffs` (`:847-920`) already relies on that window for seeds.

Overwriting is wrong: these files are project-owned once materialized. Reporting is the gap.

## Product Intent

Operators upgrading a target learn which project-owned lifecycle prompts and plan template have a changed upstream template, and whether their local copy matches the previous shipped template, so they can merge deliberately. Before: an upgrade silently leaves stale copies and nothing says so. After: the upgrade's change plan and machine-readable summary list each affected file with one of a small set of states, and say plainly when the previous template cannot be determined. The previous framework template is not necessarily the baseline that produced the local file (an earlier upgrade may have preserved an older copy), so without installation provenance a difference is reported as a difference, never as a customisation. Boundaries: the upgrade does not modify destination prompts or the plan template because of this report; no new reconcile command. AC-1 with AC-2 tests whether the intent was established.

## Requirements

1. The baseline set is derived, not enumerated: every `(destination, template)` pair in `LIFECYCLE_PROMPT_BASELINES` plus the plan-template scaffold pair used by `reconcile_scaffold_baselines`.
2. For each pair whose destination exists in the target, the upgrade determines two independent facts:
   - **shipped-change:** whether the incoming template differs from the previously shipped template, read from the target's framework `install/` copy before extraction. When the previous template is absent or unreadable, the fact is `unknown`, never assumed.
   - **local-change:** whether the local destination differs from the previously shipped template as it would have been materialized (same `{{generated_at}}` handling and profile localization, with the generated date masked), and whether it already equals the incoming materialized template.
3. Each reported file carries one state: `upstream_changed_local_matches_previous`, `upstream_changed_local_differs_from_previous`, `upstream_unchanged_local_differs`, `already_current`, or `baseline_unknown` (previous template unavailable; reports only whether the local copy differs from the incoming template). The detail for a differing local copy says the cause may be a local edit or an earlier template update that was never applied; no state claims a file was customised or is safe to refresh. Files that are `already_current` and unchanged upstream are not listed.
4. The report appears in the upgrade change plan (dry run and real run, beside the seed diffs) and in the machine-readable upgrade summary, as items shaped like the existing `renderer_warnings` entries (`channel`, `file`, `detail`).
5. Comparisons normalise line endings (CRLF and LF compare equal) and read local files through the existing contained-path helpers, so symlinked destinations outside the repository are not followed.
6. The upgrade does not modify destination prompts or the plan template because of this report, and its exit status is unchanged by any finding. Persisting the findings in upgrade state (for example the upgrade lock) is permitted.
7. Findings are captured once, before extraction. A resumed or later process (including `--cleanup`) reads the captured findings and never recomputes the shipped-change fact from the newly extracted templates.

## Scope

**Problem statement:** changed lifecycle templates and the plan template never reach existing targets, and nothing tells the operator.

**In scope:**

- A preflight comparison in `upgrade_wavefoundry.py` captured before extraction, carried to the summary.
- Rendering the findings in the change plan and the summary.
- Tests with fixture targets covering every state, CRLF local copies, and a missing previous template.

**Out of scope:**

- Automatically refreshing or merging any local file, or a new reconcile command (a later change if field data asks for it).
- Marker-fenced regions inside the templates.
- Seeds and other rendered surfaces (already covered by seed diffs and re-rendering).
- Parked plan `1vvs3` (render prompt docs from source) is not revived; it excludes these templates.

## Acceptance Criteria

Name at least one AC, or a clearly identified combination, that tests whether the intent was established. Keep implementation checks where useful; delivery of guidance alone does not prove improved agent behavior.

- [x] AC-1: An upgrade dry run against a fixture target whose previous framework ships an older `install/plan-template.md` and older lifecycle templates lists, in the change plan, each affected destination with the correct state, distinguishing a local copy that matches the previous template from one that differs from it, including a local copy preserved from a template two releases back (reported as differing, with the may-be-a-missed-update detail).
- [x] AC-2: When the previous template is absent from the target's framework copy, the file is reported as `baseline_unknown` with whether the local copy matches the incoming template, and is never reported as `upstream_changed_local_matches_previous`.
- [x] AC-3: The machine-readable upgrade summary carries the same findings as `{channel, file, detail}` items, and a target with every baseline current produces none.
- [x] AC-4: A local copy that differs from the materialized previous template only by CRLF line endings or by its generated `Last verified` date is treated as unmodified.
- [x] AC-5: After an upgrade that reports drift, every destination prompt and the plan template are byte-identical to their pre-upgrade content and the upgrade's exit status matches the same upgrade with no drift.
- [x] AC-6: When an upgrade is interrupted after extraction and resumed (or its summary is produced by the separate cleanup process), the summary carries exactly the findings captured before extraction; a fixture where the extracted templates would yield different findings proves the resumed process did not recompute them.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add a preflight baseline comparison beside `_compute_seed_diffs`, reading the incoming templates from the zip and the previous ones from disk before extraction.
- [x] Reuse the materialization transform (generated date, profile localization) to compare local copies; normalise newlines.
- [x] Print findings in `_print_change_plan` and carry them to the summary (through the upgrade lock where the summary runs in a later process).
- [x] Fixture tests for each state, CRLF, missing previous template, a two-releases-back local copy, interrupted-and-resumed upgrade, and the untouched-destinations guarantee.
- [x] Document the report in `docs/prompts/upgrade-wavefoundry.prompt.md`'s source seed and the CHANGELOG Unreleased section.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                  |
| ---------- | ----------- | ---------- | -------------------------------------- |
| compare    | implementer | none       | preflight comparison and states        |
| report     | implementer | compare    | change plan and summary channel        |
| tests      | implementer | compare    | fixture targets, CRLF, no-write oracle |
| docs       | implementer | report     | upgrade seed and changelog             |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/upgrade_lib.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` if it describes upgrade phases (adds a report-only preflight output); otherwise N/A. Confirm at Prepare.

## Platform Behavior

The comparison runs on all platforms. Native Windows: Git `autocrlf` can leave local copies in CRLF, so comparisons normalise line endings (AC-4); paths go through the existing contained-path helpers, which already handle Windows separators. macOS, Linux and WSL2 behave identically; on WSL2 a checkout shared with Windows may carry CRLF and is handled the same way.

## AC Priority


| AC   | Priority  | Rationale                                    |
| ---- | --------- | -------------------------------------------- |
| AC-1 | required  | the report itself, matches vs differs        |
| AC-2 | required  | no "matches previous" claim without evidence |
| AC-3 | important | machine-readable consumers                   |
| AC-4 | required  | Windows false positives                      |
| AC-5 | required  | destination files untouched                  |
| AC-6 | required  | resume keeps pre-extraction evidence         |
| AC-7 | required  | change-local verification                    |


## Progress Log
| Date       | Update  | Evidence                                |
| ---------- | ------- | --------------------------------------- |
| 2026-10-20 | Planned | distribution v1.34.0 feedback Y7 triage |
| 2026-10-20 | Readback: report differences for eight lifecycle baselines plus the resolved plan template, captured before extraction and replayed through resume/cleanup. AC-1–7 cover neutral states, unknown baseline, date/newline equality, preserved destinations and immutable evidence. Example: local template A with installed B and incoming C reports differs from previous without inferring customization. Upgrade runner, incoming hooks, shared renderer transform, tests, upgrade seed and architecture flow are in scope; no automatic refresh or changed upgrade exit status. | Current admitted plan and readiness approval |
| 2026-10-20 | Implemented derived comparison, shared renderer transform, incoming preview/pre-extraction capture, version-and-pack-bound retry preservation, and structured summary/cleanup replay. Missing capture reports unknown; captured empty results remain empty. Destination bytes and exit status are preserved. | 14 focused tests and 76 existing upgrade seam tests passed. Additional preview cluster: 64 passed, one ordering regression repaired; repaired ordering test passed. Twelve targeted mutants detected, including lost capture, date/newline handling, containment and target/pack binding. Logs: `/private/tmp/215a9-baseline-tests.log`, `/private/tmp/215a9-upgrade-seams.log`, `/private/tmp/215a9-preview-order-repair.log`, `/private/tmp/215a9-baseline-mutants.log`. |
| 2026-10-20 | Compatibility boundary: older installed runners show the incoming dry-run text report; their old dry-run JSON schema is unchanged. The new runner dry run and real delegated/cleanup summaries carry the structured field. | Zip-loaded public hook dispatch with an older context shape tested; archived historical runner and downstream installation not qualified. Delivery reviewers are explicitly briefed on this boundary. |
| 2026-10-20 | Canonical suite found three integration regressions; cycle 1 repair started before edits. Capture must follow retained-pack refusal; isolated compatibility fixtures need the canonical lock producer; timed-call census must name the moved helper. No production guard or assertion is weakened. | 12,005 tests across 203 files, 12 existing skips; four failed files in 647.747 seconds. Typed findings and repair-start records are in this wave ledger; full log `/private/tmp/215a9-framework-tests.log`. |
| 2026-10-20 | Cycle 1 repair applied and source frozen: report capture follows package-identity guard; isolated hook fixtures call the canonical checkpoint producer; exact timed-call census names the extracted helper. | 23 focused tests passed in 4.416 seconds. Four reverse-order, omitted-producer and stale-census controls detected the intended failures. Fresh independent repair review and canonical suite rerun pending. |
| 2026-10-20 | Implementation and delivery review complete. All acceptance criteria and tasks have evidence; no deferrals. | Final canonical suite: 12,005 tests across 203 files, 12 existing skips, 714.645 seconds, OK; current framework receipt written. Full docs validation passed before final bookkeeping and is rerun at handoff. Six specialist and council delivery approvals recorded; all three cycle-1 findings independently reverified and terminal. |

## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-20 | Report "matches/differs from previous template", never "customised" | the previous template need not be the baseline that produced the local file; without install provenance the cause is unknown | infer customisation from a difference: wrong after any earlier preserved upgrade |
| 2026-10-20 | Report-only preflight comparison against the on-disk previous templates | the only point where previous-template evidence exists; preserves project-owned files | (a) overwrite on upgrade: destroys local customisation; (b) record template hashes at install for later comparison: new persisted state, and helps only installs made after it ships; (c) compare local against today's template only: cannot tell an upstream change from a local edit |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Carrying findings across the cleanup process adds lock state | reuse the existing permissions-delta carry pattern; identify it at Prepare as new review surface |
| Materialization transform drifts from the renderer's | call the renderer's own transform rather than re-implementing it |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
