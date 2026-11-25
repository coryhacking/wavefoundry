# Architecture review: wave 24buu readiness

Owner: Engineering
Status: active
Last verified: 2026-11-24

- Lane: architecture-reviewer, readiness, fresh context, independent.
- Verdict: **not approved.** Three findings meet the seed 209 readiness bar (A1 to A3). No approval was recorded.
- Read: wave.md, specs 24but, 24ax3, 24bn7, 24bn8 and 24bn9 with their Progress Logs, `.wavefoundry/work/24buu/readiness/red-team.md`, `.wavefoundry/work/24buu/upgrade-rehearsal.md`, the role doc and seed 209.
- Retrieval: MCP `code_outline`, `code_read` and `code_keyword` first.
  - Gapfill: shell `sed` and `grep` read line ranges in 7000-line files and in `git show v1.51.0` / `03672b89` copies of the installed runner, which the index does not hold. `unzip -l` listed the 1.51.0 release zip.
- Nothing in the repository was edited; this file is the only write.

## Process and phase ownership, verified

| Step | CLI `wf upgrade` | MCP `wf_upgrade` | Release-zip direct entry |
| --- | --- | --- | --- |
| Primary (phases 0 to 4) | Installed module, in process. On 1.51.0 to 1.52.0 this is 1.51.0 code. | The installed script runs as a subprocess (`wf_upgrade_response`, `cmd = [..., "--yes"]`). On 1.51.0 to 1.52.0 this is 1.51.0 code. | Protocol 2 (1.51.0 ships `UPGRADE-PROTOCOL.json`): `upgrade_bundle._incoming_runner` stages the **incoming** runner and runs `--root --pack --expected-pack-sha256 --yes`. Protocol 1: `upgrade_bridge_bootstrap.install` swaps the framework, then runs its `next_argv`. Both run **new** code on the installing hop. |
| Lifecycle baseline capture | The incoming `upgrade_extensions.lifecycle_baseline_report` runs through `_incoming_renderer_query` and is persisted verbatim in the lock. A new digest field therefore survives the old orchestrator. | same | same |
| Phase 1 render child | 1.51.0 `phase_surface_rendering` spawns `SCRIPTS_DIR/render_platform_surfaces.py` (the extracted file) with exactly `--repo-root --include-permissions --manifest`. I checked that this argv matches v1.51.0 byte for byte. | same | new runner |
| Cleanup | A separate process runs the extracted script. | `wf_upgrade(phase='cleanup')` | The bridge `_recovery` tells the agent to call `wf_upgrade(phase='cleanup')`. |

Endorsed: moving 24ax3 and 24bn8 into the Phase 1 child is the right owner.
- That child is the only point that runs new code before the docs gate and the index on every path.
- `render_platform_surfaces.main` calls `render_claude_permissions` (L3373) before `render_agent_surfaces`. Inside `render_agent_surfaces`, `reconcile_lifecycle_prompt_baselines` runs before `reconcile_review_policy_surfaces` (L5692 to L5710).
- So a replacement followed by the region re-render in one pass is feasible. The migration must come before L3373.

F8 is resolved for MCP: adding the flag at the `wf_upgrade_response` primary command builder works. The handler and the script ship in one tree, so there is no version skew; a stale, unrestarted server is out of contract.

## Findings

### A1 (blocking; 24bn9). The release-zip entry is not covered.

- Anchors: `upgrade_bundle._incoming_runner`, `upgrade_bridge_bootstrap.install` (`next_argv`), `upgrade_bundle._recovery` (`primary_phase_complete`), `upgrade_bundle.run` (`envelope.cleanup` when no checkpoint remains).
- **What breaks.** The bridge runs the new primary without `--no-auto-cleanup`. Once 24bn7 makes the entry work, auto-cleanup fires on the 1.51.0 to 1.52.0 hop through the zip. That contradicts 24bn9's statement that the change takes effect after 1.52.0. The bridge payload still instructs "Restart hosts, complete the reconciliation pass, then call `wf_upgrade(phase='cleanup')`", and that call then finds no lock (`phase_cleanup`'s no-lock branch).
- **Why it matters.** This is the path seed 160 and MCP's `bridge_release_required` handoff send older installs down. No AC covers it.
- **Repair.** Decide one of two:
  - The bridge argv carries `--no-auto-cleanup`, keeping its recovery contract.
  - `_recovery` reports cleanup as complete when the lock is gone.
- Then add an AC, and add the zip path to the per-hop claim.

### A2 (blocking; 24ax3 and 24bn8). The Phase 1 child's trigger is unresolved.

- Anchors: `phase_surface_rendering` (1.51.0 argv), `setup_wavefoundry._run_render_platform_surfaces` (also `--include-permissions`), `spec_tool_permissions._receipt_path`.
- **The problem.** Neither spec says how the child knows it is running inside an upgrade.
  - A new flag would do nothing on the installing hop, because the old orchestrator never passes it. That is the old-code window the move was meant to escape.
  - Keying on `--include-permissions` alone makes `wf setup` migrate host settings and write verification receipts. No decision or security review covers that.
- **Why it matters.** Receipts are keyed to the workstation, home and checkout, and kept under the git-ignored `.wavefoundry/cache/`. Teammates of the upgrading operator therefore stay locked out unless setup also verifies. That conflicts with the Objective "existing installations keep the renamed spec tools".
- **Repair.**
  - Pin the trigger, for example `--include-permissions` plus an existing upgrade lock.
  - Decide what setup does.
  - State the outcome for other workstations.
  - Add an AC that drives the child with the verbatim 1.51.0 argv.

### A3 (blocking, cheap; 24bn8, 24bn9, 24ax3 and 24bn7). "Affected Architecture Docs: N/A" is false.

`docs/architecture/data-and-control-flow.md`:
- **Upgrade lifecycle baseline drift.** Three statements change under 24bn8:
  - "The report leaves project-owned destination bytes ... unchanged".
  - The finding shape `{channel, file, detail, action}`.
  - "To overwrite, finish the upgrade, delete ... run `wf render-surfaces`".
- **Upgrade rerun and cleanup outcomes.** "A successful primary phase still requires cleanup" changes under 24bn9.
- **24ax3.** It adds an out-of-checkout read edge (user-level and enterprise settings) and an upgrade-written attestation. Record both in this file and in `threat-model.md`.
- **24bn7.** The "stdlib zipapp" wording now resolves framework modules from the zip's feature members.

## Notes (not findings)

- 24bn9: `--resume-after-gate` still ends with "Run --cleanup", after a docs-gate failure on the CLI. Scope it or state it.
- 24but: AC-1's expected object omits `churn_available`, so a strict equality check cannot pass (route to qa).
- 24but: `churn_available` needs a side channel out of `_memory_ranked`, which `memory_search` and `maintenance_signals` share. Keep the two counts equal.
- 24but: the `memory_brief` section of `mcp-tool-surface.md` (near `active_memory_budget`) is the right home.
- 24bn7 is sound: the 1.51.0 zip carries `.wavefoundry/framework/scripts/contained_files.py`, and the `_materializer` allowlist is untouched.
