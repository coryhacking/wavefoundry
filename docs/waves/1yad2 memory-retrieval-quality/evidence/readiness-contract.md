# Proposed readiness contract

Owner: Engineering
Status: draft
Last verified: 2026-09-16

For independent readiness review before implementation or holdout scoring.

- Adoption requires no decrease in Recall@3, Recall@10 or MRR, no additional answerable empty responses or no-match false positives, and either at least 5 percentage points improvement in Recall@3 or 20% reduction in warm end-to-end p95. Report paired counts; the sample supports a local decision, not universal quality.
- CPU latency ceiling: warm p95 at most 500 ms and no worse than the production control under matched conditions. Record cold separately. Qualification corpus sizes: live full eligible corpus plus 10x and 100x synthetic scaling controls (timing only, never quality labels). Minimum 100 timed warm calls per finalist; report p50/p95/p99.
- Candidate bounds: at most 20 distinct semantic and 20 distinct lexical records, at most 40 fused records and 20 public results. Duplicate handling must not use unbounded chunk enumeration. Any scan cost must be reported against eligible corpus size; record caps do not imply sublinear search.
- Plain RRF k=60; score finalist 0.75 semantic + 0.25 lexical, with normalization population explicitly fixed and bounded. Weighted RRF weights 0.25/0.5/0.75 and lexical injection are development controls only. Freeze finalist parameters and normalization before holdout scoring; no holdout retuning.
- Independent QA owns disjoint queries and labels: at least 24 holdout cases, including at least eight no-match controls and broad paraphrases, identifiers, ambiguity, historical/contradictory records and duplicate-heavy cases. Judge the entire frozen corpus where practical; distinguish unjudged from irrelevant. Existing exploratory queries are development only.
- Proposed authority policy for council decision: relevance-first may be tested experimentally for explicit free-text queries; confidence/status metadata remain visible. Target-only queries, unsolicited advisories and memory_brief retain current policy. No production policy change unless adoption passes and architecture approves the precise contract.
- No-match policy candidates: no hard gate (results are candidates, not authority) versus bounded per-record raw-logit qualification. No query-wide gate may bless unrelated tails. Frozen development selects the relevance representation/threshold, if any, before holdout. Unavailable semantics must use the existing eligible lexical recovery; unavailable relevance checking must be explicit, never claim qualified hits.
- Identity is memory_id: group body vectors by their individual canonical source path, then deduplicate by memory_id. Compact archive-register entries share a manifest file and remain individually eligible lexical candidates; do not pretend each has a distinct vector or collapse entries by manifest path. History opt-in searches real archived body paths.
- Metrics count every answerable query including empty responses; every nonempty no-match response is a false positive, even when described as uncertain. Report returned judged-irrelevant and unjudged counts separately.
- Run the actual public production path as the adoption baseline and a shared-candidate-source ablation to isolate fusion from retrieval coverage. Describe improvements in the combined design when either stage changes.
- Memory-scoped SQL may scan all eligible chunks, group by canonical record path before LIMIT, and return at most 20 records; report physical row counts and timing. This is bounded result materialization, not bounded or sublinear distance computation. Stop and report unavailable if a safety bound prevents complete coverage; never report a truncated scan as complete.
- Production non-adoption remains a valid outcome. Do not replace the existing public search until all gates pass. Ship reusable evaluation and a truthful aggregate-only report even when non-adoption is the result.

## Work allocation

Local policy selects standard-depth isolated red-team primer followed by an independent docs-contract-reviewer seat and council synthesis. Coordinator integrates readiness changes. Implementer owns evaluation/retrieval code; independent QA owns holdout judgments before final scoring. Source changes wait for typed readiness and activation.
