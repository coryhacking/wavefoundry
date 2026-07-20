# Build and Verification

Owner: Engineering
Status: active
Last verified: 2026-07-20

## Verification Commands

Run these from the repository root to verify the Wavefoundry self-hosted surface is healthy:

**Agents (MCP attached):** Prefer **`wf_garden_docs`** then **`wf_validate_docs`** (or **`wf_audit`** for a combined wave + lint + index snapshot) instead of shelling out to the bin launchers. Use the tools’ structured results to fix failures.

**Operators / CI / no MCP:** Use the shell sequence below.

```bash
# Docs gate (metadata + prompt surface + manifest validation)
wf docs-gardener && wf docs-lint

# Framework script tests (no bytecode)
python3 .wavefoundry/framework/scripts/run_tests.py
```

## Semantic Index And Offline Search

Build or refresh the local semantic index with:

```bash
wf update-indexes
```

What this does:
- checks required runtime packages
- evaluates the local embedding execution provider
- prewarms the docs and code embedding model caches
- rebuilds the project docs index (seeds + docs), semantic code index, and graph index in the foreground

**MCP search is complete when setup returns.** The default setup path treats docs and code the same: both semantic layers build in the foreground.

### Onboarding

For new developer onboarding or post-upgrade rebuilds, use the default foreground build:

```bash
wf setup
# or, after setup already exists:
wf update-indexes
```

`--include-code` remains accepted for explicit CI/full-build callers, but it is redundant with the default code-included setup path:

```bash
wf setup --include-code
```

Use the background flags only when a foreground layer must be prioritized:

```bash
wf setup --background-code  # docs/graph foreground, code detached
wf setup --background-docs  # code foreground, docs detached
```

Progress for detached setup builds is written under `.wavefoundry/logs/`. Call `index_health()` or `index_build_status(layer="code"|"docs")` to check whether a background build is still running.

### Embedding provider diagnostics

Setup prints one provider line before model prewarm:

```text
Embedding provider: selected=CPUExecutionProvider; providers=['CPUExecutionProvider']; available=[...]; reason=...
```

Provider priority is CUDA/NVIDIA first, verified Apple CoreML second, explicit secondary ONNX
providers such as DirectML/OpenVINO/MIGraphX/ROCm third, then CPU. There is no generic GPU tier.
On NVIDIA machines, setup plans the `fastembed-gpu` dependency path when `nvidia-smi` reports a
GPU. If the machine has NVIDIA hardware but ONNX Runtime still does not expose
`CUDAExecutionProvider`, setup continues on CPU and prints a remediation hint to install a
CUDA-capable FastEmbed/ONNX Runtime stack, then rerun setup.

On Apple Silicon, `CoreMLExecutionProvider` is accepted whenever ONNX Runtime exposes it and the
probe produces correct embeddings — it is **not** required to beat CPU by the `min_speedup` margin
that gates the secondary ONNX providers. CoreML transparently partitions unsupported operators back
to CPU, so "CoreML selected, CPU still does meaningful work" is the intended local-setup contract,
not a failure. Selecting CoreML does **not** imply a large speedup: on the current FastEmbed model
the full framework docs rebuild measured ≈420s under CoreML vs ≈422s on the prior CPU run (no
material acceleration; high CPU usage throughout is expected from provider partitioning). The
`WAVEFOUNDRY_EMBED_PROVIDER_MIN_SPEEDUP` gate (default 1.25×) still applies to the secondary ONNX
providers (DirectML/OpenVINO/MIGraphX/ROCm), and CUDA is selected from availability without a probe.

Operators can force a provider family for diagnosis with `WAVEFOUNDRY_EMBED_PROVIDER`:
`cpu`, `cuda`, `coreml`, `directml`, `openvino`, `migraphx`, or `rocm`.

### Upgrade rebuild requirement

When a pack upgrade bumps `CHUNKER_VERSION`, a full rebuild is required for both docs and code layers — file hashes alone will not detect this. The full rebuild takes approximately 6 minutes (docs ~2.5 min + code ~3.5 min).

`index_health` will emit a `chunker_version_mismatch` advisory (distinct from `index_stale`) when the index was built with an older chunker version. If you see this advisory, run:

```bash
wf setup --full
# explicit CI/full rebuild form, equivalent for code inclusion:
wf setup --full --include-code
```

