# Strip wavefoundry-internal ADR references from shipped seeds

Change ID: `1p8xk-bug strip-internal-adr-refs-from-seeds`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-29
Wave: `1p8xm downstream-upgrade-fixes`

## Rationale

The stage-gate anti-drift guard (`1p8t5`, shipped in 1.9.7) added four **actionable references to the wavefoundry-internal ADR `1p8t4`** into shipped seeds. Seeds ship to every target repo, but `docs/architecture/decisions/1p8t4-adr stage-gate-canonical-structure.md` exists only in the wavefoundry self-host repo — so a consumer's upgrade reads `See …/1p8t4-adr …` and follows a **dangling reference**. Confirmed in the field: teton's 1.9.7 upgrade correctly split its consolidated stage-gate table (the *behavior* is right), but its handoff cited "ADR 1p8t4" — a doc teton does not have.

The leaked references:

- `seed-050` task 17 — `(standing decision, `docs/architecture/decisions/1p8t4-adr …`)`
- `seed-160` line ~127 — `— see ADR `1p8t4``
- `seed-160` line ~348 — `See `docs/architecture/decisions/1p8t4-adr …`.`
- `seed-009` — `See `docs/architecture/decisions/1p8t4-adr …`.`

The seed *rationale* is already self-contained ("referenced by literal name across host docs; the one carve-out from preserve-repo-grown"); only the ADR pointers must go. The ADR stays in our repo as our internal decision record.

## Requirements

1. **Remove the four `1p8t4` ADR references** from `seed-050`, `seed-160` (both occurrences), and `seed-009`, leaving the surrounding self-contained guidance intact (no behavior change to the stage-gate reconciliation).
2. **Do not touch the generic `docs/architecture/decisions/` references** elsewhere in the seeds (the directory, `template.md`, `README.md` — downstream repos have those, seeded by `seed-040`). Only the specific wavefoundry-internal ADR-by-id/path pointers are removed.
3. **No shipped seed should reference a specific internal ADR/wave/change ID by an actionable "See <path>" link.** Verify no remaining `1p8t4` (or `…-adr <slug>.md` path) reference exists in `.wavefoundry/framework/seeds/`.

## Scope

**Problem statement:** shipped seeds contain dangling pointers to a wavefoundry-internal ADR that downstream repos lack.

**In scope:**

- `seed-050`, `seed-160`, `seed-009` — remove the four `1p8t4` references.

**Out of scope:**

- The ADR `1p8t4` itself (stays — it's our internal record) and the wavefoundry-local change docs that reference it (not shipped).
- Generic `docs/architecture/decisions/` directory/template/README references in any seed (legitimate).
- Inline parenthetical wave-ID provenance comments already present across seeds (non-actionable; not in scope).

## Acceptance Criteria

- [x] AC-1: the four `1p8t4` references are removed from `seed-050`, `seed-160` (×2), and `seed-009` (plus a fifth — the `(ADR 1p8t4)` parenthetical in the seed-009 heading); the surrounding fixed-contract / carve-out guidance reads correctly without them.
- [x] AC-2: `grep -r "1p8t4" .wavefoundry/framework/seeds/` returns nothing; no seed contains a `docs/architecture/decisions/<id>-adr …md` actionable pointer. (verified clean)
- [x] AC-3: the generic `docs/architecture/decisions/` (directory / `template.md` / `README.md`) references in other seeds are unchanged. (grep confirms they remain)
- [x] AC-4: the stage-gate reconciliation behavior is unchanged (still re-establishes the two named sections); the full framework suite + docs-lint stay green. (suite 3702 ok; docs-lint ok)

## Tasks

- [x] Edit `seed-050` task 17 — drop the `(standing decision, …1p8t4…)` pointer (kept "a standing decision: do not add a literal-heading validator" inline) (under `seed_edit_allowed`).
- [x] Edit `seed-160` (×2) — drop the `see ADR 1p8t4` / `See …1p8t4…` clauses.
- [x] Edit `seed-009` — drop the `See …1p8t4…` clause AND the `(ADR 1p8t4)` heading parenthetical.
- [x] Grep-verify no `1p8t4` / internal-ADR-path reference remains in seeds. (clean)
- [x] Run the framework suite + docs-lint; confirm green. (suite 3702 ok; docs-lint ok)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| strip the four ADR refs | implementer | — | `seed_edit_allowed`; wording-only |
| grep-verify + suite/docs-lint | qa-reviewer | strip | AC-2/AC-4 |

## Serialization Points

- All edits are seed prose — open `seed_edit_allowed` for the pass; keep the surrounding guidance intact.

## Affected Architecture Docs

`N/A` — removes dangling references from seed prose; no boundary/flow/verification change. (The internal ADR `1p8t4` is unchanged.)

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The actual removal. |
| AC-2 | required | No dangling internal-ADR pointer survives in shipped seeds. |
| AC-3 | required | Don't over-strip the legitimate generic references. |
| AC-4 | required | Behavior unchanged; suite + docs-lint green. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-29 | Drafted from a teton 1.9.7-upgrade field report (handoff cited the missing ADR 1p8t4). Confirmed four `1p8t4` pointers shipped in seed-050/160(×2)/009; the split behavior is correct, only the references dangle downstream. | `seed-050:66`, `seed-160:127,348`, `seed-009:62`; lesson `feedback-seeds-no-internal-artifact-refs`. |
| 2026-06-29 | Implemented. Stripped the four `See …1p8t4…` / `see ADR 1p8t4` pointers + a fifth `(ADR 1p8t4)` heading parenthetical in seed-009; kept the self-contained rationale. `grep -r 1p8t4 seeds/` now empty; generic `decisions/` refs intact. | seed-050/160/009 diffs; grep clean; suite 3702 ok; docs-lint ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-29 | Strip the ADR pointers; keep the rationale inline. | Seeds must be self-contained for downstream; the WHY is already stated without the link. | Ship the ADR to downstream repos (rejected — it's a wavefoundry-internal decision record, not a per-project artifact); leave as-is (rejected — dangling ref). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Over-stripping a legitimate generic `decisions/` reference. | Target only the `1p8t4`-specific pointers; AC-3 asserts the generic references remain. |
| Removing the link weakens the rationale. | The carve-out reasoning is already stated inline in each location; the link was redundant. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
