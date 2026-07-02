# Windows venv rmtree hardening: setup_index venv recreation silently no-ops on Windows

Change ID: `1p9hk-bug windows-venv-rmtree-hardening`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-07-02
Wave: 1p9hn windows-portability-round-2

## Rationale

`setup_index._bootstrap_venv` (`:159` and `:164`) calls `shutil.rmtree(venv_dir, ignore_errors=True)` with no read-only-clearing handler before recreating the tool venv. On Windows, `rmtree` routinely fails on read-only or in-use files — pip-installed `.pyd`/`.dll` native extensions (onnxruntime, lancedb, fastembed) and mmap'd model artifacts are frequently read-only or held open by the MCP host process. `ignore_errors=True` swallows the `PermissionError`, leaving a partial directory. Because venv recreation is gated on `if not venv_dir.exists()` (`:166`), the gate is skipped and `_bootstrap_venv` returns a mismatched/half-gutted `venv_python`.

This is exactly the path operators are told to use when `wf setup` fails: "close the MCP host and rerun `wf setup`". On Windows the rmtree silently no-ops if any file is still held, so the recovery dead-ends with no actionable error.

Wave 1p6d6 added a `_clear_readonly_and_retry` handler (`os.chmod(S_IWRITE)` + retry, wired via `onexc` on Python ≥ 3.12 else `onerror`) to the sibling `upgrade_wavefoundry._remove_deprecated_framework_index` rmtree. That hardening was never applied to the `setup_index` sites.

## Requirements

1. Both `shutil.rmtree` calls in `setup_index._bootstrap_venv` (`:159` and `:164`) must use the read-only-clearing error handler, either by reusing the pattern from `upgrade_wavefoundry._remove_deprecated_framework_index` or inlining it.
2. After the rmtree, if `venv_dir.exists()` is still `True`, the function must log a clear actionable message directing the operator to close any process holding the venv (MCP host, IDE extension, terminal) and rerun `wf setup`, then raise or return a sentinel causing setup to exit non-zero rather than continuing silently with a broken venv.
3. The read-only-clearing handler must be compatible with Python 3.11 (use `onerror`) and 3.12+ (use `onexc`), matching the existing sibling implementation.

## Scope

**Problem statement:** On Windows, `wf setup` venv recreation silently no-ops when read-only or in-use native extension files prevent `rmtree` from completing, leaving the operator with a broken venv and no guidance.

**In scope:**

- `setup_index._bootstrap_venv` rmtree hardening at `:159` and `:164`
- Post-rmtree existence check with actionable error surfacing
- Shared or inlined `_clear_readonly_and_retry` handler

**Out of scope:**

- Other rmtree call sites in the codebase (reviewed separately)
- Venv recreation logic beyond the rmtree step

## Acceptance Criteria

- [x] AC-1: `setup_index._bootstrap_venv` uses a read-only-clearing error handler on both rmtree calls — new `_rmtree_clearing_readonly` helper used at both sites; `test_rmtree_clearing_readonly_removes_readonly_tree`
- [x] AC-2: If `venv_dir` still exists after rmtree, the function surfaces an actionable error message naming the likely cause (open MCP host / IDE extension) and instructs the operator to close them and rerun `wf setup` — `test_bootstrap_venv_surfaces_error_when_removal_fails`
- [x] AC-3: Setup exits non-zero (or raises) rather than continuing with a broken venv — raises `RuntimeError`; test asserts `subprocess.run` (venv create) is never reached
- [x] AC-4: The handler is compatible with Python 3.11 (`onerror`) and 3.12+ (`onexc`) — `_rm_kw` selects by `sys.version_info`, mirroring the 1p6d6 sibling
- [x] AC-5: On POSIX the behavior is unchanged (rmtree succeeds; read-only handler is a no-op for POSIX-style permissions) — pre-existing create/skip/recreate/mismatch tests still green

## Tasks

- [x] Add read-only-clearing rmtree handler to both calls at `setup_index.py:159`/`:164` — extracted a `_rmtree_clearing_readonly` module helper (reuses the 1p6d6 pattern) rather than `ignore_errors=True`
- [x] Add post-rmtree existence check (`removal_attempted and venv_dir.exists()`) with actionable error message and raise at `setup_index._bootstrap_venv`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| add-handler | implementer | — | Add read-only-clearing rmtree handler |
| add-existence-check | implementer | add-handler | Post-rmtree check + error surfacing |

## Serialization Points

- Both workstreams touch the same function; sequential steps within `_bootstrap_venv`.

## Affected Architecture Docs

N/A — confined to `setup_index.py`. No boundary or flow change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevents silent rmtree failure |
| AC-2 | required | Makes the recovery path actionable on Windows |
| AC-3 | required | Prevents setup from continuing with a broken venv |
| AC-4 | required | Python 3.11 is the minimum supported version |
| AC-5 | required | Non-regression on POSIX |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-02 | Change doc created from 10-dimension Windows audit | audit workflow wf_51bd40fe-082 |
| 2026-07-02 | Implemented: `_rmtree_clearing_readonly` helper at both rmtree sites + `removal_attempted`/exists() post-check raising an actionable error | `VenvBootstrapTests` 6/6 green (3 pre-existing + 2 new + updated partial-venv test) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-02 | Reuse the existing `_clear_readonly_and_retry` pattern from upgrade_wavefoundry rather than hoisting into subprocess_util | Minimizes scope; the pattern is already proven | Hoist into subprocess_util as shared fs helper (larger refactor, higher risk) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Files held by antivirus / Windows Defender cannot be unlocked by chmod | Error message explicitly calls out this case and directs to a retry |
| Shared handler extraction causes cross-module import cycle | Inline the pattern; a future refactor can hoist it |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