If the repo needs extra project index roots beyond the default, declare them explicitly in `docs/workflow-config.json` under `indexing.project_include_prefixes`. Use repo-relative `docs` and `code` lists rather than one-off booleans. Wavefoundry uses this in self-hosting mode to include `.wavefoundry/framework/scripts` in project code search without changing the default for ordinary target repos.

### Dependency version sync on upgrade

The tool-venv dependency check is **version-aware**: when a pack pins a new version of a dependency (e.g. `lancedb==0.33.0`), `wf setup` — and `wf_upgrade`, whose phase-4 index step already runs the same `ensure_deps` check — move an **existing** install to the pinned version, not just fresh installs. An exact (`==`) pin installs exactly that version (including downgrading a newer build to the framework's validated one); a range pin (`>=`, `<`) leaves any satisfying installed version untouched. Unpinned dependencies keep presence-only behavior (installed → not touched). Model weights are refreshed the same way — `prewarm_models` runs on each phase-4 setup invocation, so new/changed embedding and reranker models download during the upgrade. No separate command is needed for either.

### Update vs rebuild — decision table

| Situation | Action |
|---|---|
| Docs changed during a wave (post-edit hook ran automatically) | No manual action needed — MCP tools trigger a background refresh on write |
| Hook didn't run (Codex, Warp, or non-hook env) and docs feel stale | **Update:** `index_build(content="docs", mode="update")` — re-indexes changed files only |
| `index_health` reports `index_stale` | **Update:** `index_build(content="docs", mode="update")` |
| `index_health` reports `index_missing` | **Update (creates index):** `index_build(content="docs", mode="update")` or `wf update-indexes` |
| `index_health` reports `chunker_version_mismatch` after a pack upgrade | **Full rebuild required** — file hashes alone won't detect the version change. See *Upgrade rebuild requirement* above |
| `index_health` reports `chunk_index_undercovered` (lexical FTS/registry materially behind Lance) | **Derived rebuild:** `index_build(content="fts")` — rebuilds the FTS/registry from Lance from scratch, embedding-free, in seconds; any ordinary build's reconcile also backfills it (including zero-change builds) |
| Code navigation (`code_search`, `code_read`) feels stale or was never built | **Code update:** `index_build(content="code", mode="update")` — or `wf update-indexes`. Since wave 1sc7c each semantic layer tracks the hash it last embedded per path (index-state store `layer_path_state`), so a scoped update always detects the layer's own staleness — the historical no-op (content-scoped builds stamping hashes they never embedded, with the post-edit hook running docs-only) is fixed, and previously poisoned repos heal automatically on their first post-upgrade build (empty layer state reads as all-stale; vectors are reused by content hash, so the heal re-chunks without re-embedding unchanged content) |
| Framework seeds changed in the Wavefoundry source repo itself | **Project docs update:** `index_build(content="docs", mode="update")`; framework seeds are folded into the project docs index |
| First install / clean environment | `wf setup` (docs, code, and graph foreground) |
| CI deterministic full build | `wf setup --include-code` (~6 min, explicit docs and code synchronous form) |

**Update** re-indexes only changed files (fast, uses file hashes). **Rebuild** (`--full` / `mode="rebuild"`) ignores hashes and reprocesses everything — use it when `CHUNKER_VERSION` changed or the index is known corrupt.

After an ordinary upgrade, if search still looks missing or stale, stop and verify that the upgraded MCP server has been restarted before rebuilding anything. There is a single semantic index — the project index at `.wavefoundry/index/` — and framework seeds fold into that project docs index at setup/upgrade; there is no separate framework index to rebuild.

Since wave 1seav every search response tells you WHY it degraded: check `search_mode` (`lexical_fallback` = BM25 from the published FTS layer; `live_fallback` = no published index at all) and `fallback_reason` (`model_unavailable`, `index_not_ready`, `query_failed`, …) before reaching for `index_health` — the explicit health verdict is still authoritative when you need layer-level detail. In clients that do not execute the post-edit hook path, assume manual reindexing is required after meaningful docs changes.

**State recovery (wave 1sed7 — SQLite-only):** `.wavefoundry/index/index-state.sqlite` is the sole semantic-index state authority; there is no `meta.json`. A search tool returning `index_not_ready` means the store has no completed build epoch (building, interrupted, or never built) or a build fenced mid-query — check `index_build_status` and retry after the build completes. A missing/corrupt/deleted store is never data loss: the next build converges all layers by re-chunking with Lance vector reuse (readiness state cannot be manufactured per layer, so convergence is deliberately all-layer). A legacy `meta.json` from a pre-1sed7 install is never read by anything — not even the upgrade's version probes (an absent/empty store reads as unknown, which forces convergence) — and is removed automatically after the first successful build. Never treat a failed build's output as current: a build that reports `failed: true` left the epoch incomplete on purpose (and exits non-zero through the CLI, so setup/hooks/MCP subprocess callers see it) — readers stay closed until a build finalizes. An interrupted build (`index_build_status` reports `state: "interrupted"`) heals with any ordinary build run — a zero-change retry reconciles derived state, refreshes bookkeeping, and republishes readiness without re-embedding. The derived-FTS rebuild (`content="fts"`) and `index_optimize` are restore-only maintenance: they refuse on a store with no completed build epoch rather than manufacturing readiness, and an optimize that ends with an unreadable table deliberately leaves readers failed closed until a build repairs it.

When diagnosing index-state store anomalies (missing lexical results, unexpected reconciles, provisioning questions), check the persisted store log first: `.wavefoundry/logs/index-state.log` records the one-time diagnostics — cold-store provisioning, crash-window reconciliation, reconcile skip reasons, and legacy-FTS drops — that previously appeared only on the build process's raw stdout/stderr (wave 1sbfk). It is bounded and best-effort; the absence of a line is not proof an event didn't happen, but a present line is authoritative.

Wavefoundry MCP doc-mutating tools also request a detached background docs-index refresh after successful writes. That improves freshness in non-hook environments such as Codex, but it is best-effort and non-blocking; use `index_health` when you need an explicit health verdict or run `index_build` for a deterministic result.

**First clone in Codex:** Codex will prompt you to trust the project directory the first time you open it. Accept the prompt — the project-local `.codex/config.toml` (Wavefoundry MCP registration) only loads once trust is granted. No additional setup is required; `.codex/config.toml` is committed to the repo and generated by `render_agent_surfaces.py` on upgrade.

`index_build` accepts: `content` (`docs` | `code` | `all` | `graph` | `map` | `fts`), `mode` (`update` | `rebuild`). It targets the single project index/graph (the separate framework layer was removed in wave 1p4ww). Successful responses include structured `stats` confirming file count, chunk count, and whether the run was already up to date. `content="fts"` (wave 1sc7c) rebuilds **only the derived lexical layer** (FTS5 tables + chunk registry) from scratch off the authoritative Lance tables — embedding-free, in-process, seconds; the clean recovery for an under-covered or corrupt lexical layer (`mode` is ignored, always from-scratch).

## Docs Gate

Same checks whether you run **`wf_validate_docs`** / **`wf_garden_docs`** over MCP or the bin scripts below.

`wf docs-lint` validates:
- Required prompt docs exist under `docs/prompts/`
- `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches `.wavefoundry/framework/VERSION`
- Required metadata fields (`Owner:`, `Status:`, `Last verified:`) on canonical docs
- Wave and journal root directories exist

`wf docs-gardener` refreshes stale metadata timestamps.

**Secrets scanning** runs in the docs gate, but in **record-only** mode (wave 1p5pz). `wf docs-lint` runs `wave_lint_lib/secrets_validators.py` against the merged ruleset (`.wavefoundry/scan-rules.toml` + `docs/scan-rules.toml`) and **records** new matches to `docs/scan-findings.json` as `pending` — but it does **not** fail on secret findings (only a malformed inline-suppression directive is a lint error). So the post-edit hook, `wf_validate_docs`, and the upgrade docs gate never block on a found secret. For an on-demand scan use `wf_scan_secrets(mode="full")` (MCP) — incremental mode auto-escalates to full when either TOML file changed since the last scan. **The `wf_close_wave` secrets gate is the sole enforcement point**: `pending` and `suspected-secret` entries hard-block close until classified (via the security reviewer, `seed-213`); `confirmed-secret` is **non-blocking** and surfaces a standing reminder; `false-positive` (cleared) passes.

Both subcommands are dispatched by the single cross-OS `wf` (bash) / `wf.cmd` (Windows) shim under `.wavefoundry/bin/`, which routes through `wf_cli.py` to the corresponding scripts under `.wavefoundry/framework/scripts/` (`wf docs-lint` → `docs_lint.py`, `wf docs-gardener` → `docs_gardener.py`). This repository does not ship repo-root `./docs-lint` or `./docs-gardener` shims. **Agents should use MCP `wf_validate_docs` and `wf_garden_docs` first**; reserve **`wf docs-lint`** / **`wf docs-gardener`** for hooks, CI, and hosts without MCP.

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

Option A (zip drop): Place a `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` at the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/`, and run **Upgrade wave framework**. The upgrade seed (`seed-160`) adopts the highest semver zip into `.wavefoundry/framework/`, runs `wf render-surfaces`, and continues full reconciliation.

Option B (direct merge): Merge or copy into `.wavefoundry/framework/` then run **Upgrade wave framework**.

**What the unpack step ignores:** archives with other names and zips outside the repository root.

**After bringing in the pack:**

```bash
# Run framework tests
python3 .wavefoundry/framework/scripts/run_tests.py

# Run docs gate
wf docs-gardener && wf docs-lint

# Review diff of pack changes, hooks, docs/prompts/, manifests
# Then commit (operator-owned — see Git commits below)
```

**Upgrade-path checks for new features (2026-04-30+):**

- Host MCP surfaces updated by `wf render-surfaces`:
  - `.cursor/mcp.json` contains `mcpServers.wavefoundry`
  - `.mcp.json` and `.junie/mcp/mcp.json` include the Wavefoundry stdio entry when those hosts are used
- The canonical cross-OS `wf` / `wf.cmd` dispatcher exists under `.wavefoundry/bin/` and resolves to packaged scripts via `wf_cli.py`:
  - `wf docs-lint` → `docs_lint.py`
  - `wf docs-gardener` → `docs_gardener.py`
- MCP recovery tools from the upgraded server are available:
  - `wf_audit` (combined wave + lint + index check)
  - `index_build` (deterministic project index rebuild path)

**Auto-Guru routing (agents — apply on every upgrade when Guru is in the pack):**

Agents running **Upgrade wave framework** must follow `docs/prompts/upgrade-wavefoundry.prompt.md` § **Agent surfaces and auto-Guru** and `seed-160` § **Agent surfaces and auto-Guru upgrade (agent procedure)**.

1. Run `wf render-surfaces` (includes `render_agent_surfaces.py`).
2. Backfill `AGENTS.md` tier-1 sections (**Codebase and documentation questions (auto-Guru)**, **Agent platform routing**) when missing.
3. Ensure `docs/agents/guru.md` exists; migrate legacy CIA paths when needed.
4. Re-run the renderer after tier-1 backfill if it was just added.
5. Confirm generated files: `.codex/skills/auto-guru/SKILL.md`, `.codex/config.toml` (Codex MCP registration); `.cursor/rules/auto-guru.mdc` and `.claude/agents/guru.md` when those host dirs exist; tier-2 marker blocks on thin pointers per `docs/agents/platform-mapping.md`.
6. Do not hand-edit `<!-- wave:auto-guru begin` … `end -->` regions — fix templates in `render_agent_surfaces.py` instead.

**Upgrade index rule:** the pack ships framework **source only** — there is no framework semantic index in it. There is a single semantic index (the project index at `.wavefoundry/index/`), and framework seeds fold into that project docs index at setup/upgrade. On an ordinary target-repo upgrade, update the project index after restarting the MCP server; a `CHUNKER_VERSION` bump forces a full rebuild.

**For full upgrade procedure:** see `docs/prompts/upgrade-wavefoundry.prompt.md` and `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`.

**`build_pack.py` semantics:** the pack is semver-versioned — `build_pack.py --version MAJOR.MINOR.PATCH` stamps `.wavefoundry/framework/VERSION` to `MAJOR.MINOR.PATCH+<lifecycle-build-suffix>` and writes the source-only archive `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` (no semantic index is built or shipped). `--release` additionally runs the preflight (clean tree on `main`, matching `## [<version>]` CHANGELOG section, unused tag, `gh auth status` succeeds), commits the stamp, tags, pushes, and uploads. `--release-dry-run` walks the pipeline but dirties the tree.

**Install assets:** the framework-side install assets are consolidated under `.wavefoundry/framework/install/`; where every install-related asset (templates, the release-notes install block, the format specs, the install-flow seeds) lives and the source → ship → provision role it plays is mapped in `docs/references/install-assets.md`. Each shipped format-spec template must stay byte-identical to its `docs/references/` canonical copy (guarded by `test_shipped_reference_docs.py`).

## Git Commits

**Operator-owned.** Agents must not run `git commit` unless the operator explicitly instructs them to finalize that commit in the **current** request after reviewing the diff. Default agent behavior is to hand off a suggested commit message and diff for the operator to commit locally.

This policy applies to all changes: framework source edits, self-hosted docs changes, platform surface renders, and packaging builds.
