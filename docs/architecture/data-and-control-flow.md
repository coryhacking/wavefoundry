# Data and Control Flow

Owner: Engineering
Status: active
Last verified: 2026-04-29

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

1. `./docs-lint` (wrapper) calls `python3 .wavefoundry/framework/scripts/docs_lint.py`
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

1. Operator runs `python3 .wavefoundry/framework/scripts/setup_index.py [--root .] [--full]`, or the post-edit hook runs `indexer.py --content docs` directly in the background
2. `setup_index.py` verifies required packages are available in the active Python runtime and prints isolated tool-venv setup commands when missing
3. `setup_index.py --include-code` runs docs indexing and code indexing as separate subprocesses so each pass has an isolated runtime footprint
4. `walk_repo()` yields all non-excluded files (respects `.gitignore`, `.aiignore`, binary exclusions)
5. `chunker.py` dispatches each file: Python → AST-based; Markdown → header-split; others → line-window
6. Chunks classified as `code`, `doc`, or `seed` based on kind and path
7. `fastembed` embeds docs/seeds by default using `BAAI/bge-small-en-v1.5`; optional semantic code embeddings use the same lightweight model, and the code pass skips framework internal tests plus non-source/test/generated files unless `--include-tests` or `--include-generated` is passed
8. Project index written to `.wavefoundry/index/` and packaged framework index written to `.wavefoundry/framework/index/` (docs.npy, docs.json, code.npy, code.json, meta.json)
9. Subsequent runs are incremental: only files whose SHA-256 changed are re-chunked and re-embedded

**State read:** entire repository tree (excluding index, binaries, ignores)
**State written:** `.wavefoundry/index/` and `.wavefoundry/framework/index/` (gitignored)
**Triggered by:** manual run, or post-edit hook (background subprocess after each file edit)

### Path 6: MCP Tool Calls

1. MCP client (Claude Code, Cursor, etc.) sends tool request via stdio to `server.py`
2. **Discovery tool** (`wave_help`): returns a structured catalogue of core verbs, compatibility tools, workflows, recommended chains, and exact next-call usage hints
3. **Search tools** (`docs_search`, `code_search`, `seed_get`): load project index from `.wavefoundry/index/` and packaged framework index from `.wavefoundry/framework/index/`, embed query with fastembed, and return cosine-ranked chunks inside a shared response envelope with trust labels and stable result IDs
4. **Anchor tool** (`wave_map`): resolves `doc:` / `code:` / `seed:` addresses against the repo root (shared containment rules with future file-navigation tools) and returns trust metadata plus excerpts
5. **Inspection tools** (`wave_current`, `wave_list_waves`, `wave_list_plans`, `wave_get_change`, `wave_get_prompt`): read `docs/waves/`, `docs/plans/`, and `docs/prompts/` via regex parsing and return structured data plus recovery hints (with per-process caching for wave/plan lists and prompt resolution keyed by prompt file mtimes)
6. **Creation tools** (`wave_change_create` and `wave_new_*` wrappers): import `lifecycle_id.py` directly, generate change ID, dry-run or scaffold docs in `docs/plans/`, and return repeat-safe diagnostics when the artifact already exists
7. **Operations tools** (`wave_validate`, `wave_garden`, `wave_sync_surfaces`): invoke `docs_lint.py`, `docs_gardener.py`, `render_platform_surfaces.py` as subprocesses and return structured pass/fail

**State read:** `.wavefoundry/index/`, `.wavefoundry/framework/index/`, `docs/waves/`, `docs/plans/`, `docs/prompts/`
**State written:** `docs/plans/` (creation tools only), `docs/` metadata (garden tool)
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
| Wave records `docs/waves/<id>/wave.md` | wave-coordinator | wave inspection tools | wave lifecycle commands |
| Change docs `docs/plans/<id>.md` | Engineering | wave_get_change | wave_new_* tools, operator |
