# Upgrade Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-08-15

Shortcut: **`Upgrade Wavefoundry`** | Legacy: **`Upgrade wave framework`** / **`Upgrade wave context`**

## Purpose

Upgrade the Wave Framework operating surface in a target repository. Reconciles the rendered local docs, prompt surface, platform hook/config surfaces, the repo-local Codex bootstrap launcher, and `AGENTS.md` with the current canonical framework source.

## How Framework Updates Work

Use this prompt when the repository is already seeded and you want it to adopt a newer Wavefoundry framework pack or reconcile against a newer local `.wavefoundry/framework/` tree.

The expected operator flow is:

1. Put the new framework in reach of this repository.
   - Usually this means building or placing `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` in the repository root, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`. For offline model setup, place the feature ZIP and the model-set asset it declares (`wavefoundry-models-2.zip` beginning with Wavefoundry 1.16.0) in any of those standard distribution directories. Discovery ignores model assets as framework packs, selects the exact declared model-set version, and setup verifies its component hashes and licenses before indexing.
   - If the repository already has the desired newer `.wavefoundry/framework/` tree staged locally, the upgrade runs against that tree directly.
   - **Never `ls` for the pack to decide whether one exists.** It almost always lives in `~/.wavefoundry/dist/`, not the repo root, so an empty `ls wavefoundry-*.zip` at the repo root does **not** mean there's no pack. Determine it only via `wf upgrade --detect-zip` / `--list-zips` / `--dry-run` (see *Agent-safe zip discovery* below).
   - A standard-only upgrade checks the managed model-set identity but does not replace a verified cache with an unpinned upstream revision. If its release-pinned policy is newer, it retains the working cache and names the matching companion as the deterministic update path; missing models still use the normal setup download path.
2. Run **Upgrade Wavefoundry**.
   - If a root `wavefoundry-*.zip` is present, upgrade automatically unpacks the newest matching zip first.
   - It then regenerates tracked platform surfaces, reconciles docs/prompts/config, and validates drift.
3. Reload the MCP server **in-process** when the upgrade finishes.
   - The upgrade reloads the server code in-process — call `wf_reload_mcp()` (or run `wf_upgrade` cleanup, which reloads automatically). Tool additions/removals and description changes dispatch `notifications/tools/list_changed`, but the reload response proves only server-side registration/dispatch, not client adoption. A model invocation already in flight may retain its start-of-turn tool schema: check from a fresh turn first, reconnect MCP if still stale, and use a full host restart only as the final fallback.
   - **Exception — upgrades that RENAME MCP tools require a full restart of every attached host (or fresh sessions), not a hot reload.** The 1.14.0 release renames the whole tool surface (`wave_*` to `wf_*`/`memory_*`/`index_*`), including the reload tool itself: upgrading sessions still hold the OLD in-memory tool names, and the hot-reload path cannot re-register the renamed reload survivor from inside an old process. After upgrading across such a boundary, fully quit and restart every attached agent host (or start fresh conversations); until then old sessions' tools are stale and renamed-tool calls fail. The reconciliation scan lists the old-to-new tool renames alongside the retired-wrapper findings. Stale `mcp__wavefoundry__<old-name>` allow rules split by ownership: rules the permissions renderer recorded emitting into the committed `.claude/settings.json` (its `wavefoundryManagedAllow` provenance) **self-heal on the upgrade render** and surface only informationally in the `renderer_provenance_flags` channel; everything else (`.claude/settings.local.json`, non-provenance `settings.json` rules, per-host equivalents) still surfaces in the operator flags channel, and the operator must update those rules or every renamed tool call will prompt.
   - **Exception: a cutover-active 1.15 events-only review-evidence upgrade run requires a full restart of every attached MCP/agent host, including the invoking one, not a hot reload.** The restart requirement is scoped: `restart_required` is true only on cutover-active runs (the run removed a retired review-evidence sidecar or the stale v1.13 root lock, or the installed version predates 1.15; an unknown installed version is treated fail-safe as pre-1.15). On a cutover-active run the upgrade suppresses its own automatic in-process reload at both automatic-reload phases, removes `wf_reload_mcp` from the suggested next tools, and instructs the full host restart in the response; do not reload in-process on such a run. The suppression executes in the invoking host's already-loaded server code, so it is guaranteed only when that host already runs 1.15-or-later code; an upgrade invoked from a pre-1.15 host may still fire its old unconditional in-process reload, which loads the new module but does not substitute for the full restart; the full-restart instruction, delivered in the upgrade summary, stands either way. Ordinary post-1.15 upgrades, and reruns on an already-converged repository, keep the normal in-process reload flow above and report no cutover restart requirement. One narrow exception: when the upgrade pauses action-required at the historical-memory gate, that response still names `wf_reload_mcp`, because the reload is required to continue the upgrade itself; the final cleanup response still carries the full-restart instruction.
   - If you use Codex, the MCP server reloads from the committed `.codex/config.toml` automatically — no re-registration needed after upgrade.
4. The index update runs **automatically** at the end of the upgrade.
   - The upgrade's final phase updates **both** the semantic indexes and the graph, each version-aware: an incremental update normally, auto-escalating to a full rebuild when its version advanced — semantic on a `CHUNKER_VERSION`/model bump (re-embed, minutes), graph on a `GRAPH_BUILDER_VERSION` bump (graph-only re-extract, ~10–30 s). You do **not** run a separate index command for a normal upgrade.
   - A manual `index_build(...)` / `--update-index` call is only for re-running after the agent editing pass or recovering a backgrounded code build (see the Verification Checklist).
   - So a graph-builder bump materializes **during the upgrade**, symmetric with the semantic indexes — no manual step. (The first-query in-process auto-rebuild remains a safety net.) **1.8.1** bumps `GRAPH_BUILDER_VERSION` only (32→35) → a graph-only re-extract (no re-embed) carrying the new edges/nodes: cross-language confidence promotion, `reads_config`, `instruments`, `.properties`/`.yml` config-key nodes.
   - **Mandatory reload after a `GRAPH_BUILDER_VERSION` bump — a non-reloaded server DOWNGRADES the graph.** An already-running MCP server keeps the pre-upgrade graph extractor in memory for its whole lifetime. Phase 4b re-extracts the graph at the new version during the upgrade, but the first graph query on a still-stale server re-extracts it back DOWN to the old version using its in-memory extractor — silently reverting the upgrade's graph work. `wf_reload_mcp()` (or a host restart) loads the new extractor first, so the safety-net auto-rebuild can never invert into a downgrade.

What this prompt is not:

- It is **not** packaging. Packaging creates a new zip in the framework source repo.
- It is **not** init. Use init only for first-time seeding or legacy routing cases.
- It is **not** a manual unzip checklist. Root zip adoption is built into the upgrade flow.

**Supported operator environments:** native Windows, WSL2, macOS, and Linux are first-class. Prefer the MCP path or the cross-platform `wf` / `wf.cmd` dispatcher for the host; structured argv is authoritative and display commands are rendered for the detected platform.

**Python requirement:** Python 3.11 or later is required. Framework dependencies are installed into a shared tool environment at `~/.wavefoundry/venv` (or `$WAVEFOUNDRY_TOOL_VENV` to override); `wf setup` is the operator command to create/populate it and run the index setup flow when the dispatcher is on PATH. If `wf` is not on PATH, use the setup step documented in the install prompt. If the setup step fails specifically because a required model cannot be downloaded, keep recovery on the canonical setup path: in agent-driven sessions, first ask the operator for permission to rerun the same setup command with network access or host escalation enabled. If that cannot complete, manually obtain the exact `wavefoundry-models-<set>.zip` asset from the same release (or an approved internal distribution), leave it zipped, place it in the target repository root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`, and rerun `wf setup`. It verifies the set, hashes, and licenses before replacing the cache; an invalid archive leaves a verified cache unchanged.

