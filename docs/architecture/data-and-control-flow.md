# Data and Control Flow

Owner: Engineering
Status: active
Last verified: 2026-06-09

## Primary Control Paths

### Path 1: Lifecycle ID Generation

1. Operator mints an ID via the MCP `wave_create_wave` / `wave_new_<kind>` tools (preferred — they dedupe against on-disk IDs), or, when MCP is unavailable, the CLI `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind wave --slug <slug>`
2. Script reads `docs/workflow-config.json` for `lifecycle_id_policy.epoch_utc` and `hour_offset`
3. Computes hours since epoch → Crockford Base32 → `0xxxx` prefix ID
4. Prints ID to stdout for operator to use in wave or change documents

**State read:** `docs/workflow-config.json`
**State written:** none (ID is printed only)
**Domain owner of mutation:** operator (manually inserts ID into docs)

### Path 2: Docs Lint Gate

1. **Agents:** MCP **`wave_validate`** / **`wave_garden`** call the same `docs_lint.py` / `docs_gardener.py` backends as the CLI launchers. **Hooks / CI:** **`.wavefoundry/bin/docs-lint`** (canonical shell launcher) calls `python3 .wavefoundry/framework/scripts/docs_lint.py`. This repository does not rely on repo-root `./docs-lint`.
2. Linter reads `docs/prompts/prompt-surface-manifest.json`, checks `framework_revision` against `.wavefoundry/framework/VERSION`
3. Validates required prompt docs exist, metadata fields are present, wave/journal roots exist
4. Exits 0 on pass or non-zero with actionable error on failure

**State read:** `docs/`, `.wavefoundry/framework/VERSION`
**State written:** none
**Triggered by:** Claude Code post-edit hook (after any `docs/` file edit), manual operator run

### Path 3: Platform Surface Rendering

1. Operator or init process runs `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py`
2. Renderer generates `.claude/hooks/pre-edit`, `.claude/hooks/post-edit`, `.claude/hooks/pycache-cleanup`
3. Generates `.cursor/hooks/after-file-edit`, `.github/hooks/pre-tool-use`, `.github/hooks/post-tool-use`
4. Merges `.claude/settings.json` hooks (does not replace full file)
5. Writes `.mcp.json` and `.junie/mcp/mcp.json` with the `wavefoundry` MCP server entry

**State read:** `.wavefoundry/framework/scripts/` (templates)
**State written:** `.claude/`, `.cursor/`, `.github/hooks/`, `.junie/mcp/mcp.json`, `.mcp.json`
**Must not touch:** `.github/workflows/`, `.git/hooks/`

### Path 4: Framework Packaging

1. Operator runs `python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH` (from repo root)
2. Script derives the current lifecycle build suffix and validates manifest `framework_revision` against the packaged revision
3. Stamps `.wavefoundry/framework/VERSION` to `MAJOR.MINOR.PATCH+<build>`
4. Rebuilds the packaged framework semantic index at `.wavefoundry/framework/index/`
5. Zips the canonical framework tree, including `framework/index/`, into `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` under `~/.wavefoundry/dist/` by default

**State read:** `.wavefoundry/framework/` tree, output directory listing
**State written:** `.wavefoundry/framework/VERSION`, `.wavefoundry/framework/index/`, zip archive in the dist directory (or caller-supplied output dir)
**Note:** zip file is gitignored; do not commit it

### Path 5: Semantic Index Build

1. Operator runs `python3 .wavefoundry/framework/scripts/setup_index.py [--root .] [--full]`, the post-edit hook runs `indexer.py --content docs` directly in the background, or a qualifying MCP mutation requests a detached background docs refresh
2. `setup_index.py` verifies required packages are available in the active Python runtime and prints isolated tool-venv setup commands when missing
3. `setup_index.py` prewarms the embedding model cache, then verifies the same model in offline-only mode so later `docs_search` calls do not need network access
4. `setup_index.py --include-code` invokes a single `indexer.py --content all` subprocess (after dependency checks and model prewarm) so docs and code share one coordinated build and one merged `--project-include-prefix` policy
5. `walk_repo()` yields all non-excluded files (respects `.gitignore`, `.aiignore`, binary exclusions)
6. `chunker.py` dispatches each file: Python → AST-based; Markdown → header-split; others → line-window
7. Chunks classified as `code`, `doc`, or `seed` based on kind and path
8. `fastembed` embeds docs/seeds by default using `BAAI/bge-base-en-v1.5`; optional semantic code embeddings use the same model, and the code pass skips framework internal tests plus non-source/test/generated files unless `--include-tests` or `--include-generated` is passed
9. Project code indexing excludes `.wavefoundry/framework/` by default; repos can explicitly opt in additional excluded paths with `docs/workflow-config.json` -> `indexing.project_include_prefixes` (`docs` and `code` lists, consumed by `setup_index.py` and forwarded to `indexer.py --project-include-prefix`)
10. Project index written to `.wavefoundry/index/` and packaged framework index written to `.wavefoundry/framework/index/` (LanceDB `docs`/`code` tables, graph sidecars, and `meta.json`)
11. Subsequent runs are incremental: only files whose SHA-256 changed are re-chunked; existing LanceDB rows for those paths are compared by `chunk_hash` so unchanged chunk vectors can be reused and only changed/new chunks are re-embedded

