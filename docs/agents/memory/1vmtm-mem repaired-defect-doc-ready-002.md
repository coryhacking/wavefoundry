# Repaired defect DOC-READY-002

Owner: Engineering
Status: superseded
Last verified: 2026-08-17

Memory ID: `1vmtm-mem repaired-defect-doc-ready-002`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `finding:1viyu:DOC-READY-002`
Validation: rewrite
Validated by: agent
Action delta: When a change alters an MCP tool's behavior, treat the tool's registered description (its docstring in server_impl.py) as a public carrier: name it in scope, edit it, and pin it with a semantic-anchor test that fails when the description no longer states the new behavior.
Validation rationale: Readiness finding DOC-READY-002 (docs-contract-reviewer, implementing session): the 1vitr plan's carrier census omitted the registered wf_audit_install description, which still said every lint error blocks; the repair added ownership across Requirements/Scope/ACs/Tasks and the delivered test_audit_install_public_carriers_pin_status_and_pending_lint_matrix pins the live registration (verified in the first delivery pass and again at reverification: WaveInstallAuditTests + TestMcpWrapperParameterExposure green). The draft summary was a plan-status sentence with no reusable action; the durable lesson is that registered tool descriptions are carriers that need ownership and an anchor test. RT-READY-003 is the same lesson from the red-team seat and is rejected as a duplicate of this rewrite.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1vlnj-mem a-registered-mcp-tool-description-is-a-public-carrier-own-it`
## Summary

Real defect fixed in wave 1viyu: The repaired plan assigns both runtime response changes and the separately exposed registration description.

## Evidence

- `DOC-READY-002`
- `ev-doc-ready-002-3`
- `1viyu`

## Targets

- `server_impl.py`
