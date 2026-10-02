# Dependency Installs Go Through uv Only

Change ID: `1zli9-enh dependency-installs-uv-only`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-02
Wave: 1zls6 dependency-installs-uv-only

## Rationale

`wf setup` and the upgrade install missing Python dependencies through uv with the 21-day package-age guard (`--exclude-newer`). When no uv exists and the hash-pinned uv bootstrap fails (a refused hash, a network failure, a timeout, or a platform with no uv wheel), `setup_index._install_deps` falls back to a plain `pip install` of the dependencies with no age guard. That fallback silently drops the one supply-chain control the installer applies to dependencies, on exactly the machines where something already went wrong. MCP startup installs are already uv-only (`install_requirement_specs` refuses without uv); this change makes operator-run setup match.

The operator decided (2026-10-02): remove the plain-pip dependency fallback; keep the hash-pinned uv bootstrap, which uses pip only to fetch the pinned uv wheel and never for dependencies; keep honoring operator index settings (`UV_INDEX_URL`, `UV_EXTRA_INDEX_URL`, a user- or system-level `uv.toml`). No binary-only or hash-lock tightening in this change.

This reverses the 1zimd decision "keep the plain-pip fallback after a failed hash bootstrap", by operator direction.

## Requirements

1. **No dependency install without uv.** When `_install_deps` finds no uv in the tool environment or on `PATH` and `_bootstrap_uv` returns `None`, it installs nothing and exits setup with `SystemExit(2)` after one stderr message. The message says: dependencies are installed only through uv with its package-age guard; uv could not be found or installed; rerunning `wf setup` retries the pinned, hash-verified uv bootstrap once network, proxy or TLS access to the package index works (an index mirror must be configured for both: pip's settings for the bootstrap, and `UV_INDEX_URL` for the dependency install, since uv does not read pip's settings); or install uv through one of its official methods (the standalone installer at https://docs.astral.sh/uv/, an OS package manager, or `pipx install uv`) so it is on `PATH`; and do not install the dependencies with pip by hand, which bypasses the age guard. On Windows the message names the `wf.cmd` form. Nothing is installed on this path; the refusal is raised inside the held install lock, which the context manager releases.
2. **The bootstrap stays and stops promising a fallback.** `_bootstrap_uv` keeps its hash-pinned wheel install (`--require-hashes --only-binary :all: --no-deps` against `UV_BOOTSTRAP_WHEEL_SHA256`), its deadline and its `None` return on failure. Its timeout message (and the comment above it, which calls uv optional) no longer says setup falls back to plain pip; it says setup cannot continue without uv and keeps the `setup.uv_bootstrap_timeout_seconds` tuning hint. `_uv_bootstrap_failed` is unchanged. The `installer = "uv" if uv is not None else "pip"` choices in `_install_deps`'s timeout and failure messages become uv-only, and `ensure_deps`'s "pip installed into a different environment" text names the installer neutrally.
3. **Unchanged behaviour.** The uv install command (`--exclude-newer` cutoff, `_uv_config_args`, `_uv_install_env`, the tool-venv-base working directory, the dependency-install deadline and lock) is unchanged. An existing uv of any version is still used as-is. Operator index environment variables and user- or system-level uv config still apply; repository uv config stays ignored. MCP startup installs (`install_requirement_specs`) are unchanged.
4. **Every `_install_deps` caller fails closed the same way.** `_install_deps` has two callers, `ensure_deps` (which also installs the GPU and CUDA packages planned into its missing list) and `ensure_migration_deps` (the lancedb install); they are reached from `setup_index.main`, `upgrade_wavefoundry._provision_upgrade_dependencies`, the upgrade migration step and `setup_reconciliation.prepare`. Each reaches the single refusal; no other dependency install uses pip (the only remaining pip call is the hash-pinned bootstrap). The upgrade already classifies `SystemExit` as a dependency failure and skips the index update or migration.
5. **Docs.** `README.md` (the two sentences that promise a pip fallback), `docs/contributing/build-and-verification.md` (Package-age guard paragraph), `docs/architecture/threat-model.md` (uv bootstrap row known limits), `docs/architecture/decisions/1zcxi-adr startup-dependency-install.md` (the sentence that the pip fallback stays available to operator-run setup gains a dated note that wave `1zls6` removed it), the `_install_deps` docstring (the `install_requirement_specs` docstring already says it never falls back to pip and is verified unchanged), and the CHANGELOG (a `### Changed` bullet; the existing Unreleased 1zimd bullet's "falling back to plain pip" clause is corrected, since that behaviour never ships) describe uv-only installs.

## Scope

**Problem statement:** a failed or impossible uv bootstrap silently downgrades dependency installs to plain pip with no package-age guard.

**In scope:**

- Removing the plain-pip dependency branch in `_install_deps` and replacing it with the fail-closed refusal.
- The `_bootstrap_uv` timeout message.
- Docstrings, docs and CHANGELOG listed in Requirement 5.
- Tests that reach the plain-pip path today. In `test_setup_index.py`: `test_install_deps_carries_pinned_spec`, `test_install_deps_invokes_pip_via_venv_python`, `test_install_deps_does_not_use_break_system_packages`, `test_install_deps_exits_on_pip_failure`, `test_install_deps_timeout_fails_loud_with_network_guidance`, `test_install_deps_forwards_configured_timeout` and `test_install_deps_timeout_message_names_the_cap` get an explicit fake uv (so they keep their coverage, including the dependency deadline, and stop depending on whether uv is on `PATH`); `test_pip_fallback_runs_from_the_venv_base` becomes a refusal test; the `uv=None` half of `test_a_relative_interpreter_path_is_made_absolute` asserts the refusal; `test_a_failed_hash_bootstrap_is_reported_and_setup_falls_back_to_pip` becomes the end-to-end detector (real bootstrap failing, exactly one `--require-hashes` call, then `SystemExit(2)` and the refusal text); `test_bootstrap_uv_timeout_falls_back_with_loud_message` is renamed and asserts no fallback text. In `test_startup_install.py`: `test_every_installer_child_resolves_relative_path_settings_first` gets a uv.

**Out of scope:**

- Binary-only installs (`--only-binary :all:`) and hash-locked dependency installs.
- Pinning installs to PyPI or ignoring operator index settings.
- Removing the hash-pinned uv bootstrap or requiring a preinstalled uv.
- `_pip_tls_env`, which the bootstrap still uses.
- MCP startup installs.
- The upgrade's FAILED summary line, which names network access but not installing uv; the stderr refusal carries the uv guidance.
- The `pip install watchdog` hint in `indexer.py` (an optional watch-mode tool, not a setup dependency).

## Acceptance Criteria

- [x] AC-1: With no uv found and the real `_bootstrap_uv` failing, `_install_deps` runs exactly one install command (the `--require-hashes` bootstrap), then raises `SystemExit(2)` and prints the Requirement 1 message (rerun guidance, `UV_INDEX_URL`, the official uv install methods, and the warning not to pip-install dependencies by hand); with `_bootstrap_uv` stubbed to `None`, it runs no install command at all.
- [x] AC-2: When the bootstrap succeeds, or uv already exists, the uv install command is byte-identical to before (`--exclude-newer`, config args, environment, working directory, deadline).
- [x] AC-3: The `_bootstrap_uv` timeout message no longer mentions a pip fallback, says setup cannot continue without uv, and keeps the timeout tuning hint; the hash refusal message is unchanged; no `_install_deps` or `ensure_deps` message names pip as the installer.
- [x] AC-4: A source-level test of `setup_index.py` finds exactly one `"-m", "pip", "install"` command, inside `_bootstrap_uv` and carrying `--require-hashes`; reintroducing the old dependency fallback command fails it.
- [x] AC-5: `README.md`, the build-and-verification paragraph, the threat-model row, the 1zcxi ADR note, both docstrings and the CHANGELOG describe uv-only dependency installs and no longer promise a pip fallback.
- [x] AC-6: The tests listed in Scope keep their coverage with an explicit fake uv (none passes vacuously through the refusal), and the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Replace the plain-pip branch in `_install_deps` with the fail-closed refusal.
- [x] Update the `_bootstrap_uv` timeout message.
- [x] Confirm the `_install_deps` caller census in Requirement 4 still holds.
- [x] Update the tests listed in Scope (fake uv, refusal and end-to-end detector); add the AC-4 source guard.
- [x] Make the installer messages uv-only, update the `_install_deps` docstring, `README.md`, build-and-verification, the threat model, the 1zcxi ADR and the CHANGELOG.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| uv-only | implementer | none | setup_index.py, test_setup_index.py, docs |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_startup_install.py`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/threat-model.md`
- `docs/architecture/decisions/1zcxi-adr startup-dependency-install.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` (uv bootstrap row) and the `1zcxi` ADR note. No boundary or flow change: the installer already prefers uv; this removes its unguarded alternative.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The refusal is the change. |
| AC-2 | required | The normal uv path must not change. |
| AC-3 | important | Messages must not promise a removed fallback. |
| AC-4 | important | Keeps the fallback from coming back unnoticed. |
| AC-5 | important | Docs and the CHANGELOG must not describe a removed path. |
| AC-6 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Delivery review repair. `test_install_deps_invokes_pip_via_venv_python` now pins `--exclude-newer` with a date-shaped cutoff and the `_uv_install_env` environment on the setup uv install (both previously unpinned; reviewer mutations C and F survived); the `test_server_tools` subprocess-isolation guard now checks `--python str(venv_python)` and no `pythonw` inside `_install_deps` only, instead of anywhere in the file (mutation A2 survived because the startup installer carries the same text). CHANGELOG now says the upgrade reports a dependency failure rather than exiting 2; the 1zcxi ADR alternatives entry says the pip fallback existed before this wave. Accepted without change: the `wf setup` wording (without the `wf.cmd` form) in the uv failure and bootstrap timeout messages matches every other message in `setup_index.py`. | Mutations C, F and A2 now fail named tests in a scratch copy; `test_setup_index`, `test_server_tools` OK |
| 2026-10-02 | Coordinator follow-up: the uv install failure message no longer says "install manually"; it says to fix the cause (usually index access) and rerun `wf setup`, and not to install the dependencies with pip by hand. `test_install_deps_exits_on_pip_failure` pins both. | `test_setup_index`, `test_startup_install` OK |
| 2026-10-02 | Implemented. `_install_deps` now refuses when no uv is found and `_bootstrap_uv` returns `None`: it prints `_uv_required_message()` (Requirement 1 content; the Windows form names `.\.wavefoundry\bin\wf.cmd setup`, chosen by `os.name == "nt"` as elsewhere in `setup_index`) and raises `SystemExit(2)` before any install; the uv command, environment, working directory and deadline are unchanged. The `_bootstrap_uv` timeout comment and message no longer promise a fallback and say setup cannot continue without uv, keeping the `setup.uv_bootstrap_timeout_seconds` hint; `_uv_bootstrap_failed` unchanged. Timeout and failure messages name uv only; `ensure_deps` says "the installer wrote into a different environment". `install_requirement_specs` docstring verified unchanged (already says it never falls back to pip). Caller census confirmed: `_install_deps` is called only from `ensure_deps` and `ensure_migration_deps`, both inside `_held_install_lock`. Tests: the seven listed tests use an explicit `FAKE_UV` (and now assert the uv command ran exactly once); `test_pip_fallback_runs_from_the_venv_base` became `test_no_uv_refuses_without_running_any_install`; the `uv=None` half of `test_a_relative_interpreter_path_is_made_absolute` asserts the refusal; the end-to-end detector is `test_a_failed_hash_bootstrap_is_reported_and_setup_refuses_to_install` (real `_bootstrap_uv`, `_run_install_step` stubbed so pip fails: exactly one `--require-hashes` call, then `SystemExit(2)` and the refusal); the timeout test is renamed `test_bootstrap_uv_timeout_is_loud_and_promises_no_fallback`; new `test_the_refusal_names_the_windows_command_form`, `test_every_install_deps_caller_refuses_inside_the_held_lock` (both callers, lock released, no install) and the AC-4 AST guard `test_the_only_pip_install_is_the_hash_pinned_uv_bootstrap`; `test_every_installer_child_resolves_relative_path_settings_first` gets a uv. Census miss found by the full suite: `test_server_tools.FrameworkWideSubprocessIsolationGuard.test_setup_index_resolver_and_venv_bootstrap_keeps_unchanged` pinned the removed `cmd = [str(venv_python), "-m", "pip", "install"]`; repointed at the bootstrap spawn and the uv `--python` target (same intent: plain venv interpreter, no pythonw). Failing-first: 7 failures and 1 error in `test_setup_index.py` before the code change, all passing after (`test_setup_index.py` 193 OK, `test_startup_install.py` 61 OK, `test_server_tools.py` 375 OK). Full suite in a scratch copy: default `--no-cache` 10595 tests across 154 files OK, `--profile second` 10592 OK, `--profile declared` 10595 OK (the earlier run, before the `test_server_tools` repoint, failed only that guard in all three). Mutations in a scratch copy: restoring the plain-pip else-branch fails the AC-4 guard and the end-to-end detector (6 failures); restoring "Falling back to plain pip" in the timeout message fails the renamed timeout test; dropping the uv install link or the "do not install with pip by hand" sentence each fail 6 refusal tests; removing the fake uv from the seven listed tests fails all seven, and from the startup test fails it. Docs: README (two sentences), build-and-verification Package-age guard paragraph, threat-model uv bootstrap row, 1zcxi ADR dated note, `_install_deps` docstring, CHANGELOG `### Changed` bullet and the corrected 1zimd bullet; `wf_validate_docs` passes. Gapfill: shell grep used to locate the listed test definitions and to sweep the tests folder for remaining pip-command pins after the full-suite failure. | `setup_index.py`, `tests/test_setup_index.py`, `tests/test_startup_install.py`, `tests/test_server_tools.py`, docs listed; scratchpad `1zls6-failing-first.txt`, `1zls6-after.txt`, `1zls6-mut/*.txt`, `1zls6-full2-*.txt` |
| 2026-10-02 | Planned from the operator's choices: remove the plain-pip dependency fallback; keep the hash-pinned uv bootstrap; keep honoring operator index settings; no binary-only or hash-lock tightening. | Operator answers, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Remove the plain-pip dependency fallback; setup fails closed without uv | Operator direction: the fallback silently drops the package-age guard on the machines where something already failed | Keep the fallback with a warning (the 1zimd decision, now reversed) |
| 2026-10-02 | Keep the hash-pinned uv bootstrap through pip | Operator choice: pip fetches only the pinned, hash-verified uv wheel, never dependencies, and fresh machines keep working without a manual uv install | Require a preinstalled uv |
| 2026-10-02 | Keep honoring operator index settings | Operator choice: enterprise mirrors and proxies keep working; repository uv config stays ignored | Pin installs to PyPI |
| 2026-10-02 | The refusal message points at official uv install methods and warns against pip-installing dependencies by hand | Readiness security seat: a vague refusal invites an operator workaround that skips the age guard (or the bootstrap hashes) | A short message naming only the docs link |
| 2026-10-02 | No binary-only or hash-lock tightening in this change | Operator choice | `--only-binary :all:`; a universal hash-pinned lock with `--require-hashes` |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A machine that cannot reach the index for the uv wheel, but could install dependencies through a pip-only mirror, can no longer complete setup | The refusal names both recoveries (install uv onto `PATH`, or fix index access); a preinstalled uv is always used |
| A platform with no published uv wheel can no longer set up through the bootstrap | Installing uv by another route (its standalone installer) puts it on `PATH`, which setup uses as-is |
| Windows locked-down machines without uv | Same recovery; the message names the `wf.cmd` form. Behaviour is otherwise identical on Windows, macOS, Linux and WSL2 |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
