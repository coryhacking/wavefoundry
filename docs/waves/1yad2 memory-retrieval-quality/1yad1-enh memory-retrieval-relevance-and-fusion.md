# Memory retrieval relevance and fusion

Change ID: `1yad1-enh memory-retrieval-relevance-and-fusion`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-09-17
Wave: `1yad2 memory-retrieval-quality`

## Rationale

Local agents should retrieve the useful project lesson quickly without mistaking a related memory for authoritative guidance. Improve memory retrieval only: compare direct memory-scoped semantic and lexical search, preserve eligibility and recovery contracts, and adopt a measured winner. Regular code and docs query evaluation is separate future work.

Exploration found that permissive lexical admission followed by confidence-first ordering can bury directly relevant memories. Memory-scoped vectors recovered all expected records within 20 candidates on the initial sample. Plain RRF and score fusion produced strong top-three retrieval without the cross-encoder; however, neither ranking is an abstention mechanism, and relevance does not establish authority between contradictory active records.

The latest comparison selected parameters on 44 development queries, then evaluated 24 fresh queries (16 answerable, eight no-match). Plain RRF scored Recall@3 95.83%, Recall@10 100%, MRR 0.9583. Min-max score fusion with 75% semantic and 25% BM25 scored 97.92%, 100%, 0.9583: one extra relevant result in the top three, not proof of general superiority. Weighted RRF selected equal weights; lexical injection did not beat semantic-only on that held-out set. Retrieval was about 26 ms median on this small local corpus, with fusion under 0.1 ms. All eight no-match controls returned results when abstention was intentionally disabled.

A top-three relevance check reduced false positives but rejected useful paraphrases. A cosine cutoff fitted on the first sample failed on harder negatives. Action-first text improved some failures but lacks independent validation. Existing policy tests explicitly prefer high trust over relevance; a relevance-first implementation cannot silently claim to preserve that contract. These are exploratory, same-investigator labels, reused local data and single-machine timings, not release qualification. Retained evidence is linked from the wave record.

## Requirements

1. Build a reproducible full-corpus memory evaluation with immutable, versioned queries, relevance judgments, corpus/model fingerprints, parameter manifests, and separate development and untouched holdout sets. Have a reviewer who did not tune the ranker adjudicate expected results before final scoring. Include paraphrases, identifiers, ambiguous questions, near-topic no-match queries, duplicates, conflicting claims, and historical records. Query text must not simply copy its expected memory summary. Report candidate recall, Recall@3/10, MRR, judged irrelevant results, unjudged results, answerable abstentions, no-match false positives, per-stage latency and result counts separately.
2. Compare production behavior, plain RRF and score fusion using the same eligible corpus, embeddings, record-level deduplication and candidate budgets. Keep weighted RRF and lexical injection as bounded controls; do not multiply sweeps after reading holdout outcomes. Capture actual cosine/BM25 scores and normalization population; normalized scores and RRF scores are not calibrated probabilities. Search memory before applying candidate limits rather than filtering ordinary docs' final hits. A production implementation must avoid the exploratory full-subtree enumeration; prove eligible candidate coverage and bound work. Preserve compact archive-register semantics instead of silently excluding every archived reference.
3. Decide ranking versus authority explicitly before production integration. Preserve rejected/stale/superseded body exclusions, history opt-in, exact target/symbol filtering, archive entry/body distinctions and provenance. Resolve whether query relevance may precede confidence and freshness; record the changed invariant and its rationale if approved during review. Keep `memory_brief` and unsolicited advisory ordering unchanged unless separately admitted. Return enough existing evidence/status metadata for an agent to distinguish retrieved advice from current authority. Do not infer supersession from timestamps or similarity, silently rewrite records, or invent conflict resolution.
4. Evaluate abstention and candidate presentation separately from ranking. Keep no-match and broad-paraphrase cases in the holdout. Compare no hard gate with bounded relevance checks using raw scores and clearly scoped text representations. Test per-record qualification so one passing hit cannot validate an unrelated tail. Choose abstention versus uncertain-candidate behavior through an explicit documented contract; no universal threshold is justified by the exploratory cutoffs. Relevance checking is optional only if the selected design specifies and tests its unavailable/error behavior. Preserve useful no-index lexical recovery and distinguish unavailable infrastructure from zero relevant results.
5. Gate adoption on independently reviewed holdout results: no regression versus production in Recall@3, Recall@10 or MRR; no increase in answerable misses or no-match false positives; at least one material benefit whose minimum effect is fixed during readiness before holdout scoring. Report counts and paired outcomes, not only rounded averages. Do not promote the current one-result advantage to a guaranteed win. If neither finalist passes, ship the improved evaluation and document non-adoption while leaving production ranking unchanged; do not silently weaken a gate.
6. Measure cold and warm CPU execution, stage costs, p50/p95/p99 and corpus-size behavior, including high duplicate-chunk counts. Provisional readiness budget: warm end-to-end p95 must not exceed the production control under the same run conditions; establish the absolute latency and candidate-count bounds during readiness before tuning. GPU is optional, not required. Test supported Python versions and portable path handling; identify native platforms actually executed versus simulated. No new native/runtime dependency, hosted service, database migration, model change or automatic re-embedding is planned.
7. Make the evaluation tool distinguish production, experimental candidates, unavailable measurements and adoption decisions. Preserve aggregate-only MCP output: no corpus bodies, record identities or queries in ordinary evaluation responses. Detailed local evidence remains explicitly generated repository-owned evaluation output. Update affected contracts and release notes only to reflect delivered user benefits, not exploratory fixes or unselected variants.

