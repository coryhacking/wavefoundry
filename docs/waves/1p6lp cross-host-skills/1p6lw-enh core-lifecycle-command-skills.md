# Core lifecycle-command skills (the `wf-` operator loop)

Change ID: `1p6lw-enh core-lifecycle-command-skills`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-15
Wave: `1p6lp cross-host-skills`

## Rationale

With the unified skill registry from `1p6lo`, expose Wavefoundry's core operator lifecycle as host-native skills so operators on Codex / Claude / Antigravity can invoke the loop natively (discoverable via the host's skill mechanism) instead of only typing the shortcut phrases.

**Re-curated with the operator 2026-08-14, superseding the 2026-06-19 five-skill curation:** the set is now **ten** skills, adding the plan-review step (`wf-interrogate-plan`), the memory-maintenance workflow (`wf-memory-review`), the session-boundary command (`wf-pause-wave`), structured decision evaluation (`wf-evaluate-decision`), and one review-council router (`wf-council`) to the core loop. All names carry the `wf-` namespace per the `1p6lo` naming policy, so typing `/wf` filters a host's command list to the whole family.

`wf-council` is a **router**: one skill covering the three on-demand review forms (role-based Wave Council, stance-based Archetype Council, and standalone red-team review per `1v877`), because their "convene a review on this artifact" intents overlap too heavily for three separate description-matched skills.

Each skill is a **thin pointer**, not duplicated content: the `SKILL.md` body routes to the backing prompt (`docs/prompts/<command>.prompt.md`) and the matching MCP tool(s), with the step's load-bearing gate reminder, so the skills never drift from the seeds/prompts that own the actual behavior.

**Depends on `1p6lo`** (the skill registry + `SKILL.md` emitter). Author after it lands.

## Requirements

