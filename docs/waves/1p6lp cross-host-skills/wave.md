# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-06-19

wave-id: `1p6lp cross-host-skills`
Title: Cross Host Skills

## Objective

Treat skills as a first-class, cross-host surface. Today they're two ad-hoc, inconsistent paths (Codex `auto-guru` with frontmatter; Claude `upgrade-wave` without) and an incomplete catalog; meanwhile `SKILL.md` has converged into a cross-tool standard (Codex/Claude/Antigravity, all project-local). This wave builds **one skill registry + a shared `SKILL.md` emitter** (change `1p6lo`), migrates the two existing skills onto it with cross-host parity (incl. Antigravity, deferred from `1p6l5`), and — pending curation — adds a curated set of **lifecycle-command skills** (sibling change). When it closes, Wavefoundry renders consistent skills across the skill-supporting hosts from one source.

## Changes

Change ID: `1p6lo-enh unified-cross-host-skill-rendering`
Change Status: `planned`

Change ID: `1p6lw-enh core-lifecycle-command-skills`
Change Status: `planned`

## Wave Summary

Change `1p6lo` (foundation): a unified skill registry + `SKILL.md` emitter; migrate `auto-guru` + `upgrade-wave` onto it (standardize the Claude flat file, add cross-host parity incl. Antigravity); close the Tier-3 catalog gap. Change `1p6lw` (content): the operator-chosen **core loop** — Plan feature / Prepare wave / Implement wave / Review wave / Close wave — as thin-pointer skills over the `1p6lo` registry. Maintainer + review-helper skills are a deferred follow-up.

## Journal Watchpoints

- **Sequencing:** `1p6lo` (the registry/emitter) lands first; the sibling `lifecycle-command-skills` change builds on it. Don't author lifecycle skills before the registry exists.
- **`SKILL.md` is a cross-tool standard** (frontmatter `name`/`description` + body + optional `scripts/`/`examples/`/`resources/`): Codex `.codex/skills/<name>/SKILL.md`, Claude `.claude/skills/<name>/SKILL.md`, Antigravity `.agents/skills/<name>/SKILL.md` (all project-local). Author once, emit per host.
- **Migration gotcha:** the existing Claude `upgrade-wave` is a *flat, frontmatter-less* `.claude/skills/upgrade-wave.md`; standardizing to `<name>/SKILL.md` + frontmatter must stale-clean the old path and update `is_framework_maintenance_surface` (`render_platform_surfaces.py:309`).
- **Gating:** per-skill — `auto-guru` requires `docs/agents/guru.md` (guru_available); `upgrade-wave` is maintenance (preserve its current ungated-on-guru behavior, host-dir-aware).
- **Open questions** (in `1p6lo`): Cursor inclusion; registry home (`render_agent_surfaces.py` recommended); `upgrade-wave` cross-host parity vs Claude-only (body is Claude-specific); skill body = thin pointer to the backing seed vs inline.
- **Follow-up:** `1p6lw` is scoped to the operator-chosen **core loop** (Plan/Prepare/Implement/Review/Close); maintainer (Upgrade, Package) + review-helper (Interrogate, Evaluate, Council, Archetype, config/cleanup review) skills are a deferred follow-up once the core set proves out. `1p6lw` is **BLOCKED** on `1p6lo` (the registry) landing first — watch the sequencing at implement.

## Review Evidence

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.
