# Python 3.14 Suite Compatibility: Dead Lance Import, Faulthandler C Stack, And Pathlib Predicates That No Longer Raise

Change ID: `1zrai-bug python-3-14-suite-compatibility`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-10-04
Wave: 1zqe4 reload-tool-path-free

## Rationale

The operator's Python moved to 3.14.8 (Homebrew) and the tool venv was rebuilt cleanly on it. On the committed HEAD tree three framework test files now fail under that venv, and the close gate needs a whole-suite green receipt, so these failures block closing wave `1zqe4`. Python 3.14 is inside the supported range (3.11 through 3.14), so each failure is either a product defect on a supported interpreter or a test that depended on an undeclared environment. Probes against a HEAD scratch copy, run on both the 3.14 venv and the preserved 3.13 venv, located a distinct root cause for each.

1. `test_indexer.IncrementalBuildTests.test_framework_seeds_and_readme_fold_into_project_docs_index` raises `ModuleNotFoundError: No module named 'lancedb'`. The test body carries an unused `import lancedb` (line 1779 at HEAD) left over from the retired LanceDB backend; the assertions read rows through `_read_index_chunks`, which is SQLite-only. The old venv happened to contain lancedb, so the dead import passed. lancedb is not a declared runtime dependency; the only product import is the migration-only reader `sqlite_storage_migration._legacy_table`, which already fails closed with `storage_legacy_reader_missing` when it is absent. Probe: deleting the line in the scratch copy makes `test_indexer.py` pass (396 tests OK) on 3.14.
2. `test_setup_index.ProviderProbeChildIsolationTests.test_a_native_crash_in_the_measurement_never_reaches_the_caller` no longer finds `in _measure_embedding_provider` in the reported crash reason. Python 3.14 added C stack dumping to `faulthandler`, on by default (`faulthandler.enable(..., c_stack=True)`): after the Python traceback it now prints a "Current thread's C stack trace" block of about twenty `Binary file ...` lines plus an `Extension modules:` line. `setup_index._provider_probe_stderr_tail` keeps only the last `_PROVIDER_PROBE_STDERR_TAIL_LINES` (5) non-blank lines, so on 3.14 the tail is interpreter boilerplate (`Py_RunMain`, `pymain_main`, `Py_BytesMain`, `dyld start`) and the Python frame an operator needs to see which measurement step crashed falls out. Probe: a direct segfault under `faulthandler.enable()` prints the Python block then the C block on 3.14, and the Python block only on 3.13.16. This is a product defect: operator-facing diagnostics regressed on a supported interpreter. Probe: calling `faulthandler.enable(c_stack=False)` when `sys.version_info >= (3, 14)` (the keyword does not exist before 3.14) in `_provider_probe_child_main` makes `test_setup_index.py` pass on both 3.14.8 (194 OK) and 3.13.16 (194 OK).
3. `test_review_evidence.ReviewAuthorityFacadeTests.test_unresolvable_authority_path_error_is_path_free`, subtests `dir ledger` and `dir validation`, get `canonical review event ledger is unreadable: events.jsonl: Permission denied` and `wave record is unreadable: wave.md: Permission denied` instead of `review authority path is not safely resolvable`. Python 3.14 reimplemented the `pathlib.Path` predicates on top of `os.path`: `Path.exists`, `Path.is_symlink`, `Path.is_file` and `Path.is_dir` now return `False` on any `OSError`. On 3.11 through 3.13 they returned `False` for an ignored set and raised every other `OSError`. The ignored set is `_IGNORED_ERRNOS = (ENOENT, ENOTDIR, EBADF, ELOOP)` plus `_IGNORED_WINERRORS = (21, 123, 1921)` (in `pathlib` on 3.11 and `pathlib._abc` on 3.13, both read from the interpreters on 2026-10-04). So `EACCES` raised before 3.14, but `ENOTDIR` and `ELOOP` already read as absent. `review_evidence._review_authority_path_error` relies on `wave_md.is_symlink()` and `wave_md.exists()` raising on an untraversable wave directory, which routes to its `except (OSError, RuntimeError)` "not safely resolvable" branch. On 3.14 both predicates return `False`, the guard reports the authority path as safe without having determined it, and the later read fails with the generic unreadable message. Probe: with a mode-0 wave directory, `Path.is_symlink()`, `Path.exists()` and `Path.is_file()` raise `PermissionError` (errno 13) on 3.11.17 and 3.13.16 and return `False` on 3.14.8; `os.lstat`, `os.path.realpath(strict=True)` and `Path.resolve(strict=True)` raise `PermissionError` on all three. The product still refuses (the read fails), so nothing is accepted that should not be, but the guard documented as "reject symlinked/out-of-wave review authority before any read" now passes an undetermined path, which is a product defect in the guard's contract, not a fixture assumption. Probe: replacing the three predicate pairs with an `os.lstat` helper (not-found reads as absent, every other `OSError` propagates, `stat.S_ISLNK` for the symlink test) makes `test_review_evidence.py` pass on 3.14.8 (170 OK) and 3.13.16 (170 OK). A further probe on 3.11, 3.13 and 3.14 (`r2probe/pp.py`) confirmed the per-errno shape: for a member under a mode-0 directory the predicates raise `PermissionError` before 3.14 and return `False` on 3.14; for a member under a regular file (`ENOTDIR`) and under a self-referential symlink (`ELOOP`, errno 62 on macOS) they return `False` on all three; `os.lstat` raises in all three cases on all three interpreters.

