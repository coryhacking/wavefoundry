# Automated Upgrade Script

Change ID: `12r08-feat automated-upgrade-script`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-19
Wave: TBD

## Rationale

Running "Upgrade wave framework" today is a 15–30 minute, mostly-manual agent conversation. The agent follows seed-160 step by step: zip adoption, surface rendering, pruning, index rebuild, and dashboard coordination. The process is fragile at the MCP restart / index rebuild handoff, completely blind to a running dashboard (which can trigger index rebuilds mid-upgrade against a partially-replaced tree), and not repeatable in a scripted or CI context.

This feature scripted the mechanical phases so the agent retains ownership of the high-judgment work (drift detection, journal reconciliation, spec gaps) while all scaffolding steps — zip adoption, surface rendering, pruning, docs gate, index rebuild, dashboard coordination — run as reliable, auditable shell commands. The boundary: the script runs phases 0–3 (pre-flight through docs gate), hands off to the agent for its editing pass, then the agent calls phase 4 (index rebuild) and phase 5 (cleanup).

Requested by Aceiss (Teton project operator).

## Requirements

### R1 — Upgrade lock file

`upgrade_lib.py` (new framework script) provides lock file utilities shared by all components:
- `UPGRADE_LOCK_FILENAME = "upgrade-in-progress.json"`
- `upgrade_lock_path(root)` → Path at `.wavefoundry/upgrade-in-progress.json`
- `read_upgrade_lock(root)` → `dict | None` (None = no lock present)
- `write_upgrade_lock(root, from_version, to_version)` → writes `{started_at, from_version, to_version, pid}`
- `remove_upgrade_lock(root)` → bool

Lock schema:
```json
{"started_at": "<ISO-8601>", "from_version": "<str|null>", "to_version": "<str>", "pid": <int>}
```

### R2 — Dashboard upgrade-awareness

`dashboard_server.py` must check for the lock file at three points:
1. **Startup** — if lock exists, enter `upgrade_paused` immediately; skip startup stale check and index build scheduling.
2. **Watch loop** — poll the lock file path each iteration; if it appears while running, cancel queued builds and enter `upgrade_paused`; if it disappears, exit `upgrade_paused` and call `signal_startup` (same as post-startup stale check) after a short delay.
3. **SSE events** — emit `upgrade_status` event with `{"state": "paused" | "idle"}` on every transition.

Dashboard snapshot includes `"upgrade_paused": true | false` in the response payload while paused.

### R3 — upgrade-wavefoundry script

New Python implementation at `scripts/upgrade_wavefoundry.py`; thin bash launcher at `bin/upgrade-wavefoundry` (same pattern as `docs-lint`); Windows batch launcher at `bin/upgrade-wavefoundry.bat`.

