# Advise Upgrading an Affected uv at Setup

Change ID: `22ube-enh uv-tls-advisory-at-setup`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-08
Wave: 22upa security-candidates-and-uv-advisory

## Rationale

Change `22u27-maint` pins the uv bootstrap at 0.13.5, which fixes GHSA-hq85-5cpj-mr62. Before 0.13.4, uv's vendored TLS root bundle trusts a root CA whose intermediate keys were compromised. The pin only helps machines with no uv: `_uv_bin` returns an existing uv from the tool environment or a trusted `PATH` entry, of any version, and `_bootstrap_uv` runs only when there is none. So these machines keep an affected uv after upgrading:

- every tool environment that an earlier setup bootstrapped with 0.12.22 or older;
- every machine whose own `PATH` uv is older than 0.13.4.

Setup prints nothing about it. The dependency installs (`_install_deps`, `install_requirement_specs`) are not hash-pinned. Without a CA variable they verify PyPI against uv's vendored roots, the exposed path.

The operator wants setup to raise this as an advisory, never to force an upgrade, and to offer a way to upgrade that setup or an agent can run.

## Product Intent

An operator who runs `wf setup` with an affected uv sees one advisory naming the uv, its version, the advisory and the remedy, and setup continues as before. Running `wf setup --upgrade-uv`, or asking an agent to run it, replaces the tool environment's uv with the pinned, hash-verified 0.13.5. An unaffected uv produces no output.

## Requirements

1. **One check per `wf setup` run, in `setup_wavefoundry.main`.**
   - `setup_wavefoundry.main` calls `setup_index.main` twice: once with `--deps-only`, then again with the index arguments. The uv step therefore lives in `setup_wavefoundry.main` and runs once, before the first `setup_index.main` call. It is a helper in `setup_index` that `setup_wavefoundry` calls through `_load_setup_index`.
   - `--upgrade-uv` is parsed by `setup_wavefoundry` and is not forwarded to either `setup_index.main` call.
   - A direct `setup_index.py` run never performs the uv step.
2. **The probe.** The step resolves the uv setup would use with `_uv_bin`, which prefers the tool environment's uv and otherwise takes a trusted `PATH` uv. It reads the version from `uv --version` with a short timeout and without the install lock.
   - An unreadable or unparseable version, a timeout, or a launch failure produces no advisory and no error.
   - When no uv exists, the existing bootstrap path is unchanged, and it installs the fixed 0.13.5.
   - The probe has its own test seam, so a fake uv works on every platform including Windows. `_STARTUP_UV_COMMAND` is read only by `install_requirement_specs`.
3. **The advisory.** When the version is below the threshold (0.13.4), setup records the advisory and continues with unchanged exit status and behaviour. `wf setup` prints the advisory to stderr once, as the last output of the run, so it is not lost in setup's progress output. The advisory states:
   - the uv path and version;
   - GHSA-hq85-5cpj-mr62, and that uv before 0.13.4 trusts a compromised TLS root for package downloads;
   - the remedy for where that uv lives:
     - in the tool environment: rerun setup with `--upgrade-uv`, using the command `_setup_command` renders;
     - on `PATH`: update it with the installer that provided it (for example `uv self update`, a package manager or `pipx upgrade uv`), or rerun setup with `--upgrade-uv` so setup uses a pinned uv in the tool environment ahead of `PATH`;
   - that setup does not change uv unless asked, and that an agent can run the upgrade with the operator's approval.