**State read:** entire repository tree (excluding index, binaries, ignores)
**State written:** `.wavefoundry/index/` and `.wavefoundry/framework/index/` (gitignored)
**Triggered by:** manual run, post-edit hook (background subprocess after each file edit), or qualifying MCP mutation tools after successful docs writes

### Path 6: MCP Tool Calls

1. MCP client (Claude Code, Cursor, etc.) sends tool request via stdio to `server.py`
2. **Discovery tool** (`wave_help`): returns a structured catalogue of core verbs, compatibility tools, workflows, recommended chains, and exact next-call usage hints
3. **Search tools** (`docs_search`, `code_search`, `seed_get`): load project index from `.wavefoundry/index/` and packaged framework index from `.wavefoundry/framework/index/`; `docs_search` embeds queries in offline-only mode and falls back to lexical search with structured diagnostics when the index is not ready or the semantic model is unavailable offline; staleness detection is left to background reindex hooks rather than running a per-query repo walk
4. **Anchor tool** (`wave_map`): resolves `doc:` / `code:` / `seed:` addresses against the repo root (shared containment rules with future file-navigation tools) and returns trust metadata plus excerpts
5. **Inspection tools** (`wave_current`, `wave_list_waves`, `wave_list_plans`, `wave_get_change`, `wave_get_prompt`): read `docs/waves/`, `docs/plans/`, and `docs/prompts/` via regex parsing and return structured data plus recovery hints (with per-process caching for wave/plan lists and prompt resolution keyed by prompt file mtimes); `wave_current` returns all non-closed waves as `data.waves[]` (ordered active → planned → paused, with per-entry `next_action` — `implement_wave` / `prepare_wave` / `resume_wave`) and runs advisory drift detection against the active wave only; `wave_get_change(wave_id=...)` supports bulk mode returning all admitted changes for a wave in one call; `docs_search` responses include a `mode` field (`"semantic"` or `"lexical"`) for fallback transparency
5b. **Session handoff tools** (`wave_get_handoff`, `wave_set_handoff`): read and write `docs/agents/session-handoff.md` for cross-session state continuity; `wave_set_handoff` triggers a background docs-index refresh after successful writes
6. **Code navigation tools — exact layer** (`code_list_files`, `code_read`, `code_keyword`): walk repo files using indexer's ignore/exclusion rules, perform substring search or ranged file reads; all paths validated against repo root to prevent traversal; return deterministic path/line/snippet results
6b. **Code navigation tools — symbol layer** (`code_definition`, `code_references`): Python AST definitions plus tree-sitter-backed Java/C#/JS/TS navigation, with structural/text fallback for other supported non-Python languages and broad keyword fallback when unmatched
7. **Creation tools** (`wave_new_*`): import `lifecycle_id.py` directly, generate change ID, scaffold docs in `docs/plans/`, and return repeat-safe diagnostics when the artifact already exists
8. **Lifecycle mutation tools** (`wave_add_change`, `wave_remove_change`, `wave_prepare`): update the wave record and keep admitted change docs in the wave folder; add-change relocates immediately and inserts the new `Change ID:` block inside the wave's `## Changes` section (tail-append, preserving admission order), remove-change moves active docs back to `docs/plans/`, and prepare validates or repairs placement drift; `wave_prepare` decouples readiness from activation (wave 1p45l): `mode='ready'` records full readiness and leaves the wave `planned` (readied) with no guard, while `mode='create'` runs the single-OPEN guard and flips `planned→active`. The single-OPEN invariant (≤1 wave `active`/`implementing`) is enforced at the activation transitions — `wave_implement`, `wave_reopen`, and `wave_prepare(create)` — via the `another_wave_active` diagnostic (recovery: pause the open wave, or ready the target with `mode='ready'`), not at readiness; successful write paths request a detached background docs-index refresh so non-hook clients do not depend on editor hooks for search freshness
9. **Review and closure tools** (`wave_review`, `wave_close`, `wave_pause`): review remains read-first but now opportunistically requests a detached background docs refresh, while write paths trigger one after successful mutations; `wave_pause` transitions the target wave from `active` to `paused` (idempotent on paused, advisory on other states) in addition to writing the session-handoff entry, so the paused wave drops out of `wave_current`'s OPEN slot and frees the single-OPEN slot for a different wave to be opened; duplicate refreshes are throttled with repo-local runtime state so repeated MCP calls do not spawn an unbounded queue
10. **Explicit index maintenance tools** (`wave_index_health`, `wave_index_build`): `wave_index_health` reports stale/missing layer status without touching the hot search path; `wave_index_build` runs `setup_index.py` (project `content=all`, docs+code) or `indexer.py` (project `content=docs|code`, or framework-layer docs) synchronously for deterministic index builds (`mode='update'` vs `mode='rebuild'`), returns structured statistics, and invalidates the in-process loaded index state afterward
11. **Operations tools** (`wave_validate`, `wave_garden`, `wave_sync_surfaces`): invoke `docs_lint.py`, `docs_gardener.py`, `render_platform_surfaces.py` as subprocesses and return structured pass/fail

