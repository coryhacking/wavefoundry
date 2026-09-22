# Thin-Wrapper Handler Modules

Change ID: `1ymzn-ref thin-wrapper-handler-modules`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-21
Wave: `1ymzq handler-module-split-three`

## Rationale

A band of response wrappers in `server_impl.py` delegates to sibling libraries: docs validation and gardening, surface sync, secrets scanning, dashboard process control, and the edit-governance gates and session handoff. The first draft swept forty-eight definitions into three modules; readiness found that four of those members cannot move under the recipe and that two others belong to different owners, so the partition is narrower and cleaner.

What moves, in three modules. `docs_handlers` (validation and hygiene): `wf_validate_docs_response` (which carries the family's only `advisory=True` diagnostic), `wf_garden_docs_response`, `run_garden`, `wf_sync_surfaces_response`, `run_sync_surfaces`, `wf_scan_secrets_response`, `_subprocess_timeout_summary` (called only by `run_garden` and `run_sync_surfaces`); tools `wf_validate_docs`, `wf_garden_docs`, `wf_sync_surfaces`, `wf_scan_secrets`. `dashboard_handlers` (eleven definitions: the four dashboard responses and seven process helpers; the thirteen-name dashboard census also holds `_register_dashboard_child_pid` and `_reap_dashboard_child_pids`, which go with the index family, see below); tools `wf_start_dashboard`, `wf_stop_dashboard`, `wf_restart_dashboard`, `wf_open_dashboard`. `edit_gate_handlers` (gates and handoff, one coherent pair of session-governance state that close and pause both write): `wave_open_gate_response`, `wf_close_wave_gate_response`, `wf_gate_status_response`, `_force_gates_closed`, `wf_get_handoff_response`, `wf_set_handoff_response`, `_update_handoff_wave_ref`, `_read_guard_overrides`, `_write_guard_overrides` (used only by this family); tools `wf_open_gate`, `wf_close_gate`, `wf_gate_status`, `wf_get_handoff`, `wf_set_handoff`. Thirteen tools in all.

What stays in the composition root, with the reason. `_regenerate_codebase_map_safe`: its callers are `wf_prepare_wave_response` and `wf_close_wave_response`, both lifecycle stayers, so it is lifecycle-owned. `wf_audit_response` and its six `_audit_*` helpers: it is decorated at definition time with `@_fail_closed_on_record_layout("wf_audit")`, a factory defined in the monolith that closes over two response helpers, so a handler module could apply it only through a module-top import from `server_impl`, which the recipe forbids and no prior family has hit; it is also the wrapper with the most cross-family reaches (index, memory, a lifecycle table, a search constant). `_check_secrets_gate` and `_confirmed_secret_notice`: close-gate compositions called by `wf_close_wave_response`, the class `1ymzk` deliberately kept in the root. `_attach_lint_to_response` and `_run_post_write_lint`: lint substrate called by five lifecycle responses, and the shared hermeticity fixture in `tests/server_tools_support.py` (fed by six test modules) plus five test modules directly patch `_run_post_write_lint` on the server; moving its only caller would make every one of those stubs inert and run real subprocess lint inside lifecycle tests. `run_validate`, `run_validate_changed` and their helpers: the lint substrate itself. `wf_help`, `_help_catalog` and its cache helpers, `wf_server_info_response`, `wf_gpu_doctor_response`: introspection of the composed server; moving sixteen-line delegators buys nothing. `_WAVE_CURRENT_NEXT_ACTION`: read by `wf_current_wave_response` (a stayer) and `wf_audit_response` (a stayer).

Module-level objects: the five `DOCS_LINT_*` constants stay in the root; every reader is lint substrate (`run_validate`, `run_validate_changed`, the timeout helpers, `_docs_lint_verdict_gap_error`, `_cap_cause_line`, whose default argument binds one at definition time) or the `1ymzo` mover `wf_audit_install_response`, and no `docs_handlers` member reads any of them, so they are read through `server_impl` per call. `DASHBOARD_START_WAIT_SECONDS` moves with dashboard; `_VALID_GATES` and `_EDIT_GOVERNANCE_GATE_MAP` (read by `codenav_handlers` as `server_impl._EDIT_GOVERNANCE_GATE_MAP`) move with the gates and are re-exported. The child-PID trio, `_DASHBOARD_CHILD_PIDS`, `_register_dashboard_child_pid` and `_reap_dashboard_child_pids`, is written by both families (`wf_start_dashboard_response` registers and mutates the set directly; `_start_background_index_refresh` reaps) and by `test_dashboard_server.py` through `server_impl`; it goes with the index family in `1ymzm` because `_reap_dashboard_child_pids` is on the measured evaluator closure, and the dashboard responses reach all three as `server_impl.<name>` per call so the one set object is shared. `DASHBOARD_START_WAIT_SECONDS` is patched to zero on `server_impl` at seven test sites and read as a module global by `wf_start_dashboard_response` at two sites, one of them the default argument of its nested `wait_for_running`, so both become `server_impl.DASHBOARD_START_WAIT_SECONDS` reads at call time, a named exception to byte-identity that the AST test lists; the same rule this wave applies to `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` and `UPGRADE_SUMMARY_TERMINAL_KEYS`.

Cross-family reaches, all through `server_impl` at call time and none a module-top handler import: `wf_garden_docs_response` and `wf_set_handoff_response` to `_trigger_background_index_refresh_for_paths` (index, `1ymzm`); `wf_set_handoff_response` and `wf_sync_surfaces_response` to `_attach_lint_to_response` (stays); the dashboard responses to the child-PID trio (index); `codenav_handlers` to `_read_guard_overrides` and `_EDIT_GOVERNANCE_GATE_MAP` (kept valid by the rebinding). Because `_reap_dashboard_child_pids` is on the measured evaluator closure through `_fts_schedule_heal` and the background refresh, the trio is classified with the index family in `1ymzm` (which joins the production retrieval list regardless) so that no wrapper module joins. Two siblings reach the dashboard responses through `server_impl` today (`upgrade_wavefoundry` for start, `upgrade_extensions` for stop by `getattr` with a legacy-name fallback); both keep working through the rebinding and are inverted in `1ymzo`.

## Requirements

1. The committed inventory classifies every definition and object into the three modules or the root with the reasons above, records callers, patch sites and source-text anchors, and records the measured-tool derivation: no wrapper module joins `PRODUCTION_RETRIEVAL_MODULES` once `_reap_dashboard_child_pids` is placed with index.
2. Three new modules receive their families. Closures stay byte-identical; `server_impl.py` rebinds each through its own module-top block; no module imports `server_impl` at module top (function-level `import server_impl` per call is the recipe) and no module imports another handler module at any scope (the boundary test checks module-top imports only, so the inventory grep covers function-local ones); each joins the purge list and is imported by public name.
3. Patch transparency: the dashboard family has about fifty-five moved-to-moved patch sites in `tests/test_dashboard_server.py` (the block from the first `wf_start_dashboard_response` test through the restart tests, and two late sites) and `tests/test_server_tools.py` (the dashboard control block and two late sites), patching `_dashboard_cmdline_pids`, `_dashboard_url_reachable`, `_terminate_dashboard_pid`, `_dashboard_already_serving`, `_reap_dashboard_child_pids`, and the start and stop responses around `wf_restart_dashboard_response`; an inert patch would spawn real processes or wait the real start window. Every site is repointed to `dashboard_handlers.<name>` and listed in the inventory. The docs family has two moved-to-moved sites patching `run_garden`: the `_garden` helper in `test_server_tools_lifecycle.py` that wraps `wf_garden_docs_response`, and the `fake_garden` block in `test_server_context_efficiency.py` that drives `wf_garden_docs_response` under the publication lock; both repointed. The roughly sixty other `run_garden` patches in the lifecycle module wrap prepare, review and close stayers and stay on `server_impl` (`wf_validate_docs_response` calls only `run_validate`, so a block that patches `run_garden` and also calls it is not a moved-to-moved site). The gate family has no patch site (verified); `test_secrets_validators.py` binds `_check_secrets_gate` through the rebinding and stays valid.
4. Tests: `FAMILIES` in `test_handler_modules.py` becomes a tool-to-response map so `wf_open_gate` resolves to `wave_open_gate_response` and `wf_close_gate` to `wf_close_wave_gate_response` (retired-name shims that a comment in the roster says must remain); three entries; full-classified-set AST assertions per module; identity assertions for every re-exported name and the mutable PID set; reload-proof entries; the advisory-site census in `test_server_tools_lifecycle.py` adds `docs_handlers` to its owner tuple because the `wf_validate_docs_response` site moves file (the sanctioned set is unchanged); the source-text anchor in `test_server_tools.py` that counts `run_validate_changed(` call sites in `server_impl.py` is unaffected because `_run_post_write_lint` stays; the existing `test_server_tools.py`, `test_server_tools_lifecycle.py`, `test_dashboard_server.py`, `test_docs_lint.py`, `test_secrets_validators.py` and `test_lifecycle_mutation_lock.py` pass with only the listed edits; `wf_sync_surfaces_response` and `wf_scan_secrets_response`, which no test drives by name today, gain one transport-free call each on a temp repo.
5. Receipts: covered by the wave's receipt sequence; this change precedes `1ymzo` because that change needs `dashboard_handlers`.

## Scope

**Problem statement:** the wrapper families are the cheapest remaining lines to move and the most numerous tools; moving the three coherent ones together under one review avoids three readiness rounds, and the members the recipe cannot move are named and kept.

**In scope:** inventory, three modules, rebinding blocks, purge entries, the named call-time read, the listed repoints, tests, CHANGELOG bullet, architecture doc lines.

**Out of scope:** any behavior change; `wave_lint_lib`, `docs_gardener`, `dashboard_lib`, `dashboard_server`; the lint substrate, `wf_audit`, the secrets close gate, the introspection trio and `_WAVE_CURRENT_NEXT_ACTION`, all of which stay; `wf_audit_install` (moves in `1ymzo`); a `TOOLS` list.

## Acceptance Criteria

- [x] AC-1: Every classified definition and object lives in its module and not in `server_impl.py`, the named stayers remain, and the full-set AST tests prove it for all three modules.
- [x] AC-2: The thirteen tools are byte-identical to the golden fixture; every re-exported name and the PID set pass their identity assertions; the two undriven responses have transport-free calls.
- [x] AC-3: Three purge entries and module-top imports present; reload tests and the parameterized proof pass; the manifest lists all three.
- [x] AC-4: The listed patch sites are repointed, the `run_garden` patches around lifecycle stayers are left on `server_impl`, and the owner-tuple edit made; the named existing test modules pass with no other edit; no wrapper module joins the evaluator list and the derivation is recorded.
- [x] AC-5: The change's own suites and every test it adds pass, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Commit the inventory with the three-way classification, the stayers and their reasons, and the patch-site list.
- [x] Create the three modules, move the families, add the rebinding blocks, the call-time read and the purge entries.
- [x] Repoint the listed patch sites; change `FAMILIES` to a map; add the full-set assertions, identity assertions, reload-proof entries, the owner-tuple edit and the two transport-free calls.
- [x] Architecture doc lines, CHANGELOG bullet, framework suite; required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| wrapper-inventory | implementer | ce-move (sibling change) | Committed and reviewed before the move. |
| wrapper-move | implementer | wrapper-inventory | One owner; three modules in one pass. |
| independent-review | required reviewers | wrapper-move | Fresh contexts. |

## Serialization Points

- `.wavefoundry/framework/scripts/docs_handlers.py`
- `.wavefoundry/framework/scripts/dashboard_handlers.py`
- `.wavefoundry/framework/scripts/edit_gate_handlers.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_handler_modules.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/architecture/current-state.md`
- `docs/architecture/domain-map.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/domain-map.md` gain the three modules; the domain-map entry states that `wf_audit`, the secrets close gate and the lint substrate stay in the composition root and why.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The move is the change; the stay list is what keeps the decorator and the lint fixtures honest. |
| AC-2 | required | Public surface must survive across thirteen tools. |
| AC-3 | required | A missed purge entry serves stale code after reload. |
| AC-4 | required | About sixty test sites would go inert otherwise. |
| AC-5 | required | Change-local correctness. |

## Progress Log

Final delivery checkpoint (2026-09-22): all required lanes and Council approved unchanged reviewed source; R2 baseline independently verified including index AC-5. Full 9,508-test receipt current. Evidence: `evidence/qa-final.md`, `evidence/council-final.md`, `retrieval-evidence.md`. Earlier pending checkpoints are historical and resolved.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Observe: canonical isolated affected-file verification green: 3,153 tests across 14 files, two skips. All change-local and newly added checks pass, including golden/registry, scratch reload, dashboard native processes, lifecycle, docs lint and upgrade/recovery. Full-suite receipt and delivery review remain wave-level work. | run_tests.py --file (14 admitted affected modules); /private/tmp/1ymzq-pre-r1-canonical.log; extraction-equivalence.json. |
| 2026-09-21 | Observe: additional fixture anchors discovered during verification: lifecycle mutation-lock tests loaded a private server alias, making per-call public imports bypass patches; switched to shared public loader. Audit source slice ended at the moved upgrade response; now inspects the audit and three bounded helpers directly. Combined unittest modules also polluted reloaded secrets module state; isolated 157 scanner tests pass. Canonical runner isolates each file. | 24 mutation-lock/audit replays pass; existing predicates/assertions retained. |
| 2026-09-21 | Observe: classified-set/identity and packaging assertions pass; modified-scratch reload reaches public tools with required arguments; all moved bodies normalize to the committed baseline. Live MCP reload re-registers 89 tools with no description/roster change and implementation matching disk. | extraction-equivalence.json; test_handler_modules; wf_reload_mcp. |
| 2026-09-21 | Observe: 27 definitions and 3 objects extracted; 57 dashboard patch calls and 2 garden patches repointed, advisory owner tuple expanded. Structural tests, manifest/anchors, real scratch reload and transport-free response calls pass. Initial reload probes lacked required gate/CE arguments; corrected. Native dashboard 6 tests pass with host access after sandbox blocked ps/loopback. | wrapper-inventory.md; dashboard_handlers-patch-census.json; test_handler_modules; DashboardManagedIdentityTests. |
| 2026-09-21 | Readback / Thought: extract the three approved wrapper families and objects; preserve registration closures, lint/audit stayers, child-PID ownership and per-call patched start timeout. Repoint moved-to-moved patches only. | wrapper-inventory.md; mechanical AST gapfill after MCP orientation. |
| 2026-09-21 | Planned after a census: 48 definitions, 2,431 lines, fifteen tools. | AST census of `server_impl.py`. |
| 2026-09-21 | Readiness round: `wf_audit_response` is decorated at definition time and cannot move under the recipe; `_run_post_write_lint` is patched by the shared hermeticity fixture and stays with its caller; the secrets close gate is a lifecycle composition; the introspection trio and the next-action table stay; five `DOCS_LINT_*` constants, not three; `wf_validate_docs` was missing from the tool list; the gate tools need a tool-to-response map; about fifty-seven moved-to-moved patch sites listed; `_reap_dashboard_child_pids` is on the measured closure and goes with index; `DASHBOARD_START_WAIT_SECONDS` becomes a call-time read. Partition renamed to `edit_gate_handlers`. | Readiness review in this wave directory. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Three modules, one change; `wf_audit`, secrets gate, lint substrate and introspection stay. | Each stayer has a concrete reason (decorator, fixture, lifecycle class, delegator); the three movers are coherent. | Move everything (first draft); breaks the recipe and about nine hermeticity fixtures. |
| 2026-09-21 | The child-PID trio (set, register, reap) goes with index. | `_reap_dashboard_child_pids` is on the measured closure; splitting the set from its writers would need a shared-identity argument at every site. | Keep the trio with dashboard and accept that `dashboard_handlers` joins the evaluator list. |
| 2026-09-21 | `DOCS_LINT_*` constants and `_regenerate_codebase_map_safe` stay in the root. | No docs mover reads the constants; the map helper's callers are prepare and close. | Move them with docs (first draft); a domain misfit. |
| 2026-09-21 | Constants that tests patch on `server_impl` are read at call time. | The alternative is repointing every constant patch in the suite; the read costs nothing. | Repoint the seven `DASHBOARD_START_WAIT_SECONDS` sites. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A dashboard patch site is missed and a test spawns a real process. | The inventory lists every site by file and range; the delivery lane greps `patch.object(server_impl` for dashboard names. |
| `edit_gate_handlers` is mistaken for the lifecycle gate modules. | The domain-map entry distinguishes edit-governance gates from phase gates. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

Computational verification: full framework suite passed 9,508 tests across 121 files (12 skips). Required independent delivery review is still pending.
