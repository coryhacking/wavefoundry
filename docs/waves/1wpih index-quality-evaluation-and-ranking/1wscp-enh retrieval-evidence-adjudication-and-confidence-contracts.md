# Add Retrieval Evidence Adjudication and Confidence-Basis Contracts

Change ID: `1wscp-enh retrieval-evidence-adjudication-and-confidence-contracts`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-31
Wave: 1wpih index-quality-evaluation-and-ranking

## Rationale

Closed wave `1seaw` delivered a reproducible standing retrieval gate, but its review also demonstrated that a green aggregate verdict can coexist with baseline-zero classes, consulted holdouts, oracle/anchor disputes, evaluator-source contamination, and a weak rank-one citation paired with envelope `confidence="high"` because confidence reads the maximum score anywhere in the citation set. Those are evidence-truth defects, not automatically ranking defects. Before `1wpih` changes lexical, semantic, or graph ranking, the gate must distinguish genuine retrieval misses from invalid labels or contaminated carriers and must explain the evidence supporting its public confidence claim.

## Requirements

1. The final closed `1seaw` tuple SHALL be verified as historical predecessor authority: fixture digest `bda675468d4da0184a97a94c4396cf8f379981a19339c1ad4958ba50f9466312`, evaluator digest `61ec60daeb5347984f1e2c3e6f47a48d74931df11edf6f78ce84acb219c9207a`, production digest `dab71287550d9e541b8f36d734ae34b44df84ef83ad8b5b4139c611409cbbae4`, and index attempt `8916932ce45d4cd48e725493bf21eb20`. Superseded injector-era and earlier-generation reports SHALL remain provenance only.
2. Every scored fixture SHALL declare `evidence_role` as `calibration`, `independent_holdout`, or `regression_only` plus `authorship_class` (`independent_reviewer`, `qa_local`, `implementer`, or `historical`), `consultation_status` (`unconsulted`, `consulted`, or `unknown`), and `mechanism_exposure` (`unexposed`, `exposed`, or `unknown`). Gain eligibility SHALL be derived, not trusted from the role label: only `independent_holdout` + `independent_reviewer` + `unconsulted` + `unexposed` may support `minimum_improvement`; every other combination is non-regression-only and false-independence mutants SHALL fail schema validation.
3. Before production ranking changes, every zero-score or disputed `(fixture_id, tool, metric)` SHALL receive one frozen adjudication keyed by that exact tuple. Each receipt SHALL include the public run ID, inspected target path and typed anchor, observed rank/evidence, verdict (`confirmed_retrieval_miss`, `oracle_anchor_miss`, `classifier_contract_mismatch`, `carrier_contaminated`, `typed_surface_required`, or `intentional_limit`), and nonempty rationale. Adjudication SHALL replay the public response and inspect the claimed target rather than infer from aggregate metrics; a fixture-wide label cannot stand in for tool/metric evidence.
4. Reports SHALL identify top-k carriers with `carrier_kind` (`evaluator_source`, `fixture_source`, `generated_report`, `wave_record`, or `review_commentary`), normalized path, rank, `approval_state` (`approved` or `unapproved`), and `effect` (`none`, `displaced_expected`, or `supplied_gain`). An improvement claim SHALL fail when a newly introduced or unapproved carrier displaces expected evidence or supplies the apparent gain.
5. Envelope confidence SHALL describe the final lead used by `answer`, not the maximum score anywhere in the citation list, unless a machine-readable non-semantic basis such as exact owner resolution applies. Public responses SHALL expose `confidence_basis`, and citations SHALL expose `selection_reason`; a weak semantic lead cannot produce unexplained high confidence because a lower-ranked citation scored highly.
6. Upper-snake constant-value questions SHALL use one documented routing contract. The selected contract is `navigational`: it preserves exact declaration rank one, guides callers toward `code_constants`, and leaves unrelated explanatory prose containing “value” unchanged.
7. The second original live review-session misranking phrasing SHALL be recovered verbatim and labeled calibration or `regression_only`; it SHALL NOT be described as an unconsulted holdout.
8. After `1wpif` and `1wpig` complete and this wave is readied/activated, the implementer SHALL land the retrieval evidence/adjudication, ANN reference, lexical-ranking, and graph-quality measurement/schema scaffolds and tests first without changing production ranking/community behavior. QA SHALL approve/freeze and index all four scaffolds, then record immediate baseline A/B before any confidence, routing, lexical, ANN-candidate, or graph-policy production change. Per-tool/split/class results and evaluator-source carrier ranks SHALL remain visible so aggregate improvement cannot mask zero/regressed strata or scaffold contamination. Any index-eligible evaluator scaffold added later invalidates A/B and blocks production work until operator-approved replacement A/B and a revised bounded checkpoint budget are recorded.
9. Findings-register retrieval and report currentness remain owned by `1wq0b-enh findings-register-assessment-surface`. This change SHALL NOT restore a report-path prior, synthetic score, or unverified currentness claim inside `code_ask`.
10. Standing checkpoints SHALL be exactly baseline A/B, post-confidence/routing, post-lexical, one after each of at most three ANN candidate configurations, and post-graph/final, plus at most one documented replay: no more than nine invocations. Each preserves the standing evaluator's 1,200-second/report-1-MiB ceilings; the sequence is capped at 10,800 seconds, 9 MiB, 780 public calls per invocation, and 7,020 calls total. Every failed attempt is retained under a unique exclusive-create filename; exhausting any cap fails closed and requires operator direction.

