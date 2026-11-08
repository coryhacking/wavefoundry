# Bump the uv Bootstrap Pin to 0.13.5

Change ID: `22u27-maint bump-uv-bootstrap-pin-0-13-5`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-07
Wave: 22u26 post-1-40-follow-ups

## Rationale

`wf setup` installs the pinned uv only when neither the tool environment nor `PATH` has one. The pin is `uv==0.12.22`.

PyPI lists advisory GHSA-hq85-5cpj-mr62 (PYSEC-2026-4321) against every uv before 0.13.4, including 0.12.22. By default uv verifies TLS against a vendored `webpki-root-certs` bundle. Before 0.13.4 that bundle includes the `emSign ECC Root CA - G3` root, whose intermediate keys were compromised, so certificates issued through them are accepted for any hostname.

Setup is exposed in its dependency installs:

- When no CA variable is set, `setup_index._uv_install_env` adds nothing. The `uv pip install` calls in `install_requirement_specs` and `_install_deps` then trust uv's vendored roots.
- Those installs are not hash-pinned. Only the pip bootstrap of uv itself uses `--require-hashes`.

The fixes:

- 0.13.4 (2026-10-20) removes the root.
- 0.13.5 (2026-10-22) also rejects certificate chains containing the compromised eMudhra intermediate keys, through `rustls-webpki` 0.103.16.

PyPI lists no advisory for either. Both are inside the package checklist's 21-day package-age window as of 2026-11-07. The operator chose 0.13.5 as a security exception to that window.

uv 0.13.0 is a minor release with eight listed breaking changes. None touches how setup calls uv:

- setup runs uv only as `uv pip install` with `--python`, `--exclude-newer` and either `--no-config` or the operator's `--config-file`;
- it uses no constraints files, editable requirements, `uv venv` or `uv build`;
- the distutils patch removal applies to Python 3.10 and newer, which every supported interpreter is;
- the Windows ARM64 native-Python preference changes only automatic interpreter discovery.

The cache entry format changed, so the first install after the bump may download again; older uv versions can share the cache.

## Product Intent

A fresh `wf setup` on a machine without uv installs uv 0.13.5, which carries no published advisory, verified against the 18 PyPI hashes; an existing uv of any version is still used as-is.

## Requirements

1. `UV_BOOTSTRAP_REQUIREMENT` becomes `uv==0.13.5`.
2. `UV_BOOTSTRAP_WHEEL_SHA256` is replaced in the same edit with every `bdist_wheel` filename and `digests.sha256` from `https://pypi.org/pypi/uv/0.13.5/json` (18 entries, none yanked).
3. No other behaviour changes: an existing uv is never replaced, and the bootstrap still uses `--require-hashes`.

## Scope

**Problem statement:** the bootstrap pin trails the newest uv and carries a published TLS advisory.

**In scope:**

- The two constants in `setup_index.py`, a comment recording the window exception, and a CHANGELOG bullet.

**Out of scope:**

- Replacing a uv that an earlier setup already bootstrapped into a tool environment. Setup never replaces an existing uv, so such a 0.12.22 keeps the advisory until the operator removes it. That is a separate change for the operator to schedule.
- Forcing the native trust store for every uv call.
- 0.13.6 and later.

## Acceptance Criteria

- [x] AC-1: `setup_index.UV_BOOTSTRAP_REQUIREMENT == "uv==0.13.5"` and `UV_BOOTSTRAP_WHEEL_SHA256` holds exactly the 18 filename and hash pairs PyPI lists for 0.13.5, compared by a script against the PyPI JSON; Windows, macOS and Linux wheels are present, and PyPI's `vulnerabilities` list for 0.13.5 is empty. On the current code the requirement is `uv==0.12.22`, whose PyPI entry lists GHSA-hq85-5cpj-mr62.
- [x] AC-2: A real bootstrap in a scratch venv with the generated requirements line installs `uv 0.13.5`, and the same line with a zeroed hash is refused. That uv then completes `uv pip install --no-config --python <venv> --exclude-newer <cutoff>` of a small pure-Python package.
- [x] AC-3: The existing uv pin tests in `tests/test_setup_index.py` pass, and the full framework suite passes.

