# Opt-In Online Integrity Check for Vendored Dashboard Scripts

Change ID: `1zltw-enh vendored-scripts-online-integrity-check`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-02
Wave: 1zls7 waveforge-defect-fixes

## Rationale

The dashboard serves three vendored third-party scripts from `.wavefoundry/framework/dashboard/vendor/` (`react/react.production.min.js`, `react-dom/react-dom.production.min.js`, `elkjs/elk.bundled.js`). `dashboard/vendor/README.md` records, for each, the npm package and version, the source path in the tarball, the file's SHA-256 (file table), and the tarball URL with the registry's `dist.integrity` (registry table). The suite check (`tests/test_dashboard_server.py` `test_dashboard_html_loads_only_same_origin_vendored_scripts`) verifies, offline and by design, that the shipped bytes match the recorded SHA-256 values and that each registry row is present and well formed; it cannot verify that the recorded integrity is the registry's or that the files really came from those tarballs. Today that check is the manual "Reproduce and check" procedure in the README.

Waveforge asked for a mechanical check. The project's principle is no network by default, so the check must be opt-in: never part of the default offline suite, run deliberately (for example while preparing a release, or when a vendored file is updated).

## Requirements

1. **An explicit verifier script.** A new stdlib-only script, `.wavefoundry/framework/scripts/verify_vendored_scripts.py`, reads both tables from `dashboard/vendor/README.md` and, for each package: downloads the recorded tarball URL over HTTPS; computes the tarball's SHA-512 and compares it, in npm's `sha512-<base64>` form, with the recorded `dist.integrity`; reads the recorded source path from the tarball in memory (no extraction to disk, so no tar path traversal); and compares the SHA-256 of that member, and the byte content, with the vendored file and with the file table. It prints one line per package and per file and exits 0 only when every check passes, 1 when any check fails, and 2 when the README cannot be parsed or a download fails (stating which).
2. **Network only when invoked, and only to the registry.** The script makes network requests only when run directly; it is never imported by a test that runs by default. It refuses any tarball URL that is not `https://registry.npmjs.org/...` as recorded in the README, checks after redirects that `response.geturl()` still starts with that registry prefix (refusing otherwise), caps the bytes read per tarball (refusing a larger body), uses a bounded timeout per request, honours the standard proxy environment variables through `urllib`, and uses the default TLS verification.
3. **Offline unit tests.** A test module (for example `tests/test_verify_vendored_scripts.py`) exercises the verifier's logic with no network: it builds small tarballs in a temporary directory and injects a fetch function, covering a pass, a tarball whose integrity does not match, a member whose SHA-256 does not match the vendored file, a missing member, and a non-registry URL refused. It also checks that the README's tables parse into exactly the three packages and three files the offline dashboard test pins.
4. **Not shipped.** The script is development-only, like `run_tests.py`: it is added to `build_pack.EXCLUDED_REL_PATHS`, and any test that pins that set is updated. A test copies the `tests/test_build_pack.py` `test_manifest_does_not_list_excluded_files` pattern (around lines 934 to 945) to assert the script is absent from both the built MANIFEST and the zip namelist. Because `dashboard/vendor/README.md` ships while the script does not, the README says the verifier exists only in the Wavefoundry source repository.
5. **Documented where it is run, and that it is optional.** The vendor README's "Reproduce and check" section names the script as the one-command form of the procedure (the manual commands stay). `docs/prompts/package-wavefoundry.prompt.md` gains an optional item in **Required Packaging Order** (before running the framework tests): when network access is available, run the verifier; a failure stops the release; when it cannot be run, say so in the release hand-off. `docs/contributing/build-and-verification.md` mentions the script as an optional, network-using check outside the default suite. The CHANGELOG gains an Unreleased `### Added` bullet.

## Scope

**Problem statement:** the recorded registry integrity and file provenance of the vendored dashboard scripts can only be checked by hand.

**In scope:**

- `verify_vendored_scripts.py`, its offline tests, the `build_pack.EXCLUDED_REL_PATHS` entry.
- `dashboard/vendor/README.md`, `docs/prompts/package-wavefoundry.prompt.md`, `docs/contributing/build-and-verification.md`, the CHANGELOG.

**Out of scope:**

- Any network access in the default test suite, setup, upgrade, packaging or the MCP server.
- Updating the vendored files or their versions.
- Verifying npm package signatures or provenance attestations.
- An environment-variable-gated test inside the suite (decided against; see Decision Log).

## Acceptance Criteria

