# Agent Platform Mapping

Owner: Engineering
Status: active
Last verified: 2026-08-21

Maps Wave Framework agent docs, personas, specialists, and factor agents to native agent platform files.

## Auto-Guru routing (code and documentation Q&A)

**Canonical (all hosts):** `AGENTS.md` § **Codebase and documentation questions (auto-Guru)** + `docs/agents/guru.md`.

| Tier | Scope | Surfaces |
|------|--------|----------|
| 1 | Every agent host | `AGENTS.md`, `docs/agents/guru.md`, Wavefoundry MCP when attached |
| 2 | Each host thin pointer | One guardrail bullet → tier 1 (see per-host table below) |
| 3 | Optional native affordance | Host-specific rules / subagents / skills (below) |

### Tier 2 — thin pointers

| Host | Entry file |
|------|------------|
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursor/rules/project-context.mdc` → `.cursor/rules/auto-guru.mdc` |
| Codex | `AGENTS.md` (+ optional tier 3 skill) |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Junie | `.junie/guidelines.md` |
| Warp | `WARP.md` |
| Windsurf | `AGENTS.md` (no separate guidelines file in default seed) |
| Air | `AGENTS.md` (provider MCP config per `AGENTS.md` MCP table) |
| Antigravity | `AGENTS.md` (Tier-1 native; no separate file; MCP via `.agents/mcp_config.json` — workspace-local configuration) |

### Tier 3 — optional native (enhances tier 1)

| Host | File | Notes |
|------|------|--------|
| Cursor | `.cursor/rules/auto-guru.mdc` | `alwaysApply` rule |
| Claude Code | `.claude/agents/guru.md` | `PROACTIVELY` subagent |
| Codex | `.codex/skills/wf-guru/SKILL.md` | `.codex/config.toml` (project-local, committed) |

### Skills (`wf-` namespace, registry-rendered)

One registry (`render_agent_surfaces.render_skills`, wave `1p6lp`) renders every Wavefoundry skill as standard `SKILL.md` (frontmatter `name`/`description` + thin-pointer body) into each **active** skill host directory. A host is active when its root directory exists.

| Skill | Backing prompt(s) | Gate |
|-------|-------------------|------|
| `wf-plan-feature` | `docs/prompts/plan-feature.prompt.md` | none |
| `wf-prepare-wave` | `docs/prompts/prepare-wave.prompt.md` | none |
| `wf-implement-wave` | `docs/prompts/implement-wave.prompt.md` | none |
| `wf-review-wave` | `docs/prompts/review-wave.prompt.md` | none |
| `wf-close-wave` | `docs/prompts/close-wave.prompt.md` | none |
| `wf-interrogate-plan` | `docs/prompts/interrogate-plan.prompt.md` | none |
| `wf-evaluate-decision` | `docs/prompts/evaluate-decision.prompt.md` | none |
| `wf-memory-review` | `docs/prompts/memory-review.prompt.md` | none |
| `wf-pause-wave` | `docs/prompts/pause-wave.prompt.md` | none |
| `wf-council` | `docs/prompts/council-review.prompt.md`, `docs/prompts/archetype-council.prompt.md`, `docs/prompts/red-team-review.prompt.md` | none |
| `wf-guru` | `docs/agents/guru.md` (role doc) | `docs/agents/guru.md` present |
| `wf-upgrade` | `docs/prompts/upgrade-wavefoundry.prompt.md` | none (maintenance checklist) |
| `wf-package` | `docs/prompts/package-wavefoundry.prompt.md` | backing prompt present (seed 100 public-only/when-present, so normally the framework source repo only) |
| `wf-code-cleanup` | `docs/prompts/codebase-cleanup-review.prompt.md` | backing prompt present (repo-local surface; no seed provisions it to targets) |
| `wf-techdocs` | `docs/prompts/refresh-techdocs.prompt.md` | backing prompt present (seed 178 renders it into every target through seed 100, so the skill renders wherever that reconciliation has run; on the upgrade that first ships seed 178, re-run `wf render-surfaces` after the prompt backfill) |

Every skill emits to each active host dir among `.codex/skills/`, `.claude/skills/`, `.agents/skills/` (all three active here; 15 skill directories in each as of 2026-08-18). Skills render on `wf setup` and **Upgrade Wavefoundry**; rendering is independent of `enabled_agent_roles`, which gates agent-role wrappers, not skills. A skill with a `requires_doc` gate (wave `1ve3a`) emits only where that repo-relative doc exists, so the skill follows the capability rather than a repo identity. Bodies are thin pointers; workflow content stays in the backing prompt docs. Stale-cleaned legacy paths: `.claude/skills/upgrade-wave.md` (flat, frontmatter-less), `.codex/skills/auto-guru/` (pre-namespace).

## Host launcher contracts

| Host | Hook path contract | MCP path contract | Evidence level |
|------|--------------------|-------------------|----------------|
| Claude Code | Owner-bound through `CLAUDE_PROJECT_DIR`; main-session `Stop` renders separate session-capture and detached Context Efficiency projection adapters | Owner-bound through `CLAUDE_PROJECT_DIR` | Executed on macOS from nested cwd; committed launcher is platform-neutral and uses windowless detached Python on Windows |
| Cursor | Host launches project hooks from the workspace root | `${workspaceFolder}` `cwd` pin | Renderer/fixture verified |
| GitHub Copilot | Repository-root contract; native `bash` and `powershell` fields | Provider/UI registration | Schema rendered; host runtime not claimed |
| Windsurf | `working_directory: "."` project-root contract | Provider/UI registration | Renderer/fixture verified |
| Junie | No native hooks are emitted without a verified contract | Config-relative from `.junie/mcp/` | Config-relative execution contract verified |
| Codex | No native hooks are emitted without a verified project-owner signal | Project-local config; host opens the project root | Root-only; non-Git projects are supported when opened at their root |
| Air / Warp | Delegated to the underlying agent host; no invented native hook files | Provider/UI registration | Explicitly unsupported as native hook surfaces |
| Antigravity | No native hook file is emitted | Workspace-local `.agents/mcp_config.json`, root-only | Config shape verified; no native hook claim |

The Context Efficiency projection safety net is MCP-owned and therefore applies
to every attached host independently of native hook support or index-monitor
configuration. Only Claude Code receives the verified native turn-end adapter;
Codex, Cursor, Copilot, Windsurf, Junie, Air, Warp, and Antigravity receive no
invented end-turn surface and converge through the MCP quiet-period monitor.

Root-only means exactly that: the host must launch from the configured project root. Wavefoundry does
not search upward from an arbitrary cwd, because a descendant containing another installation could
silently change project identity. Missing host authority is surfaced as a support limitation, not
papered over with a generic locator.

## Rendered MCP Permission Surface (wave 1u2b0)

| Host | Rendered surface | Render path | Ownership model |
|------|------------------|-------------|-----------------|
| Claude Code | `.claude/settings.json` `permissions.allow` allowlist (read-only tier by default; write tier behind the operator-authored `wavefoundryAllowWriteTools` key) | Upgrade/install orchestration (renderer's explicit include-permissions switch); the agent-invocable `wf_sync_surfaces` render never touches `permissions` content | Provenance set-merge: emitted entries recorded under `wavefoundryManagedAllow`; operator entries (including wavefoundry-named ones) survive every render; ownership is never inferred from the `mcp__wavefoundry__` name prefix |
| Cursor / Codex / Copilot / Windsurf / Junie / Air / Warp / Antigravity | None rendered in this release | n/a | Out of scope for rendering; the design does not preclude equivalent surfaces later |

The allowlist derives from the canonical stdlib tool roster
(`.wavefoundry/framework/scripts/mcp_tool_roster.py`, tool name plus a dedicated
permission tier), so tool renames self-heal on the next upgrade render; the
upgrade output names the rendered permissions delta as an explicit operator
consent line, and the reconciliation scan reports renderer-provenance stale
rules in their own self-healing channel (see `docs/specs/mcp-tool-surface.md`).

Render-boundary honesty: the `wf_sync_surfaces` negative is a tested invariant,
but the boundary as a whole is **operator approval plus host enforcement, not
structural agent-unreachability**. `wf_upgrade` is an ordinary agent-callable
MCP tool whose first phase renders, so an agent can trigger a render; the
impact is bounded to the read tier, because the write tier needs the operator
knob and `wf_upgrade` is itself write-tier and so cannot allowlist itself.
Passing the include-permissions switch to the renderer through the `wf`
dispatcher is an accepted residual outside the threat model (an agent with
unrestricted shell access can write `.claude/settings.json` directly). The
knob's home is likewise protected by the host prompting on edits to that file
plus prompt policy, not by the framework: the framework's own pre-edit guard
there is the `framework_edit_allowed` gate, which an agent can open, so writing
the knob takes the same capability as writing the rules by hand.

First-render timing: a fresh install and a protocol-bridge upgrade render the
block immediately; an ordinary upgrade of an existing target renders it during
the same upgrade only because of backstops in the upgrade's later phases, which
exist because the in-process orchestrator running the surface-render phase is
pre-extraction (old) code. The backstops run from phases the upgrade executes in
a separate process on the freshly extracted code: the cleanup phase, which every
upgrade path reaches, plus the index-refresh phase for the flows that run it. A repo that already hand-maintained the wavefoundry
allow rules gets nothing claimed, an empty provenance, and no rename self-heal
until the operator deletes those rules and lets the renderer re-emit them; the
consent output reports them as already present and left unmanaged.

## Executable Review-Evidence Propagation

Canonical reviewer/council docs are the source surfaces. `render_agent_surfaces.py` derives its finite destination manifest from `REVIEW_PROTOCOL_CARRIER_REGISTRY` and reconciles one `wave:executable-review-evidence` marker region per enabled carrier through the public `wf render-surfaces` path. Setup, full upgrade, targeted/full refresh, and Wavefoundry self-hosting use that same operation. Missing required canonical carriers are created from installed seeds or a bounded multi-output-owner pointer; Guru and repo-local optional lanes remain existing/enabled-only. The renderer owns only the marked section and preserves project-authored extensions outside it.

Native reviewer wrappers are not discovered by a broad glob. Only an existing `.claude/agents/<registered-role>.md` or `.codex/skills/agent-role-<registered-role>/SKILL.md` derived from a registered canonical role is eligible, plus the canonical Guru wrapper paths `.claude/agents/guru.md` and `.codex/skills/wf-guru/SKILL.md`. Wrappers created during a render are reconciled again before that same render returns. Repo-local docs-contract and release reviewer docs are likewise existing/enabled-only. QA's canonical source is `239-qa-reviewer.prompt.md` → `docs/agents/qa-reviewer.md`; seed 209 remains the single full protocol/checklist.

## Canonical Factor Docs (`docs/agents/`)

| Canonical doc | Metadata / Group | Native wrapper |
|---------------|------------------|----------------|
| `docs/agents/factor-03-config.md` | `Role: factor-03-config`, `Category: factor` | `.claude/agents/factor-03-config.md` |
| `docs/agents/factor-05-build-release-run.md` | `Role: factor-05-build-release-run`, `Category: factor` | `.claude/agents/factor-05-build-release-run.md` |
| `docs/agents/factor-12-admin-processes.md` | `Role: factor-12-admin-processes`, `Category: factor` | `.claude/agents/factor-12-admin-processes.md` |
| `docs/agents/factor-13-api-first.md` | `Role: factor-13-api-first`, `Category: factor` | `.claude/agents/factor-13-api-first.md` |

The dashboard surfaces these as a separate `Factor` group, not as specialists.

## Claude Code Native Agents (`.claude/agents/`)

| File | Role / Factor |
|------|--------------|
| `.claude/agents/guru.md` | Guru — codebase and documentation Q&A (auto-delegated) |

## Generic Role Docs (`docs/agents/`)

All generic role docs are in `docs/agents/`. Agent docs carry `Category:` metadata for dashboard grouping; role-bearing docs also carry `Role:`. Native platform wrappers (`.claude/agents/<role>.md`, `.codex/skills/agent-role-<role>/`) are generated by `render_platform_surfaces.py` when enabled in `docs/workflow-config.json` `agent_platform_generation`. Currently not yet generated (deferred until MCP implementation begins).

## Specialist Role Docs (`docs/agents/specialists/`)

Specialist roles should be cataloged under `docs/agents/specialists/` and, when enabled, rendered to the same native wrapper locations as generic roles. Specialist docs carry `Category: specialist`. The framework taxonomy is:

- `universal specialist` — reusable across many projects
- `archetype specialist` — enabled from repo shape such as web/full-stack, mobile/desktop, AI/agent, JVM/service, or infrastructure-heavy repos
- `repo-local specialist` — specific to one project and preserved as a local extension

Wavefoundry currently tracks the specialist shortlist in `docs/agents/specialists/README.md` and treats wrapper generation for those roles as a follow-on platform-surface enhancement.

## Persona Agent Docs (`docs/agents/personas/`)

Persona docs carry `Category: operate`.

| File | Persona |
|------|---------|
| `docs/agents/personas/framework-operator.md` | Framework Operator |
| `docs/agents/personas/wave-coordinator.md` | Wave Coordinator (persona) |
