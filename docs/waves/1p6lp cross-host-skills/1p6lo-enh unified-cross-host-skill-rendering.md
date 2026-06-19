# Unified cross-host skill rendering (SKILL.md registry)

Change ID: `1p6lo-enh unified-cross-host-skill-rendering`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-19
Wave: TBD

## Rationale

Wavefoundry renders skills today via **two ad-hoc, inconsistent paths** with **no shared abstraction**:

- **Codex auto-guru** — `CODEX_AUTO_GURU_SKILL` constant + a direct `write_text` in `render_agent_surfaces.py:318-319` → `.codex/skills/auto-guru/SKILL.md`. **Has** YAML frontmatter (`name`/`description`). Gated on `guru_available` (`docs/agents/guru.md`).
- **Claude upgrade-wave** — `render_upgrade_skill()` in `render_platform_surfaces.py:1271-1305` → `.claude/skills/upgrade-wave.md` (flat file). **No** frontmatter. Gated only on the `claude` platform; also pinned in `is_framework_maintenance_surface` (`:309`). **Not catalogued** in the AGENTS.md Tier-3 table or `platform-mapping.md`.

Meanwhile **`SKILL.md` has converged into a cross-tool open standard** (YAML frontmatter `name`/`description` + markdown body + optional `scripts/`/`examples/`/`resources/`), supported by **Codex** (`.codex/skills/<name>/SKILL.md`), **Claude Code** (`.claude/skills/<name>/SKILL.md`), **Antigravity** (`.agents/skills/<name>/SKILL.md`, project-local), and Cursor — all project-local. A skill authored once works across them.

This change builds the **one unifying mechanism** the framework lacks: a **skill registry** + a shared `SKILL.md` emitter that renders each skill to every active skill-supporting host in the standard format, with per-skill gating — and migrates the two existing skills onto it (standardizing the Claude one, adding cross-host parity), adds Antigravity (the `1p6l5` deferral), and fixes the catalog/doc gap. The lifecycle-command skill *content* (which commands become skills) is a separate change (`lifecycle-command-skills`); this change is the **foundation + parity + consistency**.

## Requirements

1. **Skill registry + shared emitter.** A single declarative registry (e.g. a list of `Skill(name, description, body_source, gate, hosts)`) + one `render_skills(repo_root)` that, per registered skill, writes the **standard `SKILL.md`** (YAML frontmatter `name`/`description` + body) into each **active, skill-supporting host's** project-local dir: `.codex/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, `.agents/skills/<name>/SKILL.md` (Antigravity). Cursor inclusion is a decision (open question). Forward-slash policy applies to any emitted paths.
2. **Migrate the two existing skills onto the registry, remove the ad-hoc paths.** Retire `CODEX_AUTO_GURU_SKILL`'s direct write and `render_upgrade_skill`. `auto-guru` and `upgrade-wave` become registry entries. `auto-guru` now emits to **all** skill hosts (was Codex-only); `upgrade-wave` is **standardized** to `.claude/skills/upgrade-wave/SKILL.md` **with frontmatter** (was a flat, frontmatter-less `.claude/skills/upgrade-wave.md`) and given cross-host parity.
3. **Per-skill gating.** Registry declares each skill's gate: `auto-guru` stays gated on `guru_available` (`docs/agents/guru.md`); `upgrade-wave` is a maintenance skill (its current ungated-on-guru behavior preserved, but now host-dir-aware). Host emission is gated on the host surface being active (host dir present), consistent with the other Tier-3 surfaces.
4. **Backward-compat cleanup.** The old flat `.claude/skills/upgrade-wave.md` moves to `.claude/skills/upgrade-wave/SKILL.md`; add the old path to the renderer's stale-cleanup list and update `is_framework_maintenance_surface` to the new path.
5. **Catalog + docs.** AGENTS.md Tier-3 "Optional native surfaces" table lists **every** skill per host (closing the `upgrade-wave` gap); `docs/agents/platform-mapping.md` updated; note the SKILL.md standard + per-host locations.
6. **Tests + no regression.** Registry emits correct `SKILL.md` (frontmatter + body) per host; gating honored; old flat path cleaned; full suite green; docs-lint clean; POSIX/WSL2 unaffected; forward-slash policy held.

## Scope

**Problem statement:** Skills are rendered by two divergent ad-hoc paths with inconsistent formats and an incomplete catalog; there's no mechanism to render a skill across the (now-standardized) skill-supporting hosts.

**In scope:** the skill registry + shared `SKILL.md` emitter; migrating `auto-guru` + `upgrade-wave` onto it (standardize + cross-host parity, incl. Antigravity); stale-cleanup of the old flat path; catalog/doc fix; tests.

**Out of scope:**

- **The lifecycle-command skill set** (Plan feature / Implement wave / Review wave / Close wave / Prepare wave / Upgrade / Package, …) — the *content* expansion that uses this mechanism is the sibling change `lifecycle-command-skills` (pending curation of which commands become skills).
- Changing any host's MCP registration or Tier-1/Tier-2 surfaces.
- Native-Windows `.cmd` concerns (skills are markdown, OS-agnostic).

