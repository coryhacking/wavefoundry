# Build and Verification

Owner: Engineering
Status: active
Last verified: 2026-09-20

## Verification Commands

Run these from the repository root to verify the Wavefoundry self-hosted surface is healthy:

**Agents (MCP attached):** Prefer **`wf_garden_docs`** then **`wf_validate_docs`** (or **`wf_audit`** for a combined wave + lint + index snapshot) instead of shelling out to the bin launchers. Use the tools’ structured results to fix failures.

**Cadence:** routine documentation edits receive automatic incremental changed-set lint from hooks and documentation-writing MCP tools. Run this full docs gate at explicit validation or handoff boundaries and at lifecycle, install, and upgrade gates—not after every edit. Use an explicit gardener path for an untracked document that needs a timestamp refresh.

**Operators / CI / no MCP:** Use the shell sequence below.

```bash
# Docs gate (metadata + prompt surface + manifest validation)
wf docs-gardener && wf docs-lint

# Framework script tests (no bytecode)
python3 .wavefoundry/framework/scripts/run_tests.py
```

### Focused Diagnostic Runs (repair loops)

```bash
python3 .wavefoundry/framework/scripts/run_tests.py --file test_docs_lint.py --file test_wf_cli.py
```

`--file <basename>` (repeatable, wave 1tmtx) runs only the named discovered
test files through the same lock, subprocess, environment, timeout, and
stray-artifact-guard path as a full run. Focused runs label their output as
focused, never read or write the last-green cache or any timing data, and are
diagnostic only: they are never delivery, release, or close-gate evidence. One
complete canonical run (`python3 .wavefoundry/framework/scripts/run_tests.py`)
remains the delivery authority.

Timing telemetry (wave 1tmtx): every run prints per-file elapsed seconds, a
bounded top-10 slowest-file summary, and aggregate worker service time; a
successful complete run persists an advisory `durations_s` map beside the
last-green cache entry. `--no-cache` still forces a complete run and is never
forwarded to unittest; note that it still reads the cache file once for the
advisory timing map. Timing data is advisory only — it never authorizes a test
skip or a pass, and neither the cache file nor the timing manifest is a public
compatibility API.

### Golden tool-surface fixture (wave 1y0do)

`tests/test_tool_surface_golden.py` boots the real `server.build_server` with a stub handler and serializes every registered MCP tool (implementation tools and the runner survivors) to `tests/fixtures/tool-surface-golden.json`: name, roster tier, complete input schema, and annotations. Tool descriptions and prose `description` strings at schema nodes are excluded; an input property that happens to be named `description` is still covered. The test fails with a per-tool, per-key diff on any drift.

A golden diff is a public contract change. It must be named in the change doc that causes it, and the fixture is regenerated as a deliberate step, never as a reflex:

```bash
WF_UPDATE_TOOL_SURFACE_GOLDEN=1 python3 .wavefoundry/framework/scripts/run_tests.py --file test_tool_surface_golden.py
```

Without the flag the test never writes. The fixture lives under the framework test tree, so it is inside the close-time receipt hash and outside the distribution pack. The same module carries the runtime roster parity test (registered set equals `mcp_tool_roster.TOOL_TIERS` in both directions) and the behavioral wrapper-order test (cost innermost, lifecycle lock middle, upgrade-publication guard outermost, with the five wrong permutations as negative controls).

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

### Quick local readiness check

```bash
wf setup --check
wf setup --check --root /path/to/repo --json
```

The check reports `ready` (exit 0), `action_required` (exit 1), or `indeterminate` (exit 2).
Follow the reported action: plain setup for local preparation, a host restart for
stale loaded code, or the retained owning command for pending recovery. Do not
substitute setup for a pending upgrade continuation. The check installs nothing,
downloads no models and does not repair or rebuild indexes. It is read-only for
application data; SQLite may create or update normal WAL/SHM coordination files.
It is a bounded readiness check, not a complete integrity, freshness or search-quality audit.