## Readiness qualification contract

The pre-scoring thresholds and evaluation protocol in [readiness contract](evidence/readiness-contract.md) are part of this plan: no quality regression, at least five percentage points Recall@3 gain or 20% warm p95 improvement, warm p95 at most 500 ms and no worse than production, 20 semantic plus 20 lexical record candidates, and independently authored frozen holdout. Empty answerable responses remain in metric denominators; any nonempty no-match response counts as a false positive. Physical scan work is reported separately from bounded result materialization. Production-path comparison and same-source ablation distinguish retrieval-coverage changes from fusion gains.

## Production integration decision — 2026-09-17

Operator approved integration of the qualified follow-up candidate. Historical non-adoption remains accurate for the original frozen comparison; this revision adds a separately reviewed production integration and fresh verification. This section governs the selected implementation; exploratory alternatives and prior no-selection statements are historical evidence.

- Explicit free-text memory queries use eligible memory body vectors grouped by canonical path before LIMIT 20, lexical BM25 top20, equal-weight RRF k60, and summary-only (title fallback if empty) CPU cross-encoder qualification over exactly the first five identities. Raw finite logit >= -4 passes; preserve RRF order and return at most min(requested limit,5). No unchecked tail, refill or threshold tuning on observed holdout.
- Eligibility/status/kind/target/symbol filters precede retrieval. Compact archive-register entries retain independent lexical identity. Deliberately unindexed historical bodies remain searchable through the explicit lexical recovery path; do not require re-embedding archives. Empty-query/target-only listings, memory_brief and unsolicited advisories retain existing policy ordering. Confidence, provenance, validation and successor metadata remain intact; relevance does not establish authority or resolve contradictions.
- Missing, stale, incomplete or unusable semantic state and unavailable/failed/nonfinite relevance checking return existing all-token lexical + policy recovery with an explicit unavailable/fallback diagnostic. Never return unchecked semantic candidates or claim fallback is qualified success. Healthy zero qualified candidates is distinguished from unavailable infrastructure.
- Response/tool docs identify the selected retrieval method, qualification availability and checked candidate cap. A passing model score is relevance-screened candidate evidence, not verified answer support. No model-generated answers, host-agent dependency, new model, native dependency, schema change or global code/docs ranking change. Use the existing CPU reranker safely without mutating a shared global provider or affecting other search paths.
- Four known adjacent positive-query tails are not claimed fixed by this representation. Address misuse through honest support-unverified semantics and independently measure direct-support precision before shipping. Tightening score, keyword or relative-gap thresholds would be a new candidate requiring a new untouched holdout.

