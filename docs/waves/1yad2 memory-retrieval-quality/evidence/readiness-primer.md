# Memory retrieval readiness primer

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Review scope

Mode: `council-adversarial-primer`. Phase: readiness. Depth: standard, as selected by the local prepare dry-run review policy (overrides the generic full-council default). Actor: `memory_readiness_primer`, isolated from the coordinator and subsequent council seats. This is a challenge packet, not an approval or a substitute for required specialist reviews.

Evidence: the admitted change document and [exploratory evidence summary](README.md). No production code was modified or executed for this primer. Historical measurements below are reported observations, not independently reproduced results. No source retrieval was necessary for this plan-level challenge.

## Strongest challenge

The wave could improve measured ranking while weakening the meaning of a returned memory. Exploration already reports that all eight no-match controls returned hits without abstention, useful broad queries failed hard relevance gates, and relevance-first ordering failed a current high-trust invariant. Those are three distinct decisions—candidate discovery, answer relevance, and authority. A single winning aggregate score cannot settle them. The plan correctly acknowledges them, but readiness must turn those acknowledgments into fixed decision rules before implementation results are visible.

Confidence: high that the plan has these unresolved decisions; medium that the proposed separation below will improve real queries, pending independent evaluation.

## Thinking stances applied

- **Adversarial:** A near-topic question can obtain a highly ranked but non-answering instruction. Normalization can award a top score to an entirely irrelevant set; one passing hit cannot approve its tail. Require per-record judgments, explicit no-match counts, and unchanged authority metadata. Do not label an unjudged hit irrelevant or authoritative.
- **Constructive:** Separate an eligible bounded candidate source from fusion and from presentation. Compare candidate-source-only improvement with source-plus-fusion so an apparent RRF win is not actually just fixing post-limit memory filtering. This adds one ablation, not another tuning family.
- **Simplicity:** Ship the maintained evaluator and preserve production ranking if adoption fails. A production-only candidate-source improvement is a separate decision subject to the same public-path gates; it must not slip through as an implementation detail after both finalists fail.

First-principles and analogical stances were not separately applied in the final primer because the selected standard-depth policy calls for three stances.

## Best alternative

Implement an evaluation-first pipeline with three identifiable boundaries: eligible memory candidate generation; rank fusion; and public presentation. Freeze independently reviewed holdout labels and gates, reproduce the real public production baseline, then score finalists once. Retain a candidate-source-only ablation and the existing production control. Adopt at most one passing design; otherwise deliver the evaluator, clear non-adoption evidence, and unchanged production behavior.

This is better because it localizes gains and failures without forcing an authority change to obtain a ranking improvement. Its cost is extra benchmark plumbing and one ablation. Its downside is that this wave may deliver trustworthy measurement rather than immediately faster or more relevant production results, which the admitted plan expressly permits.

## Consequence of the current path

Without readiness decisions, the many competing requirements let implementation choose favorable definitions after seeing outcomes: rank metrics could omit abstained queries, unjudged tails could be called false positives selectively, a memory-scoped candidate advantage could be attributed to fusion, or latency could omit the relevance check. Each would create an apparently green gate without demonstrating the intended user benefit.

## Primer questions

1. What exact public contract changes, if any, let query relevance precede confidence, and how do positive/negative controls prove that returned evidence is not being presented as current authority? If that change cannot be justified, which bounded candidate improvement can be tested under the existing policy without silently redefining success?
2. Who freezes holdout queries and complete relevant-record labels before tuning, how are ambiguous/unjudged outputs reported, and what predeclared paired effect size warrants adoption rather than the previously observed one-result gain? Confirm the baseline uses the public response path, and failures/unavailable runs cannot count as empty-corpus success. Within that protocol, what limits bound physical chunk retrieval, distinct candidates, relevance-model calls, and total latency on CPU? How will high duplicate density, model failure, stale indexes, archive references, and the same final result limit be exercised without full-subtree enumeration or discarded relevant records masquerading as bounded coverage?

## Readiness contract assessment

The coordinator's [readiness contract](readiness-contract.md) supplies concrete, appropriately bounded gates: no quality regression, at least five percentage points Recall@3 improvement or 20% p95 reduction, CPU p95 at most 500 ms and no worse than the production control, 20 candidates per channel, 24 independent holdout cases including eight negatives, frozen finalist parameters, and explicit non-adoption. Those gates address the main readiness omission. The 500 ms ceiling is a declared maximum, not a claim about measured performance; the production-relative gate remains independently binding.

Before scoring, pin these remaining interpretations:

- Define all quality metrics over all applicable queries, including answerable queries with zero results. Record full returned lists for local adjudication while ordinary MCP output stays aggregate-only. Unlisted expected IDs are not automatically negative judgments.
- Add the candidate-source-only ablation, or explicitly attribute total gains to the combined candidate/ranking change rather than RRF alone. Avoid broadening the tuning sweep.
- Specify a finite physical chunk fetch/scan bound or explicitly report an exact scan's full eligible population cost. A distinct-record cap does not establish bounded physical work when many chunks share an ID. Test exhaustion without silently overstating coverage.
- Count model loading in cold measurements. Include embedding, fusion, optional per-record checks, metadata assembly and response construction in matched end-to-end warm measurements; use identical query-cache conditions and output limits for baseline and finalists.
- Freeze the no-match definition across both public contracts. Returning an unrelated hit labeled uncertain is still a false-positive return for the adoption comparison; uncertainty must not redefine the metric into a free pass.
- Authority changes remain experimental until the architecture decision and adoption gates pass. Non-adoption must preserve current production behavior, not deploy an unqualified candidate-source change as an incidental fix.
- The readiness contract's Work allocation paragraph still requests full-depth fixed council seats. Align it to the actual local policy receipt: standard-depth targeted red-team plus docs-contract review, followed by independent architecture/QA work for their named implementation decisions.

These are narrow clarifications; no new dependencies, schema changes, parameter families, or mandatory reranker are proposed.

## Recommendation

Proceed with readiness only after the council ratifies concrete gates and ownership. Prefer the evaluation-first design above, require a public-baseline replay plus the candidate-source ablation, and make production adoption a separate recorded decision supported by the frozen results. Route authority semantics to architecture/security, measurement and negative controls to QA, resource bounds to performance, and response privacy to docs-contract/security.
