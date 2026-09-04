# Add Exact ANN Reference and Tuning Certification

Change ID: `1wsc8-enh ann-reference-and-tuning-certification`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
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

- [x] AC-1: The exact-reference test proves `bypass_vector_index()` is invoked; a mutant that silently serves ANN fails.
- [x] AC-2: Repeated exact queries on one frozen snapshot return identical normalized IDs, and an injected ANN omission is reported in the correct layer/query/filter overlap slice.
- [x] AC-3: A candidate with aggregate improvement but a per-slice loss greater than `1/K`, a missing/mismatched default slice, or a quality-neutral result without at least 10% same-sample p95 improvement is rejected; macro aggregation weights each frozen slice equally against library defaults.
- [x] AC-4: When no candidate satisfies every quality, slice, latency, timeout, and standing-gate condition, the predecessor's defaults/no-tuning-call test remains unchanged; when one certifies, the same test asserts exactly the certified method/value receipt and rejects every unmeasured setting.
- [x] AC-5: Exact/ANN reports contain every identity and timing field in Requirement 3, evaluate defaults plus at most three candidates within the total 64-case and two-invocation/360-second/report-size bounds, and detect a deliberately altered table/index/build identity.
- [x] AC-6: The pre-change same-generation pair is captured after evaluator scaffolding and after `1wpif`/`1wpig` complete; the standing 35-fixture comparison records no new quality, latency, or payload violation or explicitly blocks delivery.
- [x] AC-7: Reports disclose evidence tier, canonical evidence role, consulted-holdout status, all named residual class metrics, and evaluator-source ranks; protected/standing cases cannot support gain claims and aggregate improvement cannot hide a regressed class/slice.
- [x] AC-8: `code_ask` citation ordering and report/currentness behavior remain unchanged, and the typed findings-register plan remains separately owned.

## Tasks