## Tasks

- [x] Replace the two constants from the PyPI JSON, with a comment naming the advisory and the window exception.
- [x] Compare the table with PyPI by script.
- [x] Run the scratch-venv bootstrap and install probe.
- [x] Run `test_setup_index.py`, then the full suite.
- [x] Add a CHANGELOG bullet under Unreleased.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| pin-bump   | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`

## Platform Behavior

0.13.5 publishes the same 18-tag wheel set as 0.12.22: Windows win32, win_amd64 and win_arm64; macOS x86_64 and arm64; Linux and WSL2 through manylinux and musllinux. The install path is unchanged. On Windows ARM64, 0.13 prefers native Python only during automatic discovery; setup always passes `--python`. The real bootstrap probe runs on macOS only.

## Affected Architecture Docs

N/A: two constants in one module; no boundary, flow or verification change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The pin and hashes are the whole change |
| AC-2 | required | Proves the new minor version installs and runs our command shape |
| AC-3 | required | The existing pin tests guard the table's shape |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-07 | Planned at operator request ("evaluate the differences between 0.12 and 0.13 uv", then "let's do all of these"). First planned as 0.13.1 (change `22u25-maint`, withdrawn before readiness). | uv CHANGELOG.md, changelogs/0.12.x.md, release pages 0.13.0 and 0.13.1 |
| 2026-11-07 | Readiness code review (finding `22u26-code-uv-tls-advisory`) found the advisory on 0.12.22 and 0.13.1. Operator chose "0.13.5, window exception". PyPI JSON checked: 0.13.5 has 18 wheels, none yanked, the same platform tags as 0.13.1, and no listed vulnerabilities. | PyPI JSON for 0.12.22, 0.13.1, 0.13.4, 0.13.5 |
| 2026-11-07 | Implemented. Both constants replaced from the PyPI 0.13.5 JSON, with a comment naming GHSA-hq85-5cpj-mr62 and the window exception. AC-1: script comparison 18 of 18 filename and hash pairs, Windows (win32, win_amd64, win_arm64), macOS (x86_64, arm64) and Linux wheels present, PyPI `vulnerabilities` empty. AC-2 on macOS arm64: the zeroed-hash line was refused (`THESE PACKAGES DO NOT MATCH THE HASHES`), the real line installed `uv 0.13.5 (46776a95d 2026-10-21)`, and that uv ran `uv pip install --no-config --python <venv> --exclude-newer <21 days ago> six` (six 1.17.0). `test_setup_index.py` 208 OK. CHANGELOG Security bullet added, noting the cache-format change and stricter source-archive extraction. Gapfill: the table was rewritten by script from the PyPI JSON, a bulk-mechanical edit. | implementation |
| 2026-11-07 | Full suite `run_tests.py --no-cache`: 12612 tests in 235 files OK, 12 expected skips, no framework bytecode (second run). The first run failed two files from this wave's own edits, both fixed before the second: `test_lifecycle_golden` (the 22r95 `conditional_fields` schema entry; golden regenerated through `check_golden` with both overwrite flags, diff exactly the three expected fixture paths, and the addition declared with its exact value in `test_only_declared_observability_additions_since_extraction_golden`) and `test_server_package` (22u24's new filesystem test read producers by path; now `framework_files.source_path`). | full suite |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-07 | Pin 0.13.5 as an exception to the 21-day package-age window | A published TLS advisory affects every uv before 0.13.4; 0.13.5 also rejects the compromised intermediates. Operator's choice | 0.13.4 (minimum fix); wait until 2026-11-10 or 2026-11-12; 0.13.1 with the risk accepted |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A copied hash is wrong, so a fresh bootstrap refuses to install | AC-1 compares the table with the PyPI JSON by script |
| A 0.13 behaviour change breaks the install command | AC-2 runs the real command shape |
| A release only 16 days old has an undiscovered regression | The bootstrap is used only when no uv exists; AC-2 runs it for real |
| Existing tool environments keep a bootstrapped 0.12.22 | Out of scope; reported to the operator as a follow-up |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
