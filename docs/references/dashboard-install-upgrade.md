# Dashboard Install, Upgrade, and Package Flows

Owner: Engineering
Status: active
Last verified: 2026-06-25

Reference doc covering how the local dashboard feature moves from the Wavefoundry framework pack into target repositories. Addresses packaging (build_pack.py), install (seed-010), upgrade (seed-160), and the sibling-directory runtime option.

## Overview

The dashboard is a framework feature, not a per-repo app. Its assets (HTML shell, CSS, application JS) and server scripts are packaged into the semver framework zip distribution and seeded into target repositories through the standard install and upgrade flows. React, React DOM, force-graph, and elkjs load from pinned unpkg CDN URLs in `dashboard.html`; `dashboard.js` and `dashboard.css` are still served locally by the dashboard server. No Node.js, npm, or build toolchain is required in target repos at install or runtime. The dashboard graph view requires network access on first load (or a warm browser cache) for those CDN scripts.

## Packaging (build_pack.py)

`build_pack.py` zips the entire `.wavefoundry/framework/` tree into a semver distribution archive (`wavefoundry-MAJOR.MINOR.PATCH.<build>.zip`) under `~/.wavefoundry/dist/` by default. The dashboard files are included automatically:

**Packed paths (canonical):**
```
dashboard/dashboard.html
dashboard/dashboard.css
dashboard/dashboard.js
scripts/dashboard_lib.py
scripts/dashboard_server.py
seeds/152-start-dashboard.prompt.md
seeds/153-stop-dashboard.prompt.md
seeds/154-restart-dashboard.prompt.md
```

These paths are tracked in `.wavefoundry/framework/MANIFEST`. The build script regenerates MANIFEST on every run, so removing or renaming a dashboard file automatically drops it from future distributions. The zip file itself is gitignored; do not commit it.

**Exclusion rules:** `build_pack.py` excludes `__pycache__`, `.pytest_cache`, `.wavefoundry` (as directory names), `.DS_Store`, and the `scripts/tests/` subtree. Dashboard assets are not matched by any exclusion rule and are always packed.

## Install (seed-010)

`seed-010` (Install Wavefoundry) unpacks the framework zip into the target repo under `.wavefoundry/framework/` using:

```bash
unzip -o wavefoundry-<date>.zip -d <repo-root>
```

The `-o` flag overwrites existing files without prompting. After unpacking, seed-010 seeds the dashboard public prompt docs: `docs/prompts/start-dashboard.prompt.md`, `docs/prompts/stop-dashboard.prompt.md`, and `docs/prompts/restart-dashboard.prompt.md`. These prompts document the operator-facing dashboard control commands and are the canonical entry points for dashboard discovery.

**Config seeding:** `docs/workflow-config.json` must include a `dashboard` block after install. The minimum valid config:

```json
{
  "dashboard": {
    "enabled": true,
    "host": "127.0.0.1",
    "preferred_port": 43127,
    "port_range_start": 43127,
    "port_range_end": 43147,
    "project_label": "<repo name>",
    "include_dirs": [],
    "terminology": {
      "wave": "wave",
      "change": "change",
      "task": "task"
    },
    "auto_index": true,
    "auto_index_delay_seconds": 30
  }
}
```

If a `dashboard` block already exists in `workflow-config.json`, seed-010 preserves operator-customized values (port ranges, `project_label`, `include_dirs`, `terminology`) and only backfills missing fields. `auto_index` now defaults to `true`; set it explicitly to `false` to opt out.

**Gitignore entries:** After install, `.wavefoundry/dashboard-server.json` must be gitignored. This file holds host-local endpoint metadata (pid, port, url) and must never be committed. Add to `.gitignore`:

```
.wavefoundry/dashboard-server.json
```

## Upgrade (seed-160)

The `Upgrade Wavefoundry` flow (seed-160) adopts the new framework zip automatically — root-zip extraction is built into the upgrade, not a manual `unzip` step — overwriting dashboard assets in place. After the upgrade extracts the pack:

1. The server script (`dashboard_server.py`) and shared reader (`dashboard_lib.py`) are replaced with the new version.
2. The browser assets (`dashboard.js`, `dashboard.css`, `dashboard.html`, React bundles) are replaced.
3. The `docs/prompts/start-dashboard.prompt.md`, `docs/prompts/stop-dashboard.prompt.md`, and `docs/prompts/restart-dashboard.prompt.md` public prompt docs are refreshed if the seed content changed.
4. Operator-customized values in `docs/workflow-config.json` `dashboard` block are preserved. Seed-160 backfills any new fields added in the upgraded version without touching existing values.

If the upgraded pack includes the dashboard feature for the first time (i.e. the prior version did not ship it), seed-160 seeds the dashboard prompt docs and prompts the operator to add the `dashboard` config block to `workflow-config.json`.

**Config field backfill for auto-index:** When upgrading from a version that predates auto-index support, seed-160 backfills the following fields into the existing `dashboard` block without touching any existing values:

```json
"auto_index": true,
"auto_index_delay_seconds": 30
```

