# Skip descriptor chmod on native Windows

Change ID: `23z47-bug windows-fchmod-guard`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-20
Wave: 23z45

## Rationale

Field feedback against v1.46.0 (item 4 in `.wavefoundry/work/23z45/field-feedback-v1.46.0.md`) reports that setup and record writes failed for a team on native Windows with Python 3.14. Python 3.13 added `os.fchmod` on Windows, and the framework decides whether to set a mode on a descriptor with `hasattr(os, "fchmod")` alone. On Python 3.12 and earlier that test was false on Windows, so the call was skipped. From 3.13 it is true, the call runs, and it fails with `PermissionError` (WinError 5). The reporting distribution already carries the fix `hasattr(os, "fchmod") and not _windows()`.

## Product Intent

Operators on native Windows with Python 3.13 or later can run setup, render surfaces and write records without a permission failure from a descriptor chmod. Before this change those writes raise `PermissionError`; after it they succeed, as they did on Python 3.12 and earlier. Behaviour on macOS, Linux and WSL2 does not change: modes are still set on the descriptor there. AC-1 and AC-2 together test this outcome.

## Requirements

1. One predicate in `contained_files.py` answers whether a mode can be set on a descriptor: `os.fchmod` exists and the platform is not native Windows (`_windows()`).
2. Every `os.fchmod` call in non-test code under `.wavefoundry/framework/` runs only when that predicate is true or the call is already inside a branch that excludes Windows. This rule governs; the census below is its result at HEAD.
3. When the predicate is false, the write proceeds without setting a mode and without raising. The file keeps the mode the operating system gave it at creation.
4. `render_agent_surfaces.py` uses the predicate from `contained_files`; it does not define its own platform test.
5. Platform behaviour:
   1. Native Windows, any Python version: `os.fchmod` is never called. This matches Python 3.12 and earlier, where the attribute was absent.
   2. macOS, Linux and WSL2 (`os.name == "posix"`): unchanged. The mode is set on the descriptor, and `_set_temporary_mode` keeps its rule that a refused chmod is tolerated only when the descriptor already has the wanted mode.

### Census of mode-setting calls (executed at HEAD, `code_keyword` with `limit=0`, cross-checked with `grep -rn chmod`)

Queries `fchmod`, `os.chmod`, `lchmod` and `.chmod(` over `.wavefoundry/framework/`. There is no `lchmod` call and no non-test `Path.chmod` call. Non-test results:

| Site | Call | Guard at HEAD | Decision |
| ---- | ---- | ------------- | -------- |
| `contained_files.py:146` | `hasattr(os, "fchmod")` inside `_DIR_FD_SUPPORTED` | also requires `os.supports_dir_fd`, empty on Windows | No change |
| `contained_files.py:703` | `os.fchmod` in `open_contained_append` | `not _windows()` | No change |
| `contained_files.py:754` | `os.fchmod` in `_set_temporary_mode` | none in the function; callers decide | Guard at the path-branch caller (line 951) through `can_chmod`; the descriptor branch (lines 929 and 931) runs only when `_dir_fd_supported()` is true, which excludes Windows |
| `contained_files.py:906` | `can_chmod = hasattr(os, "fchmod")` | `hasattr` only | Replace with the predicate |
| `contained_files.py:914` | `os.fchmod`, unchanged-content path | `can_chmod` | Covered by line 906 |
| `render_agent_surfaces.py:2918` | `os.fchmod` in `_write_text_exclusive_identity` | `hasattr` only | Use the predicate |
| `render_agent_surfaces.py:2979` | `os.fchmod` on the temporary file in `_write_bytes_atomic_exclusive_identity` | `hasattr` only | Use the predicate |
| `render_agent_surfaces.py:3007` | `os.fchmod` on the direct-copy fallback | `hasattr` only, inside the `else` of `contained_files._windows()` | Use the predicate for one uniform rule; this site is already unreachable on Windows |
| `repair_ppol_memory_staging.py:253` | `os.chmod(path)` | none | No change (path chmod, see below) |
| `upgrade_extensions.py:2898` | `os.chmod(path)` | none | No change |
| `run_tests.py:1865`, `run_tests.py:1866` | `os.chmod(path)` in an `rmtree` retry | `except OSError: pass` | No change |
| `setup_index.py:129` | `os.chmod(path)` in an `rmtree` retry | `except OSError: pass` | No change |
| `upgrade_wavefoundry.py:2375` | `os.chmod(path)` in an `rmtree` retry | `except OSError: pass` | No change |

`test_worker_guard.py:160` names the audit event string `"os.chmod"` and calls nothing. Test files and the two `upgrade_old_runner` text fixtures are outside the rule.