- [x] After readiness/activation, implement and freeze the exact/ANN evaluator schema, fixtures, measurement-only `bypass_vector_index()` seam, identity receipt, evaluator-source census, and scorer before production edits.
- [x] Add repeated-exact, forced-omission, slice-regression, false-certification, timeout, and identity-mismatch tests.
- [x] Capture the post-scaffolding/pre-ranking same-generation baseline pair after predecessor waves close and the index is rebuilt/optimized.
- [x] Evaluate library defaults and a bounded candidate set; retain only a fully certified winner.
- [x] Verify the closed `1wpif` predecessor has no inert ANN constants/tuning calls, and update `LanceQueryBuilderDefaultsTests` only if a candidate certifies with an exact method/value receipt.
- [x] Run and publish the exact/ANN component reports plus the standing 35-fixture retrieval comparison.
- [x] Update search/testing architecture and the performance budget; update MCP contracts only if a public response changes.

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
| 2026-09-03 | **Execution step 3 landed: the exact reference and the fail-closed certifier (AC-1, AC-2, AC-3).** | `ann_reference_eval.py`, `test_ann_reference_eval.py` (21 tests), and `docs/evals/ann-reference-golden.json` (5 slices spanning both layers at depths 10 and 50, `.aiignore`d). The exact side routes through a single `_apply_bypass` seam so a spy can prove the bypass ran; both sides start from one shared `_base_query` so metric, limit and prefiltered where clause are identical by construction, and a test asserts the two logs match except for the bypass call itself. A LanceDB build lacking the seam raises `exact_mode_unavailable` rather than silently returning ANN rows. |
| 2026-09-03 | Landing rule: four mutants, four named failures. | Exact mode silently serves ANN → `test_exact_search_invokes_bypass_and_ann_search_does_not` plus `test_a_build_without_the_seam_refuses_rather_than_serving_ann`; a missing slice is skipped instead of rejected → `test_a_missing_slice_is_a_rejection_not_a_skip`; per-slice loss tolerance removed → `test_an_aggregate_gain_hiding_a_slice_loss_is_rejected`; quality-neutral certifies without a latency gain → `test_quality_neutral_needs_a_real_latency_gain`. Requirement 4 and 9 numbers are pinned as literals, not compared against their own constants, after that exact mistake was caught in `1wpid`. |
| 2026-09-03 | **That prediction was WRONG, and the reasoning behind it was wrong too.** | A candidate certified. The error was a category confusion on my part: Requirement 5's evidence-role rule governs GAIN CLAIMS ON THE STANDING FIXTURE CORPUS, whereas certification is a component measurement of ANN-versus-exact overlap, which has no fixture-authorship dimension at all. Zero gain-eligible fixtures never implied a fail-closed certification. Recorded rather than quietly superseded, because the wrong reasoning is the reusable lesson. |
| 2026-09-03 | Exact reference measured on the REAL tables; two candidates rejected, one certified. | Defaults macro overlap `0.96` across five frozen slices (code shallow `0.9`, code deep `1.0`, code filtered `0.9`, docs shallow `1.0`, docs deep `1.0`), exact repetition deterministic on all five. 20 of a 64-case ceiling used across defaults plus three candidates. `nprobes=20` REJECTED (quality neutral, 3.8% latency gain against a required 10%); `nprobes=50` REJECTED (quality neutral and 2.1% SLOWER); `refine_factor=2` certified with mean overlap `0.96` → `1.00` and no slice losing any overlap. The two rejections are what show the certifier discriminating rather than rubber-stamping. |
| 2026-09-03 | **Operator asked for user-visible effect before adoption; measuring it corrected me again.** | I had argued a marginal tenth candidate rarely becomes the lead. Running the real `code_ask` path over all 31 applicable fixture questions, twice, showed the candidate changes the citation SET on 8 and the LEAD on 2, with confidence unchanged on all 31. The effect is real and reaches the user. That comparison consumed no checkpoint: it is a component diagnostic, not a standing-evaluator invocation. |
| 2026-09-03 | Standing gate then settled DIRECTION, which the diff could not. | `docs/reports/retrieval-quality-post-1wsc8-refine2.json`, valid on stable generation 395. Against the pre-candidate state: `code_ask` nDCG@10 `0.5167` → `0.5185`, class `assessment_boundary_control` nDCG `0.8175` → `0.8460`, **zero metrics worse**, and an EMPTY `operator_review_reasons`. That satisfies Requirement 4's final condition. It also retroactively confirms the post-lexical latency flag was contention: the same code path measured clean here. |
| 2026-09-03 | Adopted, with the receipt pinned by the engine's own query plan. | `ANN_REFINE_FACTOR = 2` read at the single call site in `_lance_search`. Per AC-4 the authoritative test changed shape but not strictness: it now asserts the certified method and value and still refuses every unmeasured setting. The plan assertion is the strongest part — it requires engine-default probes (`minimum_nprobes=20`, since both nprobes candidates were rejected), a refine stage present, and an over-fetch of exactly `limit × 2`, which pins the VALUE rather than merely the method. A control shows an uncertified setting producing a plan production must never exhibit. Full suite green at 8,253. |
| 2026-09-03 | **Report written as a receipt, and the receipt is falsifiable (AC-5, AC-7).** | `docs/reports/ann-reference-post-1wsc8.json`, `.aiignore`d, verified excluded from the corpus. All eleven Requirement 3 bindings present: fixture digest, evaluator digest, production identity `7130a19d…`, Lance table version 2305, build epoch 396 with attempt `5a89a44c…`, embedding model and provider, vector-index presence, backend, and a content digest computed over everything else. Five slices each carry layer, query, filter shape, K, both id lists, overlap and both timings. The epoch is read through the SAME accessor the standing evaluator uses, so a report cannot bind an epoch the gate would have refused. |
| 2026-09-03 | The verifier caught my own incomplete first report, which is why it is trustworthy. | The initial write produced three missing bindings (production identity and both epoch fields) because I called the identity helpers with the wrong signatures. `verify_report_identity` reported all three rather than writing a quietly holed receipt; the incomplete file was deleted and regenerated only after the accessors were fixed. Final report: zero identity problems. |
| 2026-09-03 | Landing rule: two mutants, both killed across every field. | Making the content digest self-referential rather than covering the body → `test_a_tampered_identity_breaks_the_content_digest` fails on all four forged fields; removing the missing-binding sweep → `test_a_missing_binding_is_reported_rather_than_tolerated` fails on every required field. The report also records BOTH rejections beside the certification, each with its reason, so an aggregate "one candidate certified" cannot hide that two were refused. Full suite green at 8,260. |
| 2026-09-03 | Incidental finding, outside this wave's scope. | Exact flat scan is roughly twice as FAST as the ANN path on every slice (code `7.9ms` exact against `17.0ms` ANN; docs `19.9` against `30.8`). At this corpus size the vector index is not earning its cost. Not acted on here; recorded because a future wave should know. |
| 2026-09-03 | **Superseded prediction, retained:** certification was expected to fail closed. | `1wscp` landed derived gain eligibility and the annotated standing corpus now has **zero** gain-eligible fixtures, because all 35 were authored by the implementing agent during the wave that built the classifier they measure. Requirement 5 permits only `independent_holdout` evidence to support a gain claim, so no ANN candidate can satisfy the improvement branch from the standing corpus. AC-4's fail-closed branch therefore governs: library defaults and the predecessor's no-tuning-call regression test stay byte-compatible. Recorded in advance so a fail-closed result is not later mistaken for incomplete work. |


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
