# Server-package census catches flat module names that focused test runs miss

Owner: Engineering
Status: active
Last verified: 2026-10-04

Memory ID: `1zp6w-mem server-package-census-catches-flat-module-names-that-focused`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 470529
Source event: `finding:1zqe4:DEL-F1`
Validation: promote
Validated by: agent
Action delta: Before finishing a change to server.py or framework tests, run test_server_package: never name a retired flat module (e.g. mcp_tool_registry) outside wf_server, and read moved-module sources through framework_files.source_path.
Validation rationale: Generated summary was empty of content. Two delivery findings in this wave (DEL-F1 in server.py, DEL-F8 in test_upgrade_wavefoundry) hit the same server-package census; both surfaced only in a full suite run, not in the focused files the implementers ran.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1zqe4 twice broke test_server_package censuses: DEL-F1 had server.py build_server call getattr(server_impl, "mcp_tool_registry"), which RetiredFlatNameCensusTests refuses, and DEL-F8 had new tests read SCRIPTS_ROOT / f"{name}.py", which test_no_source_read_of_a_moved_flat_path refuses. Both passed every focused file the implementer ran and failed only in the full suite. Fix pattern: expose a server_impl helper (e.g. _apply_render_pass) and look it up with getattr from the runner; read sources via framework_files.source_path or shipped_path. Include test_server_package in the focused run for any change touching server.py, wf_server/ or tests that read framework sources.

## Evidence

- `DEL-F1`
- `DEL-F8`
- `ev-del-f1-3`
- `ev-del-f8-3`
- `1zqe4`

## Targets

- `.wavefoundry/framework/scripts/tests/test_server_package.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