### Fresh integration verification gates

Freeze the implementation parameters above before scoring a new independent set of at least 24 queries, including at least eight absent/near-topic conceptual negatives, broad paraphrases and exact identifiers. Keep prior questions as development/regression only. Independently classify EVERY returned record from both baseline and candidate as direct_support, adjacent_context or irrelevant_or_unsupported; report contradictions separately. Pooled direct-support precision is direct-support returned records divided by all returned records (including negative-query returns); unjudged records prevent a precision qualification, never count as correct. No numerical absolute precision floor is asserted without evidence: the fixed floor is the measured paired production precision, plus no regression in useful-answer success, Recall@3/10/MRR, paired loss-of-useful-answer and no-match false-positive gates. No unsupported authority/conflict promotion is allowed. Retain 500 ms CPU p95 and material gain >=5pp Recall@3 or >=20% p95 over 100 warm calls. Report cold separately and per-query added adjacent tails. Failure retains non-adoption, not an unapproved posthoc gate. Operator decision on 2026-09-17 explicitly accepts an empty response replacing a baseline response containing no useful evidence: measure and report paired new-empty responses, but block on loss of a useful answer, not loss of an irrelevant nonempty response. This is a disclosed operator-approved acceptance revision after the preflight, not an unchanged predeclared gate. All other frozen parameters and precision/quality/false-positive/latency requirements remain unchanged.

Production-path tests must prove all filters, archive/history behavior, no-query behavior, limit handling, duplicate grouping, malformed/nonfinite reranker scores, missing/code-only/stale store, provider failure and recovery metadata. Fault mutations must fail meaningful tests. Re-run the canonical suite and delivery review after integration. Native-platform claims remain limited to executed platforms.

## Scope

**Problem statement:** Memory search has a strong candidate source but inadequate evidence for relevance-versus-policy ordering and reliable no-match handling. The current live evaluator's self-summary queries over a 12-record subset cannot qualify a replacement.

**In scope:** evaluation harness and fixtures; memory-scoped candidate retrieval; record deduplication; two fusion finalists and bounded controls; policy/fallback contract decision; optional gated memory-search integration; diagnostics, performance evidence and documentation.

**Out of scope:** regular `code_search`, `docs_search` and `code_ask` ranking changes; graph retrieval; embedding/model replacement; storage/schema migration; bulk memory curation; automatic contradiction resolution; changes to wave lifecycle or agent orchestration; default changes to `memory_brief` or read-tool advisories.

## Acceptance Criteria

- [x] AC-1: A frozen evaluation manifest identifies the full candidate corpus, independently reviewed relevance labels, disjoint development/holdout queries and fixed parameters; the report separates every metric and limitation named in requirement 1. (required)
- [x] AC-2: Production, plain RRF and score-fusion comparisons share eligibility, representation and candidate budgets; candidate-stage evidence locates losses before/after fusion, with bounded memory-scoped retrieval and record deduplication tested. (required)
- [x] AC-3: Status, history, exact-target/symbol and archive behaviors have positive and negative controls; the relevance/trust/freshness decision is explicit, with any changed policy invariant approved before integration and no implication that ranking resolves active contradictions. (required)
- [x] AC-4: The chosen no-match/uncertainty contract is exercised on absent topics, near-misses, broad paraphrases and unrelated result tails; unavailable semantic models, missing/stale indexes and unavailable/failing relevance models follow the documented recovery path. (required)
- [x] AC-5: An adoption report applies the predeclared quality gates to untouched holdout evidence and either selects one passing implementation or records non-adoption with production ordering preserved. (required)
- [x] AC-6: Bounded performance evidence records corpus size, duplicate-chunk density, candidate caps, cold/warm latency distributions, hardware/model/runtime versions and the declared budget verdict; platform qualification claims match execution. (required)
- [x] AC-7: The memory evaluation response and documentation distinguish production from experiments without leaking record identities or text; public memory-search behavior and fallback guidance match the delivered selection. (required)
- [x] AC-8: The change's own suites and every test it adds pass, edited documents validate, and no failure elsewhere is attributable to this change; regular code/docs search and advisory/brief behavior remain unchanged by this change. (required)

