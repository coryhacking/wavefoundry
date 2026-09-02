# Add Exact ANN Reference and Tuning Certification

Change ID: `1wsc8-enh ann-reference-and-tuning-certification`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-31
Wave: 1wpih index-quality-evaluation-and-ranking

## Rationale

The landed `1wpif` predecessor is expected to use Lance library defaults with no production `nprobes`/`refine_factor` calls and no inert tuning constants; its authoritative query-builder test locks that state. Production still lacks an exact-search reference that can certify whether any candidate setting improves recall or latency. Closed wave `1seaw` supplies a production-path 35-fixture regression corpus and auditable environment/production receipts, but it measures end-user retrieval rather than ANN-versus-exact candidate overlap. This change adds the missing component reference and a fail-closed certifier before any ANN setting is introduced.

## Requirements

1. The evaluator SHALL expose a measurement-only Lance exact mode using `bypass_vector_index()` against the same immutable table snapshot, query vector, metric, filter, and production candidate depth as the ANN query. Production `_lance_search` behavior SHALL remain unchanged unless a candidate setting certifies.
2. Reports SHALL score ANN-versus-exact `overlap@K` per semantic layer, query, filter shape, and production candidate depth. Stable ties SHALL normalize by chunk ID, and exact-reference repetition SHALL return identical normalized IDs before a candidate can be judged.
3. Each exact/ANN report SHALL bind the fixture and evaluator digests, production retrieval identity, Lance table/index version, completed build epoch and attempt, embedding model/provider, query/filter/K, vector-index presence, backend, exact IDs, ANN IDs, timings, and report-content identity.
4. The production library-default configuration SHALL be the sole comparator. Certification SHALL use a macro mean with one equal-weight observation for every identical frozen `(layer, query, filter, K)` key; candidate/default key sets and sample sets SHALL match exactly, and a missing slice fails. A candidate SHALL be rejected unless exact repetition is deterministic; mean overlap versus defaults improves by at least 0.02 absolute, or quality remains within 0.005 while candidate ANN warm p95 on that same slice/sample set improves by at least 10%; no slice loses more than `1/K` overlap; and the standing retrieval gate has no new fixture, class, split, critical-floor, latency, or payload violation. If no candidate certifies, the predecessor's library-default/no-tuning-call implementation and authoritative regression test remain byte/behavior compatible. If one certifies, that test SHALL change to assert only the exact certified query-builder method/value receipt; no unmeasured setting or inert constant may appear.
5. Evaluation SHALL label evidence tiers honestly and map them to the wave's canonical `evidence_role`: `standing_regression` and QA-owned `protected_local_holdout` are `regression_only`; `independent_out_of_sample` is `independent_holdout` only when an author who was not exposed to the mechanism supplies the cases; mechanism-selection cases are `calibration`. Only `independent_holdout` may support a gain claim.
6. After the wave is readied and activated, the immediate pre-change baseline SHALL be captured after the measurement-only evaluator schema, fixtures, `bypass_vector_index()` seam, and tests are implemented, frozen, and indexed, but before any production query/tuning or candidate-parameter integration. Evaluator-source occurrences in unrelated result lists SHALL be censused and reported so the new runner cannot improve or regress its own corpus invisibly.
7. The closed `1seaw` authority SHALL be recorded as historical regression input: 35 fixtures, digest `bda675468d4da0184a97a94c4396cf8f379981a19339c1ad4958ba50f9466312`, evaluator digest `61ec60daeb5347984f1e2c3e6f47a48d74931df11edf6f78ce84acb219c9207a`, and final production digest `dab71287550d9e541b8f36d734ae34b44df84ef83ad8b5b4139c611409cbbae4`. Because `1wpif` and `1wpig` change indexed state and production identity first, delivery claims SHALL use a new same-generation baseline pair captured on their completed state rather than comparing directly against the historical generation.
8. Existing measured residuals SHALL remain visible per tool, split, and class instead of being masked by aggregate improvement: zero `architecture_review_intent` holdout recall/nDCG, zero `enumeration`/`docs_search` holdout recall, zero `constant_value_lookup` question-type accuracy, zero `exact_identifier_lexical` holdout recall, and evaluator-source rows occupying unrelated result slots. These are diagnostic strata, not automatic scope commitments for this change.
9. The complete certification SHALL compare library defaults plus at most three candidate configurations across at most 64 total `(configuration, layer, query, filter, K)` cases—not 64 per candidate—using identical frozen slice/sample sets, one warm-up plus exactly three measured repetitions, and nearest-rank p95. One certification invocation has a 15-second exact-reference timeout per query and a 180-second total timeout; at most one documented replay is permitted, the two-invocation sequence is capped at 360 seconds, each exclusive-created report at 1 MiB, and all certification reports at 2 MiB. Any timeout, missing slice, overwrite attempt, or exhausted replay fails. Production ANN p95 SHALL not regress by more than `max(10%, 3 * same-generation jitter, 25 ms)`; standing tool thresholds and the 256 KiB envelope ceiling remain governed by the immediate baseline pair.
10. Findings-register retrieval and report currentness remain owned by `1wq0b-enh findings-register-assessment-surface`. This change SHALL NOT add a report-path injector, synthetic citation score, or unverified currentness claim to `code_ask`.

