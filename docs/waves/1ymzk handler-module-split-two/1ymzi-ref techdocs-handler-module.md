# Techdocs Handler Module

Change ID: `1ymzi-ref techdocs-handler-module`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-09-21
Wave: `1ymzk handler-module-split-two`

## Rationale

Wave `1y0h2` moved the code-navigation and graph handler families out of `server_impl.py` into `codenav_handlers.py` and `graph_handlers.py` with a recipe that kept the decorated closures in `register_mcp_surface` byte-identical, rebound the moved names through one module-top `from <module> import (...)` block (private names included; the existing two blocks import fifty-eight underscore names), reached the helpers that stayed behind through a function-level `import server_impl`, appended each module to the reload purge list, and proved the public tool surface unchanged against the golden fixture. The modularity kickoff (`docs/reports/wavefoundry-implementation-kickoff.md`, Slice 5) named techdocs as the reference decoupled subsystem because `techdocs_audit_lib.py` already refuses to import `server_impl`; the kickoff's `TOOLS`-list mechanism was rejected by `1y0h1` in favor of registry introspection, so the shape here is the `1y0h2` recipe, not the kickoff's.

The family is small and self-contained. `server_impl.py` (29,036 lines) holds three techdocs definitions, `_bounded_techdocs_payload`, `wf_techdocs_audit_response` and `wf_techdocs_baseline_response`, 252 lines, registered as the tools `wf_techdocs_audit` and `wf_techdocs_baseline`, plus two module-level constants the family and its tests read, `TECHDOCS_AUDIT_FINDING_CAP` and `TECHDOCS_AUDIT_SURVIVOR_CAP`. They reach three helpers that other families also use and that stay behind, read as `server_impl.<name>` per call: `_response`, `_attach_lint_to_response` and `_trigger_background_index_refresh_for_paths`; one name `server_impl` imports from a sibling, `_diagnostic`, which the new module imports directly from `lifecycle_gate_support` (the same convention as `1ymzj`); and one annotation-only name, `McpRepoCache`. Three test modules reference the family: `test_server_tools.py` and `test_server_tools_lifecycle.py` by name, and `test_render_agent_surfaces.py` through a source-text allowlist that asserts only `server_impl.py` calls `render_techdocs_baseline(`. No golden-corpus anchor names a techdocs symbol, and no measured evaluator tool reaches one. This is the smallest possible third family and the right rehearsal for the memory move in the same wave: same recipe, same reviewers, one afternoon.

## Requirements

1. A new module `.wavefoundry/framework/scripts/techdocs_handlers.py` receives the three definitions and the two constants. Helpers with callers outside the family stay in `server_impl.py` and are reached as `server_impl.<name>` through a function-level `import server_impl` resolved per call; the module never imports `server_impl` at module top and never reaches a helper through `_load_script`, because `test_server_tools.py` asserts by source that `wf_techdocs_baseline_response` contains `render_techdocs_baseline(` and not `_load_script(`. The `McpRepoCache` annotation becomes `server_impl.McpRepoCache` under the existing `from __future__ import annotations`.
2. The decorated closures in `register_mcp_surface` stay byte-identical. `server_impl.py` rebinds the moved names, the two constants included, with one module-top `from techdocs_handlers import (...)` block, so every internal caller, every test that reads `server_impl.TECHDOCS_AUDIT_*` or patches `server_impl.<name>`, and the MCP wrappers resolve through `server_impl` as today. Names, tiers, parameters, docstrings, annotations and extra-argument validation are unchanged; the golden tool-surface fixture does not change.
3. `techdocs_handlers` is appended to the reload purge list at the top of `server_impl.py` and imported by public name at module top, so `test_reload_picks_up_every_added_module` and the import-derived `test_reload_purge_covers_direct_sibling_imports` cover it without edits.
4. The existing tests are the transport-free coverage: `test_server_tools.py` drives `wf_techdocs_audit_response` against fixture roots through the real audit library and `wf_techdocs_baseline_response` through the real renderer in dry-run, and reads `inspect.getsource` of the rebound object, which survives the move. This change adds only: a `FAMILIES` entry `techdocs_handlers: (wf_techdocs_audit, wf_techdocs_baseline)` in `test_handler_modules.py`, which yields the AST location test, the no-module-top-import test, the name-resolution test with its built-in mutants, and the manifest test; an assertion that the fixture tree is byte-unchanged after a dry-run call; and the parameterized reload proof described in `1ymzj` Requirement 7. Three existing tests need a named edit, each listed here because the plan's allowed edit class is source-file path, patch target, allowlist entry or owner tuple: `test_render_agent_surfaces.py`'s `render_techdocs_baseline(` allowlist gains `techdocs_handlers.py` and its `server_impl.py` presence assertion is repointed; `test_server_tools_lifecycle.py`'s advisory-site census adds `techdocs_handlers` to its owner tuple so the three techdocs advisory sites stay in the exact set; the `test_handler_modules.py` docstring and the manifest test name that say "nineteen" and "both" are updated.
5. `retrieval_eval.PRODUCTION_RETRIEVAL_MODULES` does not gain the module: three independent reachability closures from the four measured tools reach none of the three definitions. The wave-level before-and-after standing-evaluation receipt pair in `1ymzj` Requirement 5 applies to this change too, because `server_impl.py` is a member and this change edits it; the before-receipt is recorded before this change's first edit.
6. The ninety-tool golden fixture, the registry parity test and the AST roster census pass unchanged, because registration stays in the composition root.