## Upgrade Steps

**MCP-first (do this when the Wavefoundry MCP is attached).** Drive the upgrade with the **`wf_upgrade()`** tool — it runs the phases for you (pre-flight → adopt the highest pack → extract → render surfaces → prune pack-removed files → docs gate), then `wf_upgrade(phase="update_index")` / `wf_upgrade(phase="cleanup")`. Poll/inspect the lock state with **`wf_upgrade_status()`** between phases and **before any reload/restart**. This mirrors the "prefer MCP over shell launchers" parity used for docs validation: the tool does the mechanical reconciliation (prune the retired files, re-render to `bin/wf`, re-heal the `python3` command) automatically — going manual and skipping those phases is exactly what leaves stale surfaces behind. **The steps below are the no-MCP CLI fallback (`./.wavefoundry/bin/wf upgrade` on POSIX, `.\.wavefoundry\bin\wf.cmd upgrade` on native Windows)** — follow them only when no MCP host is attached; they are not the default path. **Read the response's `data.summary` block** for computed fields — `from_version`/`to_version`, `pruned_count`, `docs_gate`, `index_update`, `failed_phase`, `is_major_or_minor`, and the `reconciliation` findings list — plus the top-level `next_step`; do not regex-scrape the raw `output` for these. **Phase semantics (wave 1p8kz):** the PRIMARY/default call — `wf_upgrade()` (phase `preflight_to_docs_gate`) — already returns `data.summary`, **including the `reconciliation` findings**. The reconciliation scan + `summary.reconciliation` run on **every upgrade** — any version delta, including a patch bump (e.g. 1.9.4→1.9.5) and a same-version build-successor (a rebuilt pack at the same semver during testing) — because a patch or build-successor can change or RETIRE a surface too; `is_major_or_minor` is an **informational** field only and no longer gates the scan. Read `data.summary` directly from that primary response — you do **not** have to wait for the `cleanup` phase. The `wf_upgrade(phase="cleanup")` call additionally prints the full human-readable operator summary prose (and reloads the server on non-cutover runs; on a cutover-active run the reload is suppressed and the response instructs a full host restart instead); both emissions are rendered from one builder, so their structured fields agree except on two provenance keys: the cleanup emission always carries `summary_schema_version`, which the primary emission carries only when its summary came from the delegated producer, and a degraded primary additionally carries `summary_source_degraded`, which a cleanup emission never carries. See **Reading token presence** below before reporting a missing token.

