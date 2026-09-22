# Upgrade Handler Module And Back-Reference Inversion

Change ID: `1ymzo-ref upgrade-handler-module-inversion`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-21
Wave: `1ymzq handler-module-split-three`

## Rationale

The upgrade family in `server_impl.py` is fourteen definitions: `wf_upgrade_response`, `_bounded_upgrade_response_envelope`, `wf_audit_install_response`, `_bounded_upgrade_summary`, `_parse_bridge_release_required`, `_upgrade_next_step`, `wf_upgrade_status_response`, `_load_upgrade_lib`, `_upgrade_summary_sentinel`, `_parse_upgrade_summary`, `_install_artifact_display`, `_install_audit_row_brief`, `_project_retired_model_cleanup_fields`, and `_cutover_restart_required`, whose only caller is `wf_upgrade_response` and which moves with it under the domain-ownership rule. Two names the sixteen-line census swept in stay: `_read_framework_pack_version`, whose only caller is the module-level `SERVER_IMPL_VERSION = _read_framework_pack_version()` executed at import (server identity, not upgrade), and `_setup_notice_key`, called only by `ImplHandler`. Tools: `wf_upgrade`, `wf_upgrade_status`, `wf_audit_install`. `_wrap_upgrade_publication_guard` is middleware applied from the `MIDDLEWARE` table and stays in the composition root. Twelve module-level objects move with re-export: the nine `UPGRADE_*` caps and key tuples (including `UPGRADE_SUMMARY_TERMINAL_KEYS`), `RETIRED_MODEL_CLEANUP_KEYS`, `_RETIRED_MODEL_CLEANUP_ITEM_RE` and `_CUTOVER_RESTART_INSTRUCTION`; `DOCS_LINT_VERDICT_GAP_PREFIX` stays in the root with the lint substrate and is read through `server_impl`. `UPGRADE_SUMMARY_TERMINAL_KEYS` is patched on `server_impl` at two test sites and read as a module global at two sites in `_bounded_upgrade_summary`, so both become call-time reads, the same named-exception rule as the other patched constants in this wave.

The runner and its extension module reach the server today in exactly three places: `upgrade_wavefoundry.py` calls `server_impl.wf_start_dashboard_response` for the post-upgrade restart and `server_impl._memory_backfill_batch_locked` for memory publication, and `upgrade_extensions.py` looks up `wf_stop_dashboard_response` on `server_impl` by `getattr` with a legacy-name fallback. Readiness corrected two things about that picture. First, the process mapping: the old runner executes every phase of `main` including the post-extraction ones (surface rendering, memory backfill, index update); only `phase_cleanup` runs in the fresh `--cleanup` process from the extracted tree, and the dashboard restart lives inside `phase_cleanup`, so it always sees the new tree. The memory seam is an old-runner reach that stays valid because `pre_extract` has already imported the old server into that process and the new server re-exports the name anyway. Second, the extension hook runs from inside the new archive before extraction against the installed scripts directory; an installed tree older than this wave has no `dashboard_handlers.py`, so a bare `import dashboard_handlers` there would raise, be caught, and abort every upgrade at `pre_extract` with "unable to stop dashboard before lock cutover". The fallback must be module-level, not name-level.

The honest purpose of the inversion is edge direction, not load: the dashboard functions still reach `_response`, `_mcp_subprocess_run` and the process helpers through a per-call `import server_impl`, so the first dashboard call loads the whole server exactly as today. What changes is that the runner's source no longer names `server_impl` for dashboard reaches, leaving the pinned memory seam as the one lexical reach. A dashboard control path with no server dependency (envelope and subprocess helpers in their own modules) is recorded as a follow-up, not claimed here. Per the standing rule that upgrade fixes cannot protect their own install, this inversion protects the next upgrade only.

## Requirements

