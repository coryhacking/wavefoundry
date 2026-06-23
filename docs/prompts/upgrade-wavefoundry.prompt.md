# Upgrade Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-06-23

Shortcut: **`Upgrade Wavefoundry`** | Legacy: **`Upgrade wave framework`** / **`Upgrade wave context`**

## Purpose

Upgrade the Wave Framework operating surface in a target repository. Reconciles the rendered local docs, prompt surface, platform hook/config surfaces, the repo-local Codex bootstrap launcher, and `AGENTS.md` with the current canonical framework source.

## How Framework Updates Work

Use this prompt when the repository is already seeded and you want it to adopt a newer Wavefoundry framework pack or reconcile against a newer local `.wavefoundry/framework/` tree.

The expected operator flow is:

1. Put the new framework in reach of this repository.
   - Usually this means building or placing `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` in the repository root, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`.
   - If the repository already has the desired newer `.wavefoundry/framework/` tree staged locally, the upgrade runs against that tree directly.
   - **Never `ls` for the pack to decide whether one exists.** It almost always lives in `~/.wavefoundry/dist/`, not the repo root, so an empty `ls wavefoundry-*.zip` at the repo root does **not** mean there's no pack. Determine it only via `.wavefoundry/bin/upgrade-wavefoundry --detect-zip` / `--list-zips` / `--dry-run` (see *Agent-safe zip discovery* below).
2. Run **Upgrade Wavefoundry**.
   - If a root `wavefoundry-*.zip` is present, upgrade automatically unpacks the newest matching zip first.
   - It then regenerates tracked platform surfaces, reconciles docs/prompts/config, and validates drift.
3. Reload the MCP server **in-process** when the upgrade finishes.
   - The upgrade reloads the server code in-process — call `wave_mcp_reload()` (or run `wave_upgrade` cleanup, which reloads automatically). A full host restart is only needed for hosts that cannot hot-reload.
   - If you use Codex, the MCP server reloads from the committed `.codex/config.toml` automatically — no re-registration needed after upgrade.
4. The index update runs **automatically** at the end of the upgrade.
   - The upgrade's final phase updates **both** the semantic indexes and the graph, each version-aware: an incremental update normally, auto-escalating to a full rebuild when its version advanced — semantic on a `CHUNKER_VERSION`/model bump (re-embed, minutes), graph on a `GRAPH_BUILDER_VERSION` bump (graph-only re-extract, ~10–30 s). You do **not** run a separate index command for a normal upgrade.
   - A manual `wave_index_build(...)` / `--update-index` call is only for re-running after the agent editing pass or recovering a backgrounded code build (see the Verification Checklist).
   - So a graph-builder bump materializes **during the upgrade**, symmetric with the semantic indexes — no manual step. (The first-query in-process auto-rebuild remains a safety net.) **1.8.1** bumps `GRAPH_BUILDER_VERSION` only (32→35) → a graph-only re-extract (no re-embed) carrying the new edges/nodes: cross-language confidence promotion, `reads_config`, `instruments`, `.properties`/`.yml` config-key nodes.

What this prompt is not:

- It is **not** packaging. Packaging creates a new zip in the framework source repo.
- It is **not** init. Use init only for first-time seeding or legacy routing cases.
- It is **not** a manual unzip checklist. Root zip adoption is built into the upgrade flow.

**Supported operator environments:** macOS and Linux are supported natively. Windows is currently supported through **WSL2** for upgrade and operator workflows because some launcher and shell steps still assume a POSIX environment.

**Python requirement:** Python 3.11 or later is required. Framework dependencies are installed into a shared tool environment at `~/.wavefoundry/venv` (or `$WAVEFOUNDRY_TOOL_VENV` to override); running `setup_wavefoundry.py` is the preferred way to create/populate it and run the index setup flow. `setup_index.py` remains supported as the compatibility entrypoint behind it. If `setup_wavefoundry.py` fails specifically because a required model cannot be downloaded, keep recovery on the canonical setup path: in agent-driven sessions, the agent should ask the operator for permission to rerun the same setup command with network access or host escalation enabled instead of doing an out-of-band manual model download.

## Upgrade Steps

**Versioning contract:** Releases use `MAJOR.MINOR.PATCH` semver. The version appears as `MAJOR.MINOR.PATCH+<build>` in `VERSION` and `framework_revision`, and as `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` in filenames. See `docs/architecture/decisions/12tm5-adr semver-versioning-contract.md` for the version bump policy.

**Distribution directories:** `upgrade_wavefoundry.py` searches the repository root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, and `~/Downloads/`, then picks the highest semver zip. Non-matching filenames are skipped silently.

**Agent-safe zip discovery (use these, not `ls`):** Never use `ls`/`find` to locate or choose the pack. Two reasons it gives the wrong answer: (1) it only sees the directory you point it at — the pack usually lives in `~/.wavefoundry/dist/`, so `ls wavefoundry-*.zip` at the repo root finds nothing and an agent wrongly concludes "already current / nothing to upgrade"; (2) `ls -1 ~/.wavefoundry/dist/` sorts lexicographically and ranks `wavefoundry-1.3.9.*.zip` *above* `wavefoundry-1.3.30.*.zip`, selecting a stale pack. Use the script flags instead — all run the same semver comparator over all five search paths the upgrade itself uses:

- `.wavefoundry/bin/upgrade-wavefoundry --detect-zip` — prints the absolute path of the selected pack and exits `0`. Exits `1` with empty output when no matching zip is found.
- `.wavefoundry/bin/upgrade-wavefoundry --list-zips` — prints every match across all five search paths, semver-sorted (highest first), with `* ` on the selected pack.
- `.wavefoundry/bin/upgrade-wavefoundry --dry-run` — prints the selected pack on a `Zip to apply:` line in the same output that surfaces seed diffs and hook inventory, with zero mutations.

Discovery/preview is **CLI-only**: run the flag via your shell (that is the agent-safe path — not `ls`). The MCP `wave_upgrade` tool *runs* the upgrade — its default `preflight_to_docs_gate` phase adopts the highest pack — and has **no** dry-run or discovery-only phase (its only argument is `phase=`; there is no `mode=`).

**Step 0 (optional zip adoption):** If a `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` is in the repository root, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`, the upgrade seed stages the selected pack under `.wavefoundry/framework/`, runs `render_platform_surfaces.py`, and continues full reconciliation. Non-matching filenames are skipped. On Windows, run this flow from **WSL2** rather than native `cmd.exe` or PowerShell.

