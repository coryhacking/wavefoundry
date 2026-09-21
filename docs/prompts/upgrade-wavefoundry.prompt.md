# Upgrade Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-09-21

Shortcut: **`Upgrade Wavefoundry`** | Legacy: **`Upgrade wave framework`** / **`Upgrade wave context`**

**Check first when unsure:** `wf setup --check` (optionally `--root PATH --json`)
reports `ready` (exit 0), `action_required` (exit 1), or `indeterminate` (exit 2).
Follow the reported action: plain setup for local preparation, a host restart for
stale loaded code, or the retained owning command for pending recovery. Do not
substitute setup for a pending upgrade continuation. The check installs nothing,
downloads no models and does not repair or rebuild indexes. It is read-only for
application data; SQLite may create or update normal WAL/SHM coordination files.
It is a bounded readiness check, not a complete integrity, freshness or search-quality audit.

## Setup after a clone or pull

`wf upgrade` installs a framework release; `wf setup` makes the framework
currently checked out usable on this machine. After pulling a teammate's
committed upgrade, run `wf setup`. It selects no archive and preserves project
customizations. Missing indexes build, compatible indexes update, and supported
obsolete storage uses the existing staged migration and verified cleanup.

A pending archive-owned upgrade cannot be adopted by setup: keep its original
archive and exact continuation. A setup-owned handoff retains the installed
framework fingerprint and supplies a setup command with explicit host-stop
confirmation. Stop the repository's hosts and run it from an external terminal.
If the installed source changes during recovery, restore the recorded framework
before retrying; never edit receipts or delete the only index copy. Unknown or
newer storage and ambiguous ownership remain preserved with a refusal.

Setup may report core search ready while historical memory validation is pending.
Complete the run-scoped memory work and rerun setup to finish adoption; core
publication never marks unvalidated memories as validated. Reconcile this section
into customized project setup/upgrade prompts during the ordinary upgrade editing
pass, preserving local additions and renderer-owned regions.

## Index writer compatibility and first protected upgrade

Protected index writers check persisted ordered revisions and their loaded producer
source contract before preparation and inside publication. A newer revision,
malformed or unproven populated identity, or changed installed producer contract
refuses with `index_version_newer`, `index_compatibility_unproven`, or
`index_runtime_stale`. Preserve the index; reload/restart the affected host and
resume the ordinary setup, upgrade or index command. Do not delete metadata,
force an older rebuild, or repeatedly retry through the same stale process.
Equal revisions retain incremental updates; a current runtime can rebuild older
supported revisions and apply supported model changes. Model names, tokenizer
identities and source hashes are compatibility identities, not ordered versions.

The first protected upgrade cannot retrofit checks into already-loaded older
hosts. It therefore retains `index_guard_handoff` in the ordinary upgrade
checkpoint and pauses with `index_guard_restart_required` before publication,
including same-schema upgrades. Capture the response's exact `command_argv`,
stop this repository's Wavefoundry MCP/dashboard hosts (including the invoking
host), then run that command through the ordinary non-MCP shell in a fresh CLI
process. It retains the selected `--pack` and `--confirm-hosts-stopped`; the
checkpoint verifies the package's SHA-256 identity on resume. Keep the checkpoint
and original archive; do not substitute a newer package or edit recovery data.
Confirmation asserts that undiscovered hosts have also stopped: discovery is
best effort, and positively identified live hosts still block. No unrelated
repository host is stopped automatically. Reconnect MCP only when CLI recovery
permits it. Fresh installs with no former runtime are exempt.

A validated pause returns outer `status: "action_required"`, without a true
`isError`, and `failed_phase: null`. This also covers the pre-guard ppjy MCP
wrapper when it first loads the incoming restart-action reader after extraction.
A host that already cached an older reader may still label the outer response
an error. In that case, follow the validated `index_guard_restart_required`
checkpoint and its exact captured CLI command; an exit code alone is not proof
of an expected pause. The presentation fix does not remove the host-stop or
confirmation requirement and does not create a storage-migration receipt.

This checkpoint records the pre-extraction capability and survives extraction
and retries. It is independent of `sqlite-migration.json`: same-schema handoff
creates no fictitious storage conversion, while actual format migrations retain
their existing receipt and forward-only recovery. The handoff is rechecked
before index children run; a post-upgrade reload alone is insufficient for this
first protected release.

## Local semantic storage conversion (wave 1xjmm)

