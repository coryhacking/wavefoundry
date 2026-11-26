# load_server shares one server_impl across tests; verify layout-isolation fixes in one interpreter

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24aex-mem load-server-shares-one-server-impl-across-tests-verify-layou`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 56010
Supersedes: `1z6oc-mem load-server-shares-server-impl-test-order-leaks-need-a-pairw`

## Summary

When you fix a test-order leak involving the record layout or load_server, verify the fix by running every layout-patching or load_server test file before the fixed module in one interpreter, not just the reported pair. tests/server_tools_support.py load_server re-executes only server.py, so server_impl and its _script_cache persist across calls. Only the first server_impl import evicts record_paths from sys.modules, so a spec-loaded module (for example a test's docs_gardener) can hold an older copy that patch_layout misses unless it is passed through modules=. A module that captures the layout at import freezes whatever layout the first importer patched. Wave 1z8tz removed the _tag_utils and retrieval_eval captures, and review_policy.SCAFFOLD_DOCS remains, classified by the census test. run_tests.py isolates files per process, so these leaks show only under single-process unittest (cold-site-preload-breaks-nested-ordering, wave 1z8tx).

## Evidence

- `cold-site-preload-breaks-nested-ordering`
- `ev-cold-site-preload-breaks-nested-ordering-3`
- `1z8tx`
- `1z8tz`

## Targets

- `.wavefoundry/framework/scripts/tests/test_record_layout_cold_sites.py`
- `.wavefoundry/framework/scripts/tests/server_tools_support.py`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/_tag_utils.py`