**Full reconciliation:**
1. Inventory current state (seed-030 in targeted mode)
2. Drift-detect against canonical framework (read-only subagents for inventory)
3. Produce a file-level upgrade plan before broad edits
4. Reconcile prompt surface, platform surfaces, `AGENTS.md`, manifests
5. **Agent surfaces and auto-Guru** (when the pack includes `seed-050` / `render_agent_surfaces.py` / Guru) — see below
6. Verify docs gate: **with MCP**, run **`wave_garden`** (when metadata needs refresh) then **`wave_validate`**; **without MCP**, run `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`

## Agent surfaces and auto-Guru (agents must apply)

Canonical procedure: `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` § **Agent surfaces and auto-Guru upgrade (agent procedure)**. Apply **all** steps in every target repository — not only Wavefoundry self-host.

**Required commands**

```bash
# Hooks, MCP JSON, bin launchers, and auto-Guru surfaces (when docs/agents/guru.md exists)
python3 .wavefoundry/framework/scripts/render_platform_surfaces.py

# Optional: agent routing only
python3 .wavefoundry/framework/scripts/render_agent_surfaces.py
```

**Agent checklist (merge + generate)**

1. **Tier 1 — `AGENTS.md`** (manual merge when sections missing; renderer does not replace these):
   - `## Codebase and documentation questions (auto-Guru)`
   - `### Agent platform routing` (all hosts; tier 1–2 for Junie, Air, Windsurf, Copilot, Warp)
