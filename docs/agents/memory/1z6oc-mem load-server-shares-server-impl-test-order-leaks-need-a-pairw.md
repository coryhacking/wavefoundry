# load_server shares server_impl; test-order leaks need a pairwise single-process sweep

Owner: Engineering
Status: active
Last verified: 2026-09-28

Memory ID: `1z6oc-mem load-server-shares-server-impl-test-order-leaks-need-a-pairw`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-09-28
Updated: 2026-09-28
Source exploration cost: 56010
Source event: `finding:1z8tx:cold-site-preload-breaks-nested-ordering`
Validation: promote
Validated by: agent
Action delta: Before fixing a test-order leak, probe _script_cache and sys.modules identity across load_server calls and run a pairwise single-process sweep of all layout-patching files, rather than reasoning from what load_server appears to reset.
Validation rationale: The first repair assumed load_server empties _script_cache; an identity probe showed it does not, and the preload broke nested then cold_sites. The drafted summary ('Resolved.') carried no lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

server_tools_support.load_server re-executes only server.py, so server_impl and its _script_cache persist across calls; only the FIRST server_impl import evicts record_paths from sys.modules, leaving spec-loaded modules (e.g. a test's docs_gardener) holding an older copy that patch_layout misses unless passed via modules=. Modules that capture layout at import (_tag_utils._DEFAULT_WAVES_PREFIX) freeze whatever layout the first importer patched. run_tests.py isolates files per process, so these leaks only show under single-process unittest; verify an isolation fix by running every layout-patching or load_server file before the fixed module in one interpreter, not just the reported pair.

## Evidence

- `cold-site-preload-breaks-nested-ordering`
- `ev-cold-site-preload-breaks-nested-ordering-3`
- `1z8tx`

## Targets

- `tests/test_record_layout_cold_sites.py`
- `tests/server_tools_support.py`
- `tests/record_layout_support.py`
- `_tag_utils.py`
