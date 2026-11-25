# CLI upgrade runs cleanup itself

Spec ID: `24bn9-enh cli-upgrade-runs-cleanup`
Spec Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-24
Wave: 24buu memory-revalidation-upgrade-delivery

## Rationale

A CLI upgrade (`wf upgrade --pack <zip> --confirm-hosts-stopped`) runs phases 0 to 4 and then stops with "Phases 0–4 complete. Proceed with agent editing pass, then run: upgrade-wavefoundry --cleanup" (`upgrade_wavefoundry.main`, primary branch). The operator or agent must then run `--cleanup`. The 24buu upgrade rehearsal (`.wavefoundry/work/24buu/upgrade-rehearsal.md`, item 7) needed exactly that step. The MCP flow sequences the phases itself: `wf_upgrade`'s next step is `wf_upgrade(phase='update_index')`, then `wf_upgrade(phase='cleanup')` (`wf_server/upgrade_handlers.py`). The operator asked that the CLI run cleanup too (2026-11-24).

Two constraints shape it (red-team primer, `.wavefoundry/work/24buu/readiness/red-team.md`, F5 and F8):

1. The primary phase runs the installed code, which imported the old module before extraction. Upgrading from 1.51.0, that code prints today's message, so this change takes effect from the first upgrade after 1.52.0 is installed.
2. The MCP `wf_upgrade` primary invokes the same command line as the CLI. If the primary auto-cleaned there, it would remove the lock before MCP's own `update_index` and `cleanup` steps.

Cleanup must also run in a process that loaded the new code: seed 160 says cleanup runs "only after a new process has verified the published SQLite generation".

## Product Intent

**Beneficiaries:** operators and agents that upgrade through the CLI.

**Before:** a successful CLI upgrade ends with a manual `--cleanup` step.

**What a target sees on the installing hop:** the primary's printed messages; seed 160's revised paragraph reaches a target's upgrade prompt on its next upgrade.

**After:** from installations at 1.52.0 or later, a successful CLI upgrade runs cleanup itself in a fresh child process, prints the full summary and ends complete; the agent editing pass follows, with `--update-index` only if it changes indexed files, as on the MCP path. The MCP flow is unchanged. Upgrading from 1.51.0 through the CLI still needs one `--cleanup`, which the 1.52.0 release notes state.

**Boundaries:** cleanup never runs automatically when phases 0 to 4 did not finish cleanly, when a retained continuation owns the next step (a storage-migration pause, a restart-required receipt, a failed index publication, a retained upgrade checkpoint), or under the MCP primary. `--cleanup` stays available.

AC-1 and AC-2 establish the intent.

## Requirements

1. The primary phase accepts `--no-auto-cleanup`. The MCP `wf_upgrade` handler passes it on its primary invocation. The primary also treats the `WAVEFOUNDRY_STORAGE_OLD_MCP_PID` environment variable, which the MCP handler already sets on every `wf_upgrade` child, as the same opt-out, so an MCP server still running older handler code cannot trigger auto-cleanup.
2. Without that opt-out, when the primary phase completes with index publication confirmed and no retained continuation pending, it runs `--cleanup` as a child process from the freshly extracted framework, using the existing upgrade child runner, with the same root and log. The same applies when `--resume-after-gate` completes. The release zip's direct entry (`upgrade_bundle.run`, which runs the new runner's primary with `--yes`) gets the same behavior, and `upgrade_bundle`'s recovery report then says cleanup is complete instead of directing `wf_upgrade(phase='cleanup')`.
3. When any condition in Boundaries holds, or `--no-auto-cleanup` is passed, the primary does not run cleanup and prints today's continuation text unchanged.
4. The child's exit code becomes the CLI's exit code; a failed cleanup prints its retained state and the `--cleanup` retry command. The primary and cleanup summaries are both printed, and the primary's summary sentinel handling still produces one terminal result.
5. The final message tells the agent to do the editing pass and to run `--update-index` only if that pass changes indexed files, matching the MCP guidance.
6. Seed 160's paragraph beginning "The primary phase can exit zero while cleanup remains pending" and the same paragraph of `docs/prompts/upgrade-wavefoundry.prompt.md` are revised in place, as is the module docstring: the CLI and the release-zip entry run cleanup themselves after a clean primary phase from 1.52.0 on, one `--cleanup` is still needed from 1.51.0 through the CLI, and cleanup stays manual when a retained continuation owns the next step. `docs/references/native-windows-support.md` statements that require a separate cleanup are updated the same way.
7. Platform behavior: the child uses the existing upgrade child runner, which already handles Windows process creation, so Windows, macOS, Linux and WSL2 behave the same.

