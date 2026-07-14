# 1sihk-adr — Annotation-First Temporal Decay (Score-Blended Decay Rejected)

Owner: Engineering
Status: accepted
Last verified: 2026-07-13

## Context

Retrieval ranked by relevance only: nothing in the pipeline knew that a highly-ranked doc citation described code that had churned through dozens of commits since the doc was last checked against it. Agents received confidently-ranked citations to drifted documentation with no signal to distrust them. The obvious fix — multiplying scores by a time factor — collides with two facts: the cross-encoder's calibrated relevance ordering is the pipeline's most valuable signal, and for documentation decay is **not** a function of age (a two-year-old doc about a stable module is fresh; a two-week-old doc about a daily-churning file is already stale).

## Decision

Temporal currency is surfaced as **annotation first, demotion only on strong evidence**, and the decay variable for docs is **doc-code drift** — churn of the described code since the doc's drift anchor (last content change or a deliberate `Verified against: <sha>` verification stamp) — never elapsed time:

- Build-time-only computation in the derived SQLite state store (freshness/churn per file, wave→files attribution from landing commits, per-doc drift summaries); zero git subprocesses on the query path, test-pinned.
- Per-citation `freshness` annotation on all four search tools via one batched read; silent absence on metadata-free stores; omitted on live-fallback serving.
- The only ranking treatment is an order-only stable partition of drift-flagged docs citations behind comparably-relevant current alternatives (relevance-band guard on the unified reranker scale), per-citation reason-tagged, suppressed off the healthy reranked path, and shipped **default-off** — flipping the default requires the recorded drift-precision census AND a golden-query eval run per the standing ranking-eval gate.
- Mechanical drift is a **proposal**, never a verdict: the drift worklist feeds a deliberate verification loop; only doc content changes or verification stamps reset the clock, and the gardener's mechanical `Last verified` date stamps carry no verification meaning.
- Wave-record archives (`docs/waves/`) are the **historical** class: landing-commit anchor, waves-behind decay, annotation-only, never worklisted; generated point-in-time reports are drift-exempt.

## Consequences

- The reranker's relevance ordering is never perturbed; correct answers about stable code cannot be buried by age.
- Agents see the suspicion signal (`drifted`, `commits_since_verified`, `historical`/`waves_behind`) at action time even while the partition stays off.
- The census recorded moderate precision as a "worth re-verification" signal and low precision as a "doc is wrong" verdict — confirming the two-tier design and keeping the partition census+eval-gated.

## Alternatives Considered

- **Rank-time decay multiplier** (`score × exp(−age/half-life)`): perturbs calibrated cross-encoder scores; buries correct answers about stable code (old ≠ wrong); risks query-path freshness math. Rejected.
- **Gardening-only staleness reporting** (no retrieval change): the signal never reaches the agent at action time, exactly where stale citations cause damage. Rejected.
- **Treating mechanical drift as staleness truth** (auto-demote by default on churn thresholds): structurally high false-staleness rate (churn ≠ invalidation) would erode trust in the signal. Rejected — evidence-gated, default-off partition instead.
