# Install Reliability Guidance Propagation

Owner: Engineering
Status: draft
Last verified: 2026-09-22

This table maps each new operative instruction in the canonical seeds and MCP help to its local carrier. A carrier may combine adjacent sentences for readability, but must preserve the stated behavior. `W` is `docs/references/native-windows-support.md`; `I` and `U` are the local install and upgrade prompts. All paths are repository-relative.

| Canonical instruction or claim | Canonical source | Local carriers and evidence |
| --- | --- | --- |
| Diagnose `python3` before setup or MCP on first install and a seeded checkout on a new workstation. | seed 011, seed 160 | W § Diagnose; I § Python requirement; U opening prerequisite; `AGENTS.md` MCP section; `README.md` Prerequisites; framework README; project overview; platform mapping; architecture current-state |
| Invoke the independent read-only diagnostic as `powershell -NoProfile -File ".\.wavefoundry\framework\scripts\diagnose_python.ps1"` from the repository root. | seed 011, seed 050, seed 160 | W § Diagnose; I/U; `AGENTS.md`; both READMEs; project overview; platform mapping; architecture current-state |
| The diagnostic needs neither Python nor MCP and does not use install-log completion as a local readiness oracle. | seed 011, seed 050, seed 160 | W § Diagnose; I/U; `AGENTS.md`; platform mapping; architecture current-state |
| Probe `python3` first; probe `python` only as bounded diagnostic evidence. | seed 011 | W § Diagnose; architecture current-state |
| Report the failed stage, attempted command, resolved path/identity when available, observed error, exit or timeout, and next step. | seed 011 | W § Diagnose; I § Python requirement; architecture current-state |
| Keep unsupported causal explanations marked as hypotheses or undetermined. | seed 011 | W § Diagnose |
| Distinguish command resolution, execution/version and later MCP bootstrap failures. | seed 011 | W § Diagnose; architecture current-state |
| If execution policy blocks the script, do not bypass it; use manual `Get-Command`, `where.exe` and version probes, then an IT handoff when restricted. | seed 011, seed 160 | W § Diagnose; I/U; platform mapping |
| A working `python.exe` is evidence of an installed interpreter, not an alternate setup/MCP launch contract. | seed 011, seed 160 | W § Diagnose; I/U; both READMEs; `AGENTS.md`; project overview; architecture current-state |
| Stop before setup mutation, provisioning and model downloads when the required `python3` is unusable. | seed 011 | W § Diagnose; architecture current-state; I § Python requirement |
| Prefer an approved existing `python3` command or permitted user PATH correction. | seed 011 | W § Diagnose; I § Python requirement; `README.md`; framework README |
| Do not assume elevation, Store, Developer Mode, machine PATH edits or a specific installer-provided command. | seed 011 | W § Diagnose; I § Python requirement |
| A shell-only alias or cmd shim does not establish raw-spawn MCP readiness. | seed 011 | W § Diagnose; I § Python requirement |
| A policy-blocked repair remains unready and gets a copy-ready IT handoff with interpreter path/version, failed `python3` probe, host visibility and verification commands. | seed 011 | W § Diagnose; I § Python requirement; framework README |
| Verify `python3 --version`, `python3 .../server.py --dry-run`, restarted-host MCP startup and representative hook after repair. | seed 011, seed 160 | W § Diagnose; I/U; framework README; `AGENTS.md` MCP section |
| Do not reseed, rebuild or discard committed config/index data solely for local interpreter diagnosis. | seed 011, seed 050, seed 160 | W § Diagnose; I/U; `AGENTS.md`; framework README; platform mapping |
| Native-Windows standard-user and fresh-host qualification is pending real-host execution; simulated checks alone do not prove it. | wave plan 1yo5l | W § Diagnose; I environment section; project overview; architecture current-state/testing |
| Target posture docs describe the target system; framework model/chunker facts are not copied to appease a consumer validator. | seed 070 | I § Required Outputs via seed; U install-reliability backfill; architecture testing; source opt-in plan 1yp0x |
| The nine mandatory framework-internal claims use only explicit `docs_lint.framework_internal_constants: true` in this source repo; consumers remain exempt while structural checks remain. | plan 1yp0x; seed 160 backfill | U install-reliability backfill; architecture testing; `docs/specs/mcp-tool-surface.md` is unchanged on validator runtime details |
| A checkpoint may be taken after verified row 2.8; leave row 2.9 unchecked and save handoff. | seed 012 | I § Required Outputs |
| Resume 2.9 by inventorying actual prompt files and manifest against seed-100's current public catalog and conditional rules, without a fixed file count. | seeds 012/100 | I § Required Outputs; U install-reliability backfill; architecture data-and-control-flow |
| Preserve project-authored prompt prose and reconcile only missing or stale required outputs. | seeds 012/100/160 | I § Required Outputs; U install-reliability backfill; platform mapping |
| Once required prompt/role sources exist, use `wf_sync_surfaces(mode='run')` over MCP or `wf render-surfaces` via CLI. | seeds 012/100/160; `server_impl.wf_sync_surfaces` docstring | I § Required Outputs; U install-reliability backfill; platform mapping; MCP tool spec; architecture data-and-control-flow |
| Renderer-owned upgrade-policy regions need populated content; empty markers and hand-copied `UPGRADE_POLICY_BLOCK` are not completion. | seeds 012/100/160; `server_impl.wf_sync_surfaces` docstring | I § Required Outputs; U install-reliability backfill; platform mapping; MCP tool spec; architecture data-and-control-flow |
| `wf_sync_surfaces` does not turn on MCP permission-allowlist rendering. | seed 100; `server_impl.wf_sync_surfaces` docstring | U install-reliability backfill; platform mapping; MCP tool spec |
| Audit actual prompt files, manifest and rendered regions before marking row 2.9 complete; leave blocking validation visible. | seeds 012/100/160 | I § Required Outputs; U install-reliability backfill; architecture data-and-control-flow |

| Consumer recovery pointers resolve to shipped seed-011 Python prerequisite guidance; local Wavefoundry runbook links remain local. | seeds 050/160; framework README | Local carriers retain W, which exists here; consumers receive seed-011 in the pack |
| Interpreter success permits first setup; dependency provisioning precedes server dry-run, then fresh-host MCP verification. Existing provisioned checkout needs no forced setup/rebuild for command repair. | seed 011; framework README; seed 160 | I/U; W |
| Sync default dry_run skips without preview; run mode renders and reports changes. | server_impl.wf_sync_surfaces docstring | MCP tool spec |

The source opt-in's nine-claim census and executable proof are owned by the validator implementation. This table does not claim real native-Windows qualification; the operator deferred native diagnostic, standard-user repair and fresh-host MCP/hook qualification to external testing after the next release on 2026-09-22. The retained protocol is post-release-windows-validation.md; no native pass is claimed.