### Claim status (seed-209 `execution_status`)

| Claim | Status |
| ----- | ------ |
| With `_windows()` true, the path branch selected and `os.fchmod` raising `PermissionError`, HEAD raises from `write_contained_bytes` (new file whose creation mode differs from the wanted mode, `executable=True`, and unchanged content with a differing mode) and from both `render_agent_surfaces` writers with `mode=0o444` | `executed` (simulation on macOS, Python 3.14.8) |
| In the same simulation a new file whose creation mode already equals the wanted mode succeeds at HEAD, because `_set_temporary_mode` tolerates the refusal; `open_contained_append` never calls `os.fchmod` | `executed` |
| `os.fchmod` on native Windows with Python 3.13 or later fails with WinError 5 on these descriptors | `unverified` (field report; no Windows host in this environment) |
| On Windows `fstat` reports a synthetic mode (`0o666` or `0o444`), so the `_set_temporary_mode` tolerance does not hold for a requested mode such as `0o600` | `inferred` |
| The `os.chmod(path)` sites do not share the defect: path chmod has been supported on Windows in every supported Python version, sets only the read-only attribute, and did not change behaviour in 3.13 | `inferred` |

## Scope

**Problem statement:** On native Windows with Python 3.13 or later, descriptor chmod calls guarded only by `hasattr(os, "fchmod")` run and fail, so contained writes and review carrier writes raise `PermissionError`.

**In scope:**

- The predicate in `contained_files.py` and its use at the `can_chmod` assignment.
- The three `hasattr(os, "fchmod")` guards in `render_agent_surfaces.py`.
- Tests that simulate Windows on a POSIX host, and the one existing assertion the fix changes.
- A changelog entry under the next release's Fixed section.

**Out of scope:**

- Setting the Windows read-only attribute for a requested read-only mode. Python 3.12 and earlier never did this through these paths.
- The `os.chmod(path)` sites in the census.
- Changing the tolerance rule inside `_set_temporary_mode`.
- A structural lint that forbids new unguarded `os.fchmod` calls (operator decision, 2026-11-20).
- Real read-only support on Windows; that is a separate future design.
- Raising the minimum Python version (it stays 3.11) and adding a Windows Python 3.13 or later run to release checks. The release-check run is a follow-up, not part of this spec.

## Acceptance Criteria

AC-1 and AC-2 together establish the Product Intent. Each test simulates native Windows on the development host by patching `contained_files._windows` to true, selecting the path branch, and replacing `os.fchmod` with a mock that raises `PermissionError`. Each fails at HEAD.

- [x] AC-1: Under the simulation, `write_contained_bytes` succeeds and the `os.fchmod` mock records zero calls in each of these cases. The zero-call assertion is required in every case, because case 1 can succeed at HEAD when the creation mode already equals the wanted mode.
  1. A new file written with an explicit `mode`.
  1. A new file written with `executable=True`.
  1. An existing file with unchanged bytes and a `mode` that differs from its current mode; the call returns false and the bytes are intact.
- [x] AC-2: Under the simulation, `_write_text_exclusive_identity` and `_write_bytes_atomic_exclusive_identity` in `render_agent_surfaces.py`, each called with `mode=0o444`, publish the exact content, leave no temporary file, and the `os.fchmod` mock records zero calls. At HEAD both raise `PermissionError`.
- [x] AC-3: On the unpatched POSIX host the same entry points still set the requested mode: a contained write with an explicit mode and both review carrier writers with `mode=0o444` leave a file whose permission bits equal the request. This fails if the fix disables descriptor chmod everywhere.
- [x] AC-4: The change's own suites and every test it adds pass (`test_contained_files.py`, `test_platform_diagnostics_followups.py` and the review carrier publication tests in `test_render_agent_surfaces.py`), and no failure elsewhere is attributable to this change.

## Tasks

- [x] Open `framework_edit_allowed`; add the predicate to `contained_files.py` beside `_windows()` and use it for `can_chmod`.
- [x] Replace the three `hasattr(os, "fchmod")` guards in `render_agent_surfaces.py` with the predicate from `contained_files`.
- [x] Add the simulated-Windows tests for AC-1 and AC-2 and confirm each fails with the fix reverted in a scratch tree.
- [x] Update the existing publication test in `test_render_agent_surfaces.py` (the `windows-rename` branch asserts mode `0o444` whenever `os.fchmod` exists) so it expects the mode only where the predicate is true; keep the POSIX branches asserting it for AC-3.
- [x] Add a Fixed entry to the changelog.
- [x] Run the focused suites, then the full framework suite last; close the gate.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                         |
| ---------- | ----------- | ---------- | ----------------------------- |
| fix        | implementer | none       | Predicate and four guard uses |
| tests      | implementer | fix        | Simulation tests, AC-3 update |


