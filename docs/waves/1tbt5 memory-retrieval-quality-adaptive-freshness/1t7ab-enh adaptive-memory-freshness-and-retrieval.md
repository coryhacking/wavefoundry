# Adaptive memory freshness and retrieval

Change ID: `1t7ab-enh adaptive-memory-freshness-and-retrieval`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-07-25
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
   re-verification cases, plus a bounded curated real-corpus sample. The
   hermetic corpus remains the repeatable suite gate. The real-corpus pass is an
   operator-run observational gate that records only aggregate metrics, corpus
   counts by kind/status, and a content fingerprint — never record bodies,
   summaries, or record ids in a fixture or report. Freeze the curated sample
   and its fingerprint before scoring candidate freshness constants or fusion
   variants; the shipped baseline, every candidate, and both single-stream
   controls must run against that same frozen sample.
2. Define adaptive freshness by memory kind using evidence age and the existing
   batched per-target commit history. "Comparable" means records in the same
   surfaced-status class, exact-target-match class, kind policy family, and
   rounded base-confidence band. The families are tactical
   (`failed_attempt`, `review_finding`, `successful_pattern`), time-sensitive
   (`environment_gotcha`, `dependency_gotcha`), protected authority
   (`decision`, `operator_preference`), and fragile (`fragile_file`).
   Freshness may reorder only inside that partition; it is not blended into
   semantic similarity and cannot move a tactical record across a
   protected-authority boundary.
3. The adaptive function is deterministic and inspectable: derive target
   cadence from the median interval of the available per-target commit
   timestamps, clamp the derived half-life with named minimum/maximum constants,
   use the most conservative target for multi-target records, and fall back to
   today's fixed kind constant when fewer than two timestamps or no readable
   freshness store exists. The evaluation calibrates the named multiplier and
   clamps; implementation must record the selected values and rejected
   candidates rather than tuning an unpinned formula from intuition.
4. Decisions and operator preferences are immune to automatic age penalties.
   Fragile-file records remain visible but gain re-verification pressure when
   their targets change.
5. Status, evidence validity, explicit target matches, the confidence policy
   key, briefing inclusion where applicable, and archive eligibility remain
   hard filters or policy constraints ahead of relevance and freshness
   ordering.
6. Reconsider the deferred `1sufn` lexical+semantic relevance fusion using this
   wave's expanded evaluation. Default-on requires: every hermetic policy
   invariant passes; hermetic recall@3 does not regress; curated-corpus MRR
   strictly improves over the shipped baseline; curated recall@3 does not
   regress; and the same report includes lexical-only and semantic-only
   controls. Evaluate the candidate before wiring it into the product path. A
   tie, an unreadable real-corpus pass, or any invariant regression leaves the
   shipped retrieval path unchanged; record the result without adding a
   dormant product flag or unreachable fusion branch.

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
- Evaluation of the deferred `1sufn` lexical+semantic relevance fusion, with
  product-path wiring only after its documented measured adoption gate passes.
- Retrieval, evaluation, and memory-schema/architecture documentation.

**Out of scope:**

- Archive storage, migrations, or retention decisions; owned by
  `1t8l9-enh memory-archival-and-retention-lifecycle`.
- A universal time-only boost that makes newer records win across every kind.
- Graph-proximity relevance and briefing token-budget redesign; defer until this
  evaluation demonstrates a need.
- Query/relevance fusion in `memory_brief`; the tool has no query input and
  continues to use shared policy/freshness ordering plus exact-target priority.

## Acceptance Criteria

- [x] AC-1: The memory eval covers archive pointers, archive opt-in, durable
  decisions, tactical recency, target churn, and fragile-file re-verification,
  with deterministic fixtures and a recorded aggregate-only curated-corpus
  result carrying a corpus fingerprint and no memory content or record ids;
  the sample/fingerprint is frozen before candidate scoring and reused by the
  baseline, every candidate, and both single-stream controls.
- [x] AC-2: Tactical kinds rank through a documented deterministic adaptive
  freshness function using the existing batched target history, named
  multiplier/clamp constants, and the explicit comparability partition; a newer
  or less-churned comparable record can win, while decisions and operator
  preferences remain immune to automatic age penalties.
- [x] AC-3: Status, explicit target matching, evidence confidence, archive
  boundaries, and fragile-file visibility remain policy constraints and are
  regression-pinned.
- [x] AC-4: `1sufn` relevance fusion is enabled by default only when all
  hermetic invariants pass, hermetic recall@3 does not regress, curated MRR
  strictly improves, curated recall@3 does not regress, and lexical-only plus
  semantic-only controls are recorded; otherwise evidence is recorded while
  the shipped retrieval path remains unchanged, with no dormant product
  fusion flag or branch.
- [x] AC-5: No semantic/index failure changes the policy contract: degraded
  retrieval remains deterministic and preserves the same filters and ordering
  guarantees.
- [x] AC-6: Documentation, full framework tests, and docs validation are clean.

## Tasks

- [x] Extend the memory golden corpus, runner, metrics, and curated-corpus
  protocol.
