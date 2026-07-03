# Dev/test-infra Windows hardening: run_tests run-lock + UTF-8 subprocess capture in build_pack

Change ID: `1p9iy-bug dev-test-infra-windows-hardening`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-03
Wave: TBD

## Rationale

Three dev/CI-host paths carry native-Windows portability defects. None ship to target-repo runtime — they run only on a contributor's or release host's machine — but one of them blocks a native-Windows contributor from running the framework test suite at all.

- **F16 (blocker) — `run_tests.py` run-lock is POSIX-only.** `_acquire_run_lock` (`run_tests.py:155`) does an unconditional `import fcntl` at `run_tests.py:157` and `fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)` at `run_tests.py:165`; `_release_run_lock` (`run_tests.py:184`) repeats this with `import fcntl` at `run_tests.py:186` and `fcntl.flock(lock_file, fcntl.LOCK_UN)` at `run_tests.py:189`. There is no `os.name` guard and no `msvcrt` branch. `fcntl` does not exist on native Windows, so `_acquire_run_lock` raises `ImportError` and crashes the runner itself — a Windows contributor cannot run `python run_tests.py` at all. The correct portable pattern already exists in this tree: `dashboard_lib.py` `dashboard_lock` branches on `os.name == "nt"` (`dashboard_lib.py:189`) to use `msvcrt.locking` (`dashboard_lib.py:190`, `:196`) versus `fcntl.flock` (`dashboard_lib.py:201`, `:203`), with a matching unlock branch (`dashboard_lib.py:218`–`:224`). `indexer.py` uses the same split.
- **F13 — `run_tests.py` parallel runner mis-decodes child output on cp1252.** `_run_file` captures each test worker's output at `run_tests.py:223` with `capture_output=True` (`:226`) and `text=True` (`:227`) but no `encoding=` and no `PYTHONUTF8` in the child env (built at `run_tests.py:207`–`:221`). On native Windows, `text=True` decodes with the locale codec (cp1252), so any non-ASCII byte in test output raises `UnicodeDecodeError` or mojibakes — while the timeout branch just below already decodes bytes with `errors="replace"` (`run_tests.py:235`–`:236`), so the success path is inconsistent with the timeout path.
- **F12 — `build_pack.py` decodes git/gh output without UTF-8.** Fourteen `subprocess.run(..., capture_output=True, text=True)` sites decode git / gh / `lifecycle_id.py` output with no `encoding=`: `build_pack.py:81` (lifecycle prefix), `:367` (git status), `:388` (git rev-parse), `:408`/`:421` (tag existence), `:446` (gh auth status), `:468` (`git log -1 --format=%s`), `:567`/`:580`/`:588` (git add/diff/commit), `:603` (git tag), `:618`/`:635` (git push), `:656` (gh release create). The clearest failure is `build_pack.py:468`: it reads the last commit subject and feeds it to a regex at `build_pack.py:478` that explicitly matches a unicode `→` in a close-wave subject (`^Close wave \S+ and ship .+\s*(?:→|->)\s*.+$`). On a native-Windows dev host, decoding that `→` under cp1252 either raises `UnicodeDecodeError` mid-release or mojibakes the subject so the tag-message derivation silently misfires.

All three are dev/test-host-only; none alter shipped target-repo runtime behavior.

## Requirements

1. `run_tests.py` must import and run on native Windows: `_acquire_run_lock` and `_release_run_lock` must acquire/release the run lock via `msvcrt.locking` when `os.name == "nt"` and via `fcntl.flock` otherwise, mirroring `dashboard_lib.py`'s existing split. POSIX mutual-exclusion behavior (the "already running" busy diagnostic) must be preserved unchanged.
2. `run_tests.py` `_run_file` must decode captured worker output as UTF-8 with an error-tolerant policy, and must set `PYTHONUTF8=1` in the child env so workers emit UTF-8 regardless of host locale.
3. Every `build_pack.py` `subprocess.run(..., capture_output=True, text=True)` site that decodes git/gh/`lifecycle_id.py` output must pass `encoding="utf-8"`, so a unicode char in a commit subject or gh output no longer raises `UnicodeDecodeError` or mojibakes mid-release.
4. Where practical, add a guard/test that exercises the Windows lock path under a simulated `os.name == "nt"` without requiring a real Windows host.
5. No shipped target-repo runtime behavior changes; the existing framework suite stays green on POSIX.

