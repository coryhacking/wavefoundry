# 050 - Agent Entry Surface Bootstrap

Intent:

- Create or normalize root agent entry files and platform-native role surfaces so they point to canonical docs and generated role/persona guidance.

Canonical entry and wrapper targets:

- `AGENTS.md` as the canonical root map
- `CLAUDE.md`
- `.cursor/rules/project-context.mdc`
- `.junie/guidelines.md`
- `.github/copilot-instructions.md`
- `WARP.md`

Native role-wrapper examples when enabled:

- Claude: `.claude/agents/<role>.md`
- Codex: `.codex/skills/agent-role-<role>/SKILL.md`

Generated role and persona docs must preserve operating identity for software-engineering work. Each generated or refreshed role/persona surface should define:

- **Operating identity:** stance, priorities, judgment style, non-negotiables, success criteria, and what the actor is responsible for noticing.
- **Salience triggers:** job-specific signals that should cause the actor to stop and journal before context is lost, such as trust-risk, repeated friction, invalidated assumptions, hard-to-rediscover constraints, operator-signal, or confidence-shift.
- **Memory responsibilities:** which observations belong in the actor journal, which belong in handoff or active wave records, and which should be promoted to canonical docs.

Keep these sections concise and role-specific. Do not claim agents have emotions; operational salience records observed engineering impact.

Canonical role docs should also carry the following structural sharpness when the role type supports it:

- **Default stance:** the evidence posture the role starts from before it has proof otherwise.
- **Do not / anti-goals:** role boundaries that prevent overlap, silent redesign, or implicit scope expansion.
- **Output shape:** the expected structure of a good role output so downstream lanes know what to expect.
- **Review dimensions or evidence requirements:** when the role reviews work rather than authors it.
- **Assumption tracking:** what assumptions must be named, tested, or escalated before the role signs off.

Tasks:

1. Create or update `AGENTS.md` as the canonical entry map. Prefer concise, **non-obvious** routing and guardrails agents would otherwise get wrong; omit trivia they can re-derive from `docs/repo-index.md` or the tree.
2. Create or update thin pointer files such as:
 - `CLAUDE.md`
 - `.cursor/rules/project-context.mdc`
 - `.junie/guidelines.md`
 - `.github/copilot-instructions.md`
 - `WARP.md`
3. Ensure the entry surface routes users through the canonical change workflow and the public wave-context prompt surface.
4. Generate native role wrappers when enabled by repo-local config.
5. Generate factor-review agent files for each factor marked `applicable` in `docs/repo-profile.json` under `factor_review`. For each applicable factor, write `docs/agents/factor-<nn>-<name>.md` as the canonical source file (zero-padded two-digit number, kebab-case name matching the factor table in the framework README), then render native wrappers at the enabled platform locations, for example `.claude/agents/factor-<nn>-<name>.md`. Each file must include: what this factor covers, why it is applicable to this project (cite evidence from the repository), the review questions it asks when evaluating a wave, and whether its findings are gating or advisory for this project. The canonical factor file header must include `Role: factor-<nn>-<name>` and `Category: factor`. Do not generate files for `partial` or `not-applicable` factors. Record the generated canonical and wrapper paths in `docs/agents/platform-mapping.md` alongside the generic role agents.
6. Generate persona wrappers only when the repo-local config and platform settings allow them.
7. Ensure parent directories exist before writing wrappers.
8. Keep non-canonical entry files and native wrappers thin and mechanical.
9. When generating or refreshing canonical role/persona docs, add or preserve operating identity, `Role:` identity, `Category:` dashboard grouping, salience triggers, and memory responsibilities. Thin native wrappers should point to those canonical sections rather than duplicating them.
10. Support the canonical agent taxonomy in repo-local docs and wrappers: `generic`, `persona`, `factor-review`, `universal specialist`, `archetype specialist`, and `repo-local specialist`. For dashboard grouping, use `Category:` values from `build`, `review`, `coordinate`, `specialist`, `factor`, `operate`, `journal`, and `factors`; `Role:` remains the identity field. Only the first three are guaranteed in every seeded repository; specialist tiers are enabled from repo evidence and repo-local config. When the repository enables Wave Council in `docs/workflow-config.json`, treat `wave-council` as part of the canonical generic role set and ensure `reality-checker` is available as a universal specialist because it is a fixed council seat in the default framework template. `red-team` is a universal specialist whenever Wave Council is enabled — always generate the role doc from `seed-225` and ensure it is present and invokable, independent of how `fixed_seats` or `rotating_seat_policy` is configured.
11. Generate specialist wrappers only for roles that are enabled by repo-local evidence or operator configuration. Universal specialists are cross-project roles such as architecture, security, docs, and onboarding. Archetype specialists are keyed to repository shape, such as web/full-stack, mobile/desktop, AI/agent, JVM/service, or infrastructure-heavy repos. Repo-local specialists are project-specific and must stay clearly separated from reusable framework defaults.

    **Senior builder specialist lanes** (`software-engineer`, `frontend-developer`, `data-engineer`) are a distinct tier: they are primary implementation lanes, not advisory reviewers. Enable them when repository evidence supports the corresponding domain — backend/API/service code for `software-engineer`; UI component or interaction surfaces for `frontend-developer`; SQL-heavy schema/migration/ETL work for `data-engineer`. Each builder specialist role requires evidence-first stack detection before the first edit, has senior-level domain expectations, and is routable as an alternative to the generic `implementer` when the admitted change needs domain depth. When a `frontend-developer` lane is enabled, generate a `docs/agents/frontend-developer.md` wrapper (Category: build) that also points to the repository's `design_system_policy` governance setting in `docs/workflow-config.json` so the role knows which mutability mode applies. Similarly, generate `docs/agents/software-engineer.md` (Category: build) when backend/API/service evidence is present.
