# Adaptive memory freshness and retrieval

Change ID: `1t7ab-enh adaptive-memory-freshness-and-retrieval`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-22
Wave: `1tbt5 memory-retrieval-quality-adaptive-freshness`

## Rationale

The memory layer has kind-aware time/churn decay, but its calibration is fixed
and its evaluation corpus is predominantly synthetic. A newer tactical lesson
should sometimes outrank an old one, while an old decision or operator
preference can remain authoritative. Improve freshness only through a measured,
policy-aware approach; do not let generic recency or semantic relevance erase
trust, status, or evidence quality.

## Requirements

1. Expand the memory-retrieval evaluation set with archive-pointer, archive-body
   opt-in, old-but-authoritative, newer-but-low-confidence, target-churn, and
   re-verification cases, plus a bounded curated real-corpus sample.
2. Define adaptive freshness by memory kind using evidence age, target churn, and
   applicable project change cadence. It is an ordering policy only within
   comparable records; it is not blended into semantic similarity.
3. Decisions and operator preferences are immune to automatic age penalties.
   Fragile-file records remain visible but gain re-verification pressure when
   their targets change.
4. Status, evidence validity, explicit target matches, confidence floors, and
   archive eligibility remain hard filters or policy constraints ahead of
   relevance and freshness ordering.
5. Reconsider the deferred `1sufn` lexical+semantic relevance fusion using the
   expanded evaluation. It may become default-on only if it improves measured
   retrieval without violating policy invariants; otherwise it remains
   default-off with results recorded.

## Scope

**Problem statement:** the current decay model cannot distinguish broadly among
old tactical records and has no real-corpus calibration. The deferred relevance
fusion also needs a sufficiently representative evaluation corpus before it can
be adopted safely.

**In scope:**

- Expansion of the existing memory-retrieval eval harness and its policy
  invariants.
- Adaptive, kind-aware freshness/re-verification policy in memory search and
  brief ordering.
- The deferred `1sufn` lexical+semantic relevance fusion behind its documented
  measured adoption gate.
- Retrieval, evaluation, and memory-schema/architecture documentation.

**Out of scope:**

- Archive storage, migrations, or retention decisions; owned by
  `1t8l9-enh memory-archival-and-retention-lifecycle`.
- A universal time-only boost that makes newer records win across every kind.
- Graph-proximity relevance and briefing token-budget redesign; defer until this
  evaluation demonstrates a need.

## Acceptance Criteria

- [ ] AC-1: The memory eval covers archive pointers, archive opt-in, durable
  decisions, tactical recency, target churn, and fragile-file re-verification,
  with deterministic fixtures and a recorded curated-corpus result.
- [ ] AC-2: Tactical kinds rank through documented adaptive freshness behavior;
  a newer or less-churned comparable record can win, while decisions and
  operator preferences remain immune to automatic age penalties.
- [ ] AC-3: Status, explicit target matching, evidence confidence, archive
  boundaries, and fragile-file visibility remain policy constraints and are
  regression-pinned.
- [ ] AC-4: `1sufn` relevance fusion is enabled by default only on measured
  improvement without invariant regressions; otherwise its default-off result
  and evidence are recorded.
- [ ] AC-5: No semantic/index failure changes the policy contract: degraded
  retrieval remains deterministic and preserves the same filters and ordering
  guarantees.
- [ ] AC-6: Documentation, full framework tests, and docs validation are clean.

## Tasks

- [ ] Extend the memory golden corpus, runner, metrics, and curated-corpus
  protocol.
- [ ] Implement and test adaptive freshness/re-verification policy.
- [ ] Integrate archive-pointer/history cases from `1t8l9` once its contract is
  available.
- [ ] Implement `1sufn` lexical+semantic fusion only behind its measured gate.
- [ ] Update retrieval, testing, and memory documentation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| evaluation expansion | qa-reviewer | archive contract | New invariants and corpus sample |
| freshness policy | implementer | evaluation expansion | Policy before relevance fusion |
| relevance fusion | implementer | freshness policy | Existing 1sufn gate applies |
| verification | qa-reviewer | all | Degraded and policy-invariant matrix |

## Serialization Points

- `memory_records.apply_decay`, `_memory_ranked`, search/brief response paths,
  and the memory evaluation runner must share one documented ordering contract.
- The archive-pointer contract is consumed but not modified by this change.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/testing-architecture.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/agents/memory/README.md`
- `docs/references/memory-retrieval-eval.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Measured foundation for every ranking decision |
| AC-2 | required | Delivers adaptive freshness safely |
| AC-3 | required | Preserves memory trust policy |
| AC-4 | important | Existing deferred plan, adoption-gated |
| AC-5 | required | Degraded behavior must be stable |
| AC-6 | required | Verification and documentation |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-22 | Planned as the retrieval companion to the archival wave. | Review of 1ro44, 1sufo, 1sufn, 1stwm, 1sxj7, and 1t3dm. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- |
| 2026-07-22 | Apply freshness as a kind-aware policy within comparable records. | Avoids generic recency demoting durable authority. | Universal recency multiplier: rejected because decisions/preferences can remain authoritative. |
| 2026-07-22 | Expand evaluation before altering ranking. | Existing baseline is intentionally synthetic and must guard archive/freshness cases. | Tune constants from intuition: rejected as unmeasured. |
| 2026-07-22 | Fold `1sufn` into this wave behind its existing adoption gate. | It is the relevant deferred retrieval feature but remains optional by measured outcome. | Ship fusion unconditionally: rejected; sparse corpora may not benefit. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Recency suppresses a durable lesson | Protected kinds and policy-invariant tests |
| Evaluation overfits the repository | Hermetic fixtures plus bounded curated real corpus |
| Fusion obscures freshness policy | Relevance-only fusion; policy remains a separate layer |
| Archive dependency blocks measurement | Sequence after the archive contract and use fixtures first |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
