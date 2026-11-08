# Advise Upgrading an Affected uv at Setup

Change ID: `22ube-enh uv-tls-advisory-at-setup`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-11-08
Wave: TBD

## Rationale

Change `22u27-maint` pins the uv bootstrap at 0.13.5, which fixes GHSA-hq85-5cpj-mr62. Before 0.13.4, uv's vendored TLS root bundle trusts a root CA whose intermediate keys were compromised. The pin only helps machines with no uv: `_uv_bin` returns an existing uv from the tool environment or a trusted `PATH` entry, of any version, and `_bootstrap_uv` runs only when there is none. So these machines keep an affected uv after upgrading:

- every tool environment that an earlier setup bootstrapped with 0.12.22 or older;
- every machine whose own `PATH` uv is older than 0.13.4.

Setup prints nothing about it. The dependency installs (`_install_deps`, `install_requirement_specs`) are not hash-pinned. Without a CA variable they verify PyPI against uv's vendored roots, the exposed path.

The operator wants setup to raise this as an advisory, never to force an upgrade, and to offer a way to upgrade that setup or an agent can run.

## Product Intent

An operator who runs `wf setup` with an affected uv sees one advisory naming the uv, its version, the advisory and the remedy, and setup continues as before. Running `wf setup --upgrade-uv`, or asking an agent to run it, replaces the tool environment's uv with the pinned, hash-verified 0.13.5. An unaffected uv produces no output.

## Requirements

1. Each `wf setup` run checks the uv that setup would use: the result of `_uv_bin` after dependency provisioning, whether or not anything was installed. It reads the version from `uv --version`, with a short timeout and without the install lock.
2. When the version is below 0.13.4, setup prints one advisory to stderr and continues with unchanged exit status and behaviour. The advisory states:
   - the uv path and version;
   - GHSA-hq85-5cpj-mr62, and that uv before 0.13.4 trusts a compromised TLS root for package downloads;
   - the remedy for where that uv lives:
     - in the tool environment: rerun setup with `--upgrade-uv`, using the command `_setup_command` renders;
     - on `PATH`: update it with the installer that provided it (for example `uv self update`, a package manager or `pipx upgrade uv`), or rerun setup with `--upgrade-uv` so setup uses a pinned uv in the tool environment ahead of `PATH`;
   - that setup does not change uv unless asked, and an agent can run the upgrade with the operator's approval.
3. An unreadable or unparseable version, a timeout or a launch failure produces no advisory and no error. When no uv exists, the existing bootstrap path is unchanged.
4. `--upgrade-uv` is a new setup flag. Under the install lock, after the tool environment exists, it installs `UV_BOOTSTRAP_REQUIREMENT` into the tool environment through the existing hash-verified `_bootstrap_uv` path (`--require-hashes`, wheel only, `--no-deps`). It then reports the resulting version.
   - If the tool environment's uv already satisfies the pin, the flag reports that and installs nothing.
   - If the bootstrap fails, setup prints the existing bootstrap-failure guidance and exits 2. pip leaves the previous uv in place because it verifies the download before replacing anything.
   - A `PATH` uv is never modified.
   - Without the flag, setup never replaces an existing uv.
5. The threshold is one named constant beside `UV_BOOTSTRAP_REQUIREMENT`, with a comment naming the advisory.

## Scope

**Problem statement:** setup silently keeps using a uv with a published TLS advisory, and offers no supported way to replace it.

**In scope:**

- `setup_index.py`: the version probe, the advisory, the `--upgrade-uv` flag and its help text.
- Tests in `tests/test_setup_index.py`, using a fake uv. The fake uv is a script that prints a chosen `--version`, launched through the existing `_STARTUP_UV_COMMAND` seam or a patched `_uv_bin`. The bootstrap is patched, not run.
- A CHANGELOG `[Unreleased]` bullet.

**Out of scope:**

- Forcing an upgrade, or refusing to run with an affected uv.
- Reporting the advisory through `wf setup --check`, `index_health` setup readiness, the session-start hook or `wf_server_info`. The MCP startup installer (`install_requirement_specs`) is unchanged.
- Updating a `PATH` uv.
- Forcing the native trust store for uv calls.

## Platform Behavior

- **Windows:** the probe runs `uv.exe --version`; `.cmd`/`.bat` shims stay refused by `_trusted_path_uv`. The upgrade writes `Scripts\uv.exe` in the tool environment. If a running process holds that file, pip fails and setup exits 2 with the old uv intact. Tests cover the `os.name == "nt"` remedy text branch.
- **macOS, Linux, WSL2:** the same flow writes `bin/uv`; the version format `uv X.Y.Z (...)` is the same on all platforms.

## Acceptance Criteria

- [ ] AC-1: With a fake uv reporting `uv 0.12.22 (abc 2026-01-01)`, `wf setup --deps-only` prints exactly one advisory on stderr. The advisory names that path, `0.12.22`, `GHSA-hq85-5cpj-mr62` and the `--upgrade-uv` command, and setup exits 0. With `0.13.4`, `0.13.5` and `1.0.0`, it prints none. On the current code no advisory is printed for 0.12.22.
- [ ] AC-2: The remedy text differs by location. A uv in the tool environment gets the `--upgrade-uv` remedy. A `PATH` uv also gets the update-it-yourself remedy.
- [ ] AC-3: A version probe that times out, exits non-zero, prints nothing parseable or fails to launch produces no advisory, and setup's outcome is unchanged.
- [ ] AC-4: `--upgrade-uv` with an affected tool-environment uv calls the hash-verified bootstrap once, under the install lock, and reports the new version. With a uv that already satisfies the pin, it calls nothing. When the bootstrap fails, it exits 2 with the bootstrap-failure guidance. On the current code the flag is rejected by argument parsing.
- [ ] AC-5: Without `--upgrade-uv`, no test path calls the bootstrap while a uv exists. The existing `test_setup_index.py` suite stays green.

## Tasks

- [ ] Add the threshold constant, the version probe and the advisory, and call the advisory from `main` after `ensure_deps`.
- [ ] Add `--upgrade-uv` to `setup_requirements.parse_args` and the upgrade step under the install lock.
- [ ] Tests for AC-1 to AC-5.
- [ ] CHANGELOG `[Unreleased]` bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| advisory-and-flag | implementer | none | setup_index.py and tests |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/setup_requirements.py`, `.wavefoundry/framework/scripts/tests/test_setup_index.py`

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
