# Fresh Installs Resolve MCP 2 and Cannot Start the Server

Change ID: `1z825-bug fresh-install-resolves-mcp-2`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-27
Wave: 1z822 hook-lock-and-setup-safety

## Rationale

`setup_requirements.REQUIRED_IMPORTS` declares `mcp[cli]` with no version bound. `mcp` 2.0.0 was published on 2026-07-28 and 2.2.0 on 2026-09-07, both older than setup's 21-day `uv --exclude-newer` package-age guard, so a fresh `wf setup` today resolves `mcp` 2.2.0. In 2.x `mcp.server.fastmcp` no longer exists (FastMCP was renamed `MCPServer`); `server.py` imports `from mcp.server.fastmcp import FastMCP`, so the server cannot start on a new workstation. Verified on 2026-09-27 by installing `mcp[cli]==2.2.0` in a scratch environment: the import fails with `ModuleNotFoundError`, and the error text itself recommends pinning `mcp<2`. Existing installs are unaffected only because they resolved 1.x before the guard admitted 2.x (this repository runs 1.28.1). (RFC section 7, B7.)

Separately, the package-age guard is documented only in a docstring. It applies when setup installs through `uv`; the plain-pip fallback (when `uv` cannot be bootstrapped) prints a warning, and a tool environment built by hand never passes through it. Operators have no documented statement of that. (RFC section 7, B9.)

## Requirements

1. **Pin MCP below 2.** Every declaration of the MCP dependency declares `mcp[cli]<2`: `setup_requirements.REQUIRED_IMPORTS` and the `dependencies` list in `pyproject.toml`. Because setup and setup readiness both treat an installed version outside a declared specifier as missing, an environment that already resolved 2.x is reported as needing setup and `wf setup` (or an upgrade's dependency sync) reinstalls a 1.x release; a 1.x environment is untouched.
2. **Document the guard.** `docs/contributing/build-and-verification.md` states, next to the setup instructions, that dependencies installed by `wf setup` through `uv` exclude packages published in the last 21 days, that the plain-pip fallback and hand-built environments do not get that protection, and that `mcp` is pinned below 2 until the server migrates to the 2.x API.

## Scope

**Problem statement:** a fresh setup installs an MCP release the server cannot import, and the supply-chain guard's limits are undocumented.

**In scope:**

- the `mcp[cli]` requirement and the tests that name it;
- the build-and-verification setup text.

**Out of scope:**

- migrating the server to the `mcp` 2.x API (a separate change);
- publishing a lock file.

## Acceptance Criteria

- [x] AC-1: the declared MCP requirement excludes 2.x; with an installed `mcp` 2.x the setup dependency probe and setup readiness each report it as missing, and with 1.x they do not.
- [x] AC-2: `docs/contributing/build-and-verification.md` states the package-age guard, where it does not apply, and the MCP pin.
- [x] AC-3: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] Pin `mcp[cli]<2` in `setup_requirements.py`; update tests that name the requirement.
- [x] Tests for AC-1 through the real readiness and setup probes (fake metadata for 2.x and 1.x).
- [x] Build-and-verification text; CHANGELOG `[Unreleased]` Fixed bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Setup pin | implementer | readiness | Single write owner; MCP code tools for reads |
| Review | combined reviewer | Setup pin | One combined reviewer |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_requirements.py`, `.wavefoundry/framework/scripts/tests/test_setup_index.py`, `.wavefoundry/framework/scripts/tests/test_setup_readiness.py`, `docs/contributing/build-and-verification.md`
- `pyproject.toml` and `CHANGELOG.md` (the changelog is shared by all three changes in this wave)

## Affected Architecture Docs

`N/A`: a dependency bound and an operator note; no module boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Fresh installs cannot start the server |
| AC-2 | important | Operators should know the guard's limits |
| AC-3 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Implemented: `mcp[cli]<2` in `REQUIRED_IMPORTS` and `pyproject.toml`; tests drive the real readiness census with 2.2.0 and 1.28.1 metadata and the real setup probe against the installed `mcp`; build-and-verification states the package-age guard, where it does not apply, and the pin. Scratch mutant removing the pin fails a test | `test_setup_readiness`, `test_setup_index` |
| 2026-09-27 | Readiness round 1: no blocking finding here. Folded in: `pyproject.toml` also declares unbounded `mcp[cli]`, so the pin covers every declaration; the CHANGELOG bullet is the operator-facing surface for the guard note, since `build-and-verification.md` is this repository's contributor document. With a constraint present, `_satisfies` applies its numeric version parse to `mcp` (plain numeric releases; low risk) | readiness review |
| 2026-09-27 | Planned from RFC section 7 (B7, B9). Verified: `REQUIRED_IMPORTS` has unbounded `mcp[cli]`; PyPI dates put `mcp` 2.0.0 and 2.2.0 outside the 21-day guard; `mcp` 2.2.0 has no `mcp.server.fastmcp`; `_missing_in_venv` and `setup_readiness._dependencies` both parse `name[extra]<spec>` and flag a violating version | scratch-venv import probe, PyPI JSON, `code_read` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | Pin `<2` now; migrate to the 2.x API later | Restores fresh installs immediately with a one-line change that existing pin logic already enforces | Migrate now (large, touches every tool registration); exact pin `==1.28.1` (blocks 1.x security fixes) |
| 2026-09-27 | Document the guard rather than ship a lock file | The guard works for the supported path; a lock file is a larger policy change | Publish a pinned lock (RFC option) |

## Risks

| Risk | Mitigation |
| --- | --- |
| 1.x stops receiving fixes | The 2.x migration is tracked separately |
| The pin changes the setup fingerprint and makes targets report `setup_inputs_changed` | Intended: those targets should rerun setup to converge |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