1. The committed inventory classifies the fourteen definitions, the two stayers and twelve objects, every caller including the runner's three reaches and the source-text pin on the runner (`server_impl._memory_backfill_batch_locked(` in `test_upgrade_wavefoundry.py`), patch sites, and the measured-tool derivation (expected: not joined).
2. A new `.wavefoundry/framework/scripts/upgrade_handlers.py` receives the classified set. Closures stay byte-identical; `server_impl.py` rebinds through one module-top block; the module never imports `server_impl` at module top nor another handler module at any scope, reaches staying helpers (`_bounded_subprocess_output`, `_load_script`, `_mcp_subprocess_run`, `_preferred_python`, `_response`, `run_validate`) per call, joins the purge list, and is imported by public name.
3. Inversion. `upgrade_wavefoundry.py`'s restart site imports `dashboard_handlers` directly (it runs post-extraction in the cleanup process). `upgrade_extensions.py` resolves the stop response in order: `dashboard_handlers.wf_stop_dashboard_response` when the module is importable from the installed tree, else `server_impl.wf_stop_dashboard_response`, else `server_impl.wave_dashboard_stop_response`, catching `ImportError` on the module step. Test hazard: once step one is `import dashboard_handlers`, the real module is importable from the scripts directory in the test process and cached in `sys.modules`, so an installed-tree fixture lacking the file does not block the import; the module-absence test and the three existing legacy-name fallback tests must inject `sys.modules["dashboard_handlers"] = None` (which makes the import raise `ImportError`) alongside their fake `server_impl`, or they stop exercising the fallback. The memory seam stays on `server_impl` with the pin as its reason. The runner's remaining `server_impl` imports are listed with reasons.
4. Old-code window: the change doc states the phase-to-process mapping above so a reviewer can confirm the three reaches stay valid on both sides; the upgrade phase-transition playbook's seam test cluster in `test_upgrade_wavefoundry.py` runs before and after.
5. Patch transparency: the ten `sys.modules["server_impl"]` injections in `test_upgrade_wavefoundry.py` that stub the dashboard start and stop reaches (four start tests in the cleanup block, six stop tests in the cutover block) are repointed to inject `dashboard_handlers`; the three current `_load_upgrade_lib` patches in `test_server_tools.py` are repointed to `upgrade_handlers`; the fourth patch in `test_upgrade_wavefoundry.py` stays on its archived server fixture, whose old ABI is deliberately unchanged; the two `UPGRADE_SUMMARY_TERMINAL_KEYS` patches stay observed through the call-time read. `test_index_upgrade_guard.py` executes its own fixture and is unaffected. The reload-call source census in `test_server_tools.py` scans the new owner too, retaining the exact two-call assertion (runner and upgrade owner).
6. Tests: a `FAMILIES` entry with the three tools; full-classified-set AST assertion; identity assertions; reload-proof entry; `test_upgrade_wavefoundry.py`, `test_storage_upgrade_resume.py`, `test_server_tools.py`, `test_install_log_lib.py` and `test_index_upgrade_guard.py` pass with only the listed edits; the source-text pin passes unmodified; `_parse_bridge_release_required`, which no test names, is covered by the identity assertion and the envelope tests that reach it.
7. Receipts: covered by the wave's receipt sequence; the mid-wave after-receipt follows this change.

## Scope

**Problem statement:** the upgrade runner names the server for two dashboard reaches, and the extension hook's fallback would abort upgrades from older installs if the module were assumed present.

**In scope:** inventory, module, rebinding block, purge entry, the module-absence fallback chain and its test, the two inversions, the listed repoints, tests, CHANGELOG bullet, architecture doc lines.

**Out of scope:** any change to upgrade phases, summaries, caps, cutover detection or the publication guard; repointing the memory backfill seam; a server-free dashboard control path (follow-up).

## Acceptance Criteria