4. **`--upgrade-uv`.**
   - It runs inside the install lock, before any dependency install in the same run, so missing dependencies are never installed through the affected uv. The tool environment is created first if needed.
   - It installs `UV_BOOTSTRAP_REQUIREMENT` into the tool environment through the existing hash-verified pip path (`--require-hashes`, wheel only, `--no-deps`). `pip install uv==0.13.5` replaces an older pip-installed uv because the exact pin is unsatisfied.
   - It prints its own message ("Upgrading uv to the pinned ... (GHSA-hq85-5cpj-mr62)"), not `_bootstrap_uv`'s "uv not found" line, and reports the resulting version.
   - If the tool environment's uv already satisfies the pin, it reports that and installs nothing.
   - If the install fails, setup prints the existing bootstrap-failure guidance and exits 2, before any dependency install. pip leaves the previous uv in place because it verifies the download before replacing anything.
   - A `PATH` uv is never modified. Without the flag, setup never replaces an existing uv.
5. **The threshold** is one named constant beside `UV_BOOTSTRAP_REQUIREMENT`, with a comment naming the advisory.

## Scope

**Problem statement:** setup silently keeps using a uv with a published TLS advisory, and offers no supported way to replace it.

**In scope:**

- `setup_index.py`: the threshold, the probe, the advisory text, the upgrade helper.
- `setup_wavefoundry.py`: the single call site, `--upgrade-uv` parsing and help, and the end-of-run advisory.
- Tests through `setup_wavefoundry.main`, with a fake uv through the probe seam and the pip install patched, not run.
- A CHANGELOG `[Unreleased]` bullet.

**Out of scope:**

- Forcing an upgrade, or refusing to run with an affected uv.
- Reporting the advisory through `wf setup --check`, `index_health` setup readiness, the session-start hook or `wf_server_info`. The MCP startup installer (`install_requirement_specs`) is unchanged. This is a possible follow-up if a stderr line proves too easy to miss.
- Updating a `PATH` uv.
- Forcing the native trust store for uv calls.
- Direct `setup_index.py` runs.

## Platform Behavior

- **Windows:** the probe runs `uv.exe --version`; `.cmd`/`.bat` shims stay refused by `_trusted_path_uv`. The upgrade writes `Scripts\uv.exe` in the tool environment. If a running process holds that file, pip fails and setup exits 2 with the old uv intact. Tests cover the `os.name == "nt"` remedy text branch.
- **macOS, Linux, WSL2:** the same flow writes `bin/uv`; the version format `uv X.Y.Z (...)` is the same on all platforms.

## Acceptance Criteria

- [x] AC-1: Through `setup_wavefoundry.main`, with a fake uv reporting `uv 0.12.22 (abc 2026-01-01)`, a full `wf setup` prints exactly one advisory on stderr, as its last output, across both `setup_index.main` calls. The advisory names that path, `0.12.22`, `GHSA-hq85-5cpj-mr62` and the `--upgrade-uv` command, and setup exits 0. With `0.13.4`, `0.13.5` and `1.0.0`, it prints none. On the current code no advisory is printed for 0.12.22.
- [x] AC-2: The remedy text differs by location. A uv in the tool environment gets the `--upgrade-uv` remedy. A `PATH` uv also gets the update-it-yourself remedy. The `os.name == "nt"` branch is covered.
- [x] AC-3: A version probe that times out, exits non-zero, prints nothing parseable or fails to launch produces no advisory, and setup's outcome is unchanged.
- [x] AC-4: With an affected tool-environment uv, `wf setup --upgrade-uv` does the following:
  1. it calls the hash-verified pip install exactly once, under the install lock;
  1. it prints the upgrade message, not "uv not found";
  1. it reports the new version;
  1. a recorded call order shows the upgrade before the first dependency install.

  With a uv that already satisfies the pin, it installs nothing. When the install fails, it exits 2 with the bootstrap-failure guidance, and no dependency install runs. Neither `setup_index.main` call receives `--upgrade-uv`. On the current code the flag is rejected by argument parsing.
- [x] AC-5: Without `--upgrade-uv`, no test path calls the uv install while a uv exists. The existing `test_setup_index.py` and `test_setup_wavefoundry.py` suites stay green.

## Tasks

