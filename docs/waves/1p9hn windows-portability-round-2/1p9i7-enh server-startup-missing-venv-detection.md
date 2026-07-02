# Server Startup: Missing Venv Detection

Change ID: `1p9i7-enh server-startup-missing-venv-detection`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-02
Wave: `1p9hn windows-portability-round-2`

## Rationale

When the tool venv at `~/.wavefoundry/venv` is missing or its deps are broken, `server.py` crashes with an unhandled `ImportError` before the MCP JSON-RPC handshake completes. The agent host receives an opaque `-32000` internal error with no actionable guidance. The operator (or agent) must already know to run `wf setup` — there is no signal in the failure itself.

`venv_bootstrap.activate_tool_venv()` is intentionally a silent no-op when the venv does not exist (so `wf setup` itself is not blocked). This means the gap must be closed in `server.py` after `activate_tool_venv()` returns: detect the missing venv or failed import, print a clear stderr message pointing to `wf setup`, and exit with code 2 — matching the pattern already used for the Python version mismatch case in `venv_bootstrap.py`.

## Requirements

1. When `server.py` starts and the tool venv Python does not exist, print a clear message to stderr — "run `wf setup`" — and exit with code 2 before attempting any heavy import.
2. When the venv exists but `import server_impl` fails (e.g. a broken or incomplete venv), catch the `ImportError`, print a similarly actionable stderr message, and exit with code 2.
3. All stderr messages must be printed to `sys.stderr` only — never to stdout — to avoid corrupting the JSON-RPC framing byte stream.
4. The `--dry-run` path must surface these failures identically (it runs the same module-level code path).
5. No changes to the MCP tool surface, `.mcp.json`, or transport configuration.

## Scope

**Problem statement:** MCP server startup failures caused by a missing or broken tool venv produce opaque `-32000` JSON-RPC errors with no actionable guidance for the operator or agent.

**In scope:**

- `.wavefoundry/framework/scripts/server.py`: add venv-missing check after `activate_tool_venv()` and try/except around `import server_impl`
- A test covering the new failure paths (mock `tool_venv_python` absent + mock `ImportError` on `server_impl`)

**Out of scope:**

- Changes to `.mcp.json`, the MCP transport, or the registered tool surface
- Auto-running `wf setup` from within the server (the server must not modify the environment)
- Changes to `venv_bootstrap.py` (the no-op behavior for missing venv is correct for setup entry points)

## Acceptance Criteria

- [x] AC-1: When the tool venv Python does not exist, `server.py` exits with code 2 and prints a message containing "wf setup" to stderr before any `ImportError` can occur.
- [x] AC-2: When the venv exists but `import server_impl` raises `ImportError`, `server.py` exits with code 2 and prints a message containing "wf setup" to stderr.
- [x] AC-3: Neither message writes to stdout.
- [x] AC-4: Framework tests pass (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Tasks

- [x] In `server.py`, after `venv_bootstrap.activate_tool_venv()`, add a venv-missing guard: if `venv_bootstrap.tool_venv_python()` does not exist, print to stderr and `sys.exit(2)`.
- [x] Wrap `import server_impl` in a `try/except ImportError` block; on failure print to stderr and `sys.exit(2)`.
- [x] Add a test in `.wavefoundry/framework/scripts/tests/` covering both failure paths.

## Agent Execution Graph

| Workstream   | Owner       | Depends On | Notes                          |
| ------------ | ----------- | ---------- | ------------------------------ |
| server-guard | implementer | —          | server.py edits + test         |

## Serialization Points

- N/A (single-file change + new test)

## Affected Architecture Docs

N/A — this change is confined to the server startup module with no boundary, flow, or tool-surface impact.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale                                                      |
| ---- | -------- | -------------------------------------------------------------- |
| AC-1 | required | Primary fix — venv missing is the most common failure mode     |
| AC-2 | required | Secondary failure mode — broken/incomplete venv                |
| AC-3 | required | Stdout purity is a hard MCP transport constraint               |
| AC-4 | required | Regression safety for the framework test suite                 |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-07-02 | Planned |          |

## Decision Log

| Date       | Decision                                              | Reason                                                                    | Alternatives                                           |
| ---------- | ----------------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------ |
| 2026-07-02 | Fail-fast in server.py, not in venv_bootstrap.py      | venv_bootstrap no-op is intentional; server.py is the right detection site | Could add server-context flag to venv_bootstrap        |
| 2026-07-02 | No MCP surface changes (exit before handshake)        | Enterprise MCP config is locked; any surface change requires re-approval   | Could emit structured MCP error response               |

## Risks

| Risk                                             | Mitigation                                                                 |
| ------------------------------------------------ | -------------------------------------------------------------------------- |
| sys.exit(2) at module level runs during --dry-run | Correct and desired — dry-run should also surface the missing-venv failure |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
