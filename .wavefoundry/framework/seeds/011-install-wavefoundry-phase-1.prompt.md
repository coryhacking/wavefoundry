# 011 - Install Wavefoundry, Phase 1 (Harness — no MCP required)

**Shortcut entry:** This seed is reached via `install-wavefoundry.md` and `wavefoundry-install-log.md` at the zip root. Operators typing **`Install Wavefoundry`** are routed here by `seed-010` for the harness phase.

**Critical invariant — Phase 1 has NO MCP available.** The MCP server is what Phase 1 installs. Do not call `wave_*` MCP tools here. Use shell, Python scripts, file edits, and direct seed reads from `.wavefoundry/framework/seeds/`.

## State machine

The install state is tracked in `.wavefoundry/install-log.md` — your project's **live log instance**, copied from `.wavefoundry/framework/install/install-log.template.md` on first install. The template is overwritten on framework upgrades; your live log is NOT, so install progress is preserved.

Each row points at a step the agent must execute and an artifact the step is expected to produce. Read the first unchecked row, execute the step, verify the artifact, mark `[x]`, advance. The full row format and trustworthy-invariant rule are in `docs/references/install-log-format.md` (provisioned during Phase 2 step 2.3 from the shipped framework template — until then, the rules are inline below).

### Bootstrap: copy template if live log doesn't exist

Before executing row 1.1, check whether `.wavefoundry/install-log.md` exists:

- **It does not exist (first install):** copy `.wavefoundry/framework/install/install-log.template.md` to `.wavefoundry/install-log.md`. Substitute `{{generated_at}}` with today's date (YYYY-MM-DD). **Write the file as UTF-8.** The log's row separators are em dashes (`—`); a non-UTF-8 write corrupts them to mojibake (`â€"`) and the install audit can no longer parse the rows. On Windows PowerShell, do **not** use bare `Get-Content`/`Set-Content`/`Out-File` (they default to the ANSI/UTF-16 code page) — pass `-Encoding utf8`, or write via a UTF-8-explicit tool (e.g. `python -c "...write_text(..., encoding='utf-8')"`).
- **It exists (resuming or upgrading):** continue from the first unchecked row. If you're unsure whether existing `[x]` markers are still valid (fresh agent session, partial recovery from an abort), the trustworthy-invariant rule says: re-execute `wave_install_audit` before trusting them (Phase 2 only — Phase 1 has no MCP).

## Steps (mirror `wavefoundry-install-log.md` Phase 1)

### 1.1 — Bootstrap harness (single orchestrated script)

**Action:** Run `wf setup`. This is the orchestrator that completes all the mechanical Phase 1 work in one call — **including provisioning the lifecycle-ID policy**: setup's first action (Step 0/4) computes and atomically writes the complete scheme-v2 `lifecycle_id_policy` into `docs/workflow-config.json` when no policy block exists yet (`epoch_utc` = the install date so no ID horizon is burned on past years; a deterministic scattered `offset`; `scheme_version: "v2"`). No manual epoch/offset computation, no separate step — do **not** hand-edit the policy block. A repo that already carries a policy block is left untouched (configured repos migrate via the upgrade pipeline, not setup). Because setup runs before any ID is minted, no ID can ever be generated under fallback settings.

**Historical projects pause before index publication.** Setup now provisions dependencies and smoke-tests the newly installed MCP before publishing an index. A fresh project with no closed wave history continues in one pass. An already wave-enabled target returns action-required exit 4 with `awaiting_memory_validation`: reload/restart the MCP host, repeatedly call `wave_memory_backfill(mode="create", entry_path="setup")`, validate each pending candidate through `wave_memory_validate`, then rerun ordinary `wf setup`. This is a retained setup phase, not failure or completion. The repeated setup invocation reuses the durable run, recomputes the authoritative `memory-state.sqlite` pending census, and owns the single index publication. There is no setup-memory-specific MCP tool or public resume flag. Migration uses this same reentrant setup gate. `wave_install_audit` remains observational and never resumes or writes backfill state.

**Python prerequisite:** Before running setup, `python3 --version` must work from the command line and report Python 3.11 or newer. If `python3` is missing, if only `python` is available, or if `python3` reports a version below 3.11, stop. The agent or operator must install/fix Python and PATH before proceeding; do not bypass this by pointing MCP at a tool-venv or project-local Python.