- [x] AC-1: The offline tests show the verifier passes on matching data and fails with a named reason for each of: tarball integrity mismatch, vendored-file SHA-256 mismatch, missing tarball member, a non-registry URL (refused before any fetch), a redirect whose final URL leaves the registry prefix, and a tarball over the size cap; exit codes are 0, 1 and 2 as in Requirement 1.
- [x] AC-2: The README parsing test finds exactly `react@18.3.1`, `react-dom@18.3.1` and `elkjs@0.10.0` with their three files.
- [x] AC-3: No default-suite test opens a network connection for this change: the offline tests inject the fetch function, and a test asserts the verifier module performs no request at import.
- [x] AC-4: `build_pack` excludes the script from the distribution, pinned by a test in the `test_manifest_does_not_list_excluded_files` pattern (absent from the MANIFEST and the zip namelist).
- [x] AC-5: The vendor README (including that the verifier exists only in the source repository), the package prompt (optional step, failure stops the release, skipping is stated in the hand-off), build-and-verification and the CHANGELOG describe the script.
- [x] AC-6: One online run of the verifier against the registry is recorded in the Progress Log with its output (or, when the implementer has no network access, the operator is asked to run it and the result is recorded).
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write the offline tests (pass, three failure kinds, refused URL, README parse, no request at import).
- [x] Write `verify_vendored_scripts.py` (README parse, fetch, SHA-512 integrity, in-memory member SHA-256 and byte compare, exit codes).
- [x] Add the script to `build_pack.EXCLUDED_REL_PATHS`; update any test that pins the set.
- [x] Update the vendor README, the package prompt, build-and-verification and the CHANGELOG.
- [x] Run the verifier online once and record the output (AC-6).
- [x] Run the change's suites and docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| vendored-verify | implementer | none | new script, its tests, build_pack exclusion, docs |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/dashboard/vendor/README.md`
- `docs/prompts/package-wavefoundry.prompt.md`
- `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

N/A: a development-only verification script outside the shipped framework and the default suite; no runtime boundary or flow change. `docs/architecture/threat-model.md` is not changed (the vendored-script row already relies on the recorded hashes).

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The verifier must detect each mismatch it exists for. |
| AC-2 | important | The verifier must read the README the dashboard test pins. |
| AC-3 | required | The default suite stays offline. |
| AC-4 | important | A network-using dev tool should not ship to targets. |
| AC-5 | important | The check is only useful if people know when to run it. |
| AC-6 | important | The online path must be shown to work at least once. |
| AC-7 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Delivery-review repair. N4: a mismatch now outranks a package that could not be checked (exit 1 wins over exit 2). N5: the new `FetchRefused` (a `FetchError`) marks deliberate refusals (a non-registry URL, a redirect that left the registry, a tarball over the size cap), printed as `<package>: refused: ...`, apart from `download failed:` for a download that could not complete; the README URL check prints `refused: non-registry URL`. The package prompt, `build-and-verification.md`, the vendor README and the CHANGELOG bullet describe the labels and the exit precedence. Tests: `test_a_mismatch_outranks_an_unverifiable_package` (failure and refusal), `test_a_refused_download_is_labelled_refused_not_failed`, `test_a_network_error_is_a_failure_not_a_refusal`, `FetchRefused` asserted for the redirect and size-cap cases; failing-first `scratchpad/1zls7-repair-others/failing-first-verifier.txt` (3 failures, 5 errors). Mutations in a scratch copy (`scratchpad/1zls7-repair-mutations.txt`), 18 of 18 killed: precedence reversed, refusal printed as download failed, redirect and size cap raising plain `FetchError`. Suites (scratch copy of the repaired tree, `scratchpad/1zls7-repair-suite-*.txt`): `run_tests.py --no-cache` 10722 tests across 156 files OK, 34 skipped; `--profile second` 10719 run, 0 of 156 files failed; `--profile declared` 10722 run, 0 of 156 files failed. | `scratchpad/1zls7-repair-*`, 2026-10-02 |
| 2026-10-02 | Implemented. New `scripts/verify_vendored_scripts.py` (stdlib only): `parse_readme` reads the file and registry tables; `default_fetch` refuses any URL outside `https://registry.npmjs.org/`, re-checks `response.geturl()` after redirects, reads at most `MAX_TARBALL_BYTES` (32 MiB) + 1 and refuses a larger body, uses a 60 s timeout, the default TLS checks and `urllib`'s proxy handling; `verify` compares the tarball SHA-512 (`sha512-<base64>`) with `dist.integrity`, reads the source member in memory by exact name (no extraction) and compares its SHA-256 and bytes with the vendored file and the file table; exit 0 all pass, 1 a mismatch or missing member, 2 the check could not be made (README unparseable, URL or redirect refused, size cap, download failure). `build_pack.EXCLUDED_REL_PATHS` gains the script. Docs: vendor README (one-command form, source-repository only), `docs/prompts/package-wavefoundry.prompt.md` (optional step 4 before the framework tests; later steps renumbered 5 to 10; no seed carries this prompt's packaging order, so no seed edit), `docs/contributing/build-and-verification.md`. Tests: new `tests/test_verify_vendored_scripts.py` (14 tests: pass, integrity mismatch, vendored SHA-256 mismatch, recorded SHA-256 mismatch, missing member, three non-registry URLs refused before any fetch, unparseable README, download failure, redirect off the registry refused with the timeout passed, redirect within the registry accepted, size cap, default fetch refusing without opening, shipped README parses into exactly `react@18.3.1`, `react-dom@18.3.1`, `elkjs@0.10.0` and their three files, import opens no connection); `tests/test_build_pack.py` `test_manifest_does_not_list_the_vendored_scripts_verifier` (absent from MANIFEST and zip namelist). Failing first: the verifier tests errored on the missing module and the pack test failed with the script in the MANIFEST. Focused: verifier 14 OK, build_pack 117 OK, reconcile_scan 61 OK, dashboard vendored test OK, 13 script-wide census modules OK. Online run (AC-6), 2026-10-02: all three packages `ok (tarball integrity matches)` and all three files `ok`, exit 0. Mutations (scratch copy): redirect check removed fails `test_redirect_leaving_the_registry_is_refused`; integrity compare removed fails `test_tarball_integrity_mismatch_fails_with_exit_one`; size cap removed fails `test_tarball_over_the_size_cap_is_refused`; prefix refusal removed fails `test_non_registry_url_is_refused_before_any_fetch` (3 subtests); pack exclusion removed adds exactly `test_manifest_does_not_list_the_vendored_scripts_verifier` to the scratch copy's environmental baseline (5 failures, 15 errors from missing repo-root files). Gapfill: shell grep used to find tests pinning `EXCLUDED_REL_PATHS` (`test_build_pack.py`, `test_reconcile_scan.py`), tests naming `urllib.request` (none census network use), script-wide census modules, and references to packaging step numbers (none outside the prompt), because these are exact-token sweeps across test files the code index excludes. Coordinator suite run (scratch copy of the whole wave tree): `run_tests.py --no-cache` 10689 tests across 156 files OK (34 skipped); `--profile declared` 10689 OK; `--profile second` 10686 run, its one failure was a 1zltr fixture (fixed, the file then passed under the second profile). | Scratchpad `1zls7-1zltw-failing-first.txt`, `1zls7-1zltw-pack-failing-first.txt`, `1zls7-1zltw-online-run.txt`, `1zls7-1zltw-mutations.txt` |
| 2026-10-02 | Planned. Verified: `dashboard/vendor/README.md` has the file table (file, package, source in the tarball, licence, SHA-256) and the registry table (package, tarball URL, `dist.integrity`); `test_dashboard_html_loads_only_same_origin_vendored_scripts` checks SHA-256 against the shipped bytes and the registry rows' form only; `build_pack.EXCLUDED_REL_PATHS` already excludes `scripts/run_tests.py` and `scripts/build_pack.py`; no framework script uses `urllib.request` except `wf_server/dashboard_handlers.py`. | Planning read, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | An explicit script run on demand, not an env-var-gated suite test | A script cannot run by accident in the default suite, gives a clear exit code for the release checklist, and keeps network code out of the test runner | A test skipped unless an environment variable is set |
| 2026-10-02 | Readiness amendments: the shipped vendor README says the verifier exists only in the source repository; the verifier checks `response.geturl()` against the registry prefix after redirects and caps tarball size (AC-1 extended); the exclusion test copies the `test_build_pack.py` `test_manifest_does_not_list_excluded_files` pattern (AC-4) | Readiness review: targets read a README naming a script they do not have, a redirect could leave the registry, and an unbounded body could exhaust memory | Disable redirects entirely (rejected: the registry may redirect within its own host) |
| 2026-10-02 | Development-only, excluded from the distribution | Targets never update the vendored files, and shipping a network-using tool conflicts with the no-network-by-default principle | Ship it with the framework |
| 2026-10-02 | Optional packaging step; failure stops the release, skipping is stated | Optional because release machines may be offline; stated so a skipped check is visible | Required step; no packaging mention |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The registry is unreachable behind a corporate proxy or TLS inspection | `urllib` honours `HTTPS_PROXY`; a download failure exits 2 with the reason, distinct from a mismatch (exit 1) |
| A malicious or malformed tarball | Members are read in memory by exact name, never extracted to disk; only registry URLs are fetched |
| Platform behaviour | Stdlib only (`urllib.request`, `tarfile`, `hashlib`, `base64`); runs the same with `python3` on macOS, Linux and WSL2 and with `py -3` or `python` on Windows; no subprocess and no shell tools, so the PowerShell differences the README documents for the manual procedure do not apply |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