## Requirements

1. The fold regression test must not import lancedb; no discovered test module may require lancedb unless it skips with a named reason when it is absent.
2. The provider probe child must keep the Python-level faulthandler frames inside the reported stderr tail on every supported interpreter, 3.11 through 3.14.
3. `_review_authority_path_error` must decide without `pathlib` predicates, by this rule on every supported interpreter:
   - It first `lstat`s the wave directory. Any `OSError`, including not-found, is "not safely resolvable", as today (today the following `resolve(strict=True)` raises for a missing directory). A symlink keeps today's "wave directory may not be a symlink" message. Anything else that is not a directory (`stat.S_ISDIR` on the `lstat` result) is "not safely resolvable". With a real directory as the parent, `ENOTDIR` on a member cannot arise from a regular-file parent.
   - It then `lstat`s `wave.md` and `events.jsonl`. `FileNotFoundError` and `NotADirectoryError` mean absent. Windows reports the missing case as `FileNotFoundError` (WinError 2 or 3), so both platforms agree. `ELOOP` and every other `OSError` propagate to "not safely resolvable".
   - The escape checks keep `resolve(strict=True)` and `is_relative_to`, unchanged.
4. Every message on these paths stays path-free, as today.
5. Behaviour is identical on Windows, macOS, Linux and WSL2 apart from platform facilities that do not exist (POSIX signals, POSIX permission bits, symlink privilege), and the fixes stay green on Python 3.11 through 3.13.

## Scope

**Problem statement:** three framework test files fail on Python 3.14 at HEAD; two of the causes are product defects on a supported interpreter (lost crash diagnostics; an authority guard that silently passes an undetermined path) and one is a dead test import of a retired backend.

**In scope:**