## Tasks

- [x] Preserve the exploratory report and evidence limitations; reconcile the current public memory-search/evaluator contract and consumer census.
- [x] During readiness, fix quality effect size, latency/candidate budgets, policy decision procedure and reviewer-owned holdout protocol before tuning.
- [x] Author independent relevance judgments and reproduce the production baseline through the public response path.
- [x] Implement the bounded evaluation comparisons and candidate-stage diagnostics.
- [x] Exercise status/history/authority, negative queries, duplicates, model/index failure and no-index recovery controls.
- [x] Run the frozen performance and holdout evaluation; record the adoption decision and paired differences.
- [x] Integrate only a passing, reviewed memory-search design, or preserve production behavior with an explicit non-adoption outcome.
- [x] Update architecture/reference/tool documentation and user-facing changelog if behavior changes; run focused verification and required delivery reviews.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Corpus and judgments | QA reviewer | — | Independent of ranker tuning; freezes holdout labels before scoring. |
| Retrieval evaluation | Implementer | Corpus and judgments | Owns candidate/fusion experiments and bounded prototype. |
| Policy and integration | Architect / implementer | Retrieval evaluation | Explicit authority decision; no automatic adoption. |
| Delivery verification | QA, code, performance, docs-contract reviewers | Policy and integration | Verify public path, failures and measured adoption claim independently. |

## Serialization Points

`server_impl.py` is shared: one writer owns memory-search integration and public evaluation response edits. Freeze labels and parameters before holdout scoring; a failed holdout becomes development data and requires a fresh holdout for any retune. Architecture/policy approval precedes editing production ranking. Preserve current standalone code/docs search behavior and marker-owned surfaces; no seed or generated-surface changes are planned.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/memory_eval.py`
- `.wavefoundry/framework/scripts/memory_records.py`
- `.wavefoundry/framework/scripts/sqlite_vector_store.py`
- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/tests/test_memory_eval.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `.wavefoundry/framework/scripts/tests/eval/memory_golden.json`
- `docs/references/memory-retrieval-eval.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/search-architecture.md`
- `docs/architecture/testing-architecture.md`
- `docs/architecture/performance-budget.md`

Storage modules are inspection targets; edit only if a bounded existing-store memory filter requires it, with no schema change. The root changelog is a prose/release target.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md`: memory candidate and ranking path, authority boundary and model-failure behavior.
- `docs/architecture/testing-architecture.md`: independent judgments, frozen holdout and policy fault probes.
- `docs/architecture/performance-budget.md`: measured memory-search budget and test conditions.
- `docs/references/memory-retrieval-eval.md` and `docs/specs/mcp-tool-surface.md`: evaluator semantics, privacy and selected public behavior.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevent self-query and holdout leakage from becoming quality claims. |
| AC-2 | required | Compare engines fairly and bound the shipped work. |
| AC-3 | required | Retrieval must not silently redefine authority. |
| AC-4 | required | False positives and degraded operation remain unresolved. |
| AC-5 | required | Adopt only a measured improvement. |
| AC-6 | required | Preserve the local performance/deployment value. |
| AC-7 | required | Accurate, private and actionable public results. |
| AC-8 | required | Verify the delivered scope and unchanged neighboring paths. |

## Progress Log

2026-09-17 Operator-requested evidence cleanup: replaced the stale evidence index with the final decision and compact lessons; retained immutable review records, final raw outputs, blind judgments and byte-identical frozen inputs. Retired superseded experiment dumps/logs with hashes in evidence/retention-manifest.json. No production, test, parameter, label or approval changes.

