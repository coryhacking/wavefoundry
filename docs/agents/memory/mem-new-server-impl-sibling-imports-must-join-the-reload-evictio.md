# New server_impl sibling imports must join the reload eviction set

Owner: Engineering
Status: active
Last verified: 2026-07-21

Memory ID: `mem-new-server-impl-sibling-imports-must-join-the-reload-evictio`
Kind: `environment_gotcha`
Confidence: 0.9
Created: 2026-07-21
Updated: 2026-07-21

## Summary

When adding a module-level import of a sibling scripts-dir module to server_impl.py, add the module name to the top-of-module reload-eviction set in the same change. importlib.reload re-executes server_impl against whatever sibling modules are already cached in sys.modules, so a missed entry makes wf_reload_mcp crash or silently serve stale values (live-caught: public_contract's five-name SEARCH_MODES unpacking crashed against the stale two-value cached module, 'expected 5, got 2'). The eviction block executes at the top of the reload, before the imports, so fixing the set and retrying the reload self-heals the live session without a restart.

## Evidence

- `1seax`
- `public-contract-missing-from-reload-eviction`
- `ev-public-contract-missing-from-reload-eviction-3`
- `test_mcp_reload_evicts_context_efficiency_dependency`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/public_contract.py`
