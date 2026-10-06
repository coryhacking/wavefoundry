# Vendored Dashboard Scripts Have No Offline Hash Check

Change ID: `1zv8a-enh offline-vendored-script-check`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-05
Wave: 1zv8c waveforge-seams-and-lock-links

## Rationale

Downstream request (Waveforge, follow-up 5004296a #2): the SHA-256 of each vendored dashboard script is already pinned in `.wavefoundry/framework/dashboard/vendor/README.md`, but the only check that reads it, `verify_vendored_scripts.py`, downloads the npm tarballs. Nothing compares the vendored files with the pinned hashes without the network, so a changed or replaced script is caught only when someone runs the online check. A distribution building its own pack wants that comparison offline, at test time and at pack time.

## Requirements

1. `verify_vendored_scripts.py` gains `--offline`: it parses the README file table (the existing `parse_readme`), hashes each vendored file and compares it with the pinned SHA-256, makes no network request, and exits 0 when all match, 1 on any mismatch or missing file (naming each), 2 when the README cannot be parsed. Without the flag behaviour is unchanged.
2. A default-suite test asserts every vendored file matches its pinned SHA-256 (through the same offline function), and that every `*.js` file under `dashboard/vendor/` is listed in the file table (dotfiles such as `.DS_Store` and the licence and README files are not scripts and are ignored; the file-table parser is unchanged).
3. `build_pack.py` runs the same offline comparison before writing a pack and refuses to build on any mismatch, naming the file. The offline function must be importable without the network code running (the module already performs no request on import).
4. The vendor README's "Reproduce and check" section documents `--offline`. CHANGELOG gets one Added bullet under `## [1.29.0]`.

## Scope

**Problem statement:** pinned hashes exist but are only checked online.

**In scope:**

- `--offline` mode, the suite test, the `build_pack` check, README and CHANGELOG.

**Out of scope:**

- A check inside target repositories (the verifier is development-only and not shipped).
- Changing the vendored versions.

## Acceptance Criteria

- [x] AC-1: `verify_vendored_scripts.py --offline` exits 0 on the real tree with no network access (a test patches the fetch to fail and the socket layer to refuse), exits 1 naming the file when one vendored byte changes or a file is missing, and exits 2 on an unparseable README.
- [x] AC-2: The default-suite test fails when a vendored file is changed or an unlisted `*.js` file is added under `dashboard/vendor/`, and ignores a `.DS_Store`.
- [x] AC-3: `build_pack` refuses to build, naming the file, when a vendored file does not match its pinned hash, and builds as before when all match.
- [x] AC-4: README and CHANGELOG describe `--offline`; the change's own tests pass and no failure elsewhere is attributable to this change.

## Tasks

- [x] Offline function and `--offline` flag
- [x] Suite test
- [x] `build_pack` check
- [x] README and CHANGELOG

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| offline-check | implementer | — | |


## Serialization Points

- `.wavefoundry/framework/scripts/verify_vendored_scripts.py`, `.wavefoundry/framework/scripts/build_pack.py`, `.wavefoundry/framework/dashboard/vendor/README.md`, `.wavefoundry/framework/scripts/tests/test_verify_vendored_scripts.py`, `.wavefoundry/framework/scripts/tests/test_build_pack.py`

## Affected Architecture Docs

N/A: a development and packaging check; no runtime boundary changes.

## Platform Behavior

Files are hashed as bytes, so line-ending conversion would show as a mismatch on any platform; the vendored files are committed as binary-identical copies (the existing `.gitattributes` handling applies). The flag and exit codes are the same on Windows (`py -3`), macOS, Linux and WSL2.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the requested offline check |
| AC-2 | required | catches drift on every test run |
| AC-3 | required | stops a pack with altered scripts |
| AC-4 | required | docs and release notes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-05 | Implemented: `offline_problems`, `unlisted_scripts` and `verify_offline` with `--offline` (exit 0/1/2); `OfflineCheckTests` (10) including a no-request proof; `build_pack._check_vendored_scripts` at the top of `build_zip` (skipped when the tree has no vendor folder, as in mini-framework test fixtures); README documents the flag. Mutation probes killed: check call removed, hash comparison disabled, a real vendored byte changed, a stray `.js` added | scratch impl8a: 192 OK (verify 42, build_pack 119, server_package 31) |
| 2026-10-05 | Readiness review folded in: the unlisted-file check covers `*.js` only, since the parser does not capture licence paths (Q1), and ignores dotfiles (Q2); import safety and `.gitattributes` confirmed | readiness review |
| 2026-10-05 | Planned from the Waveforge follow-up request | `dashboard/vendor/README.md` already pins SHA-256 per file |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-05 | Reuse the README file table as the pinned source | the hashes are already there and reviewed; one source of truth | a separate hash manifest |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A checkout converts line endings in a vendored file | the mismatch names the file; `.gitattributes` keeps them binary |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