## Scope

**Problem statement:** ANN settings cannot be selected honestly because production lacks an exact candidate reference, slice-level overlap evidence, and a fail-closed improvement certifier.

**In scope:**

- Measurement-only exact Lance queries and normalized overlap scoring.
- Candidate ANN settings, only after the evaluator and immediate baseline are frozen.
- Standing retrieval non-regression and evaluator-source contamination reporting.
- Determinism, latency, timeout, environment, and report-identity controls.

**Out of scope:**

- Changing embedding or reranking models.
- General lexical ranking, owned by `1wpid`.
- Graph fidelity/community isolation, owned by `1wpie`.
- Typed findings-register/currentness behavior, owned by `1wq0b`.
- Shipping an ANN tuning value that fails or cannot complete certification.

## Acceptance Criteria

- [ ] AC-1: The exact-reference test proves `bypass_vector_index()` is invoked; a mutant that silently serves ANN fails.
- [ ] AC-2: Repeated exact queries on one frozen snapshot return identical normalized IDs, and an injected ANN omission is reported in the correct layer/query/filter overlap slice.
- [ ] AC-3: A candidate with aggregate improvement but a per-slice loss greater than `1/K`, a missing/mismatched default slice, or a quality-neutral result without at least 10% same-sample p95 improvement is rejected; macro aggregation weights each frozen slice equally against library defaults.
- [ ] AC-4: When no candidate satisfies every quality, slice, latency, timeout, and standing-gate condition, the predecessor's defaults/no-tuning-call test remains unchanged; when one certifies, the same test asserts exactly the certified method/value receipt and rejects every unmeasured setting.
- [ ] AC-5: Exact/ANN reports contain every identity and timing field in Requirement 3, evaluate defaults plus at most three candidates within the total 64-case and two-invocation/360-second/report-size bounds, and detect a deliberately altered table/index/build identity.
- [ ] AC-6: The pre-change same-generation pair is captured after evaluator scaffolding and after `1wpif`/`1wpig` complete; the standing 35-fixture comparison records no new quality, latency, or payload violation or explicitly blocks delivery.
- [ ] AC-7: Reports disclose evidence tier, canonical evidence role, consulted-holdout status, all named residual class metrics, and evaluator-source ranks; protected/standing cases cannot support gain claims and aggregate improvement cannot hide a regressed class/slice.
- [ ] AC-8: `code_ask` citation ordering and report/currentness behavior remain unchanged, and the typed findings-register plan remains separately owned.

## Tasks

