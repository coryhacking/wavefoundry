# Extension Tool Modules Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-23

## Red-team primer (standard depth)

Independent read-only context `ext_tools_primer`.

- **Strongest challenge:** on the reload path, `server._refresh_mcp_tool_surface` removes every tool and calls `register_mcp_surface`; an exception is converted to a `register_surface_failed` warning with no teardown. A hook failure after core `@mcp.tool` registration and before `mcp_tool_registry.apply_middleware(..., MIDDLEWARE)` would leave core tools served without the lifecycle lock, upgrade guard or cost wrapper. The existing prefix-contract `RuntimeError` shares that window.
- **Best alternative:** stage extension registration against a recording surface, validate, then install into the served table.
- **Primer questions:** (1) which schema call-compatibility compares, given `**kwargs` normalization runs after the hook; (2) whether `mcp_tool_extensions` itself is purged and how the AST purge census sees dynamic entries; (3) how write-tier extension tools fail fast when `publication_control.publication_block_reason` returns `None` for unknown names; (4) how imports are confined to the scripts directory; (5) whether duplicate detection compares names or objects.

Blocking findings and the bounded repair applied to the change doc before this receipt was published:

| Finding | Claim | Repair (change doc requirement) |
| --- | --- | --- |
| RT-READY-1 | Reload failure serves unwrapped core tools | Requirement 5: any pre-middleware failure empties the served table except reload survivors; AC-3 covers startup and reload |
| RT-READY-2 | Before/after name diff cannot see FastMCP-ignored duplicates | Requirement 2: staged registration records every attempt; Requirement 4 judges duplicates from recorded attempts |
| RT-READY-3 | One-directional prefix rule lets `wf`/`m` prefixes into core namespaces | Requirement 4: prefix invalid when either begins with the other; new names may match no core prefix |
| RT-READY-4 | Public-name import can resolve outside the scripts directory | Requirement 4: module file must sit directly in the framework scripts directory; Requirement 2: flat single-file modules |

Primer questions answered in the repair: normalized-schema compatibility with the typed unknown-argument diagnostic (Requirement 3); declaration on the purge list, fresh declaration read, census accounting (Requirement 8); separate checkpoint path for write-tier extension tools (Requirement 7); staging records attempts, so identity games in the served table are impossible during staging, and in-place rebinding of core tools is a documented trust boundary (Requirement 7). `publication_control.py` and `server.py` added to Serialization Points.

The primer findings were repaired within the bounded readiness pass and are recorded here rather than as typed finding chains; the focused lanes below verify each repair.

## Focused verification round 1

Independent read-only contexts: `ext_tools_code_qa` (code-reviewer, qa-reviewer), `ext_tools_arch_sec` (architecture-reviewer, security-reviewer), `ext_tools_docs` (docs-contract-reviewer, rotating seat). All confirmed RT-READY-1 to 4 repairs close their defects. Remaining blockers, escalated to the operator per the bounded readiness protocol:

| Finding | Claim | Repair |
| --- | --- | --- |
| CODE-READY-1 / DOCS-READY-1 | Returning the typed unknown-argument diagnostic cannot be checked at registration without invoking extension code | Structural compatibility on the normalized schema (closed schema via `**kwargs`, parameter superset, no newly required parameter); diagnostic is an extension obligation (Requirement 3) |
| ARCH-READY-1 | Overriding `wf_reload_mcp` fails at startup but passes on reload | Runner tools are never override targets (Requirements 3, 4) |
| SEC-READY-1 | Renderer and upgrade merge declared tiers without validation | Roster runs the declaration's validation helpers and raises before rendering (Requirement 6, AC-3) |
| DOCS-READY-2 | Spec prefix table disagrees with `MCP_TOOL_PREFIXES` | Table corrected, constant named as the rule's source (Requirement 10) |

Operator decision 2026-09-23: one more bounded repair and one focused verification by the blocking lanes. Agreed non-blocking notes folded into the same repair.