2. **Guru role** — ensure `docs/agents/guru.md` exists (`Role: guru`); update `docs/prompts/index.md` **Guru** row
3. **Re-run renderer** after tier-1 backfill if those sections were just added
4. **Tier 2–3 — generated files** (do not hand-edit `waveframework:auto-guru` marker regions):
   - `.cursor/rules/auto-guru.mdc`, `.claude/agents/guru.md`, `.codex/skills/auto-guru/SKILL.md`
   - Marked blocks in `CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, `WARP.md`, `.github/copilot-instructions.md` when those files exist
5. **Verify** paths listed in `docs/agents/platform-mapping.md` § Auto-Guru routing
6. **Operator follow-up** — Codex: MCP reloads from committed `.codex/config.toml` automatically; Cursor/Claude: attach MCP and restart host; all hosts: restart MCP + project index per checklist below

## Secrets scan and resume

The 1.6 upgrade includes a secrets scan; understand which part blocks and how to recover:

- **Full-tree baseline (automatic, records).** The upgrade's final index phase runs the indexer's secrets scan, which auto-escalates to a **full-tree** scan when `docs/scan-findings.json` is absent (always true on a 1.5→1.6 upgrade) or when the ruleset/scanner version changed. It classifies every finding into `docs/scan-findings.json` up front. This scan **records**, it does not fail the upgrade.
- **Docs gate (incremental, records — does NOT block).** The upgrade docs gate runs an **incremental** secrets scan (changed files) in **record-only** mode (wave 1p5pz): a `pending`/`suspected-secret` finding is recorded to `docs/scan-findings.json` and surfaced as a non-fatal `[secrets]` notice, but it **does not fail the docs gate or halt the upgrade**. (Only a malformed inline-suppression directive is a lint error.) So a found secret never blocks an upgrade.
- **Enforcement is at `wave_close`, not the upgrade.** Unresolved findings (`pending`/`suspected-secret`) **hard-block the next `wave_close`** until classified via the security reviewer (seed-213); `confirmed-secret` is non-blocking + reminded. Classify the baseline + incremental findings before your next wave close — the upgrade itself proceeds regardless.

## Supported version range

- **Floor: 1.4.0.** Upgrading from below 1.4.0 (or from an unparseable version) prints a **warning and proceeds** — migrations for transitions older than 1.4→1.5 have been pruned, so a jump from below the floor may skip an intermediate migration. All known projects are ≥ 1.5.1, so this never fires in practice; it documents the supported range.
- **Multi-version skips are allowed.** Only downgrades are blocked. A single-run skip (e.g. 1.4.x → 1.6) works — the version-gated 1.4→1.5 migrations still fire on the way through. The common path is 1.5.x → 1.6, a single step.

## Config review recommendation (major/minor upgrades)

On a **major or minor** upgrade (e.g. 1.5 → 1.6), the upgrade summary surfaces a one-line recommendation that a **senior / principal architect or engineer** evaluate whether to run the **Framework Config Review** (`docs/prompts/framework-config-review.prompt.md`) — a removal-biased audit of the agent operating surface (AGENTS.md/CLAUDE.md, seeds, prompts, constraints, memory, doc-sync). It is **recommend-only and human-initiated**: it never runs automatically and never blocks the upgrade. Patch upgrades do not surface it. There is no state/threshold — the cadence is simply "evaluate it at each major/minor upgrade."

## Verification Checklist

See `docs/contributing/build-and-verification.md` **Wave framework pack upgrade verification** for the ordered operator commands.

1. Framework tests: `python3 .wavefoundry/framework/scripts/run_tests.py`
2. Docs gate: **`wave_garden`** / **`wave_validate`** over MCP when available; otherwise `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`
3. Verify host registration and CLI launch paths generated by the current pack:
   - `.cursor/mcp.json` exists and contains `mcpServers.wavefoundry` after `render_platform_surfaces --platform cursor`
   - `.mcp.json` and `.junie/mcp/mcp.json` still include the Wavefoundry stdio entry when those hosts are used
   - `.codex/config.toml` exists at the project root and contains a `[mcp_servers.wavefoundry]` entry using the venv Python launcher
   - `.wavefoundry/bin/docs-lint` and `.wavefoundry/bin/docs-gardener` exist and point to `.wavefoundry/framework/scripts/`
4. **Check version transitions:** A `CHUNKER_VERSION`/model bump requires a full semantic re-embed; a `GRAPH_BUILDER_VERSION` bump requires a graph re-extract (graph-only — fast). The upgrade's final index phase handles **both** automatically (incremental, or escalating to a rebuild on a version bump), so neither normally needs a manual command. 1.8.1 bumps `GRAPH_BUILDER_VERSION` only (32→35) → the upgrade graph-only re-extracts; no re-embed. Run `wave_index_health()` to verify — a `chunker_version_mismatch` advisory flags a still-needed semantic rebuild; `graph.<layer>.last_built_at` shows graph freshness. When a manual re-embed IS needed, rebuild using the docs-first approach so MCP is available immediately:
   ```bash
   python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --full
   python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --background-code --full
   ```
   If either setup command fails because a required model download is blocked by missing network access, ask the operator for permission to rerun the same canonical setup command with network access or host escalation enabled; do not replace this with a separate manual model-download step.
   See `docs/contributing/build-and-verification.md` **Upgrade rebuild requirement** for time estimates (~6 min total).
5. Validate upgrade-recovery tools from the upgraded MCP server:
   - `wave_audit` returns a combined `wave` + `validation` + `index` payload
   - `wave_server_info` returns the current `repo_root` and implementation version info for the attached MCP server
   - `wave_index_build` is available for deterministic project/framework index rebuilds
6. **Reload MCP, then re-index after the editing pass:** Reload the upgraded server in-process with `wave_mcp_reload()` (or `wave_upgrade` cleanup) so the new server code and rendered host config take effect — a full host restart is only needed for hosts that cannot hot-reload. The upgrade already ran an index update as its final phase; you only need a manual re-index **after** the agent editing pass changed docs:
   ```
   wave_index_build(content="docs", mode="update")                          ← project
   ```
   Use `mode="rebuild"` after a version transition (moving to 1.6 bumps `CHUNKER_VERSION` and `GRAPH_BUILDER_VERSION` — see step 4). The framework index is shipped inside the pack; do not rebuild it during an ordinary upgrade unless the pack itself invalidated it or you are intentionally reindexing the Wavefoundry source repo. See `docs/contributing/build-and-verification.md` **Upgrade index rule**.
   - If the refresh is detached or backgrounded, poll `wave_index_build_status(layer?)` until it finishes before you rely on the refreshed search state.
   - Treat the reload + post-edit re-index as part of the upgrade, not optional cleanup. Until the reload happens, the repository may still be running old MCP code or stale search state.
7. Review diff of pack changes, hooks, `docs/prompts/`, manifests
8. Commit (operator-owned)

## Optional Dashboard Verification

If the upgraded pack includes the local dashboard feature, verify the Start / Stop / Restart dashboard surfaces exist and the start path opens cleanly:

```bash
python3 .wavefoundry/framework/scripts/dashboard_server.py --root . --open
```

The command must always print the final bound URL, even when it opens the browser automatically.

## Protected Surfaces

Inventory/drift-detection subagents run read-only. Broad edits to `docs/prompts/`, `AGENTS.md`, or hook configs require `framework_edit_allowed` guard approval and a concise file-level plan before execution.

## Git Commits

**Operator-owned.** Agent hands off diff + suggested message. Operator commits.

## Aliases

- **Upgrade wave framework** / **Upgrade wave context** — legacy; identical behavior