- [ ] After readiness/activation, implement and freeze the exact/ANN evaluator schema, fixtures, measurement-only `bypass_vector_index()` seam, identity receipt, evaluator-source census, and scorer before production edits.
- [ ] Add repeated-exact, forced-omission, slice-regression, false-certification, timeout, and identity-mismatch tests.
- [ ] Capture the post-scaffolding/pre-ranking same-generation baseline pair after predecessor waves close and the index is rebuilt/optimized.
- [ ] Evaluate library defaults and a bounded candidate set; retain only a fully certified winner.
- [ ] Verify the closed `1wpif` predecessor has no inert ANN constants/tuning calls, and update `LanceQueryBuilderDefaultsTests` only if a candidate certifies with an exact method/value receipt.
- [ ] Run and publish the exact/ANN component reports plus the standing 35-fixture retrieval comparison.
- [ ] Update search/testing architecture and the performance budget; update MCP contracts only if a public response changes.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Schema, fixtures, and measurement-only exact seam | implementer | Wave readied/activated; `1wpif`, `1wpig` complete | QA approves corpus/schema independently before production edits |
| Baseline freeze and execution | qa-reviewer | Measurement seam indexed | Exact-default component and standing same-state baselines |
| Candidate parameter integration | implementer | Frozen baselines | Defaults plus at most three bounded settings |
| Independent certification | qa-reviewer, performance-reviewer | Candidate integration | Slice, standing-gate, and cost verdict |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/retrieval_eval.py`
- `.wavefoundry/framework/scripts/ann_reference_eval.py`
- `.wavefoundry/framework/scripts/tests/test_ann_reference_eval.py`
- `.wavefoundry/framework/scripts/tests/test_retrieval_candidate_generation.py`
- `docs/evals/ann-reference-golden.json`
- `docs/reports/ann-reference-*.json`
- `docs/architecture/search-architecture.md`
- `docs/architecture/testing-architecture.md`
- `docs/architecture/performance-budget.md`

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`
- `docs/architecture/testing-architecture.md`
- `docs/architecture/performance-budget.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reference is invalid if it silently uses the ANN index. |
| AC-2 | required | Deterministic exact IDs and slice-local omission detection are the fidelity oracle. |
| AC-3 | required | Prevents aggregate gains from hiding a user-visible slice regression. |
| AC-4 | required | Certification must fail closed when no setting is better. |
| AC-5 | required | Identity and runtime bounds make the evidence reproducible and operational. |
| AC-6 | required | Standing retrieval behavior remains the delivery gate. |
| AC-7 | important | Honest evidence tiers and residual visibility prevent overclaiming. |
| AC-8 | required | Preserves the closed wave's rejection of subject-blind report injection. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-31 | Planned from the `1wpif` readiness council relocation and closed `1seaw` evaluator evidence. | Final 35-fixture baseline pair and production-change receipt; current inert ANN constants/query-builder inspection. |
| 2026-08-31 | Repaired comparator, aggregation, candidate bound, and stage-gate sequencing. | Final QA/architecture review required defaults-only comparison, macro-identical slices, total-case/replay ceilings, and measurement seam before baseline but only after readiness/activation. |
| 2026-08-31 | Bound candidate integration to the predecessor's authoritative default-query regression test. | Final code review found `1wpif` had already removed inert constants and added an AST/runtime guard against unmeasured Lance tuning calls. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-31 | Create a dedicated ANN certification change and admit it to `1wpih`. | Vector-index reference/certification is materially different from lexical fusion and graph community work. | **Expand `1wpid`:** obscures lexical scope and ownership. **Leave only a wave note:** no admitted AC owns delivery. **Tune constants directly:** post-hoc and uncertified. |
| 2026-08-31 | Keep `1wq0b` separate. | Closed `1seaw` explicitly rejected report-path injection; typed findings access is a public-surface change, not ANN/ranking certification. | **Absorb findings-register work here:** expands the wave and confounds semantic ranking with a separate structural evidence channel. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Exact mode accidentally uses ANN | Require a query-builder spy and a mutant that fails unless `bypass_vector_index()` runs. |
| Component overlap improves while end-user retrieval regresses | Gate every candidate on the immediate standing retrieval pair and per-class/split checks. |
| Evaluator fixtures contaminate their own index | Capture scaffolding before baseline, census evaluator-source ranks, and keep protected evidence outside independent claims. |
| Exact queries are too costly | Bound cases, repetitions, per-query timeout, and total evaluator time; never use exact mode on public queries. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
