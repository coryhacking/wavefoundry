# Native-Windows guards in the Python execution layer (forward-compat; POSIX/WSL2 unchanged)

Change ID: `1p6d6-bug native-windows-python-exec-guards`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-18
Wave: `1p6d5 windows-python-exec-hardening-and-wsl2-support`

## Rationale

A Windows-compatibility audit (find → adversarial-verify) of the framework's **Python execution layer** found a cluster of POSIX-isms that misbehave on **native Windows** (standard Terminal/PowerShell/cmd, NOT WSL2 — WSL2 is Linux and runs the working POSIX path). The repo already carries substantial *correct* Windows scaffolding (`taskkill`, the guarded `tasklist` liveness copies in `indexer.py`/`upgrade_lib.py`, `msvcrt`/`fcntl` locking, 3-of-4 background-spawn `creationflags`, the `setup_index.py:341` `os.execv`-loses-exit-code oracle); the items below are the gaps and a few "guarded-but-wrong" spots that escaped it.

This change lands those guards **now, as forward-compat**: native Windows cannot yet start the MCP server at all (that is the launcher/Area-1 work, deliberately out of scope here), so these fixes are not end-to-end-observable on Windows today. They are included because (a) they are **pure-additive `os.name` branches or cross-platform-safe fixes** with **zero behavior change on POSIX/WSL2**, (b) they are **unit-testable by mocking `os.name`** without a Windows box, and (c) they pre-stage native-Windows support so Area 1 + a Windows smoke pass later find a clean execution layer. The non-negotiable gate is **no POSIX/WSL2 regression**.

## Requirements

