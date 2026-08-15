# wf-code-cleanup skill, doc-gated like wf-package

Change ID: `1ve3b-enh wf-code-cleanup-skill`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-15
Wave: 1ve3a package-skill

## Rationale

Operator direction (2026-08-15): add a skill for the **Codebase cleanup review** command with a name explicit about *code* cleanup. Chosen name: **`wf-code-cleanup`** (shorter than `wf-code-cleanup-review`; the description carries the recommend-only review framing so the name does not overpromise mutation).

The backing prompt (`docs/prompts/codebase-cleanup-review.prompt.md`, shortcuts **Codebase cleanup review** / **Dead code review**) is the code-reviewer's whole-codebase maintainability sweep: dead code, duplication, complexity, abandoned files, technical debt, graph-based, recommend-only. It has among the highest loose-phrasing traffic of any command not yet skill-covered ("find dead code", "what can we delete", "clean up the codebase"), and it is not covered by `wf-council`, which convenes reviews on one artifact rather than sweeping the tree.

**Gate:** no canonical seed references `codebase-cleanup-review` (verified 2026-08-15), so the prompt doc is a repo-local surface here and absent from target repos. The entry therefore uses the same `requires_doc` gate `1vbpl` introduces, on `docs/prompts/codebase-cleanup-review.prompt.md`: the skill renders wherever the cleanup surface actually exists (this repository today) and lights up automatically in any repo that gains the prompt later. This makes three users of the gate (`wf-guru`, `wf-package`, `wf-code-cleanup`), reinforcing the generalization.

## Requirements