### Path 6b: MCP Resource and Resource-Template Reads

1. MCP client requests a **resource** or **resource template** URI via the MCP resources protocol
2. **Stable resources** (`wavefoundry://overview`, `wavefoundry://prompts`, `wavefoundry://architecture/current-state`, `wavefoundry://wave/current`, `wavefoundry://session-handoff`, `wavefoundry://agents`, `wavefoundry://index/status`, `wavefoundry://graph/status`, `wavefoundry://graph/communities`, `wavefoundry://waves`): read the corresponding file(s) or index artifacts and return raw markdown text; missing files return a structured `# Not Found` markdown message
3. **Resource templates** (`wavefoundry://change/{change_id}`, `wavefoundry://wave/{wave_id}`, `wavefoundry://prompt/{slug}`, `wavefoundry://seed/{slug}`, `wavefoundry://architecture/{slug}`): parameterized reads of the matching doc in `docs/` or `.wavefoundry/framework/seeds/`; matched by name prefix; unknown identifiers return `# Not Found`
4. All resource reads are **strictly read-only** — no writes, no side effects, no background refresh requests. Use tools when a structured response envelope (`diagnostics`, `next_tools`, `usage`) is needed.

**State read:** `docs/`, `.wavefoundry/framework/seeds/`
**State written:** none
**Transport:** stdio (FastMCP MCP resources protocol)

**State read (Path 6):** `.wavefoundry/index/`, `.wavefoundry/framework/index/`, `docs/waves/`, `docs/plans/`, `docs/prompts/`, `docs/agents/session-handoff.md`
**State written (Path 6):** `docs/plans/`, `docs/waves/`, `docs/agents/session-handoff.md` (handoff tools), `docs/` metadata (garden tool)
**Transport:** stdio (FastMCP)

### Path 7: Local Dashboard

1. Operator or agent runs `python3 .wavefoundry/framework/scripts/dashboard_server.py --root . [--open]`
2. Script reads `docs/workflow-config.json` `dashboard` settings to determine host, preferred port, fallback range, poll interval, and optional `include_dirs` for file-activity metrics
3. Script resolves the runtime port using a preference-then-fallback strategy across a configured range; reuses the recorded port from `.wavefoundry/dashboard-server.json` when available and free
4. Script writes host-local endpoint metadata to `.wavefoundry/dashboard-server.json` (pid, host, port, url, started_at)
5. Browser loads `dashboard.html` (shell), `dashboard.css` (design system tokens + layout), and `dashboard.js` (React application) from the loopback server; pinned React, React DOM, force-graph, and elkjs load from unpkg CDN URLs embedded in the HTML. No build toolchain required in target repos; graph scripts need network (or cache) on first load.
6. Browser React app polls `/api/dashboard` on a graduated backoff schedule (2 → 5 → 8 → 13 → 21 → 30 s); resets to 2 s when the snapshot hash changes; UI state (selected agent, scroll) stays in browser memory
7. On each poll, `dashboard_lib.collect_dashboard_snapshot` assembles the snapshot from:
   - `docs/waves/` and `docs/plans/` — wave and change records (status, tasks, AC counts, progress logs, participants, review evidence)
   - `docs/agents/` tree including `personas/`, `specialists/`, `journals/` subdirectories — agent/persona metadata and section content for the detail dialog
   - `docs/agents/session-handoff.md` — active wave and recent progress context
   - `docs/prompts/prompt-surface-manifest.json` — public prompt count and framework revision
   - `docs/repo-profile.json` — project archetypes
   - `.wavefoundry/framework/VERSION` — framework version string
   - File-system mtime scan for `files_updated_today` and `files_updated_week` activity metrics