- `.wavefoundry/framework/scripts/tests/test_indexer.py`: delete the unused `import lancedb` in `test_framework_seeds_and_readme_fold_into_project_docs_index`.
- `.wavefoundry/framework/scripts/setup_index.py`: in `_provider_probe_child_main`, enable faulthandler without the C stack on interpreters that support the `c_stack` keyword (3.14 and later), and leave the call unchanged before 3.14.
- `.wavefoundry/framework/scripts/review_evidence.py`: in `_review_authority_path_error`, replace `wave_dir.is_symlink()` with the wave-directory `lstat` check, and the `is_symlink()` / `exists()` pairs on `wave.md` and `events.jsonl` with a member `lstat` helper, both per Requirement 3. Callers checked: `read_review_event_ledger` (line 4455) and `validate_external_review_evidence` (line 4484) are the only callers, and both pass a wave record path or its directory. A symlinked wave directory is never legitimate: the guard already rejects it with its own message, which the `S_ISLNK` branch keeps. A missing or non-traversable wave directory already ends in "not safely resolvable" through `resolve(strict=True)`. The only classification that changes for a wave directory is a regular file standing in for one. Today that passes the guard and fails later at the read with "unreadable ... Not a directory"; with the change it is "not safely resolvable". No test relies on the old result (searched `test_review_evidence.py` and `test_server_tools.py`). A Windows junction as the wave directory reports `S_ISDIR` and not `S_ISLNK` from `os.lstat`, just as `is_symlink()` returns `False` for it today, so its handling is unchanged.
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`: make `test_unresolvable_authority_path_error_is_path_free` meaningful on Windows. Fixture shape at HEAD (verified): one test method builds two fixtures, a mode-0 wave directory (`os.chmod(wave_dir, 0)`, subtests `dir ledger` and `dir validation`) and a self-referential symlink parent (`os.symlink("loop", loop)`, subtests `loop ledger` and `loop validation`), with no `os.name` guard and no privilege handling. On Windows chmod 0 only sets the read-only attribute and does not deny traversal, so the `dir` subtests cannot reach the denial branch, and `os.symlink` raises `OSError` (WinError 1314) without Developer Mode or elevation, which errors the whole test. The test is split into two methods, one per fixture, so a skip in one never hides the other's assertions. The mode-0 method skips on `nt` with a stated reason. The symlink-loop method creates the loop with `os.symlink`. On `nt`, when that raises `OSError` with `winerror == 1314` (`ERROR_PRIVILEGE_NOT_HELD`), it switches to a no-privilege fixture that still reaches the guard: a wave directory path with a component Windows rejects as invalid (`bad|name`; not `:`, which is alternate data stream syntax, and not `<`, `>`, `"`, `*` or `?`, which the `FindFirstFile` stat fallback may treat as DOS wildcards). `os.lstat` raises `OSError` (WinError 123, `ERROR_INVALID_NAME`) on it, and the guard reports "not safely resolvable". It skips with a stated reason only if that fixture also fails to raise. Any other `OSError` from `os.symlink`, or any `OSError` off `nt`, fails the test rather than skipping. On a Windows host with Developer Mode or elevation the loop fixture runs its full assertions.
- Pins in the existing test files, each oracle-diverse (asserting the reported text, not the patched call):
  - Authority guard, on every interpreter: the test patches `Path.is_symlink` and `Path.exists` to return `False` on any `OSError` (the 3.14 semantics) and asserts that the mode-0 fixture still reports "not safely resolvable", path-free, through both the ledger and validation paths. Against the HEAD guard on 3.11 to 3.13 the patched predicates hide the `PermissionError` and the test fails, so the pin no longer depends on running 3.14.
  - Faulthandler, on 3.14 only: the reported crash reason contains `_measure_embedding_provider`. No pin on an older interpreter can be oracle-diverse here, because the C stack block exists only in 3.14's `faulthandler`. Before 3.14 there is no output for a patch to imitate, and asserting the `c_stack=False` call would assert the patched call. AC-3 pins the call shape before 3.14 as a separate, call-level check.

**Out of scope:**

- A repository-wide migration of the other `pathlib` predicate call sites. Census (predicate: a call to `.exists()`, `.is_symlink()`, `.is_file()` or `.is_dir()` with no arguments, not on `os.path`, inside the body of a `try` whose handlers catch `OSError`, `PermissionError`, `Exception` or `BaseException`, in a non-test `.py` file under `.wavefoundry/framework/scripts/`): 141 sites in 36 files, led by `setup_readiness.py` (18), `wf_server/server_impl.py` (16), `model_bundle.py` (9), `record_paths.py` (9) and `upgrade_wavefoundry.py` (9). Most of those handlers exist for other calls in the same block, so membership in the census is not evidence of a defect. Triage of that set is planned separately as change `1zraj-bug python-3-14-pathlib-oserror-triage`.
- Adding lancedb, or any migration-only reader, to the runtime dependency set.
- The migration-only lancedb consumers, which already guard absence: `sqlite_storage_migration._legacy_table` (fails closed), `tests/test_sqlite_storage_migration.py` (two `skipTest` guards), `tests/test_storage_upgrade_resume.py` (`skipUnless(_legacy_available())`), and the non-discovered evaluation scripts `tests/vector_backend_eval.py`, `tests/vector_public_eval.py` and `tests/vector_public_filter_smoke.py`.

