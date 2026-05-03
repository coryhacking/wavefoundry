# Data and Control Flow

Owner: Engineering
Status: active
Last verified: 2026-05-03

## Primary Control Paths

### Path 1: Lifecycle ID Generation

1. Operator runs `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind wave --slug <slug>`
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

1. Operator runs `python3 .wavefoundry/framework/scripts/build_pack.py` (from repo root)
2. Script determines today's date; finds highest letter suffix for that date in output directory
3. Stamps `.wavefoundry/framework/VERSION` to `<date><letter>`
4. Rebuilds the packaged framework semantic index at `.wavefoundry/framework/index/`
5. Zips the canonical framework tree, including `framework/index/`, into `wavefoundry-<date><letter>.zip` at repo root

**State read:** `.wavefoundry/framework/` tree, output directory listing
**State written:** `.wavefoundry/framework/VERSION`, `.wavefoundry/framework/index/`, zip archive at repo root
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
10. Project index written to `.wavefoundry/index/` and packaged framework index written to `.wavefoundry/framework/index/` (docs.npy, docs.json, code.npy, code.json, meta.json)
11. Subsequent runs are incremental: only files whose SHA-256 changed are re-chunked and re-embedded

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
6. **Code navigation tools — exact layer** (`code_list_files`, `code_read`, `code_keyword_search`): walk repo files using indexer's ignore/exclusion rules, perform substring search or ranged file reads; all paths validated against repo root to prevent traversal; return deterministic path/line/snippet results
6b. **Code navigation tools — symbol layer** (`code_definition`, `code_references`): Python AST-based definition/reference search; non-Python returns explicit unsupported response with `code_keyword_search` fallback hint
7. **Creation tools** (`wave_new_*`): import `lifecycle_id.py` directly, generate change ID, scaffold docs in `docs/plans/`, and return repeat-safe diagnostics when the artifact already exists
8. **Lifecycle mutation tools** (`wave_add_change`, `wave_remove_change`, `wave_prepare`): update the wave record and keep admitted change docs in the wave folder; add-change relocates immediately and inserts the new `Change ID:` block inside the wave's `## Changes` section (tail-append, preserving admission order), remove-change moves active docs back to `docs/plans/`, and prepare validates or repairs placement drift; `wave_prepare` enforces the single-active-wave invariant by returning an `another_wave_active` diagnostic (with `wave_pause` recovery) when any other wave is already `active`; successful write paths request a detached background docs-index refresh so non-hook clients do not depend on editor hooks for search freshness
9. **Review and closure tools** (`wave_review`, `wave_close`, `wave_pause`): review remains read-first but now opportunistically requests a detached background docs refresh, while write paths trigger one after successful mutations; `wave_pause` transitions the target wave from `active` to `paused` (idempotent on paused, advisory on other states) in addition to writing the session-handoff entry, so the paused wave drops out of `wave_current`'s active slot and frees the single-active-wave invariant for a different wave; duplicate refreshes are throttled with repo-local runtime state so repeated MCP calls do not spawn an unbounded queue
10. **Explicit index maintenance tools** (`wave_index_health`, `wave_index_build`): `wave_index_health` reports stale/missing layer status without touching the hot search path; `wave_index_build` runs `setup_index.py` (project `content=all`, docs+code) or `indexer.py` (project `content=docs|code`, or framework-layer docs) synchronously for deterministic index builds (`mode='update'` vs `mode='rebuild'`), returns structured statistics, and invalidates the in-process loaded index state afterward
11. **Operations tools** (`wave_validate`, `wave_garden`, `wave_sync_surfaces`): invoke `docs_lint.py`, `docs_gardener.py`, `render_platform_surfaces.py` as subprocesses and return structured pass/fail

### Path 6b: MCP Resource and Resource-Template Reads

1. MCP client requests a **resource** or **resource template** URI via the MCP resources protocol
2. **Stable resources** (`wavefoundry://overview`, `wavefoundry://prompts`, `wavefoundry://architecture/current-state`, `wavefoundry://wave/current`, `wavefoundry://session-handoff`): read the corresponding file(s) from `docs/` and return raw markdown text; missing files return a structured `# Not Found` markdown message
3. **Resource templates** (`wavefoundry://change/{change_id}`, `wavefoundry://wave/{wave_id}`, `wavefoundry://prompt/{slug}`, `wavefoundry://seed/{slug}`, `wavefoundry://architecture/{slug}`): parameterized reads of the matching doc in `docs/` or `.wavefoundry/framework/seeds/`; matched by name prefix; unknown identifiers return `# Not Found`
4. All resource reads are **strictly read-only** — no writes, no side effects, no background refresh requests. Use tools when a structured response envelope (`diagnostics`, `next_tools`, `usage`) is needed.

**State read:** `docs/`, `.wavefoundry/framework/seeds/`
**State written:** none
**Transport:** stdio (FastMCP MCP resources protocol)

**State read (Path 6):** `.wavefoundry/index/`, `.wavefoundry/framework/index/`, `docs/waves/`, `docs/plans/`, `docs/prompts/`, `docs/agents/session-handoff.md`
**State written (Path 6):** `docs/plans/`, `docs/waves/`, `docs/agents/session-handoff.md` (handoff tools), `docs/` metadata (garden tool)
**Transport:** stdio (FastMCP)

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
| Background refresh state `.wavefoundry/index/background-refresh.json` | MCP server runtime | server.py background refresh helper | MCP mutation/review tools that request detached docs-index refresh |
| Wave records `docs/waves/<id>/wave.md` | wave-coordinator | wave inspection tools | wave lifecycle commands |
| Change docs `docs/plans/<id>.md` | Engineering | wave_get_change | wave_new_* tools, operator, wave_remove_change |
| Change docs `docs/waves/<wave-id>/<id>.md` | Active wave | wave_get_change, wave lifecycle tools | wave_add_change, wave_prepare |
| Session handoff `docs/agents/session-handoff.md` | Active session | wave_get_handoff, MCP resource `wavefoundry://session-handoff` | wave_set_handoff |
