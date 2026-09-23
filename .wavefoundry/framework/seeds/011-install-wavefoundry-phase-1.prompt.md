# 011 - Install Wavefoundry, Phase 1 (Harness — no MCP required)

**Shortcut entry:** This seed is reached via the zip-root `install-wavefoundry.md`, which creates and then follows the live `.wavefoundry/install-log.md`. Operators typing **`Install Wavefoundry`** are routed here by `seed-010` for the harness phase.

**Critical invariant — Phase 1 has NO MCP available.** The MCP server is what Phase 1 installs. Do not call `wave_*` MCP tools here. Use shell, Python scripts, file edits, and direct seed reads from `.wavefoundry/framework/seeds/`.

## State machine

The install state is tracked in `.wavefoundry/install-log.md` — your project's **live log instance**, copied from `.wavefoundry/framework/install/install-log.template.md` on first install. The template is overwritten on framework upgrades; your live log is NOT, so install progress is preserved.

Each row points at a step the agent must execute and an artifact the step is expected to produce. Read the first unchecked row, execute the step, verify the artifact, mark `[x]`, advance. The full row format and trustworthy-invariant rule are in `docs/references/install-log-format.md` (provisioned during Phase 2 step 2.4 from the shipped framework template — until then, the rules are inline below).

### Bootstrap: copy template if live log doesn't exist

Before executing row 1.1, check whether `.wavefoundry/install-log.md` exists:

- **It does not exist (first install):** copy `.wavefoundry/framework/install/install-log.template.md` to `.wavefoundry/install-log.md`. Substitute `{{generated_at}}` with today's date (YYYY-MM-DD). **Write the file as UTF-8.** The log's row separators are em dashes (`—`); a non-UTF-8 write corrupts them to mojibake (`â€"`) and the install audit can no longer parse the rows. On Windows PowerShell, do **not** use bare `Get-Content`/`Set-Content`/`Out-File` (they default to the ANSI/UTF-16 code page) — pass `-Encoding utf8`, or write via a UTF-8-explicit tool (e.g. `python -c "...write_text(..., encoding='utf-8')"`).
- **It exists (resuming or upgrading):** continue from the first unchecked row. If you're unsure whether existing `[x]` markers are still valid (fresh agent session, partial recovery from an abort), the trustworthy-invariant rule says: re-execute `wf_audit_install` before trusting them (Phase 2 only — Phase 1 has no MCP).

## Steps (mirror `.wavefoundry/install-log.md` Phase 1)

### 1.1 — Bootstrap harness (single orchestrated script)

**Action:** Run `wf setup`. This is the orchestrator that completes all the mechanical Phase 1 work in one call — **including provisioning the lifecycle-ID policy and required workflow defaults**. After read-only recovery preflight, Step 0/4 computes and atomically writes the complete scheme-v2 `lifecycle_id_policy` into `docs/workflow-config.json` when no policy block exists yet (`epoch_utc` = the install date so no ID horizon is burned on past years; a deterministic scattered `offset`; `scheme_version: "v2"`). It also adds each absent framework-required section from the shipped defaults: `wave_implement`, `wave_review`, `agent_memory`, `project_persona_generation`, `prompt_generation`, `factor_review_policy`, and `persona_review_policy`. Existing top-level sections are never modified or reordered. No manual epoch/offset computation and no hand-authored default policy — do **not** hand-edit the lifecycle policy block. Because setup runs before any ID is minted or docs gate runs, no ID can be generated under fallback settings and no fresh config reaches lint without its required sections.

**Setup makes the installed checkout ready.** After cloning or pulling framework changes, run the same `wf setup`. It does not discover or install release archives. Before changing local setup state it checks recovery ownership; a pending archive-owned upgrade must finish through its retained upgrade continuation. Supported obsolete indexes reconcile through staged conversion with source-bound recovery and verification before cleanup. Save any setup restart command, stop the repository's old hosts, and run that exact command in an external terminal with its explicit host confirmation. Empty host discovery is not proof that every host stopped. Never delete indexes, locks or receipts to force setup forward.

