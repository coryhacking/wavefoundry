# Vendored Dashboard Scripts Record Their npm Registry Integrity

Change ID: `1zimi-enh vendored-dashboard-scripts-registry-integrity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zimd profile-and-supply-chain-follow-ups

## Rationale

Wave 1zim2 vendored React, React DOM and elkjs under `.wavefoundry/framework/dashboard/vendor/`. Its `README.md` records each file's package, in-tarball source path and SHA-256, and `test_dashboard_server.test_dashboard_html_loads_only_same_origin_vendored_scripts` checks the shipped bytes against those SHA-256 values. A downstream reviewer can confirm the files match the README, but not that the README matches the npm registry: the README names `npm pack <name>@<version>` in prose but records neither the tarball URL nor the registry's `dist.integrity`, and gives no command sequence that reproduces each file. The downstream report asks for those so the bytes can be checked against the registry.

Verified at planning (2026-10-01), by downloading each tarball, hashing it and extracting it: each tarball's SHA-512 equals the registry's `dist.integrity`; each extracted file's SHA-256 equals the README's value; each extracted licence is byte-identical to the vendored one. `npm pack <spec> --json` (npm 11.16.0) reports the same `integrity`.

| Package | Tarball | `dist.integrity` |
| --- | --- | --- |
| `react@18.3.1` | `https://registry.npmjs.org/react/-/react-18.3.1.tgz` | `sha512-wS+hAgJShR0KhEvPJArfuPVN1+Hz1t0Y6n5jLrGQbkb4urgPE/0Rve+1kMB1v/oWgHgm4WIcV+i7F2pTVj+2iQ==` |
| `react-dom@18.3.1` | `https://registry.npmjs.org/react-dom/-/react-dom-18.3.1.tgz` | `sha512-5m4nQKp+rZRb09LNH59GM4BxTh9251/ylbKIbpe7TpGxfJ+9kv6BLkLBXIjjspbgbnIBNqlI23tRnTWT0snUIw==` |
| `elkjs@0.10.0` | `https://registry.npmjs.org/elkjs/-/elkjs-0.10.0.tgz` | `sha512-v/3r+3Bl2NMrWmVoRTMBtHtWvRISTix/s9EfnsfEWApNrsmNjqgqJOispCGg46BPwIFdkag3N/HYSxJczvCm6w==` |

## Requirements

1. **Registry table.** `dashboard/vendor/README.md` gains a table with one row per package: the package spec, the tarball URL and the registry `dist.integrity` (sha512, the base64 form npm prints), with the values above. The existing file table, with its SHA-256 per file, is unchanged.
2. **Reproduce section.** The README gives the commands that reproduce and check each file, for each package: `npm pack <name>@<version> --json` (npm checks the download against `dist.integrity`, and the JSON's `integrity` must equal the table's), `tar -xzf <name>-<version>.tgz`, then the copy of the in-tarball source path and licence to the vendored path, then the SHA-256 check. It also gives the check without npm: download the tarball URL and compare its SHA-512 in base64 with the table, with a POSIX form (`openssl dgst -sha512 -binary <file> | openssl base64 -A`; plain `base64` wraps at 76 characters on GNU systems) and a PowerShell form (`[Convert]::ToBase64String([Security.Cryptography.SHA512]::Create().ComputeHash([IO.File]::ReadAllBytes((Resolve-Path "<file>").Path)))`; `ReadAllBytes` resolves a relative name against the process folder, not the PowerShell location). The SHA-256 check uses `openssl dgst -sha256 <file>` on POSIX and `(Get-FileHash "<file>" -Algorithm SHA256).Hash.ToLower()` in PowerShell.
3. **Update instruction.** The README's update sentence says to update the integrity and tarball URL along with the version and SHA-256.
4. **Offline test.** The existing vendored-scripts test also asserts, for each of the three packages, that the README's registry table has a row naming the package spec, its `https://registry.npmjs.org/<name>/-/<name>-<version>.tgz` URL and a well-formed `sha512-` value (88 base64 characters ending `==`). The test never uses the network; it pins presence and form, and the values themselves are checked by the reproduce commands, not by the suite.
5. **Threat model.** The dashboard third-party scripts row in `docs/architecture/threat-model.md` says the README records the registry integrity and reproduce commands.
6. **CHANGELOG.** The 1zim2 `### Security` entry in `## [Unreleased]` gains one sentence that the README records each package's registry integrity and the commands that reproduce the files.
7. **Platforms.** No runtime behaviour changes. The reproduce commands work on macOS, Linux and WSL2 with `npm` or `curl`, `tar` and `openssl`; on Windows with `npm`, or `curl.exe` and `tar.exe` (both shipped with Windows 10 1803 and later) and the PowerShell hash form.