Continue through standard `wf_upgrade`; no bridge release or externally staged
replacement runner is required for any of these storage changes. Fresh installs
use one `.wavefoundry/index/index.sqlite` database for docs/code vectors,
canonical chunk text, FTS, indexing state, the code graph with its extraction
and merge state, communities and the codebase-map receipt. The memory store
stays separate.

Any storage conversion of an existing framework may return
`storage_restart_required` after extraction and before any format change. This
also covers metadata-only installations and an existing framework that has never
built an index: its old host could still create the previous format. A fresh
installation with no previous framework does not need this upgrade pause.
This is an expected checkpoint, not an upgrade failure: framework files may
already be extracted, but storage conversion has not occurred.
An already-running older MCP wrapper may still label its outer response an
error; use the explicit `storage_restart_required` action and retained checkpoint
to identify this pause. Other exit-3 failures are not restart checkpoints.

Before stopping MCP, retain the response's exact `command_argv` and its
shell-labelled command. Stop every repository-associated Wavefoundry dashboard
and MCP server, including the invoking server and servers attached to other
editors. The response lists observable hosts with PID, kind and repository
association; discovery is best-effort, so an empty list does not prove that all
hosts stopped. Restarting only the current editor is insufficient when another
host still owns the repository's index.

Continue through the ordinary non-MCP shell using that exact installed CLI
command. It preserves the repository and selected pack and includes
`--confirm-hosts-stopped`; do not launch another MCP server to submit the
confirmation. The confirmation explicitly asserts that hosts stopped and does
not replace stopping them. Identified live hosts and held locks still block
conversion. Restart/reconnect MCP only after the CLI's recovery instructions
permit it. A native SQLite binding change requires a new process; in-process
reload alone cannot complete this boundary.

The package path is a locator, not its identity: resume verifies the recorded
SHA-256 and exact target version against the private copy it consumes. Keep the
original archive until completion. If the recorded temporary path disappears,
use `--pack` with a byte-identical copy of that archive; do not substitute a newer
build or edit `pack_path` in the receipt. A changed digest remains a refusal.
If an affected older build rejects identical bytes with `storage_pack_changed`,
retain all recovery files and use a verified, build-specific installed-code
repair before retrying that same archive. A newer target cannot take over an
unfinished upgrade. Existing project-root `install-wavefoundry.md` files must
remain untouched, whether tracked or untracked.

Preserve `.wavefoundry/index/sqlite-migration.json` and its named staging and
rollback artifacts on any pause/failure. They bind recovery to the project and
exact source/target; do not delete the receipt, clear the checkpoint, or switch
packs to force success. Compatible vectors transfer without re-embedding;
normal filesystem and model/chunker checks still reconcile changed inputs.
Schema/runtime, source identity, disk-space or integrity refusals require the
reported correction before standard upgrade can continue. Never treat a copied
file or successful extraction as completed publication.

Known shipped shared-store schemas 4, 5 and 6 convert only on the unpublished
staging copy; existing auxiliary rows remain intact while missing tables are
added. Unknown formats remain refused. The legacy migration warning floor is
1.4.0; the existing protocol-1 package transition still requires at least 1.8.0.
This storage change does not bypass that protocol boundary.

**Unified index database.** A later conversion renames the shared database to
`.wavefoundry/index/index.sqlite` and folds the code graph into it, so one file
holds every semantic and graph row and one transaction publishes them together.
It is recorded in the same `sqlite-migration.json` receipt as a versioned kind,
and requires an upgrade coordinator that declares storage migration protocol 2
or newer; an older coordinator receives the ordinary restart handoff and the
installed CLI resumes it. No bridge release is required. A framework old enough
to predate the receipt version refuses to open the repository at all rather
than creating a second database beside the new one, so stop every
database-owning host when the upgrade asks.

This conversion preserves existing embeddings -- compatible vectors, canonical
chunks and FTS transfer without re-embedding -- and rebuilds the graph from the
current project sources rather than converting old graph files, so a missing,
stale or corrupt graph does not block it. Expect the rebuild to dominate the
elapsed time on a large repository. The old `index-state.sqlite`, the retired
`.wavefoundry/index/graph/` directory and the standalone codebase-map
fingerprint are removed only after a fresh process verifies the published
database, and only when a pre-deletion inventory finds nothing unrecognized in
that directory; anything unexpected preserves the whole folder and reports it.

Recovery from a failed or refused cutover is FORWARD: re-run the standard
upgrade from the retained source and the recorded recovery identities. There is
no backward rollback to the previous runner, and the retained rollback copy is
never read back into service. Never delete the receipt or the retained source
to force progress.

