# Context-Efficiency Handler Module

Change ID: `1ymzl-ref context-efficiency-handler-module`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-21
Wave: `1ymzq handler-module-split-three`

## Rationale

Wave `1ymzk` deferred context-efficiency projection from the memory move because it interleaves with the middleware chain `1y0h1` made explicit and the quiet-period monitor `1yj14` interlocked against index builds. Its readiness round verified the boundary is clean in both directions. The census: seventeen definitions, 722 lines, one tool (`wf_context_efficiency_eval`): nine projection and persistence functions (`_read_ce_projection_config`, `_pending_ce_generations`, `_maybe_project_context_efficiency`, `_project_context_efficiency_wave`, `_flush_context_efficiency`, `project_pending_context_efficiency`, `project_pending_context_efficiency_root`, `_context_efficiency_state`, `wf_context_efficiency_eval_response`), five non-memory crediting extractors (`_state_sources_review_evidence`, `_state_sources_get_change`, `_state_sources_live_waves`, `_state_sources_list_plans`, `_state_sources_map`), and the three `_state_sources_memory_*` extractors that `1ymzk` kept in the monolith for this change. `_credit_exploration_avoided_surface` and `_lifecycle_id_tokens` move with memory in `1ymzk` and are not reached by any definition here.

Outside callers, all kept valid by the rebinding block: `_flush_context_efficiency` from `_lifecycle_context_result` and the pause and reopen closures; `_maybe_project_context_efficiency` and `_read_ce_projection_config` from `ImplHandler`'s projection monitor (the monitor thread lives on `ImplHandler`, not `McpRepoCache`); `_context_efficiency_state`, `project_pending_context_efficiency` and the tool response from `register_mcp_surface`; the extractors from the module-level `_STATE_SOURCE_EXTRACTORS` dictionary, which `_wrap_first_party_tool_costs` reads by bare name. One sibling reaches in: `project_context_efficiency.py` calls `server_impl.project_pending_context_efficiency_root` from inside a function. Staying helpers the family reaches, read as `server_impl.<name>` per call: `_atomic_replace_text`, `_attempt_focus_state`, `_find_wave_md`, `_focus_clear_write_needed`, `_load_script`, `_response`, `_wave_checkpoint_floor`, `list_waves`. Names `server_impl` imports from siblings are imported directly by the new module from their owners (`context_efficiency`, `index_source_guard`, `record_paths`, `ProjectPublicationUnavailable` from `review_evidence`, `_read_wave_record_text` from `lifecycle_gate_support`), with one exception: `project_state_publication_lock` is read as `server_impl.project_state_publication_lock` at call time because a test patches it there. Module-level objects the family owns and that move with re-export: the four `_CE_PROJECTION_*` quiet-period constants and `_STATE_SOURCE_EXTRACTORS`; `_STATUS_PATTERN` has seven other users (bare name, not counting `_CHANGE_STATUS_PATTERN`) and stays.

## Requirements

