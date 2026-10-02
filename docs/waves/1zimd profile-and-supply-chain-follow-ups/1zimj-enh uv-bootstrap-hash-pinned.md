# The uv Bootstrap Installs Only Hash-Verified Wheels

Change ID: `1zimj-enh uv-bootstrap-hash-pinned`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zimd profile-and-supply-chain-follow-ups

## Rationale

When neither the tool environment nor `PATH` has a uv, `setup_index._bootstrap_uv` (called only from `_install_deps`, which `wf setup` and the upgrade's dependency and migration steps reach) runs `<tool venv python> -m pip install --only-binary :all: uv==0.12.4` from the tool-venv base. The version is pinned and reviewed at release (package checklist step 3), but the bytes are not: pip accepts whatever wheel the configured index serves for that version, and this install is outside uv's own package-age guard because uv does not exist yet. The downstream report asks for `--require-hashes` with the per-platform wheel hashes, reviewed at each release with the version.

pip accepts `--hash` only per requirement inside a requirements file, so the hashes have to reach pip through a file.

Fetched from `https://pypi.org/pypi/uv/0.12.4/json` on 2026-10-01: 18 wheels (all `py3-none`, uploaded 2026-08-13, none yanked) and one sdist, which `--only-binary :all:` already excludes. The `digests.sha256` per wheel:

| Wheel | sha256 |
| --- | --- |
| `uv-0.12.4-py3-none-linux_armv6l.whl` | `9c343a7251d1b4c47e467fd38ae16448e9d1607a645e332a95439bfb2a74b66e` |
| `uv-0.12.4-py3-none-macosx_10_12_x86_64.whl` | `bdb7de1a0f70eaf957d782f84b3d39a9248d3ffd8dbf845304c623f70421870c` |
| `uv-0.12.4-py3-none-macosx_11_0_arm64.whl` | `004e75a64fa44619b0e3bb267c206a6920e65b78c963863b649c3bcdfd870610` |
| `uv-0.12.4-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl` | `faf6430497f3bf6a1c92d10215cd4097c8094d57955fbe563b30ba3add62a9c9` |
| `uv-0.12.4-py3-none-manylinux_2_17_armv7l.manylinux2014_armv7l.musllinux_1_1_armv7l.whl` | `221744261e47b140bc29de6be9900f6d7153d1ddc2e652b24c6838beadadb032` |
| `uv-0.12.4-py3-none-manylinux_2_17_armv7l.manylinux2014_armv7l.whl` | `7517ae9cad6c0762fc1ee263980077e8715cc15976ee7516136a26f195792c71` |
| `uv-0.12.4-py3-none-manylinux_2_17_i686.manylinux2014_i686.whl` | `18a76d7d479c13fcac26e8dac42e5ac753feb076cce2b0fd7e936e5837aae89b` |
| `uv-0.12.4-py3-none-manylinux_2_17_ppc64le.manylinux2014_ppc64le.whl` | `dc5ce8196d448fc704f6c74cd6bd3a1183f82f87620f3985bae3bddab0a01dd1` |
| `uv-0.12.4-py3-none-manylinux_2_17_s390x.manylinux2014_s390x.whl` | `6b77b36b64ff260d09fc02c440a3c392d9bff77389a5a91d3a663aab074375d0` |
| `uv-0.12.4-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | `3bb292d959fa73000d524159cd5f3c1aa1cf2db9cc3005ccdec06911a9998e84` |
| `uv-0.12.4-py3-none-manylinux_2_28_aarch64.whl` | `2b387bf72accc04c50f27808188c5ecd82bd123bf87cb9bb1b01b9c5344a506f` |
| `uv-0.12.4-py3-none-manylinux_2_31_riscv64.musllinux_1_1_riscv64.whl` | `81c03a57524b8f9cf1530fc9cc69aea0a2a16d73e5dbcf5d40043b2a68a9d43b` |
| `uv-0.12.4-py3-none-manylinux_2_31_riscv64.whl` | `54635bc94277b72189b1159cc12a95e12fd92b78c84b6df4a6aecbd08edc7837` |
| `uv-0.12.4-py3-none-musllinux_1_1_i686.whl` | `8d3744d48969ecd5ca7dc766e1223f0d39106fc1ad433bae8edd45c915a1187c` |
| `uv-0.12.4-py3-none-musllinux_1_1_x86_64.whl` | `9338a8bc8e8a350ec6f954178326e6fdc8872df2f14a233644973ac7fc46aa5e` |
| `uv-0.12.4-py3-none-win32.whl` | `dc9e67e1068bc1140ebae3a5fe26c0355ab03af254d668c5b8824984b9c02126` |
| `uv-0.12.4-py3-none-win_amd64.whl` | `a49cf2bde46a181f3d22927221a8e9f1254c38b7d810a3d3a697c42f5053537f` |
| `uv-0.12.4-py3-none-win_arm64.whl` | `3dc929ea44123d4f5492cebe9dc09852152509113134030473a70fbd702d62f0` |

Planning check (scratch venv, pip 25.1.1, macOS arm64): `pip install --require-hashes --only-binary :all: --no-deps -r <file>` with `uv==0.12.4` and all 18 `--hash=sha256:` entries installed uv 0.12.4; the same file with the macOS arm64 hash altered failed with pip's "THESE PACKAGES DO NOT MATCH THE HASHES" error and a non-zero exit.

## Requirements

1. **Recorded hashes.** `setup_index.py` holds, beside `UV_BOOTSTRAP_REQUIREMENT`, a constant `UV_BOOTSTRAP_WHEEL_SHA256`: a tuple of `(wheel filename, sha256)` pairs, one per wheel PyPI publishes for the pinned version (the 18 above). The filename is kept for review; pip uses only the hashes.
2. **Hash-checked bootstrap.** `_bootstrap_uv` writes a temporary requirements file (`tempfile.mkstemp`, closed before pip runs so Windows can open it) holding one logical line: the requirement followed by one ` --hash=sha256:<value>` per recorded wheel, space-separated on that same line (pip ignores `--hash` options on lines of their own, verified at review), and runs `<venv python> -m pip install --require-hashes --only-binary :all: --no-deps -r <absolute path>`, keeping its current environment (`_installer_env(_pip_tls_env())`), timeout, working directory (tool-venv base) and lock passing. The file is removed after pip returns, fails, or times out; a removal error is ignored. The file is created in the tool-venv base folder (`tempfile.mkstemp(dir=venv_bootstrap.tool_venv_base(), ...)`), which already exists and is per-user; an `OSError` creating or writing it is reported like a failed bootstrap (Requirement 3 message) and returns `None`.
3. **Fail closed.** pip installs only a wheel whose bytes match a recorded hash. A platform with no published wheel, or a download that matches no hash (an index or mirror serving different bytes), makes the bootstrap fail: `_bootstrap_uv` prints to stderr that the pinned uv could not be installed with its recorded hashes, naming the requirement and pointing at pip's output above, and returns `None`. Setup then continues on the existing documented path: the dependency install falls back to plain pip with its existing warning that the package-age guard is off. No unverified uv is ever installed.
4. **Existing uv untouched.** `_uv_bin` still prefers the tool venv's uv and then any uv on `PATH`, whatever their versions; the bootstrap runs only when neither exists, and no existing uv is checked against or replaced by the recorded hashes.
5. **Release checklist.** Step 3 of `docs/prompts/package-wavefoundry.prompt.md` says that bumping `UV_BOOTSTRAP_REQUIREMENT` also replaces `UV_BOOTSTRAP_WHEEL_SHA256` with every `bdist_wheel` entry's `filename` and `digests.sha256` from `https://pypi.org/pypi/uv/<version>/json`, that the reviewer confirms the wheel count against the release's file list on PyPI, and that the version and hashes change in the same commit. Keeping the pin keeps the hashes.
6. **Docs.** The package-age guard paragraph in `docs/contributing/build-and-verification.md` says the bootstrap installs only a wheel matching the recorded hashes and fails closed otherwise. `docs/architecture/threat-model.md` gains a row for the uv bootstrap (pinned version and hashes; existing uv not checked; failure falls back to plain pip without the age guard). The 1zicq bullet in `## [Unreleased]` about the pinned uv wheel gains one sentence on hash verification.
7. **Platforms.** Windows (x64, x86, arm64), macOS (x86_64, arm64), Linux (glibc and musl on x86_64, aarch64 and the other published architectures) and WSL2 (a Linux wheel) each match one recorded hash and install as before. The temporary file path is absolute and passed as one argument, so a temp folder with spaces (common on Windows) works. A platform with no published wheel fails as it does today, now with the message in Requirement 3.
8. **Transition.** Takes effect for the next bootstrap after the release that ships it; machines that already have a uv are unaffected.

## Scope

**Problem statement:** the uv bootstrap pins the version but accepts any bytes the index serves for it.

**In scope:**

- `_bootstrap_uv` and the new constant in `setup_index.py`; tests in `test_setup_index.py` and `test_startup_install.py`; the package checklist step, the build-and-verification paragraph, a threat-model row, one CHANGELOG sentence.

**Out of scope:**

- Verifying or replacing an existing uv.
- Hash-pinning the dependency installs themselves (uv's age guard and the requirement ranges cover those; full hash locking is a separate decision).
- Bumping the uv version.
- A maintainer script that regenerates the hashes.

## Acceptance Criteria

- [x] AC-1: with `_uv_bin` returning `None`, `_bootstrap_uv` runs exactly `[abs venv python, "-m", "pip", "install", "--require-hashes", "--only-binary", ":all:", "--no-deps", "-r", <absolute path>]` from the tool-venv base; at call time the file holds exactly one non-empty line: `UV_BOOTSTRAP_REQUIREMENT` followed by one `--hash=sha256:` entry per recorded wheel and nothing else; after a zero exit, a non-zero exit and a timeout the file no longer exists.
- [x] AC-2: `UV_BOOTSTRAP_WHEEL_SHA256` is non-empty, every filename starts with `uv-<pinned version>-` and ends `.whl`, every hash is 64 lowercase hex characters, neither repeats, and it includes a wheel for each of win_amd64, win_arm64, macosx x86_64, macosx arm64, manylinux x86_64, manylinux aarch64 and musllinux x86_64; a scratch mutation bumping the requirement's version alone fails this test.
- [x] AC-3: a non-zero pip exit makes `_bootstrap_uv` print the Requirement 3 message to stderr and return `None`, and `_install_deps` then takes the existing pip fallback; with a uv in the tool venv or on `PATH`, no bootstrap runs (the existing test still passes).
- [x] AC-4: on the planning or implementing machine, a real pip in a scratch venv installs uv through the bootstrap's file, and refuses it with one hash altered (transcript recorded).
- [x] AC-5: the package checklist step, the build-and-verification paragraph, the threat-model row and the CHANGELOG sentence say what Requirements 5 and 6 say.
- [x] AC-6: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add `UV_BOOTSTRAP_WHEEL_SHA256` with the 18 values above.
- [x] Write the temporary requirements file in `_bootstrap_uv`, pass the hash flags, remove the file in a `finally`, and print the failure message.
- [x] Update `test_bootstrap_installs_only_the_pinned_wheel_from_the_venv_base`; add tests for AC-1 to AC-3; confirm the `test_startup_install` bootstrap tests (lock carrier, relative installer paths) still pass.
- [x] Real pip transcript for AC-4 in a scratch venv.
- [x] Checklist step, build-and-verification paragraph, threat-model row, CHANGELOG sentence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Hash-checked bootstrap | implementer | readiness | `setup_index.py` and tests |
| Checklist and docs | implementer | hash-checked bootstrap | |
| Review | code-reviewer, qa-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`, `.wavefoundry/framework/scripts/tests/test_startup_install.py`
- `docs/prompts/package-wavefoundry.prompt.md`, `docs/contributing/build-and-verification.md`, `docs/architecture/threat-model.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` (new uv bootstrap row).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The hash check is the change |
| AC-2 | required | A version bump without new hashes must fail the suite, not the field |
| AC-3 | required | Failure must be loud and must not install unverified bytes |
| AC-4 | required | Proves the real pip behaviour the unit tests mock |
| AC-5 | required | The release step keeps the hashes current |
| AC-6 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Implemented. `UV_BOOTSTRAP_WHEEL_SHA256` holds the 18 wheels; `_bootstrap_uv` writes a one-line requirements file with `tempfile.mkstemp` in the tool-venv base (closed before pip runs, removed in a `finally`), runs `pip install --require-hashes --only-binary :all: --no-deps -r <abs path>`, reports a non-zero exit or an `OSError` writing the file with the Requirement 3 message and returns `None`, so `_install_deps` keeps its plain-pip fallback. New tests: `test_bootstrap_installs_only_the_pinned_wheel_from_the_venv_base` (rewritten: exact command, one-line file, removal after exit 0, exit 1 and timeout), `test_uv_bootstrap_wheel_hashes_cover_the_pinned_version`, `test_a_failed_hash_bootstrap_is_reported_and_setup_falls_back_to_pip`, `test_an_unwritable_requirements_file_is_a_failed_bootstrap`; all failed before the change. Real pip 25.1.1 in a scratch venv whose path holds a space: the bootstrap installed uv 0.12.4; with the macOS arm64 hash altered pip refused it with its hash-mismatch error, the message printed, no uv was installed and no file was left. Mutations (drop `--require-hashes`, drop `--no-deps`, bump the version alone, hashes on separate lines, no removal, no message, `OSError` unhandled) each fail a named test. Checklist step 3, build-and-verification paragraph, threat-model row and CHANGELOG sentence updated | `setup_index.py`, `tests/test_setup_index.py`, `docs/prompts/package-wavefoundry.prompt.md`, `docs/contributing/build-and-verification.md`, `docs/architecture/threat-model.md`, `CHANGELOG.md`; scratchpad `1zimj-real-pip-transcript.txt`, `1zimd-mutations.txt` |
| 2026-10-01 | Planned from the downstream report. Verified: `_bootstrap_uv` is the only bootstrap and is called only from `_install_deps`; it runs pip with `--only-binary :all:` and the bare requirement; on failure `_install_deps` falls back to plain pip with a warning; checklist step 3 reviews the version only. Fetched the 18 wheel hashes from PyPI; real pip in a scratch venv installed uv 0.12.4 with `--require-hashes` and refused an altered hash | `setup_index.py`, `tests/test_setup_index.py`, `tests/test_startup_install.py`, `docs/prompts/package-wavefoundry.prompt.md`, PyPI JSON |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Keep the plain-pip fallback after a failed hash bootstrap (readiness security recommendation) | pip's exit code cannot tell a hash mismatch from a network failure or a mirror lacking uv, so a hard stop would break firewalled and mirrored users; an index that can substitute uv can equally substitute the dependencies a stop would only postpone; the pin's value is that an unverified uv never lands | Stop setup on a failed bootstrap |
| 2026-10-01 | Pass hashes through a temporary requirements file | pip accepts `--hash` only inside a requirements file | A requirements file committed in the framework (one more shipped file to keep in step with the constant) |
| 2026-10-01 | Record every published wheel, keyed by filename | Every supported platform installs; reviewers can compare against PyPI's file list | Only the platforms we test, which would fail closed on the rest |
| 2026-10-01 | A failed bootstrap keeps the existing plain-pip fallback for dependencies | uv stays an optional guard; the dependencies come from the same index either way, and refusing setup would break platforms without a uv wheel. The uv binary itself is never installed unverified | Abort setup on any bootstrap failure (resolved at readiness: the security review recommends keeping the fallback, see the row above) |
| 2026-10-01 | Add `--no-deps` | uv's wheel has no dependencies; a future one with an unhashed dependency should fail on that, not install it | Rely on `--require-hashes` alone, which also refuses an unhashed dependency, with a less direct message |

## Risks

| Risk | Mitigation |
| --- | --- |
| A release bumps the version without new hashes | AC-2's test fails on a filename that does not match the pinned version |
| An index or mirror repackages uv (same version, different bytes) | The bootstrap fails closed with a message; setup continues without the age guard, as it does when uv is unavailable |
| A stale temporary file on a killed process | It lives in the per-user tool-venv base folder, holds only public hashes, and has a 0600 mode on POSIX |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
