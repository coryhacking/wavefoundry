# Memory quality: written, maintained, indexed and evaluated

Owner: Engineering
Status: active
Last verified: 2026-11-23

Record ID: `244cm-arc memory-quality`

## Outcome

Agents working in a repository get memory records that are worth surfacing, and maintainers can show it with numbers. Records must be properly written, maintained, indexed and evaluated (operator decision, 2026-11-23). The arc succeeds when three things hold:

1. A frozen situation-language evaluation reports, for each wave in this arc, whether the change moved its target metric.
1. No active record silently degrades from semantic to lexical retrieval after an edit outside Review memories.
1. Every surfaced record still points at code that exists, or is queued for revalidation.

**Beneficiaries:** agents that receive briefings and `memory_search` results, and maintainers who run Review memories.

**Boundaries:** the arc keeps the current architecture: repo-visible typed records, evidence refs, strict admission, non-destructive retirement and the capped briefing. The research assessment supports that architecture and calls it unproven where it is most original ([assessment](research/agent-memory-systems-assessment.md), "The verdict"). The arc proves or simplifies that architecture rather than replacing it. The downstream paired task suite (assessment tier four) is not planned in this arc.

**Evidence base:** the assessment and its four source notes are committed under [`research/`](research/). They were copied from wave `245na`'s work folder, which is deleted when that wave closes:

- [Agent memory systems assessment](research/agent-memory-systems-assessment.md)
- [Coding-agent products](research/notes/coding_agent_products.md)
- [Evaluation methods](research/notes/evaluation_methods.md)
- [Lifecycle research](research/notes/lifecycle_research.md)
- [Memory frameworks](research/notes/memory_frameworks.md)

## Path

The tracks run as waves in this order. Evaluation comes first because every later track needs it to show an effect.

| Track | What it changes | How its signal is measured |
| --- | --- | --- |
| 1. Evaluation, including index signals | A frozen query set with about 2 or 3 situation-language queries per active record, authored independently of the record text. A leakage filter, null queries, stale cases and a dev/held-out split by record. Recall@5 and MRR first, then precision of the shown set, false-show rate on null queries and stale-shown rate, each with intervals from a bootstrap that resamples records. Baselines on the same queries and the same corpus: no memory, grep, BM25-only, dense-only, hybrid without rerank, production and full context. Memory index coverage that separates stale from missing sources, from a model-free helper track 2 can reuse, and a check that each active record is reachable by its own target path. The self-summary query stays only as a labeled sanity floor. The choice of embedded text (summary, body, targets) is measured with ablation arms. | The arm metrics on the held-out split, read by the operator; the report makes no verdict. Spec `245sp`, wave `245na`. |
| 2. Indexing freshness | A record edited outside Review memories, for example by `git pull`, must not leave semantic search silently degraded to lexical. Options: reindex on any change under the memory root, and report memory coverage in `index_health`. `AGENTS.md` already asks agents to run `index_health` after Git operations, so the work is to make that check show memory coverage. | Track 1's `index_signals.memory_vector_coverage` stays complete after an edit made outside the tools, and `production_retrieval.fallback_probes` stays 0. |
| 3. Admission hardening | Evidence refs and targets must resolve at HEAD before the agent judges a candidate. Reject candidates that contain secrets or model-control tokens, and flag candidates whose evidence comes from untrusted text. Admit a record only when it holds something the code does not already show. Rewrites keep the concrete anchor and stay specific. An empty briefing is a normal result. | The false-show rate on null queries, and precision of the shown set, compared before and after on the frozen set. A count of rejected candidates by reason. |
| 4. Maintenance | A deterministic check that every target still resolves at HEAD. Churn or a missing target queues a record for revalidation instead of silently lowering its confidence. Decay resets only on a recorded check, never on read. The audit batch is ordered by signal first (broken target, churn flag, disputed in a session), then age. `Updated:` is re-stamped only after a recorded check. The never-decaying kinds keep their age exemption but are still revalidated on churn. | The fraction of active records with unresolved targets, over time. Whether churn-flagged records are found stale on review more often than unflagged records of the same age, which is the only direct test of churn as a signal ([assessment](research/agent-memory-systems-assessment.md), tier three). |

**Dependencies:** tracks 2 to 4 each read track 1's metrics. Track 4's target check and track 3's resolution check share one mechanical primitive, so whichever ships first owns it.

**Retrieval-stack pause:** investment in the retrieval stack (dense, BM25, RRF, reranker) pauses until production is shown to beat the grep, BM25-only and full-context baselines on track 1's held-out split. Lifting the pause is the operator's decision, made from track 1's report; the report computes no pause or "beats" verdict (coordinator decision, 2026-11-23, after readiness review found that an automatic precision gate rewarded an arm that shows almost nothing). If grep or full context matches production on recall and precision, the arc should accept the simpler design.

## Declined

The operator declined these on 2026-11-23, with reasons from the assessment's "Do not do" table:

| Declined | Reason |
| --- | --- |
| Graph or entity stores (Zep, Mem0g, Cognee) | They are built for conversational scale. Zep needs at least five LLM stages per ingest, and Mem0 measured Zep's store at over 600k tokens. |
| Automatic LLM delete or rewrite on write (Mem0 CRUD, A-Mem evolution) | They lose valid records silently, churn diffs and defeat review. A-Mem scored lowest in Mem0's re-run. |
| Hidden or machine-local stores | Both documented memory-poisoning incidents in coding agents hit stores outside the repository review path. |
| Always loading every record | It adds recurring context cost with no evidence of benefit (the Cline Memory Bank pattern). |
| Background auto-consolidation | GitHub rejected offline curation as costly and still needing read-time checks. |
| Decay reset on read | Reading proves nothing about a record's truth. Copilot deliberately resets expiry only on an explicit upvote. |
| Citing LoCoMo or LongMemEval numbers as evidence | They are conversational, disputed and often not memory-bound. An audit found 6.4% of LoCoMo's answer key wrong. |

## Progress

| Wave | Track | State on 2026-11-23 | Evidence |
| --- | --- | --- | --- |
| [`245na memory-eval-production-path`](../../waves/245na%20memory-eval-production-path/wave.md) | 1 | Planned, not readied. Holds `245sp-enh memory-eval-situation-queries-and-baselines`. Readiness review raised 7 findings on 2026-11-23; repair cycle 1 revised the spec, and reverification is pending. | Wave record; `events.jsonl`. |

Spec `243hz-bug memory-eval-measures-production-path` was removed from `245na` and withdrawn as superseded by `245sp`, which carries its production-path row and bounded experimental row. Its diagnosis remains valid evidence at `docs/plans/243hz-bug memory-eval-measures-production-path.md`.

Nothing in this arc is delivered yet. No metric has been measured on independent queries.

## Next step

Finish readiness reverification and **Prepare wave** on `245na`, which this arc does not authorize by itself. After `245sp` ships, the operator reads its held-out metrics, decides whether the retrieval-stack pause holds, and then plans track 2. They set the baseline that tracks 2 to 4 are measured against.
