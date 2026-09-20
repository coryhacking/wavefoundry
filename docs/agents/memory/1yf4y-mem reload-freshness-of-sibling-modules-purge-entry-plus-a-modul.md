# Reload freshness of sibling modules: purge entry plus a module-top public-name import

Owner: Engineering
Status: active
Last verified: 2026-09-19

Memory ID: `1yf4y-mem reload-freshness-of-sibling-modules-purge-entry-plus-a-modul`
Kind: `environment_gotcha`
Confidence: 0.9
Created: 2026-09-19
Updated: 2026-09-19
Source exploration cost: 384402
Source event: `finding:1y0h1:QA-DEL-2`
Validation: promote
Validated by: agent
Action delta: When adding a sibling module that must be fresh after wf_reload_mcp, append it to the server_impl purge block and import it by public name at module top; do not rely on lazy or _load_script loading being stale, because they are not.
Validation rationale: The generated summary is reverification boilerplate. The real, durable fact from QA-DEL-2 was verified by a real perform_mcp_reload probe: _load_script modules are cached under a private _wavefoundry_ key and re-imported on reload because _script_cache is cleared, and a lazy import inside register_mcp_surface also re-runs during re-registration. What fails for them is test_reload_picks_up_every_added_module, which looks purge entries up by public name in sys.modules. Wave 1y0h2 adds two such modules, so this directly changes its implementation.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

On wf_reload_mcp, modules loaded through _load_script are re-imported (cached under a private _wavefoundry_ key; _script_cache is cleared), and a lazy import inside register_mcp_surface re-runs during re-registration, so neither is stale. The constraint is the 1y0h0 test test_reload_picks_up_every_added_module, which looks each purge-block entry after record_paths up by public name in sys.modules: a sibling module on the purge list must be appended to the purge block and imported by public name at the top of server_impl.py, or the test raises KeyError. test_mcp_tool_registry pins this placement for mcp_tool_registry.

## Evidence

- `QA-DEL-2`
- `ev-qa-del-2`
- `ev-qa-del-2-3`
- `1y0h1`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_gates_structure.py`
- `.wavefoundry/framework/scripts/tests/test_mcp_tool_registry.py`
