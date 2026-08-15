# Unified cross-host skill rendering (SKILL.md registry)

Change ID: `1p6lo-enh unified-cross-host-skill-rendering`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-15
Wave: `1p6lp cross-host-skills`

## Rationale

Wavefoundry renders skills today via **two ad-hoc, inconsistent paths** with **no shared abstraction**:

- **Codex auto-guru** — `CODEX_AUTO_GURU_SKILL` constant (`render_agent_surfaces.py:308`) + a direct `_tier3_write` (`:1370`) → `.codex/skills/auto-guru/SKILL.md`. **Has** YAML frontmatter (`name`/`description`). Gated on `guru_available` (`docs/agents/guru.md`).
- **Claude upgrade-wave** — `render_upgrade_skill()` in `render_platform_surfaces.py:2085` (called at `:2152`) → `.claude/skills/upgrade-wave.md` (flat file). **No** frontmatter; current Claude Code discovers skills only at `.claude/skills/<name>/SKILL.md` with frontmatter, so this file almost certainly does not load as a skill at all. Gated only on the `claude` platform; also pinned in `is_framework_maintenance_surface` (`:384`). **Not catalogued** in the AGENTS.md Tier-3 table or `platform-mapping.md`.

*(Line refs re-verified 2026-08-14; the 2026-06-19 census figures had drifted.)* One census addition since planning: role-typed `.codex/skills/agent-role-<role>/SKILL.md` wrappers are recognized as **conditional review-protocol carriers** (`render_agent_surfaces.py:206`, presence-gated); the registry migration must keep that recognition pointed at whatever paths exist after this change.

Meanwhile **`SKILL.md` has converged into a cross-tool open standard** (YAML frontmatter `name`/`description` + markdown body + optional `scripts/`/`examples/`/`resources/`), supported by **Codex** (`.codex/skills/<name>/SKILL.md`), **Claude Code** (`.claude/skills/<name>/SKILL.md`), **Antigravity** (`.agents/skills/<name>/SKILL.md`, project-local), and Cursor — all project-local. A skill authored once works across them.

This change builds the **one unifying mechanism** the framework lacks: a **skill registry** + a shared `SKILL.md` emitter that renders each skill to every active skill-supporting host in the standard format, with per-skill gating — and migrates the two existing skills onto it (standardizing the Claude one, adding cross-host parity), adds Antigravity (the `1p6l5` deferral), and fixes the catalog/doc gap. The lifecycle-command skill *content* (which commands become skills) is a separate change (`lifecycle-command-skills`); this change is the **foundation + parity + consistency**.

## Requirements

