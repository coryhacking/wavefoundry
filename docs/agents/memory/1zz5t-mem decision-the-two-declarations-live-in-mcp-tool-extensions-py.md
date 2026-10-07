# Decision: The two declarations live in `mcp_tool_extensions.py`, and…

Owner: Engineering
Status: active
Last verified: 2026-10-07

Memory ID: `1zz5t-mem decision-the-two-declarations-live-in-mcp-tool-extensions-py`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 95829
Source event: `decision-log:1zxnv-enh journal-migration-extension-points:680ee8fea999dad2`
Validation: promote
Validated by: agent
Action delta: Distribution extension points (journal templates, pre-migration hook) are declared in mcp_tool_extensions.py outside declared(), validated first inside the upgrade gate.
Validation rationale: EXTENSION_JOURNAL_TEMPLATES and EXTENSION_JOURNAL_PRE_MIGRATION_HOOK exist there; pre_docs_gate loads and validates them before any migration.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Decision (wave 1zyb3): The two declarations live in `mcp_tool_extensions.py`, and the hook is `"module:function"` in a declared helper module (coordinator decision).. Rationale: One declaration surface for distributions, reusing the existing helper-module and module-name rules. Kept outside `declared()` like `EXTENSION_SKILLS`, so the server and tool surface are unaffected..

## Evidence

- `1zxnv-enh journal-migration-extension-points`
- `1zyb3`

## Targets

- `mcp_tool_extensions.py`
- `upgrade_extensions.py`
