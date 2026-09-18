# Move Code Navigation And Graph Handlers Into Domain Modules

Change ID: `1y0bf-ref codenav-graph-handler-modules`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-17
Wave: `1y0h2 handler-module-split`

## Rationale

**Brief.** Goal: begin shrinking `server_impl.py` by moving the two largest self-contained handler families, code navigation and graph query, into sibling response modules observed by the introspection registry from `1y0be-ref tool-registry-and-wrapper-chain`. Audience: framework maintainers and downstream integrators who merge around the server file. Approach: move the `*_response` functions and their private helpers; keep decorated registration closures in the composition root and delegate to sibling response modules at invocation time. Constraints: public surface identical; reload safe; no change to retrieval behavior. Success: neither family's response functions are defined in `server_impl.py`, both modules are unit-tested without the transport, and the golden fixture is unchanged.

Verification found these families already delegate through loaders: `_get_chunker_module()` (`server_impl.py:22615`) and `_load_graph_query()` (line 24745, a wrapper over `_load_script("graph_query")`). That makes the seam thin. The reload investigation also settled the design question the earlier evaluation raised: `wf_reload_mcp` clears `_script_cache` and purges a named list of sibling modules, so relocated handlers stay fresh after an upgrade as long as their modules are on that list. Techdocs is not used as the exemplar here because its dependency claims in the RFC were found to be inaccurate; it can follow once the pattern is proven.

Re-verified 2026-09-17 against four intervening commits: none touched code-navigation or graph-query tool bodies, the implementation registration and runner survivors together match the roster, and the purge-list mechanism this change relies on is unchanged (see the parallel finding in `1y0be` about two new modules that were *not* added to it — a reminder to add `codenav_handlers`/`graph_handlers` to that list explicitly rather than assume it happens by default).

## Requirements

1. Two new modules, `.wavefoundry/framework/scripts/codenav_handlers.py` and `.wavefoundry/framework/scripts/graph_handlers.py`, receive the `*_response` functions and the private helpers used only by them for these tools: code navigation covers `code_list_files`, `code_read`, `code_keyword`, `code_lexical`, `code_constants`, `code_pattern`, `code_outline`, `code_definition`, `code_references`, `code_dependencies`, `code_hover`, and `code_commit_provenance`; graph covers `code_impact`, `code_callgraph`, `code_callhierarchy`, `code_graph_path`, `code_graph_community`, `code_risk_score`, and `wf_graph_report`.
2. Keep the existing decorated closures in `register_mcp_surface`; change only their delegation to resolve the moved response functions from the sibling modules at invocation time. Do not capture a module or response callable across reload. The `1y0be` registry continues to introspect FastMCP after registration; modules declare no `TOOLS` list and introduce no second registration source. Names, tiers, parameters, docstrings, annotations and extra-argument validation remain unchanged.
3. Helpers shared with other families stay in `server_impl.py` and are imported by the new modules through the same lazy indirection the family uses today, so neither module imports `server_impl` at module top level. A test asserts the absence of that import.
4. Both modules are added to the purge list at the top of `server_impl.py`, and the reload test asserts a modified handler module is picked up by `wf_reload_mcp`.
5. Unit tests exercise each module's response functions with a fixture handler and no MCP transport.
6. An AST test asserts that none of the nineteen response functions is defined in `server_impl.py` after the move, and the registry-based parity test from `1y0be` still covers their registered tools. Retain the existing AST roster census: decorated closures remain in the composition root, so moving response functions does not invalidate it.
7. The golden tool-surface fixture is unchanged, and the retrieval test corpus passes with no test edited beyond import paths.
8. `build_pack.py` includes the new modules without a manifest edit, confirmed by a packaging test that lists them in the generated manifest.

## Scope

**Problem statement:** Every handler lives in one 35,291-line file, so unrelated work collides in review and every integrator merges around the same file.

**In scope:**

- The two response modules, purge-list entries, and tests.
- Late delegation from existing registration closures to the response modules.
- Preserving both AST roster and runtime registry parity coverage.

**Out of scope:**

- Search handlers (`docs_search`, `code_search`, `code_ask`), lifecycle handlers, memory, context-efficiency, and techdocs; each follows in its own change once this pattern holds.
- Any change to ranking, chunking, graph building, or response shapes.
- A `server/` package layout.