## Scope

**Problem statement:** the techdocs handlers are the last small, self-contained family still inlined in `server_impl.py`, and moving them first rehearses the recipe the memory move in this wave depends on.

**In scope:**

- The new module with the three definitions and two constants, and the rebinding import block.
- The purge-list entry.
- The `FAMILIES` entry, the dry-run byte-unchanged assertion, and the three named test edits.
- The architecture doc lines (Affected Architecture Docs) and a CHANGELOG Unreleased bullet.

**Out of scope:**

- Any change to what the two tools return or accept.
- A `TOOLS` list or any second registration source; `1y0h1` settled that.
- Moving `_response`, `_attach_lint_to_response` or `_trigger_background_index_refresh_for_paths`, which other families call.
- Touching `techdocs_audit_lib.py` or `techdocs_baseline.py`.

## Acceptance Criteria

- [x] AC-1: The three techdocs definitions and two constants live in `techdocs_handlers.py` and not in `server_impl.py`; the module has no module-top `server_impl` import and no `_load_script` reach; the AST and source tests prove all three.
- [x] AC-2: Both responses run against a fixture root without the transport through the existing tests, the dry-run call leaves the fixture tree byte-unchanged, and the registered tools are byte-identical to the golden fixture.
- [x] AC-3: The module is in the purge list and imported at module top; both reload tests and the parameterized reload proof pass; the packaging manifest test lists it.
- [x] AC-4: The three existing test modules pass with only the named source-path, patch-target, allowlist and owner-tuple edits, and `PRODUCTION_RETRIEVAL_MODULES` is unchanged with the derivation recorded.
- [x] AC-5: The change's own suites and every test it adds pass, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Record the wave-level before-receipt (`1ymzj` Requirement 5) on the pre-change tree, then inventory the three definitions, two constants, helpers and every referencing test site including the source-text allowlist; record the table in the Progress Log.
- [x] Create `techdocs_handlers.py`, move the definitions and constants, add the rebinding import block and the purge entry.
- [x] Add the `FAMILIES` entry and the dry-run assertion; apply the three named test edits.
- [x] Run the golden fixture, registry parity and AST census tests, then the framework suite; update the architecture doc lines and add the CHANGELOG bullet; required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| techdocs-move | implementer | wave before-receipt | Small; done first so the memory move reuses the rehearsed recipe. |
| independent-review | required reviewers | techdocs-move | Fresh contexts; golden fixture and reload proof are the evidence. |

## Serialization Points