## Scope

**Problem statement:** The retrieval gate cannot yet distinguish ranking failure from oracle or carrier failure, and public confidence can describe a lower-ranked score rather than the evidence actually presented first.

**In scope:**

- Fixture evidence roles and zero/disputed-case adjudication.
- Carrier-contamination detection across all index-eligible repository content.
- Lead-aware confidence and machine-readable confidence/selection bases.
- One explicit constant-value routing contract and the second original regression phrasing.
- Immediate post-predecessor baseline evidence before other `1wpih` ranking edits.

**Out of scope:**

- Typed findings-register/currentness behavior (`1wq0b`).
- Treating every zero metric as a promised ranking fix.
- Embedding or reranker replacement.
- Reintroducing subject-blind report injection or synthetic citation scores.

## Acceptance Criteria

- [ ] AC-1: The authoritative `1seaw` identities are verified, and a fresh same-state standing pair is recorded after predecessor/evaluator integration and before ranking edits.
- [ ] AC-2: Schema and mutation tests reject false `independent_holdout` authority whenever authorship, consultation, or mechanism exposure is not independently eligible; derived gain eligibility is the sole authority for `minimum_improvement`.
- [ ] AC-3: The current constant-value `(fixture_id, tool, metric)` case is adjudicated as `classifier_contract_mismatch` despite relevant retrieval; a seeded wrong-section case is adjudicated as `oracle_anchor_miss`; each receipt binds public run ID, inspected path/anchor, observation, verdict, and rationale.
- [ ] AC-4: Seeded exact-query carrier self-match, unapproved carrier gain, and top-k carrier displacement fail the contamination gate; a clean independent holdout reports zero unapproved carriers with typed kind/path/rank/approval/effect rows.
- [ ] AC-5: A weak pinned lead plus a strong lower-ranked citation does not yield unexplained high confidence; exact-owner high confidence carries `confidence_basis="exact_owner"`, and every returned citation has a truthful `selection_reason`.
- [ ] AC-6: Both constant-value fixtures classify `navigational`, retain rank-one declarations, and preserve explanatory negative controls.
- [ ] AC-7: The second original review phrasing is present as calibration/regression evidence, and reports never describe it as independent holdout evidence.
- [ ] AC-8: Standing retrieval, lexical component, latency, payload, and full framework gates pass on the frozen post-predecessor state; any class/split regression blocks delivery.
- [ ] AC-9: Organic `code_ask` citation ordering remains free of report-path injection, and findings-register/currentness behavior stays outside this change.
- [ ] AC-10: The exact nine-invocation checkpoint/replay ceiling, cumulative time/call/report-byte limits, exclusive filenames, failed-attempt retention, and fail-closed exhaustion behavior are enforced.