## Scope

**Problem statement:** the vendored scripts can be checked against the README but not against the npm registry.

**In scope:**

- `dashboard/vendor/README.md`, the vendored-scripts test in `test_dashboard_server.py`, the threat-model row, one CHANGELOG sentence.

**Out of scope:**

- Changing the vendored files or their versions.
- A network check in the test suite, or a verification script.
- Subresource Integrity attributes in `dashboard.html` (the scripts are same-origin and pinned by the suite).

## Acceptance Criteria

- [x] AC-1: the README's registry table holds the three rows above, and its reproduce section holds the commands in Requirement 2; following those commands on the planning machine reproduces each vendored file byte for byte and each tarball's SHA-512 equals its recorded integrity (evidence: the command transcript).
- [x] AC-2: the vendored-scripts test fails when a package's registry row, tarball URL or `sha512-` value is removed from the README, or when the value is truncated (scratch mutations), and passes for the README as written, with no network access.
- [x] AC-3: the threat-model row and the CHANGELOG sentence name the registry integrity.
- [x] AC-4: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the registry table, reproduce section and update instruction to the README.
- [x] Extend the vendored-scripts test with the offline row, URL and form checks.
- [x] Run the reproduce commands from the README in a scratch folder and keep the transcript.
- [x] Threat-model row and CHANGELOG sentence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| README and test | implementer | readiness | |
| Reproduce transcript | implementer | README and test | network, scratch folder only |
| Review | code-reviewer, qa-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/dashboard/vendor/README.md`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/architecture/threat-model.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` (dashboard third-party scripts row).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The values and commands are the change |
| AC-2 | required | The README must not lose them silently |
| AC-3 | important | Keeps the threat model and release notes accurate |
| AC-4 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Implemented. `dashboard/vendor/README.md` gains a registry table (package, tarball URL, `dist.integrity`), a reproduce section (`npm pack --json`, `tar -xzf`, copy to the vendored path, `openssl dgst -sha256`; without npm, `curl` plus `openssl dgst -sha512 -binary` piped to `openssl base64 -A`, and the PowerShell `Resolve-Path` and `Get-FileHash` forms) and an update sentence naming the integrity and tarball URL. The vendored-scripts test checks one well-formed registry row per package, offline; it failed for all three packages before the README change. Reproduce transcript (npm 11.16.0, macOS arm64): each `npm pack` integrity and each curl tarball's SHA-512 equal the table, each copied file and licence is byte-identical to the vendored one; the PowerShell form was not run (no PowerShell on this machine). Mutations removing a row, a tarball URL or a value, or truncating a value, each fail the test. Threat-model row and CHANGELOG sentence updated | `dashboard/vendor/README.md`, `tests/test_dashboard_server.py`, `docs/architecture/threat-model.md`, `CHANGELOG.md`; scratchpad `1zimi-reproduce-transcript.txt`, `1zimd-mutations.txt` |
| 2026-10-01 | Planned from the downstream report. Verified: the README already names `npm pack <name>@<version>` and each in-tarball source path, but not the tarball URL or `dist.integrity`; fetched the three registry entries, downloaded the tarballs, confirmed tarball SHA-512 equals `dist.integrity`, extracted file SHA-256 equals the README, licences byte-identical; `npm pack react@18.3.1 --json` reports the same integrity | `dashboard/vendor/README.md`, `tests/test_dashboard_server.py`, registry responses |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | A separate per-package registry table rather than more columns in the file table | Integrity belongs to the tarball, not the file; the file table stays readable | Two more columns in the existing table |
| 2026-10-01 | The test pins presence and form, not registry truth | Tests never use the network; the reproduce commands are the registry check | A test that fetches the registry; a recorded tarball fixture (would ship megabytes) |
| 2026-10-01 | Give a check without npm, with a PowerShell form | Windows reviewers without Node can still verify | npm only |

## Risks

| Risk | Mitigation |
| --- | --- |
| A future update changes the file but not the integrity | The update instruction names both; the reproduce commands fail on a stale value; the existing SHA-256 test still pins the file |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