**Check first when unsure:** `wf setup --check` (optionally `--root PATH --json`)
reports `ready` (exit 0), `action_required` (exit 1), or `indeterminate` (exit 2).
Follow the reported action: plain setup for local preparation, a host restart for
stale loaded code, or the retained owning command for pending recovery. Do not
substitute setup for a pending upgrade continuation. The check installs nothing,
downloads no models and does not repair or rebuild indexes. It is read-only for
application data; SQLite may create or update normal WAL/SHM coordination files.
It is a bounded readiness check, not a complete integrity, freshness or search-quality audit.

**Historical memory remains explicit without blocking core search.** Setup can publish core docs/code/graph indexes while historical validation is pending. It reports that pending work separately and does not mark the backfill indexed, promote candidates, or change their validation labels. Run `memory_backfill(mode="create", entry_path="setup")`, validate its run-scoped worklist with `memory_validate`, then rerun ordinary `wf setup`. The ready run still uses the guarded publication receipt and authoritative pending census. Core readiness is not completion of historical memory adoption; `wf_audit_install` remains observational.

**Wavefoundry tooling Python runtime:** this policy applies to Wavefoundry’s CLI, MCP server and indexing tools. It does not change the host project’s application language or runtime requirements (for example, Java and its JDK). Python 3.13 or newer is recommended. Python 3.11 and 3.12 are deprecated but remain allowed; the minimum is still 3.11. No removal release is scheduled. Dependencies must support the selected interpreter; this recommendation does not qualify every future Python release. Follow `.wavefoundry/framework/README.md` **Python runtime advisory and transition** when deliberately changing interpreters: select PATH `python3` for setup and the restarted host, stop shared-environment consumers or propagate an isolated `WAVEFOUNDRY_TOOL_VENV`, and retain existing recovery ownership. The advisory never performs that transition automatically.

**Python prerequisite, including a new workstation with an already-seeded checkout:** Before `wf setup`, MCP attachment, or trust in completed install-log rows, verify that a fresh host can resolve `python3` to a working Python 3.11 or newer. On native Windows, run the read-only pre-Python diagnostic from the repository root even if `wf.cmd` or MCP cannot start:

```powershell
powershell -NoProfile -File ".\.wavefoundry\framework\scripts\diagnose_python.ps1"
```

It probes the required `python3` command and available `python` entry with bounded checks; a discovered `python.exe` is diagnostic evidence, never an alternate setup or MCP command. Record the failed stage, attempted command, resolved path and interpreter identity when available, observed error/exit/timeout, and a next step. Treat PATH, execution-alias, policy, and stale-host explanations as hypotheses until evidence supports one. If PowerShell policy blocks the script, use `Get-Command python3,python -All -ErrorAction SilentlyContinue`, `where.exe python3`, `where.exe python`, and direct version probes, then ask IT for help if policy prevents a permitted repair. Do not bypass execution policy.

If `python3` is absent, too old, a Store placeholder, or unusable, stop before setup writes, dependency provisioning, or model downloads. Prefer an existing approved `python3` executable/alias and a permitted user PATH correction. Do not assume administrator rights, Store access, Developer Mode, or that any particular Windows installer supplies `python3`; a shell alias or cmd shim does not satisfy a raw-spawn MCP host. If only a suitable `python.exe` exists and no approved `python3` entry can be exposed, give IT the interpreter path/version, failed `python3` probe, required command and minimum version, fresh-host visibility requirement, and `python3 .../server.py --dry-run` verification. Keep setup unready while waiting. After interpreter repair, verify `python3 --version` in a fresh terminal. For initial installation, this permits setup to provision dependencies before its `server.py --dry-run` check; afterward restart the agent host and verify MCP attachment. An existing provisioned checkout can run `python3 .wavefoundry/framework/scripts/server.py --dry-run` directly; if the environment is absent, follow setup-readiness guidance. Do not reseed or rebuild a previously installed checkout solely to diagnose its local interpreter.

