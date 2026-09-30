# Setup Follows An Upgrade And A Pull

Change ID: `1zcm3-enh setup-after-upgrade-and-pull`
Change Status: `implementing`
Owner: Engineering
Status: active
Last verified: 2026-09-29
Wave: 1zfd9 setup-after-upgrade-and-pull

## Rationale

Wave `1zc7n` made `psutil` a required dependency. A repository reaches a framework version with new requirements in two ways, and neither handles it well today:

- **`wf upgrade` / `wf_upgrade`.** The upgrade installs missing packages only as a side effect of Phase 4: `phase_index_update` starts the new `setup_index.py`, whose `main` calls `ensure_deps` (and calls `ensure_deps` in-process only when a storage migration is required). If that install fails (offline, proxy or TLS interception, application control), the upgrade reports "Index publication FAILED … Recover with index_build", which is the wrong remedy. `wf setup` appears only as an unstructured log line from `_record_setup_baseline` / `phase_cleanup`: not in `_build_upgrade_summary`, and not in `upgrade_handlers._upgrade_next_step`, which says only "Call wf_reload_mcp()".
- **`git pull` of a teammate's committed upgrade.** No upgrade code runs. A running MCP server reports `loaded_code_stale` with a `restart` action and cannot see requirements added on disk (`setup_readiness` binds `REQUIRED_IMPORTS` at import). After the restart, `server.py` assesses before activation, finds `dependencies_missing`, and exits because `startup_blocked` is set; the `wf setup` guidance goes only to stderr, so the host shows a failed MCP server. Only Claude Code's `wf-session-start` hook reports it to the agent.

The operator decided (2026-09-29) that both paths must end with the declared dependencies installed or a clear `wf setup` recommendation, and that the MCP server installs missing or version-incompatible declared dependencies itself at startup: in the background when the server can run without them, before starting otherwise; through uv only; with no opt-out. This narrows the report-only rule of wave 1yzcz for that one case.

## Requirements

