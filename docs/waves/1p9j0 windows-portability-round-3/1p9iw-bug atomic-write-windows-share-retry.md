# Windows sharing-violation retry for `_atomic_write_text` meta.json replace

Change ID: `1p9iw-bug atomic-write-windows-share-retry`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-03
Wave: TBD

## Rationale

`indexer.py::_atomic_write_text` (`.wavefoundry/framework/scripts/indexer.py:1260-1264`) writes a temp file and swaps it into place with a bare `os.replace(tmp, path)` at line 1264 — no Windows sharing-violation retry. Its sole caller `_save_meta` (`indexer.py:1199-1200`) uses it to persist `meta.json`, and `_save_meta` runs at the end of a build (`indexer.py:3573`).

On POSIX `os.replace` is atomic and never blocks on a concurrent open, so nothing needs to change there. On native Windows, `os.replace` (a `MoveFileEx` rename) fails when the destination is open in another process without full share flags: it raises `PermissionError`/`OSError` with `winerror == 32` (`ERROR_SHARING_VIOLATION`) or `winerror == 5` (`ERROR_ACCESS_DENIED`). During a background index refresh the framework has multiple concurrent `meta.json` readers — `wave_index_health`, `wave_index_build_status`, MCP freshness checks, and the dashboard watcher — any of which may have `meta.json` open at the exact instant of the replace. When that race hits, the exception propagates out of `_save_meta` and aborts the write, leaving freshly built vector data paired with **stale or missing metadata** (the vector store is updated but `meta.json` is not), which then makes the index look stale/broken to every reader that keys off `meta.json`.

The codebase already has the exact remedy idiom for Windows filesystem-lock transients: `setup_index.py::_rmtree_clearing_readonly` / `_clear_readonly_and_retry` (`setup_index.py:149-166`, waves 1p9hk / 1p6d6) clears the Windows-only failure and retries the single failing op, and is a documented no-op on POSIX. This change applies the same "Windows-only, bounded retry, POSIX untouched" shape to the `os.replace` in `_atomic_write_text`.

## Requirements

1. On Windows (`os.name == "nt"`), when `os.replace(tmp, path)` in `_atomic_write_text` raises `PermissionError`/`OSError` with `winerror` in `{5, 32}`, retry the replace a bounded number of times with a short backoff before giving up.
2. If all retries are exhausted, re-raise the last exception (do not silently swallow — a persistent lock must still surface, mirroring the caller-checks-afterward discipline in `setup_index.py:155-157`).
3. On POSIX the behavior is unchanged: `os.replace` is called exactly once with no retry wrapper active (the Windows-only guard makes the retry a no-op path there).
4. Do not retry on unrelated errors (a `winerror` outside `{5, 32}`, or a non-Windows `OSError`) — re-raise immediately so genuine failures are not masked or delayed.
5. Keep the change to a small, self-contained helper local to `indexer.py`; no new module, no config surface, no change to `_save_meta`'s or `_atomic_write_text`'s signatures or call sites.

## Scope

**Problem statement:** `_atomic_write_text` in `indexer.py` swaps `meta.json` into place with a bare `os.replace`, which on native Windows raises a sharing-violation/access-denied error when a concurrent framework reader (index-health, build-status, MCP freshness check, dashboard watcher) has `meta.json` open. The exception aborts `_save_meta`, leaving newly built vector data with stale/missing metadata.

**In scope:**

- Add a bounded Windows-only retry-with-short-backoff around the `os.replace(tmp, path)` call in `indexer.py::_atomic_write_text` (line 1264), triggered only on `PermissionError`/`OSError` whose `winerror` is 5 or 32.
- Re-raise the last exception after retries are exhausted.
- A regression test in `tests/test_indexer.py` that simulates `os.replace` raising `PermissionError` (with `winerror = 32`) on the first attempt and succeeding on retry, asserting the write completes and the final content lands.

**Out of scope:**