## Serialization Points

- `.wavefoundry/framework/scripts/contained_files.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_contained_files.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- The root changelog gains one Fixed entry.

## Affected Architecture Docs

N/A. The change is confined to a platform guard inside two modules; no boundary, flow or verification seam moves. `docs/references/native-windows-support.md` does not mention descriptor chmod and needs no edit.

## AC Priority


| AC   | Priority  | Rationale                                                          |
| ---- | --------- | ------------------------------------------------------------------ |
| AC-1 | required  | The contained write path is the reported setup and record failure. |
| AC-2 | required  | Review carrier writes are the second reported failure.             |
| AC-3 | required  | Guards against disabling mode setting on POSIX.                    |
| AC-4 | important | Confirms the changed suites, including the adjusted assertion.     |


## Progress Log

2026-11-21: The full framework suite passed on the reviewed changes. It ran 13,123 tests across 251 files in 741 seconds with 12 skips.


| Date       | Update                                                                                   | Evidence                                              |
| ---------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 2026-11-20 | Spec authored. Census run with `limit=0`; HEAD failure reproduced by simulation on macOS. | Census and claim tables under Requirements            |
| 2026-11-20 | Operator decisions recorded: `0o444` is not applied on Windows, the `windows-rename` subtest update is in scope, no structural lint, minimum Python stays 3.11. Spec relocated into the wave folder. | Decision Log rows marked operator decision |
| 2026-11-20 | Readback: add one call-time predicate `_can_set_descriptor_mode()` beside `_windows()` in `contained_files.py` (`os.fchmod` exists and not native Windows); use it for `can_chmod` and for the three `hasattr(os, "fchmod")` guards in `render_agent_surfaces.py`. ACs: AC-1 contained write under simulated Windows makes zero `os.fchmod` calls in three cases; AC-2 both carrier writers with `mode=0o444` publish and make zero calls; AC-3 POSIX still sets the mode; AC-4 focused suites pass. Scope boundary: no change to `_set_temporary_mode`, `open_contained_append`, `_DIR_FD_SUPPORTED` or any `os.chmod(path)` site. Files: the four Serialization Points plus the root changelog. Example: simulated Windows, `write_contained_bytes(root, target, b"x", executable=True)` raises `PermissionError` before and returns true with zero `os.fchmod` calls after. | Spec Requirements 1 to 5 |
| 2026-11-20 | Implemented. `_can_set_descriptor_mode()` added beside `_windows()` in `contained_files.py` as a call-time function (`hasattr(os, "fchmod") and not _windows()`); `can_chmod` and the three `render_agent_surfaces.py` guards use it. Non-test `os.fchmod` census after the edit is unchanged: six calls, each under the predicate, `not _windows()` or `_dir_fd_supported()`. | `git diff` of the two modules |
| 2026-11-20 | Tests added. `test_contained_files.WindowsBranchTests`: three simulated-Windows tests (new file with `mode`, new file with `executable=True`, unchanged bytes with a differing mode), each asserting zero `os.fchmod` calls, plus `test_off_windows_the_path_branch_still_sets_the_requested_mode` for AC-3. `test_render_agent_surfaces.MovePublicationIdentityTests.test_simulated_windows_carrier_writers_never_call_fchmod` covers the text writer and the bytes writer on its hard-link and rename routes. The `windows-rename` subtest now asserts the mode is not `0o444`; the POSIX assertions are judged from the host (`hasattr(os, "fchmod") and os.name != "nt"`), not from the predicate under test. Known-bad at HEAD (tests present, fix absent): all four simulated-Windows tests and the `windows-rename` subtest fail (`PermissionError`, or `1 != 0` calls for the tolerated new-file case). | `.wavefoundry/work/23z45/23z47/known-bad-head.log` |
| 2026-11-20 | Landing rule, mutants run in a scratch copy of the framework tree. M2 predicate returns false: `test_off_windows_the_path_branch_still_sets_the_requested_mode`, `WriteRuleTests.test_unchanged_bytes_write_nothing_and_a_mode_is_kept_or_set`, the `hard-link` and `direct-copy` publication subtests and `test_text_publication_companion_and_legacy_returns` fail. M3 `can_chmod = hasattr(os, "fchmod")`: the three AC-1 tests fail. M4.1 text-writer guard reverted to `hasattr`: the `text` subtest fails. M4.2 temporary-file guard reverted: the `bytes-hard-link` and `bytes-rename` subtests and the `windows-rename` subtest fail. M4.3 direct-copy guard reverted: no test fails. That mutant is equivalent, because the site sits in the `else` of `contained_files._windows()` and the predicate equals `hasattr` there; the spec's Decision Log takes the predicate at that site for uniformity, not as a guard. | Mutation run output in the implementer session; scratch tree removed |
| 2026-11-20 | Focused suites pass with the fix: `test_contained_files.py` 50 tests (1 skipped), `test_platform_diagnostics_followups.py` 5, `test_render_agent_surfaces.py` 222. Run with `python3 -B -m unittest discover -s tests -p <file>`; the full suite and the gate close are left to the coordinator, so the last task and AC-4 stay open. Changelog: the root changelog had no Unreleased heading, so `## [Unreleased]` with a Fixed section and this change's entry was added. Platform behaviour: native Windows (any Python) never calls `os.fchmod` through these paths and files keep their creation mode, simulated here and not executed on a Windows host; macOS, Linux and WSL2 (`os.name == "posix"`) are unchanged and still set the mode on the descriptor. | `.wavefoundry/work/23z45/23z47/focused-fixed.log` |
| 2026-11-20 | Delivery repair D1-23z47-windows-identity-fixture. On macOS with native Windows capabilities simulated, the identity fixture itself forced a POSIX writer twice and hit two descriptor chmod refusals. It now exercises hard-link and rename with the host Windows guard intact. The same fixture passed with zero chmod calls after repair. The macOS run separately exercised the POSIX direct-copy fallback, comparing published bytes and file identity and checking cleanup. Native Windows execution remains unverified. | MovePublicationIdentityTests.test_actual_publication_identity_across_all_byte_publisher_branches |

## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-11-20 | Selected: skip descriptor chmod on native Windows through one predicate in `contained_files.py`, used by every `hasattr(os, "fchmod")` guard. | It restores exactly the behaviour of Python 3.12 and earlier on Windows, which is field-proven, and matches the fix the reporting distribution runs. Efficacy: replaying the motivating case (Windows, 3.14, `os.fchmod` raising) through the predicate skips every failing call; the simulation shows HEAD raises at each guarded site. The predicate controls the outcome and does not advise. | Rejected: call `os.fchmod` and tolerate `PermissionError` on Windows. Weakness: it hides a real refusal and depends on Windows mode semantics nobody here can execute. Rejected: fall back to `os.chmod(path)` on Windows. Weakness: it re-modes through a path, which the contained write rule forbids because the path could be a link. |
| 2026-11-20 | The direct-copy site at `render_agent_surfaces.py:3007` takes the predicate although it is unreachable on Windows. | One rule for every `os.fchmod` guard is simpler to review than a per-site exception. | Leave it on `hasattr` alone. Weakness: the next reader must re-derive why it is safe. |
| 2026-11-20 | No structural lint for unguarded `os.fchmod` calls. | Six call sites in two modules; the census in this spec and review cover them. A new sensor would be a mechanism the bug does not need. | Source-scan test. Weakness: brittle against formatting and adds review surface. |
| 2026-11-20 | Operator decision: no structural lint for unguarded `os.fchmod` calls. | Confirms the row above. | Add the lint. |
| 2026-11-20 | Operator decision: a requested `0o444` is not applied on native Windows, and updating the `windows-rename` subtest is in scope. | Restores the behaviour of Python 3.12 and earlier. Real read-only support on Windows is a separate future design. | Set the read-only attribute in this change. |
| 2026-11-20 | Operator decision: the minimum Python version stays 3.11. | Raising it to 3.13 or 3.14 was considered and declined. Follow-up outside this spec: a Windows Python 3.13 or later run belongs in release checks. | Raise the minimum to 3.13 or 3.14. |
| 2026-11-20 | The `os.chmod(path)` sites stay unchanged. | Path chmod works on Windows in all supported versions (`inferred`); three of the five calls are Windows read-only clearing inside `except OSError`. | Guard them too. Weakness: it would break the Windows `rmtree` retry they exist for. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The WinError 5 behaviour is `unverified` here; the simulation may not match real Windows. | The fix does not depend on the exact error: it never calls `os.fchmod` on Windows. The reporting distribution runs the same guard in the field. |
| A requested read-only mode (`0o444`) is not applied on Windows. | Accepted by the operator on 2026-11-20; same as Python 3.12 and earlier. Real read-only support is a separate future design. |
| No Windows Python 3.13 or later run exists in release checks, so a regression would again surface in the field. | Follow-up outside this spec: add that run to release checks. |
| The predicate is patched wrongly in tests and masks a POSIX regression. | AC-3 asserts the mode on the unpatched host. |
| WSL2 is misread as Windows. | `_windows()` tests `os.name == "nt"`; WSL2 reports `posix` and keeps descriptor chmod. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
