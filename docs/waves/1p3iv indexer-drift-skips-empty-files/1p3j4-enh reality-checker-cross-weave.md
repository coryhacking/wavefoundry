# Reality-checker routes to State And Assumption Correctness patterns

Change ID: `1p3j4-enh reality-checker-cross-weave`
Change Status: `implemented`
Owner: framework-maintainer
Status: implemented
Last verified: 2026-06-05
Wave: 1p3iv indexer-drift-skips-empty-files

## Rationale

`seed-221` (code-reviewer) gained 7 State And Assumption Correctness patterns in change `1p3ix`. The reality-checker's native frame — "does the assumption actually hold across all inputs?" — is the same frame from a different stance: the code-reviewer asks "is this code correct under all assumed inputs?"; the reality-checker asks "are the assumed inputs the only ones the system will see?" Same root, different entry points.

Cross-weaving (cross-reference, not duplication) so a reality-checker reviewer can route to the canonical patterns when assumption-falsifiability is the dominant concern. Patterns stay single-sourced in `seed-221`; `seed-216` carries pointers and applies-when hints so the reviewer doesn't have to remember which seed the patterns live in.

## Requirements

1. `seed-216` gains a new section `## State And Assumption Correctness Patterns (Cross-Reference)` between `## Focus Areas` and `## Do Not`.
2. The section lists all 7 patterns by name with their applies-when hints, references `seed-221` for full definitions, and explains the cross-stance routing (code-reviewer owns the canonical pattern definitions; reality-checker routes assumption-audit findings to them).
3. Pattern text is NOT duplicated — only names, applies-when hints, and a pointer to `seed-221`.
4. Other sections of `seed-216` are unchanged.

## Scope

**Problem statement:** Reality-checker reviewers conducting an `assumption-audit` have no routing into the State And Assumption Correctness patterns in `seed-221`. Without the cross-reference, the patterns are discoverable only by reviewers who already know `seed-221`'s structure.

**In scope:**

- One new section in `seed-216`.
- CHANGELOG bullet under `[1.5.0]` `### Changed`.

**Out of scope:**

- Duplicating pattern definitions into `seed-216`.
- Restructuring `seed-216`'s other sections.

## Acceptance Criteria

- [x] AC-1: `seed-216` contains `## State And Assumption Correctness Patterns (Cross-Reference)` between `## Focus Areas` and `## Do Not`.
- [x] AC-2: All 7 pattern names appear in the section with their applies-when hints.
- [x] AC-3: Section references `seed-221` as the canonical source; does not duplicate pattern descriptions.
- [x] AC-4: `docs-lint` returns clean.

## Tasks

- [x] Edit `seed-216`: add cross-reference section between Focus Areas and Do Not.
- [x] Run docs-lint.
- [x] Add CHANGELOG bullet under `[1.5.0]` `### Changed`.

## Affected Architecture Docs

N/A — single-seed cross-reference addition.

## AC Priority


| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | The new section IS the change. |
| AC-2 | required     | All 7 patterns must be routable from the reality-checker stance. |
| AC-3 | required     | "Cross-reference, not duplicate" is the load-bearing design choice. |
| AC-4 | required     | docs-lint clean. |


## Progress Log


| Date       | Update                                                       | Evidence |
| ---------- | ------------------------------------------------------------ | -------- |
| 2026-06-05 | Change admitted into wave 1p3iv; implementation done in-session. | Edit to `seed-216` between Focus Areas and Do Not; docs-lint clean. |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-05 | Cross-reference with applies-when hints, not full pattern duplication. | Single-source: `seed-221` is canonical; `seed-216` carries just enough text to route the reviewer. Avoids parallel maintenance of the same prose across two seeds. | (a) Duplicate full pattern text into `seed-216` — rejected; doubles maintenance burden and creates drift risk when patterns evolve. (b) Just point at `seed-221` with no per-pattern names — rejected; reviewer has to context-switch to seed-221 to know if any pattern applies. The applies-when hints let the reviewer triage from inside `seed-216`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
