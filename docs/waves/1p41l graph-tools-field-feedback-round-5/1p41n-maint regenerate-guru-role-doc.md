# Regenerate docs/agents/guru.md From Seed-211 to Clear Render Drift

Change ID: `1p41n-maint regenerate-guru-role-doc`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-08
Wave: 1p41l graph-tools-field-feedback-round-5

## Rationale

`.wavefoundry/framework/seeds/211-guru.prompt.md` is a **generator seed** — its preamble declares `**Output path:** docs/agents/guru.md` and instructs an agent to write the role-definition body to `docs/agents/guru.md` with a fixed metadata header. This regeneration is an agent-executed step during install/upgrade, not a deterministic render script (`render_agent_surfaces.py` only renders the auto-Guru *routing* marker blocks in other host files; it does not produce the guru.md body).

The seed received substantial content across waves `1p2q3` (round-4), the round-5 receiver-resolution work, and the `130rj` graph-tools rounds, but `docs/agents/guru.md` was never regenerated from those updates. The rendered role doc is **380 lines vs the 694-line seed** and is missing entire sections agents depend on (grep counts in `guru.md` = 0 for each):

- the **Question-type recipes** section (`If I change X, what breaks?`, `Where does this advice/AOP method actually get called?`, etc.)
- `hub_node_id` stable-reference guidance (community_id renumbers across rebuilds)
- the `betweenness_computed` / `betweenness_skipped_reason` observability note
- the `code_graph_community` size-signal table (small/medium/large thresholds)

This drift is the **likely root cause of the Aceiss field report itself**: an external team reading a stale `guru.md` (or running an older framework version) perceives shipped guidance as missing — which is exactly the §4.x/§5 pattern the round-5 grounding found. Regenerating from the current seed (which, after `1p41m`, also carries the betweenness-dominated note) brings the role doc current.

## Requirements

1. Regenerate `docs/agents/guru.md` from the current `211-guru.prompt.md`: take the role-definition body (everything after the seed's preamble `---` separator) and write it to `docs/agents/guru.md`, prepended with the seed-mandated metadata header.
2. The metadata header must match the seed's "Generated file header" block exactly: `# Guru`, `Owner: Engineering`, `Status: active`, `Role: guru`, `Category: specialist`, `Last verified: <regeneration date>`.
3. After regeneration, `guru.md` contains the Question-type recipes, `hub_node_id` guidance, `betweenness_computed`/`betweenness_skipped_reason` note, the community size-signal table, and (from `1p41m`) the `betweenness_dominated_by_generated` anti-pattern.
4. No content authored beyond the seed — this is a faithful regeneration, not an edit of guidance. Any guidance change belongs in the seed first (`1p41m` / future changes), per the seed-first doc workflow.

## Scope

**Problem statement:** `docs/agents/guru.md` is a stale render of `211-guru.prompt.md`, ~300 lines behind, missing the recipes / size-signals / betweenness-observability sections.

**In scope:**

- Regenerate `docs/agents/guru.md` from seed-211; set `Last verified` to the regeneration date.

**Out of scope:**

- Editing seed-211 *content* (that is `1p41m` and is a precondition).
- The auto-Guru routing surfaces rendered by `render_agent_surfaces.py` (AGENTS.md bullets, `.cursor` rules, `.claude/agents/guru.md`, `.codex` skill) — unchanged.

## Acceptance Criteria

- [x] AC-1: `docs/agents/guru.md` body matches the current `211-guru.prompt.md` role-definition body (content after the seed preamble), with the seed-mandated metadata header.
- [x] AC-2: `grep` in `guru.md` returns ≥1 hit each for `Question-type recipes`, `hub_node_id`, `betweenness_computed`, and `betweenness_dominated_by_generated`.
- [x] AC-3: `docs-lint` clean; `guru.md` retains required role-doc metadata (`Owner`/`Status`/`Role`/`Category`/`Last verified`) and passes the role-doc validators.
- [x] AC-4: The regeneration introduced no collateral edits — it writes only `docs/agents/guru.md` (body == seed-211 role body + mandated header) and leaves the `render_agent_surfaces` routing markers and other agent surfaces untouched. (The shared multi-wave working tree also carries unrelated edits from concurrent changes — `1p41m`'s `mcp-tool-surface.md`/seed edits, other waves — not attributable to this regeneration.)

## Tasks

- [x] Confirm `1p41m` is implemented (seed-211 carries the betweenness note).
- [x] Read the current seed-211 body; write `docs/agents/guru.md` with the mandated header and the seed body; set `Last verified` to today.
- [x] Verify AC-2 greps and run `wave_validate` / docs-lint.

## Agent Execution Graph


| Workstream      | Owner       | Depends On | Notes |
| --------------- | ----------- | ---------- | ----- |
| guru.md regen   | Engineering | 1p41m      | Faithful regeneration from seed body |


## Serialization Points

- `211-guru.prompt.md` must be final (post-`1p41m`) before regeneration so the regenerated doc carries the betweenness note.

## Affected Architecture Docs

N/A — regeneration of a role doc from its generator seed; no architecture change.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The regeneration from the seed body is the change |
| AC-2 | required  | Greps verify the accumulated drift is actually closed |
| AC-3 | required  | Role-doc metadata + docs gate must pass |
| AC-4 | important | Guards against collateral edits to other agent surfaces |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-07 | Implemented: regenerated `docs/agents/guru.md` from seed-211 (380 → 682 lines) via faithful body copy + mandated header. | guru.md greps present: `Question-type recipes`, `hub_node_id` (×3), `betweenness_computed`, `betweenness_dominated_by_generated`; metadata header intact; only guru.md changed; docs-lint ok |
| 2026-06-08 | Re-verified at pre-close review: `guru.md` body is byte-identical to the current seed-211 role body (incl. `1p41m`'s betweenness note); `Last verified: 2026-06-08`. Faithful render confirmed current — no re-authoring. | `diff` of guru.md body (lines 8-682) vs seed body (lines 22-696) = 0 (675 lines each); AC-2 greps present; docs-lint ok |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-07 | Regenerate rather than hand-patch missing sections | Seed is the single source of truth; hand-patching reintroduces drift | Manual port of just the missing sections (rejected — drifts again) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Regeneration drops a local hand-edit that was never in the seed | Diff old vs new guru.md before commit; if a local-only paragraph exists, promote it to the seed first |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
