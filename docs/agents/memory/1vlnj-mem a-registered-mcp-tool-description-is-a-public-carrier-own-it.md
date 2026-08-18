# A registered MCP tool description is a public carrier: own it and pin it when the tool's behavior changes

Owner: Engineering
Status: active
Last verified: 2026-08-17

Memory ID: `1vlnj-mem a-registered-mcp-tool-description-is-a-public-carrier-own-it`
Kind: `review_finding`
Confidence: 0.85
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `finding:1viyu:DOC-READY-002`
Validation: promote
Validated by: agent
Action delta: When a change alters an MCP tool's behavior, treat the tool's registered description (its docstring in server_impl.py) as a public carrier: name it in scope, edit it, and pin it with a semantic-anchor test that fails when the description no longer states the new behavior.
Validation rationale: Readiness finding DOC-READY-002 (docs-contract-reviewer, implementing session): the 1vitr plan's carrier census omitted the registered wf_audit_install description, which still said every lint error blocks; the repair added ownership across Requirements/Scope/ACs/Tasks and the delivered test_audit_install_public_carriers_pin_status_and_pending_lint_matrix pins the live registration (verified in the first delivery pass and again at reverification: WaveInstallAuditTests + TestMcpWrapperParameterExposure green). The draft summary was a plan-status sentence with no reusable action; the durable lesson is that registered tool descriptions are carriers that need ownership and an anchor test. RT-READY-003 is the same lesson from the red-team seat and is rejected as a duplicate of this rewrite.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1viyu readiness (DOC-READY-002, RT-READY-003): the plan that changed wf_audit_install's status matrix and added pending_lint listed seeds, templates, and the tool-surface doc as carriers but not the registered tool description in server_impl.py, whose docstring still said every lint error blocks; an agent reading the live tool list would have been told the old contract. Repaired by owning the description in the change doc and shipping test_audit_install_public_carriers_pin_status_and_pending_lint_matrix, which reads the live registration and fails when it stops naming the seven statuses and the pending_lint carriers. Rule: whenever a change alters what a tool does, the docstring shown to hosts is a carrier with the same standing as the spec and the seeds; census it, edit it, and hold it with a semantic-anchor test rather than a prose promise.

## Evidence

- `DOC-READY-002`
- `ev-doc-ready-002-3`
- `RT-READY-003`
- `test_server_tools.TestMcpWrapperParameterExposure.test_audit_install_public_carriers_pin_status_and_pending_lint_matrix`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/specs/mcp-tool-surface.md`
