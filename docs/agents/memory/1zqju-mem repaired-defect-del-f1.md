# Repaired defect DEL-F1

Owner: Engineering
Status: superseded
Last verified: 2026-10-04

Memory ID: `1zqju-mem repaired-defect-del-f1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 470529
Source event: `finding:1zqe4:DEL-F1`
Validation: rewrite
Validated by: agent
Action delta: Before finishing a change to server.py or framework tests, run test_server_package: never name a retired flat module (e.g. mcp_tool_registry) outside wf_server, and read moved-module sources through framework_files.source_path.
Validation rationale: Generated summary was empty of content. Two delivery findings in this wave (DEL-F1 in server.py, DEL-F8 in test_upgrade_wavefoundry) hit the same server-package census; both surfaced only in a full suite run, not in the focused files the implementers ran.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zp6w-mem server-package-census-catches-flat-module-names-that-focused`

## Summary

Real defect fixed in wave 1zqe4: resolved

## Evidence

- `DEL-F1`
- `ev-del-f1-3`
- `1zqe4`

## Targets

- `server.py`