Lancedb census (predicate: an `import lancedb` or `from lancedb` statement in a `.py` file outside `docs/`, re-derived 2026-10-04): 10 sites, in `sqlite_storage_migration.py` (1), `tests/test_indexer.py` (1), `tests/test_storage_upgrade_resume.py` (2), `tests/test_sqlite_storage_migration.py` (2), `tests/vector_backend_eval.py` (2), `tests/vector_public_eval.py` (1) and `tests/vector_public_filter_smoke.py` (1). The earlier figure of 11 counted `docs/waves/1wfsl structured-docs-retrieval/evidence/walkthrough_include_prefixes.py`, which is under `docs/`. The only unguarded one in a discovered `test_*.py` module is `tests/test_indexer.py:1779`, which is the line this change deletes.

## Acceptance Criteria

- [x] AC-1: `test_framework_seeds_and_readme_fold_into_project_docs_index` passes in a venv without lancedb and the test module contains no lancedb import.
- [x] AC-2: On Python 3.14 a native crash in the provider probe child reports a stderr tail that contains the `_measure_embedding_provider` frame.
- [x] AC-3: On Python 3.11 through 3.13 the provider probe child enables faulthandler exactly as before, with no `c_stack` keyword passed.
- [x] AC-4: `_review_authority_path_error` returns a path-free "not safely resolvable" message for an untraversable wave directory on Python 3.14 and on 3.13.
- [x] AC-5: `_review_authority_path_error` still rejects a symlinked wave directory, `wave.md` or `events.jsonl`, and a member that escapes its wave directory, with the existing messages.
- [x] AC-6: A missing `wave.md` or `events.jsonl` is still treated as absent by the guard, so the existing missing-file messages are unchanged.
- [x] AC-7: Reverting either product fix makes a pinned test fail on Python 3.14.
- [x] AC-8: `test_indexer.py`, `test_setup_index.py` and `test_review_evidence.py` pass under the Python 3.14 tool venv and under a Python 3.13 interpreter.
- [x] AC-9: The change doc states Windows, macOS, Linux and WSL2 behaviour for each fix.
- [x] AC-10: The change's own test files and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-11: On `nt`, the mode-0 cases of the path-free authority test skip with a stated reason that chmod 0 does not deny directory traversal there.
- [x] AC-12: The symlink-loop case leaves the loop fixture only when `os.name == "nt"` and `os.symlink` raises `OSError` with `winerror == 1314`; any other `OSError` fails the test, and the loop fixture runs its full assertions wherever symlinks can be created, including Windows with Developer Mode.
- [x] AC-13: The member check treats only `FileNotFoundError` and `NotADirectoryError` from `os.lstat` as absent, and reports `ELOOP` and every other `OSError` on `wave.md` or `events.jsonl` as "not safely resolvable", pinned by a test that injects `ELOOP` and `EACCES` into the member `lstat`.
- [x] AC-14: A wave directory that `os.lstat` reports as neither a symlink nor a directory (a regular file) gives a path-free "not safely resolvable" message from the guard before any member is inspected, on 3.11 through 3.14.
- [x] AC-15: A test that runs on every supported interpreter patches `Path.is_symlink` and `Path.exists` to return `False` on any `OSError` and asserts the mode-0 fixture still reports a path-free "not safely resolvable" through both the ledger and validation paths, and it fails against the HEAD guard.
- [x] AC-16: The path-free authority test is split into one method per fixture, so a skip of the mode-0 method never skips the symlink-loop assertions and the reverse.
- [x] AC-17: On `nt` without symlink privilege, the symlink-loop method runs an invalid-path-component fixture (WinError 123) that reaches the guard and asserts the path-free "not safely resolvable" message, and skips with a stated reason only if that fixture does not raise.

## Tasks

