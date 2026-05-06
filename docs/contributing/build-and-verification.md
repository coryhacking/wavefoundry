# Build and Verification

Owner: Engineering
Status: active
Last verified: 2026-05-06

## Verification Commands

Run these from the repository root to verify the Wavefoundry self-hosted surface is healthy:

**Agents (MCP attached):** Prefer **`wave_garden`** then **`wave_validate`** (or **`wave_audit`** for a combined wave + lint + index snapshot) instead of shelling out to the bin launchers. Use the tools’ structured results to fix failures.

**Operators / CI / no MCP:** Use the shell sequence below.

```bash
# Docs gate (metadata + prompt surface + manifest validation)
.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint

# Framework script tests (no bytecode)
python3 .wavefoundry/framework/scripts/run_tests.py
```

## Semantic Index And Offline Search

Build or refresh the local semantic index with:

```bash
python3 .wavefoundry/framework/scripts/setup_index.py
```

What this does:
- checks required runtime packages
- prewarms the docs embedding model cache
- rebuilds the project docs index (seeds + docs)

**MCP is available as soon as the docs index build completes** (~2.5 min). The code index is separate and optional.

### Two-phase onboarding

For new developer onboarding or post-upgrade rebuilds, use the docs-first approach to unblock MCP immediately while the code index builds in the background:

```bash
# Phase 1: docs index — unblocks all MCP tools immediately (~2.5 min)
python3 .wavefoundry/framework/scripts/setup_index.py

# Phase 2: code index — builds in the background, foreground returns immediately
python3 .wavefoundry/framework/scripts/setup_index.py --background-code
```

`--background-code` builds the docs index synchronously, then spawns a detached background process for code model prewarm and code embedding. Progress is written to `.wavefoundry/index/background-build.log`. Call `wave_index_health()` to check whether the background build is still running.

To build both synchronously (e.g. CI):

```bash
python3 .wavefoundry/framework/scripts/setup_index.py --include-code
```

### Upgrade rebuild requirement

When a pack upgrade bumps `CHUNKER_VERSION`, a full rebuild is required for both docs and code layers — file hashes alone will not detect this. The full rebuild takes approximately 6 minutes (docs ~2.5 min + code ~3.5 min).

`wave_index_health` will emit a `chunker_version_mismatch` advisory (distinct from `index_stale`) when the index was built with an older chunker version. If you see this advisory, run:

```bash
python3 .wavefoundry/framework/scripts/setup_index.py --full
# or docs-first, then background code:
python3 .wavefoundry/framework/scripts/setup_index.py --full
python3 .wavefoundry/framework/scripts/setup_index.py --background-code --full
```

If the repo needs extra project index roots beyond the default, declare them explicitly in `docs/workflow-config.json` under `indexing.project_include_prefixes`. Use repo-relative `docs` and `code` lists rather than one-off booleans. Wavefoundry uses this in self-hosting mode to include `.wavefoundry/framework/scripts` in project code search without changing the default for ordinary target repos.

### Update vs rebuild — decision table

| Situation | Action |
|---|---|
| Docs changed during a wave (post-edit hook ran automatically) | No manual action needed — MCP tools trigger a background refresh on write |
| Hook didn't run (Codex, Warp, or non-hook env) and docs feel stale | **Update:** `wave_index_build(content="docs", mode="update")` — re-indexes changed files only |
| `wave_index_health` reports `index_stale` | **Update:** `wave_index_build(content="docs", mode="update")` |
| `wave_index_health` reports `index_missing` | **Update (creates index):** `wave_index_build(content="docs", mode="update")` or `setup_index.py` |
| `wave_index_health` reports `chunker_version_mismatch` after a pack upgrade | **Full rebuild required** — file hashes alone won't detect the version change. See *Upgrade rebuild requirement* above |
| Code navigation (`code_search`, `code_read`) feels stale or was never built | **Code update:** `wave_index_build(content="code", mode="update")` — or `setup_index.py --background-code` |
| Framework seeds changed (self-hosting only) | **Framework layer:** `wave_index_build(content="docs", layer="framework")` |
| First install / clean environment | `setup_index.py` (docs, ~2.5 min) then `setup_index.py --background-code` (code, background) |
| CI deterministic full build | `setup_index.py --include-code` (~6 min, both layers synchronous) |

**Update** re-indexes only changed files (fast, uses file hashes). **Rebuild** (`--full` / `mode="rebuild"`) ignores hashes and reprocesses everything — use it when `CHUNKER_VERSION` changed or the index is known corrupt.

