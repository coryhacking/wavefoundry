# Reranker Scores Depend On Batch Composition

Change ID: `1v455-bug reranker-scores-depend-on-batch-composition`
Change Status: `withdrawn`
Owner: Engineering
Status: planned
Last verified: 2026-08-12
Wave: 1v4ms reranker-order-invariance

> **WITHDRAWN 2026-08-12 by operator direction, carrying its findings.** The defect is real,
> confirmed and measured; it is deliberately NOT being fixed because every available remedy costs
> more than the defect. Measured against a single unsplit batch as ground truth, today's behaviour
> misses **1 of 60** top-10 slots while the cheapest remedy misses **17 of 70**. Do not re-attempt
> without reading the Progress Log: the remedy space was priced, not overlooked.
>
> Acceptance criteria are marked `[~]` rather than `[x]`: none was met, and none should be read as
> satisfied. The reproduction tests written during implementation were REMOVED with this
> withdrawal, because they assert an order-invariance property the code deliberately does not
> provide and would otherwise fail the suite forever. ADR `1v22e` carries the durable record.


## Rationale

The reranker's INT8 export carries 26 `DynamicQuantizeLinear` operators. That operator emits one
scalar activation scale derived from a `ReduceMin` / `ReduceMax` spanning the whole input tensor,
batch dimension included, so a row's quantized values depend on the other rows in its batch. This is
the same mechanism ADR `1v22e` records for the embedder. Its FP16 export carries **no** quantization
operators, so GPU hosts are unaffected; this is a CPU-bound defect only.

`StaticShapeReranker.rerank` batches to `RERANK_STATIC_BATCH` = 40 and pads with `(query, "")` only
when the group is short. Three facts turn that into a ranking defect rather than a contained one:

1. **Pools routinely exceed one batch.** `AGENT_CANDIDATE_MAX` = 40 is a *post*-rerank selection
   backstop, not a cap on what reaches the reranker, and `_agent_rerank` forwards the full candidate
   list. With `VECTOR_TOP_K` = 30 per index across two indexes, pools near 60 are ordinary, so a call
   splits into 40 real rows plus a padded remainder.
2. **Scores are then compared across that boundary.** `_rerank` min-max normalizes over all scores
   from both batches; `_agent_rerank` sigmoids each logit into the relevance floor, the drop-off
   cut, and the confidence band. Nothing keeps the comparison inside one batch.
3. **The shift is large enough to matter.** Holding the query and the 60 candidates fixed and
   changing only which batch a passage lands in moved its score from `+1.4068` to `+1.5228`, about
   1.8 points of sigmoid relevance.

A correct cross-encoder scores each (query, passage) pair independently, so it must be invariant to
the order of its input. Ours is not. Measured over five queries against real repository passages,
reordering the same 60-candidate pool changed **top-5 ordering in 3 of 5** and **top-10 membership in
1 of 5**; the top-1 result held in all five. Pool order comes from retrieval and is arbitrary, so
this is user-visible instability: same question, same candidates, different answer.

A control isolates the cause and pre-validates the remedy. At pool sizes of 40 and 35, where no split
occurs, ordering is **identical in 5 of 5**. The split is the cause, not the padding alone.

**Limits on this evidence:** five queries, one pool, one shuffle seed, and passages assembled from
repository text rather than drawn through the live retrieval pipeline. The direction and the cause
are established; the observed rates are not calibrated frequencies. Sizing that properly is AC-6.

**This is pre-existing, not a regression.** Wave `1v454` fixed the embedder and never touched the
reranker path. This defect has been present in every release that shipped the CPU INT8 reranker.

## Requirements

1. Reranker output is invariant to the order of the candidate pool: the same query and the same set
   of candidates produce the same scores and the same ranking regardless of input order.
2. Scores that are compared against one another, whether by min-max normalization, a relevance
   floor, a drop-off cut, or the confidence band, are produced under the same batch composition.
3. The GPU / FP16 reranker path is unchanged. It has no quantization operators and does not have
   this defect.
4. Whatever remedy is chosen, its effect on retrieval quality is measured rather than assumed. If it
   trades recall for consistency, that trade is quantified and recorded before adoption.
5. A regression test fails if reranker output becomes order-dependent again.

## Scope