When historical memory backfill overlaps this conversion, the unpublished
graph candidate completes independently of the live memory run. Only ordinary
live index publication may advance that run. Continue through the standard
upgrade flow and its retained CLI command after any required host-stop
checkpoint. Never copy the memory database into staging, edit recovery
receipts, or substitute a different package while a receipt is pending.

**Audit the documented state-store schema version.** The ordinary upgrade
snapshots supported docs-constants claims before extraction and reconciles exact,
unchanged claims against newly installed constants before its docs gate. Verify
the `state-store schema version` claim in `docs/RELIABILITY.md` during the editing
pass. If a customized claim or unavailable snapshot leaves a mismatch, correct
the named claim from the installed code at the reported docs-gate stop, then
resume the ordinary upgrade. There is no separate manual editing checkpoint
before the first gate. Repositories without that document need no edit; an
existing document with a missing required claim must be corrected.

**Rebuild legacy semantic storage from current sources.** If faithful transfer
refuses historical duplicate or missing chunk IDs, or legacy vectors cannot be
read, explicitly add `--rebuild-storage` to the retained ordinary CLI continuation
with the original `--pack` and `--confirm-hosts-stopped`. Before the first restart
pause, MCP can select `wf_upgrade(rebuild_storage=true)`; after that pause use the
external CLI, without reconnecting MCP. Do not combine the selection flag with a
standalone index/cleanup/memory phase. The receipt retains this choice for later
phases and retries, so it need not be repeated.

Rebuild uses the current filesystem, walker and chunker instead of transferring
legacy vectors. It requires available source files, readable walks, models,
native storage and sufficient disk/capacity. Original source identities and
fingerprints, package/target checks, host quiescence and structural SQLite checks
still apply. Historical duplicate IDs are not silently deduplicated. The current
chunker regenerates unique IDs; auxiliary SQLite rows, the graph tables in the
same database and the separate memory store are preserved. Both semantic layers must complete a full rebuild with
source-derived proof bound to final publication before new-process verification
can authorize cleanup. Empty consistent tables or successful child exits alone
are insufficient. Failures retain original stores and rollback data for retry.

Select this strategy while the receipt is `restart_required` or `quiesced`,
including after a failed transfer. Later receipt states refuse a strategy change. `wf setup --full` still cannot bypass a pending receipt.
An already-paused older build that lacks this option needs a verified,
build-specific installed-code repair followed by its original archive; a newer
package cannot take over its receipt. Never edit or delete the live receipt,
checkpoint or only copy of data. If source files, auxiliary storage, ownership
or a compatible runtime cannot be verified, leave the migration paused and
resolve that refusal before retrying.

Cleanup runs through `wf_upgrade(phase='cleanup')` only after a new process has
verified the published SQLite generation. It removes the proven project-owned
`docs.lance/`, `code.lance/` and `__manifest/` under `.wavefoundry/index/`, plus
recorded obsolete staging/rollback files. Review reclaimed and retained bytes
and reasons; failed removals remain pending. Shared or user-managed dependencies
remain installed when their exclusive ownership/use cannot be proven. Ordinary
SQLite queries and refreshes must not recreate Lance stores or install LanceDB.

Before cleanup, follow the retained migration's verified retry/recovery path.
After cleanup, downgrading requires reinstalling a compatible older framework
and rebuilding its derived index from current project sources; the new SQLite
format must never be opened by an old runner. Do not remove the entire index
tree or unrelated graph, memory and model caches.

## Purpose

Upgrade the Wave Framework operating surface in a target repository. Reconciles the rendered local docs, prompt surface, platform hook/config surfaces, the repo-local Codex bootstrap launcher, and `AGENTS.md` with the current canonical framework source.

**Standard upgrade path and first-hop retry protection:**

Use the normal MCP-first `wf_upgrade()` flow, including index update and cleanup, when MCP is attached; use the documented installed CLI fallback only when MCP is unavailable. Upgrading from an older protocol-2 runner does not require inspecting it for `_save_old_manifest_snapshot` or staging a newer runner outside the destination.

The first upgrade into 1.22.0 runs with the installed older runner, so it does not gain the new original-manifest snapshot protection merely by extracting the new files. If that first attempt is interrupted after replacing the MANIFEST, a retry may lack the original authority needed to remove retired framework files. This first-hop risk is accepted in favor of retaining the standard upgrade path. Subsequent upgrades launched with the fixed installed runner preserve the original manifest for retry-safe pruning.

