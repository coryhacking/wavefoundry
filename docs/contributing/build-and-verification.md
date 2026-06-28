# Build and Verification

Owner: Engineering
Status: active
Last verified: 2026-06-27

## Verification Commands

Run these from the repository root to verify the Wavefoundry self-hosted surface is healthy:

**Agents (MCP attached):** Prefer **`wave_garden`** then **`wave_validate`** (or **`wave_audit`** for a combined wave + lint + index snapshot) instead of shelling out to the bin launchers. Use the tools’ structured results to fix failures.

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
- prewarms the docs embedding model cache
- rebuilds the project docs index (seeds + docs)

**MCP is available as soon as the docs index build completes** (~2.5 min). The code index is separate and optional.

### Two-phase onboarding

For new developer onboarding or post-upgrade rebuilds, use the docs-first approach to unblock MCP immediately while the code index builds in the background:

```bash
# Phase 1: docs index — unblocks all MCP tools immediately (~2.5 min)
wf update-indexes

# Phase 2: code index — builds in the background, foreground returns immediately
wf update-indexes --background-code
```

`--background-code` builds the docs index synchronously, then spawns a detached background process for code model prewarm and code embedding. Progress is written to `.wavefoundry/index/background-build.log`. Call `wave_index_health()` to check whether the background build is still running.

To build both synchronously (e.g. CI):

```bash
wf setup --include-code
```

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

`wave_index_health` will emit a `chunker_version_mismatch` advisory (distinct from `index_stale`) when the index was built with an older chunker version. If you see this advisory, run:

```bash
wf setup --full
# or docs-first, then background code:
wf setup --full
wf setup --background-code --full
```

If the repo needs extra project index roots beyond the default, declare them explicitly in `docs/workflow-config.json` under `indexing.project_include_prefixes`. Use repo-relative `docs` and `code` lists rather than one-off booleans. Wavefoundry uses this in self-hosting mode to include `.wavefoundry/framework/scripts` in project code search without changing the default for ordinary target repos.

### Update vs rebuild — decision table

| Situation | Action |
|---|---|
| Docs changed during a wave (post-edit hook ran automatically) | No manual action needed — MCP tools trigger a background refresh on write |
| Hook didn't run (Codex, Warp, or non-hook env) and docs feel stale | **Update:** `wave_index_build(content="docs", mode="update")` — re-indexes changed files only |
| `wave_index_health` reports `index_stale` | **Update:** `wave_index_build(content="docs", mode="update")` |
| `wave_index_health` reports `index_missing` | **Update (creates index):** `wave_index_build(content="docs", mode="update")` or `wf update-indexes` |
| `wave_index_health` reports `chunker_version_mismatch` after a pack upgrade | **Full rebuild required** — file hashes alone won't detect the version change. See *Upgrade rebuild requirement* above |
| Code navigation (`code_search`, `code_read`) feels stale or was never built | **Code update:** `wave_index_build(content="code", mode="update")` — or `wf update-indexes` |
| Framework seeds changed in the Wavefoundry source repo itself | **Project docs update:** `wave_index_build(content="docs", mode="update")`; framework seeds are folded into the project docs index |
| First install / clean environment | `wf setup` |
| CI deterministic full build | `wf setup --include-code` (~6 min, docs and code synchronous) |

**Update** re-indexes only changed files (fast, uses file hashes). **Rebuild** (`--full` / `mode="rebuild"`) ignores hashes and reprocesses everything — use it when `CHUNKER_VERSION` changed or the index is known corrupt.

After an ordinary upgrade, if the framework layer still looks missing or stale, stop and verify that the upgraded MCP server has been restarted and that the shipped `.wavefoundry/framework/index/` directory is present. Do not use that symptom alone as a reason to rebuild the framework layer.

If `docs_search` falls back to lexical mode and you need to know whether the semantic index is stale or missing, call `wave_index_health` explicitly. In clients that do not execute the post-edit hook path, assume manual reindexing is required after meaningful docs changes.

Wavefoundry MCP doc-mutating tools also request a detached background docs-index refresh after successful writes. That improves freshness in non-hook environments such as Codex, but it is best-effort and non-blocking; use `wave_index_health` when you need an explicit health verdict or run `wave_index_build` for a deterministic result.

**First clone in Codex:** Codex will prompt you to trust the project directory the first time you open it. Accept the prompt — the project-local `.codex/config.toml` (Wavefoundry MCP registration) only loads once trust is granted. No additional setup is required; `.codex/config.toml` is committed to the repo and generated by `render_agent_surfaces.py` on upgrade.

`wave_index_build` accepts: `content` (`docs` | `code` | `all`), `mode` (`update` | `rebuild`), `layer` (`project` | `framework`). Successful responses include structured `stats` confirming file count, chunk count, and whether the run was already up to date.

## Docs Gate

