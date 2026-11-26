# A registered MCP tool description is a public carrier; census it and pin it

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24asu-mem a-registered-mcp-tool-description-is-a-public-carrier-census`
Kind: `review_finding`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 3068146
Supersedes: `1vlnj-mem a-registered-mcp-tool-description-is-a-public-carrier-own-it`

## Summary

When a change alters what an MCP tool does, list the tool's registered description (its docstring in wf_server/server_impl.py, shown to hosts in the live tool list) among the change's carriers, with the same standing as the tool-surface contract, the seeds and the templates. Edit it, and pin it with a test on its key wording rather than a promise in prose. The tool-surface golden excludes descriptions, so nothing else catches drift. In wave 1viyu readiness (DOC-READY-002, RT-READY-003), the plan for wf_audit_install's status matrix and pending_lint left the docstring saying every lint error blocks. The repair added test_audit_install_public_carriers_pin_status_and_pending_lint_matrix, which reads the live registration.

## Evidence

- `DOC-READY-002`
- `ev-doc-ready-002-3`
- `RT-READY-003`
- `1viyu`
- `test_server_tools_retrieval.TestMcpWrapperParameterExposure.test_audit_install_public_carriers_pin_status_and_pending_lint_matrix`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `docs/architecture/contracts/mcp-tool-surface.md`
