# Init Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-09-22

Shortcut: **`Init Wavefoundry`** | Legacy: **`Install Wavefoundry`** / **`Init wave framework`** / **`Install wave framework`** / **`Init wave context`** / **`Install wave context`**

## Purpose

Initialize a target repository with the Wave Framework operating surface. Detects existing state first: if the repository is already seeded, hands off to **Upgrade Wavefoundry** instead of re-running init.

## What Init Does

1. Reads the run contract (seed-020) and builds an evidence base (seed-030): `docs/repo-index.md`, `docs/repo-profile.json`.
2. Detects existing Wave Framework state. If already installed, routes to **Upgrade Wavefoundry**.
3. For greenfield repos (no prior context): skips baseline wave; proceeds directly to bootstrap.
4. For repos with legacy corpus (pre-wave plans/specs): captures and closes a `00000 wave-zero-plans-and-specs` baseline wave before bootstrapping.
5. Bootstraps the full Wave Framework operating surface: docs structure, agent entry files, architecture docs, quality posture, prompt surface, wave artifacts, personas, and typed memory records.
5a. Generates the Backstage catalog and TechDocs baseline at the end of Phase 2 through **Refresh TechDocs** (install-log row 2.13.5, `(seed-178)`): `wf_techdocs_baseline` over MCP, or the `wf techdocs-baseline` CLI, writes the root `catalog-info.yaml`, the root `mkdocs.yml`, and `docs/index.md` missing-only, each with a one-line generated-by stamp, and only once `docs/references/project-overview.md`, `docs/ARCHITECTURE.md`, and `docs/prompts/index.md` exist (otherwise it writes nothing, names the missing targets, and exits non-zero). Existing files are preserved byte-for-byte; when the trio is mixed (some generated, some project-owned) the command prints one `techdocs-baseline: WARNING` naming the project-owned files and never claims the mixed result is a validated site. Conservative defaults (`kind: Component`, `spec.type: documentation`, `spec.lifecycle: experimental`, `spec.owner: engineering`, `backstage.io/techdocs-ref: dir:.`, a `-docs` entity name, deny-by-default `exclude_docs`) are project-owned after generation. Wavefoundry validates the modeled publication contract through its Python tools but does not render or preview the downstream site; rendering and publication are owned by the operator's chosen Backstage/CI environment. Mark row 2.13.5 `[~]` when the precondition is unmet or the operator declines TechDocs. The operator follow-up checklist (verify the owner and the catalog-unique name, rendering/publication ownership, production CI generation plus external storage, optional `repo_url`/`edit_uri` edit links, and the organization-specific files intentionally not generated) lives in `docs/prompts/refresh-techdocs.prompt.md`.
6. Removes the single-use bootstrap file `install-wavefoundry.md` from the project root once the final `wf_audit_install()` gate is the only remaining step (install-log row 2.14) — it ships at the zip root only so the agent can discover the install instructions before `.wavefoundry/` exists; afterwards it is consumed (the canonical instructions live in this doc). Delete it (`rm -f install-wavefoundry.md`), do not move it.
7. Delivers the operator summary after `wf_audit_install()` returns `complete` (row 2.15) covering what was seeded, the workflow, commands, roles, and docs gate.

## Required Outputs

See `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md` for the complete required output list.

Phase 2 may pause after verified row 2.8 when session context is low. Leave row 2.9 unchecked and save a handoff. On return, inventory actual prompt files and `docs/prompts/prompt-surface-manifest.json` against seed-100's current public catalog and conditional rules, preserving project-authored content while reconciling missing or stale required outputs. Do not rely on a fixed prompt count. Once required prompt and role sources exist, call `wf_sync_surfaces(mode='run')` over MCP; use `wf render-surfaces` from CLI when MCP is unavailable. Check that owned upgrade-policy marker regions contain rendered content; empty marker pairs do not satisfy row 2.9, and hand-copying `UPGRADE_POLICY_BLOCK` is not the repair. Only mark 2.9 complete after the real `wf_audit_install` accepts the files, manifest and rendered regions. Keep validation errors visible.

## Git Commits

**Operator-owned.** Agent hands off diff + suggested message. Operator commits.

## MCP / Wavefoundry Server

After installing Wave Framework, enable the local MCP server in your agent host so tools like `wf_help`, `docs_search`, `code_ask`, `wf_audit`, and `index_health` are available.

**Supported operator environments:** macOS, Linux, Windows via WSL2 and native Windows. Native-Windows standard-user diagnosis/repair and fresh-host launch remain pending real-host qualification for this change; see `docs/references/native-windows-support.md`.