0. **Every platform.** Behaviour is the same on Windows, macOS, Linux and WSL2. The startup install uses the tool venv resolved by `venv_bootstrap` (per user, shared by every repository on the machine), uv with the existing `--exclude-newer` 21-day guard and TLS environment (`_uv_install_env`), and the stdlib-only `runtime_lock.RuntimeFileLock`. No new dependency.
1. **Startup install (pull path).** In `server.py`'s executable entry (not `--dry-run`, which never installs):
   1. **Trigger.** `_assess_startup` returns `startup_blocked`, a `dependencies_missing` reason is present, and none of `environment_missing`, `environment_incompatible`, `framework_missing`, `recovery_pending`, `recovery_unproven`, `loaded_code_stale`, `assessment_unproven`, `probe_timeout` or `inputs_changed` is present. Non-blocking reasons that a pull also produces (`setup_inputs_changed`, `producer_changed`, `index_*`, `model_changed`, `configuration_*`, `surface_*`) do not prevent the install.
   2. **What.** Exactly the requirement specs the assessment reports under `dependencies_missing`, absent or at a version outside the pin; `assess_setup` exposes them as a structured list on that reason (additive field). A new `setup_index` function installs a given spec list into the existing `venv_bootstrap.tool_venv_python()`: it never calls `_bootstrap_venv`, never creates or recreates the venv, never adds accelerator packages the assessment did not report, catches the installer's `SystemExit`, and does not import `sqlite_runtime` (which activates the tool venv). `setup_index` is imported lazily, on the install path only.
   3. **When.** `setup_requirements` declares `STARTUP_DEFERRABLE_IMPORTS`, the packages the server imports lazily and runs without (initially the `psutil` requirement; a test pins that no module imported at server start imports them at module level). If every reported spec is deferrable, the server starts the MCP transport and installs in a background thread; progress and outcome show in the setup notice and `wf_server_info`. While a startup background install is pending or running, `process_info._load` does not import the package and raises `ProcessInfoUnavailable` saying the startup install is in progress (a flag the runner publishes); after the install finishes it imports normally, so the next call after a successful install loads the installed version. If the package was already imported in this process before the install (only possible when the flag could not be published), the replacement takes effect after a restart and `wf_server_info` says so. The background thread keeps its record in the runner under a lock and republishes it to the current `server_impl` (through `_record_runner_identity`), so a `wf_reload_mcp` during the install does not publish stale state. Otherwise it installs before starting, before `server_impl` is imported, after printing one stderr line naming the packages and "if startup is interrupted, run `wf setup`". A foreground lock waiter polls for at most `STARTUP_INSTALL_LOCK_WAIT_SECONDS` (a named constant) before reporting the install as busy.
   4. **uv only.** Startup installs only through an existing uv (in the tool venv or on PATH, resolved through an injectable path seam for tests) with `--exclude-newer`, passing the operator's own user- or system-level `uv.toml` explicitly with `--config-file`, or `--no-config` when there is none, so no repository `uv.toml` or `[tool.uv]` applies even when the tool venv lives inside a checkout (uv environment variables still apply); it also runs from the tool-venv base. It never bootstraps uv and never falls back to pip; without uv it installs nothing and keeps today's block (foreground) or notice (background) with the `wf setup` guidance. `wf setup` keeps its pip fallback for operator-run installs.
   5. **Stdout stays clean.** Nothing reaches stdout before or outside the MCP protocol: the installer's Python output goes to `sys.stderr`, and every installer child runs with its stdout on fd 2 (`stdout=sys.stderr`, or fd 1 duplicated onto fd 2 for the install and restored before the transport starts). `contextlib.redirect_stdout` alone is insufficient because children inherit fd 1. The background install passes `stdout=sys.stderr` to each child and never touches fd 1, and it starts only after `_isolate_native_stdout_from_protocol`. Importing `setup_index` runs `cli_stdio.configure_utf8_stdio()`; the import happens before the transport starts (foreground) or is shown not to disturb the protocol streams (background).
   6. **One installer at a time.** Every change to the tool venv (its creation or recreation, and every `setup_index` dependency install: `wf setup`, `setup_index.main`, the upgrade dependency step, startup) takes one OS lock (`runtime_lock.RuntimeFileLock`) stored beside the tool-venv base, not inside it, at the resolved base (so a per-user `~/.wavefoundry` that is a symlink or junction is not subject to the repository `.wavefoundry` link refusal), held by the installing process until `run_with_tree_kill` has reaped or killed the installer tree (on POSIX the carrier fd is also inherited by the installer child; a parent killed mid-install on Windows releases it early, a documented limit). Lock errors (`RuntimeLockError`, an `OSError`) fail closed everywhere: nothing is installed or recreated without ownership. A read-only check that finds nothing to install and no venv to create or recreate takes no lock, so it does not fail on lock errors; when it finds work, the lock is taken and the check repeats under it. A foreground startup waiter polls non-blocking within its budget; any waiter reassesses after acquiring the lock instead of installing again. `runtime_lock.py` joins the stdlib-only guard list in `tests/test_process_info.py`.
   7. **Bounded and final.** The install uses `setup.dep_install_timeout_seconds`. If the reassessment after a reported-successful install is still blocked, the server exits once (foreground) or reports once (background) with that reason and `wf setup`; it does not retry in a loop. On Windows, a failure to replace a loaded extension names stopping other Wavefoundry hosts, index builds and the dashboard.
   8. **Visible.** The runner records the startup install (packages, mode foreground or background, outcome) and publishes it beside `_SETUP_STARTUP_RESULT` so it survives `wf_reload_mcp`; `wf_server_info` reports it. `_STARTUP_ASSESSMENT` is replaced by the reassessed result. The startup install writes no setup stamp itself; after a foreground install the reassessed result goes to `_adopt_setup_baseline`, which may write its usual `adopted` stamp when the result is ready.
