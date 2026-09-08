# Evaluate and Conditionally Upgrade LanceDB to 0.38.0

Change ID: `1xhdh-maint evaluate-lancedb-038-upgrade`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-08
Wave: 1xhbo lancedb-038-evaluation

## Rationale

Evaluate whether upgrading the local embedded vector backend from pinned LanceDB 0.33.0 to 0.38.0 improves reliability without reducing retrieval quality, performance, or destination-project compatibility. Implement the upgrade only when the evidence supports it; a documented decision to retain 0.33.0 is a valid outcome. This wave is separate from the operator's forthcoming 1.22.0 test-upgrade feedback and is not automatically assigned to that release.

## Requirements

1. Compare isolated 0.33.0 and 0.38.0 environments using identical vectors, metadata, queries, and representative local corpus sizes. Do not upgrade the working tool environment or mutate the live index for evaluation.
2. Trace the actual underlying Lance versions and relevant upstream fixes. Exercise repeated append/delete/compact operations and verify row contents, vector reuse, and disk reclamation. Distinguish prevention of new failures from reading/reclaiming an existing affected table. If the baseline does not reproduce the historical defect, report it as inconclusive rather than fixed.
3. Preserve cosine scores, pre-top-k kind/language/tag filters, candidate budgets, exact-reference evaluation, reranking, incremental updates, and publication/recovery contracts. Define paired performance acceptance thresholds before collecting candidate results; require no retrieval-metric regression or new contract violation.
4. Verify Python/dependency compatibility, including Pydantic 2, and installation support on macOS, Linux, and native Windows. Document any unavailable platform evidence before an adoption decision.
5. If evidence supports adoption, update the single dependency pin and only necessary integration, tests, install/upgrade guidance, and user-facing release notes. Keep the compaction fallback unless its retirement is independently justified; it may remain useful even after the motivating bug is fixed. Otherwise retain the pin and record the specific reason.

## Scope

**In scope:** dependency compatibility, compaction defect evaluation, retrieval and performance parity, local index migration/rebuild behavior, conditional version update, and correction of the local bug reference using verified upstream evidence.

**Out of scope:** SQLite vector migration, hosted services, new database features, embedding-model changes, unrelated 1.22.0 feedback, automatic release publication.

## Acceptance Criteria

- [ ] AC-1: A reproducible comparison records exact package/engine versions, fixtures, commands, expected versus observed compaction outcomes, and whether the historical failure is reproduced, resolved, or inconclusive.
- [ ] AC-2: Candidate retrieval behavior meets existing relevance gates with no metric regression or new filter/citation/publication violation; paired latency, memory, build/update time, and disk-growth results meet thresholds recorded before candidate measurement.
- [ ] AC-3: The adoption decision records supported-platform and dependency evidence, existing-index handling, and recovery behavior; missing evidence cannot be reported as compatibility success.
- [ ] AC-4: The decision is implemented consistently: adopt 0.38.0 only with sufficient evidence and focused integration checks, or retain 0.33.0 with an explicit no-go rationale. The workaround disposition and edited guidance accurately reflect observed behavior.

## Tasks

- [ ] Establish isolated comparison environments and predeclare performance thresholds and fixture slices.
- [ ] Trace upstream fixes and run baseline/candidate compaction and existing-data recovery probes.
- [ ] Run retrieval, filter, mutation, failure-recovery, and performance comparisons.
- [ ] Verify destination installation compatibility and record the adoption decision.
- [ ] Apply the conditional upgrade or no-go outcome; update affected documentation and release notes as applicable.
- [ ] Run required review lanes and validation, recording evidence in this change and the existing wave ledger.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Evaluation | implementer | Readiness | Isolated environments; no live index mutation |
| Evidence review | qa-reviewer, performance-reviewer | Evaluation | Verify parity and compaction conclusions |
| Conditional integration | implementer | Adoption evidence | Pin and necessary compatibility changes only |
| Delivery review | code-reviewer, qa-reviewer | Integration or no-go decision | Required lanes selected at Prepare |

## Serialization Points

Prepare/readiness precedes repository code edits. Evaluation precedes adoption. Dependency changes precede final integration verification. No approval to commit, close, or publish is inferred from wave creation.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/ann_reference_eval.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/references/lance-list-offset-corruption.md`
- `docs/architecture/search-architecture.md`
- `docs/architecture/chunking-and-indexing-pipeline.md`

## Affected Architecture Docs

Review `docs/architecture/search-architecture.md` and `docs/architecture/chunking-and-indexing-pipeline.md` for any adopted integration or maintenance changes. Correct `docs/references/lance-list-offset-corruption.md`: the cited upstream nested-list fix describes a reader defect, not proof of our single-level failure's cause or resolution.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establish what actually changed |
| AC-2 | required | No backwards step in user outcomes |
| AC-3 | required | Preserve destination compatibility |
| AC-4 | required | Deliver an evidence-based decision |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-08 | Planned on operator request; evaluation not started | Current pin in setup_index.py; upstream references below |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-08 | Evaluate first, conditionally adopt | Tests can establish value without exposing the working index | Immediate upgrade risks regressions; waiting solely for release-note confirmation cannot establish our actual defect outcome |

Upstream starting points: [LanceDB 0.38.0](https://github.com/lancedb/lancedb/releases/tag/v0.38.0), [nested-list decoder fix 7546](https://github.com/lance-format/lance/pull/7546), [Arrow-offset validation 8382](https://github.com/lance-format/lance/pull/8382). These are research leads, not proof that our compaction failure is fixed.

## Risks

| Risk | Mitigation |
| --- | --- |
| Historical reproducer does not fail on baseline | Mark inconclusive; seek retained affected data or a stronger reproducer before retiring workaround |
| Benchmark noise hides regressions | Same corpus and embeddings, repeated paired runs, predefined thresholds |
| Candidate changes old index files | Evaluate disposable copies; verify rollback/rebuild procedure before adoption |
| New dependency or platform requirement complicates upgrades | Inspect resolved dependencies and test supported destination environments |

## Session Handoff

Planned only. Next step is Prepare wave when selected by the operator. Keep this wave separate from upcoming 1.22.0 test-upgrade feedback.