1. **Register `wf-code-cleanup`** in the skill registry, `requires_doc="docs/prompts/codebase-cleanup-review.prompt.md"`:
   - **Description** (single-line, YAML-safe, no `": "`): keyword-rich for the loose phrasings (dead code, duplication, abandoned files, technical debt, cleanup sweep); states it is a recommend-only review that proposes keep/simplify/remove and changes nothing itself; distinct from `wf-council` (one-artifact reviews) and `wf-review-wave` (the open wave's required lanes).
   - **Thin-pointer body** to the backing prompt with two reminders: the sweep is recommend-only and safe (graph-based; it proposes, the operator disposes); acting on a recommendation is ordinary lifecycle work (plan, admit, implement), never an inline mass deletion. No duplicated prompt content.
2. **Catalog rows.** `docs/agents/platform-mapping.md` skills table row with the gate; AGENTS.md skills paragraph mention.
3. **Tests.** Gate polarity both directions (prompt doc present emits on active hosts; absent emits nothing); the `1p6lw` registry invariants (name policy, distinct + YAML-safe descriptions, pointer-target resolution) cover the entry automatically. Full suite green; docs-lint clean.

## Scope

**Problem statement:** The highest-traffic uncovered command has no skill, and its backing prompt exists only where the surface was authored, so the entry must be doc-gated.

**In scope:** the one registry entry + body, catalog rows, gate-polarity tests.

**Out of scope:**

- The `requires_doc` mechanism itself (that is `1vbpl`; this change consumes it).
- Seeding `codebase-cleanup-review.prompt.md` to target repos (a separate decision; the gate makes this change indifferent to it).
- `wf-config-review` (evaluated as worthwhile, not yet operator-chosen).
- Any change to the cleanup prompt's own workflow.

## Acceptance Criteria

- [x] AC-1: `wf-code-cleanup` is a registry entry gated on `docs/prompts/codebase-cleanup-review.prompt.md`; it renders on this repository's skill hosts, and a test proves a repo without the doc emits no `wf-code-cleanup` anywhere.
- [x] AC-2: the description is keyword-rich, recommend-only-framed, and pairwise distinct from every other entry; the body is a thin pointer carrying the recommend-only and lifecycle-for-deletions reminders.
- [x] AC-3: `platform-mapping.md` skills table + AGENTS.md skills paragraph list `wf-code-cleanup` with its gate.
- [x] AC-4: gate-polarity tests in both directions; full suite green; docs-lint clean.

## Tasks

- [x] Add the `wf-code-cleanup` registry entry (description + thin-pointer body) using the `1vbpl` gate.
- [x] Catalog rows (platform-mapping + AGENTS.md).
- [x] Tests (gate polarity both directions); re-render this repo; full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| entry      | implementer | —          | Goal: the gated registry entry, description distinctness held |
| surface    | implementer | entry      | Goal: catalogs, re-render, tests, suite + lint green |


## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `docs/agents/platform-mapping.md`
- `AGENTS.md`

## Affected Architecture Docs

`N/A`: one gated entry on the wave-`1p6lp` registry; catalog rows only.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The entry and its negative-direction gate proof are the deliverable. |
| AC-2 | required  | Recommend-only framing prevents the name overpromising mutation; distinctness is the standing anti-collision contract. |
| AC-3 | important | Catalog/discoverability. |
| AC-4 | required  | The negative direction proves target repos stay clean. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-15 | Planned per operator direction (name made code-explicit; `wf-code-cleanup` chosen over the longer `wf-code-cleanup-review`). Gate premise verified: zero seed references to `codebase-cleanup-review`, so the prompt is repo-local and target repos lack it. | `grep -rln codebase-cleanup-review .wavefoundry/framework/seeds/` returns nothing, 2026-08-15 |
| 2026-08-15 | Interrogated (batch) before implementation. Four branches walked, all resolved: the name is operator-settled; description collision risk is bounded by the boundary phrasing requirement plus the standing pairwise-distinctness test; the gate-polarity fixture trivially controls doc absence in a temp repo; whether to seed the cleanup prompt to target repos remains a deliberately deferred separate decision, and the doc gate keeps this change correct under either outcome. One out-of-scope observation recorded for the record, not a blocker: in a target repo whose upgrade doc-reconciliation arm lags, `wf-council`'s third pointer (`red-team-review.prompt.md`) can briefly dangle, the same two-arms caveat wave `1p6lp` already disclosed; a future change could doc-gate nothing or extend `requires_doc` thinking there, but no evidence yet warrants it. Zero open operator questions. | Change doc Scope/Risks sections; wave `1p6lp` transition notes |
| 2026-08-15 | Implemented. `wf-code-cleanup` registered on the `1vbpl` gate with the recommend-only description (boundary sentences against `wf-council` and `wf-review-wave`) and the two-reminder body; covered by the shared gate-polarity and gate-equals-pointer tests plus the standing invariants; catalog rows landed; skill live-discovered by the Claude Code host in-session after re-render. | `render_agent_surfaces.py` `SKILL_REGISTRY`; scratchpad `t1ve3a.log` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-15 | Name `wf-code-cleanup`. | Operator wants code-explicit and short; the recommend-only framing lives in the description where hosts match on it anyway. | `wf-code-cleanup-review` (rejected: longer, per operator preference); `wf-cleanup-review` (rejected: not code-explicit); `wf-code-review` (rejected: collides with the review-lane vocabulary). |
| 2026-08-15 | Doc-gate on the backing prompt rather than shipping ungated. | The prompt is not seeded to target repos, so an ungated skill would dangle there; the gate follows the capability and needs no new mechanism beyond `1vbpl`. | Ungated entry (rejected: dangling pointer in every target repo); seed the prompt to targets first (deferred: separate curation decision, and the gate makes this change indifferent to its outcome). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The name reads as a mutating command. | Description and body state recommend-only; the body routes deletions through the ordinary lifecycle. |
| Description collides with `wf-council` or `wf-review-wave`. | Boundary phrasing in the description; the pairwise-distinctness test covers it. |
| Depends on `1vbpl`'s gate landing first. | Same wave, sequenced entry-after-mechanism; the wave watchpoints record the ordering. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