## Open questions (resolve at prepare/implement)

1. **Cursor inclusion** — Cursor is SKILL.md-compatible; emit `auto-guru`/skills to Cursor too, or keep Cursor on its existing `.cursor/rules/auto-guru.mdc` rule? (Recommendation: keep the Cursor rule as-is for `auto-guru`; revisit per-skill.)
2. **Where the registry lives** — consolidate into `render_agent_surfaces.py` (already handles Codex skills + the guru gate) vs a new `render_skills.py`. (Recommendation: `render_agent_surfaces.py`.)
3. **`upgrade-wave` gating + host set** — keep it Claude-only (status quo) or give it real cross-host parity? It references Claude-specific guard mechanics; the body may need host-neutralizing before emitting to Codex/Antigravity.
4. **Body sourcing** — registry body as inline content vs a thin pointer to the backing seed/prompt. (Recommendation: thin pointer to the seed/prompt where one exists, to avoid drift; see the `lifecycle-command-skills` change.)

## Acceptance Criteria

- [ ] AC-1: a skill registry + `render_skills` emitter writes standard `SKILL.md` (frontmatter `name`/`description` + body) to each active skill host's project-local dir (`.codex/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, `.agents/skills/<name>/SKILL.md`).
- [ ] AC-2: `auto-guru` and `upgrade-wave` are registry-driven; the ad-hoc `CODEX_AUTO_GURU_SKILL` direct write and `render_upgrade_skill` are removed. `auto-guru` emits to all skill hosts; `upgrade-wave` is standardized to `<name>/SKILL.md` with frontmatter.
- [ ] AC-3: per-skill gating honored (`auto-guru` ⇒ requires `docs/agents/guru.md`); host emission gated on host-dir presence.
- [ ] AC-4: the old flat `.claude/skills/upgrade-wave.md` is stale-cleaned on render; `is_framework_maintenance_surface` points at the new path.
- [ ] AC-5: AGENTS.md Tier-3 table + `platform-mapping.md` catalog every skill per host (the `upgrade-wave` gap closed).
- [ ] AC-6: tests cover registry emission per host + gating + stale cleanup; full suite green; docs-lint clean; no POSIX/WSL2 regression; forward-slash policy held.

## Tasks

- [ ] Define the `Skill` registry + `render_skills(repo_root)` emitter (standard SKILL.md; per-host project-local dirs; forward-slash).
- [ ] Migrate `auto-guru` + `upgrade-wave` to the registry; remove `CODEX_AUTO_GURU_SKILL` direct write + `render_upgrade_skill`; standardize `upgrade-wave` to `<name>/SKILL.md` + frontmatter.
- [ ] Per-skill gating + host-dir gating; stale-clean the old flat path; update `is_framework_maintenance_surface`.
- [ ] Catalog/doc: AGENTS.md Tier-3 table + `platform-mapping.md`.
- [ ] Tests: per-host emission, gating, stale cleanup; full suite + docs-lint.

## Affected Architecture Docs

`N/A` for boundaries/flow — consolidates two render paths into one mechanism. Updates the Tier-3 host-surface catalog in `AGENTS.md` + `docs/agents/platform-mapping.md`.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The unifying mechanism is the deliverable. |
| AC-2 | required | Migrate + de-duplicate the two ad-hoc paths. |
| AC-3 | required | Correct gating (don't ship auto-guru without guru.md). |
| AC-4 | important | Don't orphan the old flat skill file. |
| AC-5 | important | Catalog completeness/discoverability. |
| AC-6 | required | Tested + no regression. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-19 | Planned from skills discovery. Two ad-hoc paths (Codex `auto-guru` w/ frontmatter; Claude `upgrade-wave` w/o), no registry; `SKILL.md` is now a cross-tool standard (Codex/Claude/Antigravity/Cursor, project-local). | `render_agent_surfaces.py:318-319`, `render_platform_surfaces.py:1271-1305`/`:1334`/`:309`; Antigravity `.agents/skills/`, Codex `.codex/skills/`, Claude `.claude/skills/` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-19 | Build one skill registry + shared `SKILL.md` emitter; migrate both existing skills onto it. | Two divergent ad-hoc paths + a converged `SKILL.md` standard; a registry enables author-once/emit-per-host parity and closes the catalog gap. | Keep adding bespoke per-skill/per-host functions (rejected — drift, the exact problem today). |
| 2026-06-19 | Split mechanism (this change) from the lifecycle-command skill *content* (sibling change). | The mechanism is testable infra; the command→skill curation is a separate decision. | One mega-change (rejected — couples infra with a curation debate). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Standardizing `upgrade-wave` to `<name>/SKILL.md` orphans the old flat file / breaks the maintenance-surface guard. | AC-4: stale-clean the old path + update `is_framework_maintenance_surface`; test both. |
| `upgrade-wave` body is Claude-specific; cross-host parity could mislead. | Open question #3 — host-neutralize the body before parity, or keep it Claude-scoped in the registry. |
| Registry abstraction over-engineers a 2-skill problem. | Kept minimal (a list + one emitter); it immediately pays off via the sibling lifecycle-skills change + Antigravity. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
