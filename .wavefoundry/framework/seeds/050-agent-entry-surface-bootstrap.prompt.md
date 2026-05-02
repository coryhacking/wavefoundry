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
5. Generate factor-review agent files for each factor marked `applicable` in `docs/repo-profile.json` under `factor_review`. For each applicable factor, write `.claude/agents/factor-<nn>-<name>.md` (zero-padded two-digit number, kebab-case name matching the factor table in the framework README). Each file must include: what this factor covers, why it is applicable to this project (cite evidence from the repository), the review questions it asks when evaluating a wave, and whether its findings are gating or advisory for this project. Do not generate files for `partial` or `not-applicable` factors. Record the generated agent paths in `docs/agents/platform-mapping.md` alongside the generic role agents.
6. Generate persona wrappers only when the repo-local config and platform settings allow them.
7. Ensure parent directories exist before writing wrappers.
8. Keep non-canonical entry files and native wrappers thin and mechanical.
9. When generating or refreshing canonical role/persona docs, add or preserve operating identity, salience triggers, and memory responsibilities. Thin native wrappers should point to those canonical sections rather than duplicating them.
10. Support the canonical agent taxonomy in repo-local docs and wrappers: `generic`, `persona`, `factor-review`, `universal specialist`, `archetype specialist`, and `repo-local specialist`. Only the first three are guaranteed in every seeded repository; specialist tiers are enabled from repo evidence and repo-local config.
11. Generate specialist wrappers only for roles that are enabled by repo-local evidence or operator configuration. Universal specialists are cross-project roles such as architecture, security, docs, and onboarding. Archetype specialists are keyed to repository shape, such as web/full-stack, mobile/desktop, AI/agent, JVM/service, or infrastructure-heavy repos. Repo-local specialists are project-specific and must stay clearly separated from reusable framework defaults.
12. Update `.gitignore` so framework-managed platform files are tracked rather than silently excluded.
13. Add the framework script hygiene rule to `AGENTS.md` as a universal cross-agent instruction (see below).
14. Seed `.claude/settings.json` with the project-level Claude Code hook that automates the same rule for Claude Code (see below).
15. Prefer generating platform hook/config surfaces via `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` rather than hand-editing each hook file independently. Keep the repo-local hook files at the platform-expected paths, but treat them as generated Python entrypoints rendered from generic framework templates. Use a repo-global guard override file (`.wavefoundry/guard-overrides.json`) rather than provider-specific sentinel files for temporary seed/framework edit approval.
16. **Stage gate (repository code)** — Add a `## Stage Gate (repository code)` section to `AGENTS.md` before the Implementation guard. This gate applies to all repository code (product source, scripts, tests, build manifests, and other checked-in code/config that affects shipped or verified behavior). It must require all three of the following before the first code edit in a given effort: (1) a consolidated change document exists; (2) the change is admitted into a wave via `Create wave` / `Add change to wave`; (3) the wave has a successful `Prepare wave` / `Ready wave` pass as the immediately preceding lifecycle step. If any step is missing, agents must stop and route back to `Plan feature`, `Create wave`, `Add change to wave`, or `Prepare wave`. Mark documentation-only edits under `docs/`, prompt/framework docs that do not change repository code, and operator-approved explicit waivers for a named scope as out of scope for this gate.
17. **Implementation guard (product code)** — When the project ships product implementation source (present in the repository), add an `## Implementation guard (product code)` section to `AGENTS.md` immediately after the Stage gate section. Use the decision signals and template below. When the repo is documentation-only, specs-only, or contains only the wave framework pack with no shipped product code, omit the section or add a single line that the guard should be added once implementation directories exist.
18. When an Implementation guard section exists in `AGENTS.md`, set thin-pointer startup step 1 in `CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, `.github/copilot-instructions.md`, and `WARP.md` to: read `AGENTS.md` including **Implementation guard (product code)** before editing product targets. When the section does not exist, keep the generic “read `AGENTS.md`” step without that sub-clause.

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
- factor-review agent routing when applicable factors exist
- persona routing when personas exist
- specialist routing when repo evidence enables universal, archetype, or repo-local specialists
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

> The framework test suite (`scripts/tests/`, `scripts/run_tests.py`) is a development-only artifact that lives in the Wavefoundry source repository and is **not included in the distribution pack**. Downstream repositories that vendor the pack do not have these files and must not attempt to run them. If anything created `__pycache__` caches, delete them:
> ```
> find .wavefoundry/framework/scripts -type d -name '__pycache__' -prune -exec rm -rf {} \;
> ```

## Hook Contract

Use `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` to materialize tracked hook entrypoints and merged settings files for every enabled platform. For each entrypoint the renderer writes three variants — a self-contained Python implementation (`<name>.py`), a POSIX launcher (`<name>`), and a Windows launcher (`<name>.cmd`) — all `chmod +x`. The JSON snippets below show POSIX launcher command values; on Windows the renderer emits the corresponding `cmd.exe /c ...\\.cmd` invocation. Prefer `render_platform_surfaces.py` over hand-editing each hook file independently (see task 13).

### Shared hook policy (all platforms)

- **Canonical guard override file** — use exactly this repo-global schema at `.wavefoundry/guard-overrides.json` for temporary approvals; do not introduce provider-specific sentinel files:
```json
{
  "framework_edit_allowed": { "enabled": false },
  "seed_edit_allowed":      { "enabled": false }
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
- **Framework distribution zip drops (do not commit)** — the version-controlled pack is the unpacked tree under `.wavefoundry/framework/` (including sources consumed by `scripts/build_pack.py`). Zip archives at the repository root — dated `wavefoundry-*.zip` from packaging or vendor drops, or legacy `agent-workflows.zip` — are for local unpack or transport only; **never commit them**. If a repository still tracks an older zip, remove it from the index (`git rm --cached <file>.zip`) and rely on ignore rules. When the following anchored block is missing from `.gitignore`, add it (leading `/` limits matches to repository root):
```gitignore
# Wavefoundry framework pack archives (tracked source lives under .wavefoundry/framework/; do not commit zip drops)
/agent-workflows.zip
/wavefoundry-*.zip
```
- **Operator-owned `git commit` (policy, not hooks)** — document in `AGENTS.md` and `docs/contributing/build-and-verification.md` that **agents must not** run `git commit` unless the operator explicitly instructs them to finalize that commit in the **current** request after review; default is to hand off a suggested message and diff for the operator to commit locally. The policy must also say that agents do **not** infer commit approval from broad phrases like "go ahead", "ship it", or "commit the changes": before any commit, the agent must present or confirm the exact commit scope and receive a clear finalization instruction for that reviewed scope. Do not rely on shell hooks or env-var bypasses for this — keep it as explicit workflow policy.
- **Project-specific post-edit checks** — when a repository needs additional formatter or validator hooks beyond the generic docs gate, define and render those as repo-local adaptations rather than hard-coding project paths into the shared framework.

### Wavefoundry MCP — docs gate for agents

Seeded **`AGENTS.md`**, **`CLAUDE.md`**, thin pointers, and **`docs/prompts/*`** must instruct **agents** to prefer MCP **`wave_validate`** (docs lint results), **`wave_garden`** (metadata gardening; follow the tool `mode` contract), and **`wave_audit`** (combined wave + validation + index readout) over shelling out to **`.wavefoundry/bin/docs-lint`** / **`.wavefoundry/bin/docs-gardener`**. Treat the **bin** launchers as **CLI / hook / CI** fallbacks when MCP is not attached. Hooks below **cannot** call MCP and therefore still invoke **`.wavefoundry/bin/docs-lint`** — that does not change MCP-first agent guidance.

This MCP-first principle extends beyond docs validation to **all wave and plan state queries**: before reaching for `ls`, `grep`, or filesystem tools to answer any question about wave state, plans, or change docs, agents must check the MCP tool list first. `wave_list_plans` (pending changes not yet admitted to a wave), `wave_list_waves`, `wave_current`, and `wave_get_change` return structured answers directly. Seeded `AGENTS.md` must include this guidance in its MCP or docs-gate section.

### Shared hook purposes (apply on every host per its pre/post capability)

- **Seed protection** — block (or warn+halt where pre-write is unavailable) edits to `*.prompt.md` files under `.wavefoundry/framework/` unless `.wavefoundry/guard-overrides.json` sets `seed_edit_allowed.enabled` to `true`. Use the repo-global override file only for intentional seed edits, then remove it or set the flag back to `false`.
- **Framework plan gate** — block (or warn+halt) broad framework-maintenance edits to `.wavefoundry/framework/`, `docs/prompts/`, `AGENTS.md`, and tracked hook configs unless `.wavefoundry/guard-overrides.json` sets `framework_edit_allowed.enabled` to `true` after the operator reviews the file-level patch plan.
- **`docs-lint` hook** — run **`.wavefoundry/bin/docs-lint`** after any Edit/Write to files under `docs/`, failing the hook when the docs gate fails (subprocess hook path; not MCP).
- **pycache cleanup** (Claude Code only) — remove `__pycache__` directories after framework script runs.

### Per-platform capability matrix

| Tool or Host | Pre-write block                                      | Post-write validation                                   | Config file                                                        |
|--------------|------------------------------------------------------|---------------------------------------------------------|--------------------------------------------------------------------|
| Claude Code  | ✅ `PreToolUse` seed protection + framework plan gate | ✅ `PostToolUse` `docs-lint` + pycache cleanup           | `.claude/settings.json`                                            |
| Cursor       | ⚠️ `afterFileEdit` warn+halt (write already landed)   | ✅ `afterFileEdit` `docs-lint`                           | `.cursor/hooks.json`                                               |
| Windsurf     | ✅ `pre_write_code` true blocking (exit code 2)       | ✅ `post_write_code` `docs-lint`                         | `.windsurf/hooks.json`                                             |
| Copilot      | ✅ `preToolUse` seed + framework approval             | ✅ `postToolUse` `docs-lint`                             | `.github/hooks/hooks.json`                                         |
| Codex        | ❌ instruction-only                                   | ❌                                                       | `AGENTS.md`, `docs/prompts/`, `.codex/skills/`                     |
| Air          | ❌ hosted-provider only                               | ❌ hosted-provider only                                  | existing provider wrappers only                                    |
| Junie        | ❌ instruction-only (`AGENTS.md`, `.junie/guidelines.md`) | ❌                                                    | `.junie/guidelines.md`                                             |
| Warp         | ❌ instruction-only                                   | ❌                                                       | `WARP.md`                                                          |

For Codex, Air, Junie, and Warp, reinforce rules in `AGENTS.md` and the respective thin-pointer or native-wrapper files only.

### Claude Code

Seed or update `.claude/settings.json` with the hooks below. **Merge with any existing hooks — do not replace the entire file.** `.claude/settings.json` is not read by Cursor, Codex, Windsurf, or other tools, so the behavioral rules must also be present in `AGENTS.md`, `CLAUDE.md`, and other platform thin-pointer files.

```json
{
  "hooks": {
    "PreToolUse":  [ { "matcher": "Edit|Write", "hooks": [ { "type": "command", "command": ".claude/hooks/pre-edit",        "statusMessage": "Checking framework edit gates..." } ] } ],
    "PostToolUse": [
      { "matcher": "Bash",       "hooks": [ { "type": "command", "command": ".claude/hooks/pycache-cleanup", "statusMessage": "Cleaning __pycache__..." } ] },
      { "matcher": "Edit|Write", "hooks": [ { "type": "command", "command": ".claude/hooks/post-edit",       "statusMessage": "Running docs gates..." } ] }
    ]
  }
}
```

Generated entrypoints (three variants each: `.py`, POSIX launcher, `.cmd`):
- `.claude/hooks/pre-edit` — seed protection + framework plan gate
- `.claude/hooks/post-edit` — `docs-lint`
- `.claude/hooks/pycache-cleanup` — `__pycache__` cleanup after framework script runs
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
    "pre_write_code":  [ { "command": ".windsurf/hooks/seed-protect", "show_output": true } ],
    "post_write_code": [ { "command": ".windsurf/hooks/docs-lint",     "show_output": true } ]
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
    "preToolUse":  [ { "type": "command", "bash": ".github/hooks/pre-tool-use" } ],
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

## Execution Contract in Canonical Role Docs

When canonical role docs exist under `docs/agents/`, ensure each active role doc includes an **Execution contract** section with the role-relevant subset of rules from `.wavefoundry/framework/seeds/020-run-contract.prompt.md`. Backfill when missing on init or upgrade.

Role-subset mapping:

- **`implementer.md`** — execution-discipline rules: in brownfield repositories, detect dominant patterns in the relevant scope (naming, error handling, abstraction depth, argument ordering, test structure, module organization) and follow them — surface significant pattern problems with rationale and wait for operator approval before deviating; state current behavior and why the change is needed before making it; prefer the smallest correct change; when stuck, diagnose and explain before switching approaches; after making changes, reason through whether they actually address the stated problem.
- **`planner.md`** — reasoning-depth rules: planning requests are complex-tier by default (the planner role does not handle lightweight tasks); reason step-by-step, surface tradeoffs, and provide comprehensive analysis; surface assumptions explicitly; when multiple approaches exist, compare them; prefer one precise clarifying question over proceeding on a wrong assumption.
- **`wave-coordinator.md`** — full contract for coordination: coordinator decisions span planning and execution, so apply the same reasoning depth as complex-tier work in `020` — evaluate the admitted change set, dependencies, and lane interactions step-by-step (do not shortcut evaluation); surface assumptions explicitly; state current wave state and rationale before changing readiness, allocation, or closure posture; when blocked or uncertain, diagnose and explain before switching approaches; prefer one precise clarifying question over proceeding on a wrong assumption about scope; verify the execution state matches the plan before declaring a coordination phase done.
- **Reviewer roles** (`code-reviewer`, `qa-reviewer`, `architecture-reviewer`, `security-reviewer`, etc.) — no Execution contract section required; reviewer output contracts already govern their outputs.

The Execution contract section belongs near the end of the role doc, after Responsibilities or Guardrails. Do not copy all six rules to every role doc — use the subset above so each role doc remains focused and non-redundant with `020`.

## Cleanup and Destructive Operations

Add a `## Cleanup and Destructive Operations` section to `AGENTS.md` when the repository contains installed artifacts (shipped binaries, installed apps) or legacy content that could be confused with live working docs:

> **Historical reference preservation:** During legacy cleanup, only remove live working docs and deprecated prompt/wrapper files that have valid replacements. Do not delete mentions of removed artifacts from changelogs, wave records, closed-wave archives, release notes, or historical documentation. Retiring a file removes the file — not the historical record of it.
>
> **Destructive operations outside the repo:** Before overwriting or replacing an installed artifact outside the repository (for example, an app bundle in `/Applications`), confirm the target, verify a rollback path exists, and build to a staging location first. A distribution build that clobbers a working installation without a backup is not recoverable from the repository alone.
>
> **Legacy cleanup scoping:** When asked to clean up legacy content, default to removing only the explicitly named deprecated artifacts. Do not expand scope to adjacent historical records, prior wave archives, or references in closed-wave docs without explicit instruction.

## Design-System Extraction Guidance in AGENTS.md

When `docs/design/` exists in the target repository (or when `seed-040` task 14 has been applied), add the following guidance to the `AGENTS.md` **Docs Map** or equivalent section so agents can locate the extraction contract:

> **`docs/design/`** — machine-readable design system extraction contract (tokens, component specs, gap log, source map). Distinct from `docs/design/design-language.md`, which is the operator-owned narrative design document.
>
> - Regeneration regenerates JSON/spec trees (e.g. `manifest.json`, `tokens/`, `components/`). It **never** rewrites `design-language.md` or `index.md` body content.
> - `docs/design/AGENTS.md` contains agent rules for this subtree — check it before building UI components or writing hard-coded values.
> - `docs/design/.design-system/proposed-additions.md` is the escape valve for new component proposals before they are formally added.
> - **Split B subtrees** (`patterns/`, `state-patterns/`, `validation-patterns/`, `content/`, `skills/`) — extend the core contract with pattern guidance, state definitions, validation conventions, voice/tone, and agent-facing skills. Consult these when implementing UI patterns, form validation, content copy, or building new agent design tasks. Present only when Split B has been applied.

This entry must be present whenever `docs/design/` is seeded or detected. Keep it concise and route to `docs/design/AGENTS.md` for the full agent rules rather than duplicating them.

Guardrails:

- Keep non-canonical entry files thin.
- Do not duplicate deep policy in multiple places.
- Edit project role or persona policy in canonical docs under `docs/agents/`, not thin wrappers.
- Do not generate platform-native wrappers for platforms that are not enabled in repo-local config.
- When seeding `.claude/settings.json`, merge into the existing file rather than replacing it.