- [x] AC-1: Every classified definition and object lives in `upgrade_handlers.py` and not in `server_impl.py`; the full-set AST tests prove it.
- [x] AC-2: The three tools are byte-identical to the golden fixture; every re-exported name passes its identity assertion.
- [x] AC-3: Purge entry and module-top import present; reload tests and the parameterized proof pass; the manifest lists the module.
- [x] AC-4: The runner imports `dashboard_handlers` for the restart; the extensions resolve the stop response through the three-step chain, the module-absence test passes, and the legacy-name fallback tests block the module step explicitly; the memory seam stays and its pin passes; the seam cluster passes; every remaining `server_impl` reach in the runner is listed.
- [x] AC-5: The sixteen listed patch sites are repointed or covered by the call-time read, and the named test modules pass with no other edit.
- [x] AC-6: The change's own suites and every test it adds pass, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Commit the inventory including the runner's reach list, the phase-to-process mapping and the pin.
- [x] Create the module, move the classified set, add the rebinding block, the call-time read and the purge entry.
- [x] Implement the fallback chain and its module-absence test; repoint the restart import and the sixteen listed sites; run the seam cluster.
- [x] Add the `FAMILIES` entry, full-set assertion, identity assertions and reload-proof entry.
- [x] Architecture doc line, CHANGELOG bullet, framework suite; required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| upgrade-inventory | implementer | wrapper-move (sibling change) | Needs `dashboard_handlers` to exist. |
| upgrade-move | implementer | upgrade-inventory | One owner for the module, the runner and the extensions. |
| independent-review | required reviewers | upgrade-move | Fresh contexts; the seam cluster and the absence test are the evidence. |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/tests/test_handler_modules.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/architecture/current-state.md`
- `docs/architecture/domain-map.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/domain-map.md` gain the module; the Handler modules paragraph in `current-state.md` gains one sentence: the runner and extensions reach the dashboard responses through `dashboard_handlers` with a module-absence fallback, and the runner's one remaining `server_impl` reach is the pinned memory seam.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The move is the change. |
| AC-2 | required | Public surface must survive. |
| AC-3 | required | A missed purge entry serves stale code after reload. |
| AC-4 | required | The fallback chain is what keeps upgrades from older installs working. |
| AC-5 | required | Sixteen test sites would go inert otherwise. |
| AC-6 | required | Change-local correctness. |

## Progress Log

Final delivery checkpoint (2026-09-22): all required lanes and Council approved unchanged reviewed source; R2 baseline independently verified including index AC-5. Full 9,508-test receipt current. Evidence: `evidence/qa-final.md`, `evidence/council-final.md`, `retrieval-evidence.md`. Earlier pending checkpoints are historical and resolved.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Observe: canonical isolated affected-file verification green: 3,153 tests across 14 files, two skips. All change-local and newly added checks pass, including golden/registry, scratch reload, dashboard native processes, lifecycle, docs lint and upgrade/recovery. Full-suite receipt and delivery review remain wave-level work. | run_tests.py --file (14 admitted affected modules); /private/tmp/1ymzq-pre-r1-canonical.log; extraction-equivalence.json. |
| 2026-09-21 | Observe: 967-test combined run exposed an over-repointed archived-server patch and a reload source census still looking only in the root; both mechanical fixture corrections made. Three targeted replays pass. Index-guard mutant control failed only in combined order and passes isolated; shared-state investigation remains with coordinator, so no green combined receipt claimed. One pre-existing skip. All 14 normalized definition ASTs and 12 exact object ASTs match; module-absence test kills fallback-removal mutant. | upgrade-inventory.md; test_archived_servers_execute_validation_transition_envelope, test_reload_helper_has_exactly_two_production_call_sites, test_legacy_wrapper_control_detects_missing_reader_or_final_normalization. |
| 2026-09-21 | Implement: fourteen definitions and twelve objects extracted after wrapper verification; restart imports dashboard owner, archive hook falls back on module absence. Memory seam untouched. Mechanical AST gapfill after MCP navigation captured the inventory. | upgrade-inventory.md; focused verification pending. |
| 2026-09-21 | Planned after a census: 15 definitions, 1,461 lines, three tools, three runner reaches of which one is source-text pinned. | AST census; runner and extensions reads. |
| 2026-09-21 | Focused verification: `_read_framework_pack_version` (import-time server identity) and `_setup_notice_key` (`ImplHandler`) stay; `UPGRADE_SUMMARY_TERMINAL_KEYS` is a twelfth moving object with two call-time reads; the fallback tests must block the module import explicitly because the real module is on the test path. | Readiness review in this wave directory. |
| 2026-09-21 | Readiness round: the name-level fallback would have aborted every upgrade from a pre-wave install at `pre_extract`; the phase-to-process mapping was wrong (the old runner runs everything but cleanup); the purpose sentence overstated load reduction; `_cutover_restart_required` and `_CUTOVER_RESTART_INSTRUCTION` move with the family; an eleventh object; sixteen patch sites listed; `test_upgrade_extensions.py` does not exist and the extension tests live in `test_upgrade_wavefoundry.py`. | Readiness review in this wave directory. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Module-absence fallback chain in the extensions. | The hook runs from the new archive against the installed tree before extraction. | Name-level fallback only (first draft); aborts upgrades from older installs. |
| 2026-09-21 | Invert the two dashboard reaches; keep the memory seam. | The seam is pinned by a source-text test and by the playbook. | Full inversion; fails the pin. |
| 2026-09-21 | Claim edge direction, not load reduction. | The dashboard functions still load the server per call; a server-free control path is a separate extraction. | Claim the old-code-window benefit; false. |
| 2026-09-21 | Fourth in the wave. | Needs `dashboard_handlers` from `1ymzn`. | Earlier; no inversion possible. |

## Risks

| Risk | Mitigation |
| --- | --- |
| The installing upgrade runs the old runner against the new tree. | The mapping in Requirement 4; the rebinding keeps every name resolvable on both sides. |
| A future extension edit drops the module-absence step. | The absence test with a scripts fixture lacking the module pins it. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

Integration repair: the record-layout census detected its full-corpus-lint comment moved to upgrade_handlers.py. Repointed only the allowlist filename; stale-entry and unlisted-site checks remain active.

Computational verification: full framework suite passed 9,508 tests across 121 files (12 skips). Required independent delivery review is still pending.