0. **Step 0/4 — lifecycle-ID policy** (fresh repos only): provisions the scheme-v2 `lifecycle_id_policy` described above when `docs/workflow-config.json` has no policy block; prints `lifecycle policy: …` and aborts setup loudly if the existing config is unparseable. Recovery fallback if this step was somehow skipped: `wf upgrade --materialize-lifecycle-policy`.
1. **Step 1/4 — `wf` dispatcher shim + platform host configs** (via `render_platform_surfaces.py`):
   - The cross-OS `wf` entry point and generated `wf.cmd` shim that dispatch to `wf_cli.py`, which routes subcommands `wf docs-lint`, `wf docs-gardener`, `wf gate`, `wf dashboard`, `wf update-indexes`, `wf lifecycle-id`, `wf upgrade`, and `wf setup` to their backing scripts.
   - `.claude/settings.json` (if Claude Code is detected) and equivalents for other hosts; registers the MCP server (the committed `.mcp.json` runs `python3 .wavefoundry/framework/scripts/server.py`).
   - MCP configs must launch the PATH `python3` command on Wavefoundry's `server.py`; do not point them at `.wavefoundry/venv/Scripts/python.exe`, `.wavefoundry/venv/bin/python`, or another project-local venv interpreter as a workaround for a missing or too-old `python3`. `server.py` activates the shared tool environment itself.
   - **Do NOT create these files by hand.** The renderer is the source of truth; pre-created files will be overwritten on next render and cause spurious diffs.
   - Setup/render installs prospective lifecycle carriers only. It must not create, migrate, repair, or rewrite `docs/waves/*/{wave.md,events.jsonl}`; historical target-project wave bytes remain untouched. New external-ledger state begins only when the operator later invokes the public Create-wave path.
2. **Step 2/4 — venv + framework dependencies**:
   - Creates the tool venv at `~/.wavefoundry/venv/` (user-home, not project-root — the venv is shared across all wavefoundry projects on the machine; `WAVEFOUNDRY_TOOL_VENV` env var overrides).
   - Installs framework deps, including the embedding/index stack and SOCKS proxy support for httpx-backed downloads.
   - Does **not** publish semantic or graph indexes yet. Historical-memory inventory runs after the MCP smoke test; only a no-work result or an explicit successful resume authorizes publication.
3. **Step 3/4 — MCP server dry-run smoke test** (via `server.py --dry-run`):
   - Verifies the MCP server can initialize through the same launch shape generated MCP configs use: `python3 .wavefoundry/framework/scripts/server.py --dry-run`.
   - Confirms all imports work, tool registration succeeds, framework state is loadable, and the PATH `python3` that the host will launch can use the Wavefoundry tool environment.
   - Exits 0 on success, non-zero on failure with a clear diagnostic.
   - This catches startup misconfigurations BEFORE the operator restarts their agent; without this, a broken MCP would only surface after restart.
4. **Step 4/4 — historical-memory gate, then index publication**:
   - Inventories closed waves into the durable SQLite backfill state.
   - Returns action-required exit 4 before publication when validation remains.
   - Otherwise—or after an ordinary repeated `wf setup` recomputes an empty pending set—builds `.wavefoundry/index/` (docs/seeds, semantic code embeddings, code embeddings, and graph). The framework seeds and top-level README fold into the project docs index; there is no separate framework index.
   - Use `--background-code` or `--background-docs` only when the operator intentionally accepts one semantic layer finishing after setup returns. A candidate-bearing historical-memory publication intentionally ignores either flag and converges both semantic layers synchronously under its publication receipt.

**Expected artifact:** the committed `.mcp.json` names `command: "python3"` + `args: [".wavefoundry/framework/scripts/server.py"]` AND `python3 .wavefoundry/framework/scripts/server.py --dry-run` exits 0.

If any step fails, the orchestrator stops and reports which step. Re-run after fixing — the orchestrator is idempotent (each sub-step detects existing state).

### 1.2 — Verify lifecycle-ID policy provisioned by setup

**Action:** confirm `docs/workflow-config.json` carries `lifecycle_id_policy.scheme_version` set to `"v2"` (setup's Step 0 wrote it, or left an existing policy block untouched — both outcomes are correct). If the key is absent on a fresh install, run `wf upgrade --materialize-lifecycle-policy` — never hand-edit `epoch_utc`, `offset`, or `scheme_version`; issued IDs depend on them.

**Expected artifact:** `docs/workflow-config.json` with `lifecycle_id_policy.scheme_version` present (fresh installs: `"v2"`).

### 1.3 — STOP: Instruct operator to restart agent

**Action:** Mark this row `[x]` only after instructing the operator: **"Phase 1 is complete. Please fully quit and reopen your AI agent in this project, or start a fresh conversation after your host's MCP restart command, so the Wavefoundry MCP server becomes available before we proceed to Phase 2."**

Do not start Phase 2 in the current agent session. The MCP server is not yet reachable to the agent until restart.

## After Phase 1

When the operator restarts the agent and returns, the agent should:

1. Read `wavefoundry-install-log.md` again
2. Confirm all Phase 1 rows are `[x]`
3. Begin Phase 2 (seed-012) starting with row 2.1, which is `wave_install_audit(phase=1)`

If any Phase 1 row is not `[x]`, do not proceed. Return to that row.

## Out of scope for Phase 1

These belong to Phase 2 (seed-012):

- Generating agent role docs (`docs/agents/<role>.md`) — needs MCP for verification
- Generating per-role journals
- Synthesizing personas
- Bootstrapping architecture docs
- Bootstrapping design system
- Wiring docs-gate seeds 080 + 090 in full (only the bin/ launchers are Phase 1; the gate-rules are Phase 2)
- Generating the prompt surface (seed-100)
- Bootstrapping wave artifacts (seed-110)
- Setting drift expectations (seed-140)

These need either MCP for validation, or sit on top of the harness Phase 1 installs.