`auto_index` now backfills as `true`. Operators who want automatic index rebuilds disabled must explicitly set it to `false` after upgrade.

**No restart required for asset changes:** The dashboard server re-reads `workflow-config.json` and serves updated static files on the next request. If the server process is already running when assets are upgraded, the browser will pick up new JS/CSS on the next page reload. To pick up a `workflow-config.json` change (e.g. disabling `auto_index`), restart the server process.

## Sibling-Directory Runtime Option

When a dashboard session must survive branch switching or parallel work in the same repo, the server can be run from a sibling directory outside the git worktree:

```bash
# From any stable path (e.g. a persistent process manager):
python3 /path/to/.wavefoundry/framework/scripts/dashboard_server.py \
  --root /path/to/target-repo
```

The `--root` argument tells the server where to read project state from. The dashboard assets are always loaded from the framework directory co-located with the script, not from the `--root`. This means asset upgrades in `--root/.wavefoundry/framework/` take effect on the next request even when the server process is stable.

## Operator-Facing Command

The operator-facing dashboard controls are:

```bash
# Via public prompt shortcut (preferred):
Start dashboard

# Via public prompt shortcut:
Stop dashboard

# Via public prompt shortcut:
Restart dashboard

# Via MCP tool (agent-facing):
wave_dashboard_start

# Via MCP tool (agent-facing):
wave_dashboard_stop

# Via MCP tool (agent-facing):
wave_dashboard_restart

# Via wf dispatcher shortcut (see below):
wf dashboard

# Via low-level script — opens browser:
python3 .wavefoundry/framework/scripts/dashboard_server.py --root . --open

# Startup-only (no browser launch):
python3 .wavefoundry/framework/scripts/dashboard_server.py --root .
```

The `--open` flag is appropriate for interactive operator sessions. Automation, tests, and headless environments should use the startup-only form.

`Start dashboard` and `Restart dashboard` always print the final bound URL after the dashboard is ready. `Stop dashboard` reports the repo-local process state it stopped or found absent.

## wave_dashboard_start / wave_dashboard_stop / wave_dashboard_restart MCP Tools

`wave_dashboard_start`, `wave_dashboard_stop`, and `wave_dashboard_restart` are MCP tools registered in `scripts/server.py`. They are part of the framework pack and available after any install or upgrade that includes `server.py`. No additional config is required.

Start behavior:
- Checks `.wavefoundry/dashboard-server.json` for an already-running process (by PID). If running, returns the existing URL immediately.
- If not running, spawns `dashboard_server.py --root <repo> --open` as a detached background process.
- Polls the metadata file for up to 5 seconds for the bound URL, then returns it.

Stop behavior:
- Targets the dashboard process recorded for the current repository only.
- Stops the current repository dashboard and clears stale repo-local metadata when appropriate.

Restart behavior:
- Stops the current repository dashboard first.
- Starts a fresh dashboard process for the same repository root.
- Returns the new final URL once the restarted dashboard is ready.

These tools are the preferred agent-facing entry points when an agent needs to control the dashboard programmatically.

## wf dashboard Shortcut

`wf dashboard` is a subcommand of the cross-OS `wf` entry point. It routes through `wf_cli.py` to start the dashboard server with `--open` (browser launch). The renderer writes the single generated Windows shim alongside the POSIX entry point; there is no longer a per-wrapper `wave-dashboard` script. No-PATH invocation is POSIX `./.wavefoundry/bin/wf dashboard`; native Windows `.\\.wavefoundry\\bin\\wf.cmd dashboard`.

The dispatcher resolves the repo root and runs the dashboard server, roughly equivalent to:
```bash
python3 .wavefoundry/framework/scripts/dashboard_server.py --open "$@"
```

Invoke it from the repo root:
```bash
./.wavefoundry/bin/wf dashboard
```

The script passes through any additional arguments (`$@`) to `dashboard_server.py`, so `--root` and other flags work as expected.

## Verification After Install or Upgrade

After install or upgrade, confirm the dashboard is functional:

1. Run `python3 .wavefoundry/framework/scripts/dashboard_server.py --root . --open`.
2. Confirm the browser opens and the dashboard header shows the correct `project_label` and framework version.
3. Confirm the state badge shows `LIVE` after the first poll.
4. Run `python3 .wavefoundry/framework/scripts/run_tests.py` to confirm framework tests pass.

## Cross-Links

- `docs/references/dashboard-adapter-model.md` — config surface and data source declaration (AC-7)
- `docs/design-system/foundations/dashboard.md` — UI token and component rules (AC-7a)
- `docs/architecture/data-and-control-flow.md` — Path 4 (packaging), Path 7 (dashboard server)
- `.wavefoundry/framework/scripts/build_pack.py` — packaging script
- `.wavefoundry/framework/MANIFEST` — canonical packed-file list
- `docs/prompts/start-dashboard.prompt.md` — operator-facing command doc
- `docs/prompts/stop-dashboard.prompt.md` — operator-facing stop command doc
- `docs/prompts/restart-dashboard.prompt.md` — operator-facing restart command doc