0. **Step 0/4 — lifecycle-ID policy + workflow defaults** (fresh repos only): provisions the scheme-v2 `lifecycle_id_policy` described above when `docs/workflow-config.json` has no policy block, then adds only absent required sections from `.wavefoundry/framework/install/workflow-config.defaults.json`; prints the lifecycle-policy result plus `workflow config: provisioned N default section(s)` or `workflow config: already complete`, and aborts setup loudly without writing if the existing config is unparseable. Recovery fallback for a missing lifecycle policy is `wf upgrade --materialize-lifecycle-policy`; rerun ordinary `wf setup` for missing default sections.
1. **Step 1/4 — `wf` dispatcher shim + platform host configs** (via `render_platform_surfaces.py`):
   - The cross-OS `wf` entry point and generated `wf.cmd` shim that dispatch to `wf_cli.py`, which routes subcommands `wf docs-lint`, `wf docs-gardener`, `wf gate`, `wf dashboard`, `wf update-indexes`, `wf lifecycle-id`, `wf upgrade`, and `wf setup` to their backing scripts.
   - `.claude/settings.json` (if Claude Code is detected) and equivalents for other hosts; registers the MCP server with the host's verified owner-root/config-relative contract.
   - MCP configs must launch the PATH `python3` command on Wavefoundry's `server.py`; do not point them at `.wavefoundry/venv/Scripts/python.exe`, `.wavefoundry/venv/bin/python`, or another project-local venv interpreter as a workaround for a missing or too-old `python3`. `server.py` activates the shared tool environment itself.
   - **Do NOT create these files by hand.** The renderer is the source of truth; pre-created files will be overwritten on next render and cause spurious diffs.
   - Setup/render installs prospective lifecycle carriers only. It must not create, migrate, repair, or rewrite `docs/waves/*/{wave.md,events.jsonl}`; historical target-project wave bytes remain untouched. New external-ledger state begins only when the operator later invokes the public Create-wave path.
2. **Step 2/4 — venv + framework dependencies**:
   - Creates the tool venv at `~/.wavefoundry/venv/` (user-home, not project-root — the venv is shared across all wavefoundry projects on the machine; `WAVEFOUNDRY_TOOL_VENV` env var overrides).
   - Installs framework deps, including the embedding/index stack and SOCKS proxy support for httpx-backed downloads.
   - Does **not** publish semantic or graph indexes yet. Storage reconciliation follows dependency provisioning; historical-memory inventory follows the MCP smoke test. Pending curation does not block normal core publication.
3. **Step 3/4 — MCP server dry-run smoke test** (via `server.py --dry-run`):
   - Verifies the MCP server can initialize through the same launch shape generated MCP configs use: `python3 .wavefoundry/framework/scripts/server.py --dry-run`.
   - Confirms all imports work, tool registration succeeds, framework state is loadable, and the PATH `python3` that the host will launch can use the Wavefoundry tool environment.
   - Exits 0 on success, non-zero on failure with a clear diagnostic.
   - This catches startup misconfigurations BEFORE the operator restarts their agent; without this, a broken MCP would only surface after restart.
4. **Step 4/4 — core index publication and historical-memory status**:
   - Inventories closed waves into the durable SQLite backfill state.
   - Builds core indexes and reports pending memory validation without claiming adoption complete.
   - Builds `.wavefoundry/index/` (docs/seeds, semantic code embeddings, code embeddings, and graph). The framework seeds and top-level README fold into the project docs index; there is no separate framework index.
   - Use `--background-code` or `--background-docs` only when the operator intentionally accepts one semantic layer finishing after setup returns. A storage migration or candidate-bearing validated historical-memory publication intentionally ignores either flag and converges both semantic layers synchronously under its publication receipt.