**State read:** `docs/workflow-config.json`, `docs/repo-profile.json`, `docs/waves/`, `docs/plans/`, `docs/prompts/prompt-surface-manifest.json`, `docs/agents/` tree, `.wavefoundry/framework/VERSION`, repo file mtimes
**State written:** `.wavefoundry/dashboard-server.json`
**Transport:** localhost HTTP on loopback only; browser never speaks to MCP or git directly

### Path 8: Daemon-Triggered Incremental Index Rebuild

Opt-in via `dashboard.auto_index: true` in `docs/workflow-config.json` (default: false).

1. `SnapshotStore._watch_loop` runs every `_WATCH_INTERVAL` seconds; when any watched path (excluding `.wavefoundry/index/index-build-stats.json`) has a changed mtime, it calls `IndexBuilder.signal_change()`
2. On startup and every `_STALENESS_CHECK_INTERVAL` seconds (default 60 s), `SnapshotStore` calls `_index_is_stale()` — a git-based check comparing uncommitted changes and commits since `meta.json`'s `built_at`; a stale result calls `IndexBuilder.signal_change()`
3. `IndexBuilder` arms a debounce timer for `auto_index_delay_seconds` (default 30 s, min 10 s); if a second signal arrives during an active build, the rebuild is re-armed for after completion — only one build runs at a time
4. After the settling delay, `IndexBuilder` spawns an incremental indexer subprocess using the same Python interpreter that started the server, with `start_new_session=True` and `close_fds=True` to prevent file-handle leakage
5. `SnapshotStore._rebuild()` overlays `IndexBuilder.get_status()` (`idle` | `running` | `done` | `failed`) onto `health.index.project` after `collect_dashboard_snapshot()` returns; build status is injected at the server layer, not in `dashboard_lib`
6. On build completion, `SnapshotStore._on_index_build_done` calls `_rebuild()` **before** `_notify_sse()` so the browser fetches a snapshot that already contains the fresh `index-build-stats.json` data
7. External index builds (manual CLI, MCP `wave_index_build`) are detected when `_watch_loop` sees a mtime change on `.wavefoundry/index/index-build-stats.json`; this triggers `SnapshotStore._rebuild()` so the dashboard reflects the new chunk counts without any daemon rebuild

**State read:** `docs/workflow-config.json` (auto_index config), `.wavefoundry/index/index-build-stats.json`, repo file mtimes, git state (staleness check)
**State written:** `.wavefoundry/index/` (via indexer subprocess — idempotent, atomic temp-then-rename)
**Transport:** loopback only; subprocess uses the same Python interpreter as the server

## State Ownership

| State | Owner | Read By | Written By |
|-------|-------|---------|-----------|
| `docs/workflow-config.json` | Engineering | lifecycle_id.py, docs_lint.py | Wave Framework init/upgrade |
| `docs/prompts/prompt-surface-manifest.json` | Engineering | docs_lint.py | seed-100 / upgrade |
| `.wavefoundry/framework/VERSION` | build_pack.py | docs_lint.py | build_pack.py |
| `.claude/settings.json` | Engineering | Claude Code | render_platform_surfaces.py (merge) |
| `.mcp.json` | Engineering | Claude Code and compatible clients | render_platform_surfaces.py |
| `.junie/mcp/mcp.json` | Engineering | JetBrains Junie / AI Assistant MCP | render_platform_surfaces.py |
| `.wavefoundry/index/` | indexer.py | server.py | indexer.py (incremental) |
| `.wavefoundry/dashboard-server.json` | dashboard_server.py | dashboard_server.py | dashboard_server.py |
| Background refresh state `.wavefoundry/index/background-refresh.json` | MCP server runtime | server.py background refresh helper | MCP mutation/review tools that request detached docs-index refresh |
| Wave records `docs/waves/<id>/wave.md` | wave-coordinator | wave inspection tools | wave lifecycle commands |
| Change docs `docs/plans/<id>.md` | Engineering | wave_get_change | wave_new_* tools, operator, wave_remove_change |
| Change docs `docs/waves/<wave-id>/<id>.md` | Active wave | wave_get_change, wave lifecycle tools | wave_add_change, wave_prepare |
| Session handoff `docs/agents/session-handoff.md` | Active session | wave_get_handoff, MCP resource `wavefoundry://session-handoff` | wave_set_handoff |
