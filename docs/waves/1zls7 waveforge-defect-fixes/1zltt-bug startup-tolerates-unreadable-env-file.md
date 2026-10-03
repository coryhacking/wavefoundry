# MCP Startup Tolerates an Unreadable .env File

Change ID: `1zltt-bug startup-tolerates-unreadable-env-file`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-02
Wave: 1zls7 waveforge-defect-fixes

## Rationale

`build_server` in `.wavefoundry/framework/scripts/server.py` constructs `FastMCP("wavefoundry_mcp")`. In the installed mcp 1.x (1.28.1 in the tool venv, `mcp[cli]<2` pinned in `setup_requirements.py`), `FastMCP.__init__` builds `mcp.server.fastmcp.server.Settings`, a pydantic-settings `BaseSettings` whose `model_config` sets `env_prefix="FASTMCP_"` and `env_file=".env"`. The env file path is relative to the process working directory, which is whatever directory the agent host launched the server from, not the repository.

Waveforge reported, and a scratch reproduction on 2026-10-02 confirmed, that a `.env` the server process cannot read crashes startup: with a mode-000 `.env` in the working directory, `FastMCP("x")` raises `PermissionError: [Errno 13] Permission denied: '.env'` from the pydantic-settings dotenv source; a `.env` that is not valid UTF-8 raises `UnicodeDecodeError` the same way. The server never starts, and the error names a file the operator did not know the server reads. A `.env` belonging to an unrelated project (a common file in a home or workspace directory) is enough.

The report also said a stray `.env` with `FASTMCP_` keys silently changes server settings. In mcp 1.28.1 this was not reproduced: `FastMCP.__init__` passes every `Settings` field explicitly, and pydantic-settings gives initialiser arguments priority over dotenv values, so `FASTMCP_LOG_LEVEL`, `FASTMCP_DEBUG`, `FASTMCP_PORT`, `FASTMCP_WARN_ON_DUPLICATE_TOOLS`, a nested `FASTMCP_AUTH__ISSUER_URL` and `FASTMCP_TRANSPORT_SECURITY__ENABLE_DNS_REBINDING_PROTECTION` in a `.env` all had no effect. That holds only while every field stays an explicit argument in the installed release, so this change pins it with a test instead of relying on it.

Wavefoundry never configures FastMCP through a `.env` (it runs over stdio with settings fixed in code), so the server should not read one at all.

## Requirements

1. **The server never reads a `.env` for FastMCP settings.** Before `build_server` constructs `FastMCP`, the dotenv source of mcp's FastMCP `Settings` is disabled (decision: set `env_file` to `None` in `mcp.server.fastmcp.server.Settings.model_config`, which pydantic-settings consults at each instantiation; verified in the tool venv on 2026-10-02 that this makes construction succeed with a mode-000 `.env` present). The step lives in one small helper in `server.py` called from `build_server`, with a comment naming the reason and the mcp version range it was verified against.
2. **Version tolerance.** If a future mcp 1.x no longer exposes `Settings` at that path, or its `model_config` has no `env_file` key, the helper does nothing and startup proceeds; it never raises. The helper does not touch any other setting, the process environment, or the working directory.
3. **Environment variables are unchanged.** `FASTMCP_`-prefixed process environment variables are not part of this change; the server's behaviour with them stays whatever mcp gives it (initialiser arguments already take priority in 1.28.1).
4. **Scope of the process-wide change.** The `model_config` edit is process-wide for mcp's `Settings` class. The server process is the only FastMCP owner in it; the helper is idempotent across `wf_reload_mcp` and repeated `build_server` calls in tests.
5. **Docs.** The CHANGELOG gains an Unreleased `### Fixed` bullet: MCP startup no longer reads a `.env` file in the working directory, so an unreadable or undecodable one no longer stops the server.

## Scope

**Problem statement:** an unreadable or undecodable `.env` in the host's working directory crashes MCP startup, and the server reads a file it has no use for.

**In scope:**

- `server.py`: the helper and its call in `build_server`.
- A new test module (for example `tests/test_server_env_file.py`) that runs `build_server` (or the helper plus a `FastMCP` construction) in a subprocess whose working directory holds the `.env` under test, using the tool-venv interpreter, and skips when `mcp` is not importable.
- The CHANGELOG bullet.

**Out of scope:**

- Upgrading mcp or changing the `mcp[cli]<2` pin.
- Any other pydantic-settings source (process environment, secrets directory).
- The dashboard server and other entry points that do not construct `FastMCP` (`server.py` `build_server` is the only `FastMCP(` construction in the framework scripts, checked 2026-10-02).

## Acceptance Criteria