When `.wavefoundry/upgrade-manifest-old.json` exists, preserve it and retry the same target pack. Do not delete it or switch targets to bypass a pending-recovery refusal; only observed successful pruning retires it. A snapshot cannot reconstruct authority already lost by an earlier unfixed attempt; do not guess retired paths in that case. Existing preflight, permission, host-quiescence, reconciliation, memory, index, cleanup, and protocol-1 bridge requirements remain unchanged.

## How Framework Updates Work

Use this prompt when the repository is already seeded and you want it to adopt a newer Wavefoundry framework pack or reconcile against a newer local `.wavefoundry/framework/` tree.

The expected operator flow is:

1. Put the new framework in reach of this repository.
   - Usually this means building or placing `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` in the repository root, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`. For offline model setup, place the feature ZIP and the model-set asset it declares (`wavefoundry-models-2.zip` for Wavefoundry 1.16.0 through 1.17.0; `wavefoundry-models-3.zip` after, same weights and embedding identity, one reference file corrected) in any of those standard distribution directories. Discovery ignores model assets as framework packs, selects the exact declared model-set version, and setup verifies its component hashes and licenses before indexing.
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
   - **Index writer compatibility:** protected runtimes refuse stale writes with restart guidance and preserve newer graph, semantic, lexical and chunker/walker state. The first upgrade from an unprotected host requires the confirmed fresh-CLI handoff above before publication, even when the schema is unchanged; reloading afterward cannot retroactively protect it.

What this prompt is not:

- It is **not** packaging. Packaging creates a new zip in the framework source repo.
- It is **not** init. Use init only for first-time seeding or legacy routing cases.
- It is **not** a manual unzip checklist. Root zip adoption is built into the upgrade flow.

**Supported operator environments:** native Windows, WSL2, macOS, and Linux are first-class. Prefer the MCP path or the cross-platform `wf` / `wf.cmd` dispatcher for the host; structured argv is authoritative and display commands are rendered for the detected platform.

**Wavefoundry tooling Python runtime:** this policy applies to Wavefoundry’s CLI, MCP server and indexing tools. It does not change the host project’s application language or runtime requirements (for example, Java and its JDK). Python 3.13 or newer is recommended. Python 3.11 and 3.12 are deprecated but remain allowed; the minimum is still 3.11. No removal release is scheduled. Dependencies must support the selected interpreter; this recommendation does not qualify every future Python release. Follow `.wavefoundry/framework/README.md` **Python runtime advisory and transition** when deliberately changing interpreters: select PATH `python3` for setup and the restarted host, stop shared-environment consumers or propagate an isolated `WAVEFOUNDRY_TOOL_VENV`, and retain existing recovery ownership. The advisory never performs that transition automatically.

**Python requirement:** Python 3.11 or later is required. Framework dependencies are installed into a shared tool environment at `~/.wavefoundry/venv` (or `$WAVEFOUNDRY_TOOL_VENV` to override); `wf setup` is the operator command to create/populate it and run the index setup flow when the dispatcher is on PATH. If `wf` is not on PATH, use the setup step documented in the install prompt. If the setup step fails specifically because a required model cannot be downloaded, keep recovery on the canonical setup path: in agent-driven sessions, first ask the operator for permission to rerun the same setup command with network access or host escalation enabled. If that cannot complete, manually obtain the exact `wavefoundry-models-<set>.zip` asset from the same release (or an approved internal distribution), leave it zipped, place it in the target repository root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`, and rerun `wf setup`. It verifies the set, hashes, and licenses before replacing the cache; an invalid archive leaves a verified cache unchanged.

## Upgrade Steps