## Scope

**Problem statement:** Three dev/CI-only code paths (`run_tests.py` run-lock, `run_tests.py` worker-output capture, and `build_pack.py` git/gh subprocess decoding) assume POSIX/`fcntl` and a UTF-8 locale. On native Windows the run-lock crashes the test runner outright (F16), and the two decode paths corrupt or crash on non-ASCII output (F13, F12). These block or degrade a native-Windows contributor and release host without any effect on target-repo runtime.

**In scope:**

- `run_tests.py`: guard `_acquire_run_lock` (`:155`) and `_release_run_lock` (`:184`) on `os.name`, adding a `msvcrt.locking` branch alongside the existing `fcntl.flock` path, mirroring `dashboard_lib.py:189`–`:224`.
- `run_tests.py`: add `encoding="utf-8"` (with error-tolerant handling) to the `_run_file` capture at `:223` and set `PYTHONUTF8=1` in the child env built at `:207`–`:221`.
- `build_pack.py`: add `encoding="utf-8"` to the 14 `capture_output=True, text=True` subprocess sites that decode git/gh/`lifecycle_id.py` output (enumerated in Rationale).
- A unit test / importability guard for the run-lock Windows path under a simulated `os.name`.

**Out of scope:**

- Any target-repo runtime code path (server, indexer runtime behavior, MCP tools) — this change touches only dev/CI-host scripts.
- Broadening the fix to other subprocess sites outside `run_tests.py` and `build_pack.py`, or a general subprocess-encoding audit of the whole tree.
- Introducing a shared cross-platform lock abstraction or any new dependency (e.g. `portalocker`).
- Real native-Windows CI wiring; validation on a live Windows host stays an operator-side spot check.

## Acceptance Criteria

- [x] AC-1: On native Windows (`os.name == "nt"`), `run_tests.py` imports without `ImportError` and both `_acquire_run_lock`/`_release_run_lock` acquire and release the run lock via `msvcrt.locking`; on POSIX, `fcntl.flock` mutual exclusion is unchanged (a second concurrent invocation still returns the "already running" busy diagnostic). — Evidence: both helpers branch on `os.name` (`run_tests.py:160`, `:206` — line refs refreshed at delivery review); `tests/test_run_tests_lock.py` proves the Windows `msvcrt` path (stubbed: acquire/release/roundtrip plus the contended-lock busy diagnostic added at delivery review) and the POSIX busy diagnostic (`RunLockPosixMutualExclusionTests`). The lock-file module's tests are 6 OK (the earlier "9 tests" count spanned this module plus the build_pack tag-derivation class).
- [x] AC-2: `_run_file`'s `subprocess.run` passes `encoding="utf-8"` with an error-tolerant policy, and the child env sets `PYTHONUTF8=1`; non-ASCII worker output is decoded without `UnicodeDecodeError` or mojibake under a cp1252 host locale. — Evidence: `_run_file` passes `encoding="utf-8", errors="replace"` to the capture (consistent with the timeout branch's replace-decode) and, per delivery review, now builds the child env via `subprocess_util.utf8_child_env` so BOTH `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` are set (an inherited `PYTHONIOENCODING=cp1252` would otherwise win over `PYTHONUTF8`, per the 1p8gv helper contract). Pinned by the new `RunFileEncodingTests` kwarg-capture test (the AC previously had no automated test).
- [x] AC-3: Every `build_pack.py` `subprocess.run(..., capture_output=True, text=True)` site decoding git/gh/`lifecycle_id.py` output passes `encoding="utf-8"`; specifically the `git log -1 --format=%s` decode returns a subject containing `→` intact so the regex matches, with no `UnicodeDecodeError`. — Evidence: all 14 sites now pass `encoding="utf-8"` (verified: 14 `text=True` → 14 paired `encoding="utf-8"`); `tests/test_build_pack.py::test_git_log_decoded_as_utf8` asserts the `encoding="utf-8"` kwarg and the intact `→` subject.
- [x] AC-4: A unit test confirms the run-lock helpers select the Windows path under a simulated `os.name == "nt"` (with a stubbed `msvcrt`) and do not raise `ImportError`. — Evidence: new `tests/test_run_tests_lock.py::RunLockWindowsPathTests` (3 tests: acquire, release, roundtrip-no-ImportError).
- [x] AC-5: No target-repo runtime behavior changes; the existing suite stays green on POSIX (no new `__pycache__`). — Evidence: change is confined to two dev/CI-host scripts (`run_tests.py`, `build_pack.py`), no runtime paths touched; my owned test modules pass (9 OK), run with `-B` so no bytecode was written. Full-suite POSIX green is confirmed by the coordinator's central run (I must not run `run_tests.py` while siblings edit the shared tree).