## Scope

**Problem statement:** the CLI upgrade leaves cleanup as a manual step.

**In scope:** the automatic cleanup child, `--no-auto-cleanup` and its use by the MCP handler, skip conditions, messages, guidance text, tests and a changelog entry.

**Out of scope:** changes to the cleanup phase itself, the MCP phase sequence, and storage-migration recovery.

## Acceptance Criteria

- [x] AC-1: An upgrade fixture run through the primary phase without `--no-auto-cleanup` ends with the upgrade lock removed, the cleanup summary printed and exit code 0, with no separate `--cleanup` call. Known bad: today the lock remains and the output ends with "then run: upgrade-wavefoundry --cleanup".
- [x] AC-2: The MCP `wf_upgrade` primary invocation carries `--no-auto-cleanup`, and a primary run with that flag keeps the lock and prints today's continuation, so the following `wf_upgrade(phase='update_index')` and `wf_upgrade(phase='cleanup')` find the lock.
- [x] AC-3: With a failed index publication, and separately with a retained storage-migration continuation, the primary does not run cleanup, keeps the lock and prints today's continuation.
- [x] AC-4: The cleanup child runs the extracted tree's `upgrade_wavefoundry.py`, shown by the child's recorded script path.
- [x] AC-5: A failing cleanup child makes the primary exit nonzero and print the `--cleanup` retry command.
- [x] AC-6: Seed 160's paragraph, its self-hosted copy and the module docstring state requirement 6; a text test pins the new text and the absence of today's "then run: upgrade-wavefoundry --cleanup" instruction as an unconditional step (known bad: today's text). `CHANGELOG.md` has an `[Unreleased]` entry naming this wave and change and the one `--cleanup` still needed from 1.51.0.
- [x] AC-7: With a restart-required storage receipt, and separately with a retained upgrade checkpoint, the primary does not run cleanup, keeps the lock and prints today's continuation.
- [x] AC-8: AC-1 runs the real cleanup child (no fake), and the run produces exactly one terminal result: one final summary sentinel, exit code 0.
- [x] AC-9: The release-zip direct entry, run against a protocol-2 fixture to completion, ends with the lock removed and a recovery report that does not direct `wf_upgrade(phase='cleanup')`; with `WAVEFOUNDRY_STORAGE_OLD_MCP_PID` set, a primary run keeps the lock.
- [x] AC-10: A `--resume-after-gate` run that completes cleanly also runs cleanup and removes the lock.

## Tasks

- [x] `upgrade_wavefoundry.py`: `--no-auto-cleanup`, the cleanup child after a clean primary phase, skip conditions, messages, docstring.
- [x] `wf_server/upgrade_handlers.py`: pass `--no-auto-cleanup` on the primary invocation.
- [x] Tests in `tests/test_upgrade_wavefoundry.py` and the upgrade handler tests for AC-1 to AC-5.
- [x] Seed 160 (under `seed_edit_allowed`) and its self-hosted copy; text pin; changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| auto-cleanup | implementer | — | AC-1 to AC-5 |
| guidance | implementer | — | AC-6 |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`, `.wavefoundry/framework/scripts/upgrade_bundle.py`
- `docs/architecture/data-and-control-flow.md`, `docs/references/native-windows-support.md`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`
- The root `CHANGELOG.md` entry.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` section "Upgrade rerun and cleanup outcomes": "A successful primary phase still requires cleanup" changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The operator-visible outcome. |
| AC-2 | required | The MCP flow is not broken. |
| AC-3 | required | Recovery states are never cleaned up early. |
| AC-4 | required | Cleanup runs new code. |
| AC-5 | required | Failures stay recoverable. |
| AC-6 | required | Guidance and release notes. |
| AC-7 | required | Recovery states are never cleaned up early. |
| AC-8 | required | One terminal result with the real child. |
| AC-9 | required | The zip entry and old MCP servers behave correctly. |
| AC-10 | required | The gate-resume path ends complete. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned from the 24buu upgrade rehearsal. | `.wavefoundry/work/24buu/upgrade-rehearsal.md` item 7 |
| 2026-11-24 | Revised before readiness approval from the red-team primer: the change takes effect after 1.52.0 is installed (F5), and the MCP primary opts out with `--no-auto-cleanup` (F8). | `.wavefoundry/work/24buu/readiness/red-team.md` |
| 2026-11-24 | Bounded readiness repair (cycle 1) for AR-1, AR-3, QA-6, DC-1 and DC-4: the release-zip entry and gate resume also auto-clean and the bridge recovery report says so; the MCP environment variable is also an opt-out; restart-required, retained-checkpoint, real-child and single-result ACs added; the seed paragraph is revised in place; architecture docs named. | `.wavefoundry/work/24buu/readiness/repair-1.md` |
| 2026-11-24 | Readback: after confirmed publication, a CLI primary or gate resume runs the target's installed cleanup in a fresh process. MCP and retained recovery keep their continuation. | Runner, MCP handler, bundle, seed 160, project prompt, architecture, Windows guidance and changelog. Gapfill: used exact source and fixture reads after MCP retrieval to trace both transaction-release points and the final bundle report. |
| 2026-11-24 | The CLI delegates only after releasing its lifecycle transaction. Cleanup emits the terminal result, and the bundle confirms that result against checkpoint removal. | Ten focused tests passed on macOS, including extraction followed by a real cleanup child, gate resume, the protocol-2 release entry, retained recovery and both MCP opt-outs. The direct-entry fixture supplies the primary publication checkpoint. The separate primary fixture exercises extraction with bounded index work. Native Windows, Linux and WSL2 share the child runner and were not exercised here. |
| 2026-11-24 | Seven mutations failed their specific tests: disabling the primary child kept the lock, bypassing the old-host opt-out or restart receipt started cleanup prematurely, swallowing the child exit lost status 19, dropping the MCP flag changed its argv, skipping resumed cleanup left the lock, and misclassifying ZIP cleanup returned the wrong recovery. | CLI primary, opt-out, retained-continuation, failure and gate-resume tests in test_upgrade_wavefoundry, storage-pause handler test in test_server_tools, protocol-two cleanup test in test_upgrade_protocol. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | The CLI runs cleanup itself. | Operator: "have the CLI run cleanup too". | Keep the manual step (documented design until now). |
| 2026-11-24 | Selected: a fresh cleanup child after a clean primary phase, skipped for retained continuations and when the MCP handler passes `--no-auto-cleanup`. Efficacy: replaying the rehearsal shape on a 1.52.0-to-later hop, the primary published the index with no continuation, so cleanup would run and the manual step disappears; on the 1.51.0 hop the old primary prints today's message, which the release notes cover. It controls the outcome on the CLI and leaves MCP sequencing intact. | Planner default after red-team F5 and F8. | Run cleanup in-process: the primary holds the old module. Detect MCP from an environment variable: not set on every MCP primary invocation, so an explicit flag is clearer. |

## Risks

| Risk | Mitigation |
| --- | --- |
| An agent relied on editing files while the upgrade lock was held. | The MCP path already cleans up before the editing pass; guidance points at `--update-index` for later edits. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
