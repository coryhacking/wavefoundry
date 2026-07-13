# Dashboard Adapter Model

Owner: Engineering
Status: active
Last verified: 2026-07-12

Reference doc for how target repositories declare custom data sources, port preferences, terminology, and file-activity scope for the local dashboard. The dashboard is a generic Wave Framework feature; this doc defines the knobs available to any seeded repo without forking the core UI or server.

## Config Surface

All dashboard configuration lives in `docs/workflow-config.json` under the `dashboard` key. The server reads this file at startup (and on each snapshot poll if the file changes). Unrecognised keys are silently ignored so repos can safely annotate the block.

```json
{
  "dashboard": {
    "enabled": true,
    "host": "127.0.0.1",
    "preferred_port": 43127,
    "port_range_start": 43127,
    "port_range_end": 43147,
    "poll_interval_ms": 2000,
    "project_label": "My Project",
    "entrypoint": "dashboard.html",
    "include_dirs": [],
    "auto_index": true,
    "auto_index_delay_seconds": 30,
    "terminology": {
      "wave": "wave",
      "change": "change",
      "task": "task"
    }
  }
}
```

### Field Reference

| Field | Type | Default | Effect |
|---|---|---|---|
| `enabled` | bool | `true` | When `false`, `dashboard_server.py` exits immediately with an advisory message |
| `host` | string | `"127.0.0.1"` | Bind address. Only loopback addresses are accepted; any non-loopback value is rejected at startup |
| `preferred_port` | int | `43127` | First port to try. If unavailable, the server scans upward through `port_range_end` |
| `port_range_start` | int | `43127` | Lower bound of the fallback scan range |
| `port_range_end` | int | `43147` | Upper bound of the fallback scan range (inclusive) |
| `poll_interval_ms` | int | `2000` | Not currently enforced server-side (the browser controls polling); reserved for a future server-sent events path |
| `project_label` | string | repo directory name | Name shown in the dashboard header and browser tab title |
| `entrypoint` | string | `"dashboard.html"` | Filename served at `/`. Override only when the repo ships a custom shell page alongside the default assets |
| `include_dirs` | string[] | `[]` | Additional root-relative directories included in the `files_updated_today` / `files_updated_week` mtime scan. By default the scan excludes `.wavefoundry`, `.git`, `node_modules`, and similar noise dirs |
| `auto_index` | bool | `true` | When `true`, the dashboard server schedules background index rebuilds for stale index layers; set to `false` to opt out |
| `auto_index_delay_seconds` | int | `30` | Debounce/settling delay before a scheduled auto-index rebuild starts; values below `10` are clamped up |
| `terminology.wave` | string | `"wave"` | Singular display label for a wave-level work item |
| `terminology.change` | string | `"change"` | Singular display label for a change-level work item |
| `terminology.task` | string | `"task"` | Singular display label for a task-level work item |

## Data Sources

The dashboard reads exclusively from Wave Framework doc conventions. There are no pluggable adapter entry points in v1 — the server calls fixed Python reader functions for each data domain.

| Data domain | Source | Reader function |
|---|---|---|
| Wave status and progress | `docs/waves/<id>/wave.md` | `collect_waves` |
| Change docs | `docs/waves/<id>/*.md`, `docs/plans/*.md` | `collect_changes` |
| Session handoff | `docs/agents/session-handoff.md` | `collect_dashboard_snapshot` |
| Agent / persona / specialist info | `docs/agents/personas/`, `docs/agents/specialists/`, `docs/agents/journals/` | `collect_agents` |
| Prompt count | `docs/prompts/prompt-surface-manifest.json` | `collect_dashboard_snapshot` |
| Framework version | `.wavefoundry/framework/VERSION` | `collect_dashboard_snapshot` |
| Index health | `.wavefoundry/index/index-state.sqlite` (build snapshot; wave 1sed7) | `collect_dashboard_snapshot` |
| File activity | Repo mtime scan, scoped by `include_dirs` | `count_files_updated_since` |

### Extending File Activity Scope

The `include_dirs` config field controls which directories are included in the file-activity mtime scan. Directories not listed in `include_dirs` and present in the default skip list (`.wavefoundry`, `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.tox`, `dist`, `build`) are excluded.

To include framework internals in the activity count:

```json
"include_dirs": [".wavefoundry"]
```