## Tasks

- [x] Re-read the three cited sites to confirm constructs and current line numbers before editing (tree has wave 1p9hn applied). — All three confirmed: F16 `run_tests.py:157`/`:165`/`:186`/`:189`; F13 `run_tests.py:222`–`:229`; F12 the 14 `text=True` sites incl. `build_pack.py:468` (`→` regex at `:478`).
- [x] F16: refactor `_acquire_run_lock` and `_release_run_lock` to branch on `os.name == "nt"`, using `msvcrt.locking(...LK_NBLCK, 1)` / `LK_UNLCK` on Windows and the existing `fcntl.flock` on POSIX, mirroring `dashboard_lib.py`. Map the Windows `OSError` to the "already running / lock file busy" diagnostic; take the lock on a SENTINEL byte at `_LOCK_BYTE_OFFSET` (1 GiB) so the same-handle pid write/truncate at byte 0 is not blocked. — Done; POSIX path preserved (BlockingIOError → busy, other exceptions → "could not acquire").
- [x] F13: add `encoding="utf-8", errors="replace"` to the `_run_file` `subprocess.run` (consistent with the timeout branch's replace-decode) and add `env["PYTHONUTF8"] = "1"` to the child env dict.
- [x] F12: add `encoding="utf-8"` to each of the 14 `capture_output=True, text=True` `subprocess.run` sites in `build_pack.py` (lifecycle prefix, git status/rev-parse/tag-verify/ls-remote/gh-auth/git-log/add/diff/commit/tag/push-main/push-tag/gh-release). — Verified 14 `text=True` → 14 paired `encoding="utf-8"`; line 274's `subprocess.run` (no capture, no decode) correctly untouched.
- [x] Add a unit test that patches `os.name` to `"nt"` and injects a stub `msvcrt` into `sys.modules`, asserting the run-lock helpers select the Windows locking path without `ImportError`. — New `tests/test_run_tests_lock.py` (3 Windows-path tests + 1 POSIX busy test).
- [x] Run the POSIX suite; confirm green and clean up any stray `__pycache__`. — Delegated to the coordinator's central full-suite run (I must not launch `run_tests.py` while siblings edit the shared tree). My owned modules pass (`tests.test_run_tests_lock` + `tests.test_build_pack.TagMessageDerivationTests`: 9 OK); run with `-B`, so no `__pycache__` was written by my run (the pre-existing gitignored `scripts/__pycache__` is from another process, not this change).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| workstream-1 (F16 run-lock os.name guard + Windows-path test) | implementer | — | Edits `run_tests.py:155`–`:195`; mirror `dashboard_lib.py:189`–`:224`; the blocker fix. |
| workstream-2 (F13 UTF-8 capture + PYTHONUTF8 child env) | implementer | workstream-1 | Also edits `run_tests.py` (`:207`–`:229`); serialized after WS1 to avoid same-file merge coordination. |
| workstream-3 (F12 build_pack UTF-8 subprocess decoding) | implementer | — | Independent file (`build_pack.py`); parallelizable with WS1/WS2. |


## Serialization Points

- `run_tests.py` is edited by both workstream-1 (F16) and workstream-2 (F13). Serialize WS2 after WS1 (single-author or sequential) to avoid overlapping edits to the same file; both touch nearby regions (`:155`–`:229`).
- `build_pack.py` (workstream-3) is an isolated file with no overlap with `run_tests.py`; it may proceed in parallel.

## Affected Architecture Docs

N/A — the change is confined to two dev/CI-host scripts (`run_tests.py`, `build_pack.py`) and adds platform-portability guards + decode encodings. It introduces no new boundary, data/control flow, or verification strategy: the test *architecture* (what is verified and how the suite is organized) is unchanged; only the runner's ability to import and decode on native Windows is fixed. No `docs/ARCHITECTURE.md` or `docs/architecture/*` update is warranted.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | F16 is the blocker: without the `os.name` guard the test runner raises `ImportError` on native Windows, so a Windows contributor cannot run the suite at all. |
| AC-2 | important | F13 corrupts/crashes on non-ASCII worker output on cp1252 hosts; degrades but does not fully block the runner. |
| AC-3 | important | F12 can crash or silently mis-derive the tag message mid-release on a native-Windows dev host; release-time correctness, dev-host only. |
| AC-4 | important | The simulated-`os.name` test is the only portable guard against F16 regressing without a live Windows host. |
| AC-5 | required | Confirms the change is truly dev/test-host-only with zero target-repo runtime impact and no POSIX regression. |


## Progress Log


| Date | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-07-02 | Scoped from the native-Windows audit and dashboard/indexer comparison; verified all three cited sites against the current tree (wave 1p9hn applied, line numbers re-confirmed): F16 `run_tests.py:157`/`:165`/`:186`/`:189`, F13 `run_tests.py:223`/`:226`–`:229`, F12 `build_pack.py:468` (`→` decode feeding `:478` regex) + 13 sibling sites. | Windows audit `wf_eab9a03d-004`; comparison `wf_33ca6bdb-757`; reference pattern `dashboard_lib.py:189`–`:224`. |
| 2026-07-02 | Delivery-review fix pass: `_run_file` child env now built via `subprocess_util.utf8_child_env` (adds `PYTHONIOENCODING=utf-8` alongside `PYTHONUTF8=1` — closes the inherited-cp1252 override gap the factor-12 lane found); added `RunFileEncodingTests` (kwarg/env capture — F13 previously evidence-by-diff-read only) and `test_windows_busy_lock_reports_already_running` (the stubbed contended-lock branch previously uncovered); refreshed drifted line refs in AC-1 evidence. | `tests.test_run_tests_lock` 6 OK + `SetupPhase1DeadlineTests` 18 OK |
| 2026-07-02 | Implemented F16/F13/F12. F16: added `_LOCK_BYTE_OFFSET` and branched `_acquire_run_lock`/`_release_run_lock` on `os.name` (msvcrt sentinel-byte lock on Windows, fcntl.flock on POSIX; POSIX busy/other-error split preserved). F13: `_run_file` sets `PYTHONUTF8=1` in the child env and passes `encoding="utf-8", errors="replace"`. F12: added `encoding="utf-8"` to all 14 git/gh/lifecycle subprocess sites. Added `tests/test_run_tests_lock.py` (4 tests) and `test_build_pack.py::test_git_log_decoded_as_utf8`. | 4 files ast-parse clean; owned test modules 9 OK (`-B`, no `__pycache__` written). Central full-suite POSIX run delegated to the coordinator. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-07-02 | Mirror `dashboard_lib.py`'s `os.name` `fcntl`/`msvcrt` split in `run_tests.py` rather than adding a shared lock abstraction. | Proven in-tree pattern; keeps the fix minimal and consistent with `dashboard_lib.py`/`indexer.py`. | New shared lock helper (rejected — scope creep); `portalocker` dependency (rejected — no new deps); skip locking on Windows (rejected — loses the concurrent-run guard). |
| 2026-07-02 | Add `errors="replace"` alongside `encoding="utf-8"` for the `run_tests.py` capture. | Matches the existing timeout-branch replace-decode (`:235`–`:236`); a stray byte must never crash the runner. | `encoding` only (rejected — an odd byte re-raises); `errors="strict"` (rejected — reintroduces the crash). |
| 2026-07-02 | Keep scope to F12/F13/F16 dev/test-host paths only. | These do not ship to target-repo runtime; a broader subprocess-encoding audit is a separate concern. | Whole-tree subprocess encoding sweep (deferred — out of scope). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `msvcrt.locking` is mandatory byte-range; locking byte 0 could interfere with the same-handle pid write/truncate at `run_tests.py:173`–`:179`. | Follow `dashboard_lib.py`'s sentinel-byte-offset approach (`:192`–`:196`) if byte-0 locking interferes; a single handle writing to its own locked region is permitted — verify on the operator Windows spot check. |
| No live native-Windows CI in this environment, so the Windows lock path can't be exercised end-to-end here. | Simulated-`os.name` unit test (AC-4) + operator native-Windows spot check post-merge; the fix mirrors an already-Windows-validated pattern (`dashboard_lib.py`). |
| `errors="replace"` could mask genuinely garbled test/git output. | Acceptable for dev/test decode; matches the existing timeout-branch behavior and never crashes the runner mid-suite/mid-release. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