**MCP-first (do this when the Wavefoundry MCP is attached).** Drive the upgrade with the **`wf_upgrade()`** tool — it runs the phases for you (pre-flight → adopt the highest pack → extract → render surfaces → prune pack-removed files → docs gate), then `wf_upgrade(phase="update_index")` / `wf_upgrade(phase="cleanup")`. Poll/inspect the lock state with **`wf_upgrade_status()`** between phases and **before any reload/restart**. This mirrors the "prefer MCP over shell launchers" parity used for docs validation: the tool does the mechanical reconciliation (prune the retired files, re-render to `bin/wf`, re-heal the `python3` command) automatically — going manual and skipping those phases is exactly what leaves stale surfaces behind. **The steps below are the no-MCP CLI fallback (`./.wavefoundry/bin/wf upgrade` on POSIX, `.\.wavefoundry\bin\wf.cmd upgrade` on native Windows)** — follow them only when no MCP host is attached; they are not the default path. **Read the response's `data.summary` block** for computed fields — `from_version`/`to_version`, `pruned_count`, `docs_gate`, `index_update`, `failed_phase`, `is_major_or_minor`, and the `reconciliation` findings list — plus the top-level `next_step`; do not regex-scrape the raw `output` for these. **Phase semantics (wave 1p8kz):** the PRIMARY/default call — `wf_upgrade()` (phase `preflight_to_docs_gate`) — already returns `data.summary`, **including the `reconciliation` findings**. The reconciliation scan + `summary.reconciliation` run on **every upgrade** — any version delta, including a patch bump (e.g. 1.9.4→1.9.5) and a same-version build-successor (a rebuilt pack at the same semver during testing) — because a patch or build-successor can change or RETIRE a surface too; `is_major_or_minor` is an **informational** field only and no longer gates the scan. Read `data.summary` directly from that primary response — you do **not** have to wait for the `cleanup` phase. The `wf_upgrade(phase="cleanup")` call additionally prints the full human-readable operator summary prose (and reloads the server on non-cutover runs; on a cutover-active run the reload is suppressed and the response instructs a full host restart instead); both emissions are rendered from one builder, so their structured fields agree except on two provenance keys: the cleanup emission always carries `summary_schema_version`, which the primary emission carries only when its summary came from the delegated producer, and a degraded primary additionally carries `summary_source_degraded`, which a cleanup emission never carries. See **Reading token presence** below before reporting a missing token.