2026-09-17 Final integration verification: AC-8 and all tasks complete; canonical suite passed 9,126 tests (12 skips), current receipt hash independently reproduced, full MCP docs gate green and whitespace check clean. Current results and limits are in evidence/summary5-final-verification.md. Earlier non-adoption completion entries remain historical; current production behavior is the reviewed summary5 integration. Both repair findings independently cleared; zero memory proposals. Wave remains open, uncommitted and unpushed.

2026-09-17 Observe: both delivery repairs passed fresh independent public-tool/native-SQL verification and known-bad mutations. Production reproduces all 24 frozen candidate lists; the original public function reproduces its 24 lists on the same snapshot with no semantic failures. Useful expected-set queries improve 12/16 to 15/16, blind direct-support queries 11/16 to 15/16, precision 11/16 to 15/21, no-match returns remain 0/8, and p95 falls 614.0ms to 192.2ms. Six adjacent returns remain for caller judgment. AC-4 through AC-7 verified by summary5-production-qualification.md plus final independent reviews. Thought: run final canonical suite and documentation validation for AC-8, then record final review authority without closing or committing.

2026-09-17 Observe: AC-3 verified by implementation controls and independent delivery probes for status/history, target/symbol/kind eligibility, distinct archive entries, confidence preservation and unchanged queryless briefing. Evidence: summary5-implementation.md, summary5-delivery-review.md and summary5-delivery-qa.md. AC-4/7 remain open for the recorded freshness and recovery-guidance repairs; no approval inferred from passing neighboring controls.

2026-09-17 Observe: production implementation passed 238 focused tests and four meaningful fault mutations; source frozen for independent delivery review. Operator clarified that the calling agent assesses relevance and support for memories just as for semantic, lexical and graph results; public guidance and support_verified=false reflect this. Review reproduced a same-path changed-source freshness gap; retain AC-4 open and repair within the existing stale-state contract. The public benchmark refused an interrupted local build epoch before querying; standard all-content incremental recovery completed, with no receipt or index-state edits.

2026-09-17 Operator decision: proceed because increased useful results justify replacing an irrelevant baseline response with an empty response. Runtime remains local CPU summary qualification; independent agents validate evidence during evaluation/review, not an extra agent call per search. Integration preflight original labels: 15/16 useful vs12/16, 0/8 no-match both, p95 200ms vs694ms; blind direct-support judgments 15/16 vs11/16, pooled precision15/21 vs11/16. The new empty response is reported explicitly; no baseline-useful query is lost. Revise only that acceptance condition and renew readiness before implementation.

2026-09-17 Readback: before, explicit queries use docs-wide candidates and confidence-first ordering; after, eligible memory-scoped RRF plus five CPU summary checks returns bounded relevance-screened candidates with authority metadata unchanged. Renew AC-3 through AC-8 for production integration and fresh precision/failure verification. Gapfill: MCP code_definition failed with index_compatibility.register_loaded_source unavailable; direct code_read works, with narrow rg used only to locate the definition.

2026-09-17 Observe: follow-up evaluation completed with frozen fresh QA labels. RRF + summary-only top-five checks found useful memories for 11/12 positives versus production 8/12, rejected all eight absent-fact queries versus production two false positives, and measured 196.2 ms p95 versus 674.6 ms. No new empty response or production-relevant hit loss; QA independently recomputed metrics. Four adjacent positive-query tails remain. Blind host-agent support validation found 12/12 with zero no-match responses but lacks serving/cost qualification. Reflect: representation helps substantially; precise per-record support remains the next integration risk. Retained report and reproduction bundle: evidence/relevance-followup.md. No production code changes or automatic adoption; original qualification evidence unchanged.

2026-09-17 Thought: operator requested a follow-up relevance-admission experiment. Run scratch-only comparisons of focused evidence, answer-support admission and agent validation; use previous holdout as development, freeze parameters before independent fresh labels are scored. Preserve the completed production non-adoption decision until new evidence and explicit integration review justify a change. No repository code or frozen evidence edits.

