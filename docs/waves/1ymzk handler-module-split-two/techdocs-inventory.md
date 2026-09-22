# TechDocs handler move inventory

Owner: Engineering
Status: active
Last verified: 2026-09-21

## Baseline and boundary

Implementation preparation for `1ymzi-ref techdocs-handler-module`; no source edits. Source `server_impl.py` SHA-256 is `2ab7e97732dc7491471c4a5c77b3c2b846f684ca8107ecef8ccbad07e0c5c651`. MCP `code_outline` and `code_references` independently rechecked the live definitions and callers. The memory brief identified the server file playbook and response-envelope constraints. No runtime behavior, transport registration, response cap, or provider policy changes are authorized here.

| Symbol | Current source lines | Disposition | Readers / callers |
| --- | --- | --- | --- |
| `TECHDOCS_AUDIT_FINDING_CAP` | 12735 | Move; re-export | `_bounded_techdocs_payload`; `test_server_tools.TechdocsAuditToolTests` through `server_impl` |
| `TECHDOCS_AUDIT_SURVIVOR_CAP` | 12736 | Move; re-export | `_bounded_techdocs_payload`; `test_server_tools.TechdocsAuditToolTests` through `server_impl` |
| `_bounded_techdocs_payload` | 12739–12776 | Move; re-export | `wf_techdocs_audit_response` |
| `wf_techdocs_audit_response` | 12779–12835 | Move; re-export | Decorated `wf_techdocs_audit` closure; eleven calls in `TechdocsAuditToolTests`; advisory-site census names |
| `wf_techdocs_baseline_response` | 12838–12995 | Move; re-export | Decorated `wf_techdocs_baseline` closure; fixture `_call` in `TechdocsBaselineToolTests`; `inspect.getsource` pin; advisory-site census names |

The source region is contiguous. Move the definitions and caps into `techdocs_handlers.py`. A single module-top rebinding import in `server_impl.py` preserves the five names, while a plain imported module name enters the existing reload purge set. Leave all decorated closures inside `register_mcp_surface` byte-identical.

## Dependencies

Direct imports in the new module: `re`, `pathlib.Path`, `typing.Any`, `typing.Optional`, and `lifecycle_gate_support._diagnostic`. Retain existing function-local imports of `techdocs_audit_lib` and `render_agent_surfaces`. Do not introduce `_load_script` calls.

The two response functions gain function-local `import server_impl`. Their shared helper reads become `server_impl._response`, `server_impl._attach_lint_to_response`, and `server_impl._trigger_background_index_refresh_for_paths`. Deferred `McpRepoCache` annotation becomes `server_impl.McpRepoCache`; ordinary typing and Path references remain local direct imports. `_bounded_techdocs_payload` needs no composition-root dependency.

## Named test edits and proof

- `test_handler_modules.py`: add `techdocs_handlers` with tools `wf_techdocs_audit` and `wf_techdocs_baseline` to `FAMILIES`; update the count-specific docstring and manifest test name; generalize the actual scratch reload proof to graph and TechDocs. Memory joins that same template only after its separately reviewed inventory.
- `test_server_tools.py`: existing audit/renderer producer tests stay intact. The dry-run baseline test already compares SHA-256 maps; add exact pre/post byte maps around the same real producer call, preserving existing assertions.
- `test_server_tools_lifecycle.py`: import `techdocs_handlers` and add it to the advisory-site owner tuple. The expected three TechDocs advisory sites remain exactly unchanged.
- `test_render_agent_surfaces.py`: add `techdocs_handlers.py` to the existing baseline-renderer allowlist and repoint its positive source-presence assertion; retain the CLI entry, renderer exclusions and negative census.

Verification: normalized AST equivalence for the moved definitions (only the named qualification and local-import edits removed), byte-equality of `register_mcp_surface`, unchanged ninety-tool golden fixture and registry parity, existing producer tests, dry-run byte preservation, generated manifest, import-derived purge census and actual reload through the registered public callable. No golden corpus anchor names a TechDocs definition; no measured evaluator root calls one. Do not add the module to `PRODUCTION_RETRIEVAL_MODULES`; the before/after receipt obligation still applies because `server_impl.py` remains a member.

## Sequence

1. Coordinator records a valid before benchmark and confirms activation before source edits.
2. Implement and verify only TechDocs, then obtain the independent review checkpoint.
3. Only afterward publish and independently review the memory inventory, then move memory.

The privately prepared memory inventory remains outside the repository until that checkpoint. Existing generated-document edits and the previously added architecture topology line are preserved.
