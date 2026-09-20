# Repaired defect QA-DEL-2

Owner: Engineering
Status: superseded
Last verified: 2026-09-19

Memory ID: `1yg1m-mem repaired-defect-qa-del-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-19
Updated: 2026-09-19
Source exploration cost: 384402
Source event: `finding:1y0h1:QA-DEL-2`
Validation: rewrite
Validated by: agent
Action delta: When adding a sibling module that must be fresh after wf_reload_mcp, append it to the server_impl purge block and import it by public name at module top; do not rely on lazy or _load_script loading being stale, because they are not.
Validation rationale: The generated summary is reverification boilerplate. The real, durable fact from QA-DEL-2 was verified by a real perform_mcp_reload probe: _load_script modules are cached under a private _wavefoundry_ key and re-imported on reload because _script_cache is cleared, and a lazy import inside register_mcp_surface also re-runs during re-registration. What fails for them is test_reload_picks_up_every_added_module, which looks purge entries up by public name in sys.modules. Wave 1y0h2 adds two such modules, so this directly changes its implementation.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1yf4y-mem reload-freshness-of-sibling-modules-purge-entry-plus-a-modul`
## Summary

Real defect fixed in wave 1y0h1: The original reproduction now agrees with the record; qa-reviewer clears itself.

## Evidence

- `QA-DEL-2`
- `ev-qa-del-2-3`
- `1y0h1`

## Targets

- `tests/test_mcp_tool_registry.py`
- `tests/test_lifecycle_gates_structure.py`