**Wavefoundry tooling Python runtime:** this policy applies to Wavefoundry’s CLI, MCP server and indexing tools. It does not change the host project’s application language or runtime requirements (for example, Java and its JDK). Python 3.13 or newer is recommended. Python 3.11 and 3.12 are deprecated but remain allowed; the minimum is still 3.11. No removal release is scheduled. Dependencies must support the selected interpreter; this recommendation does not qualify every future Python release. Follow `.wavefoundry/framework/README.md` **Python runtime advisory and transition** when deliberately changing interpreters: select PATH `python3` for setup and the restarted host, stop shared-environment consumers or propagate an isolated `WAVEFOUNDRY_TOOL_VENV`, and retain existing recovery ownership. The advisory never performs that transition automatically.

**Python requirement:** Python 3.11 or later must be resolvable as `python3` on PATH for a directly spawned agent host. Wavefoundry does not modify Python or PATH. On native Windows, run `powershell -NoProfile -File ".\.wavefoundry\framework\scripts\diagnose_python.ps1"` from the repository root before setup, including an already-seeded checkout newly opened on this machine. The script needs neither Python nor MCP and reports the failed stage, observed command/path/version/error or timeout, and next action. If policy blocks it, use the manual probes and IT handoff in `docs/references/native-windows-support.md`; do not bypass policy. A working `python.exe` is diagnostic evidence, not an MCP alternative. Prefer an approved existing `python3` entry or permitted user PATH repair; do not assume elevation, Store access, Developer Mode or that an installer creates `python3`. A shell alias or cmd shim does not establish raw-spawn host readiness. A successful `python3 --version` at the supported version permits initial setup. `wf setup` creates the shared tool environment at `~/.wavefoundry/venv` (or `$WAVEFOUNDRY_TOOL_VENV`), installs dependencies, then verifies `server.py --dry-run` before index setup. After setup, restart the agent host and verify MCP initialization. For an existing checkout with a provisioned environment, verify `python3 .wavefoundry/framework/scripts/server.py --dry-run` after the interpreter repair; if the environment is missing, follow setup-readiness guidance. Do not reseed or rebuild solely to diagnose a local interpreter gap.

**Versioning:** Wavefoundry uses `MAJOR.MINOR.PATCH` semver internally. Distribution zips use `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` and land in `~/.wavefoundry/dist/` after packaging.

**Check first when unsure:** `wf setup --check` (optionally `--root PATH --json`)
reports `ready` (exit 0), `action_required` (exit 1), or `indeterminate` (exit 2).
Follow the reported action: plain setup for local preparation, a host restart for
stale loaded code, or the retained owning command for pending recovery. Do not
substitute setup for a pending upgrade continuation. The check installs nothing,
downloads no models and does not repair or rebuild indexes. It is read-only for
application data; SQLite may create or update normal WAL/SHM coordination files.
It is a bounded readiness check, not a complete integrity, freshness or search-quality audit.

**Step 1 — Make the installed checkout ready:**

```bash
wf setup
```

Use the same command after a fresh clone or a teammate's framework update.
Setup provisions dependencies and surfaces, updates compatible indexes, and
reconciles supported obsolete storage without selecting a ZIP. Pending
archive-owned recovery stays with its original upgrade continuation. For a
setup storage handoff, save the exact command, stop the repository's old hosts,
and continue in an external terminal with explicit host confirmation. Never
purge local stores or recovery files to bypass a refusal.

Historical memory validation does not block core search. Setup reports core
readiness and pending memory adoption separately; candidates keep their status
and validation labels. Run `memory_backfill(mode="create", entry_path="setup")`,
validate each run-scoped worklist item with `memory_validate`, then rerun
ordinary `wf setup`. Only the guarded memory-publication path may mark that
run indexed. Core readiness alone does not complete historical adoption.

If this setup step fails specifically because a required model cannot be downloaded, keep recovery on the canonical setup path. In agent-driven sessions, the agent should ask the operator for permission to rerun the same setup command with network access or host escalation enabled instead of switching to an out-of-band manual model download.

After setup, MCP host configs should launch the PATH `python3` command on Wavefoundry's `server.py`. Do not point MCP config at `.wavefoundry/venv/Scripts/python.exe`, `.wavefoundry/venv/bin/python`, or another project-local venv interpreter as a workaround for a missing or too-old `python3`; fix `python3 --version` first. The server activates the shared tool environment itself.

`wf setup` smoke-tests the same launch shape the host will use: `python3 .wavefoundry/framework/scripts/server.py --dry-run`. If that fails, fix the reported Python/PATH/dependency issue before restarting the host.

**Step 2 — Register the server in your host:**

