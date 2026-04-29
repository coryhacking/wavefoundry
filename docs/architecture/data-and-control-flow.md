# Data and Control Flow

Owner: Engineering
Status: active
Last verified: 2026-04-28

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

**State read:** `.wavefoundry/framework/scripts/` (templates)
**State written:** `.claude/`, `.cursor/`, `.github/hooks/`
**Must not touch:** `.github/workflows/`, `.git/hooks/`

### Path 4: Framework Packaging

1. Operator runs `python3 .wavefoundry/framework/scripts/build_pack.py` (from repo root)
2. Script determines today's date; finds highest letter suffix for that date in output directory
3. Stamps `.wavefoundry/framework/VERSION` to `<date><letter>`
4. Zips the canonical framework tree into `wavefoundry-<date><letter>.zip` at repo root

**State read:** `.wavefoundry/framework/` tree, output directory listing
**State written:** `.wavefoundry/framework/VERSION`, zip archive at repo root
**Note:** zip file is gitignored; do not commit it

### Path 5: Future MCP Tool Calls (planned)

1. MCP client sends `wave.current` tool request
2. Server reads `docs/waves/` and `docs/agents/session-handoff.md` in configured target root
3. Returns structured JSON response with active wave state
4. For `code.search`: reads target repo file index (future SQLite index) or walks files

**State read:** target repository docs and files (within allowed roots)
**State written:** none for read-only tools; TBD for mutation tools

## State Ownership

| State | Owner | Read By | Written By |
|-------|-------|---------|-----------|
| `docs/workflow-config.json` | Engineering | lifecycle_id.py, docs_lint.py | Wave Framework init/upgrade |
| `docs/prompts/prompt-surface-manifest.json` | Engineering | docs_lint.py | seed-100 / upgrade |
| `.wavefoundry/framework/VERSION` | build_pack.py | docs_lint.py | build_pack.py |
| `.claude/settings.json` | Engineering | Claude Code | render_platform_surfaces.py (merge) |
| Wave records `docs/waves/<id>/wave.md` | wave-coordinator | wave.current (future MCP) | wave lifecycle commands |
