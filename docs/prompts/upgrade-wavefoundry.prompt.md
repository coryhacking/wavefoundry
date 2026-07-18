# Upgrade Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-07-17

Shortcut: **`Upgrade Wavefoundry`** | Legacy: **`Upgrade wave framework`** / **`Upgrade wave context`**

## Purpose

Upgrade the Wave Framework operating surface in a target repository. Reconciles the rendered local docs, prompt surface, platform hook/config surfaces, the repo-local Codex bootstrap launcher, and `AGENTS.md` with the current canonical framework source.

## How Framework Updates Work

Use this prompt when the repository is already seeded and you want it to adopt a newer Wavefoundry framework pack or reconcile against a newer local `.wavefoundry/framework/` tree.

The expected operator flow is:

1. Put the new framework in reach of this repository.
   - Usually this means building or placing `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` in the repository root, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`.
   - If the repository already has the desired newer `.wavefoundry/framework/` tree staged locally, the upgrade runs against that tree directly.
   - **Never `ls` for the pack to decide whether one exists.** It almost always lives in `~/.wavefoundry/dist/`, not the repo root, so an empty `ls wavefoundry-*.zip` at the repo root does **not** mean there's no pack. Determine it only via `wf upgrade --detect-zip` / `--list-zips` / `--dry-run` (see *Agent-safe zip discovery* below).
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
   - **Mandatory reload after a `GRAPH_BUILDER_VERSION` bump — a non-reloaded server DOWNGRADES the graph.** An already-running MCP server keeps the pre-upgrade graph extractor in memory for its whole lifetime. Phase 4b re-extracts the graph at the new version during the upgrade, but the first graph query on a still-stale server re-extracts it back DOWN to the old version using its in-memory extractor — silently reverting the upgrade's graph work. `wave_mcp_reload()` (or a host restart) loads the new extractor first, so the safety-net auto-rebuild can never invert into a downgrade.

What this prompt is not:

- It is **not** packaging. Packaging creates a new zip in the framework source repo.
- It is **not** init. Use init only for first-time seeding or legacy routing cases.
- It is **not** a manual unzip checklist. Root zip adoption is built into the upgrade flow.

**Supported operator environments:** macOS and Linux are supported natively. Windows is currently supported through **WSL2** for upgrade and operator workflows because some launcher and shell steps still assume a POSIX environment.

**Python requirement:** Python 3.11 or later is required. Framework dependencies are installed into a shared tool environment at `~/.wavefoundry/venv` (or `$WAVEFOUNDRY_TOOL_VENV` to override); `wf setup` is the operator command to create/populate it and run the index setup flow when the dispatcher is on PATH. If `wf` is not on PATH, use the setup step documented in the install prompt. If the setup step fails specifically because a required model cannot be downloaded, keep recovery on the canonical setup path: in agent-driven sessions, the agent should ask the operator for permission to rerun the same setup command with network access or host escalation enabled instead of doing an out-of-band manual model download.

## Upgrade Steps

**MCP-first (do this when the Wavefoundry MCP is attached).** Drive the upgrade with the **`wave_upgrade()`** tool — it runs the phases for you (pre-flight → adopt the highest pack → extract → render surfaces → prune pack-removed files → docs gate), then `wave_upgrade(phase="update_index")` / `wave_upgrade(phase="cleanup")`. Poll/inspect the lock state with **`wave_upgrade_status()`** between phases and **before any reload/restart**. This mirrors the "prefer MCP over shell launchers" parity used for docs validation: the tool does the mechanical reconciliation (prune the retired files, re-render to `bin/wf`, re-heal the `python3` command) automatically — going manual and skipping those phases is exactly what leaves stale surfaces behind. **The steps below are the no-MCP CLI fallback (`./.wavefoundry/bin/wf upgrade` on POSIX, `.\.wavefoundry\bin\wf.cmd upgrade` on native Windows)** — follow them only when no MCP host is attached; they are not the default path. **Read the response's `data.summary` block** for computed fields — `from_version`/`to_version`, `pruned_count`, `docs_gate`, `index_update`, `failed_phase`, `is_major_or_minor`, and the `reconciliation` findings list — plus the top-level `next_step`; do not regex-scrape the raw `output` for these. **Phase semantics (wave 1p8kz):** the PRIMARY/default call — `wave_upgrade()` (phase `preflight_to_docs_gate`) — already returns `data.summary`, **including the `reconciliation` findings**. The reconciliation scan + `summary.reconciliation` run on **every upgrade** — any version delta, including a patch bump (e.g. 1.9.4→1.9.5) and a same-version build-successor (a rebuilt pack at the same semver during testing) — because a patch or build-successor can change or RETIRE a surface too; `is_major_or_minor` is an **informational** field only and no longer gates the scan. Read `data.summary` directly from that primary response — you do **not** have to wait for the `cleanup` phase. The `wave_upgrade(phase="cleanup")` call additionally prints the full human-readable operator summary prose (and reloads the server); both emissions are rendered from one builder, so their structured fields agree.

**Reconciliation on every upgrade (the upgrade runs a scan; you act on it).** On **every upgrade** — any version delta, including a patch bump and a same-version build-successor, since a patch can change/retire a surface during testing (`is_major_or_minor` is informational, not a gate) — after the mechanical phases complete the upgrade **runs the retired-surface reconciliation scan** (`reconcile_scan.py`, shipped under `.wavefoundry/framework/scripts/`) over THIS repo and surfaces an actionable `file:line → suggested wf form` list in the operator summary (`wave_upgrade`'s `summary.reconciliation` field; the human prose lists the same). The scan flags docs/prompts/configs/scripts that named a framework surface the bump **changed or RETIRED** — e.g. the 1.9.0 cutover retired the `.wavefoundry/bin/*` wrappers in favor of the cross-OS `wf` dispatcher, so a local doc still naming `.wavefoundry/bin/<wrapper>` is now a broken instruction. The scan consumes the single retired→new map co-located with `_RETIRED_BIN_WRAPPERS` in `render_platform_surfaces.py`: renames map 1:1 to `wf <subcommand>` (e.g. `docs-lint`→`wf docs-lint`, `wave-gate`→`wf gate`, `wave-dashboard`→`wf dashboard`), and `mcp-server` has **no** `wf` form — remove/rewrite it (the MCP server launches via `python3 .wavefoundry/framework/scripts/server.py`). The scan is **report-only** (it never auto-edits repo docs): apply each suggested edit yourself, then re-run the drift detection in the Verification Checklist to confirm. The scan's baked-in exclusion set never flags the framework pack tree, the generated index, `docs/waves/`, `docs/reports/`, `CHANGELOG.md`, journals/snapshots, or test files.

**Host permission/allow-rule files (flag for the operator — do not self-edit).** The scan does **not** cover host permission/allow-rule files (e.g. `.claude/settings.local.json` allow rules, and per-host equivalents). When a renamed surface changes the command an allow rule references, **flag it for the operator** in the upgrade summary — agents cannot self-edit those files under host auto-mode guards. Name the stale rule and the new `wf <subcommand>` form; let the operator make the edit.

**Versioning contract:** Releases use `MAJOR.MINOR.PATCH` semver. The version appears as `MAJOR.MINOR.PATCH+<build>` in `VERSION` and `framework_revision`, and as `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` in filenames. See `docs/architecture/decisions/12tm5-adr semver-versioning-contract.md` for the version bump policy.

**Distribution directories:** `upgrade_wavefoundry.py` searches the repository root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, and `~/Downloads/`, then picks the highest semver zip. Non-matching filenames are skipped silently.

**Agent-safe zip discovery (use these, not `ls`):** Never use `ls`/`find` to locate or choose the pack. Two reasons it gives the wrong answer: (1) it only sees the directory you point it at — the pack usually lives in `~/.wavefoundry/dist/`, so `ls wavefoundry-*.zip` at the repo root finds nothing and an agent wrongly concludes "already current / nothing to upgrade"; (2) `ls -1 ~/.wavefoundry/dist/` sorts lexicographically and ranks `wavefoundry-1.3.9.*.zip` *above* `wavefoundry-1.3.30.*.zip`, selecting a stale pack. Use the script flags instead — all run the same semver comparator over all five search paths the upgrade itself uses:

- `wf upgrade --detect-zip` — prints the absolute path of the selected pack and exits `0`. Exits `1` with empty output when no matching zip is found.
- `wf upgrade --list-zips` — prints every match across all five search paths, semver-sorted (highest first), with `* ` on the selected pack.
- `wf upgrade --dry-run` — prints the selected pack on a `Zip to apply:` line in the same output that surfaces seed diffs and hook inventory, with zero mutations.

Discovery/preview is **CLI-only**: run the flag via your shell (that is the agent-safe path — not `ls`). The MCP `wave_upgrade` tool *runs* the upgrade — its default `preflight_to_docs_gate` phase adopts the highest pack — and has **no** dry-run or discovery-only phase (its only argument is `phase=`; there is no `mode=`).

**Step 0 (optional zip adoption):** If a `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` is in the repository root, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`, the upgrade seed stages the selected pack under `.wavefoundry/framework/`, runs `wf render-surfaces`, and continues full reconciliation. Non-matching filenames are skipped. The shell-heavy upgrade flow still runs from **WSL2** on Windows; the no-PATH dispatcher fallback above is the native-Windows form. The pack ships the single-use bootstrap `install-wavefoundry.md` at the zip root, so extraction re-drops it at the repository root; the upgrade removes it automatically (`wave_upgrade` / `wf upgrade`). If you run a fully-manual `unzip -o`, delete it yourself after pruning (`rm -f install-wavefoundry.md`).

**Full reconciliation:**
1. Inventory current state (seed-030 in targeted mode)
2. Drift-detect against canonical framework (read-only subagents for inventory)
3. Produce a file-level upgrade plan before broad edits
4. Reconcile prompt surface, platform surfaces, `AGENTS.md`, manifests
5. **Agent surfaces and auto-Guru** (when the pack includes `seed-050` / `render_agent_surfaces.py` / Guru) — see below
6. Verify docs gate: **with MCP**, run **`wave_garden`** (when metadata needs refresh) then **`wave_validate`**; **without MCP**, run `./.wavefoundry/bin/wf docs-gardener && ./.wavefoundry/bin/wf docs-lint` on POSIX or `.\\.wavefoundry\\bin\\wf.cmd docs-gardener && .\\.wavefoundry\\bin\\wf.cmd docs-lint` on native Windows

## Agent surfaces and auto-Guru (agents must apply)

Canonical procedure: `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` § **Agent surfaces and auto-Guru upgrade (agent procedure)**. Apply **all** steps in every target repository — not only Wavefoundry self-host.

**Required commands**

```bash
# Hooks, MCP JSON, bin launchers, and auto-Guru surfaces (when docs/agents/guru.md exists)
wf render-surfaces

# Optional: agent routing only
python3 .wavefoundry/framework/scripts/render_agent_surfaces.py
```

**Agent checklist (merge + generate)**

1. **Tier 1 — `AGENTS.md`** (manual merge when sections missing; renderer does not replace these):
   - `## Codebase and documentation questions (auto-Guru)`
   - `### Agent platform routing` (all hosts; tier 1–2 for Junie, Air, Windsurf, Copilot, Warp)
2. **Guru role** — ensure `docs/agents/guru.md` exists (`Role: guru`); update `docs/prompts/index.md` **Guru** row
3. **Re-run renderer** after tier-1 backfill if those sections were just added
4. **Tier 2–3 — generated files** (do not hand-edit `wave:auto-guru` marker regions):
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

## Reconciliation scan (major/minor upgrades)

On a **major or minor** upgrade, the upgrade **runs the retired-surface reconciliation scan** (`reconcile_scan.py`, shipped under `.wavefoundry/framework/scripts/`) over THIS repo and surfaces an actionable `file:line → suggested wf form` list in the operator summary (`wave_upgrade`'s `summary.reconciliation` field; the human prose lists the same). It flags local surfaces (docs, prompts, configs, scripts) that referenced a framework surface the bump **changed or RETIRED**. Concrete example: the 1.9.0 cutover retired the `.wavefoundry/bin/*` wrappers in favor of the cross-OS `wf` dispatcher, so a local doc still naming `.wavefoundry/bin/<wrapper>` is now a broken instruction. The scan consumes the single retired→new map co-located with `_RETIRED_BIN_WRAPPERS` in `render_platform_surfaces.py`: renames map 1:1 to `wf <subcommand>` (e.g. `docs-lint`→`wf docs-lint`, `wave-gate`→`wf gate`, `wave-dashboard`→`wf dashboard`), and `mcp-server` has **no** `wf` form — remove/rewrite it (the MCP server launches via `python3 .wavefoundry/framework/scripts/server.py`). The mechanical reconciliation (prune pack-removed files, re-render surfaces, re-heal the `python3` command) is automatic when `wave_upgrade()` runs its phases; the scan is **report-only** for the local-surface part agents must still judge — apply each suggested edit yourself, then re-run the drift detection in the Verification Checklist. The exclusion set never flags the framework pack tree, the generated index, `docs/waves/`, `docs/reports/`, `CHANGELOG.md`, journals/snapshots, or test files. **Host permission/allow-rule files** (e.g. `.claude/settings.local.json` allow rules) are **not** scanned — flag a stale allow rule for the operator rather than self-editing it (host auto-mode guards block agent edits there). Patch upgrades skip the scan; never blocks.

## Verification Checklist

See `docs/contributing/build-and-verification.md` **Wave framework pack upgrade verification** for the ordered operator commands.

1. Framework tests: `python3 .wavefoundry/framework/scripts/run_tests.py`
2. Docs gate: **`wave_garden`** / **`wave_validate`** over MCP when available; otherwise `wf docs-gardener && wf docs-lint`. **Gate-before-reload window:** when MCP is attached but still running the **pre-upgrade** server impl (new code is on disk but the in-process server has not reloaded yet — i.e. before the `wave_mcp_reload()` step), prefer the **`wf` CLI docs gate** here rather than the MCP `wave_validate`/`wave_garden` tools — those would run the stale in-process impl against the new tree. The CLI path is correct in that window, not only a no-MCP fallback; switch back to the MCP tools once the reload lands.
3. Verify host registration and CLI launch paths generated by the current pack:
   - `.cursor/mcp.json` exists and contains `mcpServers.wavefoundry` after `render_platform_surfaces --platform cursor`
   - `.mcp.json` and `.junie/mcp/mcp.json` still include the Wavefoundry stdio entry when those hosts are used
   - `.codex/config.toml` exists at the project root and contains a `[mcp_servers.wavefoundry]` entry using the venv Python launcher
   - The cross-OS `wf` entry point and generated `wf.cmd` shim route the no-PATH forms — POSIX `./.wavefoundry/bin/wf docs-lint` / `./.wavefoundry/bin/wf docs-gardener`, native Windows `.\\.wavefoundry\\bin\\wf.cmd docs-lint` / `.\\.wavefoundry\\bin\\wf.cmd docs-gardener` — to `.wavefoundry/framework/scripts/` via `wf_cli.py`
4. **Check version transitions:** A `CHUNKER_VERSION`/model bump requires a full semantic re-embed; a `GRAPH_BUILDER_VERSION` bump requires a graph re-extract (graph-only — fast). The upgrade's final index phase handles **both** automatically (incremental, or escalating to a rebuild on a version bump), so neither normally needs a manual command. 1.8.1 bumps `GRAPH_BUILDER_VERSION` only (32→35) → the upgrade graph-only re-extracts; no re-embed. Run `wave_index_health()` to verify — a `chunker_version_mismatch` advisory flags a still-needed semantic rebuild; `graph.<layer>.last_built_at` shows graph freshness. When a manual re-embed IS needed, rebuild with the default foreground docs+code setup path:
   ```bash
   wf setup --full
   ```
   If setup fails because a required model download is blocked by missing network access, ask the operator for permission to rerun the same canonical setup command with network access or host escalation enabled; do not replace this with a separate manual model-download step.
   See `docs/contributing/build-and-verification.md` **Upgrade rebuild requirement** for time estimates (~6 min total).
5. Validate upgrade-recovery tools from the upgraded MCP server:
   - `wave_audit` returns a combined `wave` + `validation` + `index` payload
   - `wave_server_info` returns the current `repo_root` and implementation version info for the attached MCP server
   - `wave_index_build` is available for deterministic project index rebuilds
6. **Reload MCP, then re-index after the editing pass:** Reload the upgraded server in-process with `wave_mcp_reload()` (or `wave_upgrade` cleanup) so the new server code and rendered host config take effect — a full host restart is only needed for hosts that cannot hot-reload. The upgrade already ran an index update as its final phase; you only need a manual re-index **after** the agent editing pass changed docs:
   ```
   wave_index_build(content="docs", mode="update")                          ← project
   ```
   Use `mode="rebuild"` after a version transition (moving to 1.6 bumps `CHUNKER_VERSION` and `GRAPH_BUILDER_VERSION` — see step 4). There is a single project index (the framework's seeds fold into it) — no separate framework index to rebuild. See `docs/contributing/build-and-verification.md` **Upgrade index rule**.
   - If the refresh is detached or backgrounded, poll `wave_index_build_status(layer?)` until it finishes before you rely on the refreshed search state.
   - Treat the reload + post-edit re-index as part of the upgrade, not optional cleanup. Until the reload happens, the repository may still be running old MCP code or stale search state. **After a `GRAPH_BUILDER_VERSION` bump this is not optional:** issuing any graph query (`code_callhierarchy`, `code_impact`, `wave_graph_report`, …) before the reload makes the stale server re-extract the graph DOWN to its old builder version — reload first, then query.
7. Review diff of pack changes, hooks, `docs/prompts/`, manifests
8. Commit (operator-owned)

## Optional Dashboard Verification

If the upgraded pack includes the local dashboard feature, verify the Start / Stop / Restart dashboard surfaces exist and the start path opens cleanly:

```bash
wf dashboard --root . --open
```

The command must always print the final bound URL, even when it opens the browser automatically.

## Protected Surfaces

Inventory/drift-detection subagents run read-only. Broad edits to `docs/prompts/`, `AGENTS.md`, or hook configs require `framework_edit_allowed` guard approval and a concise file-level plan before execution.

## Git Commits

**Operator-owned.** Agent hands off diff + suggested message. Operator commits.

## Aliases

- **Upgrade wave framework** / **Upgrade wave context** — legacy; identical behavior