Check mode accepts only `--check`, `--root` and `--json`; it rejects repair or
build options. Native Windows uses the same arguments through
`.\.wavefoundry\bin\wf.cmd setup --check`. A missing advisory setup stamp
causes live assessment, not an automatic rebuild. Ordinary source edits belong
to normal incremental indexing. Pending historical memory validation remains a
separate advisory and does not invalidate an otherwise usable core index.
MCP startup and its existing staleness monitor use the same assessment; startup
notices use stderr so they cannot corrupt MCP protocol output.

After Git operations that change the checkout, follow `AGENTS.md` **Check readiness after Git changes**: call `index_health()` and inspect both freshness and `data.setup_readiness`. If MCP is unavailable, use `wf setup --check --json`; this fallback does not verify source freshness. The check reports actions without automatically executing repairs.

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

Structured-format directories (wave `1wfsl`, `1wdvr`): the code index covers every
`SOURCE_CODE_EXTENSIONS` format including YAML/JSON/TOML across the WHOLE repository by
default (everything outside `.wavefoundry/`, the corpus exclusions, and ignore files), so
OpenAPI specs, JSON Schemas, and infrastructure manifests in ordinary directories are
searchable with no configuration. When spec content is missing from `code_search`, check
`.gitignore`/`.aiignore` first (the walk respects both); for `.wavefoundry/`-nested content
(self-hosting), opt the curated subpath in via `indexing.project_include_prefixes.code`; then
rebuild (`wf update-indexes` or MCP `index_build(content='code', mode='update')`) and verify
with a `code_search` query. Detected OpenAPI / JSON Schema / AsyncAPI files and
GraphQL SDL / Protobuf files chunk structure-aware with breadcrumbed prose units
(measured default-on per format; override `indexing.spec_aware_chunking`). The DOCS layer
serves documentation content — doc-kind prose chunks (markdown, reStructuredText, and
AsciiDoc sections, plain-text/extensionless docs, docstring doc chunks, HTML/XML element text,
notebook markdown cells) plus `doc-code` chunks for the fenced code blocks, code-directive
bodies, listing blocks, and notebook code cells extracted from those formats AND standalone hand-authored diagram
files (Mermaid `.mmd`/`.mermaid`, PlantUML `.puml`/`.plantuml`, Graphviz DOT `.dot`/`.gv` —
one title-or-stem-breadcrumbed unit per file), filterable via
`docs_search(kind='doc-code')` (non-exhaustive; chunk-kind routing is the authority;
prompt-kind files keep fences inline; tool-generated diagram formats contribute extracted labels, never raw serializations) — while
machine-authority files (per-wave `events.jsonl`, memory-archive bodies, the secret-scan
findings ledger) stay excluded by path predicates and route through typed tools. CSV is never
indexed (use a markdown carrier page); `indexing.walk_reinclude_filenames` can restore a
name-layer-excluded filename but never overrides the binary/sniff/machine-authority layers.
Never widen prefixes into secret-bearing or machine-authority artifacts. The canonical
carrier of this guidance is seed 211's Index Scope section (mirrored in `docs/agents/guru.md`).

### Dependency version sync on upgrade