- [x] Evaluate candidate cadence multipliers/clamps, record the chosen and
  rejected values, then implement and test the deterministic adaptive
  freshness/re-verification policy.
- [x] Integrate archive-pointer/history cases from `1t8l9` once its contract is
  available.
- [x] Evaluate `1sufn` lexical+semantic fusion against the frozen corpus, then
  wire it into the product path only if the measured gate passes.
- [x] Update retrieval, testing, and memory documentation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| evaluation expansion | qa-reviewer | archive contract | New invariants and corpus sample |
| freshness policy | implementer | evaluation expansion | Policy before relevance fusion |
| relevance-fusion evaluation | implementer | freshness policy | Gate result precedes any product wiring |
| relevance-fusion wiring | implementer | relevance-fusion evaluation | Runs only when the gate passes |
| verification | qa-reviewer | all | Degraded and policy-invariant matrix |

## Serialization Points

- `memory_records.apply_decay`, `_memory_ranked`, search/brief response paths,
  and the memory evaluation runner must share one documented ordering contract.
- Pure cadence, comparability, lexical, and fusion calculations belong in the
  memory-policy layer; `server_impl` owns prefiltering and response
  orchestration so the eval runner and product path cannot grow parallel
  ranking formulas.
- The archive-pointer contract is consumed but not modified by this change.
- The existing `_memory_ranked` one-read `file_commit_times` batch remains the
  only hot-path freshness read; adaptive cadence must not add per-record or
  per-target store opens.

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
| 2026-07-24 | Readiness review made comparability, adaptive-cadence fallback, real-corpus privacy, and fusion adoption thresholds executable. | `memory_records.apply_decay`; `_memory_ranked`; `file_commit_times`; `run_memory_eval.py` |
| 2026-07-24 | Implemented adaptive cadence and policy partitions over the existing one-batch history read; expanded the hermetic corpus to 11 invariants and froze an aggregate-only 12-record live sample. | Hermetic fingerprint `72ead292…d23f4a4`; curated fingerprint `9355a41f…23fe395`; targeted memory suites green. |
| 2026-07-24 | Fusion gate failed safely: hermetic baseline `1.0000/1.0000` recall@3/MRR vs candidate `1.0000/0.8485`; curated semantic scoring unavailable to the standalone interpreter. The shipped semantic tie-break remains unchanged with no dormant branch. | `run_memory_eval.py --json --curated-root .`; `test_failed_gate_leaves_no_product_fusion_branch`. |
| 2026-07-24 | Final implementation verification passed. | Full framework suite on the final tree: 6,193 tests across 59 files OK in 289.113s; `wf_validate_docs`: clean. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- |
| 2026-07-22 | Apply freshness as a kind-aware policy within comparable records. | Avoids generic recency demoting durable authority. | Universal recency multiplier: rejected because decisions/preferences can remain authoritative. |
| 2026-07-22 | Expand evaluation before altering ranking. | Existing baseline is intentionally synthetic and must guard archive/freshness cases. | Tune constants from intuition: rejected as unmeasured. |
| 2026-07-22 | Fold `1sufn` into this wave behind its existing adoption gate. | It is the relevant deferred retrieval feature but remains optional by measured outcome. | Ship fusion unconditionally: rejected; sparse corpora may not benefit. |
| 2026-07-24 | Partition freshness by status, exact-target class, kind family, and base-confidence band. | "Comparable records" must be deterministic so recency cannot cross a policy boundary. | One global recency score: rejected because it can demote durable authority. |
| 2026-07-24 | Derive cadence from the existing batched target timestamps with named clamps and a fixed fallback. | Makes freshness dynamic on active targets without adding hot-path I/O or making missing index state nondeterministic. | Repo-wide git scan at query time: rejected as slow and unavailable in degraded mode. |
| 2026-07-24 | Require strict curated-MRR improvement plus recall/invariant non-regression to enable fusion. | The hermetic baseline already reaches perfect headline metrics in some cases; "beats" needs an unambiguous, non-cherry-picked rule. | Subjective council judgment from a mixed report: rejected as non-repeatable. |
| 2026-07-24 | Freeze the curated sample before scoring and gate fusion before product wiring. | Prevents after-the-fact corpus tuning and avoids maintaining dormant product code when the optional experiment does not beat the shipped order. | Wire a default-off branch before evaluation: rejected because failed experiments should not expand the production surface. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Recency suppresses a durable lesson | Protected kinds and policy-invariant tests |
| Evaluation overfits the repository | Hermetic fixtures plus a bounded curated sample whose fingerprint is frozen before candidate scoring |
| Fusion obscures freshness policy | Relevance-only fusion; policy remains a separate layer |
| Archive dependency blocks measurement | Sequence after the archive contract and use fixtures first |
| Adaptive cadence adds per-record store work | Reuse the existing one-batch timestamp read; pin query count in tests |
| Curated reports leak memory content | Aggregate metrics + counts + corpus fingerprint only |
| Candidate and product ranking formulas drift | Shared pure memory-policy helpers consumed by both the eval runner and response orchestration |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