1. **`build_pack` venv re-exec** (`build_pack.py:804,808`): `_reexec_with_venv_if_needed` hardcodes `~/.wavefoundry/venv/bin/python` (Windows is `Scripts\python.exe` → `.exists()` is always False → re-exec silently no-ops → build runs under system Python without numpy/lancedb) AND uses `os.execv` (on Windows = spawn-and-exit, loses the child exit code). Branch the venv path on `os.name` (mirror `setup_index._tool_venv_python`), and on `nt` use `subprocess.run([...], check=False)` + `sys.exit(rc)` (mirror the `setup_index.py:341-345` oracle); reserve `os.execv` for POSIX.
2. **Process liveness** (`server_impl.py:4556` `_pid_is_running` + `:2748` inline `os.kill(pid,0)`): the only **unguarded** liveness checks in the codebase (no `nt` `tasklist` branch, unlike the correct copies in `indexer.py:192`/`upgrade_lib.py:121`). Called from 12+ sites incl. the dashboard `1p654` reconciliation, so on Windows they misjudge live/dead PIDs and defeat orphan reconciliation. Hoist ONE shared guarded helper (`tasklist /FI "PID eq {pid}" /NH /FO CSV` on `nt`, `os.kill(pid,0)` on POSIX) and route both sites through it; POSIX behavior identical.
3. **Background reindex spawn** (`server_impl.py:4669`): uses `start_new_session=True` (POSIX detach) + `close_fds=os.name!='nt'` but is missing the `creationflags=DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` `nt` branch the three sibling spawns have (`setup_index.py:772`, `server_impl.py:3486`, `:6640`). Add the `nt` branch (mechanical, mirrors siblings).
4. **Map link href** (`gen_codebase_map.py:1318` `_area_context_link_href`): `os.path.relpath` is `ntpath.relpath` on Windows → emits `..\..\libs\ui\AGENTS.md` **backslash** hrefs (the `.as_posix()` inputs don't help; the output separator is platform-fixed) → broken codebase-map markdown links + docs-lint failure on a Windows-generated map. (This is `1p66d` code.) Force forward slashes (`.replace("\\","/")` or compute via `PurePosixPath`). Cross-platform-safe and cross-platform-testable.
5. **Explicit text encoding**: text I/O without `encoding=` defaults to cp1252 on Windows (corruption / `UnicodeDecodeError`). Add `encoding="utf-8"` at the confirmed sites — `server_impl.py:4900` (`wave_md.write_text`), `:15536` (the `code_ask` line-count `Path.open()`), `build_scan_allowlist.py:70` — and sweep the remaining `Path.open()` text reads the inline grep's `.open(` exclusion missed. Harmless on POSIX (UTF-8 default).
6. **Filesystem edge guards** (verification needs a Windows box, but the fix is code-decidable): `upgrade_wavefoundry.py:1195` `shutil.rmtree` of the stale framework index → add an `onexc`/`onerror` handler that clears the read-only attribute (`os.chmod(p, stat.S_IWRITE)`) and retries (Windows refuses to delete read-only/mapped files), keeping the `OSError` fallback; `setup_index.py:546-561` HF-cache corruption checks gated on `path.is_symlink()` → also validate plain (non-symlink) files for missing/zero-byte content, since HF copies (not symlinks) on a stock Windows cache.
7. **No POSIX/WSL2 regression (the gate)** and **generic**: every `nt` branch is additive; every cross-platform fix (4,5) is verified byte-identical on POSIX. Unit tests mock `os.name=='nt'` to assert the Windows branch builds the right command/path, and assert POSIX behavior is unchanged. Affected docs (`docs/architecture/graph-index-system.md` if the map-href note belongs there) updated minimally.

## Scope

**Problem statement:** The Python execution layer has native-Windows POSIX-isms (venv path, `os.execv`, unguarded liveness, missing spawn `creationflags`, `ntpath` backslash hrefs, missing `encoding=`, read-only rmtree, symlink-only cache checks) that will misbehave once native Windows can run the framework.

**In scope:** the seven items above, in `build_pack.py`, `server_impl.py`, `gen_codebase_map.py`, `build_scan_allowlist.py`, `upgrade_wavefoundry.py`, `setup_index.py`; a shared guarded liveness helper; `os.name`-mocked unit tests + POSIX no-regression assertions.

**Out of scope:**

- The **launcher surface (Area 1)** — `.mcp.json`/`settings.json`/`bin/*`/git-hooks/the renderer emitters and the distribution-model ADR. Native Windows can't start the server without it; tracked separately.
- `indexer.py:1096` `os.replace` sharing-violation — the audit's explicit "leave as-is" (low-likelihood; add a retry only if it surfaces in field testing).
- DirectML auto-detect and the secrets-scanner `_physical_perf_core_count` darwin gate — the latter is a benign perf helper (secrets scanning runs on Linux/WSL2; verified), NOT a bug.
- End-to-end **native-Windows verification** — deferred to the future Windows-smoke wave (needs Area 1 + a real Windows host).

## Acceptance Criteria

- [x] AC-1: `build_pack` re-exec selects `Scripts\python.exe` on `nt` and uses `subprocess.run(...)+sys.exit(rc)` (never `os.execv`) on `nt`; POSIX keeps `bin/python` + `os.execv` unchanged. Also honors `WAVEFOUNDRY_TOOL_VENV`. POSIX no-regression unit-tested (`BuildPackVenvReexecTests.test_posix_uses_bin_python_and_execv`). **nt-branch unit test intentionally omitted:** patching `os.name='nt'` makes pathlib instantiate `WindowsPath`, which raises `UnsupportedOperation` on a POSIX runner the instant the function builds the venv `Path` — the same reason the mirrored `setup_index.py:341` oracle isn't nt-unit-tested. nt branch verified by code review + that shared oracle; execution Windows-deferred.
- [x] AC-2: a single shared guarded liveness helper (`tasklist` on `nt`, `os.kill(pid,0)` on POSIX) is now `server_impl._pid_is_running`; the inline `:2748` check routes through it; the other 12+ callers already called `_pid_is_running` so they inherit the guard unchanged; POSIX behavior byte-identical. Tested: `WindowsLivenessGuardTests` (4 — pid≤0, POSIX os.kill present/absent, nt tasklist present/absent/OSError, `_background_build_status` routing).
- [x] AC-3: the reindex `Popen` now selects `creationflags=DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` on `nt` / `start_new_session=True` on POSIX (mirrors the three sibling spawns); POSIX unchanged. **No dedicated unit test:** no spawn site in the codebase asserts detach kwargs (the two shipped siblings are untested too — the thin OS branch hits the same `WindowsPath` issue); mirror-of-siblings + code review, execution Windows-deferred.
- [x] AC-4: `_area_context_link_href` now uses `posixpath.relpath` → forward-slash hrefs on every OS. Cross-platform test `AreaContextHrefPortabilityTests` asserts the href contains `/`, never `\`, and equals `../../libs/ui/AGENTS.md`.
- [x] AC-5: added `encoding="utf-8", errors="replace"` at the one genuine gap — `server_impl.py` `code_ask` line-count `Path.open()`. **Audit correction:** the other two flagged sites (`wave_md.write_text` and `build_scan_allowlist.py`) already pass `encoding="utf-8"` (false positives from the grep window) — no change needed. POSIX-unchanged (UTF-8 default). Covered by the full suite.
- [x] AC-6: `upgrade` rmtree now installs an `onexc`/`onerror` (version-gated) handler that clears read-only (`os.chmod(p, stat.S_IWRITE)`) and retries, keeping the `OSError` fallback log; the HF snapshot check now validates plain (non-symlink) `.onnx` artifacts for zero-byte content. HF check cross-platform-tested (`test_model_cache_corruption_reason_detects_zero_byte_plain_onnx` + non-empty control); rmtree read-only path is Windows-only behavior (POSIX dir-write governs deletion) so observation is Windows-deferred, fix code-decidable.
- [x] AC-7: **No POSIX/WSL2 regression** — full framework suite green on macOS (`3323` tests, +8 new); the `nt` branches are exercised by `os.name` mocks where pathlib permits (liveness) and by code-review + mirrored oracles where it doesn't (build_pack/reindex nt); end-to-end native-Windows verification explicitly deferred to the Windows-smoke wave (documented, not silently skipped).

## Tasks

- [x] `build_pack._reexec_with_venv_if_needed`: `os.name` venv-path branch (+ `WAVEFOUNDRY_TOOL_VENV`) + `nt` `subprocess.run`+`sys.exit` (mirror `setup_index.py:341`).
- [x] Hoist a shared guarded `_pid_is_running` (tasklist/`os.kill`); replace the `server_impl` body + route the inline `:2748` site through it.
- [x] Add the `nt` `creationflags` branch to the reindex spawn.
- [x] `gen_codebase_map._area_context_link_href`: force forward-slash output (`posixpath.relpath`).
- [x] Add `encoding="utf-8"` at the one real gap (`code_ask` line-count `Path.open()`); confirmed the other two flagged sites already had `encoding=`.
- [x] `upgrade` rmtree read-only retry; `setup_index` HF non-symlink (plain-file) corruption check.
- [x] Tests: liveness (POSIX+nt) + href + build_pack POSIX + HF zero-byte; full suite green (3323). nt-branch tests blocked by `WindowsPath` are documented + covered by code-review/oracle.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — only if the map-href portability note belongs there; otherwise `N/A` (single-module guards with no boundary/flow change).

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | `build_pack` is doubly broken on Windows (silent no-op + lost exit code). |
| AC-2 | required | Unguarded liveness is a real Windows correctness regression (dashboard reconciliation). |
| AC-3 | important | Spawn detachment parity with the three sibling spawns. |
| AC-4 | required | Backslash hrefs break the codebase map + docs-lint on a Windows-generated map (our `1p66d` code). |
| AC-5 | important | cp1252 corruption / decode errors on Windows. |
| AC-6 | important | rmtree / HF-cache edge guards (Windows observation deferred). |
| AC-7 | required | No POSIX/WSL2 regression — the load-bearing gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-18 | Planned from the Windows-compat audit (Area 2 = python-exec). All items native-Windows-only (WSL2=Linux unaffected); landed as forward-compat guards, POSIX-unchanged, `os.name`-mock-tested. | audit inventory; `build_pack.py:804/808`, `server_impl.py:4556/2748/4669`, `gen_codebase_map.py:1318`, `build_scan_allowlist.py:70`, `upgrade_wavefoundry.py:1195`, `setup_index.py:546` |
| 2026-06-18 | Implemented all 7 items. Re-located each construct (lines had drifted). **Two audit corrections:** (a) only ONE real `encoding=` gap (the `code_ask` line-count `Path.open()`) — `wave_md.write_text` + `build_scan_allowlist.py` already had `encoding=`; (b) `subprocess` is locally-imported per-function in `server_impl` (convention) so the `nt` liveness branch needs a local `import subprocess` (added — would have `NameError`d on Windows otherwise). `_pid_is_running` POSIX branch kept byte-identical (did NOT adopt the oracle's `PermissionError→True` — out of scope). nt unit tests for build_pack/reindex omitted (pathlib `WindowsPath` blocks `os.name='nt'` patching when a `Path` is built) — documented, mirror-of-oracle. | +8 tests; full suite **3323 green**; `gen_codebase_map` now imports `posixpath`; `upgrade_wavefoundry` now imports `stat` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-18 | Land Area-2 guards now as forward-compat, before the launcher (Area 1). | Operator directive ("harden area 2 now"); pure-additive `nt` branches + cross-platform-safe fixes, zero POSIX risk, unit-testable without a Windows box. | Wait for Area 1 + a Windows box (rejected — these are safe, cheap, and pre-stage the execution layer cleanly). |
| 2026-06-18 | Reuse the `setup_index.py:341` `os.execv`-loses-exit-code oracle and the `indexer.py:192` tasklist helper rather than inventing new patterns. | Proven, already-trusted Windows branches; consistency. | Bespoke per-site handling (rejected — drift risk). |
| 2026-06-18 | Exclude `os.replace` (`indexer.py:1096`) and the secrets darwin perf-helper. | Audit verdict: `os.replace` leave-as-is (low-likelihood); the darwin gate is a benign perf helper, not a bug (secrets scan runs on Linux/WSL2 — verified). | Fix them anyway (rejected — no demonstrated problem; scope discipline). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A guard accidentally changes POSIX/WSL2 behavior. | AC-7 no-regression gate; every `nt` change is additive; cross-platform fixes (4,5) verified byte-identical on POSIX; full suite on macOS/Linux. |
| `nt` branches are unverifiable here → could be subtly wrong. | Unit-test the branch logic via `os.name` mocks (command/path built correctly); honestly defer end-to-end to the Windows-smoke wave; reuse proven oracles. |
| Shared-liveness-helper refactor regresses one of the 12+ callers. | Keep the POSIX path byte-identical; test each caller class (background-refresh, stale-lock, index-build-status, dashboard reconciliation). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
