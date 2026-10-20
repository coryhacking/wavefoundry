# An environment switch to turn off MCP startup installs

Change ID: `2136x-enh mcp-startup-install-opt-out`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-19
Wave: `2136z upgrade-and-startup-field-fixes`

## Rationale

MCP startup installs missing or version-incompatible declared dependencies through uv (`server._startup_install_gate_unguarded`, called from `server.py`; specs from `setup_readiness.startup_install_specs`; deferrable ones in the background). Waveforge accepted this for their own checkout but needs, for the teams they deploy to, a way to make installs happen only through setup. No environment variable or config switch exists today; the only bypasses are `--dry-run` and excluded readiness reasons.

## Product Intent

An operator who sets one environment variable gets an MCP server that never installs packages at startup and instead reports the blocked state with the `wf setup` remedy. Boundaries: default behaviour unchanged; the switch does not alter the setup stamp's identity. AC-1 and AC-2 test the outcome.

## Requirements

1. When `WAVEFOUNDRY_NO_STARTUP_INSTALL` is set to `1` (truthy values per the framework's existing env-flag convention), `_startup_install_gate_unguarded` returns the readiness assessment without installing anything, foreground or background.
2. When only deferrable dependencies are missing (`setup_requirements.STARTUP_DEFERRABLE_IMPORTS`), the server still starts without installing them and its setup readiness carries a `startup_install_disabled` reason naming the `wf setup` remedy, visible in `wf_server_info`; when a non-deferrable dependency is missing, startup exits as it does today, printing the remedy on stderr.
3. The variable is not part of `setup_readiness.ENV_KEYS`, so setting it does not change the setup stamp's environment identity.
4. The variable is documented next to the existing `WAVEFOUNDRY_*` switches in `docs/contributing/build-and-verification.md`.

## Scope

**Problem statement:** There is no way to turn off startup installs.

**In scope:**

- `server.py` startup gate, tests, `docs/contributing/build-and-verification.md`, one CHANGELOG bullet.

**Out of scope:**

- A config-file switch.
- Changing what setup installs.

**Platform behaviour:** the same on Windows, macOS, Linux and WSL2; environment variables are read the same way.

## Acceptance Criteria

- [x] AC-1: With the variable set, startup performs no install (no uv subprocess, foreground or background); with only a deferrable dependency missing the server starts and `wf_server_info` reports `startup_install_disabled` with the `wf setup` remedy; with a non-deferrable one missing it exits with the remedy on stderr. Oracle: tests patching the install call and readiness.
- [x] AC-2: With the variable unset, startup installs as today; with it set, the setup stamp's environment identity is unchanged. Oracle: tests.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the early return.
- [x] Add the tests.
- [x] Document the variable; add the CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| startup | implementer | none | one gate |

## Serialization Points

- `.wavefoundry/framework/scripts/server.py`, `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

N/A: an opt-out on an existing gate.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required | The requested switch. |
| AC-2 | required | No regression and stamp stability. |
| AC-3 | required | Standard verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned. | Waveforge carried-forward note; investigation of `_startup_install_gate_unguarded`. |
| 2026-10-19 | Readiness red-team blocker: with the switch set, a missing deferrable package (today installed in the background while the server runs) would make startup exit, so `wf_server_info` could never show the remedy. Repaired before any approval: deferrable-only gaps start the server with a `startup_install_disabled` reason; non-deferrable gaps exit with the remedy on stderr. Flag convention noted: `strip().lower() in {"1","true","yes","on"}`. | Readiness red-team primer; receipt `review-policy-0b4525186c4d8166a8f7` superseded. |
| 2026-10-19 | Implemented: `server._startup_install_disabled` (flag convention `strip().lower() in {"1","true","yes","on"}`) and `_startup_install_refused`, checked before the deferrable split in `_startup_install_gate_unguarded`. With the switch set nothing installs; one stderr line names the packages and `wf setup`; the runner record reads `mode`/`status` `disabled`, so `wf_server_info` `data.startup_install` shows it; a `startup_install_disabled` reason is added and, for a deferrable-only gap, `startup_blocked` is cleared so the server starts (`dependencies_missing` stays). Non-deferrable gaps stay blocked and the entry exits with the remedy. Not added to `ENV_KEYS`. Documented in `docs/contributing/build-and-verification.md`. CHANGELOG bullet left to the coordinator. | `run_tests.py --file test_startup_install.py`: 67 OK (6 new: 4 gate, 2 end-to-end). Scratch mutants killed: drop the early return (4 failures), keep `startup_blocked` (2), add the switch to `ENV_KEYS` (1). `wf_validate_docs` ok. |
| 2026-10-19 | Coordinator: CHANGELOG bullet added. Combined focused run of the wave's test files: 1430 OK, including test_startup_install 67. | `scratchpad/2136z-focused.log`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | One environment variable. | Smallest switch; deployments set environment per host. | A workflow-config key: per repository, not per deployment host. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The switch hides a needed install. | Startup still reports the remedy. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
