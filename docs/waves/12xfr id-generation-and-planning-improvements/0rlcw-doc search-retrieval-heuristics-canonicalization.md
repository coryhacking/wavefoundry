# Search Retrieval Heuristics Canonicalization

Change ID: `0rlcw-doc search-retrieval-heuristics-canonicalization`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xfr id-generation-and-planning-improvements`

## Rationale

The build-number retrieval case showed a repeated pattern: agent-side query formulation and server-side routing improvements help, but the same heuristics should not remain buried only in ad hoc notes. If the pattern recurs, the canonical guidance should live in the search-architecture docs or the Guru journal so future retrieval work can reuse the lesson directly.

## Requirements

1. Add a canonical follow-up note that says repeated retrieval heuristics should be promoted into the search-architecture docs or Guru journal.
2. Keep the note narrowly framed as a follow-up to repeated friction cases, not as a new retrieval rule.
3. Cross-link the note from the existing search-retrieval friction report so the evidence and the canonical guidance stay connected.

## Scope

**Problem statement:** The existing search-retrieval friction report captures the symptom and the candidate fixes, but it does not yet say where repeated heuristics should graduate if this pattern appears again.

**In scope:**

- `docs/reports/search-retrieval-friction-2026-05-26.md`
- either `docs/architecture/` search guidance or `docs/agents/guru.md`, depending on the least disruptive canonical home

**Out of scope:**

- server-side retrieval code
- immediate ranking or routing changes

## Acceptance Criteria

- [x] AC-1: The canonical guidance notes that repeated search heuristics should move into search-architecture docs or the Guru journal.
- [x] AC-2: The search-retrieval friction report points to that canonical guidance or otherwise records the follow-up path.
- [x] AC-3: `wave_validate` passes after the docs update.

## Tasks

- [x] Choose the canonical home for the recurring-heuristics note.
- [x] Add the follow-up language to that doc.
- [x] Update the friction report to cross-reference the canonical note.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| canonical note | docs-contract-reviewer | — | Promote the repeated-heuristics follow-up |
| cross-reference | docs-contract-reviewer | canonical note | Keep the report linked to the note |

## Serialization Points

- `docs/reports/search-retrieval-friction-2026-05-26.md`

## Affected Architecture Docs

Likely `docs/architecture/cross-cutting-concerns.md` or a related search guidance doc, if the team chooses architecture as the canonical home. If the Guru journal becomes the canonical home instead, the architecture docs can remain unchanged.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Core canonicalization goal |
| AC-2 | important | Keeps evidence linked to guidance |
| AC-3 | required  | Docs gate before handoff |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-26 | Added as the follow-up for recurring retrieval heuristics. | Search-retrieval friction report |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-26 | Defer canonicalization until the recurring pattern is clear enough to justify a stable home. | The immediate fix is already split across docs guidance and server routing; this note captures the next-step promotion path. | Leave the note only in the friction report |
| 2026-05-27 | Canonicalize repeated retrieval heuristics in the Guru journal. | The journal is the least disruptive durable home for a recurring pattern note, and the friction report can point to it directly. | Add a separate architecture note now — deferred until the pattern recurs again |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The note is too abstract to act on | Keep it tied to repeated friction cases and a concrete canonical destination |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