- [x] AC-1: With a `.env` in the server's working directory that the process cannot read (POSIX: mode 000, skipped when running as root; Windows: a deny-read ACL set with `icacls`, skipped when that cannot be applied), the server builds and registers its tools; the same test fails against `server.py` as of 2026-10-02.
- [x] AC-2: With a `.env` that is not valid UTF-8, the server builds; this fails before the change.
- [x] AC-3: With a `.env` setting `FASTMCP_LOG_LEVEL=DEBUG`, `FASTMCP_DEBUG=true`, `FASTMCP_PORT=9999` and `FASTMCP_WARN_ON_DUPLICATE_TOOLS=false`, the built server's `settings` equal those of a server built with no `.env` present.
- [x] AC-4: After the helper runs, `mcp.server.fastmcp.server.Settings.model_config["env_file"]` is `None`; with the `Settings` attribute or the `env_file` key absent (patched), the helper returns without raising and `build_server` still builds. The in-process test restores `Settings.model_config` with `patch.dict` so its mutation does not leak into other tests.
- [x] AC-5: The CHANGELOG has the Unreleased bullet.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write the failing-first subprocess tests (unreadable, undecodable, FASTMCP_ keys) with a temporary working directory.
- [x] Add the helper to `server.py` and call it from `build_server` before constructing `FastMCP`.
- [x] Add the version-tolerance test (AC-4).
- [x] Add the CHANGELOG bullet.
- [x] Run the change's suites and docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| env-file | implementer | none | server.py and a new test module |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: one startup step in `server.py`; no boundary, flow or verification change.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported crash. |
| AC-2 | important | Same crash through a decode error. |
| AC-3 | important | Pins that a stray `.env` cannot change settings, which today holds only by mcp's argument order. |
| AC-4 | required | The fix must never itself stop startup on another mcp 1.x. |
| AC-5 | nice-to-have | Release notes. |
| AC-6 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Implemented. `server.py` gains `_fastmcp_settings_class()` (returns `mcp.server.fastmcp.server.Settings` or None) and `_disable_fastmcp_dotenv()` (sets `model_config["env_file"] = None` only when the class has a dict `model_config` with an `env_file` key; otherwise a no-op; never raises; idempotent), called in `build_server` immediately before `FastMCP("wavefoundry_mcp")`, with a comment naming the reason and mcp 1.28.1 / pydantic-settings 2.14.2. New `tests/test_server_env_file.py` (7 tests): AC-1 `test_ac1_unreadable_env_file_does_not_stop_startup` (subprocess `build_server` with a mode-000 `.env` in its working directory; Windows deny-read ACL via `icacls`; skips as root or when the deny cannot be applied); AC-2 `test_ac2_undecodable_env_file_does_not_stop_startup`; AC-3 `test_ac3_fastmcp_keys_in_env_file_do_not_change_settings` (settings dump equals the no-`.env` build); AC-4 `test_helper_sets_env_file_to_none`, `test_helper_is_a_no_op_without_the_env_file_key`, `test_helper_is_a_no_op_without_the_settings_attribute`, `test_build_server_still_builds_without_the_settings_attribute` (all restore `Settings.model_config` with `patch.dict`). Failing first (before the helper): AC-1 failed with `PermissionError: [Errno 13] Permission denied: '.env'`, AC-2 with `UnicodeDecodeError`, the four AC-4 tests errored (no helper); AC-3 passed before the change as planned (it pins mcp's argument priority). After: 7 of 7 pass; neighbouring `test_server_package.py` (31), `test_tool_surface_golden.py` (13), `test_handler_modules.py` (13), `test_change_kinds.py` (28) pass. Mutations in a scratch copy: dropping the `build_server` call fails AC-1 and AC-2; replacing the guarded lookup with an unconditional `settings_cls.model_config["env_file"] = None` fails `test_helper_is_a_no_op_without_the_env_file_key`; inverting the key test fails AC-1, AC-2 and two AC-4 tests. Gapfill: one shell `grep -n` over `server.py` to confirm its `typing.Any` import (a known file, trivial lookup). Coordinator suite run (scratch copy of the whole wave tree): `run_tests.py --no-cache` 10689 tests across 156 files OK (34 skipped); `--profile declared` 10689 OK; `--profile second` 10686 run, its one failure was a 1zltr fixture (fixed, the file then passed under the second profile). | Scratchpad `1zls7-1zltt-failing-first.txt`, `1zls7-1zltt-after.txt`, `1zls7-1zltt-mut/`, 2026-10-02 |
| 2026-10-02 | Planned. In the tool venv (mcp 1.28.1, pydantic-settings 2.14.2): `Settings.model_config` has `env_prefix "FASTMCP_"` and `env_file ".env"`; `FastMCP.__init__` passes every `Settings` field explicitly; a mode-000 `.env` raises `PermissionError` and a non-UTF-8 `.env` raises `UnicodeDecodeError` at construction; `FASTMCP_` keys in a readable `.env` (flat and nested) had no effect; setting `model_config["env_file"] = None` before construction let it succeed with the unreadable file present. | Scratch probes under the session scratchpad, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Disable the dotenv source on mcp's `Settings` class before constructing `FastMCP` | `FastMCP.__init__` in 1.x exposes no argument to pass `_env_file` or settings; Wavefoundry never wants a `.env`; verified to fix the crash | Catch the error and retry (still needs a way to disable the source); change the working directory around construction (affects the whole process and other relative paths); patch the module's `Settings` name with a subclass (more invasive) |
| 2026-10-02 | Readiness amendment: AC-4's in-process test restores `model_config` with `patch.dict` | Readiness review: the helper mutates a process-wide class attribute, which would leak into later tests in the same process | Restore by hand in `tearDown` (rejected: misses exception paths) |
| 2026-10-02 | Pin, rather than fix, the FASTMCP_ key behaviour | Not reproduced in 1.28.1; disabling the env file also removes the path in releases where it would apply | No test |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A future mcp 1.x moves or renames `Settings` | The helper is a no-op then (AC-4), and AC-1 would show the crash returning in that release |
| Windows: no mode-000 equivalent | The Windows case uses a deny-read ACL on the file and skips when it cannot be set; the helper itself is platform-independent. macOS, Linux and WSL2 use mode 000 (skipped as root, where permissions do not deny reads) |
| The test needs the real mcp package | It runs under the tool-venv interpreter and skips when `mcp` is not importable, like `test_eight_lifecycle_tool_schemas_match_the_golden_fixture` |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
