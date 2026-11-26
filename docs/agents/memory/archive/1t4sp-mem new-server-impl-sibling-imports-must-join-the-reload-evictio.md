# New server_impl sibling imports must join the reload eviction set

Owner: Engineering
Status: archived
Last verified: 2026-09-25

Memory ID: `1t4sp-mem new-server-impl-sibling-imports-must-join-the-reload-evictio`
Kind: `environment_gotcha`
Confidence: 0.9
Created: 2026-07-21
Updated: 2026-11-25
Checked at: 2026-11-25T16:09:19Z
Check note: Item 7 review: encoded elsewhere. Encoded at whole-lesson scope: tests/test_lifecycle_gates_structure.py::ReloadClosureGuardTests::test_the_tree_passes_with_the_starting_lists asserts _reload_closure_problems(...) == [], which reports 'not reloaded: <name>' for any flat module imported anywhere in server_impl or another evicted module that is neither in the purge set (server_impl.py:76-127), relo.
Check flags: target_churn
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, encoded in Encoded at whole-lesson scope: tests/test_lifecycle_gates_structure.py::ReloadClosureGuardTests::test_the_tree_passes_with_the_starting_lists asserts _reload_closure_problems(...) == [], which reports 'not reloaded: <name>' for any flat module imported.
Archive path: `docs/agents/memory/archive/1t4sp-mem new-server-impl-sibling-imports-must-join-the-reload-evictio.md`

## Summary

When adding a module-level import of a sibling scripts-dir module to server_impl.py, add the module name to the top-of-module reload-eviction set in the same change. importlib.reload re-executes server_impl against whatever sibling modules are already cached in sys.modules, so a missed entry makes wf_reload_mcp crash or silently serve stale values (live-caught: public_contract's five-name SEARCH_MODES unpacking crashed against the stale two-value cached module, 'expected 5, got 2'). The eviction block executes at the top of the reload, before the imports, so fixing the set and retrying the reload self-heals the live session without a restart.

## Evidence

- `1seax`
- `public-contract-missing-from-reload-eviction`
- `ev-public-contract-missing-from-reload-eviction-3`
- `test_mcp_reload_evicts_context_efficiency_dependency`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/public_contract.py`