To include a custom source tree:

```json
"include_dirs": ["src", "tests"]
```

The scan always walks the entire repo root tree except for the excluded directories, so `include_dirs` effectively un-excludes entries from the default skip list and does not restrict which non-skip directories are scanned.

## Graceful Degradation

Every reader is written to tolerate missing, empty, or partially-written files. The specific guarantees:

| Condition | Dashboard behavior |
|---|---|
| `docs/waves/` missing or empty | Waves card shows empty-state; no crash |
| `docs/agents/` missing | Agents section is absent from hero; no crash |
| `docs/agents/session-handoff.md` missing | Handoff pill is absent from wave cards |
| `docs/prompts/prompt-surface-manifest.json` missing | Prompt count shown as `—` |
| `.wavefoundry/framework/VERSION` missing | Framework version shown as `—` |
| No completed build epoch in `index-state.sqlite` | Index tile shows `unknown` |
| Any file mid-write during snapshot | JSON parse errors are caught per-file; the remainder of the snapshot is served normally |

Repos that do not use Wave Framework wave/plan conventions will see an empty dashboard rather than an error. The dashboard does not fabricate numbers.

## Adding Custom Data Sources (Target-Repo Approach)

The v1 adapter model is config-driven, not plugin-driven. If a target repo needs to expose data not available in the Wave Framework conventions (e.g. a `TASKS.md` task tracker, CI test results, or a custom log file), the recommended approaches in priority order:

1. **Model the data as Wave Framework docs.** If the data can be expressed as a wave, change doc, or progress log entry, the dashboard picks it up automatically with no extra config.

2. **Map to `include_dirs` for file activity.** If the primary signal needed is "how much activity happened in this directory today," add the directory to `include_dirs`. This is zero-code.

3. **Fork `dashboard_lib.py` in the target repo.** The server imports `dashboard_lib` from the framework path. A target repo that places a `dashboard_lib.py` at a higher-priority location on `sys.path` can override the reader functions. This is a full-responsibility fork; the target repo owns update hygiene when the framework ships a new version.

4. **Open a framework enhancement request.** If a data source pattern is generic enough to benefit all Wave Framework repos (e.g. reading a `PROGRESS.md` or a JUnit-style test report), file it as a framework wave rather than a per-repo customization.

v2 of the adapter model (not yet designed) may introduce a formal `dashboard_adapters.py` hook module discoverable from the target repo's `docs/workflow-config.json`, allowing typed reader extensions without forking the core library.

## Terminology Register

The `terminology` block lets repos rename work-item levels without changing any card labels in code. The dashboard JavaScript reads terminology from the `/api/dashboard` response and substitutes labels throughout.

Example for a repo using "sprint" and "story" instead of Wave Framework vocabulary:

```json
"terminology": {
  "wave": "sprint",
  "change": "story",
  "task": "task"
}
```

Terminology values are singular. Pluralization is handled by the frontend's `p(n, singular, plural)` helper, which appends `s` by default. For irregular plurals, the current convention is to keep the singular and accept the default plural; custom plural overrides are not supported in v1.

## Port Selection and Concurrent Repos

Multiple Wave Framework repos may run dashboards concurrently on one machine. The port allocation strategy avoids fixed-port conflicts without requiring committed host-specific config:

1. Read `preferred_port` from `workflow-config.json`.
2. Check `.wavefoundry/dashboard-server.json` for a previously resolved port; if the recorded port is still free, reuse it.
3. Otherwise, scan `port_range_start` → `port_range_end` for the first available port.
4. Write the resolved port to `.wavefoundry/dashboard-server.json` (gitignored). This file is never committed.

Repos that need to coexist must use non-overlapping `port_range_start`–`port_range_end` windows. The default range (43127–43147) leaves room for several concurrent repos before overlap occurs.

## Cross-Links

- `docs/architecture/data-and-control-flow.md` — Path 7: dashboard server topology
- `docs/design-system/foundations/dashboard.md` — UI token and component rules (AC-7a)
- `docs/references/dashboard-install-upgrade.md` — install, upgrade, and package flows (AC-6)
- `.wavefoundry/framework/scripts/dashboard_lib.py` — canonical reader implementation
- `.wavefoundry/framework/scripts/dashboard_server.py` — HTTP server and config loading