**Reconciliation on every upgrade (the upgrade runs a scan; you act on it).** On **every upgrade** — any version delta, including a patch bump and a same-version build-successor, since a patch can change/retire a surface during testing (`is_major_or_minor` is informational, not a gate) — after the mechanical phases complete the upgrade **runs the retired-surface reconciliation scan** (`reconcile_scan.py`, shipped under `.wavefoundry/framework/scripts/`) over THIS repo and surfaces an actionable `file:line → suggested wf form` list in the operator summary (`wf_upgrade`'s `summary.reconciliation` field; the human prose lists the same). The scan flags docs/prompts/configs/scripts that named a framework surface the bump **changed or RETIRED** — e.g. the 1.9.0 cutover retired the `.wavefoundry/bin/*` wrappers in favor of the cross-OS `wf` dispatcher, so a local doc still naming `.wavefoundry/bin/<wrapper>` is now a broken instruction. The scan consumes the single retired→new map co-located with `_RETIRED_BIN_WRAPPERS` in `render_platform_surfaces.py`: renames map 1:1 to `wf <subcommand>` (e.g. `docs-lint`→`wf docs-lint`, `wave-gate`→`wf gate`, `wave-dashboard`→`wf dashboard`), and `mcp-server` has **no** `wf` form — remove/rewrite it (the MCP server launches via `python3 .wavefoundry/framework/scripts/server.py`). The scan is **report-only** (it never auto-edits repo docs): repair each live instruction, then re-run the drift detection in the Verification Checklist. When a finding is truthful historical narrative rather than a live instruction, verify its exact line and heading context, then record the printed `v2:` `disposition_key` once with status `historical-record` in `docs/reconcile-dispositions.json`; the complete audit scan still retains it while the reported reconciliation channel suppresses only that unique v2 finding. Existing 16-hex legacy entries remain byte-preserved but never suppress: zero candidates are dormant, one candidate reports `legacy-reclassification-required` with its proposed v2 key, and multiple candidates report `legacy-ambiguous`. Duplicate v2 fingerprints report `v2-ambiguous`; malformed and unknown-version keys also fail open. Never auto-rewrite the operator-owned store. A project-specific agents-layer prompt finding is never auto-renamed: follow its suggestion to merge unique project guidance into `docs/prompts/review-plan.prompt.md`, remove the obsolete agents prompt, and rerun the scan. The scan's baked-in exclusion set never flags the framework pack tree, the generated index, `docs/waves/`, `docs/reports/`, `CHANGELOG.md`, journals/snapshots, or test files.

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

**Step 0 (optional zip adoption):** The ordinary upgrade selects a matching package from the supported discovery paths, extracts framework members and continues full reconciliation. Native Windows, WSL2, macOS and Linux use the same MCP/dispatcher flow. The package retains `install-wavefoundry.md` for fresh installs; upgrades exclude it before extraction, including the installing hop under a supported older runner. Zipapp runner members also stay out of the project root. For fully manual unpack, scope extraction: `unzip -o <zip> '.wavefoundry/*' -d .`. Existing root installers and older leftovers remain untouched. Do not infer ownership from the filename, matching bytes or untracked status; removal requires provenance review and operator authorization.

**Tracked runtime files:** Surface rendering refreshes the managed `.gitignore` block and warns about tracked guards, locks, logs, indexes, recovery assets and package archives matching its rules. Ignore rules do not untrack files. Review each reported path; with operator authorization, `git rm --cached -- <path>` stops tracking while retaining the local file. Do not automatically untrack files or alter guards. An unavailable inspection is not a clean result: resolve Git access and rerun `wf render-surfaces`. During upgrades, reconcile this guidance and the installer preservation rule into customized prompts outside renderer-owned marker regions.

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
   - `.cursor/rules/auto-guru.mdc`, `.codex/skills/wf-guru/SKILL.md`; `.claude/agents/guru.md` has a generated body with existing operator frontmatter preserved
   - Marked blocks in `CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, `WARP.md`, `.github/copilot-instructions.md` when those files exist
5. **Verify** paths listed in `docs/agents/platform-mapping.md` § Auto-Guru routing, and, when a skill host root exists (`.claude/`, `.codex/`, `.agents/`), that `platform-mapping.md` § Skills lists the rendered skill set as found on disk (host skill directories, rendered skills, gating rules; seed-050 specifies the section, seed-100 points `docs/prompts/index.md` at it)
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

- **Backstage/TechDocs baseline (wave 1vj4e).** The upgrade does **not** generate `catalog-info.yaml`, `mkdocs.yml`, or `docs/index.md` and never rewrites them: nothing about them runs in the pipeline, in `wf render-surfaces`, or in setup. Point operators at **Refresh TechDocs** (`docs/prompts/refresh-techdocs.prompt.md`; alias **Author TechDocs**; the doc-gated `wf-techdocs` skill), which runs the baseline (`wf_techdocs_baseline` over MCP, the CLI dispatcher `./.wavefoundry/bin/wf techdocs-baseline` as the fallback) missing-only and is safe to rerun: existing files are preserved byte-for-byte, each generated file carries a one-line generated-by stamp (not a review-protocol marker; nothing to repair or re-render), the command runs only when `docs/references/project-overview.md`, `docs/ARCHITECTURE.md`, and `docs/prompts/index.md` exist, and when the trio is mixed (some files generated, some project-owned) it prints one `techdocs-baseline: WARNING` naming the project-owned files (the `--json` envelope carries the same `partial` record) without claiming the mixed result is a validated site. Make **Refresh TechDocs** discoverable in `AGENTS.md`, `docs/prompts/index.md`, and the manifest like **Review memories** above. On the upgrade that first ships seed `178`, backfill `docs/prompts/refresh-techdocs.prompt.md` per `seed-100` and then run `wf render-surfaces` **again**, because the render passes at steps 2 and 4 of the agent procedure below ran before that prompt existed and the doc-gated `wf-techdocs` skill renders only once it does. After an upgrade, `wf_techdocs_audit` (CLI dispatcher `./.wavefoundry/bin/wf techdocs-audit`, native Windows `.\.wavefoundry\bin\wf.cmd techdocs-audit`) is the safe read-only check: it reports the publication boundary, the nav targets, links that escape that boundary and the audience invariant, and writes nothing. A new MCP tool appears to a host only after a reconnect, so use the CLI until then (wave 1vqqi).
- **Storage recovery guidance in existing upgrade prompts (seed 160).** On every upgrade, including same-version retries, compare the existing `docs/prompts/upgrade-wavefoundry.prompt.md` with freshly extracted `160-upgrade-wavefoundry.prompt.md` § Local semantic storage conversion, even when the pre-apply diff reports no seed change. Retain the read-only pre-apply seed diff as context, but check the destination itself for previously missed guidance. During the agent editing pass, reconcile during the same installing run: restart checkpoint and retained CLI continuation; `--rebuild-storage` and its MCP-before-pause/CLI-after-pause boundary; package identity and receipt prohibitions; publication/verification gate before cleanup; and the unified index database contract (one `index.sqlite`, the versioned receipt and its protocol floor, the source graph rebuild, inventory-gated cleanup and forward-only recovery). Preserve project-only additions, metadata and all renderer-owned marker regions; merge only missing or stale storage guidance outside those regions, and never replace the project-owned prompt as a whole. If no prior storage section exists, add a single section at an unambiguous location; already-current guidance remains unchanged. If the old clause or insertion location cannot be identified uniquely, or local wording conflicts with the new contract, stop and present the conflict to the operator rather than guessing or overwriting it. Re-run `wf render-surfaces` and the docs gate after the merge; rendering alone does not reconcile project-authored prose.
- **Changed Refresh TechDocs instructions (seed 178).** Keep the read-only pre-apply seed diff through the installing run. If it reports `178-refresh-techdocs.prompt.md` changed, merge the changed canonical clauses into the existing `docs/prompts/refresh-techdocs.prompt.md` during the same installing run, after extraction makes the new seed available. Preserve project-only additions and metadata; never replace the project-owned prompt as a whole. If the prior canonical clause cannot be identified uniquely, or local wording conflicts with the new invariant, stop and present the conflict to the operator instead of guessing or overwriting it. After the merge, run `wf render-surfaces` again so doc-gated skills and other generated agent surfaces see the reconciled prompt.
- **Changed briefing-loop carriers.** Retain the read-only pre-apply change evidence for the seeds and install baseline through the installing run. After extraction, reconcile each changed source into its destination during the same installing run:
   - `170-plan-feature.prompt.md` -> `docs/prompts/plan-feature.prompt.md`: Brief before drafting.
   - `175-review-plan.prompt.md` -> `docs/prompts/review-plan.prompt.md`: Compare the draft with its brief, including permission to consult Rationale as reference.
   - `180-implement-feature.prompt.md` -> `docs/prompts/implement-feature.prompt.md`: Readback before editing.
   - `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md` -> `docs/prompts/implement-wave.prompt.md`: Readback before editing.
   Merge only changed authored clauses, preserving project additions, metadata, and every renderer-owned marker region. For newly added guidance, verify a unique insertion location and absence of conflicting local instructions. If the old clause or insertion location is ambiguous, or local intent conflicts, stop and present the conflict to the operator. Never replace a whole destination or silently omit a changed mapping. Missing-only baseline rendering does not update existing authored prose; run `wf render-surfaces` after reconciliation for the regions it owns.

- **Changed Prepare Serialization Points carrier.** When `170-plan-feature.prompt.md` changed, or the freshly extracted `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md` carries Serialization Points grammar absent from the existing destination, merge only that grammar into the project-authored prose of `docs/prompts/prepare-wave.prompt.md`. Preserve its metadata, all other project prose, and every renderer-owned marker region; the final `wf render-surfaces` pass remains responsible for those managed regions. Never replace the carrier as a whole. If the prior project-authored clause cannot be identified uniquely or local wording conflicts with the new grammar, stop and present the conflict to the operator instead of guessing or overwriting it.
- **Changed contribution-workflow carrier.** When seeds `170` or `190` changed, merge their AC-locality and advisory-sensor clauses into `docs/contributing/change-workflow.md`. Preserve project-only content and metadata; never replace the carrier as a whole. If the prior canonical clause cannot be identified uniquely or local wording conflicts with the new contract, stop and present the conflict to the operator instead of guessing or overwriting it.
- **Changed project-owned review carriers.** When seeds `170`, `180`, `190`, `209`, `214`, `221`, or `239` changed, merge their relevant workflow and reviewer-contract clauses into the existing project-owned carriers: `docs/prompts/plan-feature.prompt.md`, `docs/prompts/implement-wave.prompt.md`, `docs/prompts/review-wave.prompt.md`, `docs/prompts/close-wave.prompt.md`, `docs/agents/architecture-reviewer.md`, `docs/agents/code-reviewer.md`, `docs/agents/qa-reviewer.md`, `docs/agents/wave-coordinator.md`, and `docs/contributing/review-and-evals.md`. This reconciliation includes the AC-locality advisory sensor, the landing and external-blocker rules, frozen-tree review briefs and mutation tables, and Review Artifact Discipline. Preserve project-only content and metadata, preserve historical review artifacts, never replace a whole carrier, and stop for operator resolution when the old canonical clause is not unique or local wording conflicts with the new contract.

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

## Host-neutral orchestration reconciliation

When seeds 050, 100 or 180 or their lifecycle templates change, reconcile the host-neutral orchestration contract during the same upgrade editing pass. Seed 180 remains the policy owner; preserve project additions, metadata and renderer-owned regions. Compare each destination with its source and merge only the changed authored clauses at a unique location; if local intent conflicts or placement is ambiguous, present the conflict instead of overwriting it. Missing-only rendering preserves existing prose and is not proof that this merge happened.

| Source | Existing project destinations |
| --- | --- |
| Seed 180, via seed 100 | prepare-wave, implement-feature, implement-wave, review-wave, pause-wave, close-wave and agent-routing-concurrency under docs/prompts/; phase-specific pointers cover task-fit model selection throughout Prepare-to-Close, honest fallbacks, integration and independent handoff. |
| Missing-only lifecycle templates | Corresponding prepare-wave, implement-wave, review-wave and close-wave prompts; compare changed authored clauses even when the destination already exists. |
| Seed 050 entry/coordinator clauses | AGENTS.md and docs/agents/wave-coordinator.md; replace presumed child MCP inheritance with actual receiving-worker capability and the seed 180 fallback. |
| Seed 100 operating guidance | docs/contributing/agent-team-workflow.md and docs/agents/platform-mapping.md; concise pointers, not separate vendor policies. |
| Seed 050 Claude wrapper defaults | `.claude/agents/guru.md` and `.claude/agents/factor-*.md` frontmatter: omit model/effort on fresh wrappers; preserve existing explicit values. Never add a framework pin or infer ownership from a model name. Retire an existing pin only when provenance or explicit scoped operator direction proves it framework-owned; otherwise retain it and note the concrete optional edit (delete the `model:` or `effort:` line). The renderer also preserves `tools:` verbatim: compare each wrapper against seed 050 and add missing read-only retrieval entries when reconciling stale framework defaults. Preserve deliberate operator restrictions; surface any unresolved mismatch between the tools granted and the refreshed body instead of silently broadening permissions. |

Verify the policy reaches each applicable destination, stale inheritance claims are removed from touched guidance, customization survives and a repeat merge makes no further changes. Run `wf render-surfaces` afterward for its managed regions, then the docs gate. Do not rewrite native host configs or create a model registry. This is an agent editing obligation, not an automatic prose migration claim.

Claude wrapper rendering preserves existing frontmatter. Malformed or ambiguous model/effort frontmatter leaves the wrapper byte-for-byte unchanged throughout rendering, warns on stderr and is excluded from the written list; fix the malformed file deliberately before expecting it to refresh. This stderr warning is not added to the upgrade summary channel.

Surface rendering in the normal installing upgrade runs the on-disk renderer in a fresh subprocess after extraction; it uses the newly extracted implementation. This does not reload agent definitions already held by a running host or worker. Start a fresh agent, or restart the host when it caches definitions, before relying on the changed defaults. Do not mutate user-global host configuration, environment variables, permissions, tool allowlists, active agents or another wave's files as a migration shortcut.

### Post-Git readiness instruction reconciliation

When seed 050 changes, merge its **Check readiness after Git changes** instruction into root `AGENTS.md`, preserving project-specific guidance. Verify checkout-changing operations and conflict stops require `index_health()`, that both freshness and `data.setup_readiness` are inspected, and that the no-MCP `wf setup --check --json` fallback is described as bounded readiness only. Keep host wrappers as pointers; do not install Git hooks or automatically execute recommended repairs.

## Wavefoundry tooling Python runtime guidance

**Wavefoundry tooling Python runtime:** this policy applies to Wavefoundry’s CLI, MCP server and indexing tools. It does not change the host project’s application language or runtime requirements (for example, Java and its JDK). Python 3.13 or newer is recommended. Python 3.11 and 3.12 are deprecated but remain allowed; the minimum is still 3.11. No removal release is scheduled. Dependencies must support the selected interpreter; this recommendation does not qualify every future Python release.

During the editing pass, reconcile this tooling-only policy into existing install/upgrade prompts and Wavefoundry Python support guidance, preserving project additions and renderer-owned regions. Explain the once-per-`wf` invocation and once-per-MCP-serving-start stderr notice, silent dry-run verification, and structured `setup_readiness.advisories` visibility. The advisory is nonblocking and must not be treated as a setup/rebuild action.

Use `.wavefoundry/framework/README.md` **Python runtime advisory and transition** for the deliberate transition: select newer PATH `python3` for both setup and the restarted host; stop all consumers before ordinary setup replaces an incompatible shared environment, or select and propagate an isolated `WAVEFOUNDRY_TOOL_VENV`. Setup does not install Python. Preserve pending recovery ownership and perform a full host restart after changing interpreters.
