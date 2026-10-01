# The Setup and Upgrade Installer Honours Repository uv Config and Bootstraps an Unpinned uv

Change ID: `1zhmd-bug setup-install-isolation`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zicq install-and-permission-hardening

## Rationale

A downstream validation of v1.28.0 (request 2 and 3), verified against the code: the MCP startup installer `setup_index.install_requirement_specs` runs `uv pip install` with `_uv_config_args()` (an operator's user or system `uv.toml`, otherwise `--no-config`) from the tool venv folder, so a target repository's uv configuration cannot apply. The installer behind `wf setup` and every upgrade (`setup_index._install_deps`, reached through `ensure_deps` and `ensure_migration_deps`, which `upgrade_wavefoundry._provision_upgrade_dependencies` and the migration step call) runs `uv pip install` without `_uv_config_args()` and from the inherited working directory, so a repository's `uv.toml` or `[tool.uv]` (an index URL, for example) is discovered and applied to installs into the shared per-user tool environment. When no uv exists, `_bootstrap_uv` runs `pip install uv` unpinned, so it installs whatever uv release is newest, without any age guard. Separately, `setup.dep_install_timeout_seconds` is read from the repository's `docs/workflow-config.json` (`_setup_deadlines`) with only a lower bound, so a repository can hold the foreground install and the shared install lock for as long as it likes.

The plain-pip fallback when uv cannot be found or bootstrapped is a deliberate design (wave `1p9it`: setup must not hang behind TLS-intercepting or flaky proxies) and stays; the operator confirmed this on 2026-09-30, declining the validation's request to fail closed. Network access during install is acceptable.

## Requirements

1. **Repository uv config never applies.** `_install_deps` passes `_uv_config_args()` and runs from `venv_bootstrap.tool_venv_base()`, the same as `install_requirement_specs`, so only the operator's own uv configuration (and uv environment variables) apply. The plain-pip fallback and the uv bootstrap also run from that folder. Because the working directory moves, every path these commands carry (the venv interpreter passed to `--python` and used as the pip program) is absolute, in both `_install_deps` and `install_requirement_specs` (a relative `WAVEFOUNDRY_TOOL_VENV` would otherwise resolve against the new folder). An existing uv too old to accept `--no-config` or `--config-file` fails the install as it already does on the startup path; this is accepted and documented, not worked around.
2. **Pinned uv bootstrap.** `_bootstrap_uv` installs an exact pinned version from one constant (`UV_BOOTSTRAP_REQUIREMENT = "uv==0.12.4"`), not the newest release, as a wheel only (`--only-binary :all:`), so a platform without a published wheel fails quickly instead of attempting a Rust source build of uv's sdist. An existing uv is never replaced: `_uv_bin` keeps preferring the tool venv's uv and then any uv on `PATH`, whatever their versions, and the bootstrap runs only when neither exists.
3. **Bounded lock-held timeouts.** `_setup_deadlines` clamps each deadline that runs under the shared install lock to twice its default: `venv_create_timeout_seconds` 600, `uv_bootstrap_timeout_seconds` 1200, `dep_install_timeout_seconds` 3600 (defaults unchanged); a larger configured value uses the cap. The other deadline keys are unchanged. The `_install_deps` timeout message, which tells the operator to raise the setting, states the cap, and so do the `setup` notes in `docs/workflow-config.json`.
4. **Release checklist.** The "Required Packaging Order" in `docs/prompts/package-wavefoundry.prompt.md` gains a step to review and, when appropriate, bump `UV_BOOTSTRAP_REQUIREMENT` to a uv release that has been public for at least the package-age window. `docs/contributing/build-and-verification.md` (package-age guard paragraph) describes the pinned bootstrap and the config isolation.
5. **Offline startup fails fast and says why.** With no reachable package index, the MCP startup install ends through uv's own network error (measured 2026-09-30 with uv 0.12.4: about 12 s for a refused connection, about 45 s for a black-holed address, exit 2), not the install deadline, and records status `failed`. Its message for a non-zero uv exit names the likely cause (network, proxy or TLS access to the package index; uv's output above has the detail) and still tells the operator to run `wf setup`. The existing blocked-startup and background reporting are unchanged. No opt-out is added.
6. **Platforms.** Windows, macOS, Linux and WSL2 behave the same; the working-directory and argument changes are path-only. The pin must have published wheels for all four.
7. **Transition.** Takes effect for `wf setup` once the release is installed. Whether the installing upgrade's own dependency step already runs the new `setup_index` (upgrade imports it lazily) is verified during implementation, and the CHANGELOG states the verified answer. The CHANGELOG entry goes under `### Fixed` in a new `## [Unreleased]` section.

## Scope

