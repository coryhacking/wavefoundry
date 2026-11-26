# Journal-migration extension points live in mcp_tool_extensions.py

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bum-mem journal-migration-extension-points-live-in-mcp-tool-extensio`
Kind: `decision`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 95829
Supersedes: `1zz5t-mem decision-the-two-declarations-live-in-mcp-tool-extensions-py`

## Summary

When a distribution needs to declare journal templates or a pre-migration hook for the upgrade's journal migration, declare them in .wavefoundry/framework/scripts/mcp_tool_extensions.py as EXTENSION_JOURNAL_TEMPLATES and EXTENSION_JOURNAL_PRE_MIGRATION_HOOK (a 'module:function' in a declared helper module), outside declared() like EXTENSION_SKILLS. Why: decision of wave 1zyb3; one declaration surface for distributions reuses the helper-module and module-name rules, upgrade_extensions.py validates them first inside the upgrade gate, and keeping them out of declared() leaves the server and tool surface unaffected.

## Evidence

- `1zxnv-enh journal-migration-extension-points`
- `1zyb3`

## Targets

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
