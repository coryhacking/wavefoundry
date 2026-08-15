# Red-team standalone review command

Change ID: `1v877-enh red-team-standalone-review-command`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-14
Wave: `1p6lp cross-host-skills`

## Rationale

Red-team already runs standalone in practice but has no operator-facing command. The specialist doc (`docs/agents/specialists/red-team.md`, rendered from seed `225-red-team.prompt.md`) defines nine modes, of which only two are council-bound (`council-adversarial-primer`, `council-seat`); the other seven are standalone lenses with operating invariants and an Output Shape already specified. Yet the council prompts tell operators to "reach for `red-team`" (`archetype-council.prompt.md:17`, `:26`, `:89`) with nothing to reach for: no shortcut phrase in the catalog, no `docs/prompts/red-team-review.prompt.md`, and no stated contract for where standalone output lands or what it may not certify.

The gap becomes load-bearing with wave `1p6lp`: the `wf-council` skill (`1p6lw`) routes between three review forms (Wave Council, Archetype Council, red-team in isolation), and a thin-pointer skill needs a real prompt doc behind each route. This change promotes red-team-in-isolation to a first-class command so the third route resolves.

## Requirements

1. **New canonical seed, rendering an operator prompt doc.** Add a seed in the operator-command band (e.g. `177-red-team-review.prompt.md`; pick the free number at implement) that renders `docs/prompts/red-team-review.prompt.md` with shortcut phrases **Red-team review** / **Red team this**. The prompt defines:
   - **Input:** any artifact (change doc, code, ADR, prose, design, workflow, decision narrative).
   - **Mode selection:** choose from the specialist doc's standalone modes (`abuse-path-review`, `failure-pressure-test`, `option-challenge`, `technology-evaluation`, `workflow-challenge`, `feature-definition-challenge`, `design-provocation`), or apply a better-grounded lens per the specialist doc's own "not an exhaustive ceiling" clause. The council-bound modes (`council-adversarial-primer`, `council-seat`) are named as out of scope for standalone invocation.
   - **Output:** the specialist doc's Output Shape, unchanged; this command adds no new output schema.
   - **Recording:** when run against a wave artifact, record the outcome as a `## Review Checkpoints` entry in that wave's record; otherwise output is conversation-level. No entry is required to invoke it.
   - **Authority boundary:** the command records **no signoffs** and satisfies **no gate** (mirroring the Archetype prompt's "does not record `wave-council-readiness`" boundary); credible security findings are handed to `security-reviewer` per the specialist doc's Role Boundaries.
2. **Cross-references resolve.** Update at source, under `seed_edit_allowed`: seed `236-archetype-council.prompt.md` and seed `237-council-review.prompt.md` point their "reach for `red-team`" guidance at the new command; seed `225-red-team.prompt.md` gains one line naming the standalone entry point. Re-render the three prompt docs.
3. **Catalog rows.** Add the command to `docs/prompts/index.md` and the AGENTS.md shortcut-phrase table.
4. **Prompt-surface manifest.** Regenerate whatever manifest or render pass tracks `docs/prompts/` membership (e.g. `docs/prompts/prompt-surface-manifest.json`) so the new doc is a tracked surface, not drift.
5. **No behavior change to councils.** The primer and seat modes, council flows, and review-policy machinery are untouched; this is packaging for a capability the specialist doc already defines.

## Scope

**Problem statement:** Red-team in isolation is documented as a reach-for but is not invocable: no shortcut, no prompt doc, no standalone recording/authority contract; the `wf-council` router (`1p6lw`) needs the route to resolve.

**In scope:**

- The new seed + rendered `docs/prompts/red-team-review.prompt.md` (Requirement 1).
- Cross-reference updates in seeds 236/237/225 + re-render (Requirement 2).
- Catalog rows + prompt-surface manifest (Requirements 3 and 4).

**Out of scope:**

- Any change to the specialist doc's modes, invariants, or Output Shape (the standalone contract reuses them as-is).
- Any change to council flows, review-policy gating, or signoff vocabulary.
- The `wf-council` skill itself (that is `1p6lw`; this change only supplies its third pointer target).
- A dedicated `wf-red-team` skill (rejected in `1p6lw`: the router absorbs the overlapping "review this artifact" intent).

## Acceptance Criteria

- [x] AC-1: the new seed exists and renders `docs/prompts/red-team-review.prompt.md` carrying the shortcut phrases, the standalone-mode selection guidance, the Output Shape reference, the recording rules, and the explicit no-signoff/no-gate boundary.
- [x] AC-2: the "reach for `red-team`" guidance in the rendered `archetype-council.prompt.md` and `council-review.prompt.md` points at the new command; the specialist doc names the standalone entry point; no remaining reach-for lacks a resolvable target.
- [x] AC-3: `docs/prompts/index.md` and the AGENTS.md shortcut table list the command.
- [x] AC-4: the prompt-surface manifest (or equivalent tracked-surface mechanism) includes the new doc; full suite green; docs-lint clean.
- [x] AC-5: the rendered prompt states that the command records no signoffs and satisfies no gate, and standalone invocation adds no review-authority records.

## Tasks

- [x] Author the new seed (operator-command band; free number chosen at implement) under `seed_edit_allowed`.
- [x] Update seeds 236, 237, 225 cross-references under the same gate cycle.
- [x] Re-render the prompt surfaces; regenerate the prompt-surface manifest.
- [x] Catalog rows: `docs/prompts/index.md` + AGENTS.md shortcut table.
- [x] Verify: docs-lint, full suite, reach-for resolution sweep (grep for `red-team` reach-fors with no target).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| seed       | implementer | —          | Goal: the new seed + 236/237/225 cross-refs authored under one `seed_edit_allowed` cycle; renders clean |
| surface    | implementer | seed       | Goal: prompt docs re-rendered, manifest regenerated, catalog rows added; lint + suite green |


## Serialization Points

- `.wavefoundry/framework/seeds/236-archetype-council.prompt.md`
- `.wavefoundry/framework/seeds/237-council-review.prompt.md`
- `.wavefoundry/framework/seeds/225-red-team.prompt.md`
- `docs/prompts/`
- `AGENTS.md`

## Affected Architecture Docs

`N/A`: this adds an operator prompt surface and catalog rows; no code boundary, flow, or verification architecture changes. The review-system overview seed (`007`) is intentionally untouched because the command grants no authority.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The command is the deliverable. |
| AC-2 | required  | Dangling reach-fors are the defect being fixed. |
| AC-3 | important | Discoverability; the `wf-council` route works without the catalog row but operators cannot find the phrase. |
| AC-4 | required  | Untracked prompt surfaces are drift. |
| AC-5 | required  | The authority boundary is the safety property. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-14 | Planned per operator direction ("change that so it's not only a seat") during the `1p6lp` skill re-curation. Census grounded: specialist doc has 7 standalone modes + Output Shape; reach-fors at `archetype-council.prompt.md:17/:26/:89` and `council-review.prompt.md:21` have no operator command behind them. | `docs/agents/specialists/red-team.md`; seeds 225/236/237 located by grep |
| 2026-08-14 | Implemented. Seed `177-red-team-review.prompt.md` authored; rendered `docs/prompts/red-team-review.prompt.md`; cross-refs updated in seeds 236/237/225 and their rendered docs; catalog rows in `index.md` + AGENTS.md; manifest row added (note: the manifest's `public_prompt_surface` already omitted `evaluate-decision`/`archetype-council`, a pre-existing inconsistency left as-is). Live find during implementation: seed 225 defines an eighth standalone mode, `improvement-review`, that the rendered specialist doc lagged; the drift was repaired by mirroring the seed section into `docs/agents/specialists/red-team.md`, and `improvement-review` is the command's default mode row. `wf_get_prompt('Red-team review')` resolves; reach-for sweep returns zero unresolved sites; docs-lint clean. | Seed 177; grep sweep 2026-08-14; `wf_get_prompt` executed |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-14 | Promote red-team-in-isolation to an operator command via a new seed in the operator-command band. | The capability exists (7 standalone modes, invariants, Output Shape); only invocation packaging is missing, and the `wf-council` router needs a resolvable third target. | Leave as a reach-for (rejected: `wf-council` would route to a specialist doc, blurring role vs command surfaces); extend seed 225 (rejected: 225 renders a role doc consumed by lanes; operator commands live in the 17x prompt band). |
| 2026-08-14 | The command records no signoffs and satisfies no gate. | Red-team's value is the challenge, not certification; the specialist doc already hands security findings to `security-reviewer`, and Archetype sets the precedent for a no-authority review command. | Let it record a lane signoff (rejected: creates a self-certifying adversarial lane and expands review authority in a packaging change). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| "Red team this" phrasing auto-matches too loosely once surfaced via `wf-council`. | The skill router (`1p6lw`) owns matching; this prompt is explicit-invocation like every other shortcut. Revisit the router description if noisy. |
| Seed numbering collision in the operator band. | Number chosen at implement against the then-current seed listing. |
| Prompt-surface manifest or render tests fail on the new doc. | Requirement 4 makes manifest regeneration part of the change; AC-4 gates on suite + lint. |
| Scope creep into council mechanics. | Requirement 5 pins councils untouched; out-of-scope list names primer/seat modes. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
