# Add a `wf gpu-doctor` subcommand

Change ID: `1p8gz-enh wf-gpu-doctor-subcommand`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-27
Wave: `1p8gx windows-upgrade-hardening`

## Rationale

GPU/provider diagnostics are exposed as the `wave_gpu_doctor` MCP tool (`server_impl.py:15908 wave_gpu_doctor_response`, backed by `provider_policy`'s GPU/provider detection), but there is **no `wf` subcommand** for it. Every other operational diagnostic has a `wf` entry (`docs-lint`, `docs-gardener`, `secrets-scan`, `codebase-map`, `update-indexes`, …), so an operator or agent on the CLI — or any host without MCP attached — cannot run the GPU/provider doctor. Add `wf gpu-doctor` so the same diagnostics are reachable from the cross-OS `wf` dispatcher.

## Requirements

1. Add a `gpu-doctor` entry to `wf_cli.py` `_SUBCOMMANDS`, routing to a GPU-doctor CLI entry that surfaces the same diagnostics as the `wave_gpu_doctor` MCP tool.
2. Reuse the existing backing logic — do NOT duplicate provider/GPU detection. Share the function(s) behind `wave_gpu_doctor_response` / `provider_policy`; if no CLI `main()` exists, add a thin one that formats the doctor result for a terminal.
3. The subcommand self-bootstraps into the tool venv like the other `wf` subcommands (per the dispatcher's venv-activation rule) so GPU/provider libs resolve.
4. The `wf` surface listings name `gpu-doctor` (`wf --help`, the `docs/prompts/` command index, and the AGENTS.md / docs wf-subcommand listing).

## Scope

**Problem statement:** GPU/provider diagnostics are MCP-only; there is no `wf gpu-doctor` for CLI/no-MCP use.

**In scope:**

- The `wf gpu-doctor` subcommand + routing + a thin CLI entry reusing the existing doctor logic.
- Help/index/docs updates listing the subcommand.
- A dispatch + venv-activation test mirroring the other subcommands.

**Out of scope:**

- Changing the GPU/provider detection itself.
- The Windows subprocess/encoding/path fixes (siblings `1p8gu`/`1p8gv`) and the install-audit fix (`1p8gw`).

## Acceptance Criteria

- [x] AC-1: `wf gpu-doctor` runs and prints the GPU/provider diagnostics — the same data as `wave_gpu_doctor` — reusing the shared backing logic (no duplicated detection). — new thin `gpu_doctor.py` calls `provider_policy.diagnostic_report(provider_probe=setup_index._probe_embedding_provider)` + `format_diagnostic_report` (identical to `wave_gpu_doctor_response` / `setup_wavefoundry._run_gpu_check`). Verified end-to-end (prints the full diagnostic). Tests: `GpuDoctorSubcommandTests.test_main_reuses_provider_policy_backing_logic` + `test_gpu_doctor_does_not_duplicate_detection`.
- [x] AC-2: the subcommand is registered in `_SUBCOMMANDS`, appears in `wf --help`, and self-bootstraps into the tool venv (dispatch + venv-activation tests, mirroring the existing subcommand tests in `test_wf_cli.py`). — registered `"gpu-doctor"` → `gpu_doctor`; added to the routing/venv-activation/help list tests + `test_self_bootstraps_into_tool_venv`.
- [x] AC-3: the `wf` surface docs/index (prompt index + AGENTS.md / docs listing) name `gpu-doctor`. — `docs/prompts/index.md` (new GPU doctor row), `docs/specs/mcp-tool-surface.md` (wave_gpu_doctor row names `wf gpu-doctor`), `docs/reports/wsl2-smoke-checklist.md`. (No canonical wf-subcommand enumeration seed exists; `wf --help` auto-lists it from `_SUBCOMMANDS`.)
- [x] AC-4: full framework suite + docs-lint pass. — `run_tests.py`: 3611 tests OK; `docs_lint.py`: ok. (gpu_doctor also wires `cli_stdio.configure_utf8_stdio()` and is covered by the entry-point wiring guard.)

## Tasks

- [x] Add the `gpu-doctor` routing to `_SUBCOMMANDS` + a thin CLI entry reusing `provider_policy` / the `wave_gpu_doctor` backing logic. — `gpu_doctor.py` + `_SUBCOMMANDS["gpu-doctor"]`.
- [x] Update `wf --help`, the prompt/command index, and the wf-subcommand listing. — help description added; `docs/prompts/index.md`, `docs/specs/mcp-tool-surface.md`, wsl2-smoke-checklist.
- [x] Add dispatch + venv tests.
- [x] Full suite + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| CLI entry + routing | implementer | — | reuse provider_policy/wave_gpu_doctor logic; no dup detection |
| help/index/docs | docs-contract-reviewer | CLI entry | name gpu-doctor on the wf surface |
| dispatch + venv tests | qa-reviewer | CLI entry | mirror existing subcommand tests |

## Serialization Points

- Touches `wf_cli.py` `_SUBCOMMANDS` (also in `1p8gu`'s `wf`-dispatch coverage scope). Minimal overlap (this adds a dict entry; `1p8gu` audits dispatched spawns) — coordinate the `wf_cli.py` edits.

## Affected Architecture Docs

`N/A` — additive CLI surface; update the wf-subcommand listing in AGENTS.md / `docs/prompts/` index.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The subcommand must actually surface the diagnostics. |
| AC-2 | required | Registration + venv bootstrap is the dispatcher contract. |
| AC-3 | important | Discoverability on the wf surface. |
| AC-4 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-27 | Planned (operator request) — `wave_gpu_doctor` has no `wf` equivalent. | `server_impl.py:15908`; `_SUBCOMMANDS` has no gpu-doctor entry. |
| 2026-06-27 | Implemented. New `gpu_doctor.py` thin CLI (venv-bootstrap + UTF-8 stdio + reuse of `provider_policy.diagnostic_report`/`format_diagnostic_report` — no duplicated detection); registered `wf gpu-doctor` in `_SUBCOMMANDS` + help. Docs updated. Verified end-to-end on macOS (CoreML provider report). | `GpuDoctorSubcommandTests` (4) + list-test additions; `wf gpu-doctor` ran live. Full suite 3599 OK; docs-lint ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-27 | Reuse the `wave_gpu_doctor` backing logic for the CLI. | One source for GPU/provider detection; CLI and MCP stay in sync. | Separate CLI detection (rejected: duplication/drift). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The doctor logic isn't cleanly importable as a CLI entry. | Add a thin `main()` that calls the shared function + formats; keep detection in `provider_policy`. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
