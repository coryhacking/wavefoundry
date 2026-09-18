# Registry Readiness Clarification Review

Owner: Engineering
Status: active
Last verified: 2026-09-17

Phase: readiness. Context: `snapshot-crosswave-readiness-20260917-independent`. Scope: operator-authorized count, survivor-boundary and downstream composition clarifications. No implementation changes.

Standard red-team primer applied adversarial, constructive and simplicity stances; a separate docs-contract reviewer received it and independently reviewed the change and wave mirrors. The primer asked whether the full-public snapshot and implementation registry scopes agree, and whether the downstream split preserves introspection and reload ownership. Both reviewers approve after focused repair replay; agreement unanimous, no remaining bounded findings. The initial maximum severity was medium; no challenge round was needed.

The strongest challenge was a false timing invariant: hot reload does not remove and re-add runner survivors. Current `server.py:319–335` retains them while refreshing implementation tools. A bounded `python3 -B` probe built the real server with `build_handler` stubbed in a temporary root, then invoked `_refresh_mcp_tool_surface` with a spy around actual `register_mcp_surface`. An explicit assertion observed `wf_reload_mcp` already present at entry. The refresh returned no tool-refresh warnings; FastMCP emitted duplicate-resource notices during same-app re-registration. This known-bad control refuted the earlier absent-survivor assumption. No actual module reload, serving, or product edits occurred.

The amended Requirement 2 explicitly filters `RUNNER_TOOLS` at startup and reload. AC-2 uses exact name-set and tier equality against the roster minus survivors. The full-runner snapshot remains broader and includes survivor schemas. Requirement 5 and the wave watchpoint now preserve the AST census as response functions move while decorators stay in the root. The strongest alternative—explicit filtering with one introspection source—was adopted; it improves correctness without introducing another inventory.

Readiness approved for the amended plan. All five evidence-integrity checks are true for this review, including the actual-registration known-bad control. This is not proof of unimplemented registry or middleware behavior. Required delivery tests, module reload checks, golden invariance and specialist approvals remain outstanding; the coordinator owns typed readiness and lifecycle state.