## Tasks

- [ ] Freeze the closed `1seaw` identity/adjudication manifest and immediate baseline protocol.
- [ ] Extend fixture/report schemas with derived evidence-role authority, `(fixture_id, tool, metric)` adjudication receipts, and typed carrier/effect evidence.
- [ ] Expand the holdout leak/carrier scan across all index-eligible repository content.
- [ ] Implement lead-aware confidence, `confidence_basis`, and citation `selection_reason`.
- [ ] Implement and document the constant-value navigational routing contract with negative controls.
- [ ] Recover and classify the second original review-session phrasing.
- [ ] After readiness/activation, freeze/index the scaffold, record baseline A/B, then run only the bounded post-confidence, post-lexical, per-candidate ANN, and post-graph/final checkpoints.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Evidence schema/adjudication implementation | implementer | Wave readied/activated; `1wpif`, `1wpig` complete | Schema/tests only before production ranking edits |
| Evidence approval and baseline | qa-reviewer | Scaffold implemented/indexed | Freeze roles/adjudications and execute A/B independently |
| Confidence/routing contract | implementer | Evidence schema | Public response and classifier behavior |
| Independent verification | qa-reviewer, docs-contract-reviewer | Implementation | Carrier, confidence, parity, and standing-gate replay |


## Serialization Points

- `.wavefoundry/framework/scripts/retrieval_eval.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_retrieval_eval.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py`
- `.wavefoundry/framework/seeds/211-guru.prompt.md`
- `docs/evals/retrieval-quality-golden.json`
- `docs/agents/guru.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/search-architecture.md`
- `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`
- `docs/architecture/testing-architecture.md`
- `docs/specs/mcp-tool-surface.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Ranking work needs an authoritative immediate baseline. |
| AC-2 | required | Prevents consulted fixtures from masquerading as improvement evidence. |
| AC-3 | required | Separates evaluator/oracle defects from product ranking defects. |
| AC-4 | required | The evaluator and its artifacts must not improve their own measured ranking. |
| AC-5 | required | Confidence is a public trust contract tied to the evidence users see. |
| AC-6 | important | Resolves a measured classifier-contract mismatch without broad heuristics. |
| AC-7 | important | Preserves the original user signal without overclaiming independence. |
| AC-8 | required | Every later ranking change remains standing-gate controlled. |
| AC-9 | required | Preserves the operator-approved rejection of report injection. |
| AC-10 | required | Stage-wise replay must remain operationally bounded and fail closed. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-31 | Planned from closed `1seaw` review findings and final baseline residuals. | Final 35-fixture pair; cycle-2 council; constant-value, enumeration, assessment, contamination, and confidence evidence. |
| 2026-08-31 | Made evidence authority and stage-wise replay machine-complete. | Final QA review required derived independence fields, tool/metric adjudication receipts, typed carrier effects, and a fixed nine-invocation sequence budget after readiness/activation. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-31 | Adjudicate evidence before fixing ranking and make confidence lead-aware. | Closed `1seaw` showed aggregate green can coexist with oracle disputes, consulted fixtures, and misleading confidence. | **Treat all zeroes as ranking bugs:** fixture-fitting risk. **Ignore residuals:** leaves the next wave unable to make honest improvement claims. |
| 2026-08-31 | Keep findings-register access in `1wq0b`. | A typed structural surface is different from organic retrieval evidence and currentness. | **Reintroduce a report prior:** explicitly rejected by the closed council. **Absorb the typed surface here:** unnecessarily broadens this ranking/evidence contract. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Adjudication becomes subjective relabeling | Freeze enums, public replay evidence, target inspection, and mutation tests before ranking edits. |
| Carrier scan rejects legitimate repository evidence | Declare approved carrier roles and report exact path/rank/reason rather than blanket-excluding classes. |
| Lead-aware confidence lowers existing bands | Treat it as truthful contract repair, publish before/after bands, and preserve exact-owner non-semantic confidence. |
| Constant-value heuristic overmatches prose | Restrict to upper-snake constant-value form and retain explanatory negative controls. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