2. **Running server after a pull.** When `assess_setup` reports `loaded_code_stale`, the setup notice and `wf_server_info` keep `restart` first and add that the restarted server attempts to install any newly required dependencies at startup, and to run `wf setup` if it fails to start. (The running server cannot see requirements added on disk.) This applies to pulls after the version that ships it.
3. **Upgrade dependency step.** A helper called at the top of `phase_index_update` and `phase_index_rebuild` (so also `phase_index_update_parent_owned` and the `--update-index`, `--rebuild-index` and `--resume-after-memory` sites) provisions dependencies through `setup_index` under the lock of Requirement 1.6. It catches `SystemExit`, `RuntimeError` and `OSError`, records `dependency_provisioning_failed` in the upgrade lock, skips the Phase 4 children, and leaves `index_update` as not run rather than publication failed. `wf_upgrade_response` adds a `dependency_provisioning_failed` diagnostic naming `wf setup`, detected like `index_publication_failed`. `setup_index` is imported function-locally (`upgrade_wavefoundry` is in `MANDATORY_FEATURE_MODULES`).
4. **Upgrade summary and next step.** `_record_setup_baseline` returns its assessment; when `index_update_failed` is set, `phase_cleanup` still assesses (without stamping). The cleanup summary carries flat fields `setup_status` (`ready`, `action_required`, `indeterminate`, `not_assessed`), `setup_reasons` (list of reason codes) and `setup_command` (string or null), per the flat-field rule of ADR `1u49j`; they are `not_assessed` on the `failed_phase` path and in the primary-phase `--emit-summary` and degradation payloads. `SUMMARY_SCHEMA_VERSION` stays 1; the scalars join the bounded summary's terminal keys so the response bounder keeps them. `_print_operator_summary` prints them. After cleanup, when `setup_status` is not `ready`, `wf_upgrade_response` (reading the raw parsed summary, as `_cutover_restart_required` does) recommends `setup_command` before `wf_reload_mcp` in `next_step`, with the ask-first sentence used by `setup_not_ready_diagnostic`, and lists it in `next_tools`.
5. **Policy and docs.**
   - Seed `050-agent-entry-surface-bootstrap.prompt.md` and `AGENTS.md` narrow the install-never rule to the startup exception, keeping the "Check readiness after Git changes" section byte-identical (`ReadinessGuidanceParityTests`); checks, the session-start hook and `index_health` still report and ask.
   - The `wf-session-start` hook message for `dependencies_missing` says the MCP server attempts to install them at startup and to run `wf setup` if it fails to start; `.claude/hooks/wf-session-start.py` is re-rendered (`test_checked_in_settings_carry_the_hook`).
   - Seed `160-upgrade-wavefoundry.prompt.md` and `docs/prompts/upgrade-wavefoundry.prompt.md` describe the dependency step, the summary's setup fields, the pull path, the startup exception in "Post-Git readiness instruction reconciliation", and the transition runs (Requirement 6).
   - `docs/specs/mcp-tool-surface.md` narrows "No automatic setup, dependency install or storage recovery is triggered" to the startup exception and documents the `wf_server_info` field, the `wf_upgrade` next step and the `dependency_provisioning_failed` diagnostic.
   - `docs/architecture/domain-map.md` ("Local setup assessment"), `docs/architecture/layering-rules.md` (the startup install runs as a child; the parent never activates the tool environment), `docs/architecture/data-and-control-flow.md` (startup sequence) and `docs/contributing/build-and-verification.md` (checks still never execute repairs) are updated.
   - A new ADR records the decision, the trust model (the installed specs come from the checkout's own `setup_requirements.py`, the same code the host already runs; the package index follows the operator's uv configuration; the startup install ignores the repository's own uv configuration (Requirement 1.4), while `wf setup` does not) and the accepted shared-venv re-pinning risk, with an entry in `docs/architecture/decisions/README.md`.
   - `CHANGELOG.md`: the Unreleased 1zc7n psutil operator note is rewritten for the dependency step and the startup install, and an entry is added for this change.
6. **Transition disclosure.** The summary's setup fields are produced by the new-code `--cleanup` process, so they apply on the installing upgrade (CLI and MCP). The dependency step lags one upgrade on the default path of both `wf upgrade` and `wf_upgrade()`, because the pre-extraction orchestrator runs Phase 4 in-process; it applies immediately only when Phase 4 runs as a separate new-code process (`--update-index`, `--rebuild-index`, `--resume-after-memory`). On the transition run, installs still happen through `setup_index.main`'s own `ensure_deps` in the Phase 4a child. The `wf_upgrade` `next_step` change is computed by the running server's handler, so on the MCP path it applies after `wf_reload_mcp` or a restart onto the new code; the installing upgrade shows the old next step. The docs name these runs so they are not reported as the fix failing.

## Scope

**Problem statement:** a framework version that adds or re-pins a required package can leave a repository without it, after an upgrade whose install failed or after a pull, with the MCP server refusing to start and no clear remedy reaching the agent.

**In scope:**

- `server.py` startup install, `setup_readiness` structured missing list and stale-code notice, `setup_requirements.STARTUP_DEFERRABLE_IMPORTS`, a `setup_index` spec-list installer and the shared install lock, `wf_server_info` field.
- `upgrade_wavefoundry.py` dependency step and summary fields; `wf_server/upgrade_handlers.py` next step and diagnostic.
- `render_platform_surfaces` session-start hook message and the rendered hook.
- Seeds 050 and 160, `AGENTS.md`, the upgrade prompt, the spec, the architecture docs and ADR, `build-and-verification.md`, `CHANGELOG.md`.
- Tests for each.

**Out of scope:**

- Creating or recreating the tool venv at startup, index rebuilds, model downloads.
- An operator opt-out (operator decision).
- Git hooks; changing which packages are required.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/setup_requirements.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.claude/hooks/wf-session-start.py`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/domain-map.md`
- `docs/architecture/layering-rules.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/decisions/README.md`
- `.wavefoundry/framework/scripts/process_info.py`
- `docs/contributing/build-and-verification.md`

Root files also edited: AGENTS.md and CHANGELOG.md.

## Acceptance Criteria

- [x] AC-1: with the tool venv present, a setup stamp whose sources differ (`setup_inputs_changed` alongside `dependencies_missing`) and a non-deferrable declared package absent, starting `server.py` installs it before starting and then serves MCP requests; the fake installer is a child process that writes to its own stdout, and no bytes reach the MCP stdout outside the protocol.
- [x] AC-2: with only deferrable packages missing (absent or version-incompatible), the server starts first, installs in the background, and `wf_server_info` shows the background install and its outcome; `process_info` reports the install in progress while it runs (including when `index_health` or `wf_server_info` is called during it) and succeeds on the next call after it; a version-incompatible package is replaced and loaded at its new version.
- [x] AC-3: with the install failing, timing out, or no uv available, the server exits (foreground) or reports (background) with the failure and `wf setup`, without pip; with any excluded reason present, or under `--dry-run`, no install is attempted; a reported-successful install that still reassesses as blocked exits once without retrying.
- [x] AC-4: two concurrent installers into one tool venv (two startups, or a startup and `wf setup`) perform one install; the waiter reassesses without installing.
- [x] AC-5: with `loaded_code_stale` reported, the notice keeps `restart` first and says the restart attempts to install newly required dependencies; a test covers a requirement present on disk but unknown to the loaded code.
- [x] AC-6: an upgrade whose dependency step fails reports `dependency_provisioning_failed` naming `wf setup`, skips the Phase 4 children, and does not report an index publication failure.
- [x] AC-7: the cleanup summary carries `setup_status`, `setup_reasons` and `setup_command` (also when the index update failed), they survive the response bounder, `SUMMARY_SCHEMA_VERSION` is unchanged, the primary-phase summary reports `not_assessed`, and after cleanup with setup not ready `wf_upgrade`'s `next_step` and `next_tools` recommend the command before `wf_reload_mcp`.
- [x] AC-8: the session-start hook's `dependencies_missing` message says the MCP server attempts the install at startup and to run `wf setup` if it fails; the checked-in hook matches the renderer.
- [x] AC-9: the documents in Requirement 5 state the narrowed rule, the pull path and the transition runs; seed 050 and `AGENTS.md` stay byte-identical in the readiness section; docs validate.
- [x] AC-10: the change's own suites and every test it adds pass, and no failure elsewhere is attributable to this change.

## Tasks

- [x] `setup_readiness`: structured missing-spec list on `dependencies_missing`; stale-code notice text.
- [x] `setup_requirements.STARTUP_DEFERRABLE_IMPORTS` and its import-time pin test.
- [x] `setup_index`: spec-list installer (uv only when called from startup, existing venv, fd-level stdout), shared install lock used by every install path.
- [x] `server.py`: trigger, foreground and background paths, reassessment, runner record; `wf_server_info` field.
- [x] Upgrade dependency step, lock record, summary fields, operator summary, `wf_upgrade` next step and diagnostic.
- [x] Session-start hook message and re-render.
- [x] Seeds 050 and 160 (seed gate), `AGENTS.md`, upgrade prompt, spec, architecture docs, ADR and index, `build-and-verification.md`, CHANGELOG.
- [x] Tests, including a real-subprocess startup test with a fake uv on every platform the suite runs on (injection through `WAVEFOUNDRY_TOOL_VENV` and a fixture uv, not a shell script).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readiness and installer | implementer | none | `setup_readiness`, `setup_requirements`, `setup_index`, lock |
| Startup install | implementer | readiness and installer | `server.py`, `server_impl` |
| Upgrade step and summary | implementer | readiness and installer | `upgrade_wavefoundry`, `upgrade_handlers` |
| Policy and docs | implementer | all above | Seeds under the seed gate |
| Review | code, release, docs-contract, security, architecture reviewers | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/seeds/`

Root release note: CHANGELOG.md.

## Affected Architecture Docs

- `docs/architecture/domain-map.md`: "Local setup assessment" gains the startup installer and the shared install lock.
- `docs/architecture/layering-rules.md`: pre-activation startup may start an installer child; the parent still never activates the tool environment.
- `docs/architecture/data-and-control-flow.md`: MCP startup sequence with the foreground and background install.
- `docs/architecture/decisions/`: a new ADR for the startup install (first recorded decision on the setup-readiness install rule of wave 1yzcz), indexed in `README.md`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The pull path's fix |
| AC-2 | required | Host startup timeouts |
| AC-3 | required | Failure stays clear, bounded and guarded |
| AC-4 | required | Shared venv, concurrent hosts |
| AC-5 | required | Running server after a pull |
| AC-6 | required | Correct remedy on upgrade failure |
| AC-7 | required | The upgrade path's recommendation |
| AC-8 | important | Claude Code session start |
| AC-9 | required | Policy change must be documented |
| AC-10 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-29 | Delivery repair round 1 (seven findings). Startup review: DEL-STARTUP-ENTRY-UNTESTED (end-to-end tests now run the real `__main__` entry via runpy; background-failure case; found and fixed a real race: the background thread now publishes the reassessment before recording its final status). Operator-pasted review: DEL-INSTALL-LOCK-OWNERSHIP (lock errors fail closed; `ensure_deps` / `ensure_migration_deps` take the lock before `_bootstrap_venv`; venv creation and the uv bootstrap pass the carrier on POSIX), DEL-UV-CONFIG-ISOLATION (`_uv_config_args`: operator user/system `uv.toml` via `--config-file`, else `--no-config`; verified against uv 0.12.4 that an explicit file skips discovery), DEL-SETUP-COMMAND-QUOTING (`setup_readiness.format_command`). Upgrade review: DEL-TRANSITION-NOTE-WRONG (CHANGELOG, seed 160, prompt), DEL-PHASE4-TESTS-REACH-INSTALLER (`test_upgrade_wavefoundry` stubs the metadata read module-wide), DEL-UPGRADE-COVERAGE-GAPS (tests for the cleanup flag, delegated summary, oversized bounding, pending-migration raise, no stamp after a dependency failure). Advisories adopted: gate falls back on any exception, lock-wait message, psutil diagnostic during an install, `CalledProcessError` caught, failed-phase flag, spec `restart_required`, code-span backticks (summary value now `run wf setup`). Declined: council alternative to drop the in-process upgrade step (operator-approved design; recorded for the operator). Plan Requirements 1.4 and 1.6 aligned (receipt rotates). Mutants: all reviewer survivors and a revert of each repair are caught (startup 3, lock/config/quoting 5; M5-M9 rerun below). Model choice for the next reverification: most capable model (judges real defects); requested explicitly, observed unknown. Earlier reviewers this wave: requested none (inherited), observed unknown. | `tests/test_startup_install.py`; scratch mut-1zfd9-r1..r3 |
| 2026-09-29 | Delivery repair round 2: DEL-LOCK-LINK-REFUSAL (reverifier, regression from the round-1 lock repair: `ensure_deps` always took the lock, which `runtime_lock` refuses under a linked `~/.wavefoundry`, so `wf setup`, index builds and the upgrade failed even with nothing to install). `ensure_deps` / `ensure_migration_deps` now run a read-only check first (`_venv_needs_bootstrap`, `_missing_in_venv`) and take the lock, then recheck, only when something must change; `dependency_install_lock_path` resolves the base's parent. Advisories adopted: a falsy `UV_NO_CONFIG` keeps isolation on; ADR and CHANGELOG state the user/system `uv.toml` merge limit and the lockless no-op check. Requirement 1.6 aligned (receipt rotates). Mutants (scratch mut-lock): no lockless precheck, no migration precheck, no realpath, any-value `UV_NO_CONFIG`; all caught. The seven round-1 findings were reverified RESOLVED (reverifier requested Opus explicitly for defect judgment; observed unknown). | `tests/test_startup_install.py` LockOwnershipTests, UvConfigIsolationTests |
| 2026-09-30 | Operator-requested fixes for two round-2 advisories (DEL-LOCK-PATH-ADVISORIES). `dependency_install_lock_path` now resolves the whole tool-venv base, so every spelling of a linked venv directory shares one lock beside its real location (plan 1.6 and ADR 1zcxi already say "resolved base"). Resolving the path can raise `OSError` on Windows (a winerror outside `ntpath.realpath`'s allowlist): `install_requirement_specs` now returns a failed outcome naming `wf setup` instead of raising, and `_held_install_lock` builds the lock inside its fail-closed handler, which now catches any `OSError`. Tests: `test_every_spelling_of_a_linked_venv_directory_shares_one_lock`, `test_a_lock_path_that_cannot_be_resolved_fails_closed_without_a_traceback`. Mutants (scratch mut-r3): parent-only resolution, lock built outside the installer's try, handler narrowed to `RuntimeLockError`, held lock built before the try; all caught. | `tests/test_startup_install.py` LockOwnershipTests |
| 2026-09-29 | Full framework suite green on a quiet tree (10100 tests, receipt recorded). The first run failed only `test_tree_kill_routing` (the new installer's timed call was not in the census); registered as routed. Added a gate test for a reported-successful install that still reassesses blocked (AC-3). | `run_tests.py --no-cache` |
| 2026-09-29 | Implemented. `setup_readiness`: `dependencies_missing` carries `missing`; `startup_install_specs`, `missing_dependency_specs`, `STARTUP_INSTALL_EXCLUDED_REASONS`; stale-code notice says the restart attempts the install. `setup_requirements.STARTUP_DEFERRABLE_IMPORTS = {psutil}`. `setup_index`: `install_requirement_specs` (uv only, test seam `_STARTUP_UV_COMMAND`, cwd tool-venv base, child stdout on fd 2, recheck under the lock, statuses installed / already_installed / no_uv / busy / failed, Windows in-use hint), shared lock `dependency_install_lock_path` beside the venv, taken by `ensure_deps` and `ensure_migration_deps` (`_held_install_lock`, blocking; unopenable lock warns and proceeds) with a recheck, carrier fd passed to POSIX installer children. `process_info`: `set_startup_install_pending` gate, `psutil_loaded`. `server.py`: `_startup_install_gate` (foreground before `server_impl` import, background planned with a `startup_install_running` reason, torn-tree tolerant), `_run_background_install` (reassesses, clears the gate, publishes to the handler under its lock), record read by `wf_server_info` through `_SETUP_STARTUP_INSTALL_PROVIDER`. Upgrade: `_provision_upgrade_dependencies` (metadata precheck, then `ensure_deps`; records `dependency_provisioning_failed`) at the top of `phase_index_update` (raises when a storage migration is pending) and `phase_index_rebuild`; `_record_index_publication_outcome` records no publication failure when no child ran; `_record_setup_baseline` returns its assessment and assesses without stamping after a failed index update; flat `setup_status` / `setup_reasons` / `setup_command` and `dependency_provisioning_failed` in the summary and operator prose. `wf_upgrade`: terminal keys, `dependency_provisioning_failed` diagnostic, after-cleanup `next_step` naming `setup_command` with the ask-first sentence; `wf setup` is a CLI command, so `next_tools` leads with `index_health`, which reports the same assessment and command. Hook message and re-rendered `.claude/hooks/wf-session-start.py`. Seeds 050 and 160, `AGENTS.md`, upgrade prompt, spec, domain-map, layering-rules, data-and-control-flow, build-and-verification, ADR `1zcxi` and index, CHANGELOG (1zc7n note rewritten). Tests: new `test_startup_install.py` (29, including real-subprocess MCP startup in both modes and the psutil version-replacement harness); updated `test_setup_index` (lock and recheck), `test_upgrade_wavefoundry` (baseline message), `test_process_info` (`runtime_lock` stdlib guard). Scratch mutants, each caught: no process_info gate, child stdout inherited, no install lock, trigger requiring every reason to be dependencies_missing, never background, upgrade children run after a failed step, no next_step override. Gapfill: code was read with shell `grep`/`sed` because the running MCP server serves pre-change code for the files being edited and `server_impl.py` exceeds the `code_pattern` size limit. | `tests/test_startup_install.py`; scratch `mut-1zfd9/mutate.py` |
| 2026-09-29 | Readiness round 2: every round-1 finding resolved; two new blocks folded in with the reviewer's wording: N1 (`process_info` must not import a deferrable package while a startup install is running, or a version replacement is invisible on POSIX and fails on Windows) and N2 (wave record watchpoints). Advisories adopted: lock lifetime limit, background stdout never touches fd 1, reload-safe install record, `OSError` handling, stamp adoption stated, Windows message names index builds and the dashboard, uv runs from the tool-venv base, uv path seam, named lock-wait budget. | Round-2 readiness report |
| 2026-09-29 | Readiness round 1: code, release, docs-contract, security, architecture and the council (red-team, docs-contract) blocked with corrections, all folded in: trigger accepts non-blocking reasons a pull produces; install exactly the reported specs without `_bootstrap_venv`; fd-level stdout; one lock for every installer; flat summary fields from the cleanup process; corrected transition disclosure; upgrade dependency failure handled; expanded docs list. Operator decided: background install when the server can run without the packages, absent or wrong-version packages, uv only, no opt-out. | Readiness reports for receipt `review-policy-e485af2b4cb98c49ae14` |
| 2026-09-29 | Planned. Investigation found the upgrade installs dependencies only through Phase 4's `setup_index` child, reports install failures as index failures, and never surfaces `wf setup` in its summary or next step; after a pull a missing dependency blocks MCP startup with stderr-only guidance. Operator chose startup auto-install for the pull path. | `upgrade_wavefoundry.phase_index_update`, `_record_setup_baseline`, `_build_upgrade_summary`; `upgrade_handlers._upgrade_next_step`; `setup_readiness.assess_setup`; `server._assess_startup` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-29 | Install in the background when every missing package is deferrable; before starting otherwise | Host MCP startup timeouts can be seconds; a server that can run without the package should not wait for it | Always install before starting (killed by short host timeouts) |
| 2026-09-29 | Startup installs absent and version-incompatible packages | Operator decision: a pull that re-pins a package must also self-heal | Absent only (avoids shared-venv re-pinning between repositories on different framework versions) |
| 2026-09-29 | uv only at startup, no pip fallback, no uv bootstrap | Keeps the 21-day `--exclude-newer` guard for unattended installs | Reuse `_install_deps` with its pip fallback |
| 2026-09-29 | No operator opt-out | Operator decision | An operator-owned environment variable disabling the startup install |
| 2026-09-29 | MCP server startup installs missing declared dependencies when the only blocking reason is dependencies | Operator decision: a pull that adds a requirement must not leave the MCP server unable to start; the installer already exists with age guard, TLS handling and timeout | Start degraded and recommend `wf setup`; keep blocking and only improve the message |
| 2026-09-29 | Upgrade keeps installing dependencies itself, as an explicit step, and reports setup readiness in its summary rather than running a full `wf setup` | The upgrade already provisions dependencies and rebuilds indexes, which are setup's main jobs | Run `wf setup` at the end of every upgrade |

## Risks

| Risk | Mitigation |
| --- | --- |
| Two repositories on framework versions with different pins re-pin the shared tool venv on each host start | Accepted by the operator; the ADR records it; `wf_server_info` shows each startup install; on Windows a locked extension fails with guidance to stop other hosts |
| The host's MCP startup timeout kills a foreground install | Background install whenever the missing packages are deferrable; foreground prints the `wf setup` remedy before starting; the lock is held until the installer tree exits, and the next start reassesses |
| Installer output corrupts the MCP stdio stream | Requirement 1.5 routes all output to stderr at the file-descriptor level; AC-1 uses a child that writes to its own stdout |
| Network use at startup is blocked by proxy, TLS interception or application control on enterprise Windows | Bounded by `dep_install_timeout_seconds`; reports the existing network guidance and `wf setup` |
| A package published minutes ago is installed unattended | uv with the 21-day `--exclude-newer` guard only; no pip fallback or uv bootstrap at startup |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
