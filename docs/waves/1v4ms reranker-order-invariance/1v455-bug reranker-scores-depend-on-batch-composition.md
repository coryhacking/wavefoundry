# Reranker Scores Depend On Batch Composition

Change ID: `1v455-bug reranker-scores-depend-on-batch-composition`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-12
Wave: 1v4ms reranker-order-invariance

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

- [ ] AC-1: Reranking the same candidate set in different input orders produces identical scores, asserted on a pool larger than `RERANK_STATIC_BATCH`.
- [ ] AC-2: Reranking the same candidate set in different input orders produces an identical ranking, asserted on the same oversized pool.
- [ ] AC-3: Every score that is compared against another score is produced under the same batch composition, or the comparison sites are shown not to compare across compositions.
- [ ] AC-4: The GPU / FP16 reranker path is unchanged, asserted by a test that fails if its batching or graph selection changes.
- [ ] AC-5: A regression test fails if reranker output becomes order-dependent again, using the oversized-pool oracle from AC-1.
- [ ] AC-6: The retrieval-quality effect of the chosen remedy is measured against the current behaviour on a pool of realistic size, with the query set, pool construction, and per-query results recorded in the Progress Log. If the remedy drops candidates, the recall cost is stated explicitly.
- [ ] AC-7: Reranker latency before and after is measured and recorded, since the remedy may change the number of inference calls per query.

## Tasks

- [ ] Reproduce order-dependence as a failing test before changing behaviour, using an oversized pool and the shuffle oracle from the Rationale.
- [ ] Enumerate every consumer of reranker scores and record which ones compare scores across batch boundaries. Use `code_references` on the scoring seam rather than an identifier grep, per the census-instrument rule in seed 209.
- [ ] Choose the remedy and record the decision with its measured tradeoff.
- [ ] Implement the remedy and make the reproduction test pass.
- [ ] Add the GPU-path pin required by AC-4.
- [ ] Measure retrieval quality and latency before and after; record both.
- [ ] Update ADR `1v22e`'s reranker section from confirmed-open to resolved, retaining the measurements.

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
