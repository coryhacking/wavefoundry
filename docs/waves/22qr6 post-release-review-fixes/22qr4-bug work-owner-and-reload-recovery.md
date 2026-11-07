# Preserve work ownership and report reload and inspection state truthfully

Change ID: `22qr4-bug work-owner-and-reload-recovery`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-06
Wave: 22qr6 post-release-review-fixes

## Rationale

Three verified review findings:

1. **Work owner loss (executed with monkeypatching).** In `wave_work.py` `cleanup_work`, after `.owner.json` is unlinked, a `_Refused` from `_anchor` or `_entry` escapes the `except OSError` recovery. This happens both before `rmdir` and in the recovery after an `rmdir` failure, so the owner file is never restored. Every later describe, ensure, cleanup or reopen then returns `work_ownership_unproven`, and the work area can never be cleaned automatically.
2. **Reload monitors (inferred from reading `wf_server/server_impl.py` `prepare_reload`/`close` and `server.py`).** When `old.close()` reports incomplete cleanup, the retained handler keeps serving. Its staleness and context-efficiency monitors are already stopped, and nothing restarts them. The response does not say so. A later successful reload recovers.
3. **Inspection imports (executed).** The `scanner_upgrade.py --inspect-root` child leaves the installed scripts directory on `sys.path` after the staged path. A module missing from an incomplete incoming pack silently resolves from the installed copy and hides the gap. Only `bytecode_cache` currently resolves this way, which is harmless.

## Product Intent

Operators never lose the ability to clean a wave's work area because of a transient failure. After a partial reload failure they are told that background monitors stopped and how to recover. An incoming upgrade pack is judged only on its own modules.

## Requirements

1. Any refusal or OS error after `.owner.json` is unlinked in `cleanup_work` restores the owner record through the retained directory descriptor, without re-running path identity checks first, before the outcome is returned. The restored directory keeps its owner wherever it now is. A later cleanup succeeds when the directory is still at its expected path.
2. A reload response on the cleanup-incomplete path names the stopped background monitors and the recovery (retry `wf_reload_mcp` or restart). When a monitor stop times out, so that the thread may still run while scheduling is paused, monitor status reports a stopped or paused reason rather than an unqualified `alive: true`.
3. The inspect child resolves framework modules only from the staged tree, apart from its own bootstrap.

## Scope

**In scope:** `wave_work.cleanup_work` recovery, the reload cleanup-incomplete response text, `scanner_upgrade` inspect-child `sys.path`, and tests.

**Out of scope:** automatic monitor restart; other reload paths; work-area layout.

## Acceptance Criteria

- [x] AC-1: Three injected variants each leave `.owner.json` present afterwards: `rmdir` failing and then `_anchor` refusing; `_entry` refusing before `rmdir`; and `rmdir` failing and then `_anchor` raising `OSError`. Where the directory stayed at its expected path, a retry with the same generation removes the work. On the current code the first two leave no owner file.
- [x] AC-2: With telemetry close made to raise during `wf_reload_mcp`, the response names the stopped monitors and the recovery. With a monitor stop made to time out, `index_health` `background_monitors` reports a stopped or paused reason instead of unqualified `alive: true`. On the current code the response does not mention the monitors, and the stop-timeout status reads alive.
- [x] AC-3: A staged pack missing one module that the scanner imports yields an `incomplete` inspection, not `compatible`. On the current code it yields `compatible`.
- [x] AC-4: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Restore the owner on every post-unlink failure path.
- [x] Make the reload cleanup-incomplete response truthful about monitors.
- [x] Restrict the inspect child's framework import path to the staged tree.
- [x] Add regression tests with known-bad controls.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| robustness | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_work.py`, `.wavefoundry/framework/scripts/server.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/scanner_upgrade.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A unless the reload section of `docs/architecture/data-and-control-flow.md` describes the cleanup-incomplete response; if it does, update that sentence.

## Platform Behavior

