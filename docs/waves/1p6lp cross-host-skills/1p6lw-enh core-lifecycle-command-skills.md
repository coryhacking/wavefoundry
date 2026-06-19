# Core lifecycle-command skills (Plan / Prepare / Implement / Review / Close)

Change ID: `1p6lw-enh core-lifecycle-command-skills`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-19
Wave: `1p6lp cross-host-skills`

## Rationale

With the unified skill registry from `1p6lo`, expose Wavefoundry's **core operator lifecycle** as host-native skills so operators on Codex / Claude / Antigravity can invoke the loop natively (discoverable via the host's skill mechanism) instead of only typing the shortcut phrases. Scope = the 5-step loop (operator-curated): **Plan feature, Prepare wave, Implement wave, Review wave, Close wave**.

Each skill is a **thin pointer**, not duplicated content: the `SKILL.md` body routes to the backing prompt (`docs/prompts/<command>.prompt.md`) and the matching MCP tool, with the key gate reminders — so the skills never drift from the seeds/prompts that own the actual behavior.

**Depends on `1p6lo`** (the skill registry + `SKILL.md` emitter). Author after it lands.

## Requirements

1. **Register 5 core-loop skills** in the `1p6lo` registry, each emitted as standard `SKILL.md` (frontmatter `name`/`description` + thin-pointer body) to every active skill host (`.codex/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, `.agents/skills/<name>/SKILL.md`):

   | Skill name | Backing prompt | Primary MCP tool(s) |
   | --- | --- | --- |
   | `plan-feature` | `docs/prompts/plan-feature.prompt.md` (seed 170) | `wave_new_<kind>`, `wave_add_change` |
   | `prepare-wave` | `docs/prompts/prepare-wave.prompt.md` | `wave_prepare` |
   | `implement-wave` | `docs/prompts/implement-wave.prompt.md` | `wave_implement` |
   | `review-wave` | `docs/prompts/review-wave.prompt.md` | `wave_review` |
   | `close-wave` | `docs/prompts/close-wave.prompt.md` | `wave_close` |

2. **Thin-pointer bodies.** Each `description` is third-person + keyword-rich (so the host matches it to the right task); the body says, in one short block: read the backing prompt doc, prefer the MCP tool, and the load-bearing gate for that step (e.g. Prepare = stage gate before code edits; Close = operator signoff + AC reconciliation). No re-stating the prompt's full content.
3. **Gating.** These are **general lifecycle** skills — NOT `guru`-gated (unlike `auto-guru`). Emit whenever the host surface is active (host dir present), per the `1p6lo` host-dir gate.
4. **Catalog/docs.** Add the 5 skills to the AGENTS.md Tier-3 table + `platform-mapping.md` (per host), alongside `auto-guru`/`upgrade-wave`.
5. **Tests + no regression.** Each skill emits valid `SKILL.md` (frontmatter + pointer body) to each host; `description`s are present + distinct; full suite green; docs-lint clean; forward-slash policy held.

## Scope

**Problem statement:** The core lifecycle commands are prose shortcut-phrases only; they should be host-native, discoverable skills via the `1p6lo` registry.

**In scope:** the 5 core-loop skills as thin-pointer `SKILL.md` registry entries + their catalog/doc rows + tests.

**Out of scope:**

- The skill **mechanism** (that's `1p6lo`).
- **Maintainer skills** (Upgrade, Package) and **review-helper skills** (Interrogate, Evaluate, Council, Archetype, config/cleanup review) — deferred (operator chose the core loop); a later change/wave can add them once the core set proves out.
- Authoring new seeds for the no-seed commands (Prepare/Implement/Review/Close are backed by their `docs/prompts/*.prompt.md`; the skill points at those — no new seed needed).

## Acceptance Criteria

- [ ] AC-1: the 5 core-loop skills are registry entries (`1p6lo`), each emitting standard `SKILL.md` (frontmatter `name`/`description` + thin-pointer body) to `.codex/skills/<name>/`, `.claude/skills/<name>/`, `.agents/skills/<name>/` on active hosts.
- [ ] AC-2: each body routes to its backing `docs/prompts/<command>.prompt.md` + the matching `wave_*` MCP tool + the step's gate reminder; no duplicated prompt content.
- [ ] AC-3: the skills are NOT `guru`-gated (general lifecycle); host-dir-gated per `1p6lo`.
- [ ] AC-4: AGENTS.md Tier-3 table + `platform-mapping.md` list the 5 skills per host.
- [ ] AC-5: tests cover emission per host + frontmatter/description presence + pointer targets; full suite green; docs-lint clean; no POSIX/WSL2 regression; forward-slash policy held.

## Tasks

- [ ] Add the 5 `Skill` registry entries (name, description, thin-pointer body, gate=general, hosts=all skill hosts).
- [ ] Author each thin-pointer body (prompt ref + MCP tool + gate reminder).
- [ ] Catalog/doc rows (AGENTS.md Tier-3 + platform-mapping).
- [ ] Tests; full suite + docs-lint.

## Affected Architecture Docs

`N/A` — content entries on the `1p6lo` mechanism + catalog rows.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The 5 skills are the deliverable. |
| AC-2 | required | Thin-pointer (no drift) is the design contract. |
| AC-3 | required | Correct gating (lifecycle skills aren't guru-gated). |
| AC-4 | important | Catalog/discoverability. |
| AC-5 | required | Tested + no regression. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-19 | Planned. Operator curated the **core loop** (Plan/Prepare/Implement/Review/Close). Thin-pointer skills over the `1p6lo` registry; backing prompts all exist under `docs/prompts/`. Maintainer + review-helper skills deferred. | `docs/prompts/{plan-feature,prepare-wave,implement-wave,review-wave,close-wave}.prompt.md`; depends on `1p6lo` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-19 | Scope to the core 5-step loop (operator-chosen). | Highest-value, focused; proves the registry before expanding to maintainer/review-helper skills. | Comprehensive set now (deferred — more content to author/maintain before the core proves out). |
| 2026-06-19 | Thin-pointer bodies → backing prompt + MCP tool. | Skills stay in sync with the seeds/prompts that own behavior; no duplication/drift. | Inline the full command content (rejected — drift risk). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Skill descriptions overlap and the host mis-routes between loop steps. | Distinct, keyword-rich third-person `description`s per step; AC-2/AC-5 assert presence + distinctness. |
| A skill body drifts from its prompt. | Thin pointer to `docs/prompts/<command>.prompt.md` (single source of truth), not duplicated content. |
| Lands before `1p6lo`. | Hard dependency recorded; sequence `1p6lo` first (wave watchpoints). |


## Dependencies

- **Depends on `1p6lo`** (unified skill registry + `SKILL.md` emitter) — must land first.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