1. **Skill registry + shared emitter.** A single declarative registry (e.g. a list of `Skill(name, description, body_source, gate, hosts)`) + one `render_skills(repo_root)` that, per registered skill, writes the **standard `SKILL.md`** (YAML frontmatter `name`/`description` + body) into each **active, skill-supporting host's** project-local dir: `.codex/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, `.agents/skills/<name>/SKILL.md` (Antigravity). Cursor inclusion is a decision (open question). Forward-slash policy applies to any emitted paths.
2. **`wf-` skill namespace (operator direction, 2026-08-14).** Every registry skill name is prefixed `wf-` and kebab-case, and the emitted directory matches the name (`.claude/skills/wf-<name>/SKILL.md`). Rationale: typing `/wf` in a host filters to the whole Wavefoundry skill family (discoverability for operators who don't know the names), and the prefix namespaces our skills inside target repos that carry skills from other tooling. Hosts match auto-invocation on `description`, not name, so the prefix costs nothing on routing. The hyphenated skill names deliberately rhyme with (not duplicate) the underscore MCP tool names: `/wf-prepare-wave` the skill, `wf_prepare_wave` the tool.
3. **Migrate the two existing skills onto the registry, remove the ad-hoc paths.** Retire `CODEX_AUTO_GURU_SKILL`'s direct write and `render_upgrade_skill`. Both become registry entries **renamed into the namespace**: `auto-guru` → **`wf-guru`**, `upgrade-wave` → **`wf-upgrade`** (deliberate exception to full-phrase naming: `wf-upgrade-wavefoundry` would say "wavefoundry" twice). `wf-guru` now emits to **all** skill hosts (was Codex-only); `wf-upgrade` is **standardized** to `.claude/skills/wf-upgrade/SKILL.md` **with frontmatter** (was a flat, frontmatter-less `.claude/skills/upgrade-wave.md`) and given cross-host parity.
4. **Per-skill gating.** Registry declares each skill's gate: `wf-guru` stays gated on `guru_available` (`docs/agents/guru.md`); `wf-upgrade` is a maintenance skill (its current ungated-on-guru behavior preserved, but now host-dir-aware). Host emission is gated on the host surface being active (host dir present), consistent with the other Tier-3 surfaces.
5. **Backward-compat cleanup.** The old flat `.claude/skills/upgrade-wave.md` and the old `.codex/skills/auto-guru/` directory go on the renderer's stale-cleanup list; `is_framework_maintenance_surface` (`render_platform_surfaces.py:384`) points at the new `wf-upgrade` path; the conditional review-protocol carrier recognition (`render_agent_surfaces.py:206`, which names `.codex/skills/auto-guru/SKILL.md`) follows the rename to `wf-guru`.

   **Rename census (readiness review, 2026-08-14): every site that names the old paths must follow the rename.** Beyond the two sites above: the tier-3 destinations list in `render_agent_surfaces.py:1094`; canonical seeds `050-agent-entry-surface-bootstrap.prompt.md` (7 skill-path refs) and `160-upgrade-wavefoundry.prompt.md` (3 refs), edited under the `seed_edit_allowed` gate (also audit seed 040, which mentions `skills/`); and the reviewer-wrapper eligibility prose in `docs/agents/platform-mapping.md` (the doc counterpart of the carrier recognition). Note the `is_framework_maintenance_surface` pin lives inside a **rendered hook template**, so target repos pick up the new path only on re-render/upgrade; already-installed repos keep pinning the old path until upgraded (disclose as a transition note).
6. **Catalog + docs.** AGENTS.md Tier-3 "Optional native surfaces" table lists **every** skill per host (closing the `upgrade-wave` gap); `docs/agents/platform-mapping.md` updated; note the SKILL.md standard + per-host locations + the `wf-` namespace.
7. **Tests + no regression.** Registry emits correct `SKILL.md` (frontmatter + body) per host; gating honored; both old paths cleaned; full suite green; docs-lint clean; POSIX/WSL2 unaffected; forward-slash policy held.

## Scope

**Problem statement:** Skills are rendered by two divergent ad-hoc paths with inconsistent formats and an incomplete catalog; there's no mechanism to render a skill across the (now-standardized) skill-supporting hosts.

**In scope:** the skill registry + shared `SKILL.md` emitter; the `wf-` naming policy; migrating `auto-guru` + `upgrade-wave` onto it as `wf-guru` + `wf-upgrade` (standardize + cross-host parity, incl. Antigravity); stale-cleanup of both old paths; catalog/doc fix; tests.

**Out of scope:**

- **The lifecycle-command skill set** (Plan feature / Implement wave / Review wave / Close wave / Prepare wave / Upgrade / Package, …) — the *content* expansion that uses this mechanism is the sibling change `lifecycle-command-skills` (pending curation of which commands become skills).
- Changing any host's MCP registration or Tier-1/Tier-2 surfaces.
- Native-Windows `.cmd` concerns (skills are markdown, OS-agnostic).

## Open questions (resolve at prepare/implement)

1. **Cursor inclusion** — Cursor is SKILL.md-compatible; emit `wf-guru`/skills to Cursor too, or keep Cursor on its existing `.cursor/rules/auto-guru.mdc` rule? (Recommendation: keep the Cursor rule as-is for guru; revisit per-skill.)
2. **Where the registry lives** — consolidate into `render_agent_surfaces.py` (already handles Codex skills + the guru gate) vs a new `render_skills.py`. (Recommendation: `render_agent_surfaces.py`.)
3. **`wf-upgrade` gating + host set** — keep it Claude-only (status quo) or give it real cross-host parity? It references Claude-specific guard mechanics; the body may need host-neutralizing before emitting to Codex/Antigravity.

**Resolved 2026-08-14:** body sourcing (former open question 4): registry bodies are **thin pointers** to the backing prompt/seed, never inline copies of the workflow content. Decided with the operator during the `1p6lw` re-curation; see that change's design contract.

## Acceptance Criteria

- [x] AC-1: a skill registry + `render_skills` emitter writes standard `SKILL.md` (frontmatter `name`/`description` + body) to each active skill host's project-local dir (`.codex/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, `.agents/skills/<name>/SKILL.md`).
- [x] AC-2: every registry skill name is `wf-`-prefixed kebab-case and the emitted directory matches the name; the registry rejects (or a test forbids) an unprefixed entry.
- [x] AC-3: `wf-guru` and `wf-upgrade` are registry-driven; the ad-hoc `CODEX_AUTO_GURU_SKILL` direct write and `render_upgrade_skill` are removed; `wf-upgrade` is standardized to `<name>/SKILL.md` with frontmatter; `wf-guru` emits to all skill hosts.
- [x] AC-4: per-skill gating honored (`wf-guru` ⇒ requires `docs/agents/guru.md`); host emission gated on host-dir presence.
- [x] AC-5: the old flat `.claude/skills/upgrade-wave.md` and old `.codex/skills/auto-guru/` are stale-cleaned on render; `is_framework_maintenance_surface` and the conditional carrier recognition in `render_agent_surfaces.py` point at the new paths.
- [x] AC-6: AGENTS.md Tier-3 table + `platform-mapping.md` catalog every skill per host (the `upgrade-wave` gap closed) and state the `wf-` namespace.
- [x] AC-7: tests cover registry emission per host + gating + stale cleanup; full suite green; docs-lint clean; no POSIX/WSL2 regression; forward-slash policy held.

## Tasks

- [x] Define the `Skill` registry + `render_skills(repo_root)` emitter (standard SKILL.md; per-host project-local dirs; forward-slash; `wf-` name policy enforced).
- [x] Migrate `auto-guru` + `upgrade-wave` to the registry as `wf-guru` + `wf-upgrade`; remove `CODEX_AUTO_GURU_SKILL` direct write + `render_upgrade_skill`.
- [x] Per-skill gating + host-dir gating; stale-clean both old paths; update `is_framework_maintenance_surface` + the conditional carrier recognition.
- [x] Catalog/doc: AGENTS.md Tier-3 table + `platform-mapping.md` (incl. `wf-` namespace).
- [x] Tests: per-host emission, naming policy, gating, stale cleanup; full suite + docs-lint.

## Affected Architecture Docs

`N/A` for boundaries/flow — consolidates two render paths into one mechanism. Updates the Tier-3 host-surface catalog in `AGENTS.md` + `docs/agents/platform-mapping.md`.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The unifying mechanism is the deliverable. |
| AC-2 | required | The `wf-` namespace is the operator's discoverability contract. |
| AC-3 | required | Migrate + de-duplicate the two ad-hoc paths. |
| AC-4 | required | Correct gating (don't ship wf-guru without guru.md). |
| AC-5 | important | Don't orphan old paths or the carrier recognition. |
| AC-6 | important | Catalog completeness/discoverability. |
| AC-7 | required | Tested + no regression. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-19 | Planned from skills discovery. Two ad-hoc paths (Codex `auto-guru` w/ frontmatter; Claude `upgrade-wave` w/o), no registry; `SKILL.md` is now a cross-tool standard (Codex/Claude/Antigravity/Cursor, project-local). | `render_agent_surfaces.py:318-319`, `render_platform_surfaces.py:1271-1305`/`:1334`/`:309`; Antigravity `.agents/skills/`, Codex `.codex/skills/`, Claude `.claude/skills/` |
| 2026-08-14 | Revived from parked state. Line refs re-verified (constant `:308`, write `:1370`; `render_upgrade_skill` `:2085`/`:2152`; maintenance pin `:384`); census gained the conditional agent-role carrier recognition (`render_agent_surfaces.py:206`); added the `wf-` namespace requirement + renames (`auto-guru`→`wf-guru`, `upgrade-wave`→`wf-upgrade`); resolved body-sourcing open question to thin pointers. | Operator direction in-session; grep of both renderers 2026-08-14 |
| 2026-08-14 | Implemented. Registry (`Skill` dataclass, `SKILL_REGISTRY`, `render_skills`) lives in `render_agent_surfaces.py` (open question 2 resolved per recommendation); called before the Guru gate so lifecycle skills are not Guru-gated; carrier-region graft keeps re-renders byte-convergent (wf-guru on Codex is also a review carrier). `wf-upgrade` given cross-host parity with a host-neutral body (open question 3 resolved: the old body was already host-neutral apart from its title). Cursor stays on its rule (open question 1: status quo kept). Maintenance guard now covers the `wf-` skill prefix on all three hosts, replacing the single exact path. Self-hosted surfaces re-rendered: old paths removed, `wf-guru`/`wf-upgrade` present on `.codex`/`.claude`/`.agents`; second render writes nothing. Focused tests: 197 across 4 files OK; Claude Code live-discovered both skills. | `render_agent_surfaces.py` (`SKILL_REGISTRY`, `render_skills`, `_extract_marked_block`); `render_platform_surfaces.py` (`is_framework_maintenance_surface` prefixes, `render_upgrade_skill` retired); seeds 050/160 under `seed_edit_allowed`; scratchpad `t1p6lo.log`, `render2.json` (empty manifest) |
| 2026-08-14 | Full-suite find, repaired: the first stale-clean implementation would `unlink` through a symlinked parent (deleting outside the repo) and dropped the refusal contract the old write path enforced for tampered legacy wrapper paths; two setup/upgrade integration tests caught it (`test_setup_refuses_dangling_native_wrapper_parent_before_indexing`, `test_upgrade_surface_phase_refuses_dangling_native_wrapper_parent`). `render_skills` now containment-checks every stale path before deletion and raises on symlink escape; a dedicated regression (`test_stale_cleanup_refuses_symlink_escape`) proves the outside file survives. Both original fixtures pass unmodified. | Suite log `suite-1p6lp.log` (failures) and `t-fix.log` (604 tests OK); `render_skills` containment block |
| 2026-08-14 | Delivery-review finding, repaired in-cycle (qa lane): the rendered-hook maintenance-guard prefix change had no pinning test (nor did the old exact path it replaced). Assertions added to the rendered-hook fixture asserting the three `wf-` prefixes present and the retired flat path absent; executed. | `test_render_platform_surfaces.py` rendered-hook fixture; `t-guard.log` (94 tests OK) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-19 | Build one skill registry + shared `SKILL.md` emitter; migrate both existing skills onto it. | Two divergent ad-hoc paths + a converged `SKILL.md` standard; a registry enables author-once/emit-per-host parity and closes the catalog gap. | Keep adding bespoke per-skill/per-host functions (rejected — drift, the exact problem today). |
| 2026-06-19 | Split mechanism (this change) from the lifecycle-command skill *content* (sibling change). | The mechanism is testable infra; the command→skill curation is a separate decision. | One mega-change (rejected — couples infra with a curation debate). |
| 2026-08-14 | All registry skills live in a `wf-` kebab-case namespace; the two migrated skills are renamed into it (`wf-guru`, `wf-upgrade`). | Operator direction: `/wf` filters the host's command list to the whole family, and the prefix namespaces our skills inside target repos carrying third-party skills. Renaming during the migration is one cleanup instead of two. | Unprefixed names (rejected: collision risk in target repos, no grouped discovery); `wf_` underscores (rejected: kebab-case is the SKILL.md/dir convention; underscores stay the MCP-tool signature). |
| 2026-08-14 | Skill bodies are thin pointers to backing prompts/seeds, never inline workflow content. | Resolves former open question 4; skills can never drift from the seeds that own behavior. | Inline bodies (rejected: drift, the exact defect this wave exists to remove). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Renaming/standardizing the two existing skills orphans an old path or breaks the maintenance-surface guard / carrier recognition. | AC-5: stale-clean both old paths + update `is_framework_maintenance_surface` and the carrier candidates; test all. |
| `wf-upgrade` body is Claude-specific; cross-host parity could mislead. | Open question #3 — host-neutralize the body before parity, or keep it Claude-scoped in the registry. |
| Registry abstraction over-engineers a 2-skill problem. | Kept minimal (a list + one emitter); it immediately pays off via the sibling lifecycle-skills change (now 10 entries) + Antigravity. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