The tool-venv dependency check is **version-aware**: when a pack pins a new version of a dependency (e.g. `apsw==3.53.4.0`), `wf setup` — and `wf_upgrade`, whose phase-4 index step already runs the same `ensure_deps` check — move an **existing** install to the pinned version, not just fresh installs. An exact (`==`) pin installs exactly that version (including downgrading a newer build to the framework's validated one); a range pin (`>=`, `<`) leaves any satisfying installed version untouched. Unpinned dependencies keep presence-only behavior (installed → not touched). Model weights are refreshed the same way — `prewarm_models` runs on each phase-4 setup invocation, so new/changed embedding and reranker models download during the upgrade. No separate command is needed for either.

### Update vs rebuild — decision table

| Situation | Action |
|---|---|
| Docs changed during a wave (post-edit hook ran automatically) | No manual action needed — MCP tools trigger a background refresh on write |
| Hook didn't run (Codex, Warp, or non-hook env) and docs feel stale | **Update:** `index_build(content="docs", mode="update")` — re-indexes changed files only |
| `index_health` reports `index_stale` | **Update:** `index_build(content="docs", mode="update")` |
| `index_health` reports `index_missing` | **Update (creates index):** `index_build(content="docs", mode="update")` or `wf update-indexes` |
| `index_health` reports `chunker_version_mismatch` after a pack upgrade | **Full rebuild required** — file hashes alone won't detect the version change. See *Upgrade rebuild requirement* above |
| `index_health` reports `chunk_index_undercovered` (lexical FTS/registry materially behind canonical SQLite chunks) | **Derived rebuild:** `index_build(content="fts")` — rebuilds the derived FTS/registry from canonical SQLite chunks, embedding-free, in seconds; any ordinary build's reconcile also backfills it (including zero-change builds) |
| Code navigation (`code_search`, `code_read`) feels stale or was never built | **Code update:** `index_build(content="code", mode="update")` — or `wf update-indexes`. Since wave 1sc7c each semantic layer tracks the hash it last embedded per path (index database `layer_path_state`), so a scoped update always detects the layer's own staleness — the historical no-op (content-scoped builds stamping hashes they never embedded, with the post-edit hook running docs-only) is fixed, and previously poisoned repos heal automatically on their first post-upgrade build (empty layer state reads as all-stale; vectors are reused by content hash, so the heal re-chunks without re-embedding unchanged content) |
| Framework seeds changed in the Wavefoundry source repo itself | **Project docs update:** `index_build(content="docs", mode="update")`; framework seeds are folded into the project docs index |
| First install / clean environment | `wf setup` (docs, code, and graph foreground) |
| CI deterministic full build | `wf setup --include-code` (~6 min, explicit docs and code synchronous form) |

**Update** re-indexes only changed files (fast, uses file hashes). **Rebuild** (`--full` / `mode="rebuild"`) ignores hashes and reprocesses everything — use it when `CHUNKER_VERSION` changed. For corruption, follow the preservation and recovery guidance below before attempting a rebuild.

After an ordinary upgrade, if search still looks missing or stale, stop and verify that the upgraded MCP server has been restarted before rebuilding anything. There is a single semantic index — the project index at `.wavefoundry/index/` — and framework seeds fold into that project docs index at setup/upgrade; there is no separate framework index to rebuild.

Since wave 1seav every search response tells you WHY it degraded: check `search_mode` (`lexical_fallback` = BM25 from the published FTS layer; `live_fallback` = no published index at all) and `fallback_reason` (`model_unavailable`, `index_not_ready`, `query_failed`, …) before reaching for `index_health` — the explicit health verdict is still authoritative when you need layer-level detail. In clients that do not execute the post-edit hook path, assume manual reindexing is required after meaningful docs changes.

**State recovery (wave 1sed7 — SQLite-only):** `.wavefoundry/index/index.sqlite` is the sole index state authority for semantic and graph content; there is no `meta.json`. A search tool returning `index_not_ready` means the store has no completed build epoch (building, interrupted, or never built) or a build fenced mid-query — check `index_build_status` and retry after the build completes. The unified store now holds canonical chunks, vectors, and auxiliary state as well as readiness. A missing index can be rebuilt from repository sources, but lost vectors must be regenerated and auxiliary state may not be recoverable from those sources. A corrupt or unsupported store is preserved and refused; ordinary indexing does not silently replace it. Retain the database, WAL/SHM files, and migration receipt together, diagnose the runtime/filesystem error, and use an explicit recovery procedure before retrying. After conversion, retired Lance tables are no longer a recovery source. A legacy `meta.json` from a pre-1sed7 install is never read by anything — not even the upgrade's version probes (an absent/empty store reads as unknown, which forces convergence) — and is removed automatically after the first successful build. Never treat a failed build's output as current: a build reporting `failed: true` exits non-zero through CLI/setup/hooks/MCP subprocess callers. After a verified precommit source refusal, it may restore the previous completed snapshot and explicitly report that readers can serve historical content. This is availability, not current-source freshness. Crashes, uncertain commits, postcommit failures and unproven recovery remain fail-closed. An interrupted build (`index_build_status` reports `state: "interrupted"`) heals with any ordinary build run — a zero-change retry reconciles derived state, refreshes bookkeeping, and republishes readiness without re-embedding. The derived-FTS rebuild (`content="fts"`) and `index_optimize` are restore-only maintenance: they refuse on a store with no completed build epoch rather than manufacturing readiness, and an optimize that ends with an unreadable table deliberately leaves readers failed closed until a build repairs it.

When diagnosing index database anomalies (missing lexical results, unexpected reconciles, provisioning questions), check the persisted store log first: `.wavefoundry/logs/index-state.log` records the one-time diagnostics — cold-store provisioning, crash-window reconciliation, reconcile skip reasons, and legacy-FTS drops — that previously appeared only on the build process's raw stdout/stderr (wave 1sbfk). It is bounded and best-effort; the absence of a line is not proof an event didn't happen, but a present line is authoritative.

Wavefoundry MCP doc-mutating tools also request a detached background project-index refresh after successful writes. The MCP process additionally polls for stale inputs after the configured index quiet period and recovers completed/zombie children or recycled PID records before deciding a refresh is still active. Automatic project refreshes pass `content=all` so docs and code converge together. Inspect `index_health.data.background_monitors.index` for the monitor's configured/alive and latest stale/trigger/reason state; use `index_build_status.lock.held` for the authoritative live-build decision. Both automatic paths are best-effort and non-blocking, so run `index_build` when a deterministic completion boundary is required.

Context Efficiency uses a separate trigger hierarchy. Eligible accounting is written through to SQLite immediately. Claude Code renders a dedicated main-session `Stop` adapter that schedules portable `wave.md` projection, while every MCP server supplies the same accounting-neutral operation after an unchanged-generation quiet period. Configure the latter with `context_efficiency.projection.quiet_period_seconds` (default 120, clamped 90–600) and inspect `index_health.data.background_monitors.context_efficiency_projection`. Automatic projection defers under the shared source-mutation guard while a build reads sources, retaining pending work for a later poll. Missing-map resource generation uses the same guard. Builders retry caught source drift once with entirely fresh preparation; repeated drift reports refusal and actual reader availability. This does not change index cadence or replace operator-triggered lifecycle/reload/upgrade publication barriers.

**First clone in Codex:** Codex will prompt you to trust the project directory the first time you open it. Accept the prompt — the project-local `.codex/config.toml` (Wavefoundry MCP registration) only loads once trust is granted. No additional setup is required; `.codex/config.toml` is committed to the repo and generated by `render_agent_surfaces.py` on upgrade.

`index_build` accepts: `content` (`docs` | `code` | `all` | `graph` | `map` | `fts`), `mode` (`update` | `rebuild`). It targets the single project index/graph (the separate framework layer was removed in wave 1p4ww). Successful responses include structured `stats` confirming file count, chunk count, and whether the run was already up to date. `content="fts"` (wave 1sc7c) rebuilds **only the derived lexical layer** (FTS5 tables + chunk registry) from scratch off the canonical SQLite chunks — embedding-free, in-process, seconds; the clean recovery for an under-covered or corrupt lexical layer (`mode` is ignored, always from-scratch).

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

## Close gate: the framework test receipt

`run_tests.py` records every successful WHOLE-suite run in
`.wavefoundry/framework/test-cache.json` with an `inputs_hash` covering every
file under `.wavefoundry/framework/` except `VERSION`, `MANIFEST`, the cache
itself, `test-run.lock`, and the `index` / `__pycache__` / `.pytest_cache`
directories, so the receipt self-invalidates the moment any framework file
changes.

`wf_close_wave` VERIFIES that receipt (wave `1wur7`). It requires
`result == "ok"` with an `inputs_hash` matching the current framework tree, and
reports a missing, red, stale, or unreadable receipt as `framework_test_receipt_not_proven`
rather than assuming green — `_write_cache` only ever records successful runs, so
"no receipt" means "not proven", never "passed". The gate runs no suite and
spawns no subprocess: record a fresh receipt yourself with
`python3 -B .wavefoundry/framework/scripts/run_tests.py`.

**Scope, stated exactly.** The hash covers `.wavefoundry/framework/`, so only
receipt STALENESS is framework-scoped: a docs edit does not invalidate a receipt.
But the receipt is written only on a whole-suite pass, so a suite failure
triggered by content under `docs/` prevents a NEW receipt from being written.
When the framework tree also changed, the standing receipt is stale and close is
blocked; in a documentation-only wave a current green receipt persists and close
is not blocked despite a red suite.
A green receipt therefore attests the framework code, not the tree. Describe it
as neither a whole-repository guarantee nor a whole-repository exemption.

**Run the suite last.** Any edit under `.wavefoundry/framework/` invalidates the
receipt, a seed edit made during closure included. The check itself costs
milliseconds; the remediation is a full suite run, so sequence the suite as the
final step before close rather than the first. Where
`.wavefoundry/framework/scripts/run_tests.py` is absent (every repository that
consumes the packaged framework — `build_pack.py` excludes the runner,
`scripts/tests`, and the receipt) the check is a documented no-op that neither
blocks close nor claims proof.

This is what keeps the whole-suite requirement machine-visible now that it no
longer belongs in per-change acceptance criteria; see **Writing Acceptance
Criteria** in `change-workflow.md`.

## Wave Framework Pack Upgrade Verification

When a new framework version is available, upgrade using this procedure:

**Bring the pack in:**

Option A (single release package): A protocol-2 installation may select `wavefoundry-<version>.zip` directly with `--pack`. A protocol-1 installation uses that same file, stops the dashboard and every attached agent/MCP host, and runs `python <package>.zip --root <repo> --confirm-hosts-stopped`. The package contains and verifies the exact bridge and feature payload bytes, performs both hops, and returns the restart or retained-checkpoint recovery action. The internal bridge zip/bootstrap/selection remain builder composition inputs and are removed from `dist/` after assembly. The upgrade seed (`seed-160`) carries the complete recovery flow.

The upgrade also migrates the review policy explicitly: legacy enabled projects become `wave_review.enabled=true, delivery_mode=targeted`, while legacy disabled projects become `enabled=false, delivery_mode=disabled`.

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
5. Confirm generated files: `.codex/skills/wf-guru/SKILL.md` (registry-rendered; pre-namespace `auto-guru/` is stale-cleaned), `.codex/config.toml` (Codex MCP registration); `.cursor/rules/auto-guru.mdc` and `.claude/agents/guru.md` when those host dirs exist; tier-2 marker blocks on thin pointers per `docs/agents/platform-mapping.md`.
6. Do not hand-edit `<!-- wave:auto-guru begin` … `end -->` regions — fix templates in `render_agent_surfaces.py` instead.

**Upgrade index rule:** the pack ships framework **source only** — there is no framework semantic index in it. There is a single semantic index (the project index at `.wavefoundry/index/`), and framework seeds fold into that project docs index at setup/upgrade. On an ordinary target-repo upgrade, update the project index after restarting the MCP server; a `CHUNKER_VERSION` bump forces a full rebuild.

**1.15 events-only cutover (maintenance window):** upgrading across the 1.15 boundary removes the retired review-evidence sidecars (`docs/waves/review-evidence-adoptions.json`, `docs/waves/review-evidence-migration.json`) one-way, without reading either, and leaves every historical `wave.md` and `events.jsonl` byte-for-byte untouched; upgrade no longer reprojects wave review state. The cleanup refuses while either shipped publication-lock path is held (retained `failed_phase=review_sidecar_cleanup`; stop the dashboard and every attached host, then re-run the upgrade), then acquires and holds both lock paths across the sidecar deletions; the v1.13 root-level lock file is released and then unlinked last (Windows cannot delete an open locked file; on POSIX an unlink under a concurrent v1.13-era holder would split the lock domain onto a fresh inode; both residual slivers are bounded by the full-restart instruction). The restart boundary is cutover-scoped: `restart_required` is true only on cutover-active runs (the run removed a sidecar or the stale root lock, or the installed version predates 1.15, with an unknown version treated fail-safe as pre-1.15). A cutover-active run requires a full restart of every attached MCP/agent host, including the invoking one, before lifecycle mutation resumes; the upgrade suppresses its automatic in-process reload on such runs (guaranteed only from newly loaded code onward: a pre-1.15 host crossing the boundary may still fire its old unconditional reload, which does not substitute for the full restart), and `wf_reload_mcp` alone is not sufficient. Ordinary post-1.15 upgrades keep the established reload flow and report no cutover restart requirement. Mixed-version concurrent lifecycle mutation during the cutover window is unsupported.

**For full upgrade procedure:** see `docs/prompts/upgrade-wavefoundry.prompt.md` and `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`.

**`build_pack.py` semantics:** the pack is semver-versioned — `build_pack.py --version MAJOR.MINOR.PATCH` stamps `.wavefoundry/framework/VERSION` to `MAJOR.MINOR.PATCH+<lifecycle-build-suffix>` and writes the source-only archive `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` (no semantic index is built or shipped). Beginning with 1.16.0, `--release` and `--release-dry-run` require `--with-models` and build the declared `wavefoundry-models-<MODEL_SET_VERSION>.zip` companion (set 3 from the release after 1.17.0) from the warmed local cache before publication; bare non-release builds may remain feature-only. `--release` additionally runs the preflight (clean tree on `main`, matching `## [<version>]` CHANGELOG section, unused tag, `gh auth status` succeeds), commits the stamp, tags, pushes, and uploads both exact assets.

**1.16 retired-model cleanup:** after the freshly loaded upgrade code verifies the installed canonical model set and a stable complete docs-and-code epoch in `index.sqlite`, cleanup removes only the exact retired Wavefoundry-owned BAAI cache components. It runs before dashboard restart and lock removal. A cleanup failure retains the upgrade lock with `failed_phase=retired_model_cleanup`; rerun the cleanup phase after correcting the reported target. The flat `retired_model_cleanup_status`, `_removed`, `_absent`, `_unowned`, and `_failed` fields are the recovery authority. Dry-run reports `dry_run` with four empty lists and deletes nothing.

**Install assets:** the framework-side install assets are consolidated under `.wavefoundry/framework/install/`; where every install-related asset (templates, the release-notes install block, the format specs, the install-flow seeds) lives and the source → ship → provision role it plays is mapped in `docs/references/install-assets.md`. Each shipped format-spec template must stay byte-identical to its `docs/references/` canonical copy (guarded by `test_shipped_reference_docs.py`).

## Git Commits

**Operator-owned.** Agents must not run `git commit` unless the operator explicitly instructs them to finalize that commit in the **current** request after reviewing the diff. Default agent behavior is to hand off a suggested commit message and diff for the operator to commit locally.

This policy applies to all changes: framework source edits, self-hosted docs changes, platform surface renders, and packaging builds.

<!-- wavefoundry:review-policy:begin -->
## Review-policy release baseline

Release verification consumes the current review policy and preserves the
documented protocol bridge boundary.
<!-- wavefoundry:review-policy:end -->

## Python runtime policy

**Wavefoundry tooling Python runtime:** this policy applies to Wavefoundry’s CLI, MCP server and indexing tools. It does not change the host project’s application language or runtime requirements (for example, Java and its JDK). Python 3.13 or newer is recommended. Python 3.11 and 3.12 are deprecated but remain allowed; the minimum is still 3.11. No removal release is scheduled. Dependencies must support the selected interpreter; this recommendation does not qualify every future Python release.

The notice appears once per `wf` invocation or direct MCP serving startup, on stderr. Inspect `setup_readiness.advisories` through index health when host logs are hidden. It does not request repair or change command success. Follow the [runtime transition procedure](../../.wavefoundry/framework/README.md#python-runtime-advisory-and-transition): select PATH `python3` for setup and the restarted host, stop shared-environment consumers or propagate an isolated environment override, and retain pending recovery ownership. Ordinary setup may replace an incompatible tool environment; the advisory never does.