- [x] Threshold, probe with its seam, advisory text and upgrade helper in `setup_index.py`.
- [x] Single call site, `--upgrade-uv` and the end-of-run advisory in `setup_wavefoundry.py`.
- [x] Tests for AC-1 to AC-5.
- [x] CHANGELOG `[Unreleased]` bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| advisory-and-flag | implementer | none | setup_index.py and tests |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/setup_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: confined to setup's dependency provisioning, with no boundary, flow or verification change.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The advisory is the requested outcome |
| AC-2 | required | The remedy must fit where the uv lives |
| AC-3 | required | The advisory must never break setup |
| AC-4 | required | Setup must be able to perform the upgrade |
| AC-5 | required | No forced upgrade |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-08 | Planned at the operator's request: advise, do not force, and let setup or an agent perform the upgrade. | operator request |
| 2026-11-08 | Readiness round 1 repair (22upa-cr-uv-advisory-runs-twice, 22upa-sec-upgrade-uv-after-deps): one call site in `setup_wavefoundry.main` before the first `setup_index.main`; the upgrade runs under the lock before any dependency install, with its own message; the advisory prints last; the probe has its own seam. | repair_start records, context 22upa-impl-repair-1 |
| 2026-11-08 | Implementer note from code review: `setup_reconciliation`'s session runs `setup_index.parse_args`, so `setup_wavefoundry` strips `--upgrade-uv` before building the session and before forwarding arguments. | code-reviewer reverification |
| 2026-11-08 | Implemented. `setup_index`: `UV_TLS_ADVISORY_ID`/`UV_TLS_ADVISORY_FIXED_IN`, `_uv_version` probe (10s timeout, never raises, test seam `_UV_PROBE_COMMAND`), `uv_tls_advisory` text, `uv_tls_step`; the hash-verified pip install moved from `_bootstrap_uv` into `_install_pinned_uv`, shared with the upgrade. `setup_wavefoundry`: `--upgrade-uv` stripped in `main` before `setup_reconciliation.session`, `_run_uv_tls_step` called once in `_run_setup` before the Step 2 `setup_index.main`, advisory printed in `main`'s `finally` as the last output, help text. Tests: new `test_setup_uv_advisory.py` (10) drives the real `main` and real uv step; `test_setup_wavefoundry.load_setup_wavefoundry` makes the step a no-op for the existing fakes (`real_uv_step=True` opts in), and the `test_memory_backfill` and `test_setup_reconciliation` main-level fakes patch the seam; two `test_setup_index` censuses updated (the single `--require-hashes` pip install now lives in `_install_pinned_uv`; `_uv_bin(venv_python, root)` has 4 callers). Known-bad, by mutation in a scratch framework copy: no final print (2 fail), flag forwarded (3 errors), upgrade ignored (3 fail), threshold lowered to 0.12.0 (2 fail). AC-4's Windows path: only the remedy text is rendered under a patched `os.name` because pathlib refuses `WindowsPath` on POSIX. `run_tests.py --file` for setup_index, setup_uv_advisory, setup_wavefoundry, setup_reconciliation, memory_backfill: 376 OK. | test runs, mutation probes |
| 2026-11-08 | `test_tree_kill_routing` census: the version probe now runs through `_run_install_step` (tree kill on timeout), and the routed table names `_install_pinned_uv` and `_uv_version`. `run_tests.py --file` tree_kill_routing, setup_uv_advisory, setup_index: 251 OK. | test run |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-08 | Advisory on stderr every setup run, upgrade only behind `--upgrade-uv` | Operator asked not to force the upgrade | Auto-upgrade the tool environment uv; refuse affected uv |
| 2026-11-08 | Upgrade installs into the tool environment, never the `PATH` uv | Setup does not own the operator's uv; the tool environment uv is preferred over `PATH` | Run `uv self update` on the PATH uv |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The probe adds a subprocess and delay to every setup | One `--version` call with a short timeout; failures stay silent |
| A failed upgrade leaves no uv | pip verifies the hash-pinned download before uninstalling; AC-4 covers the failure exit |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
