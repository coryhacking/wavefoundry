# Artifact Query Formulation for Guru

Change ID: `12xcg-enh artifact-query-formulation-guru`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: `12wsj framework-cleanup`

## Rationale

Explanatory search questions that name a concrete artifact or symbol but use only generic verbs can over-weight broad semantic matches and force an extra retrieval round-trip. The observed failure mode was not the implementation itself; it was query vocabulary that omitted the owning script, symbol, or format example.

## Requirements

1. Update Guru guidance so that when a question uses an implementation verb (`generated`, `derived`, `stamped`, `computed`, `encoded`, `written`) **and** names a concrete artifact — a recognizable token such as a filename, config key, version format string (e.g. `+2vr8`), or named symbol — the agent includes that artifact name, symbol, or format example verbatim in the `code_ask` or `code_search` query rather than substituting a generic noun such as "build number" or "version". The guidance must include a concrete before/after example showing a generic query rewritten to include the owning script, symbol name, and format example (e.g. "how is the build number generated?" → "how does `lifecycle_id.py` `build_prefix()` generate the `+2vr8` format?").
2. Add a small usage note for framework-scoped implementation questions showing `tags=["framework"]` as the supported scoping lever.
3. Keep this change docs-side only. It should improve how agents formulate retrieval queries without changing server routing behavior.

## Scope

**Problem statement:** Generic phrasing such as "build number" or "version" is too broad for some explanatory questions. In the build-number case, naming the owning script and format value was the difference between a slow semantic detour and a direct answer.

**In scope:**

- `docs/agents/guru.md`
- `docs/agents/journals/guru.md` if the guidance needs a short cross-reference

**Out of scope:**

- `server_impl.py`
- any retrieval-ranking or classification code

## Acceptance Criteria

- [x] AC-1: `docs/agents/guru.md` tells agents to include concrete artifact names, symbol names, and format examples when querying for artifact-anchored explanatory questions, and includes a before/after example showing a generic query rewritten with the owning script, symbol, and format value.
- [x] AC-2: `docs/agents/guru.md` includes a concrete `tags=["framework"]` example or equivalent guidance for framework-scoped implementation questions.
- [x] AC-3: `wave_validate` passes after the docs edit.

## Tasks

- [x] Update the Guru query-formulation guidance in `docs/agents/guru.md`.
- [x] Add or refine the `framework` tag usage note in the same doc.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| docs guidance | docs-contract-reviewer | — | Agent-side retrieval advice |
| validation | qa-reviewer | docs guidance | Confirm docs lint passes |

## Serialization Points

- `docs/agents/guru.md`

## Affected Architecture Docs

N/A. This change is confined to agent guidance and a supporting report note; it does not alter repository architecture or runtime behavior.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | Core query-formulation fix |
| AC-2 | important  | Concrete framework-scoping example |
| AC-3 | required   | Docs validation guardrail |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-26 | Added to `12wsj` and drafted from the build-number retrieval friction case. | Wave admission + search-friction report |
| 2026-05-26 | Implemented: added `### Query Formulation` section to `docs/agents/guru.md` with before/after examples and `tags=["framework"]` guidance. Docs-lint passes. | `docs/agents/guru.md`; `python3 .wavefoundry/framework/scripts/docs_lint.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-26 | Keep the scope docs-side only. | The search-quality improvement starts with query formulation; server routing is tracked in a separate change. | Fold server routing into this doc |
| 2026-05-26 | Do not add a new "artifact-anchored" classification row to the Question Classification table in `guru.md`. | Red-team review found the classification branch had undefined decision boundaries and could misfire silently. Query formulation guidance and the existing `tags` lever address the observed failure mode without routing complexity. | Add a classification row and pre-flight `code_keyword` routing step |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Guidance is too vague to change behavior | Make the examples concrete: artifact name, symbol name, and format value |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