| Host | Registration surface | What to do |
|------|----------------------|------------|
| **Claude Code** | `.mcp.json` (auto-generated) | Run `render_platform_surfaces --platform claude`. Open the project - Claude Code discovers `.mcp.json` automatically. |
| **Cursor** | `.cursor/mcp.json` (auto-generated) | Run `render_platform_surfaces --platform cursor`. Enable under **Cursor -> Settings -> MCP** if not auto-loaded. |
| **Junie** | `.junie/mcp/mcp.json` (auto-generated) | Run `render_platform_surfaces --platform junie`. Junie discovers this on project open. |
| **GitHub Copilot** | VS Code MCP settings | Open **VS Code -> Settings -> MCP servers** and add the stdio entry below. |
| **Codex** | `.codex/config.toml` (committed) | Project-local `.codex/config.toml` is committed to the repo. Codex loads the `wavefoundry` MCP server automatically for trusted projects. Trust the project when Codex prompts on first clone. |
| **Antigravity** | `.agents/mcp_config.json` (auto-generated) | Run `render_platform_surfaces --platform antigravity`. The `ag` CLI loads `.agents/mcp_config.json` automatically. (The app/IDE uses the global `~/.gemini/…` config — add the stdio entry below there.) |
| **Windsurf / Air / Warp / other** | Host UI / settings | Add the stdio entry below via your host's MCP settings. Windsurf also gets auto-rendered hooks via `render_platform_surfaces --platform windsurf`; its MCP attachment is still manual. See your host's MCP documentation. |

After connecting, call `wf_server_info()` once to confirm the attached `repo_root` before you rely on any other MCP tools.

**Copy-ready stdio entry** for hosts that accept a direct MCP command block:

```json
{
  "command": "python3",
  "args": [
    "<repo>/.wavefoundry/framework/scripts/server.py",
    "--root",
    "<repo>"
  ]
}
```

See `AGENTS.md → MCP / Wavefoundry server — enabling per host` for the full matrix with UI paths and vendor links.

**Codex config** (`~/.codex/config.toml`):

```toml
[mcp_servers.wavefoundry]
command = "python3"
args = [
  "<repo>/.wavefoundry/framework/scripts/server.py",
  "--root",
  "<repo>"
]
cwd = "<repo>"
```

Register each additional Wavefoundry repo with its own project-local MCP config so the command points at that repo root. Do not rely on hashed Codex server labels as the routing contract. After changing MCP config or fixing Python on PATH, fully quit and reopen the host or start a fresh conversation; do not resume an old session that started before setup completed, because existing sessions may keep the toolset from the failed startup.

**Docs validation (agents):** After MCP is enabled, use **`wf_validate_docs`** and **`wf_garden_docs`** for the docs gate instead of shelling out to the dispatcher. Use the no-PATH fallback only when MCP is not attached: POSIX `./.wavefoundry/bin/wf docs-lint` / `./.wavefoundry/bin/wf docs-gardener`; native Windows `.\\.wavefoundry\\bin\\wf.cmd docs-lint` / `.\\.wavefoundry\\bin\\wf.cmd docs-gardener`.

**Optional local dashboard:** After install, the repository can expose the local dashboard surface with **`Start dashboard`**, **`Stop dashboard`**, and **`Restart dashboard`**. The start command runs:

```bash
wf dashboard --root . --open
```

**Step 3 — Restart MCP and verify the setup-owned index:**

After registration, restart the MCP server in your host so it loads the installed
framework. Use `index_health()` and `index_build_status()` to verify core search
and graph readiness. If historical memory remains pending, complete its
run-scoped validation and rerun `wf setup`; no manual index purge or lower-level
script is needed.

The framework's seeds fold into this project docs index — there is no separate framework index to build.

See `docs/contributing/build-and-verification.md` **Update vs rebuild — decision table** for when to use `mode="update"` vs `mode="rebuild"`.

If you launched a detached background setup build, poll `index_build_status(layer?)` until it finishes before assuming that layer's search is current.

## Aliases

- **Install Wavefoundry** / **Install wave framework** / **Install wave context** — accepted; routes to init (greenfield) or upgrade (already seeded)
- **Init wave framework** / **Init wave context** — legacy alias; identical behavior

## Local index storage

Fresh setup uses `.wavefoundry/index/index.sqlite` for docs/code chunks,
vectors, FTS, indexing state, the code graph and its communities. Text is stored
once and every layer publishes in one transaction. Standard setup provisions
the pinned SQLite runtime and extension without a LanceDB runtime dependency.
An existing legacy index follows **Upgrade Wavefoundry**, including any required
host restart and retained recovery checkpoint; do not delete it to force a
fresh install.