**Problem statement:** the setup and upgrade installer applies a target repository's uv configuration to the shared tool environment, bootstraps the newest uv unpinned, and accepts an unbounded install timeout from the repository.

**In scope:**

- `setup_index._install_deps`, `_bootstrap_uv`, `_setup_deadlines`, `install_requirement_specs` (absolute paths and failure message); tests.
- `docs/workflow-config.json` setup notes.
- `docs/prompts/package-wavefoundry.prompt.md` release checklist; `docs/contributing/build-and-verification.md`; CHANGELOG.

**Out of scope:**

- Failing closed without uv (declined; the pip fallback stays).
- An opt-out for the MCP startup install (validation request 1; not needed: install-time network use is acceptable).
- uv environment variables such as `UV_INDEX_URL` (an operator setting, honoured on every path).

## Acceptance Criteria

- [x] AC-1: `_install_deps` builds its uv command with `_uv_config_args()` and runs it (and the pip fallback) with `cwd` set to the tool venv base and absolute interpreter paths; a repository `uv.toml` above the venv is not read by a real uv run through `_install_deps`.
- [x] AC-2: with no uv in the tool venv or on `PATH`, `_bootstrap_uv` installs exactly `UV_BOOTSTRAP_REQUIREMENT` as a wheel only, from the tool venv base; with an existing uv of any version in either place, no bootstrap runs and that uv is used.
- [x] AC-3: each lock-held deadline above twice its default resolves to that cap (600, 1200, 3600); values at or below it, the defaults and the other keys are unchanged; the timeout message names the cap.
- [x] AC-4: a startup install whose uv exits non-zero reports status `failed` with a message naming network, proxy or TLS access to the package index and telling the operator to run `wf setup`; the Windows in-use hint is still appended on Windows; a real uv against an unreachable index exits on its own well inside the install deadline (recorded evidence).
- [x] AC-5: the release checklist and the build-and-verification guide describe the pin bump and the config isolation.
- [x] AC-6: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Config isolation and working directory in `_install_deps`.
- [x] Pinned bootstrap constant.
- [x] Timeout caps and message.
- [x] Startup failure message.
- [x] Tests for AC-1 to AC-4; offline timing evidence.
- [x] Release checklist, guide and CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Installer hardening | implementer | readiness | |
| Review | code-reviewer, qa-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/tests/test_setup_index.py`, `.wavefoundry/framework/scripts/tests/test_startup_install.py`
- `docs/workflow-config.json` (setup notes only)
- `docs/prompts/package-wavefoundry.prompt.md`, `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

