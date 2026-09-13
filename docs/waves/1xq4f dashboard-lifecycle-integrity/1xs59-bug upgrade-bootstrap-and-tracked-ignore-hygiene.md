# Upgrade Bootstrap and Tracked-Ignore Hygiene

Change ID: `1xs59-bug upgrade-bootstrap-and-tracked-ignore-hygiene`
Change Status: `complete`
Owner: Engineering
Status: completed
Completed At: 2026-09-12
Last verified: 2026-09-12
Wave: 1xq4f dashboard-lifecycle-integrity

## Rationale

A destination upgrading 1.23.0+powy to 1.24.0+ppd0 completed schema-8 conversion and passed post-restart retrieval, but retained a package-created root installer. Extraction precedes a restart-capable hook; the process-local creation receipt cannot survive that pause. The same destination already tracked guard-overrides.json, so the newly rendered ignore rule did not stop Git tracking. The operator requests both fixes before the next local build: upgrades leave no new root installer and explicitly flag tracked runtime state without changing project Git ownership.

## Requirements

1. Ordinary upgrade extraction skips the archive-root install-wavefoundry.md even when absent in the destination. The incoming pre-extract extension applies the same rule to supported older runners on the installing hop, before any extraction/restart pause. Existing root files (regular, tracked, modified, symlink or dangling link) are never overwritten or removed. Unknown old-runner extraction interfaces refuse before mutation rather than assuming protection.
2. The package continues to contain the installer for manual fresh-install discovery; fresh-install cleanup stays separate. Retire process-local bootstrap cleanup machinery where it no longer has a production owner; do not replace it with another recovery receipt. Already-leftover installers remain untouched automatically.
3. The normal platform renderer, used by setup and upgrade, reports paths already tracked by Git that match the canonical managed runtime-ignore patterns. Use Git's own pattern semantics and NUL-delimited records; examine only the configured project root and canonical rules, not unrelated project/global ignore rules. Include all managed runtime categories, not only guard-overrides.json. Report paths safely even with spaces or newlines. A bounded display may include an explicit omitted count.
4. The warning explains that ignore rules do not untrack files and advises review before git rm --cached; it never removes files, stages changes, rewrites Git history or changes guard values. Missing Git/non-repositories degrade harmlessly; timeout/inspection failures are non-blocking and do not claim a clean census. Worktrees with a .git file are supported. Permission-only renders remain permission-only.
5. Ship concise upgrade guidance and changelog benefits. Upgrade logging must retain the renderer warning so the agent/operator sees it. No mandatory approval, automatic untracking or new blocking docs sensor is introduced.

## Scope

In scope: upgrade extractor and incoming compatibility hook; canonical runtime-ignore renderer and captured warning; focused real-Git and mixed-runner tests; upgrade guidance and release note.

Out of scope: storage/schema changes, deleting existing bootstrap leftovers, automatic Git index changes, fresh-install redesign, remote release or package build, native platform qualification claims.

## Acceptance Criteria

- [x] AC-1: A package containing the root installer upgrades an absent-file destination without creating it, including a supported old-runner pre-extract hook followed by restart/resume; preexisting regular/tracked/modified/link files retain bytes and identity.
- [x] AC-2: The installer remains present in the built feature inventory for fresh installs; unrelated feature members still extract and archive-only runner members remain excluded.
- [x] AC-3: A real Git repository with tracked guard state, locks, index/log/backup entries and a package drop reports those exact paths; untracked ignored files and tracked files matched only by project/global rules are not reported. Spaced/newline names and worktrees are handled safely.
- [x] AC-4: Renderer warnings leave the Git index, file bytes and guard state unchanged; repeated checks agree. Non-repository, missing Git, failed/timeout Git inspection and permission-only controls remain non-blocking and truthful.
- [x] AC-5: Ordinary upgrade rendering captures the warning on the installing hop, and the edited upgrade instructions accurately distinguish fresh-install bootstrap use, upgrade exclusion and operator-owned untracking.

## Tasks