1. The committed inventory classifies the seventeen definitions and five objects, with every caller, patch site and source-text anchor.
2. A new `.wavefoundry/framework/scripts/context_efficiency_handlers.py` receives the classified set. The decorated closures, the `ImplHandler` monitor and `_wrap_first_party_tool_costs` stay byte-identical in `server_impl.py` and resolve every moved name through one module-top `from context_efficiency_handlers import (...)` block. The module never imports `server_impl` at module top nor another handler module at any scope, reaches staying helpers per call, is appended to the purge list, and is imported by public name.
3. Patch transparency (the `1ymzk` rule): the interlock fixture in `test_index_source_guard.py` patches `_read_ce_projection_config` on `server_impl` and starts the real monitor, which calls the moved `_maybe_project_context_efficiency`, which today calls `_read_ce_projection_config` by bare name; after the move that patch would be inert and the real ninety-second clamp would time the test out. So `_maybe_project_context_efficiency` reads `server_impl._read_ce_projection_config` at call time, a named exception, and the interlock tests pass unchanged. The other moved-to-moved sites are repointed to the new module and listed: `test_server_context_efficiency.py` patching `_project_context_efficiency_wave` around `project_pending_context_efficiency_root` (two blocks asserting call counts), and its two source-text reads of `server_impl.py` that locate `_project_context_efficiency_wave` and expect it among `_attempt_focus_state`'s callers (repointed with a per-anchor source map). The `_atomic_replace_text` patches in `test_index_source_guard.py` stay observed because the moved code reads it as `server_impl._atomic_replace_text`.
4. `project_context_efficiency.py` imports `context_efficiency_handlers` for `project_pending_context_efficiency_root`; it no longer names `server_impl` lexically and transitively loads it at first call, as `memory_cli` does after `1ymzk`.
5. The `1yj14` interlock is preserved: the monitor's write path still acquires `index_source_guard` with `wait=False` before its publication lock; `test_index_source_guard.py` (`test_same_process_build_excludes_monitor_and_unlocked_carrier_allows_write`, `test_unknown_acquisition_preserves_pending_work`, `test_publication_contention_releases_source_guard`) and `test_lifecycle_gates_structure.test_reload_refreshes_imported_siblings_and_source_guard_callable` pass unchanged.
6. Tests: a `FAMILIES` entry (`context_efficiency_handlers: {wf_context_efficiency_eval: wf_context_efficiency_eval_response}` under the tool-to-response map this wave introduces); a full-classified-set AST assertion that every moved definition is absent from `server_impl.py` and present in the module; identity assertions for every re-exported name and object; the reload-proof entry; the existing `test_context_efficiency.py`, `test_server_context_efficiency.py`, `test_index_source_guard.py`, `test_render_platform_surfaces.py` (the hook seam) and `test_memory_records.py` (which drives `_flush_context_efficiency` and `project_pending_context_efficiency`) pass with only the listed edits.
7. Receipts: this change edits `server_impl.py` and is covered by the wave's receipt sequence in the wave record (the before-receipt follows the unused containment/evaluator bootstrap but precedes production caller adoption in `1ymzp`; the mid-wave after-receipt follows `1ymzo`).

## Scope

**Problem statement:** context-efficiency projection is the family `1ymzk` deferred and the last one with a sibling back-reference into the monolith.

**In scope:** inventory, module, rebinding block, purge entry, the named call-time exception, the sibling inversion, the listed test edits, CHANGELOG bullet, architecture doc lines.

**Out of scope:** any change to projection semantics, quiet-period defaults, the cost middleware or the monitor's behavior; moving `_STATUS_PATTERN`, `ImplHandler` or the lifecycle helpers; the exploration-avoided module.

## Acceptance Criteria

- [x] AC-1: Every classified definition and object lives in `context_efficiency_handlers.py` and not in `server_impl.py`; the full-set AST, boundary and name-resolution tests prove it.
- [x] AC-2: The tool is byte-identical to the golden fixture; every re-exported name passes its identity assertion; `project_context_efficiency.py` no longer names `server_impl`.
- [x] AC-3: Purge entry and module-top import present; both reload tests and the parameterized proof pass; the manifest test lists the module.
- [x] AC-4: The interlock tests pass unchanged through the named call-time read; the four listed test sites are repointed; the remaining named test modules pass with no other edit.
- [x] AC-5: The change's own suites and every test it adds pass, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Commit the inventory.
- [x] Create the module, move the classified set, add the rebinding block, the call-time read and the purge entry.
- [x] Invert `project_context_efficiency.py`; repoint the four listed sites.
- [x] Add the `FAMILIES` entry, full-set assertion, identity assertions and reload-proof entry; run the interlock tests.
- [x] Architecture doc lines, CHANGELOG bullet, framework suite; required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| ce-inventory | implementer | 1ymzp delivered | Second change in the wave. |
| ce-move | implementer | ce-inventory | One owner for `server_impl.py`, the module and the sibling. |
| independent-review | required reviewers | ce-move | Fresh contexts; golden fixture, reload proof, interlock tests. |

## Serialization Points

- `.wavefoundry/framework/scripts/context_efficiency_handlers.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/project_context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_handler_modules.py`
- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `docs/architecture/current-state.md`
- `docs/architecture/domain-map.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/domain-map.md` (Handler ownership) gain the module; the boundary row `1ymzk` adds to `layering-rules.md` covers it.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The move is the change. |
| AC-2 | required | Public surface and every reached name must survive; the inversion is the point. |
| AC-3 | required | A missed purge entry serves stale code after reload. |
| AC-4 | required | The interlock is a fixed defect and must not regress. |
| AC-5 | required | Change-local correctness. |