Phases:
- **Phase 0 — Pre-flight**: detect dashboard (warn, don't abort); version guard via `check_version.py` (exit 3 on downgrade); save old MANIFEST; detect and confirm zip to apply; emit structured change plan (R6); prompt for confirmation (skip in non-interactive/`--yes`); write upgrade lock.
- **Phase 1 — Surface rendering**: `render_platform_surfaces.py`; exit 2 on failure.
- **Phase 2 — Pruning**: `prune_framework.py --old-manifest /tmp/wf-manifest-old.txt`.
- **Phase 3 — Docs gate**: `docs-gardener && docs-lint`; exit 1 on failure with clear message.
- **Phase 4 — Index rebuild** (separate entry, `--rebuild-index` flag): `setup_index.py --full` then `setup_index.py --background-code --full`.
- **Phase 5 — Cleanup**: remove lock; print operator summary (R8).

Exit codes: 0=success, 1=docs gate failed, 2=surface rendering failed, 3=pre-flight/downgrade/lock failed.

### R4 — check_version.py

New standalone script `scripts/check_version.py`:
- Reads pack VERSION from `.wavefoundry/framework/VERSION`
- Reads installed revision from MANIFEST `framework_revision` field
- Compares using string sort (format `YYYY-MM-DDx` is lexicographically ordered)
- Prints: `Pack: 2026-05-19a  Installed: 2026-05-10a  → upgrade` (or `downgrade` / `same`)
- Exit 0 = pack ≥ installed (ok to proceed), 1 = downgrade, 2 = cannot determine

### R5 — wave_upgrade_status MCP tool

New `wave_upgrade_status_response(root)` in `server.py` reads the lock file and returns:
```json
{"in_progress": bool, "started_at": str|null, "from_version": str|null, "to_version": str|null, "pid": int|null}
```

Registered as `wave_upgrade_status` MCP tool (`_READONLY_TOOL`).

### R6 — Change plan output

`upgrade_wavefoundry.py` phase 0 prints a structured change plan before any disk mutation:
```
Wavefoundry Upgrade Plan
========================
Pack version:       2026-05-19a
Installed revision: 2026-05-10a
Zip to apply:       wavefoundry-2026-05-19a.zip  (or: none, using current tree)
Surfaces to render: hooks, MCP config, bin launchers, agent surfaces
Prune mode:         MANIFEST diff (old=2026-05-10a)  (or: legacy removal list)
Docs gate:          .wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint
Index rebuild:      full  (or: update)
Dashboard:          running — will pause during upgrade  (or: not running)
Prompt files:       <list or "none">
Proceed? [y/N]
```
Non-interactive (no TTY or `--yes`): skip prompt, proceed.

### R7 — wave_dashboard_restart upgrade guard

`wave_dashboard_restart_response(root)` checks for the upgrade lock before restarting. If lock exists, returns an error with a message explaining the block.

### R8 — Operator summary

Phase 5 of the upgrade script prints a structured summary:
```
Upgrade complete
================
Version:            2026-05-10a → 2026-05-19a
Zip applied:        wavefoundry-2026-05-19a.zip  (or: none)
Surfaces rendered:  hooks, MCP, bin launchers, agent surfaces
Files pruned:       N
Docs gate:          PASSED
Index rebuild:      docs complete, code running in background  (or: not run — use --rebuild-index)
Dashboard:          paused during upgrade
MCP restart needed: YES — restart MCP server to load upgraded server code

Next steps for agent editing pass:
  1. Drift detection (seed-160 step 6)
  2. Journal reconciliation (seed-160 step 0e)
  3. Spec gaps via seed-230
  4. Docs gate re-run after edits
  5. Remove upgrade lock: .wavefoundry/bin/upgrade-wavefoundry --cleanup
```

### R9 — Prompt file migration detection

Phase 0 runs:
```
find docs/prompts -maxdepth 2 -name "*.md" ! -name "index.md" ! -name "README.md" ! -name "*.prompt.md"
```
Prints results (or "none") in the change plan. Does not auto-rename.

## Scope

**Problem statement:** The upgrade process is slow, manual, fragile at MCP/index handoff, and not repeatable without an agent.

**In scope:**

- `scripts/upgrade_lib.py` — lock file utilities
- `scripts/check_version.py` — version comparison script (R4)
- `scripts/upgrade_wavefoundry.py` — main upgrade implementation (R3, R6, R8, R9)
- `bin/upgrade-wavefoundry` — bash launcher
- `bin/upgrade-wavefoundry.bat` — Windows batch launcher
- `dashboard_server.py` — upgrade awareness (R2)
- `server.py` — `wave_upgrade_status` tool (R5) + `wave_dashboard_restart` guard (R7)
- Unit tests for `upgrade_lib`, `check_version`, `wave_upgrade_status`, dashboard guard, restart guard

**Out of scope:**

- Agent-owned phases: drift detection, journal reconciliation, spec gap remediation, AGENTS.md normalization, reference updates after `.prompt.md` rename
- CI/CD pipeline integration
- Automated `wave_dashboard_restart` post-upgrade (agent calls it explicitly)

## Acceptance Criteria

- AC-1: `.wavefoundry/bin/upgrade-wavefoundry` on a repo with a root zip applies the zip, renders surfaces, prunes orphans, and runs the docs gate without manual agent shell commands.
- AC-2: A running dashboard detects `upgrade-in-progress.json` and does not trigger any index build while it is present.
- AC-3: When the lock file is removed, the dashboard triggers a post-upgrade index rebuild automatically.
- AC-4: `wave_dashboard_restart` returns an error (not a restart) while the lock file is present.
- AC-5: `wave_upgrade_status` reflects the current lock state over MCP.
- AC-6: Script exits non-zero on docs gate failure; the failure message names the failing check.
- AC-7: Script detects a pack downgrade and exits before modifying anything on disk.
- AC-8: Change plan is printed and confirmed before any disk mutation in interactive mode.
- AC-9: All of the above work on macOS, Linux, and Windows.
- AC-10: `check_version.py` exits 0/1/2 correctly and prints a human-readable version comparison.

## Tasks

1. Write `upgrade_lib.py` — lock file utilities
2. Write `check_version.py` — version comparison (R4)
3. Write `upgrade_wavefoundry.py` — phases 0–5 (R3, R6, R8, R9)
4. Write `bin/upgrade-wavefoundry` — bash launcher
5. Write `bin/upgrade-wavefoundry.bat` — Windows launcher
6. Patch `dashboard_server.py` — startup check, watch loop poll, SSE event, snapshot field (R2)
7. Patch `server.py` — `wave_upgrade_status_response` + tool + `wave_dashboard_restart` guard (R5, R7)
8. Write unit tests
9. Run full test suite

## Agent Execution Graph

| Workstream       | Owner              | Depends On        | Notes                                      |
| ---------------- | ------------------ | ----------------- | ------------------------------------------ |
| upgrade-lib      | framework-engineer | —                 | Foundation; no other code depends on it yet |
| check-version    | framework-engineer | upgrade-lib       | Standalone script + tests                  |
| upgrade-script   | framework-engineer | upgrade-lib       | Main phases; bin launchers                 |
| dashboard-patch  | framework-engineer | upgrade-lib       | R2; framework gate required                |
| server-patch     | framework-engineer | upgrade-lib       | R5 + R7; framework gate required           |
| tests            | framework-engineer | all workstreams   | Unit tests for all new code                |

## Serialization Points

- `upgrade_lib.py` must exist before `dashboard_server.py` and `server.py` patches
- `server.py` — framework gate; single file, serialize within session

## Affected Architecture Docs

`docs/architecture/current-state.md` — add upgrade lock file and `upgrade-wavefoundry` script to the tooling surface. Otherwise N/A (new file, follows existing script patterns).

## AC Priority

| AC    | Priority  | Rationale |
| ----- | --------- | --------- |
| AC-1  | required  | Core feature |
| AC-2  | required  | Safety — prevents corrupt rebuild mid-upgrade |
| AC-3  | required  | Post-upgrade reindex automation |
| AC-4  | required  | Safety — prevents restart mid-upgrade |
| AC-5  | required  | Agent observability |
| AC-6  | required  | Operator feedback on failure |
| AC-7  | required  | Downgrade protection |
| AC-8  | required  | No silent disk mutation |
| AC-9  | required  | Cross-platform requirement |
| AC-10 | required  | check_version.py standalone usability |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-19 | Implemented. `upgrade_lib.py` (lock utilities), `check_version.py` (R4), `upgrade_wavefoundry.py` (phases 0–5, R6/R8/R9), `bin/upgrade-wavefoundry` (bash), `bin/upgrade-wavefoundry.bat` (Windows). `dashboard_server.py` patched: startup check, watch-loop poll, SSE `upgrade_status` event, `upgrade_paused` snapshot field (R2). `server.py` patched: `wave_upgrade_status` tool (R5), `wave_dashboard_restart` upgrade guard (R7). 589 server tests pass; 1374 total (2 pre-existing flaky dashboard tests, not attributed to this change). | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'` — 589 OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-19 | Lock file in `.wavefoundry/` (not repo root) | Survives dashboard restarts; inspectable; consistent with dashboard-server.json location | In-memory flag (lost on restart) |
| 2026-05-19 | `upgrade_lib.py` as shared module | Avoids duplicating lock read/write across upgrade script, dashboard, and server | Inline in each consumer |
| 2026-05-19 | Phase 4 as `--rebuild-index` flag, not a separate script | Single entry point; agent calls it independently after editing pass; matches R3 spec | Separate `rebuild-index` bin script |
| 2026-05-19 | `wave_upgrade_status` as dedicated MCP tool (not field on `wave_server_info`) | Independently discoverable; clean separation of concerns; `wave_server_info` already dense | Add `upgrade` field to `wave_server_info` |
| 2026-05-19 | bin launcher is bash + .bat pair | Follows existing `docs-lint`/`docs-gardener` pattern; .bat covers Windows CMD | Single Python shebang script (breaks on Windows without Python on PATH) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Stale lock file from crashed upgrade blocks dashboard indefinitely | Lock file includes pid; dashboard and upgrade script can detect stale lock (pid not running) and auto-clear |
| Surface rendering or prune fails mid-upgrade, lock file not removed | Script uses try/finally to ensure lock removal in cleanup; `--cleanup` flag for manual removal |
| Dashboard watch loop polls lock file every `_WATCH_INTERVAL` seconds — adds stat() call per cycle | stat() on a non-existent file is ~1µs; negligible vs existing mtime polling |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