## Acceptance Criteria

- [ ] AC-1: The golden tool-surface fixture is unchanged and the retrieval corpus passes with only import-path edits.
- [ ] AC-2: The AST test finds none of the nineteen response functions defined in `server_impl.py`, and both modules pass the no-top-level-`server_impl`-import test.
- [ ] AC-3: Unit tests for both modules run without booting the transport and cover every relocated response function with at least one call.
- [ ] AC-4: After `wf_reload_mcp` a modified `graph_handlers.py` is served, proven by the reload test.
- [ ] AC-5: The registry parity test covers the relocated tools, the AST roster census remains green, and both initial registration and reload preserve the full public surface.
- [ ] AC-6: The packaging test lists both modules in the generated manifest.
- [ ] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Inventory the private helpers each family uses and classify them as move, share, or duplicate-then-dedupe; commit the inventory as a short table (helper name, used by, classification) for review before Task 2 starts, so a missed helper is caught at review rather than mid-move.
- [ ] Move the graph response family first with late delegation from its existing closures; run golden and retrieval corpus.
- [ ] Move the code-navigation family; run golden and retrieval corpus.
- [ ] Verify all relocated response calls resolve through the new modules at invocation time; preserve introspection registration.
- [ ] Add purge-list entries, the no-import test, the AST absence test, and the reload test.
- [ ] Run the existing AST census and registry parity test against both original and reloaded registration.
- [ ] Add the packaging manifest test.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| inventory      | implementer | `1y0h1` registry | helper classification |
| graph          | implementer | inventory    | smaller family first |
| codenav        | implementer | graph        | |
| compose-guards | qa          | codenav      | delegation, tests, census preservation, packaging |


## Serialization Points

- `.wavefoundry/framework/scripts/codenav_handlers.py`
- `.wavefoundry/framework/scripts/graph_handlers.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/domain-map.md` list the two handler modules and state the rule that a handler family is a reloadable sibling response module with registration retained in the composition root. `docs/architecture/search-architecture.md` updates file references for the graph query entry points. The decision record from `1y0be` gains the exemplar outcome.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Unchanged public surface and behavior |
| AC-2 | required  | The move is the deliverable |
| AC-3 | required  | Testability without transport is the maintainer benefit |
| AC-4 | required  | Stale handlers after upgrade would be a silent regression |
| AC-5 | important | Preserves both registration and runtime parity coverage |
| AC-6 | required  | Downstream repositories must receive the modules |
| AC-7 | required  | Standard change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-14 | Change planned and admitted to `1y0h2 handler-module-split` | this document |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-14 | Code navigation and graph first, techdocs and memory later | Largest self-contained families with existing loader seams; techdocs' dependency picture was misstated in the RFC and memory has a static import back-reference | Techdocs as exemplar per the RFC: smaller, but not representative |
| 2026-09-14 | Modules never import `server_impl` at top level | Prevents a cycle and keeps each module testable in isolation; matches the existing `techdocs_audit_lib.py` rule | Allow the import: simpler moves, permanent cycle |
| 2026-09-14 | Originally proposed retiring the AST census; superseded 2026-09-17 | The original proposal moved registration, but the accepted introspection design keeps decorated closures in the composition root | Current decision: preserve AST and runtime parity tests |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A helper is used by both a moved family and a remaining one and gets duplicated | Inventory step classifies helpers first; duplicates are flagged for a follow-up dedupe |
| The inventory itself is wrong or incomplete, discovered mid-move | Archetype Council (Yoda, 2026-09-17): the inventory is now a committed, reviewed deliverable before Task 2 starts, not an internal step with no checkpoint |
| The two modules grow their own import-time cost | They stay on the lazy path the families already use |
| Downstream integrators with local patches to these handlers hit conflicts once | One-time cost, documented in the release notes for the version that ships this |
| Whether Waveforge's real fork has diverged inside these specific 19 tool bodies was not individually verified | `docs/reports/waveforge-fork-audit.md` (2026-09-17) confirms `register_mcp_surface` and its supporting infra are name-identical across both forks, which is what makes this split low-risk to attempt, but the individual code-navigation/graph tool names were not checked one by one against Waveforge's tree — an open detail to confirm before implementing, not a blocking one |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