- Any change to POSIX behavior or to `os.replace`'s atomicity guarantees.
- Broadening the retry to other writers, other `os.replace`/`os.rename` call sites, or the temp-file write itself (`tmp.write_text`).
- Serializing readers/writers of `meta.json`, adding file locks, or changing how readers open `meta.json`.
- Making retry counts/backoff operator-configurable (a small fixed bound is sufficient for this transient).
- Refactoring `_save_meta`, its second call site at `indexer.py:3573`, or the meta I/O section generally.

## Acceptance Criteria

- [x] AC-1: On Windows, when `os.replace` in `_atomic_write_text` raises `PermissionError`/`OSError` with `winerror` in `{5, 32}`, the helper retries with a short backoff up to a fixed bound and completes the write when a retry succeeds; the regression test simulates a first-attempt `PermissionError(winerror=32)` and asserts the target file ends with the intended content. — test `test_retries_then_succeeds_on_sharing_violation`.
- [x] AC-2: When the sharing violation persists past the retry bound, the last `PermissionError`/`OSError` is re-raised (not swallowed); a test asserts the exception propagates when every simulated `os.replace` attempt raises. — test `test_persistent_sharing_violation_reraises_after_bound` (asserts `_META_REPLACE_MAX_ATTEMPTS` calls then re-raise).
- [x] AC-3: An `OSError`/`PermissionError` whose `winerror` is not in `{5, 32}` (or any error on POSIX) is re-raised immediately with no retry; verified by a test asserting `os.replace` is called exactly once for that case. — test `test_non_share_winerror_reraises_immediately` (winerror 13 → single call, no sleep).
- [x] AC-4: POSIX behavior is unchanged — `os.replace` is invoked exactly once on the success path; the existing `_atomic_write_text` / `_save_meta` regression coverage still passes. — test `test_posix_single_replace_call_on_success`; full `test_indexer` (193 tests) green.
- [x] AC-5: `python3 .wavefoundry/framework/scripts/run_tests.py` passes with the new test included, and no bytecode/`__pycache__` is left under `scripts/`. — full-suite run deferred to the coordinator central pass; the `__pycache__` left by in-lane runs was cleaned (verified none under `scripts/`), and `test_indexer` (incl. `AtomicWriteWindowsShareRetryTests`) runs green.

## Tasks

- [x] Read `indexer.py:1256-1265` and `setup_index.py:149-166` to confirm the current construct and mirror the established Windows-retry style.
- [x] Add a small Windows-only bounded-retry-with-short-backoff around `os.replace(tmp, path)` in `_atomic_write_text` (`indexer.py:1260-1264`): retry only on `PermissionError`/`OSError` with `winerror` in `{5, 32}`, short `time.sleep` backoff (`time` is already imported at `indexer.py:13`), fixed small attempt bound, re-raise the last exception when exhausted, and re-raise immediately for any other error. — inline loop; `_META_REPLACE_MAX_ATTEMPTS = 5`, `_META_REPLACE_BACKOFF_SECONDS = 0.1`.
- [x] Add a concise docstring/comment on the helper naming the failure mode (WinError 32 sharing violation / WinError 5 access denied on concurrent `meta.json` readers), the caller (`_save_meta`), and the POSIX-no-op nature, citing the mirrored `setup_index._rmtree_clearing_readonly` pattern (waves 1p9hk / 1p6d6) by mechanism (not a downstream-dangling ADR/wave-ID pointer inside shipped seed text — this is a `docs/` plan so wave-ID references are fine here).
- [x] Add regression tests to `tests/test_indexer.py`: (a) first-attempt `PermissionError(winerror=32)` then success → content lands; (b) persistent failure → exception re-raised; (c) non-{5,32} `winerror` → single call, immediate re-raise. — class `AtomicWriteWindowsShareRetryTests` (4 tests, incl. a POSIX single-call test).
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`; clean any `__pycache__` under `scripts/` if it appears. — full suite deferred to coordinator; `__pycache__` cleaned in-lane.
- [x] Mark ACs/tasks `[x]` in real time as each lands; update `Change Status` and `wave.md`. — change doc updated; `wave.md` is edited centrally by the coordinator (not touched in-lane per wave-landing rules).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| ws-1 implement Windows retry helper in `_atomic_write_text` | implementer | — | Windows-only guard, `winerror in {5,32}`, bounded retry + short backoff, re-raise on exhaustion/other errors; POSIX single-call path unchanged |
| ws-2 regression tests in `tests/test_indexer.py` | implementer | ws-1 | first-attempt-fail-then-succeed, persistent-fail-reraise, non-{5,32}-immediate-reraise; run `run_tests.py` |


## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py` — single edited source file; `_atomic_write_text` is the only construct touched. One implementer holds it for ws-1 before ws-2 references the final signature/behavior.
- `.wavefoundry/framework/scripts/tests/test_indexer.py` — new test cases only; coordinate if another wave concurrently edits this test module.