Same checks whether you run **`wave_validate`** / **`wave_garden`** over MCP or the bin scripts below.

`wf docs-lint` validates:
- Required prompt docs exist under `docs/prompts/`
- `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches `.wavefoundry/framework/VERSION`
- Required metadata fields (`Owner:`, `Status:`, `Last verified:`) on canonical docs
- Wave and journal root directories exist

`wf docs-gardener` refreshes stale metadata timestamps.

**Secrets scanning** runs in the docs gate, but in **record-only** mode (wave 1p5pz). `wf docs-lint` runs `wave_lint_lib/secrets_validators.py` against the merged ruleset (`.wavefoundry/scan-rules.toml` + `docs/scan-rules.toml`) and **records** new matches to `docs/scan-findings.json` as `pending` — but it does **not** fail on secret findings (only a malformed inline-suppression directive is a lint error). So the post-edit hook, `wave_validate`, and the upgrade docs gate never block on a found secret. For an on-demand scan use `wave_scan_secrets(mode="full")` (MCP) — incremental mode auto-escalates to full when either TOML file changed since the last scan. **The `wave_close` secrets gate is the sole enforcement point**: `pending` and `suspected-secret` entries hard-block close until classified (via the security reviewer, `seed-213`); `confirmed-secret` is **non-blocking** and surfaces a standing reminder; `false-positive` (cleared) passes.

Both subcommands are dispatched by the single cross-OS `wf` (bash) / `wf.cmd` (Windows) shim under `.wavefoundry/bin/`, which routes through `wf_cli.py` to the corresponding scripts under `.wavefoundry/framework/scripts/` (`wf docs-lint` → `docs_lint.py`, `wf docs-gardener` → `docs_gardener.py`). This repository does not ship repo-root `./docs-lint` or `./docs-gardener` shims. **Agents should use MCP `wave_validate` and `wave_garden` first**; reserve **`wf docs-lint`** / **`wf docs-gardener`** for hooks, CI, and hosts without MCP.

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
  - `wave_audit` (combined wave + lint + index check)
  - `wave_index_build` (deterministic project/framework index rebuild path)

**Auto-Guru routing (agents — apply on every upgrade when Guru is in the pack):**

Agents running **Upgrade wave framework** must follow `docs/prompts/upgrade-wavefoundry.prompt.md` § **Agent surfaces and auto-Guru** and `seed-160` § **Agent surfaces and auto-Guru upgrade (agent procedure)**.

1. Run `wf render-surfaces` (includes `render_agent_surfaces.py`).
2. Backfill `AGENTS.md` tier-1 sections (**Codebase and documentation questions (auto-Guru)**, **Agent platform routing**) when missing.
3. Ensure `docs/agents/guru.md` exists; migrate legacy CIA paths when needed.
4. Re-run the renderer after tier-1 backfill if it was just added.
5. Confirm generated files: `.codex/skills/auto-guru/SKILL.md`, `.codex/config.toml` (Codex MCP registration); `.cursor/rules/auto-guru.mdc` and `.claude/agents/guru.md` when those host dirs exist; tier-2 marker blocks on thin pointers per `docs/agents/platform-mapping.md`.
6. Do not hand-edit `<!-- waveframework:auto-guru begin` … `end -->` regions — fix templates in `render_agent_surfaces.py` instead.

**Upgrade index rule:** the framework index is shipped inside the pack. On an ordinary target-repo upgrade, update the project index after restart, but do not rebuild the framework layer unless `CHUNKER_VERSION` changed, the shipped framework index is missing/corrupt, or you are intentionally reindexing the Wavefoundry source repo itself.

**For full upgrade procedure:** see `docs/prompts/upgrade-wavefoundry.prompt.md` and `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`.

**`build_pack.py` semantics:** default zip date is today (local ISO); letter suffix is the next letter after the maximum suffix already present for that date in the output directory (not the first missing gap). The script stamps `.wavefoundry/framework/VERSION` to `<date><letter>` before writing the archive, then updates and compacts `.wavefoundry/framework/index/` before zipping. Use `--date` only for tests or exceptional reissues.

**Install assets:** the framework-side install assets are consolidated under `.wavefoundry/framework/install/`; where every install-related asset (templates, the release-notes install block, the format specs, the install-flow seeds) lives and the source → ship → provision role it plays is mapped in `docs/references/install-assets.md`. Each shipped format-spec template must stay byte-identical to its `docs/references/` canonical copy (guarded by `test_shipped_reference_docs.py`).

## Git Commits

**Operator-owned.** Agents must not run `git commit` unless the operator explicitly instructs them to finalize that commit in the **current** request after reviewing the diff. Default agent behavior is to hand off a suggested commit message and diff for the operator to commit locally.

This policy applies to all changes: framework source edits, self-hosted docs changes, platform surface renders, and packaging builds.