- `.wavefoundry/framework/scripts/techdocs_handlers.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_handler_modules.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `docs/architecture/current-state.md`
- `docs/architecture/domain-map.md`
- `docs/architecture/layering-rules.md`
- `docs/reports/`

## Affected Architecture Docs

`docs/architecture/current-state.md` lists the handler modules beside the composition root and `docs/architecture/domain-map.md` (Handler ownership) names them with the function-local-import rule; both gain `techdocs_handlers.py`, and their "both siblings" wording about purge-and-reimport becomes "every handler sibling". `docs/architecture/layering-rules.md` has no handler-module row in its boundary invariants; this wave adds one (module-top import of the composition root prohibited, function-level lookup permitted, purge-list membership required, verified by `test_handler_modules`). No boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The move is the change. |
| AC-2 | required | Public surface and behavior must not move. |
| AC-3 | required | A missed purge entry serves stale code after reload. |
| AC-4 | required | Existing coverage must survive the relocation, and the evaluator identity must be derived. |
| AC-5 | required | Change-local correctness. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Observe: complete test_server_tools, test_server_tools_lifecycle, test_render_agent_surfaces and test_tool_surface_golden passed: 1,031 tests in 178.487 seconds. Together with the earlier 70 focused tests, all named TechDocs verification is green. Source frozen for independent checkpoint; AC-5 and the final suite/docs/review task await combined-wave checks. | [TechDocs delivery evidence](techdocs-delivery-evidence.md), including reproducible AST/registration checks and hashes; /private/tmp/1ymzk-techdocs-existing.log. |
| 2026-09-21 | Implement: extracted the three definitions and two caps with per-call retained-helper lookup, public compatibility reexports and plain-name purge. Replaced the renderer census exemption for the old owner with the new owner, preserving its exact two-entry contract. Observe: normalized AST equality for all three definitions; registration bytes unchanged; 70 focused handler, real producer, registry and reload/purge tests passed. Complete existing modules and golden verification running; memory untouched pending independent TechDocs review. | techdocs-inventory.md; /private/tmp/1ymzk-techdocs-focused.log; /private/tmp/1ymzk-techdocs-equivalence.json. |
| 2026-09-21 | Observe: valid before receipt completed on frozen generation 1861 before source edits; verdict fail versus older standing generation 1772, with no invalidation. Existing quality differences predate this wave; after evidence will compare both with standing and this fresh before state. Original invalid attempt retained; retry uses a fresh path. Thought: execute approved TechDocs inventory, keeping registration byte-identical and replacing the renderer census owner rather than permitting both owners. | docs/reports/retrieval-quality-1ymzk-before-retry1.json; techdocs-inventory.md; independent code/QA and architecture inventory approvals. |
| 2026-09-21 | Readback: Move the three TechDocs definitions and two caps to techdocs_handlers, preserve registration bytes and public behavior, qualify only retained helpers, and verify dry-run bytes, golden/registry, reload and manifest (AC-1 through AC-5). Thought: capture pre-change evaluation before moving source. Generic implementer owns source/tests; coordinator owns docs/evaluation; independent reviewer checkpoints follow each family. Inherited host model chosen for careful mechanical refactoring; runtime identity unknown. Gapfill: MCP index_health and code_definition refused with index_runtime_stale even after reload; native AST and targeted source reads used. Initial before evaluation produced an invalid receipt because index changed to building; preserved as retrieval-quality-1ymzk-before.json, retry follows stable CLI convergence. | Current plans; scoped source inventory; before-run invalid receipt. |
| 2026-09-21 | Planned as the rehearsal change of the second handler-split wave after a census found three definitions, three shared helpers and two referencing test modules. | AST census of `server_impl.py`; `retrieval_eval.TOOLS`; `docs/evals/retrieval-quality-golden.json` has no techdocs anchor. |
| 2026-09-21 | Readiness round (red-team and architecture seats, code and QA lanes, all fresh). Corrections folded in: a source-text allowlist test in `test_render_agent_surfaces.py` and an advisory-site census in `test_server_tools_lifecycle.py` both fail on a third module and are now named edits; the two `TECHDOCS_AUDIT_*` constants and the `McpRepoCache` annotation were missing from the inventory; `_diagnostic` is imported directly from its owner; the existing tests are the transport-free coverage, so only the `FAMILIES` entry and a dry-run assertion are added; the wave owes a before-and-after retrieval receipt pair because `server_impl.py` is a production retrieval module; `domain-map.md` and a `layering-rules.md` row join the affected docs. | Readiness review in this wave directory; context `handler-split-two-readiness-20260921`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Follow the `1y0h2` recipe, not the kickoff's `TOOLS` list. | `1y0h1` chose registry introspection; a per-module tool list would be a second registration source. | The kickoff's Slice 5 shape; rejected as already superseded. |
| 2026-09-21 | Techdocs first, memory second, in one wave. | Same recipe and reviewers; the small move rehearses the large one and the golden fixture is checked twice. | Separate waves: two readiness rounds for one recipe. |
| 2026-09-21 | Constants move with the family and are re-exported. | Consistent with `1y0h2`, and tests read them through `server_impl` unchanged. | Keep them in the monolith and prefix reads; more edits for no gain. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A test reads `server_impl.py` source text for a techdocs definition. | One is known and named (`test_render_agent_surfaces.py` allowlist); the inventory greps for others before the move. |
| The dry-run baseline path writes into the fixture root during the transport-free test. | Verified write-free at readiness (the renderer returns before its write loop; lint attachment and refresh are gated on run mode); the new assertion pins it. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

| 2026-09-21 | Repaired whole suite passes 9,481 tests across 119 files, 12 skips, in 283.551 seconds with host process/localhost access. Framework receipt result ok, inputs_hash 58bd9cc3ca90dfa056e3d7c7bd5ecbe01661aa25db1133e37a567e9eb1e020fb. Both cycle-1 findings terminal after independent code/QA verification. | delivery-review.md; /private/tmp/1ymzk-full-suite-repair1.log. |