If `docs_search` falls back to lexical mode and you need to know whether the semantic index is stale or missing, call `wave_index_health` explicitly. In clients that do not execute the post-edit hook path, assume manual reindexing is required after meaningful docs changes.

Wavefoundry MCP doc-mutating tools also request a detached background docs-index refresh after successful writes. That improves freshness in non-hook environments such as Codex, but it is best-effort and non-blocking; use `wave_index_health` when you need an explicit health verdict or run `wave_index_build` for a deterministic result.

`wave_index_build` accepts: `content` (`docs` | `code` | `all`), `mode` (`update` | `rebuild`), `layer` (`project` | `framework`). Successful responses include structured `stats` confirming file count, chunk count, and whether the run was already up to date.

## Docs Gate

Same checks whether you run **`wave_validate`** / **`wave_garden`** over MCP or the bin scripts below.

`.wavefoundry/bin/docs-lint` validates:
- Required prompt docs exist under `docs/prompts/`
- `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches `.wavefoundry/framework/VERSION`
- Required metadata fields (`Owner:`, `Status:`, `Last verified:`) on canonical docs
- Wave and journal root directories exist

`.wavefoundry/bin/docs-gardener` refreshes stale metadata timestamps.

Both launchers live under `.wavefoundry/bin/` and delegate to `.wavefoundry/framework/scripts/`. This repository does not ship repo-root `./docs-lint` or `./docs-gardener` shims. **Agents should use MCP `wave_validate` and `wave_garden` first**; reserve **`.wavefoundry/bin/docs-lint`** / **`.wavefoundry/bin/docs-gardener`** for hooks, CI, and hosts without MCP.

## Framework Script Hygiene

Run tests without writing bytecode:

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py
```

Or use the run_tests.py wrapper which already sets `-B`. If `__pycache__` directories appeared anyway, clean them:

```bash
find .wavefoundry/framework/scripts -type d -name '__pycache__' -prune -exec rm -rf {} \;
```

## Wave Framework Pack Upgrade Verification

When a new framework version is available, upgrade using this procedure:

**Bring the pack in:**

Option A (zip drop): Place a `wavefoundry-<date><letter>.zip` at the repository root and run **Upgrade wave framework**. The upgrade seed (`seed-160`) unpacks the lexicographically greatest zip into `.wavefoundry/framework/`, runs `render_platform_surfaces.py`, and continues full reconciliation.

Option B (direct merge): Merge or copy into `.wavefoundry/framework/` then run **Upgrade wave framework**.

**What the unpack step ignores:** archives with other names (e.g. `agent-workflows.zip`) and zips outside the repository root.

**After bringing in the pack:**

```bash
# Run framework tests
python3 .wavefoundry/framework/scripts/run_tests.py

# Run docs gate
.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint

# Review diff of pack changes, hooks, docs/prompts/, manifests
# Then commit (operator-owned — see Git commits below)
```

**Upgrade-path checks for new features (2026-04-30+):**

- Host MCP surfaces updated by `render_platform_surfaces.py`:
  - `.cursor/mcp.json` contains `mcpServers.wavefoundry`
  - `.mcp.json` and `.junie/mcp/mcp.json` include the Wavefoundry stdio entry when those hosts are used
- Canonical CLI launchers exist and resolve to packaged scripts:
  - `.wavefoundry/bin/docs-lint`
  - `.wavefoundry/bin/docs-gardener`
- MCP recovery tools from the upgraded server are available:
  - `wave_audit` (combined wave + lint + index check)
  - `wave_index_build` (deterministic project/framework index rebuild path)

**For full upgrade procedure:** see `docs/prompts/upgrade-wavefoundry.prompt.md` and `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`.

**`build_pack.py` semantics:** default zip date is today (local ISO); letter suffix is the next letter after the maximum suffix already present for that date in the output directory (not the first missing gap). The script stamps `.wavefoundry/framework/VERSION` to `<date><letter>` before writing the archive. Use `--date` only for tests or exceptional rebuilds.

## Git Commits

**Operator-owned.** Agents must not run `git commit` unless the operator explicitly instructs them to finalize that commit in the **current** request after reviewing the diff. Default agent behavior is to hand off a suggested commit message and diff for the operator to commit locally.

This policy applies to all changes: framework source edits, self-hosted docs changes, platform surface renders, and packaging builds.