12. Update `.gitignore` so framework-managed platform files are tracked rather than silently excluded.
13. Add the framework script hygiene rule to `AGENTS.md` as a universal cross-agent instruction (see below).
14. Seed `.claude/settings.json` with the project-level Claude Code hook that automates the same rule for Claude Code (see below).
15. Prefer generating platform hook/config surfaces via `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` rather than hand-editing each hook file independently. Keep the repo-local hook files at the platform-expected paths, but treat them as generated Python entrypoints rendered from generic framework templates. Use a repo-global guard override file (`.wavefoundry/guard-overrides.json`) rather than provider-specific sentinel files for temporary seed/framework edit approval.
16. **Implementation principles** — Add an `## Implementation Principles` section to `AGENTS.md` after `## Core Principles` (or after the project's equivalent design-values section). Include these four principles verbatim:
    1. **Ask, don't assume.** If something is unclear, ask before writing a single line. Never make silent assumptions about intent, architecture, or requirements.
    2. **Simplest solution first.** Always implement the simplest thing that could work. Do not add abstractions or flexibility that weren't explicitly requested.
    3. **Don't touch unrelated code.** If a file or function is not directly part of the current task, do not modify it, even if you think it could be improved.
    4. **Flag uncertainty explicitly.** If you are not confident about an approach or technical detail, say so before proceeding. Confidence without certainty causes more damage than admitting a gap.
17. **Stage gate (repository code)** — Add a `## Stage Gate (repository code)` section to `AGENTS.md` before the Implementation guard. This gate applies to all repository code (product source, scripts, tests, build manifests, and other checked-in code/config that affects shipped or verified behavior). It must require all three of the following before the first code edit in a given effort: (1) a consolidated change document exists; (2) the change is admitted into a wave via `Create wave` / `Add change to wave`; (3) the wave has a successful `Prepare wave` / `Ready wave` pass as the immediately preceding lifecycle step. If any step is missing, agents must stop and route back to `Plan feature`, `Create wave`, `Add change to wave`, or `Prepare wave`. Mark documentation-only edits under `docs/`, prompt/framework docs that do not change repository code, and operator-approved explicit waivers for a named scope as out of scope for this gate.
18. **Change doc tracking (real-time)** — Add a `## Change Doc Tracking (Real-Time)` section to `AGENTS.md` after the Stage gate section. It must contain: "Mark task and AC checkboxes `[x]` as each item completes; update `Change Status` in the change doc and `wave.md` immediately — not at wave end."
19. **Implementation guard (product code)** — When the project ships product implementation source (present in the repository), add an `## Implementation guard (product code)` section to `AGENTS.md` immediately after the Stage gate section. Use the decision signals and template below. When the repo is documentation-only, specs-only, or contains only the wave framework pack with no shipped product code, omit the section or add a single line that the guard should be added once implementation directories exist.
20. **Codebase and documentation questions (auto-Guru)** — Add the `## Codebase and documentation questions (auto-Guru)` section and **Agent platform routing** subsection to `AGENTS.md` per the templates below (unconditional forward-looking pointer; tier 1 is hand-seeded or upgraded in place — not overwritten by the renderer). Run `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` (which calls `render_agent_surfaces.py`) when `docs/agents/guru.md` exists to materialize **tier 2** thin-pointer marker blocks and **tier 3** native surfaces (`.cursor/rules/auto-guru.mdc`, `.claude/agents/guru.md`, `.codex/skills/auto-guru/SKILL.md`). Re-run after upgrade or when auto-Guru templates change in the framework pack. Do not hand-edit generated marker regions between `waveframework:auto-guru begin` and `end` comments — change `render_agent_surfaces.py` instead. Junie, Air, Windsurf, Copilot, and Warp use the same tier-1 contract via `AGENTS.md` plus tier-2 bullets on their thin pointers when those files exist.
21. **Harness extension boundary** — `## Project harness extensions` is a rendered target-repository section that belongs only in `docs/agents/` output files, never in seed bodies. When an implementer adds a harness extension section to a seed body, it becomes part of every rendered target repo and must therefore remain fully generic. If the content requires project-specific examples or checks, place them only in the rendered `docs/agents/` output files.

**When to add the guard**

- `docs/repo-profile.json` `project_archetypes` includes shipped-software shapes such as `desktop_app`, `mobile_app`, `cli_tool`, `backend_service`, `embedded`, or similar; or
- `primary_languages` lists languages used for shipped binaries or runtime artifacts; or
- `docs/repo-index.md` (from inventory) documents top-level implementation modules, app targets, or packages.

**What the guard must require (repo-specific paths filled from `docs/repo-index.md`)**

- Before the first edit to **product implementation source** in a given effort: (1) a consolidated change document exists at `docs/plans/<change-id>.md` or `docs/waves/<wave-id>/<change-id>.md`, grounded in `docs/plans/plan-template.md`; (2) `Prepare wave` / `Ready wave` has passed cleanly for that wave as the immediately preceding lifecycle step before implementation.
- **Explicit waiver:** operator may waive in the current request for a named scope; record waiver in the change doc or `docs/agents/session-handoff.md`.
- List **product implementation source** as concrete roots from `docs/repo-index.md` (or a placeholder bullet: “Fill module roots from `docs/repo-index.md` after first inventory” if init runs before the index is detailed).

**Do not** place project-specific domain rules (example: dual grace maps for a particular vendor SDK) in this generic guard; those belong in `docs/specs/` and role docs after evidence exists.

The coordinator shortcut `seed-180` already references `AGENTS.md` for this policy; the section must exist when product code is present so that reference is actionable.

Required semantics:

- public prompt phrases and their local docs
- canonical docs routing
- generic role routing
- wave-council routing when Wave Council is enabled
- factor-review agent routing when applicable factors exist
- persona routing when personas exist
- specialist routing when repo evidence enables universal, archetype, or repo-local specialists
- auto-Guru routing for codebase and documentation Q&A (operators need not say **Guru**)
- sync policy for thin pointer files
- native wrapper locations and naming policy when enabled
- tracking policy for generated platform-native files

Implementation details to preserve:

- `AGENTS.md` should stay map-like and route work to canonical docs rather than duplicating deep policy
- thin pointer files should identify startup order and canonical sources, not restate project-specific operational guidance
- native wrappers should point back to canonical role or persona docs rather than duplicating policy
- wrapper naming should stay stable so upgrades can reconcile them safely

`.gitignore` remediation guidance:

- if `.cursor/`, `.codex/`, or `.claude/` are ignored broadly, replace those broad rules with scoped patterns that still track framework-managed files
- ensure the framework-managed wrapper directories are not silently excluded from version control
- do not modify unrelated ignore rules unnecessarily
- preserve repo-root ignore rules for framework distribution zip drops when already present (see **Framework distribution zip drops** below); add them when missing so dated packs and legacy aggregate zips stay out of commits
- `.claude/settings.json` is a committed project-level file and must not be gitignored
- `.claude/settings.local.json` is a personal override file and should be gitignored

## Framework Script Hygiene Rule

This rule must be present in `AGENTS.md` and any other agent entry files where a "development rules" or "workflow notes" section is appropriate. Add it once in a shared location rather than repeating it in every thin pointer file:

> The framework test suite (`scripts/tests/`, `scripts/run_tests.py`) is a development-only artifact that lives in the Wavefoundry source repository and is **not included in the distribution pack**. Downstream repositories that vendor the pack do not have these files and must not attempt to run them. `__pycache__` directories created by Python imports under `.wavefoundry/framework/scripts/` are gitignored and excluded from `docs-lint` (wave `1p35d` / `1p35n`) — no manual cleanup needed.

## Codebase and Documentation Questions (auto-Guru) in AGENTS.md

Add this section to `AGENTS.md` after **Start Here** (or immediately before **Purpose** / product boundary). Seed it unconditionally — it applies once `docs/agents/guru.md` exists (`seed-211`) and MCP search tools are expected; operators must not need to say **Guru** for code or documentation Q&A.

```markdown
## Codebase and documentation questions (auto-Guru)

Operators do **not** need to say **Guru** or **Ask codebase** for questions about how this repository's **code** or **documentation** works.

**Pre-flight question — ask this before responding to any user message:** *does answering this require reading code or documentation to understand what's there?* If yes, route to Guru. Surface forms vary infinitely ("how does X work", "tell me about X", "walk me through X", "I want to understand X", "where is X", "describe the Y flow"); intent does not. Apply the intent check on every message, not just messages that obviously match a phrase pattern.

When the answer is yes (or when the message is primarily about **understanding, locating, or explaining** source code or project docs — including architecture, specs, and content under `docs/`) and is **not** a wave lifecycle shortcut from `docs/prompts/index.md` (**Plan feature**, **Implement wave**, **Close wave**, etc.), adopt the **Guru** workflow:

1. Read and follow `docs/agents/guru.md` (question classification, retrieval loop, mechanism completeness, citations).
2. When MCP is available, use `code_ask(question)` for cross-cutting code questions and `docs_search` for documentation-heavy questions per Guru's classification table.
3. Complete Pass 3 validation (`code_outline`, targeted `code_read`, `code_keyword` as needed) before synthesizing — do not answer from memory or from the `code_ask` `answer` field alone.
4. When MCP is unavailable, follow Guru's **When MCP is Not Available** fallbacks in `docs/agents/guru.md`.

**Examples — anchoring the boundary (these are examples, NOT a keyword list to match against; the rule is the pre-flight question above):**

| Example user question | Route to Guru? | Reason |
| --- | --- | --- |
| "How does authentication work?" | Yes | Explicit how-question; answer comes from reading auth code. |
| "Tell me about the way authentication works" | Yes | Semantic intent = "how does it work"; surface form doesn't match keyword patterns but the answer still comes from reading auth code. |
| "Walk me through the request flow" | Yes | Code investigation; answer comes from reading routing/middleware code. |
| "I want to understand session management" | Yes | Code investigation; answer comes from reading session code. |
| "What's the structure of the API layer?" | Yes | Architecture question; answer comes from reading code + docs. |
| "Where is the rate limiter defined?" | Yes | Code-location question; answer comes from code search. |
| "Explain how config loading works" | Yes | Explanation question; answer comes from reading config code. |
| "Describe the data flow from request to response" | Yes | Flow question; answer comes from reading code. |
| "Rename `getUserId` to `resolveUserId`" | No | Operational; the agent does the rename, no code-understanding required to answer. |
| "Delete the old session config" | No | Operational. |
| "Run the test suite" | No | Operational. |
| "What's the value of `MAX_RETRIES` in this file?" | No | Trivial lookup; targeted read suffices, no investigation needed. |

**Retrieval-intent backstop — late-detect signal:** if you find yourself about to call `code_search`, `code_keyword`, `code_read`, `code_definition`, `code_outline`, `code_callhierarchy`, `code_references`, or `code_pattern` in service of a user question, **stop**. That retrieval IS Guru's job. Route to Guru instead of doing the retrieval yourself. The tool reach-for catches misses the pre-flight skipped.

Explicit shortcut **Guru** remains available in `docs/prompts/index.md` when the operator wants to name the mode.
```

**Cursor thin pointer** (`.cursor/rules/project-context.mdc`) — one line under startup or guardrails: `Follow \`.cursor/rules/auto-guru.mdc\` for code and documentation Q&A.` (full workflow lives in that always-on rule file.)

**All thin pointers** — seed the same one-line guardrail on every host entry file the project uses (`CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, `.github/copilot-instructions.md`, `WARP.md`, and any other pointer from task 2). Do not duplicate the full workflow:

`- Code and documentation Q&A: follow **Codebase and documentation questions (auto-Guru)** in \`AGENTS.md\` and \`docs/agents/guru.md\`; use Wavefoundry MCP (\`code_ask\`, \`docs_search\`) when attached; do not answer from memory alone.`

**Instruction-only hosts** (Codex without skills, Junie, Air, Warp, and any host without rules/subagents/skills) rely on tier 1 + tier 2 only — no extra files required.

### Auto-Guru routing by agent capability

When `docs/agents/guru.md` exists (`seed-211`), record routing in `docs/agents/platform-mapping.md` and run **`render_agent_surfaces.py`** (via `render_platform_surfaces.py`) to populate tier 2–3 files. Source of truth for generated bodies: `.wavefoundry/framework/scripts/render_agent_surfaces.py`. Operators must not need to say **Guru** for code or documentation Q&A on **any** host.

**Tier 1 (all hosts):** `AGENTS.md` § **Codebase and documentation questions (auto-Guru)** + `docs/agents/guru.md`.

**Tier 2 (all seeded thin pointers):** one guardrail bullet (see above) in each host entry file.

**Tier 3 (optional native — only when the host supports it):** the surfaces below **reinforce** tier 1; they do not replace it. Skip tier 3 for hosts that have no equivalent (Junie, Air, Warp, Windsurf, Copilot use tier 1–2 plus MCP when configured).

**Cursor** (optional) — `.cursor/rules/auto-guru.mdc` (`alwaysApply: true`):

```markdown
---
description: Auto-route code and documentation questions to Guru (code_ask, docs_search, validated reads)
globs: ["**/*"]
alwaysApply: true
---

# Auto-Guru (Cursor — optional native surface)

Canonical rules: \`AGENTS.md\` auto-Guru section + \`docs/agents/guru.md\`. Applies unless the user invokes a wave lifecycle command from \`docs/prompts/index.md\`.

When the user asks to understand, locate, or explain source code or project docs:

1. Read \`AGENTS.md\` § **Codebase and documentation questions (auto-Guru)** and \`docs/agents/guru.md\`.
2. Call Wavefoundry MCP \`code_ask\` / \`docs_search\` (see \`.cursor/mcp.json\`).
3. Complete Guru Pass 3 before answering.
4. Prefer MCP over raw grep for orientation; use a read-only subagent for large investigations.
```

**Claude Code** (optional) — `.claude/agents/guru.md` (subagent; `description` must include **PROACTIVELY** so Claude delegates code/doc questions):

```markdown
---
name: guru
description: PROACTIVELY use when the user asks how this repository's source code or project documentation works. Do not use for wave lifecycle commands (Plan feature, Implement wave, Close wave, etc.).
tools: Read, Grep, Glob, Bash
model: sonnet
---

# Guru (Claude Code subagent — optional native surface)

Canonical role for all hosts: \`docs/agents/guru.md\` + \`AGENTS.md\` auto-Guru section. Use wavefoundry MCP when attached. Read-only here — architecture writes stay in the main session.
```

`CLAUDE.md` must tell the main agent to delegate large code/doc investigations to the **guru** subagent and to use `.mcp.json` for MCP.

**Codex** (optional) — `.codex/skills/auto-guru/SKILL.md`:

```markdown
---
name: auto-guru
description: PROACTIVELY use when the user asks how repository source code or project documentation works. Not for wave lifecycle commands.
---

Read \`AGENTS.md\` auto-Guru section and \`docs/agents/guru.md\`. Use \`code_ask\` / \`docs_search\`; complete Pass 3 before answering.
```

Ensure `.gitignore` does not exclude `.codex/skills/` (track project skills like other framework-managed platform files).

**Windsurf, Copilot, Junie, Air, Warp** — no tier-3 file required. Seed tier 1 in `AGENTS.md` and tier 2 in the host thin pointer; attach MCP per `AGENTS.md` when the operator uses that host. Windsurf/Copilot may also use existing hook surfaces from this seed — hooks enforce edit gates, not Guru routing.

Add to `AGENTS.md` auto-Guru section an **Agent platform routing** subsection: three tiers above, optional native table (Cursor / Claude / Codex), and a row that tier 1–2 suffice for all other hosts.

## Hook Contract

Use `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` to materialize tracked hook entrypoints and merged settings files for every enabled platform. For each entrypoint the renderer writes three variants — a self-contained Python implementation (`<name>.py`), a POSIX launcher (`<name>`), and a Windows launcher (`<name>.cmd`) — all `chmod +x`. The JSON snippets below show POSIX launcher command values; on Windows the renderer emits the corresponding `cmd.exe /c ...\\.cmd` invocation. Prefer `render_platform_surfaces.py` over hand-editing each hook file independently (see task 13).

### Shared hook policy (all platforms)

- **Canonical guard override file** — use exactly this repo-global schema at `.wavefoundry/guard-overrides.json` for temporary approvals; do not introduce provider-specific sentinel files:
```json
{
 "framework_edit_allowed": { "enabled": false },
 "seed_edit_allowed": { "enabled": false }
}
```
- **Canonical ignore rule** — keep this exact rule in `.gitignore` so Wavefoundry's local approval state is never committed:
```gitignore
.wavefoundry/guard-overrides.json
```
Preserve the personal-override carve-out (the framework tree can be tracked, but the override file itself stays uncommitted):
```gitignore
.wavefoundry/guard-overrides.json
```
- **Framework distribution zip drops (do not commit)** — the version-controlled pack is the unpacked tree under `.wavefoundry/framework/` (including sources consumed by `scripts/build_pack.py`). Zip archives at the repository root such as `wavefoundry-*.zip` are for local unpack or transport only; **never commit them**. If a repository still tracks an older zip, remove it from the index (`git rm --cached <file>.zip`) and rely on ignore rules. When the following anchored block is missing from `.gitignore`, add it (leading `/` limits matches to repository root):
```gitignore
# Wavefoundry framework pack archives (tracked source lives under .wavefoundry/framework/; do not commit zip drops)
/wavefoundry-*.zip
```
- **Wavefoundry runtime files (never commit)** — the framework writes per-machine runtime files on every dashboard start and during upgrade. They are regenerated on each run (same class as the semantic indexes) and must be gitignored so they do not appear dirty or get committed accidentally. When the following block is missing from `.gitignore`, add it:
```gitignore
# Wavefoundry runtime state files (host-local — never commit)
.wavefoundry/dashboard-server.json
.wavefoundry/upgrade-in-progress.json

# Wavefoundry runtime lock files (host-local process/test locks — never commit)
.wavefoundry/**/*.lock

# Wavefoundry runtime logs — all logs consolidated here (upgrade, index build, dashboard)
.wavefoundry/logs/

# Wavefoundry semantic index (binary + per-machine, never commit)
.wavefoundry/index/
.wavefoundry/framework/index/
```
If any of these files are already tracked (e.g. `dashboard-server.json` committed before this rule existed), untrack them without deleting them: `git rm --cached .wavefoundry/dashboard-server.json` (repeat for each tracked file). A gitignored file that remains tracked continues to appear dirty in `git status` and will churn live pid/port/url into history on every dashboard restart until it is removed from the index.
- **Operator-owned `git commit` (policy, not hooks)** — document in `AGENTS.md` and `docs/contributing/build-and-verification.md` that **agents must not** run `git commit` unless the operator explicitly instructs them to finalize that commit in the **current** request after review; default is to hand off a suggested message and diff for the operator to commit locally. The policy must also say that agents do **not** infer commit approval from broad phrases like "go ahead", "ship it", or "commit the changes": before any commit, the agent must present or confirm the exact commit scope and receive a clear finalization instruction for that reviewed scope. Do not rely on shell hooks or env-var bypasses for this — keep it as explicit workflow policy.
- **Project-specific post-edit checks** — when a repository needs additional formatter or validator hooks beyond the generic docs gate, define and render those as repo-local adaptations rather than hard-coding project paths into the shared framework.

### Wavefoundry MCP — docs gate for agents

Seeded **`AGENTS.md`**, **`CLAUDE.md`**, thin pointers, and **`docs/prompts/*`** must instruct **agents** to prefer MCP **`wave_validate`** (docs lint results), **`wave_garden`** (metadata gardening; follow the tool `mode` contract), and **`wave_audit`** (combined wave + validation + index readout) over shelling out to **`.wavefoundry/bin/docs-lint`** / **`.wavefoundry/bin/docs-gardener`**. Treat the **bin** launchers as **CLI / hook / CI** fallbacks when MCP is not attached. Hooks below **cannot** call MCP and therefore still invoke **`.wavefoundry/bin/docs-lint`** — that does not change MCP-first agent guidance.

This MCP-first principle extends beyond docs validation to **all wave and plan state queries**: before reaching for `ls`, `grep`, or filesystem tools to answer any question about wave state, plans, or change docs, agents must check the MCP tool list first. `wave_list_plans` (pending changes not yet admitted to a wave), `wave_list_waves`, `wave_current`, and `wave_get_change` return structured answers directly. Seeded `AGENTS.md` must include this guidance in its MCP or docs-gate section.

The same principle applies to **literal-identifier and cross-surface text sweeps across docs, config, and prompts** — not only source-code navigation. `code_keyword` and `code_pattern` index every repository file (markdown, JSON, TOML, config, prompts), and `docs_search` covers documentation; reach for them before `grep`/`rg` when reconciling renamed identifiers across docs + config (role renames, config-key renames during upgrade — the highest-drift-risk sweeps). Shell text search remains correct for operations the index cannot answer: git inspection (`git status`/`diff`/`log`), exact byte-level file-state checks, and key-presence verification in config files. Record a `Gapfill:` note when shell was used for a sweep MCP could have answered, per the implementer rule below.

### Shared hook purposes (apply on every host per its pre/post capability)

- **Seed protection** — block (or warn+halt where pre-write is unavailable) edits to `*.prompt.md` files under `.wavefoundry/framework/` unless `.wavefoundry/guard-overrides.json` sets `seed_edit_allowed.enabled` to `true`. Use the repo-global override file only for intentional seed edits, then remove it or set the flag back to `false`.
- **Framework plan gate** — block (or warn+halt) broad framework-maintenance edits to `.wavefoundry/framework/`, `docs/prompts/`, `AGENTS.md`, and tracked hook configs unless `.wavefoundry/guard-overrides.json` sets `framework_edit_allowed.enabled` to `true` after the operator reviews the file-level patch plan.
- **`docs-lint` hook** — run **`.wavefoundry/bin/docs-lint`** after any Edit/Write to files under `docs/`, failing the hook when the docs gate fails (subprocess hook path; not MCP).

### Per-platform capability matrix

| Tool or Host | Pre-write block | Post-write validation | Config file |
|--------------|------------------------------------------------------|---------------------------------------------------------|--------------------------------------------------------------------|
| Claude Code | ✅ `PreToolUse` seed protection + framework plan gate | ✅ `PostToolUse` `docs-lint` | `.claude/settings.json` |
| Cursor | ⚠️ `afterFileEdit` warn+halt (write already landed) | ✅ `afterFileEdit` `docs-lint` | `.cursor/hooks.json` |
| Windsurf | ✅ `pre_write_code` true blocking (exit code 2) | ✅ `post_write_code` `docs-lint` | `.windsurf/hooks.json` |
| Copilot | ✅ `preToolUse` seed + framework approval | ✅ `postToolUse` `docs-lint` | `.github/hooks/hooks.json` |
| Codex | ❌ instruction-only | ❌ | `AGENTS.md`, `docs/prompts/`, `.codex/skills/auto-guru/SKILL.md` |
| Air | ❌ hosted-provider only | ❌ hosted-provider only | existing provider wrappers only |
| Junie | ❌ instruction-only (`AGENTS.md`, `.junie/guidelines.md`) | ❌ | `.junie/guidelines.md` |
| Warp | ❌ instruction-only | ❌ | `WARP.md` |

For Codex, Air, Junie, and Warp, reinforce rules in `AGENTS.md` and the respective thin-pointer or native-wrapper files only.

### Claude Code

Seed or update `.claude/settings.json` with the hooks below. **Merge with any existing hooks — do not replace the entire file.** `.claude/settings.json` is not read by Cursor, Codex, Windsurf, or other tools, so the behavioral rules must also be present in `AGENTS.md`, `CLAUDE.md`, and other platform thin-pointer files.

```json
{
 "hooks": {
 "PreToolUse": [ { "matcher": "Edit|Write", "hooks": [ { "type": "command", "command": ".claude/hooks/pre-edit", "statusMessage": "Checking framework edit gates..." } ] } ],
 "PostToolUse": [
 { "matcher": "Edit|Write", "hooks": [ { "type": "command", "command": ".claude/hooks/post-edit", "statusMessage": "Running docs gates..." } ] }
 ]
 }
}
```

Generated entrypoints (three variants each: `.py`, POSIX launcher, `.cmd`):
- `.claude/hooks/pre-edit` — seed protection + framework plan gate
- `.claude/hooks/post-edit` — `docs-lint`
- `.claude/hooks/simulate-hooks` — local test harness for the above

`.gitignore` tracks `.claude/skills/` and `.claude/hooks/` (for reusable operator skills and generated hook entrypoints). `.claude/settings.json` is a committed project-level file and must not be gitignored; `.claude/settings.local.json` is a personal override and should be gitignored.

### Cursor

Cursor has **no pre-write event** — the earliest file-edit hook is `afterFileEdit`, which fires after the write has already landed. Seed protection is therefore warning-and-halt rather than true blocking; outputting `{"continue": false, ...}` to stdout stops the agent loop after the edit.

```json
{
 "version": 1,
 "hooks": {
 "afterFileEdit": [ { "command": ".cursor/hooks/after-file-edit" } ]
 }
}
```

Generated entrypoints:
- `.cursor/hooks/after-file-edit` — runs Cursor gates in order and stops after the first blocking result
- `.cursor/hooks/seed-warn` — seed-protection warn+halt
- `.cursor/hooks/framework-plan-warn` — framework-plan-gate warn+halt
- `.cursor/hooks/docs-lint` — runs `.wavefoundry/bin/docs-lint` after docs edits and halts with actionable output when the docs gate fails

`.gitignore` must track `.cursor/hooks.json` and `.cursor/hooks/` (`!.cursor/hooks.json` and `!.cursor/hooks/` carve-outs when `.cursor/` is broadly ignored). The repo-global `.wavefoundry/guard-overrides.json` override file remains gitignored.

### Windsurf (Codeium Cascade)

Windsurf has `pre_write_code` which fires **before** the write — true blocking via exit code 2.

```json
{
 "hooks": {
 "pre_write_code": [ { "command": ".windsurf/hooks/seed-protect", "show_output": true } ],
 "post_write_code": [ { "command": ".windsurf/hooks/docs-lint", "show_output": true } ]
 }
}
```

Generated entrypoints:
- `.windsurf/hooks/seed-protect` — true-blocking seed protection + framework plan gate
- `.windsurf/hooks/docs-lint` — runs `.wavefoundry/bin/docs-lint` after docs edits

`.gitignore` tracks `.windsurf/hooks.json` and `.windsurf/hooks/`.

### GitHub Copilot (coding agent)

Use repository-tracked generated Python entrypoints for both blocking and post-edit validation so the gate logic stays reviewable and cross-platform.

Scope boundary:
- The framework may manage `.github/hooks/` for Copilot agent enforcement.
- The framework must **not** create or modify `.github/workflows/` GitHub Actions files as part of hook rendering.
- The framework must **not** create or modify local git hook scripts under `.git/hooks/`.

```json
{
 "version": 1,
 "hooks": {
 "preToolUse": [ { "type": "command", "bash": ".github/hooks/pre-tool-use" } ],
 "postToolUse": [ { "type": "command", "bash": ".github/hooks/post-tool-use" } ]
 }
}
```

Generated entrypoints:
- `.github/hooks/pre-tool-use` — blocks seed-prompt edits and broad framework-maintenance edits per the guard-override file
- `.github/hooks/post-tool-use` — runs `.wavefoundry/bin/docs-lint` after docs edits

Keep `.github/copilot-instructions.md` as a thin pointer and route mechanical enforcement through `.github/hooks/hooks.json`.

## Junie

Junie does not ship the same hook surfaces as Cursor or Copilot. Rely on `AGENTS.md` and `.junie/guidelines.md` for seed and framework edit discipline (`seed_edit_allowed`, stage gate).

Do **not** add `.wavefoundry/framework/seeds/*.prompt.md` to `.aiignore` for Junie: in hosts that enforce `.aiignore`, that pattern blocks **reads** as well as writes, which hides canonical seeds from agents. The install renderer seeds `.aiignore` with **index directories only** (see `render_aiignore`).

## Per-Role Authoritative Seeds

When generating per-role docs at `docs/agents/<role>.md` and `docs/agents/specialists/<role>.md`, **read the authoritative per-role seed in full and incorporate its operating identity, responsibilities, modes, output shape, and salience triggers**. Generating a thin generic template from seed-050's structural fields alone produces shallower content than the role's authoritative seed carries.

Authoritative per-role seed pointers:

- `seed-214` — architecture-reviewer
- `seed-215` — wave-council (framework-default council coordinator)
- `seed-216` — reality-checker (fixed Wave Council seat)
- `seed-221` — code-reviewer
- `seed-222` — software-engineer
- `seed-223` — frontend-developer (when UI surface present)
- `seed-224` — data-engineer (when database/ETL present)
- `seed-225` — red-team (universal challenger + Wave Council Phase 1 primer)
- `seed-236` — archetype-council (operator-invoked Archetype Council)

**The three councils are always surfaced as specialist agents.** Canonical fresh-install location is `docs/agents/specialists/` (shown below); established repos with a flat `docs/agents/` layout may keep their existing location — `docs-lint` accepts either. The presence of all three role docs is load-bearing for council invocation; the directory they live in is a convention, not an enforced contract:

- `red-team.md` — read `seed-225` in full
- `wave-council.md` — read `seed-215` in full
- `archetype-council.md` — read `seed-236` in full

Generating thin generic templates for these three misses the framework's intent. Pull from the authoritative seeds; preserve protocol details, seat composition, swap-in lists, and the broader-scope framing (Archetype Council applies to plans, design docs, code, prose, decision narratives, naming, AC formulation — NOT text-only).

## `docs/agents/platform-mapping.md` — Availability Matrix

`docs/agents/platform-mapping.md` is the availability matrix the framework consults for "who can be invoked on this project." It is not a stub of intent; it is a record of fact. Its content must reflect on-disk state at the moment it is written.

**Write timing.** Write `platform-mapping.md` **after** the canonical role docs and native wrappers have been written to disk in this seed's run (the generic role docs, factor-review docs when applicable, and any universal/archetype specialist docs the install configuration enables). Persona rows are appended later by `seed-120` (which owns persona synthesis). Writing the mapping table before the underlying docs exist produces a file that claims roles are available when they are not.

**Pending-bootstrap stub.** If for any reason this seed must write `platform-mapping.md` before any per-role docs exist on disk (rare — e.g., a partial install that creates the file ahead of role-doc generation, or an upgrade harness that pre-touches the file), write the following stub instead of the normal mapping table:

```markdown
# Agent Platform Mapping

Owner: Engineering
Status: pending
Last verified: <YYYY-MM-DD>

> **Pending agent surface bootstrap.** No per-role docs exist on disk yet. Run **Init agent surfaces** (seed-050) to generate them; this file becomes the availability matrix once roles exist.
```

An unconditional "all roles available" stub is factually wrong before role docs exist, hides the missing-seed-050 failure mode behind a misleading availability claim, and was a documented retrospective failure (wave `1p35d` / `1p35l`). The conditional shape lets `wave_install_audit` and the dashboard report honest state.

## Canonical Agent Doc Structure

Agent docs in `docs/agents/` are rendered directly in the dashboard — write them for human readability, not just machine parsing. The dashboard renders the full document body with markdown formatting (headings, bold, bullet lists). Authors should treat `## Operating Identity` and `## Responsibilities` as the primary human-facing sections.

### Required Metadata Fields

Every agent role doc in `docs/agents/` must include the following metadata fields in the header block (after the H1 title, before the first H2 section):

```
Owner: <team or owner name>
Status: active
Role: <role-slug matching the filename without .md>
Category: <build|review|coordinate|specialist|factor|operate|journal|factors>
Last verified: <YYYY-MM-DD>
```

> **Every generated role doc MUST include `Role: <role-slug>` in the header.**
> The dashboard classifies agents by this field; a doc missing `Role:` is **invisible** — it does not appear in the Agents panel, does not count toward role coverage, and is silently skipped without warning. `docs-lint` enforces this on every `docs/agents/*.md` file (`wave-1p35d` / `1p35l`); the `wave_install_audit` MCP tool surfaces lint failures so the gap fails fast at install time rather than at first dashboard load.

`Role:` is the inclusion gate that tells the dashboard this file is an agent role doc. Files without `Role:` (e.g. `session-handoff.md`, `platform-mapping.md`, `README.md`) are not role docs and will be excluded from the Agents panel. The `Role:` value must match the filename slug (e.g. `Role: code-reviewer` for `code-reviewer.md`). `Category:` is the separate dashboard grouping field; use it to control which bucket the dashboard renders without reusing `Role:` for presentation.

### Canonical H2 Headings and Section Order

Use the following heading strings exactly. Only include sections relevant to the role — omit sections that do not apply rather than leaving them empty.

**Preferred section order:**

1. `## Operating Identity` — 2–5 sentences describing the role's stance, priorities, and what success looks like. Do not duplicate content already in `AGENTS.md` or `020-run-contract`.
2. `## Responsibilities` — what the role owns and does
3. `## Salience Triggers` — signals that should cause the agent to stop and journal
4. `## Default Stance` — how the role approaches uncertainty or conflict
5. `## Review Dimensions` / `## Evidence Requirements` — reviewer roles only
6. `## Output Shape` — what the role produces
7. `## Do Not` — explicit guardrails
8. `## Assumption Tracking` — how the role surfaces and records assumptions
9. `## Memory Responsibilities` — what the role must capture in its journal
10. `## Execution Contract` — role-relevant subset of run-contract rules (see section below)

**Role-type applicability:**

| Section | Generic roles | Reviewer roles | Coordinator roles |
|---|---|---|---|
| Operating Identity | required | required | required |
| Responsibilities | required | required | required |
| Salience Triggers | required | required | required |
| Review Dimensions / Evidence Requirements | — | required | — |
| Execution Contract | required | not required | required |
| Others | as applicable | as applicable | as applicable |

**Specialist roles** (defined in `docs/agents/specialists/`) follow their own domain-appropriate heading conventions. The canonical section order above applies to generic framework roles; do not impose it on specialist role docs.

### Authoring Best Practices

- **Focus and length:** Agent docs should be scannable. `## Operating Identity` must not exceed 5 sentences — if it is longer, trim to the core stance and move details to `## Responsibilities`.
- **Non-duplication:** Do not repeat content from `AGENTS.md` or `020-run-contract`. The Execution Contract section should contain only the role-relevant subset of run-contract rules, not all six rules.
- **Dashboard awareness:** The dashboard renders the full agent doc. Write identity and responsibilities sections as if a human reader will see them directly in the UI — avoid internal shorthand or implementation references that only make sense in code context.
- **Evidence-based salience triggers:** Salience triggers must be operational impact signals, not emotional states. Ground them in the role's specific workflows and failure modes.

## Execution Contract in Canonical Role Docs

When canonical role docs exist under `docs/agents/`, ensure each active role doc includes an **Execution contract** section with the role-relevant subset of rules from `.wavefoundry/framework/seeds/020-run-contract.prompt.md`. Backfill when missing on init or upgrade.

Role-subset mapping:

- **`implementer.md`** — execution-discipline rules: in brownfield repositories, detect dominant patterns in the relevant scope (naming, error handling, abstraction depth, argument ordering, test structure, module organization) and follow them — surface significant pattern problems with rationale and wait for operator approval before deviating; state current behavior and why the change is needed before making it; prefer the smallest correct change; when stuck, diagnose and explain before switching approaches; after making changes, reason through whether they actually address the stated problem.
- **`planner.md`** — reasoning-depth rules: planning requests are complex-tier by default (the planner role does not handle lightweight tasks); reason step-by-step, surface tradeoffs, and provide comprehensive analysis; surface assumptions explicitly; when multiple approaches exist, compare them; prefer one precise clarifying question over proceeding on a wrong assumption.
- **`wave-coordinator.md`** — full contract for coordination: coordinator decisions span planning and execution, so apply the same reasoning depth as complex-tier work in `020` — evaluate the admitted change set, dependencies, and lane interactions step-by-step (do not shortcut evaluation); surface assumptions explicitly; state current wave state and rationale before changing readiness, allocation, or closure posture; when blocked or uncertain, diagnose and explain before switching approaches; prefer one precise clarifying question over proceeding on a wrong assumption about scope; verify the execution state matches the plan before declaring a coordination phase done.
- **Reviewer roles** (`code-reviewer`, `qa-reviewer`, `architecture-reviewer`, `security-reviewer`, etc.) — no Execution contract section required; reviewer output contracts already govern their outputs.

The Execution contract section belongs near the end of the role doc, after Responsibilities or Guardrails. Do not copy all six rules to every role doc — use the subset above so each role doc remains focused and non-redundant with `020`.

## MCP Tools / Guru Orientation Section in Canonical Role Docs

Ensure each of the following role docs includes an **MCP tools** section (or **Codebase orientation** section) that references the Guru as the first-stop tool before reading files, writing plans, or making code decisions. Seed this section unconditionally — Guru guidance is a forward-looking pointer that is valid once MCP is enabled, and having it present from the first init is better than requiring a follow-on upgrade. Place this section near the top of the role doc, after the role overview and before Responsibilities.

MCP is not active at init time — it is registered separately via **Enable Wavefoundry MCP** after the framework is seeded. The role doc section should reflect this by framing the tools as available once MCP is set up, e.g. "When the Wavefoundry MCP server is available, use these tools as your first orientation pass before reading files."

To reduce tool-schema friction that causes agents to default to shell exploration over MCP navigation: when the host supports it, register Wavefoundry MCP tools at repository init time via `render_platform_surfaces.py` rather than relying on on-demand schema loading. Pre-registration ensures the full MCP tool list is available at the start of every session, removing the path-of-least-resistance advantage that makes `grep`/`rg` the habitual first choice.

- **`implementer.md`** — Before writing or modifying code, use `code_search(topic, kind="code-summary", max_per_file=1)` when the owning file or symbol is not known yet, then use `code_definition(symbol)` to confirm whether the target already exists, `code_references(symbol)` to find all call sites, and `code_keyword(pattern)` to find similar implementations. If `code_references` is noisy, rerun it with `exclude_tests=true`; inspect `detail_buckets` / `detail_counts` when you need to separate definitions, imports, mentions, and the `reads` bucket (the functions that read a **constant's** value — wave `1p4hi` made module-/type-level constant values retrievable via `code_ask`/`code_search`/`code_definition`). Follow `docs/agents/guru.md` **Implementer guidance** for the standard pre-implementation orientation pass. When MCP is available, `rg`, `grep`, and broad file reads are **fallback tools only** — not first-choice exploration for questions `code_ask`, `code_search`, `code_definition`, `code_references`, or `code_keyword` are built to answer. Fallback is permitted when MCP is not attached, the relevant tool is unavailable in the host session, index health makes results unreliable, or MCP results are genuinely insufficient after a reasonable pass. Record a `Gapfill:` note when fallback was required so repeated tool friction becomes visible.

- **`planner.md`** — Before drafting a change doc, run a `code_search(topic, kind="code-summary", max_per_file=1)` module inventory and `code_ask("how does X currently work?")` to ground the rationale and affected-architecture sections in indexed evidence. When the subject symbol is already known, use `code_definition(symbol)` and `code_references(symbol)` to confirm exact declarations and usages, including SQL where structural support is available. Follow `docs/agents/guru.md` **Planner guidance** for the standard pre-planning orientation pass. When MCP is available, prefer `code_ask` and `code_search` over `grep`/`rg` for module discovery and codebase questions; shell search is a fallback path, not the default.

- **`wave-coordinator.md`** — During scope assessment and readiness review, use `code_ask` and `code_search(topic, kind="code-summary", max_per_file=1)` to answer "what does X currently do?" and "which files are affected?" without launching full file reads. When the relevant symbol is already known, switch to `code_definition(symbol)` or `code_references(symbol)` before broad file reads. If you are validating call-site signal, remember that `exclude_tests=true` is available for quieter reads without losing the broad mode. `code_dependencies(path)` is the fastest path to understanding what a changed file touches. When MCP is available, shell search and broad file reads are fallback tools only — use them when MCP is not attached, results are unavailable, or genuinely insufficient. The MCP-first code navigation obligation applies during coordination as well as implementation; do not default to shell exploration for questions MCP tools are designed to answer.

When role docs for persona agents exist under `docs/agents/personas/`, add the same orientation guidance — persona agents should ground answers to user questions in `code_ask` / `docs_search` results, not memory recall. Reference `docs/agents/guru.md` **Persona guidance**.

**Guru journal:** When seeding the Guru agent surface, also create `docs/agents/journals/guru.md` if it does not already exist. Use the same journal contract as other role journals (Operating Identity, Salience Triggers, Distillation, Active Signals, Index Gaps, Promotion Evidence, Retirement, Governance). The Guru journal is the recording surface for durable discoveries, index gaps, edge cases, and operator Q&A answers. Seed it with Guru's operating identity and salience triggers from `docs/agents/guru.md` (or `seed-211`).

## Cleanup and Destructive Operations

Add a `## Cleanup and Destructive Operations` section to `AGENTS.md` when the repository contains installed artifacts (shipped binaries, installed apps) or legacy content that could be confused with live working docs:

> **Historical reference preservation:** During legacy cleanup, only remove live working docs and deprecated prompt/wrapper files that have valid replacements. Do not delete mentions of removed artifacts from changelogs, wave records, closed-wave archives, release notes, or historical documentation. Retiring a file removes the file — not the historical record of it.
>
> **Destructive operations outside the repo:** Before overwriting or replacing an installed artifact outside the repository (for example, an app bundle in `/Applications`), confirm the target, verify a rollback path exists, and build to a staging location first. A distribution build that clobbers a working installation without a backup is not recoverable from the repository alone.
>
> **Legacy cleanup scoping:** When asked to clean up legacy content, default to removing only the explicitly named deprecated artifacts. Do not expand scope to adjacent historical records, prior wave archives, or references in closed-wave docs without explicit instruction.

## Design-System Extraction Guidance in AGENTS.md

When `docs/design-system/` exists in the target repository (or when `seed-040` task 14 has been applied), add the following guidance to the `AGENTS.md` **Docs Map** or equivalent section so agents can locate the extraction contract:

> **`docs/design-system/`** — machine-readable design system extraction contract (tokens, component specs, gap log, source map). Distinct from `docs/design-system/design-language.md`, which is the operator-owned narrative design document.
>
> - Regeneration regenerates JSON/spec trees (e.g. `manifest.json`, `tokens/`, `components/`). It **never** rewrites `design-language.md` or `index.md` body content.
> - `docs/design-system/AGENTS.md` contains agent rules for this subtree — check it before building UI components or writing hard-coded values.
> - `docs/design-system/proposed-additions.md` is the escape valve for new component proposals before they are formally added.
> - **Split B subtrees** (`patterns/`, `state-patterns/`, `validation-patterns/`, `content/`, `skills/`) — extend the core contract with pattern guidance, state definitions, validation conventions, voice/tone, and agent-facing skills. Consult these when implementing UI patterns, form validation, content copy, or building new agent design tasks. Present only when Split B has been applied.

This entry must be present whenever `docs/design-system/` is seeded or detected. Keep it concise and route to `docs/design-system/AGENTS.md` for the full agent rules rather than duplicating them.

Guardrails:

- Keep non-canonical entry files thin.
- Do not duplicate deep policy in multiple places.
- Edit project role or persona policy in canonical docs under `docs/agents/`, not thin wrappers.
- Do not generate platform-native wrappers for platforms that are not enabled in repo-local config.
- When seeding `.claude/settings.json`, merge into the existing file rather than replacing it.