**Expected artifact:** the committed `.mcp.json` names `command: "python3"` and the repo-relative `.wavefoundry/framework/scripts/server.py` as its only argument — a path, never an inline `-c` program, so the committed config stays auditable for enterprise review; `python3 .wavefoundry/framework/scripts/server.py --dry-run` exits 0 from the repository root. The server anchors its own repository from its install location, so no `--root` and no project-anchor variable belongs in this stanza. Hook launchers are the separate case that does need `CLAUDE_PROJECT_DIR`.

If any step fails, the orchestrator stops and reports which step. Re-run after fixing — the orchestrator is idempotent (each sub-step detects existing state).

Fresh index storage uses one project-local
`.wavefoundry/index/index.sqlite` for both docs and code and for the code graph,
with canonical text stored once and chunks, vectors, FTS, graph rows and
communities published together in a single transaction. Standard setup provisions
pinned APSW/SQLite and sqlite-vec in the tool environment; it does not install
LanceDB for a new project. Keep Python 3.11+ and the existing platform bootstrap
path. Setup reconciles supported old stores through staged migration; never delete
them or treat the project as fresh to bypass recovery.

### 1.2 — Verify lifecycle policy and workflow defaults provisioned by setup

**Action:** confirm `docs/workflow-config.json` carries `lifecycle_id_policy.scheme_version` set to `"v2"` and the required top-level sections `wave_implement`, `wave_review`, `agent_memory`, `project_persona_generation`, `prompt_generation`, `factor_review_policy`, and `persona_review_policy`. Setup's Step 0 adds only absent default sections and leaves every operator-set section untouched. If a default section is absent, rerun `wf setup`. If only the lifecycle policy is absent, run `wf upgrade --materialize-lifecycle-policy` — never hand-edit `epoch_utc`, `offset`, or `scheme_version`; issued IDs depend on them.

**Expected artifact:** `docs/workflow-config.json` with `lifecycle_id_policy.scheme_version` present (fresh installs: `"v2"`) and all seven required framework-default sections present.

### 1.3 — STOP: Instruct operator to restart agent

**Action:** Mark this row `[x]` only after instructing the operator: **"Phase 1 is complete. Please fully quit and reopen your AI agent in this project, or start a fresh conversation after your host's MCP restart command, so the Wavefoundry MCP server becomes available before we proceed to Phase 2."**

Do not start Phase 2 in the current agent session. The MCP server is not yet reachable to the agent until restart.

## After Phase 1

When the operator restarts the agent and returns, the agent should:

1. Read `.wavefoundry/install-log.md` again
2. Confirm all Phase 1 rows are `[x]`
3. Begin Phase 2 (seed-012) starting with row 2.1, which is `wf_audit_install(phase=1)`

If any Phase 1 row is not `[x]`, do not proceed. Return to that row.

## Out of scope for Phase 1

These belong to Phase 2 (seed-012):

- Generating agent role docs (`docs/agents/<role>.md`) — needs MCP for verification
- Synthesizing personas
- Bootstrapping architecture docs
- Bootstrapping design system
- Wiring docs-gate seeds 080 + 090 in full (only the bin/ launchers are Phase 1; the gate-rules are Phase 2)
- Generating the prompt surface (seed-100)
- Bootstrapping wave artifacts (seed-110)
- Setting drift expectations (seed-140)
- Generating the Backstage catalog and TechDocs baseline (`catalog-info.yaml`, `mkdocs.yml`, `docs/index.md`): Phase 1 never generates them and `wf setup` never writes them; **Refresh TechDocs** at row 2.13.5 runs `wf_techdocs_baseline` (CLI fallback `wf techdocs-baseline`) once the Phase 2 navigation targets (`docs/references/project-overview.md`, `docs/ARCHITECTURE.md`, `docs/prompts/index.md`) exist

These need either MCP for validation, or sit on top of the harness Phase 1 installs.