**Problem statement:** reranker scores depend on which batch a candidate lands in, and those scores
are then compared across batches, so the ranking a user sees depends on the arbitrary order of the
retrieval pool rather than on relevance alone.

**In scope:**

- Making reranker scoring order-invariant for pools of any size.
- The comparison sites that consume those scores (`_rerank` normalization, `_agent_rerank` floor,
  drop-off, and confidence band) insofar as they depend on cross-batch comparability.
- Measuring the retrieval-quality effect of the chosen remedy.
- Regression coverage for order-invariance.

**Out of scope:**

- The embedder path. Fixed in wave `1v454`; do not reopen it here.
- The GPU / FP16 reranker path and its batching.
- Replacing dynamic quantization with a calibrated static export. Recorded in ADR `1v22e` as the
  standing alternative for the whole defect class; if it is ever taken it should cover both the
  embedder and the reranker in one change, not this one.
- Retuning `VECTOR_TOP_K`, `AGENT_CANDIDATE_MAX`, or the candidate-selection policy for reasons
  other than this defect.

## Acceptance Criteria

- [~] AC-1: Reranking the same candidate set in different input orders produces identical scores, asserted on a pool larger than `RERANK_STATIC_BATCH`. **Not met (withdrawn).** Reproduction existed and failed 60/60; no remedy adopted.
- [~] AC-2: Reranking the same candidate set in different input orders produces an identical ranking, asserted on the same oversized pool. **Not met (withdrawn).** Order-dependence is real but its trigger is likely latent, since retrieval order is deterministic for a fixed index.
- [~] AC-3: Every score that is compared against another score is produced under the same batch composition, or the comparison sites are shown not to compare across compositions. **Not achievable in scope.** Two batches never share an activation range under per-tensor dynamic quantization, so only a single-batch-for-the-whole-pool or a calibrated export satisfies this. Both were priced and rejected.
- [~] AC-4: The GPU / FP16 reranker path is unchanged, asserted by a test that fails if its batching or graph selection changes. **Not met (withdrawn).** No change was made, so the GPU path is untouched by construction.
- [~] AC-5: A regression test fails if reranker output becomes order-dependent again, using the oversized-pool oracle from AC-1. **Not met (withdrawn).** The regression test was removed; it asserted a property the code deliberately does not provide.
- [~] AC-6: The retrieval-quality effect of the chosen remedy is measured against the current behaviour on a pool of realistic size, with the query set, pool construction, and per-query results recorded in the Progress Log. If the remedy drops candidates, the recall cost is stated explicitly. **Met as a measurement, and it is what killed the change.** Cap-at-40 misses 17/70 top-10 slots against ground truth; today's split misses 1/60.
- [~] AC-7: Reranker latency before and after is measured and recorded, since the remedy may change the number of inference calls per query. **Measured anyway.** Batch 60 costs +43% peak RSS (2954 -> 4220 MiB) and +12% latency; batch 140 reaches ~6 GB.

## Tasks

