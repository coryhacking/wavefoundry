# Upgrade Wave Framework

Owner: Engineering
Status: active
Last verified: 2026-05-26

Shortcut: **`Upgrade wave framework`** | Legacy: **`Upgrade Wavefoundry`** / **`Upgrade wave context`**

## Purpose

Upgrade the Wave Framework operating surface in a target repository. Reconciles the rendered local docs, prompt surface, platform hook/config surfaces, the repo-local Codex bootstrap launcher, and `AGENTS.md` with the current canonical framework source.

## How Framework Updates Work

Use this prompt when the repository is already seeded and you want it to adopt a newer Wavefoundry framework pack or reconcile against a newer local `.wavefoundry/framework/` tree.

The expected operator flow is:

1. Put the new framework in reach of this repository.
   - Usually this means building or placing `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` in the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/`.
   - If the repository already has the desired newer `.wavefoundry/framework/` tree staged locally, the upgrade runs against that tree directly.
2. Run **Upgrade wave framework**.
   - If a root `wavefoundry-*.zip` is present, upgrade automatically unpacks the newest matching zip first.
   - It then regenerates tracked platform surfaces, reconciles docs/prompts/config, and validates drift.
3. Restart the MCP server after the upgrade finishes.
   - The upgraded server code and regenerated host config do not take effect until the running MCP process is restarted.
   - If you use Codex, the MCP server reloads from the committed `.codex/config.toml` automatically — no re-registration needed after upgrade.
4. Update indexes after restart.
   - Normal framework updates: run docs-layer index updates.
   - Chunker/schema changes: run a full rebuild instead.

What this prompt is not:

- It is **not** packaging. Packaging creates a new zip in the framework source repo.
- It is **not** init. Use init only for first-time seeding or legacy routing cases.
- It is **not** a manual unzip checklist. Root zip adoption is built into the upgrade flow.

**Supported operator environments:** macOS and Linux are supported natively. Windows is currently supported through **WSL2** for upgrade and operator workflows because some launcher and shell steps still assume a POSIX environment.

**Python requirement:** Python 3.11 or later is required. Framework dependencies are installed into a shared tool environment at `~/.wavefoundry/venv` (or `$WAVEFOUNDRY_TOOL_VENV` to override); running `setup_wavefoundry.py` is the preferred way to create/populate it and run the index setup flow. `setup_index.py` remains supported as the compatibility entrypoint behind it. If `setup_wavefoundry.py` fails specifically because a required model cannot be downloaded, keep recovery on the canonical setup path: in agent-driven sessions, the agent should ask the operator for permission to rerun the same setup command with network access or host escalation enabled instead of doing an out-of-band manual model download.

## Upgrade Steps

**Versioning contract:** Releases use `MAJOR.MINOR.PATCH` semver. The version appears as `MAJOR.MINOR.PATCH+<build>` in `VERSION` and `framework_revision`, and as `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` in filenames. See `docs/architecture/decisions/12tm5-adr semver-versioning-contract.md` for the version bump policy.

**Distribution directories:** `upgrade_wavefoundry.py` searches the repository root, `~/.wavefoundry/`, and `~/.wavefoundry/dist/`, then picks the highest semver zip. Non-matching filenames are skipped silently.

**Step 0 (optional zip adoption):** If a `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` is in the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/`, the upgrade seed stages the selected pack under `.wavefoundry/framework/`, runs `render_platform_surfaces.py`, and continues full reconciliation. Non-matching filenames are skipped. On Windows, run this flow from **WSL2** rather than native `cmd.exe` or PowerShell.

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
2. **Guru role** — ensure `docs/agents/guru.md` exists (`Role: guru`); migrate from legacy `code-insight-agent` paths when present; update `docs/prompts/index.md` **Guru** row
3. **Re-run renderer** after tier-1 backfill if those sections were just added
4. **Tier 2–3 — generated files** (do not hand-edit `waveframework:auto-guru` marker regions):
   - `.cursor/rules/auto-guru.mdc`, `.claude/agents/guru.md`, `.codex/skills/auto-guru/SKILL.md`
   - Marked blocks in `CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, `WARP.md`, `.github/copilot-instructions.md` when those files exist
5. **Verify** paths listed in `docs/agents/platform-mapping.md` § Auto-Guru routing
6. **Operator follow-up** — Codex: MCP reloads from committed `.codex/config.toml` automatically; Cursor/Claude: attach MCP and restart host; all hosts: restart MCP + project index per checklist below

## Verification Checklist

See `docs/contributing/build-and-verification.md` **Wave framework pack upgrade verification** for the ordered operator commands.

1. Framework tests: `python3 .wavefoundry/framework/scripts/run_tests.py`
2. Docs gate: **`wave_garden`** / **`wave_validate`** over MCP when available; otherwise `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`
3. Verify host registration and CLI launch paths generated by the current pack:
   - `.cursor/mcp.json` exists and contains `mcpServers.wavefoundry` after `render_platform_surfaces --platform cursor`
   - `.mcp.json` and `.junie/mcp/mcp.json` still include the Wavefoundry stdio entry when those hosts are used
   - `.codex/config.toml` exists at the project root and contains a `[mcp_servers.wavefoundry]` entry using the venv Python launcher
   - `.wavefoundry/bin/docs-lint` and `.wavefoundry/bin/docs-gardener` exist and point to `.wavefoundry/framework/scripts/`
4. **Check `CHUNKER_VERSION`:** If the pack bumped `CHUNKER_VERSION`, a full index rebuild is required. Run `wave_index_health()` — a `chunker_version_mismatch` advisory confirms the rebuild is needed. Rebuild using the docs-first approach so MCP is available immediately:
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
6. **Restart MCP and update indexes:** Restart the MCP server so the upgraded server and any newly rendered hook/config surfaces take effect. Then update the project index:
   ```
   wave_index_build(content="docs", mode="update")                          ← project
   ```
   If `CHUNKER_VERSION` changed (step 4), use `mode="rebuild"` instead. The framework index is shipped inside the pack; do not rebuild it during an ordinary upgrade unless the pack itself invalidated it or you are intentionally reindexing the Wavefoundry source repo. See `docs/contributing/build-and-verification.md` **Upgrade index rule**.
   - If the refresh is detached or backgrounded, poll `wave_index_build_status(layer?)` until it finishes before you rely on the refreshed search state.
   - Treat the restart + project index update as part of the upgrade, not optional cleanup. Until restart happens, the repository may still be running old MCP code or stale search state.
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

- **Upgrade wave context** — legacy; identical behavior