1. **Register 10 skills** in the `1p6lo` registry, each emitted as standard `SKILL.md` (frontmatter `name`/`description` + thin-pointer body) to every active skill host (`.codex/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, `.agents/skills/<name>/SKILL.md`):

   | Skill name | Backing prompt | Primary MCP tool(s) |
   | --- | --- | --- |
   | `wf-plan-feature` | `docs/prompts/plan-feature.prompt.md` (seed 170) | `wf_new_<kind>` (all ten creation tools), `wf_add_change` |
   | `wf-prepare-wave` | `docs/prompts/prepare-wave.prompt.md` | `wf_prepare_wave` |
   | `wf-implement-wave` | `docs/prompts/implement-wave.prompt.md` | `wf_implement_wave` |
   | `wf-review-wave` | `docs/prompts/review-wave.prompt.md` | `wf_review_wave`, `wf_review_event` |
   | `wf-close-wave` | `docs/prompts/close-wave.prompt.md` | `wf_close_wave` |
   | `wf-interrogate-plan` | `docs/prompts/interrogate-plan.prompt.md` | `wf_get_change` (workflow is prompt-driven) |
   | `wf-evaluate-decision` | `docs/prompts/evaluate-decision.prompt.md` | none (workflow is prompt-driven) |
   | `wf-memory-review` | `docs/prompts/memory-review.prompt.md` | `memory_reconcile`, `memory_consolidate`, `memory_purge` |
   | `wf-pause-wave` | `docs/prompts/pause-wave.prompt.md` | `wf_pause_wave` |
   | `wf-council` | `docs/prompts/council-review.prompt.md`, `docs/prompts/archetype-council.prompt.md`, `docs/prompts/red-team-review.prompt.md` (from `1v877`) | `wf_review_event` (when recording against a wave; workflows are prompt-driven) |

   Tool names verified against the post-`1t3gt` tool surface on 2026-08-14 (the original table predated the `wave_*` to `wf_*` rename); every backing prompt doc verified present (a standing test asserts each pointer target resolves).

2. **Thin-pointer bodies.** Each `description` is third-person + keyword-rich (so the host matches it to the right task); the body says, in one short block: read the backing prompt doc, prefer the named MCP tool(s), and the load-bearing gate for that step. No re-stating the prompt's full content. Body-specific requirements:
   - `wf-plan-feature` is the **single, kind-aware planning skill**: its description enumerates the change kinds (feature, bug fix, enhancement, refactor, documentation, tech debt, task, maintenance, operations) so loose phrasing routes to it, and its body notes that the workflow selects among the `wf_new_<kind>` creation tools by change kind. There are deliberately no per-kind skills.
   - `wf-close-wave` carries the operator-owned close rule: dry-run freely; `mode="create"` only on explicit operator instruction, never inferred from adjacent actions.
   - `wf-implement-wave` carries the stage-gate reminder (change doc, admitted, readied wave before any code edit). `wf-implement-wave` and `wf-close-wave` each add one pointer line naming the single-change variant (Implement feature / Finalize feature) instead of those variants getting their own skills.
   - `wf-memory-review` notes that consolidation, archival, and purge apply only per the prompt's eligibility gates.
   - `wf-evaluate-decision`'s description scopes to structured evaluation of ADR-shaped decisions, not any decision talk, to avoid over-triggering.
   - `wf-council` carries the three-way chooser in one line (Wave Council for code/architecture/trust-boundary artifacts; Archetype Council for prose/naming/AC-formulation/decision-narrative artifacts; standalone red-team review for a single sharp adversarial challenge) plus two boundary sentences keeping it distinct: it is NOT `wf-review-wave` (the OPEN wave's required lanes) and NOT `wf-interrogate-plan` (a change doc before admission). The routing knowledge itself stays in the backing prompts (the archetype prompt's chooser table); the skill points at it.
3. **Gating.** These are **general lifecycle** skills: NOT `guru`-gated (unlike `wf-guru`). Emit whenever the host surface is active (host dir present), per the `1p6lo` host-dir gate.
4. **Catalog/docs.** Add the 10 skills to the AGENTS.md Tier-3 table + `platform-mapping.md` (per host), alongside `wf-guru`/`wf-upgrade`.
5. **Tests + no regression.** Each skill emits valid `SKILL.md` (frontmatter + pointer body) to each host; `description`s are present + pairwise distinct; the `wf-` prefix held; full suite green; docs-lint clean; forward-slash policy held.

## Scope

**Problem statement:** The core lifecycle commands are prose shortcut-phrases only; they should be host-native, discoverable skills via the `1p6lo` registry.

**In scope:** the 10 thin-pointer `SKILL.md` registry entries + their catalog/doc rows + tests.

**Out of scope** (full catalog evaluated with the operator 2026-08-14; each exclusion carries its reason):

- The skill **mechanism** (that's `1p6lo`).
- **Per-kind planning skills** (`wf-plan-bug`, `wf-plan-refactor`, ...): the plan types are one workflow with a scaffold choice, and ten near-identical descriptions would aggravate the mis-routing risk this change already flags. Covered by `wf-plan-feature`'s kind-aware description.
- **Create wave / Add change to wave / Remove change from wave**: each is essentially one MCP call (`wf_create_wave`, `wf_add_change`, `wf_remove_change`) already orchestrated inside the plan and prepare flows.
- **Implement feature / Finalize feature**: descriptions would sit nearly on top of `wf-implement-wave`/`wf-close-wave` (mis-routing risk); covered by pointer lines in those two bodies. Revisit on target-repo demand.
- **Dashboard start/stop/restart**: single tool calls; no workflow to carry.
- **Init Wavefoundry / Migrate to Wavefoundry**: skills are rendered surfaces that exist only after install, so they cannot be the install vehicle; also near-one-time.
- **Migrate journals**: one-time legacy retirement.
- **Dedicated `wf-archetype-council` and `wf-red-team` skills**: their "review this artifact" intents overlap each other and Wave Council too heavily for separate description-matched skills; the `wf-council` router covers all three forms (this supersedes the earlier blanket exclusion of Archetype review, whose objection was auto-matching noise from a dedicated skill).
- **Package Wavefoundry**: meaningful only in the framework source repo, needing repo-conditional gating the registry does not have; deferred with the other maintainer skills (`wf-upgrade` itself ships via the `1p6lo` migration).
- Authoring new seeds for the no-seed commands (each skill points at its existing `docs/prompts/*.prompt.md`; no new seed needed).

## Acceptance Criteria

- [x] AC-1: the 10 skills are registry entries (`1p6lo`), each emitting standard `SKILL.md` (frontmatter `name`/`description` + thin-pointer body) to `.codex/skills/<name>/`, `.claude/skills/<name>/`, `.agents/skills/<name>/` on active hosts, every name `wf-`-prefixed.
- [x] AC-2: each body routes to its backing `docs/prompts/<command>.prompt.md` + the named MCP tool(s) + the step's gate reminder; no duplicated prompt content; the six body-specific requirements in Requirement 2 hold (including `wf-council`'s three-way chooser + boundary sentences).
- [x] AC-3: `wf-plan-feature`'s description enumerates all nine change kinds; no per-kind planning skills exist.
- [x] AC-4: the skills are NOT `guru`-gated (general lifecycle); host-dir-gated per `1p6lo`.
- [x] AC-5: AGENTS.md Tier-3 table + `platform-mapping.md` list the 10 skills per host.
- [x] AC-6: tests cover emission per host + frontmatter/description presence + pairwise-distinct descriptions + pointer targets; full suite green; docs-lint clean; no POSIX/WSL2 regression; forward-slash policy held.

## Tasks

- [x] Add the 10 `Skill` registry entries (name, description, thin-pointer body, gate=general, hosts=all skill hosts).
- [x] Author each thin-pointer body (prompt ref + MCP tool(s) + gate reminder; the six body-specific requirements).
- [x] Catalog/doc rows (AGENTS.md Tier-3 + platform-mapping).
- [x] Tests; full suite + docs-lint.

## Affected Architecture Docs

`N/A`: content entries on the `1p6lo` mechanism + catalog rows.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The 9 skills are the deliverable. |
| AC-2 | required | Thin-pointer (no drift) is the design contract. |
| AC-3 | required | The single kind-aware planning skill is the anti-collision design. |
| AC-4 | required | Correct gating (lifecycle skills aren't guru-gated). |
| AC-5 | important | Catalog/discoverability. |
| AC-6 | required | Tested + no regression. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-19 | Planned. Operator curated the **core loop** (Plan/Prepare/Implement/Review/Close). Thin-pointer skills over the `1p6lo` registry; backing prompts all exist under `docs/prompts/`. Maintainer + review-helper skills deferred. | `docs/prompts/{plan-feature,prepare-wave,implement-wave,review-wave,close-wave}.prompt.md`; depends on `1p6lo` |
| 2026-08-14 | Revived and re-curated with the operator: 5 skills become 9 (adding interrogate-plan, evaluate-decision, memory-review, pause-wave); all names take the `wf-` prefix; tool names corrected to the post-`1t3gt` surface; all nine backing prompt docs verified present; full shortcut catalog re-evaluated with per-exclusion reasons recorded in Scope. | Operator direction in-session; `ls docs/prompts/*.prompt.md` 2026-08-14; `memory-review`/`pause-wave` prompt tool citations verified by grep |
| 2026-08-14 | Tenth skill added, same session: `wf-council`, a router over the three on-demand review forms; depends on `1v877` supplying the third pointer target (`red-team-review.prompt.md`). Supersedes the blanket Archetype exclusion. | Operator direction in-session; chooser table verified at `archetype-council.prompt.md:17-26`; standalone red-team modes verified in `docs/agents/specialists/red-team.md` |
| 2026-08-14 | Implemented. Ten registry entries with a shared `_thin_pointer_body` builder (`wf-council` carries a custom router body); descriptions pairwise distinct and single-line YAML-safe (a live find replaced three descriptions containing `": "`, which breaks strict frontmatter parsers, and a test now forbids the pattern); all twelve skills render to `.codex`/`.claude`/`.agents` and the Claude Code host live-discovered them in-session. Tests extended: distinctness, pointer-target resolution, YAML-safety. Catalogs updated with the full roster. | `render_agent_surfaces.py` `SKILL_REGISTRY`; `SkillRegistryTests` (189 focused tests OK, scratchpad `t1p6lw.log`); AGENTS.md + `platform-mapping.md` skills table |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-19 | Scope to the core 5-step loop (operator-chosen). | Highest-value, focused; proves the registry before expanding to maintainer/review-helper skills. | Comprehensive set now (deferred: more content to author/maintain before the core proves out). |
| 2026-06-19 | Thin-pointer bodies → backing prompt + MCP tool. | Skills stay in sync with the seeds/prompts that own behavior; no duplication/drift. | Inline the full command content (rejected: drift risk). |
| 2026-08-14 | Supersede the core-5 curation: add `wf-interrogate-plan`, `wf-memory-review`, `wf-pause-wave`, `wf-evaluate-decision` (operator-chosen). | Operator named plan review and memory review explicitly; all four are recurring workflows with high loose-phrasing value (a skill earns its slot when it is a recurring workflow, not a single tool call, and benefits from description-matched discovery). | Keep 5 (rejected: operator direction); full catalog (rejected: one-time, single-call, and collision-prone commands excluded per Scope). |
| 2026-08-14 | One kind-aware planning skill instead of ten per-kind skills. | The plan types are one workflow with a scaffold parameter; ten near-identical descriptions would mis-route, and the kind enumeration in one description catches the same phrasings. | Per-kind skills (rejected: description-space pollution for zero new behavior). |
| 2026-08-14 | One `wf-council` router instead of dedicated archetype/red-team skills (operator-proposed). | The three review forms share the "convene a review on this artifact" intent, the routing table already lives in the archetype prompt, and a router with boundary sentences avoids both the auto-matching noise of a dedicated archetype skill and a red-team/interrogate-plan collision. | `wf-archetype-council` + `wf-red-team` as separate skills (rejected: overlapping descriptions, the change's own top risk); omitting the forms entirely (rejected: operator wants them discoverable). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Skill descriptions overlap and the host mis-routes between loop steps. | Pairwise-distinct, keyword-rich third-person `description`s per step (AC-6 asserts distinctness); the interrogate/evaluate pair and the implement/review/close trio are the watch items; single kind-aware planning skill. |
| `wf-evaluate-decision` over-triggers on ordinary decision talk. | Description scoped to structured evaluation of ADR-shaped decisions; revisit at review if noisy in practice. |
| `wf-council` mis-routes against `wf-review-wave` or `wf-interrogate-plan`. | Two explicit boundary sentences in its description (not the required lanes of the OPEN wave; not a change doc before admission); AC-6 distinctness assertion covers the pair. |
| A skill body drifts from its prompt. | Thin pointer to `docs/prompts/<command>.prompt.md` (single source of truth), not duplicated content. |
| Lands before `1p6lo`. | Hard dependency recorded; sequence `1p6lo` first (wave watchpoints). |


## Dependencies

- **Depends on `1p6lo`** (unified skill registry + `SKILL.md` emitter); must land first.
- **Depends on `1v877`** (red-team standalone review command); `wf-council`'s third pointer target (`docs/prompts/red-team-review.prompt.md`) must exist before that skill body lands.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