- [x] Delete the dead `import lancedb` from the fold regression test.
- [x] Gate `faulthandler.enable(c_stack=False)` on `sys.version_info >= (3, 14)` in `_provider_probe_child_main`, with a comment naming the 3.14 C stack and the five-line tail.
- [x] In `_review_authority_path_error`, add the wave-directory `lstat` check and the member `lstat` helper per Requirement 3 (AC-13, AC-14).
- [x] Split `test_unresolvable_authority_path_error_is_path_free` into one method per fixture: the mode-0 method skips on `nt` with a stated reason, and the symlink-loop method uses the `winerror == 1314` no-privilege branch to the invalid-name fixture, skipping only as the last fallback (AC-11, AC-12, AC-16, AC-17).
- [x] Add or tighten pins for AC-2, AC-4, AC-5, AC-6, AC-7, AC-13, AC-14 and AC-15 in the existing test files; confirm each pin goes red against the HEAD code in a scratch copy (on 3.14, and for AC-15 also on 3.13).
- [x] Run the three test files under the 3.14 tool venv and under the 3.13 interpreter (`WAVEFOUNDRY_TOOL_VENV` pointed at a 3.13 venv), in a scratch copy.
- [x] Add a CHANGELOG Unreleased bullet.
- [x] Validate docs.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| lance-import | implementer | none | One-line test deletion. |
| probe-tail | implementer | none | `setup_index.py` plus pin. |
| authority-guard | implementer | none | `review_evidence.py` plus pins. |
| verification | qa | lance-import, probe-tail, authority-guard | Three files on 3.14 and 3.13, scratch copy. |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`, `.wavefoundry/framework/scripts/tests/test_setup_index.py`, `.wavefoundry/framework/scripts/tests/test_review_evidence.py`

## Affected Architecture Docs

N/A. Each fix is confined to one function (or one test line) and changes no boundary, flow or verification architecture; the supported Python range is unchanged.

## Platform Behaviour

- **macOS:** all three failures reproduce on Homebrew Python 3.14.8; the fixes were probed there on 3.14.8 and 3.13.16.
- **Linux and WSL2:** same as macOS. The 3.14 faulthandler C stack is available wherever the interpreter has a backtrace facility (glibc), and the 3.14 pathlib predicate change is platform-independent, so both product fixes apply unchanged. `os.lstat` raises `PermissionError` on an untraversable directory exactly as on macOS.
- **Windows:** the 3.14 pathlib predicate change applies; `os.lstat` raises `PermissionError` on access denial, so the guard classifies the same way. Windows has no POSIX signals or C stack backtrace through `_Py_DumpStack`; with `c_stack=False` nothing is printed for the C stack on any platform, and the existing Windows crash-code path (`_WINDOWS_CRASH_CODE_FLOOR`) is unchanged. `os.chmod(dir, 0)` does not deny traversal on Windows, so the mode-0 cases of the path-free test skip on `nt` with that reason (AC-11); the symlink-loop case runs when Developer Mode or elevation permits `os.symlink`. Without privilege (WinError 1314 only) it runs an invalid-path-component fixture that reaches the guard through WinError 123 (AC-12, AC-17), and it skips only if that fixture does not raise. A loop of two junctions made with `_winapi.CreateJunction` would also need no privilege, but `_winapi` is a private CPython module and the resulting error (WinError 1921) could not be checked without a Windows host, so the public-API invalid-name fixture is preferred. No Windows CI exists, so this branch is verified by reasoning and, where a Windows host is available, by a run there.
- **Python 3.11 through 3.13:** the faulthandler call is unchanged (the `c_stack` keyword is not passed, since it raises `TypeError` before 3.14). For the authority guard, `EACCES` on a member is "not safely resolvable" before and after, since the predicates raised it and the `lstat` helper propagates it. Two classifications deliberately tighten:
  - `ELOOP` on a member (which the predicates read as absent) now propagates as "not safely resolvable". With the wave-directory check in place, a loop through the wave directory itself already fails there, and today it fails at `resolve(strict=True)`, so in practice the change is confined to the member check.
  - A regular file in the wave-directory position is now "not safely resolvable". Today it passes the guard and the read fails.
  `ENOTDIR` on a member is still absent, though a real-directory parent makes it unreachable. The Windows winerrors the predicates ignored (21, 123, 1921) also now propagate from both `lstat` calls, which is the same safe tightening.
- **Windows, missing members:** a missing `wave.md` or `events.jsonl` raises `FileNotFoundError` (WinError 2, or WinError 3 for a missing intermediate directory, both mapped to `ENOENT`), so the absent branch behaves as on POSIX.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Blocks the whole-suite receipt on a clean venv. |
| AC-2 | required | Operator crash diagnostics regressed on a supported interpreter. |
| AC-3 | required | 3.11 through 3.13 must not break on an unknown keyword. |
| AC-4 | required | The authority guard must not pass an undetermined path. |
| AC-5 | required | The guard's existing rejections must survive the rewrite. |
| AC-6 | required | Missing-file handling is a separate, unchanged contract. |
| AC-7 | required | Without a pin the 3.14 behaviour can silently regress. |
| AC-8 | required | Fixes must hold across the supported range. |
| AC-9 | important | Cross-platform statement for an enterprise-critical Windows audience. |
| AC-10 | required | Standard change-scoped verification. |
| AC-11 | required | Windows is enterprise-critical; a fixture that cannot reach its branch there must say so rather than fail. |
| AC-12 | required | Project rule: symlink-dependent tests need a no-privilege branch that keeps the assertion meaningful; a bare `OSError` skip would hide real failures. |
| AC-13 | required | Pins the decided errno rule, including the deliberate `ELOOP` tightening. |
| AC-14 | required | The wave-directory check is what makes member `ENOTDIR` unreachable for a regular-file parent. |
| AC-15 | required | Keeps the guard regression pinned on interpreters other than 3.14. |
| AC-16 | required | One fixture's skip must never hide the other's assertions. |
| AC-17 | important | Keeps the loop-case assertion meaningful on Windows without privilege; not verifiable without a Windows host. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-04 | Implemented. `test_indexer.py`: dead `import lancedb` deleted. `setup_index._provider_probe_child_main`: `faulthandler.enable(c_stack=False)` on 3.14 and later, `enable()` before. `review_evidence._review_authority_path_error`: wave-directory `os.lstat` (symlink message kept, non-directory "not safely resolvable"), new `_authority_member_lstat` (only `FileNotFoundError` and `NotADirectoryError` absent); escape checks unchanged. `test_review_evidence.py`: the path-free test split into mode-0 (skips on `nt`) and symlink-loop (WinError 1314 only, to the `bad\|name` fixture, skip last) methods; new pins for AC-5, AC-6, AC-13, AC-14, AC-15. `test_setup_index.py`: the child-entry test asserts the per-version `faulthandler.enable` call (AC-3); the existing native-crash test is the AC-2 pin. Failing first, HEAD product code in a `git archive HEAD` scratch copy with the new tests: 3.14 red on the native-crash text, the 3.14 call shape, AC-13 absent cases, AC-14, AC-15 and the mode-0 test; 3.13 and 3.11 red on AC-13, AC-14 and AC-15 (AC-15 red on all three); `test_setup_index.py` green on 3.13 at HEAD, as planned (the C stack exists only on 3.14). Mutations of the fixed code in the scratch copy: member helper swallowing every `OSError` turns 8 assertions red (AC-13 `ELOOP` and `EACCES`, AC-15, mode-0); dropping `S_ISDIR` turns AC-14 red; dropping the wave-directory `S_ISLNK` branch turns AC-5 red; passing `c_stack=False` unconditionally turns three `test_setup_index.py` tests red on 3.13. Fixed tree in the repo, focused files: `test_review_evidence.py` 176 OK, `test_setup_index.py` 194 OK, `test_indexer.py` 396 OK, `test_path_containment.py` 23 OK, each on the 3.14 tool venv (no lancedb installed) and on 3.13.16; `ReviewAuthorityFacadeTests` 17 OK on 3.11.17. The repo-change guard tripped on two runs while the parallel implementer edited; the reruns were clean. The `nt` branches (mode-0 skip, WinError 1314 to WinError 123 fixture) were verified by reading only: no Windows host. | `run_tests.py --file` on `~/.wavefoundry/venv` (3.14.8) and `venv-py313-bak` (3.13.16); `/opt/homebrew/bin/python3.11 -m unittest`; scratch `/tmp/wf1zrai-head` |
| 2026-10-04 | Readiness repair. R1: corrected the 3.11 to 3.13 contract in Rationale and Platform Behaviour (`_IGNORED_ERRNOS` and `_IGNORED_WINERRORS` read from 3.11 and 3.13), adopted the wave-directory-first guard rule (Requirement 3, AC-13, AC-14), and recorded the `ELOOP` tightening. Checked both callers of `_review_authority_path_error` and the tests for any reliance on a non-directory wave path (none). Lancedb census corrected to 10 sites outside `docs/`. Added the every-interpreter guard pin (AC-15), the per-fixture split (AC-16), the `winerror == 1314` skip predicate (AC-12) and the invalid-name no-privilege Windows branch (AC-17). The faulthandler pin stays 3.14-only, with the reason stated. | `r2probe/pp.py` run on 3.11, 3.13 and 3.14; `review_evidence.py` lines 775 to 808, 4450 to 4500; `test_review_evidence.py` lines 4564 to 4726; lancedb import search over `.py` files |
| 2026-10-04 | Planned from HEAD scratch-copy probes on 3.14.8 and 3.13.16. | Failing logs `head_test_indexer.log`, `head_test_setup_index.log`, `head_test_review_evidence.log`; probed fixes passed 396, 194 and 170 tests. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-04 | Disable the faulthandler C stack on 3.14 rather than widen the tail. | The C stack bottom is interpreter boilerplate; a version-gated keyword restores the 3.13 output exactly. | Raise the tail line count (bloats every reason, still order-dependent); select the Python traceback block when present (more parsing code). |
| 2026-10-04 | Treat failure 3 as a product defect and fix the guard. | The guard's contract is to reject before any read; on 3.14 it passes an undetermined path. | Change the test to accept the unreadable message (hides the guard regression). |
| 2026-10-04 | Include the Windows fixture fix in this change (coordinator decision). | Windows is enterprise-critical and the project rule requires a no-privilege branch for symlink-dependent tests. | Leave the fixture failing on Windows as a recorded risk. |
| 2026-10-04 | Keep the 141-site pathlib census out of this change (coordinator decision). | It is a separate triage effort, planned as its own bug change doc. | Fold the census into this change. |
| 2026-10-04 | Delete the lancedb import rather than skip the test. | The import is unused; the test is SQLite-only. | Skip when lancedb is absent (loses a real-pipeline regression test). |
| 2026-10-04 | Guard rule (readiness R1, reviewer recommendation combined with the council alternative): `lstat` the wave directory first and require a real directory; members treat `FileNotFoundError` and `NotADirectoryError` as absent; `ELOOP` and every other `OSError` are "not safely resolvable". | The earlier draft said 3.11 to 3.13 raised every non-not-found error, which is wrong (`ENOTDIR` and `ELOOP` were ignored). Requiring a real directory makes member `ENOTDIR` unreachable for a regular-file parent, and `NotADirectoryError` as absent matches Windows, which reports that case as `FileNotFoundError`. Callers checked: no legitimate wave directory is a symlink (already rejected) or a non-directory. | (a) Member `FileNotFoundError` only as absent, with no directory check: a regular-file parent would read as unresolvable through `ENOTDIR` on POSIX but absent on Windows. (b) Reproduce the 3.13 ignored set exactly: keeps `ELOOP` reading as absent in an authority guard. |
| 2026-10-04 | Treat `ELOOP` (and the formerly ignored Windows winerrors 21, 123 and 1921) as "not safely resolvable": a deliberate tightening. | An authority guard should refuse what it cannot determine. Every affected case already fails later at `resolve(strict=True)` or at the read, so nothing that works today stops working. | Keep 3.13 parity for those errors. |
| 2026-10-04 | Add an every-interpreter pin for the guard by patching the predicates to 3.14 semantics; keep the faulthandler text pin 3.14-only. | The guard pin then fails against HEAD on 3.11 to 3.13 too. The C stack block exists only in 3.14's `faulthandler`, so an older-interpreter pin could only assert the patched call. | Pin both on 3.14 only (regressions go unseen on the 3.13 venv); assert the `c_stack` call shape (not oracle-diverse). |
| 2026-10-04 | Split the path-free test per fixture; skip the loop fixture only on `nt` with `winerror == 1314`, falling back first to an invalid-path-component fixture. | A bare `OSError` skip would hide genuine failures, and the project rule prefers a no-privilege branch that still reaches the guard. WinError 123 needs only public APIs. | `_winapi.CreateJunction` loop (private module, unverified error); pure skip. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Other guards rely on `pathlib` predicates raising, now silent on 3.14 (141-site census). | Out of scope here; triaged by the separate change `1zraj-bug python-3-14-pathlib-oserror-triage`. |
| A C-level crash below Python loses its C frames in the reported tail on 3.14. | The tail was five lines and showed only boilerplate; the full stderr remains available when the probe is run directly. |
| The Windows skip branches are not exercised by any CI. | Skip reasons are explicit and narrow (privilege `OSError` only); verify on a Windows host when one is available. |
| Readiness probes ran on macOS only. | Linux and Windows reasoning recorded above; verification lane re-runs on any available host. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
