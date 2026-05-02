# Journal: Signal Over Log

Change ID: `12b9v-feat journal-signal-over-log`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-02
Wave: `12b9x journal-signal-over-log`

## Rationale

Agent and persona journals in practice drift toward activity logs — wave IDs, change IDs, "wave X closed" records — rather than durable operating memory. This pattern erodes journal value: future agents retrieving the journal find a git-history transcript instead of guidance that defines how this actor should think, what risks it must watch for, and what hard-won lessons shape its judgment.

The root cause is structural: the `Recent Captures` section name, its chronological ordering, and the absence of a strong filter gate all invite append-style logging. The distillation prompt catches it at closure but does not prevent the pattern from forming. The current wave-coordinator journal is a clear instance: `Recent Captures` is a near-complete wave ledger.

The upgrade path is also unaddressed: existing journals in deployed repos will keep the old shape until someone manually refactors them.

## Requirements

1. seed-006 must name the activity-log anti-pattern explicitly with concrete before/after examples so agents can recognize it before writing.
2. seed-130 must rename `Recent Captures` to `Active Signals`, add a filter gate question ("would this still matter to a new agent inheriting this role with no access to git history?"), and make wave-completion summaries an explicitly disqualified entry type.
3. seed-130's journal section ordering must put **Operating Identity** and **Distillation** before `Active Signals` so durable identity is front-loaded.
4. seed-210 must add an explicit distillation step: identify and delete activity-log entries (wave-closed, change-shipped records) — that information lives in git and wave docs.
5. seed-160 (upgrade) must include a journal upgrade step: when upgrading, rename `Recent Captures` → `Active Signals`, run a distillation pass to remove activity-log entries, and verify the `Operating Identity` and `Distillation` sections are populated and leading.
6. The in-repo wave-coordinator journal must be updated to reflect the new shape: activity-log entries stripped, `Recent Captures` renamed, sections reordered.
7. The `docs/agents/journals/README.md` template (if present) must be updated to match the new section ordering and filter gate language.

## Scope

**Problem statement:** Journals accumulate wave/change activity records instead of durable operating memory, making them useless as identity and guidance documents for future agents.

**In scope:**

- seed-006: anti-pattern section with examples
- seed-130: section rename, filter gate, section reordering
- seed-210: activity-log deletion step
- seed-160: journal upgrade sub-step
- All five in-repo journals: `wave-coordinator.md`, `wave-coordinator-persona.md`, `framework-operator.md`, `implementer.md`, `planner.md`
- `docs/agents/journals/README.md` template update

**Out of scope:**

- Changing the salience band taxonomy
- Changing the memory taxonomy (procedural/episodic/semantic/working)
- Persona journal content beyond reordering and entry cleanup
- Any automation or lint rule for journal entries

## Acceptance Criteria

- AC-1: seed-006 contains an explicit "activity-log anti-pattern" section with a disqualified example and a qualifying example.
- AC-2: seed-130 uses `Active Signals` (not `Recent Captures`) and includes the filter gate question.
- AC-3: seed-130's seeded journal section order is: Operating Identity → Salience Triggers → Distillation → Active Signals → Promotion Evidence → Retirement And Supersession.
- AC-4: seed-210 contains a step explicitly naming deletion of activity-log entries as a required distillation action.
- AC-5: seed-160 contains a journal upgrade sub-step covering rename, distillation pass, and section-order verification.
- AC-6: All five in-repo journals (`wave-coordinator.md`, `wave-coordinator-persona.md`, `framework-operator.md`, `implementer.md`, `planner.md`) use `Active Signals` (not `Recent Captures`), contain no wave-closed/change-shipped log entries in that section, and have sections in the correct order.
- AC-7: `docs/agents/journals/README.md` reflects the new section order and filter gate if it contains a structural template.

## Tasks

1. Edit seed-006: add "The Activity-Log Anti-Pattern" subsection under "What Journals Are For".
2. Edit seed-130: rename section, add filter gate text, reorder the required journal sections list, update the bootstrap example format.
3. Edit seed-210: add step 0 (or prepend to step 1): "Delete activity-log entries — wave-closed records, change-shipped summaries, and routine success notes. This information belongs in git history and wave docs, not journals."
4. Edit seed-160: add a journal upgrade sub-step to the upgrade checklist (after hook regeneration, before drift detection).
5. Update all five in-repo journals — `wave-coordinator.md`, `wave-coordinator-persona.md`, `framework-operator.md`, `implementer.md`, `planner.md`: rename `Recent Captures` → `Active Signals`, strip activity-log entries, verify section order.
6. Update `docs/agents/journals/README.md` template if it carries structural section guidance.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| seed-edits | wave-coordinator | — | seeds 006, 130, 210, 160 in one pass (all gate-guarded) |
| journal-cleanup | wave-coordinator | seed-edits | in-repo journal + README update |

## Serialization Points

- Gate `seed_edit_allowed` must be open for all seed edits; close immediately after.
- Journal cleanup reads the updated seed-130 section order before rewriting the in-repo journal.

## Affected Architecture Docs

N/A — no boundary, flow, or verification architecture is affected.

## AC Priority

| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | Anti-pattern must be named or agents will keep writing logs |
| AC-2 | required     | Section rename is the primary structural fix |
| AC-3 | required     | Section order determines what agents read first |
| AC-4 | required     | Distillation step must actively delete log entries |
| AC-5 | required     | Upgrade path ensures deployed repos get the fix |
| AC-6 | required     | In-repo journals are the concrete evidence the fix works |
| AC-7 | important    | README template consistency, but journals are the real signal |

## Progress Log

| Date       | Update              | Evidence |
| ---------- | ------------------- | -------- |
| 2026-05-02 | Implementation complete | All ACs satisfied: seeds 006/130/210/160 updated, five in-repo journals cleaned, README updated, docs-lint clean |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-02 | Rename `Recent Captures` → `Active Signals` rather than removing the section | Forces an identity shift without breaking the capture flow; section name signals intent to future agents | Remove section entirely (too disruptive); keep name but add warnings (insufficient) |
| 2026-05-02 | Reorder sections to put Operating Identity + Distillation before Active Signals | Durable identity should be front-loaded; activity belongs at the bottom | No reorder (doesn't fix the structural pull toward log-first reading) |
| 2026-05-02 | Embed upgrade step in seed-160 rather than a separate migration prompt | Upgrades already run seed-160; adding a separate prompt creates another surface to maintain | Separate migration prompt (overkill for a rename + cleanup pass) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Existing deployed repos have journals with `Recent Captures` — agents on old packs won't know to rename | seed-160 upgrade step covers this for anyone who upgrades; legacy journal shape is tolerated until upgrade |
| Stripping activity-log entries from wave-coordinator journal loses the wave history | Wave history lives in `docs/waves/` and git; journals are not the authoritative record |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