## Affected Architecture Docs

N/A — this is a localized robustness fix confined to one helper (`_atomic_write_text`) in a single module. No boundary, data/control-flow, layering, or verification-architecture change: the write contract (atomic replace of `meta.json`) is preserved; only its Windows transient-failure resilience improves.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | --------- | --------- |
| AC-1 | required | Core fix: retry-then-succeed on the WinError 5/32 race is the whole point of the finding. |
| AC-2 | required | Persistent-lock re-raise prevents silently masking a real failure (mirrors setup_index caller-checks discipline). |
| AC-3 | important | Guards against over-broad retry masking/delaying genuinely different errors. |
| AC-4 | required | POSIX must be provably unchanged (single `os.replace` call) — regression safety for the common platform. |
| AC-5 | required | Suite-green with no bytecode leakage is the framework-script hygiene gate. |

## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-02 | Scoped from Windows audit `wf_eab9a03d-004` + comparison `wf_33ca6bdb-757`; F17 (medium). Verified primary site `indexer.py:1260-1264` (`os.replace` at :1264), caller `_save_meta` `indexer.py:1199-1200` (build-time call at :3573), mirror pattern `setup_index.py:149-166`. | `indexer.py:1260-1264`, `indexer.py:1199-1200`, `indexer.py:3573`, `setup_index.py:149-166` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-02 | Gate retry on `os.name == "nt"` and `winerror in {5, 32}` only; POSIX single-call path untouched. | POSIX `os.replace` is atomic and never sharing-violates; scoping to Windows keeps the common path unchanged and avoids masking real POSIX errors. | Always-retry on any OSError (rejected: masks/delays genuine failures on all platforms). |
| 2026-07-02 | Re-raise the last exception after a fixed small retry bound instead of swallowing. | A persistent lock is a real failure the caller must see; mirrors `setup_index._rmtree_clearing_readonly` caller-checks discipline (waves 1p9hk / 1p6d6). | Swallow-and-return (rejected: leaves stale meta silently). |
| 2026-07-02 | Keep it a small local helper/inline guard in `indexer.py`; no new module or config. | Simplest-thing-that-works; single call site; no operator surface warranted for a transient. | New shared retry util / operator-tunable bounds (rejected: over-engineered for this finding). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Retry bound/backoff too short to clear a real reader open → still fails intermittently. | Bound covers the brief `meta.json` read window; on genuine persistence the last exception re-raises (unchanged failure surface, not a regression) and AC-2 asserts it. |
| Over-broad `except` masks a genuinely different error. | Retry only on `winerror in {5, 32}`; all other errors re-raise immediately (AC-3 test). |
| POSIX behavior accidentally altered. | Windows-only guard; AC-4 asserts a single `os.replace` call on the success path and existing coverage still passes. |
| Test simulates a Windows-only code path on POSIX CI. | Test injects a `PermissionError` with `.winerror` set and forces the Windows branch (monkeypatch `os.name`/the replace call) so the retry logic is exercised platform-independently. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