## Progress Log

Final delivery checkpoint (2026-09-22): all required lanes and Council approved unchanged reviewed source; R2 baseline independently verified including index AC-5. Full 9,508-test receipt current. Evidence: `evidence/qa-final.md`, `evidence/council-final.md`, `retrieval-evidence.md`. Earlier pending checkpoints are historical and resolved.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Observe: canonical isolated affected-file verification green: 3,153 tests across 14 files, two skips. All change-local and newly added checks pass, including golden/registry, scratch reload, dashboard native processes, lifecycle, docs lint and upgrade/recovery. Full-suite receipt and delivery review remain wave-level work. | run_tests.py --file (14 admitted affected modules); /private/tmp/1ymzq-pre-r1-canonical.log; extraction-equivalence.json. |
| 2026-09-21 | Observe: classified-set/identity and packaging assertions pass; modified-scratch reload reaches public tools with required arguments; all moved bodies normalize to the committed baseline. Live MCP reload re-registers 89 tools with no description/roster change and implementation matching disk. | extraction-equivalence.json; test_handler_modules; wf_reload_mcp. |
| 2026-09-21 | Observe: 113 server-CE/interlock/lifecycle-structure tests and 381 core-CE/platform/memory tests pass, no skips. All 17 moved definition ASTs match pre-move HEAD after only documented root attribute/import normalization; registrar, monitor and middleware remained byte-identical at extraction. Initial test patch used a handler imported before server startup purged it; moved the test import after server_impl and repeated the focused run successfully. | test_server_context_efficiency, test_index_source_guard, test_lifecycle_gates_structure; test_context_efficiency, test_render_platform_surfaces, test_memory_records. Structural family/golden/reload coverage remains coordinator-owned. |
| 2026-09-21 | Implement: extracted 17 definitions and 5 objects after containment handoff; preserved registrar, monitor and middleware bytes. Retained ImplHandler annotation precision with TYPE_CHECKING-only import, no runtime root import. MCP navigation preceded mechanical AST gapfill. Four test anchors repointed; verification pending. Inventory is durable evidence, not a Git commit. | context-efficiency-inventory.md; normalized AST checks and focused tests follow. |
| 2026-09-21 | Planned from the `1ymzk` deferral. | AST census of `server_impl.py`; `project_context_efficiency.py`. |
| 2026-09-21 | Readiness round: the interlock fixture's patch would have been inert after the move (named call-time read added); four moved-to-moved and source-text sites listed; census corrected to seventeen definitions and 722 lines; `_lifecycle_id_tokens` dropped from the staying list; the real test module names; the monitor's owner corrected to `ImplHandler`. | Readiness review in this wave directory. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Second change, after containment. | Boundary verified clean; smallest family with a back-reference; `1ymzp` must precede it for the receipt window. | First; leaves a production-module edit outside the pair. |
| 2026-09-21 | `_read_ce_projection_config` read through `server_impl` at call time. | The interlock fixture patches it on the server and starts the real monitor; repointing the fixture would weaken a `1yj14` test. | Repoint the fixture; rejected. |
| 2026-09-21 | The extractor dictionary moves and is re-exported. | It is a table of family functions; the middleware reads a name, not a location. | Keep it in the monolith; more edges for nothing. |

## Risks

| Risk | Mitigation |
| --- | --- |
| The monitor thread captures a stale function reference across reload. | Verified at readiness: the thread resolves free names from the server globals at call time; the reload proof covers the module. |
| A lifecycle closure patches a projection name in tests. | The inventory greps every `patch.object` on the seventeen names; the four found are listed. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

Integration repair: the record-layout census detected its pending-plan docstring moved to context_efficiency_handlers.py. Repointed only the allowlist filename; stale-entry and unlisted-site checks remain active.

Computational verification: full framework suite passed 9,508 tests across 121 files (12 skips). Required independent delivery review is still pending.