N/A: installer arguments and a configuration bound inside one module; documented in the build-and-verification guide.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Supply-chain isolation of the shared tool environment |
| AC-2 | required | No unaged uv release; never override an existing uv |
| AC-3 | important | Bounded lock hold |
| AC-4 | important | Offline startup reports cleanly |
| AC-5 | required | The pin must be maintained |
| AC-6 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Second post-close finding DEL-1ZICQ-TILDE-CACHE-PATH (external review): the first repair rebased `PIP_CACHE_DIR=~/.cache/pip` to a literal `~` folder because `abspath` ran before pip's own home expansion. Consumer probes: pip's `type="path"` options (`--cache-dir`, `--cert`, `--client-cert`) apply `os.path.expanduser`; uv 0.12.4 reads `UV_CONFIG_FILE` and `UV_CACHE_DIR` literally (real uv: `failed to open file ~/...`, `uv cache dir` prints `~/...`); pip reads `PIP_CONFIG_FILE` without expansion. Repair: `_PIP_EXPANDED_PATH_ENV_VARS` (`PIP_CACHE_DIR`, `PIP_CERT`, `PIP_CLIENT_CERT`) get `expanduser` before rebasing; the rest keep caller-folder rebasing. Tests: real `pip cache dir` from the tool base with the rebased env equals pip from the caller with the original env (`~` and plain relative values); per-variable consumer expectations for all eight settings. Mutations: expanding every variable, and dropping the expansion, each fail | Focused runs; mutation |
| 2026-09-30 | Gapfill: the post-close repair read `_uv_install_env`/`_pip_tls_env` and the three call sites with direct shell reads, because the finding named the exact function and the edit surface was already known from implementation; the call-site census was done by the independent reverifier (only three installer subprocesses run from the tool-venv base) | Reverification 1zicq-reverify-r1 |
| 2026-09-30 | Post-close finding DEL-1ZICQ-RELATIVE-OPERATOR-CONFIG (external review, replayed independently): a relative `UV_CONFIG_FILE` resolved inside the tool-venv base after the cwd move and uv exited 2. Wave reopened; repair: `_installer_env` makes the relative path-valued uv and pip settings (`UV_CONFIG_FILE`, `UV_CACHE_DIR`, `PIP_CONFIG_FILE`, `PIP_CERT`, `PIP_CLIENT_CERT`, `PIP_CACHE_DIR`, `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`) absolute against the caller's folder at all three installer call sites (`_install_deps`, `_bootstrap_uv`, `install_requirement_specs`); the null device and absolute values pass through, and an environment with nothing relative stays inherited. Tests: real-uv relative `UV_CONFIG_FILE` through `_install_deps` (fails before the repair), per-call-site resolution; removing the helper from any call site fails a test; real uv control reproduces `failed to open file`. Build guide sentence added | Focused runs; mutation |
| 2026-09-30 | Full suite round 1: two failures from this wave, both fixed. `test_venv_bootstrap` single-resolver scan flagged two new comments naming the tool-venv environment variable (reworded); `test_review_policy` corpus check found 1zhme's first Serialization Points bullet rejected by the strict parser because of a backticked note (note moved to its own bullet). Delivery advisories taken: `_uv_bin` returns an absolute path for a relative `PATH` entry (test added); the relative-override startup test uses `contextlib.chdir` instead of `os.path.relpath`, which raises across Windows drives. Not taken: `pip --isolated` for the bootstrap, because it would also ignore an operator's `pip.conf` proxy and index settings | Full suite; delivery review |
| 2026-09-30 | Implemented. `_install_deps` passes `_uv_config_args()`, runs uv and the pip fallback from `tool_venv_base()`, and absolutizes the interpreter (`os.path.abspath`, not `resolve`, which would follow the venv symlink to the base interpreter); `install_requirement_specs` absolutizes too and names the network cause on a non-zero uv exit; `UV_BOOTSTRAP_REQUIREMENT = "uv==0.12.4"` installed with `--only-binary :all:` from the venv base; `_LOCK_HELD_DEADLINE_CAPS` (600/1200/3600). Transition verified: the upgrade runner does not load `setup_index` at import (probe: `'setup_index' in sys.modules` False after importing `upgrade_wavefoundry`); `_provision_upgrade_dependencies` imports it lazily after extraction, so the installing upgrade runs the new installer; `isolated_run` takes `**kwargs` and `tool_venv_base` exists in every release from 1.24.0, so the new `cwd=` works under an older runner's `subprocess_util`. Mutation: removing `*_uv_config_args()` from `_install_deps` fails `test_the_setup_install_keeps_a_repository_uv_toml_out_with_real_uv` and `test_uv_install_passes_config_isolation_and_runs_from_the_venv_base`. `test_setup_index.py` 174 OK, `test_startup_install.py` 57 OK (run per file; one process for both swaps `setup_index` via `load_setup_index`, pre-existing) | Focused runs; mutation |
| 2026-09-30 | Readiness round 1: red-team and the lanes approved 1zhmd with notes, now folded in: wheel-only bootstrap from the tool venv base; absolute interpreter paths after the cwd move; old uv without `--no-config` accepted; caps for all lock-held deadlines with the message and workflow-config notes; transition claim verified during implementation; the startup install test file added | Prepare council and lane review |
| 2026-09-30 | Planned from the v1.28.0 downstream validation (requests 2 and 3), verified: `install_requirement_specs` passes `_uv_config_args()` and uses the tool venv base as cwd; `_install_deps` does neither; `_bootstrap_uv` runs `pip install uv`; `_setup_deadlines` bounds only below; callers are `ensure_deps` and `ensure_migration_deps`, which upgrade's dependency and migration steps call; tool venv uv is 0.12.4. Operator: keep the pip fallback; exact pin with a release-checklist bump; an existing uv is never replaced; add the offline startup check as an AC. Measured uv 0.12.4 against an unreachable index: refused 12 s, black-holed 45 s, exit 2; the current message is `uv install failed (exit 2); run \`wf setup\`` | Code reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Keep the plain-pip fallback | Setup must not hang or fail behind TLS-intercepting proxies (wave `1p9it`); enterprise networks matter | Fail closed (validation request) |
| 2026-09-30 | Exact pin, bumped at release | A floor still installs the newest release; a pin installs only an already-public version | `uv>=0.12.4`; `uv>=0.12.4,<0.13` |
| 2026-09-30 | Cap each lock-held timeout at twice its default | One rule bounds every shared lock hold | Cap only the dependency install; no cap |

## Risks

| Risk | Mitigation |
| --- | --- |
| The pin lacks a wheel for a new platform | Wheel-only bootstrap fails quickly and setup falls back to pip with a warning; the release checklist bumps the pin |
| Existing pins on installer source lines (`test_server_tools.py` pip-command source pin, `_PYTHONW_KEEPS`) | Keep the `-m pip install` call shape on one line; run those tests |
| A slow network needs more than an hour | The cap is twice the default; the operator can install uv or dependencies directly |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