Final verification: all eight ACs and tasks complete. Canonical suite passed 9,115 tests (21 skips), receipt hash matches; full MCP documentation validation passed without errors or warnings. Six independent delivery lanes approved non-adoption; see [final verification](evidence/final-verification.md). The earlier Session Handoff below is retained as the readiness-bound snapshot; this progress entry supersedes its pending-work status. Wave remains open pending operator closure.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-16 | Observe: all four experimental designs fail at least one fixed adoption gate; preserve production ordering. AC-1 through AC-7 have frozen labels, measured comparisons, policy/fault controls, non-adoption and documented diagnostics. Reflect: ranking gains alone do not establish safe no-match behavior. Thought: validate the complete suite and independently review delivered evidence. | evidence/qualification-report.md; qualification-decision.json; implementation-checks.md. |
| 2026-09-16 | Readback: implement an evaluation-only memory candidate path, frozen RRF/score fusion controls and truthful qualification reports. Before: summary queries over a 12-record subset cannot qualify ranking. After: independent full-corpus queries measure public production and bounded candidates, including no-match and failures; production remains unchanged unless all adoption gates pass. AC-1 through AC-8 apply; normal docs/code/brief/advisory ranking and storage format stay outside scope. | Files: memory_eval.py and tests, bounded sqlite_vector_store helper, server evaluator descriptions, wave evidence and named docs. |
| 2026-09-16 | Observe: standard targeted council and six prepare lanes approved; QA froze corpus/24 holdout cases and public policy baseline passed 14/14. Thought: implement metrics and candidate retrieval independently, then freeze parameters and score once. | evidence/readiness-synthesis.md; evidence/prepare-lanes.md; evidence/qa-readiness.md; evidence/authority-decision.md. |
| 2026-09-16 | Thought: fix gates before tuning; run independent standard-depth primer and docs-contract seat under the local targeted review policy. QA independently owns frozen holdout labels. | evidence/readiness-contract.md; operator request to implement. |
| 2026-09-16 | Exploratory comparison completed; plan authored and awaiting readiness. No production ranking changes. | Wave evidence bundle and evaluation summary. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-16 | Compare plain RRF and score fusion through gated adoption. | Both are fast and strong on exploratory retrieval; neither is independently qualified. | Immediate RRF adoption leaves policy/no-match behavior unresolved; immediate score-fusion adoption overstates a one-result gain. |
| 2026-09-16 | Keep weighted RRF and lexical injection as bounded controls. | Equal RRF weights won development selection; injection did not improve held-out retrieval. | Broad parameter sweeps increase overfitting without demonstrated value. |
| 2026-09-16 | Separate memory evaluation from regular code/docs search. | Different relevance, graph and authority requirements need separate evidence. | Global defaults would extrapolate memory-only results. |
| 2026-09-16 | Do not select a universal cutoff or mandatory cross-encoder now. | Hard gates rejected useful broad queries; score scaling is corpus/model-dependent. | A fixed exploratory cutoff would trade recall away without qualification. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Same-author labels and repeated local queries overstate gains | Independent adjudication and untouched holdout; disclose sample size and paired counts. |
| Trust or recency promotes an irrelevant or obsolete instruction | Separate eligibility, relevance and authority; conflict/supersession tests and explicit policy review. |
| One relevant hit admits an unrelated tail | Measure per-record relevance and result counts; no query-level gate treated as per-record proof. |
| Memory filtering after limits loses candidates; duplicates consume budget | Eligible memory scope before limits and record-level coverage tests. |
| Min-max normalization gives irrelevant results high scores | Treat score as ranking only; independently validate uncertainty/abstention. |
| Candidate optimization affects normal docs/code search | Memory-owned path, public regression controls and no global ranking edits. |
| Native GPU or thresholds hide portability failures | CPU-first qualification, injected failures, platform evidence stated honestly. |

## Session Handoff

Operator authorized the separately qualified summary5 production integration. Renew readiness before source edits, retain prior artifacts, implement the frozen candidate, then run fresh per-record qualification and delivery review. No closure, commit or push is authorized.
