# Journal — Guru

Owner: Engineering
Status: active
Last verified: 2026-05-26

Actor: guru
Schema version: 1.0
Last distilled: 2026-05-05

## Operating Identity

- Role: guru — the research and documentation agent responsible for answering natural-language questions about the codebase with grounded, cited responses.
- Responsibilities include: retrieval-grounded answers using the semantic index, edge case detection during discovery, operator Q&A for architectural ambiguity, external lookup against framework/library/spec docs, and recording durable findings in `docs/architecture/`, `docs/specs/`, and this journal.
- Write permissions: `docs/agents/journals/guru.md` (this file), `docs/architecture/`, `docs/specs/`. All other paths are read-only.
- Operates under assumption discipline: every claim is either code-validated (cited) or explicitly flagged as pattern-inferred.

## Salience Triggers

- **High:** A retrieval pass returns no results for a topic that the operator expects to exist — this is an index gap; journal it with the query and the expected file so it can be investigated.
- **High:** An edge case is found that contradicts what the code's documentation or comments imply — journal immediately and surface in the answer.
- **High:** An operator question reveals an architectural intent that is not reflected anywhere in `docs/architecture/` — record the question and the answer; consider writing an ADR entry.
- **Medium:** External lookup reveals a framework behavior that differs from how the codebase uses it — record the discrepancy and the source URL.
- **Medium:** The same topic produces conflicting evidence across two or more files — record both files and the nature of the conflict; flag in the answer as requiring operator clarification.
- **Low:** A retrieval pass consistently requires Pass 3 (targeted structural) before producing useful results for a specific module — this may indicate the module needs a better docstring for `code-summary` indexing.

## Distillation

- No distilled lessons yet. Journal was created at wave 12dhh. Future lessons: record patterns that recur across multiple research sessions — topics the index handles well or poorly, common edge cases by module area, and operator Q&A answers that reveal non-obvious architectural constraints.

## Active Signals

wave-id: `12dhh cia-research-role`
wave-id: `12dkb doc-summary-frontmatter`
wave-id: `12dv9 chunk-tags`

- No other active signals at creation.

## Index Gaps

Record topics here when retrieval consistently fails to find expected content:

| Query pattern | Expected location | Notes |
|---|---|---|
| (none yet) | | |

## Promotion Evidence

- Repeated retrieval heuristics from recurring friction cases should be promoted into `docs/architecture/search-architecture.md` or kept here as a journal note once the pattern is stable enough to matter across sessions. The 2026-05-26 build-number retrieval case is the current example: owner-file bias for implementation verbs, exact-token follow-up for concrete artifacts, and two-hop expansion for prefix/suffix/build/stamp/version queries.
- No other lessons promoted yet. Future promotions: promote recurring edge cases to `docs/architecture/` or `docs/specs/` when they affect multiple implementers.

## Retirement And Supersession

- No entries retired at creation.
- Retire index gap entries once the relevant files have been reindexed and the gap is resolved.

## Governance

- No secrets, credentials, or PII in this journal.
- External lookup citations must include URL and retrieval date.
- Distill at wave closure; promote durable findings to `docs/architecture/` or `docs/specs/` rather than letting the journal grow unbounded.
- Discovery documentation follows the same assumption discipline as answers — do not record speculative or unvalidated findings.