**Reconciliation on every upgrade (the upgrade runs a scan; you act on it).** On **every upgrade** — any version delta, including a patch bump and a same-version build-successor, since a patch can change/retire a surface during testing (`is_major_or_minor` is informational, not a gate) — after the mechanical phases complete the upgrade **runs the retired-surface reconciliation scan** (`reconcile_scan.py`, shipped under `.wavefoundry/framework/scripts/`) over THIS repo and surfaces an actionable `file:line → suggested wf form` list in the operator summary (`wf_upgrade`'s `summary.reconciliation` field; the human prose lists the same). The scan flags docs/prompts/configs/scripts that named a framework surface the bump **changed or RETIRED** — e.g. the 1.9.0 cutover retired the `.wavefoundry/bin/*` wrappers in favor of the cross-OS `wf` dispatcher, so a local doc still naming `.wavefoundry/bin/<wrapper>` is now a broken instruction. The scan consumes the single retired→new map co-located with `_RETIRED_BIN_WRAPPERS` in `render_platform_surfaces.py`: renames map 1:1 to `wf <subcommand>` (e.g. `docs-lint`→`wf docs-lint`, `wave-gate`→`wf gate`, `wave-dashboard`→`wf dashboard`), and `mcp-server` has **no** `wf` form — remove/rewrite it (the MCP server launches via `python3 .wavefoundry/framework/scripts/server.py`). The scan is **report-only** (it never auto-edits repo docs): apply each suggested edit yourself, then re-run the drift detection in the Verification Checklist to confirm. The scan's baked-in exclusion set never flags the framework pack tree, the generated index, `docs/waves/`, `docs/reports/`, `CHANGELOG.md`, journals/snapshots, or test files.

**Host permission/allow-rule files (three channels: self-healing vs operator).** The scan never folds host permission/allow-rule files (`.claude/settings.json`, `.claude/settings.local.json`, `.cursor/settings.json`, and per-host equivalents) into the editable `summary.reconciliation` list; agents cannot self-edit those files under host auto-mode guards. It still inspects them and partitions the hits by ownership: stale rules **inside** the permissions renderer's `wavefoundryManagedAllow` provenance in the committed `.claude/settings.json` are **SELF-HEALING** (`summary.renderer_provenance_flags`: the upgrade/install permissions render prunes/replaces them automatically; the upgrade renders surfaces before it scans, so these are informational), while everything else (all of `.claude/settings.local.json` and `.cursor/settings.json`, plus any non-provenance `settings.json` entry, including operator-authored rules that happen to name a wavefoundry tool) stays in the operator channel (`summary.host_permission_flags`): **flag it for the operator**, name the stale rule and the new `wf <subcommand>` form, and let the operator make the edit. The upgrade also names the rendered permissions delta (added/removed `permissions.allow` entries) as an explicit consent line in its output.

**When the permissions block first appears, and who can trigger the render.** A fresh install and a protocol-bridge upgrade render the permissions block immediately. An ordinary upgrade of an existing target also renders it during that same upgrade, but only because of deliberate backstops in the upgrade's later phases: the in-process orchestrator that runs the surface-rendering phase is pre-extraction code, so on the transition upgrade that phase runs the OLD renderer, which has no permissions switch. The backstops run only from phases the upgrade executes in a SEPARATE process on the freshly extracted code, which is what closes that old-code window. The cleanup phase carries the site every upgrade path reaches (`wf upgrade --cleanup` on the CLI, `wf_upgrade(phase="cleanup")` through MCP); the index-refresh phase carries a second one for the flows that run it. Without them the block would first appear one full upgrade cycle later. Rendering is **operator-approved rather than structurally unreachable by an agent**: `wf_upgrade` is an ordinary agent-callable tool whose first phase renders, so an agent can trigger the render, but only at the **read tier**, because the write tier requires the operator-authored `wavefoundryAllowWriteTools` knob and `wf_upgrade` is itself a write-tier tool and so cannot allowlist itself. Passing the renderer's include-permissions switch through the `wf` dispatcher is an accepted residual outside the threat model, since an agent with unrestricted shell access can write `.claude/settings.json` directly. The knob's home is protected by the **host** (which prompts before an agent edits `.claude/settings.json`) plus prompt policy, not by framework-enforced isolation: the framework's own pre-edit guard on that file is the `framework_edit_allowed` gate, which an agent can open, so writing the knob takes the same capability as writing the rules by hand. If the committed `.claude/settings.json` already carried the wavefoundry allow rules by hand, the render claims nothing, `wavefoundryManagedAllow` stays empty, and those rules get no rename self-heal; the consent output reports them as already present and left unmanaged. To hand them over to the renderer, delete those allow rules and let the next upgrade or `wf setup` re-emit them.

**Upgrade REPORTING no longer waits a cycle (and what still does).** The same old-code window used to apply to the upgrade's own reporting: the primary-phase summary sentinel was built by the pre-extraction orchestrator, so any change to what the upgrade reports shipped one upgrade late and produced false "the fix does not work" field reports. That window is now closed structurally: the parent delegates the primary-phase summary (and the reconciliation scan it embeds) to a subprocess running the freshly extracted tree's `upgrade_wavefoundry.py --emit-summary`, behind a pinned entry-point contract carrying a `summary_schema_version` token (a tripwire against silent drift: deliberate versioned evolution is supported by bumping the token, and old runners then degrade with a marker for one transition run); any delegation failure degrades to the parent's own in-process summary marked with `summary_source_degraded`, never a silent substitution. Three class boundaries matter when reading upgrade output: (a) sentinel-carried summary fields take effect on the upgrade that installs them; (b) behavior-class fixes (what the upgrade DOES mid-run) still need a pack hook bridge, like the permissions backstops above, to act on their installing upgrade; and (c) server-resident response fields (`runner_stale`, diagnostics composition, response bounding) are computed by the running MCP server and still require a full host restart on every release. One residual fires exactly once per target: the upgrade that first installs the delegation is still driven by a pre-delegation parent, so that single transition run reports an old-schema summary. Do not report that one transition run's old-schema summary as the backstop failing to work; every later upgrade reports on fresh code.

**Reading token presence (do this before reporting a missing token).** `summary_schema_version` is NOT delegation-exclusive: the cleanup phase's emit site carries it too, on both the success and the failure branch. Present, it says only that post-extraction framework code rendered THIS summary; it never says which emitter produced it, and it never claims the upgrade succeeded (`failed_phase` is the success discriminator). Absent, it has three distinct causes and a field report must name which one applies instead of reporting a bare "absent":

1. **The in-process degradation fallback produced the summary.** Always accompanied by `summary_source_degraded`, which names the delegation failure class.
2. **The runner predates this contract.** Distinguished by `to_version`.
3. **No summary was emitted at all.** A memory-checkpoint pause and `--resume-after-memory` emit no sentinel in their own process; each reaches a tokened summary at its subsequent recovery `--cleanup`.

"A sentinel was emitted without the token" and "no sentinel was emitted" are different observations with different causes. Report them as different observations; collapsing both into one "absent" reading is the reporting half of the defect this contract exists to remove.

**Versioning contract:** Releases use `MAJOR.MINOR.PATCH` semver. The version appears as `MAJOR.MINOR.PATCH+<build>` in `VERSION` and `framework_revision`, and as `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` in filenames. See `docs/architecture/decisions/12tm5-adr semver-versioning-contract.md` for the version bump policy.

**Distribution directories:** `upgrade_wavefoundry.py` searches the repository root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, and `~/Downloads/`, then picks the highest semver zip. Non-matching filenames are skipped silently.

**Agent-safe zip discovery (use these, not `ls`):** Never use `ls`/`find` to locate or choose the pack. Two reasons it gives the wrong answer: (1) it only sees the directory you point it at — the pack usually lives in `~/.wavefoundry/dist/`, so `ls wavefoundry-*.zip` at the repo root finds nothing and an agent wrongly concludes "already current / nothing to upgrade"; (2) `ls -1 ~/.wavefoundry/dist/` sorts lexicographically and ranks `wavefoundry-1.3.9.*.zip` *above* `wavefoundry-1.3.30.*.zip`, selecting a stale pack. Use the script flags instead — all run the same semver comparator over all five search paths the upgrade itself uses:

- `wf upgrade --detect-zip` — prints the absolute path of the selected pack and exits `0`. Exits `1` with empty output when no matching zip is found.
- `wf upgrade --list-zips` — prints every match across all five search paths, semver-sorted (highest first), with `* ` on the selected pack.
- `wf upgrade --dry-run` — prints the selected pack on a `Zip to apply:` line in the same output that surfaces seed diffs and hook inventory, with zero mutations.

Discovery/preview is **CLI-only**: run the flag via your shell (that is the agent-safe path — not `ls`). The MCP `wf_upgrade` tool *runs* the upgrade — its default `preflight_to_docs_gate` phase adopts the highest pack — and has **no** dry-run or discovery-only phase (its only argument is `phase=`; there is no `mode=`).

**Step 0 (optional zip adoption):** If a `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` is in the repository root, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`, the upgrade seed stages the selected pack under `.wavefoundry/framework/`, runs `wf render-surfaces`, and continues full reconciliation. Non-matching filenames are skipped. Native Windows, WSL2, macOS, and Linux use the same MCP/dispatcher flow with host-appropriate command rendering. The zip root also carries the pack's zipapp installer members (`payload/*`, `__main__.py`, `upgrade_bridge_bootstrap.py`, `subprocess_util.py`) and the single-use bootstrap `install-wavefoundry.md`; the script/MCP path extracts through an allowlist so none of the runner members reach the project root, and removes the bootstrap automatically (the one exception: the upgrade run that first installs the allowlist still extracts with the pre-upgrade code, so the debris lands one final time on that transition run — positively identify it first: untracked, byte-identical to the corresponding zip member, and named in the zip's `payload/*.json` installer manifest or among the fixed zip-root runner names; once every criterion holds, removal is safe. Every later upgrade extracts scoped). If you run a fully-manual unzip, scope it (`unzip -o <zip> '.wavefoundry/*' -d .`) rather than extracting the whole archive — an unscoped `unzip -o` dumps the runner members into the repository root and can overwrite same-named project files — and delete any previously re-dropped bootstrap after pruning (`rm -f install-wavefoundry.md`).

**Full reconciliation:**
1. Inventory current state (seed-030 in targeted mode)
2. Drift-detect against canonical framework (read-only subagents for inventory)
3. Produce a file-level upgrade plan before broad edits
4. Reconcile prompt surface, platform surfaces, `AGENTS.md`, manifests
5. **Agent surfaces and auto-Guru** (when the pack includes `seed-050` / `render_agent_surfaces.py` / Guru) — see below
6. Verify docs gate: **with MCP**, run **`wf_garden_docs`** (when metadata needs refresh) then **`wf_validate_docs`**; **without MCP**, run `./.wavefoundry/bin/wf docs-gardener && ./.wavefoundry/bin/wf docs-lint` on POSIX or `.\\.wavefoundry\\bin\\wf.cmd docs-gardener && .\\.wavefoundry\\bin\\wf.cmd docs-lint` on native Windows

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
   - `.cursor/rules/auto-guru.mdc`, `.claude/agents/guru.md`, `.codex/skills/wf-guru/SKILL.md`
   - Marked blocks in `CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, `WARP.md`, `.github/copilot-instructions.md` when those files exist
5. **Verify** paths listed in `docs/agents/platform-mapping.md` § Auto-Guru routing
6. **Operator follow-up** — Codex: MCP reloads from committed `.codex/config.toml` automatically; Cursor/Claude: attach MCP and restart host; all hosts: restart MCP + project index per checklist below

## Secrets scan and resume

The 1.6 upgrade includes a secrets scan; understand which part blocks and how to recover:

- **Full-tree baseline (automatic, records).** The upgrade's final index phase runs the indexer's secrets scan, which auto-escalates to a **full-tree** scan when `docs/scan-findings.json` is absent (always true on a 1.5→1.6 upgrade) or when the ruleset/scanner version changed. It classifies every finding into `docs/scan-findings.json` up front. This scan **records**, it does not fail the upgrade.
- **Docs gate (incremental, records — does NOT block).** The upgrade docs gate runs an **incremental** secrets scan (changed files) in **record-only** mode (wave 1p5pz): a `pending`/`suspected-secret` finding is recorded to `docs/scan-findings.json` and surfaced as a non-fatal `[secrets]` notice, but it **does not fail the docs gate or halt the upgrade**. (Only a malformed inline-suppression directive is a lint error.) So a found secret never blocks an upgrade.
- **Enforcement is at `wf_close_wave`, not the upgrade.** Unresolved findings (`pending`/`suspected-secret`) **hard-block the next `wf_close_wave`** until classified via the security reviewer (seed-213); `confirmed-secret` is non-blocking + reminded. Classify the baseline + incremental findings before your next wave close — the upgrade itself proceeds regardless.

## Supported version range

- **Floor: 1.4.0.** Upgrading from below 1.4.0 (or from an unparseable version) prints a **warning and proceeds** — migrations for transitions older than 1.4→1.5 have been pruned, so a jump from below the floor may skip an intermediate migration. All known projects are ≥ 1.5.1, so this never fires in practice; it documents the supported range.
- **Multi-version skips are allowed.** Only downgrades are blocked. A single-run skip (e.g. 1.4.x → 1.6) works — the version-gated 1.4→1.5 migrations still fire on the way through. The common path is 1.5.x → 1.6, a single step.

## Config review recommendation (major/minor upgrades)

On a **major or minor** upgrade (e.g. 1.5 → 1.6), the upgrade summary surfaces a one-line recommendation that a **senior / principal architect or engineer** evaluate whether to run the **Framework Config Review** (`docs/prompts/framework-config-review.prompt.md`) — a removal-biased audit of the agent operating surface (AGENTS.md/CLAUDE.md, seeds, prompts, constraints, memory, doc-sync). It is **recommend-only and human-initiated**: it never runs automatically and never blocks the upgrade. Patch upgrades do not surface it. There is no state/threshold — the cadence is simply "evaluate it at each major/minor upgrade."

## Reconciliation scan

The canonical contract for this scan is the **Reconciliation on every upgrade** and **Host permission/allow-rule files** sections above (the scan runs on every upgrade, host permission/allow-rule files ARE inspected, and their hits are partitioned into a self-healing renderer-provenance channel and an operator channel). Read those; there is no separate major/minor-only behavior and no second contract here.

## Verification Checklist

See `docs/contributing/build-and-verification.md` **Wave framework pack upgrade verification** for the ordered operator commands.

1. Framework tests: `python3 .wavefoundry/framework/scripts/run_tests.py`
2. Docs gate: **`wf_garden_docs`** / **`wf_validate_docs`** over MCP when available; otherwise `wf docs-gardener && wf docs-lint`. **Gate-before-reload window:** when MCP is attached but still running the **pre-upgrade** server impl (new code is on disk but the in-process server has not reloaded yet — i.e. before the `wf_reload_mcp()` step), prefer the **`wf` CLI docs gate** here rather than the MCP `wf_validate_docs`/`wf_garden_docs` tools — those would run the stale in-process impl against the new tree. The CLI path is correct in that window, not only a no-MCP fallback; switch back to the MCP tools once the reload lands.
3. Verify host registration and CLI launch paths generated by the current pack:
   - `.cursor/mcp.json` exists and contains `mcpServers.wavefoundry` after `render_platform_surfaces --platform cursor`
   - `.mcp.json` and `.junie/mcp/mcp.json` still include the Wavefoundry stdio entry when those hosts are used
   - `.codex/config.toml` exists at the project root and contains a `[mcp_servers.wavefoundry]` entry using the venv Python launcher
   - The cross-OS `wf` entry point and generated `wf.cmd` shim route the no-PATH forms — POSIX `./.wavefoundry/bin/wf docs-lint` / `./.wavefoundry/bin/wf docs-gardener`, native Windows `.\\.wavefoundry\\bin\\wf.cmd docs-lint` / `.\\.wavefoundry\\bin\\wf.cmd docs-gardener` — to `.wavefoundry/framework/scripts/` via `wf_cli.py`
4. **Check version transitions:** A `CHUNKER_VERSION`/model bump requires a full semantic re-embed; a `GRAPH_BUILDER_VERSION` bump requires a graph re-extract (graph-only — fast). The upgrade's final index phase handles **both** automatically (incremental, or escalating to a rebuild on a version bump), so neither normally needs a manual command. 1.8.1 bumps `GRAPH_BUILDER_VERSION` only (32→35) → the upgrade graph-only re-extracts; no re-embed. Run `index_health()` to verify — a `chunker_version_mismatch` advisory flags a still-needed semantic rebuild; `graph.<layer>.last_built_at` shows graph freshness. When a manual re-embed IS needed, rebuild with the default foreground docs+code setup path:
   ```bash
   wf setup --full
   ```
   If setup fails because a required model download is blocked by missing network access, ask the operator for permission to rerun the same canonical setup command with network access or host escalation enabled. If that cannot complete, manually obtain the exact `wavefoundry-models-<set>.zip` asset from the same release (or an approved internal distribution), leave it zipped, place it in the target repository root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`, then rerun the same `wf setup --full` command. Setup validates the set, hashes, and licenses before replacing the cache; an invalid archive leaves a verified cache unchanged.
   See `docs/contributing/build-and-verification.md` **Upgrade rebuild requirement** for time estimates (~6 min total).
5. Validate upgrade-recovery tools from the upgraded MCP server:
   - `wf_audit` returns a combined `wave` + `validation` + `index` payload
   - `wf_server_info` returns the current `repo_root` and implementation version info for the attached MCP server, including `runner_stale`: `false` confirms the captured runner identity matches disk; `true` means the un-reloadable runner files (`server.py`, `venv_bootstrap.py`) changed on disk since this process launched, and only a full host restart (quit and relaunch) loads them; an in-process reload cannot. `null` means the comparison is unavailable, so report runner freshness as **unknown**, not as proof a restart is unnecessary. Check it after every upgrade.
   - `index_build` is available for deterministic project index rebuilds
6. **Reload MCP, then re-index after the editing pass:** Reload the upgraded server in-process with `wf_reload_mcp()` (or `wf_upgrade` cleanup) so the new server code and rendered host config take effect — a full host restart is only needed for hosts that cannot hot-reload, on a cutover-active 1.15 run (the upgrade response then suppresses the reload and instructs the full restart; see How Framework Updates Work above), or when the upgrade changed the un-reloadable runner files themselves: check `wf_server_info()` after the upgrade and treat `runner_stale: true` as the full-restart signal (the on-disk `server.py`/`venv_bootstrap.py` no longer match the running process, and an in-process reload cannot load them). Treat `runner_stale: null` as **unknown**, not as confirmation that the runner is current; only a full host restart guarantees runner-file changes are loaded in that case. The upgrade already ran an index update as its final phase; you only need a manual re-index **after** the agent editing pass changed docs:
   ```
   index_build(content="docs", mode="update")                          ← project
   ```
   Use `mode="rebuild"` after a version transition (moving to 1.6 bumps `CHUNKER_VERSION` and `GRAPH_BUILDER_VERSION` — see step 4). There is a single project index (the framework's seeds fold into it) — no separate framework index to rebuild. See `docs/contributing/build-and-verification.md` **Upgrade index rule**.
   - If the refresh is detached or backgrounded, poll `index_build_status(layer?)` until it finishes before you rely on the refreshed search state.
   - Treat the reload + post-edit re-index as part of the upgrade, not optional cleanup. Until the reload happens, the repository may still be running old MCP code or stale search state. **After a `GRAPH_BUILDER_VERSION` bump this is not optional:** issuing any graph query (`code_callhierarchy`, `code_impact`, `wf_graph_report`, …) before the reload makes the stale server re-extract the graph DOWN to its old builder version — reload first, then query.
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

## Historical-Memory Gate

Established projects first run one canonical bounded historical extraction
batch after the docs gate. When its run-wide total contains no candidates,
failures, or remaining waves, upgrade advances to Phase 4 automatically; an
empty candidate page before extraction is not treated as proof of no work.
A real candidate, failure, or remaining bounded batch pauses before Phase 4
with lifecycle state `awaiting_memory_validation` (CLI exit 4: action required,
not failure or completion). Reload the newly installed MCP, repeatedly call
`memory_backfill(mode="create", entry_path="upgrade")`, validate every
exact `data.validation_worklist[].memory_id`, then call backfill again until
the run is clear and call
`wf_upgrade(phase="resume_after_memory")`. The resume recomputes the
authoritative `memory-state.sqlite` pending set and alone publishes the index.
Resume-after-memory, index, and cleanup verbs all refuse while the
retired-sidecar cleanup or docs lint has a retained failed phase; recover a
docs-gate failure through `resume_after_gate`, and recover a
`review_sidecar_cleanup` refusal by stopping every attached host and
re-running the full upgrade. After lint passes, `resume_after_gate` establishes
or refreshes the memory checkpoint and may return its action-required worklist;
continue through `resume_after_memory`, not `update_index`. Index and cleanup also refuse while memory
work remains. Fresh/no-history projects continue directly. Upgrade/status responses expose the run id, outcome/pending
counts, last failure, and next bounded worklist; do not scrape output or use a
global candidate search. The no-MCP `wf memory-validate` fallback has full
rewrite-field parity.

When candidates are already validated and ready for receipt-owned publication,
the action-required checkpoint is `awaiting_memory_publication`: reload or
reconnect, then call `wf_upgrade(phase="resume_after_memory")`; do not repeat
backfill. This is not an `index_update` failure. The first response from an
older MCP server can retain its validation-oriented structured label until the
reload, but its exit 4 and captured publication guidance remain action-required.

When the upgrade was started by a pre-gate MCP process, the newly extracted
pre-docs extension executes the one-way retired-sidecar cleanup before lint;
upgrade does not enumerate, reproject, or rewrite historical waves, and every
existing `wave.md` and `events.jsonl` is left byte-for-byte untouched. A
refused cleanup (a shipped publication-lock path is held) leaves
`failed_phase=review_sidecar_cleanup`: stop the dashboard and every attached
MCP/agent host, then re-run the full upgrade. A lint repair leaves
`failed_phase=docs_gate`; after the repair, `wf upgrade --resume-after-gate`
or `wf_upgrade(phase="resume_after_gate")` reruns only the docs gate against
the already-extracted tree, then establishes or refreshes the memory
checkpoint. If it returns memory action-required, inspect the worklist and
continue through `resume_after_memory`. A cutover-active run (the run removed a retired
sidecar or the stale root lock, or the installed version predates 1.15, with
unknown treated fail-safe as pre-1.15) requires a full restart of every
attached host, including the invoking one, before lifecycle mutation resumes;
on such a run the upgrade suppresses its automatic in-process reload and
removes `wf_reload_mcp` from the suggested next tools, because an in-process
reload alone is not sufficient. The suppression executes in the invoking
host's already-loaded server code, so it is guaranteed only when that host
already runs 1.15-or-later code; an upgrade invoked from a pre-1.15 host may
still fire its old unconditional in-process reload, which loads the new
module but does not substitute for the full restart; the full-restart
instruction, delivered in the upgrade summary, stands either way. Non-cutover
runs keep the normal reload flow
and report no cutover restart requirement. A later
historical-memory exit 4 is action-required, not an index failure:
reload/restart MCP, inspect the structured run worklist, then resume through
`resume_after_memory`. New-code resume-after-memory, update, rebuild, and
cleanup all refuse a retained sidecar-cleanup/docs failure until the matching
recovery succeeds. Update, rebuild, and cleanup also run the publication
backstop, so an old-shaped retained lock cannot publish or clean up around
the cutover.

<!-- wavefoundry:review-policy-upgrade:begin -->
## Versioned review-policy and bridge recovery

Upgrade maps legacy review enablement to the current default: enabled projects become
`enabled=true, delivery_mode=targeted`; disabled projects become
`enabled=false, delivery_mode=disabled`. The structured upgrade result reports the
selected delivery mode. Every non-closed declared wave is marked for re-Prepare when
the migration changes the policy (a no-op migration marks nothing); closed wave
Markdown and ledgers remain immutable. After the upgrade reload—or a
restart when `runner_stale` or cutover requires one—check from a fresh turn. If the
catalog remains stale, reconnect MCP, then restart as the final fallback. Once current,
use `wf_list_waves` for compact wave metrics and `memory_brief` for the active-memory
budget and any consolidation candidates. If `memory_brief` reports
`curation_required=true` or returns consolidation candidates, recommend the public
**Review memories** shortcut (alias **Memory review**); Upgrade never auto-curates or
purges memory.

Every upgrade also reconciles shortcut discovery merge-safely: ensure the canonical
**Review memories** entry exists in `AGENTS.md` and `docs/prompts/index.md`, and ensure
`docs/prompts/prompt-surface-manifest.json` contains exactly the canonical shortcut
`Review memories` for `docs/prompts/memory-review.prompt.md` (the alias stays in the
human-readable surfaces). Preserve project-authored additions and prose outside the
framework-owned regions; never replace an entire discovery surface to add this entry. While
`.wavefoundry/upgrade-in-progress.json` exists, lifecycle, review-evidence,
context-efficiency, memory, docs, and index publication is blocked except the named
memory-recovery phase.

Feature packs carry integer `upgrade_protocol_version` and
`minimum_runner_protocol`. `upgrade_protocol_invalid` means the pack is missing,
malformed, import-incomplete, or incompatible and is refused before extraction.
`bridge_release_required` means the installed protocol-1 runner must not extract the
feature. Use the same single matching `wavefoundry-<version>.zip` release package.
The agent stops the dashboard, disconnects/stops every Wavefoundry MCP server for
the repository, and leaves the current host session idle; it then runs the exact
`command_argv` through its ordinary non-MCP shell. No operator-entered terminal
command is required. The package records that confirmation, verifies both embedded
archives, swaps only
`.wavefoundry/framework/`, and immediately executes the hash-bound feature hop.
Fully restart every attached host and follow the package's structured recovery result;
retry or resume any retained failed phase until the checkpoint reaches terminal cleanup.
An already-loaded protocol-1 MCP wrapper predates the current response cap and cannot
be changed by the incoming pack. Its compact bridge JSON is emitted last; if the host
rejects or truncates that one legacy response, the agent uses its ordinary shell to
detect and execute the single installed package after Wavefoundry services stop. The
operator still does not copy or type a terminal command.
<!-- wavefoundry:review-policy-upgrade:end -->