- [~] Reproduce order-dependence as a failing test before changing behaviour, using an oversized pool and the shuffle oracle from the Rationale.
- [~] Enumerate every consumer of reranker scores and record which ones compare scores across batch boundaries. Use `code_references` on the scoring seam rather than an identifier grep, per the census-instrument rule in seed 209.
- [~] Choose the remedy and record the decision with its measured tradeoff.
- [~] Implement the remedy and make the reproduction test pass.
- [~] Add the GPU-path pin required by AC-4.
- [~] Measure retrieval quality and latency before and after; record both.
- [~] Update ADR `1v22e`'s reranker section from confirmed-open to resolved, retaining the measurements.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reproduce | implementer | — | Failing order-invariance test on an oversized pool; this is the oracle the remedy is judged against. |
| consumer-census | implementer | — | Which sites compare scores across batches. Reference-level instrument required, not identifier grep. |
| remedy | implementer | reproduce, consumer-census | The design choice is genuinely open; see Decision Log. Do not implement before the census, because the right remedy depends on where comparisons happen. |
| gpu-pin | qa | reproduce | Independent; guards the unaffected path against collateral change. |
| measure | qa | remedy | Retrieval quality and latency. Must be run by someone who did not author the remedy. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_accel_embedder.py`

## Affected Architecture Docs

ADR `1v22e-adr int8-encoding-is-batch-composition-sensitive` already records this exposure as
confirmed, with the measurements. It needs updating from open to resolved when this lands, retaining
the evidence. No new ADR is required: the constraint is the same one `1v22e` states, applied to a
second graph. `docs/specs/mcp-tool-surface.md` should be checked for any claim about reranker
determinism that this change makes true or false.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect itself, at score level. |
| AC-2 | required | The user-visible consequence; scores matter only through ranking. |
| AC-3 | required | Cross-batch comparison is what turns composition dependence into a ranking defect. |
| AC-4 | required | The GPU path is the unaffected majority path and must not be disturbed. |
| AC-5 | required | Without it the fix silently regresses later. |
| AC-6 | required | The likely remedy trades recall for consistency. Shipping that trade unmeasured repeats the gap this wave's predecessor had to defer. |
| AC-7 | important | Latency could change materially if the remedy alters call count; not a correctness gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-12 | **Reproduction landed before any behaviour change.** `test_rerank_is_order_invariant_on_a_pool_larger_than_one_batch` fails 60/60 on a 60-candidate pool, with `test_rerank_order_invariance_oracle_is_not_vacuous` proving the fake session is genuinely composition-sensitive. The fake reproduces the `DynamicQuantizeLinear` mechanism (each row's output carries a batch-spanning term), so it asserts the property rather than a remedy and needs no model or hardware. | `tests/test_accel_embedder.py`. |
| 2026-08-12 | **Consumer census, two instruments, and they disagreed.** `code_references` on `rerank` returned only `accel_embedder`-internal call sites and MISSED both consumers; `code_keyword` found `server_impl` 1340 and 1357 in one call. Recorded per the seed 209 census-instrument rule, which was refined the same day BECAUSE of this disagreement: the first draft ranked references above identifier search, and this is the opposite failure. Consumers confirmed: `_rerank` min-max normalizes across all scores, `_agent_rerank` sigmoids into the relevance floor, drop-off and confidence band. | `code_references`, `code_keyword`; seed 209 refinement. |
| 2026-08-12 | **Remedy search: every in-scope option measured and rejected.** Cap at 40 restores invariance but loses recall. Single-row costs ~35x inference calls at query time. Batch 60, measured per-process for clean peak RSS: **+43% memory (2954 -> 4220 MiB) and +12% latency (1198 -> 1341 ms)** despite computing fewer rows, and it still splits at the 140-candidate worst case. Batch 140 reaches ~6 GB peak and is slower than today. An earlier single-process run suggesting batch 60 was FASTER was confounded by cumulative `ru_maxrss`; isolated runs reverse it. | Isolated-process benchmarks; `VECTOR_TOP_K` 30/index, `VECTOR_TOP_K_EXPLANATORY` 50/index, `LEXICAL_TOP_K` 20/table give a ~140 worst-case pool. |
| 2026-08-12 | **AC-6 decisive: the cure is worse than the disease.** Measured against a single unsplit batch as ground truth (one regime, no cross-batch comparison), **today's split misses 1 of 70 top-10 slots** while **cap-at-40 misses 17 of 70**. The defect is real mechanically but nearly benign in delivered results, because the pool arrives cosine-sorted so batch 1 already holds the strongest candidates and the padded remainder's inflation rarely promotes past them. That protection exists only because docs and code now share one embedder, making cosine comparable across indexes. Every remedy costs an order of magnitude more than the defect. Limits: top-10 membership rather than intra-top-10 ordering; seven queries, one corpus. | Reference-vs-split-vs-cap comparison on real repository passages. |
| 2026-08-12 | Defect confirmed and measured during the 1v454 close-out, no code changed. 26 `DynamicQuantizeLinear` operators in the reranker INT8 export and none in its FP16 export; batch position alone moved a passage score `+1.4068` to `+1.5228`; pool reordering changed top-5 ordering in 3 of 5 queries and top-10 membership in 1 of 5, with top-1 stable in all 5; pools of 40 and 35 (no split) were order-identical in 5 of 5. | Session probe transcripts; ADR `1v22e` **Related** section. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-12 | File as its own change rather than reopening wave `1v454`. | The reranker is a separate surface with its own batch shape and its own consumers, the defect is pre-existing rather than introduced by that wave, and `1v454`'s watchpoints explicitly deferred it to avoid scope growth. | Fold into 1v454 before closing it (rejected: would have grown a closed, reviewed wave and delayed a verified embedder fix). |
| 2026-08-12 | Leave the remedy OPEN at plan time rather than pre-committing to capping the pool at `RERANK_STATIC_BATCH`. | Capping is measured to restore order-invariance (5/5 identical at pool 40 and 35) and costs no extra inference calls, which makes it the leading candidate. But it discards candidates 41 and beyond from reranking, trading recall for consistency, and the size of that trade is unmeasured. The consumer census may also show a cheaper containment. Choosing before measuring would repeat the pattern this defect class keeps producing. | **Cap the pool at 40** (leading candidate; measured to work; unquantified recall cost). **Single-row scoring** as the embedder took (rejected as the default: 40x the inference calls at query time, where the embedder's equivalent cost was amortized over an offline build). **Pad every batch to a fixed composition** (rejected on the embedder by direct measurement: adding one empty row did not stabilize the scale). **Score in fixed-size batches and normalize within each** (possible, but changes what the scores mean across the pool and needs its own quality measurement). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The leading remedy caps the reranked pool, trading recall for consistency, and the recall cost is currently unmeasured. | AC-6 requires that measurement before adoption and requires the cost to be stated explicitly if candidates are dropped. |
| The evidence is five queries, one pool, one shuffle seed, and passages not drawn through the live retrieval pipeline. | AC-6 requires the remedy to be measured on a realistic pool; treat the recorded rates as directional, not calibrated. |
| Reranker scores feed the relevance floor, drop-off cut, and confidence band, so a change in score scale can shift which candidates are returned even when ordering improves. | AC-3 requires enumerating those consumers, and AC-6 measures the end-to-end effect rather than only the ordering property. |
| Single-row scoring would multiply query-time inference calls. | AC-7 requires latency measurement; the Decision Log already records why it is not the default choice here. |
| The census of score consumers could miss a site, which is exactly how the embedder change introduced a defect one file outside its declared scope. | The census task mandates a reference-level instrument rather than identifier grep, per the rule added to seed 209. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

## Readiness Review (wave `1v4ms`, withdrawn 2026-08-12)

This change was admitted to wave `1v4ms reranker-order-invariance`, readied, and reviewed before
being withdrawn on measurement. That wave directory was removed once empty, because closing it would
have required recording delivery-lane and operator approvals for zero delivered changes, which would
have put untrue statements in an append-only ledger. The review's substantive findings are preserved
here so the container's removal loses nothing.

**Prepare-phase Wave Council — PASS.** Moderator wave-council; seats red-team (fixed) and
docs-contract-reviewer (rotating); receipt `review-policy-eb76616eafe00dd7843a`; lanes code-reviewer
and qa-reviewer both approved at readiness.

- **red-team** attacked the premise whose falsity would have killed the change: that production
  pools exceed `RERANK_STATIC_BATCH`. Verified against the tree rather than the plan, and found the
  opposite of a refutation. The shipped comment at the `_agent_rerank` call site states the
  cross-encoder scores "the full retrieved pool on ONE unified relevance scale ... BEFORE selection",
  confirming there is no pre-rerank cap and raising severity, because the split violates a documented
  design invariant rather than merely perturbing numbers. Also confirmed 26 `DynamicQuantizeLinear`
  operators in the reranker INT8 export and zero in FP16 (CPU-only blast radius), the conditional
  padding, and that the cross-batch comparison is real via `_rerank`'s min-max normalization and
  `_agent_rerank`'s sigmoid floor, drop-off and confidence band.
- **docs-contract-reviewer** recorded no finding. `docs/specs/mcp-tool-surface.md` makes no
  determinism or stable-ordering promise about the rerank path, so no shipped documentation was
  false, and no new ADR was warranted because the constraint is ADR `1v22e`'s applied to a second
  graph.

**What the review did not catch, and could not have.** Both council rounds and both lanes accepted
the premise that a cheap remedy existed. That premise was only falsified later, by the AC-6
measurement during implementation. This is the intended shape: readiness review checks that a plan's
claims about the *current tree* hold, not that its proposed remedy will prove affordable. The AC that
required measuring before adopting is what caught it.