- [x] Repair current and incoming-old-runner bootstrap extraction with regression controls.
- [x] Add canonical-pattern tracked-runtime warning with real Git and failure controls.
- [x] Update upgrade guidance, tests and changelog; execute focused mutants and full framework/docs gates.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| bootstrap | implementer | — | Current extractor, incoming hook, tests. |
| tracked-runtime | implementer | bootstrap | Renderer warning and own fixtures. |
| verification | qa-reviewer | tracked-runtime | Mixed runner, real Git, negative controls. |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `CHANGELOG.md`

One implementer owns sequential edits. Reviewers are read-only. Preserve protected project files, managed renderer boundaries and the existing migration receipt protocol.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: clarify upgrade archive extraction and renderer diagnostics; no storage or ownership redesign.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Fix the demonstrated leftover without deleting project files. |
| AC-2 | required | Preserve fresh-install and upgrade package contracts. |
| AC-3 | required | Detect the reported tracking gap across canonical runtime rules. |
| AC-4 | required | Keep Git mutations operator-owned and inspection advisory. |
| AC-5 | required | The fix must reach the installing upgrade and its operator. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-12 | Operator authorized the two upgrade fixes. Plan grounded in current extraction ordering, incoming pre_extract hook and unconditional renderer entry. No code edits before readiness. | Field report; upgrade_wavefoundry._extract_feature_members; upgrade_extensions._protect_existing_root_bootstrap; render_gitignore_block. |

| 2026-09-12 | Current and incoming-old-runner exclusions implemented; retired process-local cleanup. Native Git census and captured summary warning implemented. Root coordinator is the sequential implementer; QA execution is implementer-owned, not independent delivery approval. | RootBootstrapUpgradeTests; TrackedRuntimeDiagnosticsTests; TrackedRuntimeUpgradeWarningTests. |
| 2026-09-12 | Nine in-memory guard mutations detected by named tests: current exclusion, old-runner exclusion, legacy cleanup, unknown interface, canonical-only rules, nested prefix, timeout reporting, display cap and summary propagation. | upgrade-fixes-evidence.json implementation.mutations; framework source not mutated. |
| 2026-09-12 | Gapfill: MCP outline/targeted code reads grounded changes; shell readback and exact edits used for mechanical test/docs updates and executable fixtures. | Focused test logs and durable evidence. |

| 2026-09-12 | Focused validation passed: 102 renderer tests, 781 upgrade/protocol/migration/package tests (2 skips), and 2 captured-upgrade-summary tests. Full docs gate passed. Read-only source-repo census found no tracked runtime paths (one 42.4 ms sample). | upgrade-fixes-evidence.json implementation.focused_tests and repository_smoke. |

| 2026-09-12 | First full suite exposed the new raw Git spawn's isolation contract violation; switched to canonical isolated_run with binary output. Native dashboard cases were separately blocked by sandbox process inspection. Corrected full suite rerunning with approved host access; no receipt waiver. | FrameworkWideSubprocessIsolationGuard; first_full_run in upgrade-fixes-evidence.json. |

| 2026-09-12 | Final framework suite passed: 8,902 tests, 21 skips; fresh receipt hash recomputed and matched. Post-repair 124 focused tests and all nine mutants passed. All ACs/tasks complete; new delivery review pending. No new package or commit. | upgrade-fixes-evidence.json implementation.full_suite. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-12 | Skip upgrade-only bootstrap extraction at both current and old-runner boundaries. | No artifact means no restart-spanning ownership debt. | Persist cleanup ownership: adds state and failure paths. Unconditional deletion: loses project files. |
| 2026-09-12 | Warn using Git's matching of canonical patterns; never untrack automatically. | Exact native semantics with operator ownership preserved. | General ignored-file scan: falsely includes intentional project tracking. Automatic git rm --cached: changes a project's index without review. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Old runner writes before new behavior is loaded. | Incoming pre_extract hook test with frozen older extraction behavior. |
| Nested Git roots or global excludes widen scope. | Scope scan explicitly and use only canonical patterns; real Git fixtures. |
| Warning breaks rendering or hides inspection failure. | Bounded subprocesses, failure diagnostics, no blocking gate. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