The owner restore uses the existing directory descriptor (`dir_fd`) path. On hosts without `dir_fd` support (native Windows), `cleanup_work` already refuses with `safe_work_io_unsupported` before any unlink, so the defect cannot occur there and the change leaves that behavior unchanged. Reload and inspect changes are platform-neutral.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Permanent loss of cleanup ability. |
| AC-2 | important | Silent loss of background monitoring until a retry. |
| AC-3 | important | Hides incomplete upgrade packs. |
| AC-4 | required  | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-06 | Planned from verified review findings 7, 6 and 8. | Verifier probes f7/f8; reload reading |
| 2026-11-06 | AC-1: `cleanup_work` now catches `(OSError, _Refused)` around everything after the owner unlink, restores the owner through the retained fd first, and returns the original refusal as `preserved` (never `absent`). A failed restore adds `owner_restore: failed:<errno>`. | `test_wave_work`: `test_rmdir_failure_then_anchor_refusal_restores_owner`, `test_entry_refusal_before_rmdir_restores_owner`, `test_rmdir_failure_then_anchor_oserror_restores_owner`, `test_post_unlink_not_found_is_preserved_not_absent`, `test_failed_owner_restore_keeps_original_refusal_and_reports_restore`; 56 ok. Known-bad (HEAD `wave_work.py` in scratch): all 5 fail (4 FAIL, 1 ERROR). |
| 2026-11-06 | AC-2: the cleanup-incomplete reload response adds `data.reload.monitors_stopped` and a message naming both monitors and the recovery (retry `wf_reload_mcp` or restart). `background_monitor_status` adds `paused: true` and a `stopped_for_reload` reason while scheduling is paused (not for a disabled index monitor). No automatic restart. | `test_mcp_lifecycle`: `test_cleanup_incomplete_reload_names_stopped_monitors_and_recovery`, `test_monitor_stop_timeout_status_is_paused_not_unqualified_alive`, `test_running_monitor_status_is_not_marked_paused`; 14 ok. Known-bad (HEAD `server.py` and `server_impl.py`): the first two ERROR (`KeyError`), the negative control passes. |
| 2026-11-06 | AC-3: the inspect child replaces `sys.path` with the staged scripts first, then drops the installed scripts directory and any inherited `PYTHONPATH` entry outside stdlib/site. Other entries, including `.pth` additions, are kept. | `test_scanner_upgrade`: `test_pack_missing_a_scanner_module_is_incomplete_not_installed_fallback` (removes `lifecycle_id.py`; with and without `PYTHONPATH`), `test_staged_import_path_drops_installed_and_inherited_scripts`; 8 ok. Known-bad (HEAD `scanner_upgrade.py`, full framework scratch copy): both subtests yield `compatible`, and the helper test ERRORs. Mutant keeping `PYTHONPATH` entries: the `PYTHONPATH` subtest and the helper test FAIL. |
| 2026-11-06 | Platform: owner restore uses the existing `dir_fd` path; native Windows (no `dir_fd`) still refuses with `safe_work_io_unsupported` before any unlink, so it is unchanged. The reload text and monitor status are platform-neutral. Path filtering compares `normcase(realpath())`, so case-insensitive Windows and macOS spellings match; it splits `PYTHONPATH` on `os.pathsep`. Verified on macOS only. | Code review; Windows/Linux not executed |
| 2026-11-06 | AC-4: focused run of 14 related files (wave_work, wave_work_lifecycle, mcp_lifecycle, mcp_tool_registry, scanner_upgrade, upgrade_reload_runner, setup_readiness_integration, server_tools_retrieval, bytecode_cache, distribution_seams, handler_modules, upgrade_wavefoundry, archive_ownership_portability, startup_install): 2178 tests, 0 failures. The repository-changed guard tripped only on concurrent edits by other implementers and on this change's CHANGELOG edit. `wf_validate_docs` full: ok. Full suite not run (coordinator-owned). | `run_tests.py --file ...` ×14 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-06 | Truthful response rather than an automatic monitor restart. | This is the simplest option; a retry already recovers. Efficacy: the operator sees the actionable state. | Restart dead monitors on the retained handler; adds lifecycle surface. |
| 2026-11-06 | One try block covering all post-unlink work, with `(OSError, _Refused)`. | Covers both verified paths. | Patch only the reported line; misses the pre-`rmdir` path. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The owner restore itself fails | Return the original refusal and record the restore failure in the diagnostic; never claim cleanup. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
