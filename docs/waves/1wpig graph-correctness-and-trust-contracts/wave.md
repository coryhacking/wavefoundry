# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-04
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wpig graph-correctness-and-trust-contracts`
Title: Graph Correctness And Trust Contracts

## Objective

Restore graph fidelity and consumer trust by preventing cross-domain phantom edges, applying report filters before truncation, and preserving per-edge confidence metadata in public call hierarchies.

## Changes

Change ID: `1wpai-bug graph-edge-resolution-guards`
Change Status: `implemented`

Change ID: `1wpaj-bug graph-query-contract-correctness`
Change Status: `implemented`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer, code-reviewer, qa-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer
- Product-owner admission review: operator-approved on 2026-08-30 by the request to plan and admit the audited graph correctness findings; behavior restores documented contracts.

Completed At: 2026-09-02

## Wave Summary

Wave `1wpig` (Graph Correctness And Trust Contracts) delivered two changes: Add Type and Provenance Guards to Graph Edge Resolution and Restore Graph Query Filtering and Edge-Trust Contracts. Notable adjustments during implementation: Add Type and Provenance Guards to Graph Edge Resolution: DELIVERED, and the two-sided census re-derived across a rebuild of BOTH sides per AC-5's re-derivation clause rather than trusting the planning literals. Pre-fix (all three guards reverted, real graph build on a scratch copy): 123 structural-node `calls` targets; 166 `reads_config` = 102 declared-positive + 64 false. Post-fix (live graph, builder version 46): 0 structural targets, 0 false, 134 declared-positive. The positive set GREW rather than merely surviving: removing the fixture copy from the config-target index left 13 previously ambiguous literals with a single candidate, so they bind for the first time. AC-5's fail-on-drop condition is satisfied, and the repair is recorded as NOT purely subtractive, which a census counting only false removals and true retentions cannot see. Each of the three exclusions now carries its own deletion check after review found the schema-lever fixture was suppressed by a different lever and its mutant survived.; Add Type and Provenance Guards to Graph Edge Resolution: OPERATOR DIRECTION: the mandated execution order is reordered. Graph production edits land FIRST, evidenced by fixtures and the two-sided live census; the evaluator scaffold and the A/B/C receipt chain follow. This supersedes Requirement 7 here and `1wpaj` Requirement 9's rule that no graph production edit may precede successful runs A and B. Consequence recorded rather than glossed: a pre-change baseline on the current production identity can no longer be captured in place, so the before-side receipt must later be reconstructed from a clean worktree at the predecessor commit, or the chain re-scoped to an after-only measurement. The graph fixes remain fully evidenced independently of the receipt chain.; Restore Graph Query Filtering and Edge-Trust Contracts: DELIVERED, with two contract families repaired during delivery review after they were found specified but unimplemented: collapsed betweenness now returns the documented unsupported result instead of serving base-topology centrality, and `communities` eligibility moved above its truncation, where it had reproduced this wave's own headline defect (a filtered `limit=1` returning `[]` while an eligible community sat one row below an ineligible one). Both now carry oracles: 8 new tests, and reverting both repairs on a scratch copy turns 9 of them red. AC-3's worst-case response measurement, against the highest in-degree project symbol at 239 incoming entries: the four trust fields add 46,936 bytes to the incoming list, 89.9% over the same list without them, in a 99,808-byte envelope. The environment identity gained an eleventh variable, `WAVEFOUNDRY_SPEC_CHUNKING`, after review found it missing; it is the second variable the indexer assigns during every build and it changes the chunk set, so omitting it left a false-clean comparison path open.

**Changes delivered:**

- **Add Type and Provenance Guards to Graph Edge Resolution** (`1wpai-bug graph-edge-resolution-guards`) — 7 ACs completed. Key decisions: Restrict resolution per relation using compatible target kinds and provenance.; Repair config attribution on the target side and keep loader provenance additive.
- **Restore Graph Query Filtering and Edge-Trust Contracts** (`1wpaj-bug graph-query-contract-correctness`) — 5 ACs completed. Key decisions: Filter the candidate universe before ranking truncation and preserve edge metadata in projection.; Persist the complete deterministic betweenness order beside the compatibility top-N view and bump the cluster builder version.
## Watchpoints

- Watchpoint: stricter resolution must preserve positive callable, constructor, and runtime-config edges; false-positive removal cannot be accepted by edge-count reduction alone.
- Watchpoint: unfiltered graph-report rankings must remain stable while filtered rankings refill correctly.
- Watchpoint: hierarchy metadata additions must remain schema-compatible and payload-bounded.
- Watchpoint: filtered betweenness refill requires a versioned complete persisted order; preserve the compatibility top-N view and measure compressed artifact/rebuild cost.
- Watchpoint: the closed `1seaw` standing gate identifies graph extraction/query modules as production retrieval code, but its evaluator does not yet bind cluster code/version or per-fixture regressions. Add/freeze that scaffold first, capture a fresh post-`1wpif` run A/B pair, then require exact-baseline run C with graph-carrier evidence and explicit controlled cross-generation results.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | do_now | no | completed | — |
| CODE-DEL-1 | do_now | no | completed | — |
| DOCS-DEL-1 | do_now | no | completed | — |
| QA-DEL-1 | do_now | no | completed | — |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Plan readiness may be reviewed independently, but implementation follows completion of `1wpif` so the required immediate-predecessor standing pair isolates graph-wave effects from content/retrieval-correctness changes.
- The wave remains planned/readied while `1wpif` owns the single OPEN slot; activation occurs only after `1wpif` closes and its final production/index identities are available.
- `1wpai` removes the phantom edge family and therefore changes fan rankings and community shape, so any `1wpaj` evidence captured against the live graph before the extraction repair is invalidated and SHALL be re-captured after the post-`1wpai` rebuild. Fixture-based matrix cells are unaffected.
- Within the wave, ordering is mandatory: evaluator scaffold → freeze/index successor evaluator → exclusive-create run A → run B against caller-declared A → `1wpai` extraction edits → `1wpaj` query/cluster edits → graph/cluster rebuild → run C against caller-declared B. No graph production edit may precede successful A/B.

## Current Assumptions

- JSON/YAML structural nodes remain useful graph content and will not be removed wholesale.
- `EXTRACTED` edges remain a supported fallback when no stronger attribution exists.
- Existing graph schema can carry the corrected edges and response metadata without a wholesale format rewrite.

## Outputs Produced or Expected

- Relation-compatible call/config edges with bounded before/after fidelity census.
- Correctly filled filtered graph reports.
- Call hierarchies exposing stable node and per-edge trust metadata.
- Frozen-corpus standing retrieval run A/B/C chain bound to graph/query/cluster production identity, builder versions, the exact predecessor receipt, and exercised graph-carrier evidence.
- Graph architecture updates and full/incremental regression evidence.

## Review Checkpoints

- **Plan review — 2026-08-30: COMPLETE.** Requirements, scope, and acceptance criteria were walked for extraction-time edge fidelity and query-time trust contracts. Resolved branches require relation-compatible code-origin call targets, provenance-backed config reads, a `GRAPH_BUILDER_VERSION` bump with unchanged-corpus re-extraction, pre-truncation filtering for every affected report view, and compact per-node/per-edge hierarchy metadata.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: fixing the extractor without a builder-version bump leaves cached graphs carrying the same phantom edges indefinitely; strongest-alternative: use a broad name-based suppression list, rejected in favor of versioned invalidation and a conservative relation-specific code-origin/provenance matrix)
- Readiness synthesis: READY. Architecture verdict: approved-with-notes, high confidence; keep unfiltered ranking stable, preserve positive callable/constructor/runtime-config controls, and keep hierarchy metadata payload-bounded.
- **Closed-wave evidence intake — 2026-08-31: PLAN AMENDED; RE-PREPARE REQUIRED.** Closed `1seaw` proved that graph production modules can alter `code_ask` citations. Fresh code/QA review then found the historical evaluator did not bind cluster identity, could mask a per-fixture regression, and could not by itself prove immediate-predecessor provenance. `1wpaj` now requires a successor evaluator scaffold followed by uniquely named post-`1wpif` run A/B and exact-baseline post-rebuild run C, while retaining the closed evaluator digest as provenance only. The 2026-08-30 readiness receipt predates this gate and is not current authority.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-31: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: a self-selected or replaced predecessor, escaped/aliased report path, aggregate-masked fixture regression, concurrent artifact publication, or unexercised graph carrier could make an internally consistent receipt green without proving the graph change safe; strongest-alternative: hold a run-wide publication lock, rejected in favor of a confined single-handle sequence driver with atomic exclusive writes and bounded around-call lock/token/artifact fences that fail closed without lock inversion)
- Readiness synthesis: APPROVED. Independent code and QA lanes approved the successor evaluator and exact A/B/C chain after repair; performance approved the bounded evaluator/rebuild sequences; red-team and security seats approved externally declared predecessor identity, confined/exclusive report I/O, per-fixture oracles, persisted builder/artifact evidence, publication-race mutants, and the fixed carrier-loss mutant. A supplemental architecture review approved the graph/cluster version sequence and rejected split sidecar authority. Implementation remains ordered after `1wpif` closure.
- Prepare: confirm target-kind compatibility rules, provenance boundary, and public response compatibility.
- Mid-wave: architecture/QA review of negative and adjacent positive edge fixtures.
- Delivery: replay `os.cpu_count`, schema/config, filtered fan-in, and hierarchy confidence probes through public tools.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-02: BLOCKED** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: security-reviewer; strongest-challenge: `1wpai` Requirement 3's negative-control list is a literal description of how every true `reads_config` edge in this repository is produced, so an implementer who satisfies it deletes 102 of the 166 live edges while AC-4's synthetic controls stay green and AC-5's false-positive-only census reports the recall collapse as a precision win; strongest-alternative: demote rather than delete, attaching a provenance class and letting consumers filter, rejected on code grounds because `_CONFIDENCE_RANK` and `_edge_confidence_weight` bucket an unrecognized class into the low tier and `GraphQueryIndex.report._ranked` counts edges without weighting confidence at all, so a new class would be absorbed rather than honored)

  Re-Prepare was triggered by review-policy receipt staleness: `1wpaj`'s Serialization Points bullet changed after the 2026-08-31 council, moving the policy input digest and lapsing that approval. All five seats returned changes-required independently. The wave stays `planned` and is not readied. No typed `wave-council-readiness` approval was recorded for this pass.

  **Blocking items requiring plan repair before re-Prepare:**

  1. **`1wpai` Requirement 3 relocates a working gate and states no covering mechanism.** The current `reads_config` gate is target-side (`_is_config_file_path`, `_config_literal_is_distinctive`, and the unique-match requirement in the finalize bind); the source side has no receiver provenance at all. Requirement 3 makes source-side loader provenance necessary while enumerating only `json.load`, `yaml.safe_load`, `tomllib.load`, and the Spring APIs. Every live true edge is produced by a generic `.get` on a receiver crossing at least one frame from a loader whose body is `json.loads` on a string, and 42 of them are read by test functions with no loader in the chain at all. Repair: keep the existing target-side gate as sufficient provenance, add schema-file, JSON Schema meta-vocabulary, and fixture-path exclusions as the precision levers, and make loader-tracing additive rather than necessary.
  2. **`1wpai` AC-5 cannot distinguish a precision gain from a recall collapse.** It counts false positives only, with no denominator, no recall term, and no live positive control. Repair: make it two-sided against the enumerable live true population, and fail on any unexplained drop.
  3. **`1wpai` Requirement 1 names no code-origin discriminator.** The reproduced phantom target has `kind` of `class`, which Requirement 1 explicitly admits, and node records carry no language or origin marker. `_is_json_config_node_id` already exists and already returns true for that node. Repair: name it as the guard.
  4. **`1wpaj` Requirement 9's fixed carrier probe fails today on an untouched tree.** Executed verbatim, `graph_related` returns three neighbours of the named seed and does not contain `isolated_stdout_fd`, and no citation carries `from_graph`. The named function does not reference that symbol; the only graph-path call site is `_ensure_graph_builder_current`. Because the probe gates an invocation the plan orders before any graph edit, the sequence cannot start. Repair: re-anchor on the function that actually calls it, or assert a `graph_query.py` citation whose excerpt contains the symbol and re-specify the `from_graph` clause against the real merge mechanism.
  5. **`1wpaj` Requirement 9's protected-report list resolves to nothing in this wave.** No report path appears anywhere under this wave's directory; the three are named in the sibling `1wpih` record. AC-8 mandates a protected-path mutant whose target set is therefore undefined. Repair: enumerate `docs/reports/retrieval-quality-baseline-run1.json`, `docs/reports/retrieval-quality-baseline.json`, and `docs/reports/retrieval-quality-post-1seas-vs-before.json` inline.
  6. **`1wpaj` Requirement 8 leaves graph-shaping environment variables outside receipt identity.** `RETRIEVAL_TOGGLE_ENVS` declares five names and `_environment_snapshot` captures env state only through them, while `BETWEENNESS_TOP_N`, `BETWEENNESS_EXACT_MAX_NODES`, `BETWEENNESS_CUTOFF_MAX_NODES`, `BETWEENNESS_CUTOFF`, `WAVEFOUNDRY_MAX_TS_PARSE_BYTES`, and `WAVEFOUNDRY_MAX_LINE_SCAN_BYTES` change centrality method, artifact shape, and which edges exist at all. None moves a module hash, so the production digest is blind to every one and the no-active-toggles clause would report clean. Repair: extend the disclosed and compared environment set with the graph extraction and centrality knobs.
  7. **`1wpaj` Requirement 9 opens a self-contamination path.** Confinement to `docs/reports` does not imply the `retrieval-quality-` filename prefix that the ignore rule is keyed on, and `.json` is an indexed extension. A failed attempt written under a post-verdict filename enters the retrieval corpus and pollutes the next invocation's own measurement; the existing exclusion assertion runs once at start, before that destination is chosen. Verified by executing the real ignore matcher against both name shapes. Repair: require the prefix in the confinement rule and re-assert exclusion against the actual destination immediately before the exclusive create.
  8. **`1wpaj` Requirement 7 re-arms a measurement the operator decided is advisory.** The `1wur7` close set latency enforcement to operator review for every comparison kind, on the recorded ground that contention cannot be told from a real regression on a shared machine, and the in-code note records quiet-machine swings above twenty percent. Requirement 7 specifies one attempt per sample and a tighter band than the evaluator's, with no jitter derivation, no contention flag, and no advisory routing, and AC-7 makes passing it required. Repair: route violations to operator review as `apply_baseline_comparison` does, or derive a jitter band from a repeated same-state baseline before enforcing.
  9. **`1wpaj` AC-2 and AC-7 do not define a countable or discriminating matrix.** The described cross resolves to between 147 and 176 cells depending on readings the plan does not settle. Measured on the live graph, the eight collapse combinations yield two distinct topologies, no node carries the generated tag, no module reaches the file-hub threshold, and the whole cross reduces to two distinct observations, so the pre-fix code passes nearly every cell. Repair: settle the cell count, require each cell to be constructed with at least one ineligible candidate ranked above the Nth eligible row, require a deletion check per cell, and mark structurally vacuous cells not-applicable with a stated reason instead of counting them as coverage.

  **Per-seat evidence.**

- **red-team [council-adversarial-primer] — 2026-09-02: findings recorded.** Dumped the live graph and split the 166 `reads_config` edges into 64 false and 102 true, traced the producing loader, and reproduced the filtered fan-in underfill and the seven-edge `cpu_count` phantom through the public tool. Raised the strongest challenge above plus the unnamed discriminator and the dangling report list. Confirmed as accurate: truncation genuinely precedes filtering, all three collapse transforms precede report computation, the centrality ranking is genuinely sliced to a bounded prefix, the hierarchy projection genuinely omits the four requested fields, the frozen corpus digest is correct when computed over the normalized corpus, and the cluster module is genuinely absent from evaluator production identity while the graph indexer is already bound. Withdrew one finding in place after identifying its own methodology error on the digest computation.
- **architecture-reviewer — 2026-09-02: changes-required, strong confidence.** Established that the extraction-time seam is correct and refuted the demote alternative on code grounds. Located the repair inside the existing gate design. Found no read-side cluster staleness gate, so the rebuild guarantee holds in this wave only because a co-occurring builder-version bump reaches the cluster path. Verified by live query that the communities hub is collapse-sensitive while the plan asserts collapse flags do not project that section. Confirmed the two builder-version bumps and the invalidation chain are sound, and that the hierarchy fields are an additive compatible extension. Noted that Requirements 8 and 9 gate `1wpai`'s work from inside `1wpaj`'s criteria list.
- **security-reviewer [rotating] — 2026-09-02: changes-required, strong confidence.** Re-derived the edge census independently and found every one of the 166 edges shares a single confidence class with no provenance field, making AC-4's trust promise vacuous for the relation this wave repairs. Raised the environment-identity gap and the self-contamination path, both verified by execution. Established that the around-call state token and end-of-run production re-hash already exist and already work, that every artifact-mutating path funnels through the durable build epoch, and that the fence as proposed spends roughly two minutes per invocation rehashing artifacts the cheap token already covers while omitting the two stores that serve the measured results. Credited the confinement and exclusive-creation work as a genuine narrowing of an existing over-broad write path, and flagged that exclusive creation can permanently poison a declared destination on a mid-write timeout.
- **qa-reviewer — 2026-09-02: changes-required, strong confidence.** Executed the precommitted carrier probe and found it red on an untouched tree with one structurally unsatisfiable clause. Ran all eight collapse tuples through the real transforms and measured the matrix down to two distinct observations. Found the latency contract reverts a recorded operator decision. Credited the per-fixture oracle as buildable today against existing report rows and the two headline defects as genuinely reproduced and currently red. Noted that both change documents trip this repository's own criterion-locality sensor, and that the undefined null semantics leave the masking channel the oracle exists to close unspecified.
- **reality-checker — 2026-09-02: changes-required, strong confidence.** Measured the real harm and found it larger than the primer stated: 115 phantom call edges rather than seven, whose dominant family fuses 149 production nodes with 81 evidence keys into a publicly ranked community, and a filtered fan-in that returns one project row for a requested ten. Established that the risk surface is materially unharmed, so that rationale claim is overstated, and that the largest community defect visible publicly is out of this wave's declared scope. Judged the evidence apparatus disproportionate to its own detector, which is one scored fixture and one unscored probe, and found that this wave funds a re-baseline the dependent wave will invalidate by its own written contract. Recommended moving the cluster-artifact and evaluator criteria to the sibling wave while keeping the extraction guard coupled to the filter fix, because landing the filter fix alone would promote a phantom into the top-ranked project symbols.

- **Operator decision recorded — 2026-09-02.** The council recommended narrowing this wave and moving the cluster-artifact ordering, evaluator scaffold, and measurement chain into `1wpih index-quality-evaluation-and-ranking`. The operator declined and chose to keep the wave whole and repair in place, preserving the intent that graph edits are gated by a hardened evaluator in the same wave. The operator also confirmed that latency comparisons stay advisory and route to operator review, preserving the decision recorded at the `1wur7` close. Both decisions are carried in `1wpaj`'s Decision Log.

- **Council verification round — 2026-09-02: repairs verified, second pass applied.** All five seats re-reviewed the repaired documents against the tree. Six to eight of the nine blocking items closed on measurement: the declared populations partition the live relation exactly, the named discriminator is exactly separating across every structural-node call target and no legitimate one, the criterion-locality repair was proven by falsification against the pre-repair text, and the null semantics were confirmed against the real report corpus. The seats then found defects in the repairs themselves, most of them introduced by the first pass: an unnamed language classifier reintroduced in the sentence written to remove one, an exclusion that is not recall-safe outside this repository, a link-publish that collides with the wave's own hard-link rejection, a temporary filename that reopens the contamination channel the sibling repair closed, an environment clause naming a class rather than its members, an escape hatch with no floor, a reference order that cannot reach two of the sections it governs, a jitter mandate that does not fit its own budget and contradicts its own decision log, and an obligation with no criterion behind it. A second repair pass addressed each. The seats disagreed on the re-anchored carrier probe: two executed it green reproducibly and one got red on different phrasings, so the exact query string is now pinned rather than the outcome asserted.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-02: PASS WITH NOTES** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the config-attribution rule as first written would have deleted the live true population while its synthetic controls stayed green and its one-sided census scored the loss as a precision win, which was repaired by keeping the existing target-side gate sufficient and making loader provenance additive; strongest-alternative: demote weak edges rather than delete them, rejected on code grounds because an unrecognized confidence class is bucketed into the low tier and the report ranking counts edges without weighting confidence, so the label would be absorbed rather than honored)

  Six repair passes were required after the initial BLOCKED verdict. Every pass was independently verified against the tree, and every pass but the last introduced at least one defect that a verification seat caught, including a publish primitive that collided with the wave's own hard-link rejection, an exclusion that was not recall-safe outside this repository, a reference order that could not reach two of the sections it governed, a falsification check that could not redden a third of its own cells, and a requirement to pin a probe string that did not itself contain one. The probe is now pinned verbatim and was executed green by three independent seats, matching field for field including neighbour order. All nine original blocking items are closed on measurement. Residual notes are recorded in the change documents and none blocks readiness.

- **docs-contract-reviewer [rotating] — 2026-09-02: changes-required at review, repaired and cleared.** The rotating seat rotated to this lane when repair moved the policy digest, and it found three blocking items four code-focused seats had walked past. The Guru obligation named the rendered surface while the canonical seed is the declared source of truth, is gated, and is covered by no parity detector for that prose, so an implementer would have left the framework source wrong and shipped a superseded parameter contract to every target repository. A payload obligation contradicted this document's own risk-table mitigation with neither branch reachable from a criterion. The environment-recording mechanism existed only as requirement prose, and the implementation an implementer would reach for first makes the wave's own required no-active-toggles clause permanently unsatisfiable, because the indexer sets one of the ten variables during every build. It also found nine documentary gaps: three documents carrying contracts this wave changes that neither change declared, two of them with no detector at all; a lint-bound builder-version claim the bump breaks; obligations with no criterion or task behind them; an undefined term whose two readings give opposite instructions; and the performance oracle having no place in the mandatory execution order. All three blocking items and every note are repaired, and declaring the seed and specification paths correctly recruited this lane as a required delivery lane.

- **Prepare-phase lane review — 2026-09-02.** The council seats are not the required delivery lanes, so the two lanes that had not reviewed this plan were run before the wave could open.

  **code-reviewer: approved-with-notes.** Verified all six named seams exist, are the right ones, and are singular, and re-checked eleven load-bearing code claims the documents rest on, every one of which reproduced. Found three placement ambiguities that would each have cost a repair round during implementation: the call-resolution guard belongs immediately before the single return of a resolver with ten acceptance branches; the ranking method truncates at three sites and takes no eligibility argument, so editing the shared helper alone fixes half the matrix; and the cluster payload reader has eight further production consumers, so a gate placed there would strand the community tools and redden nine existing fixtures. Its strongest note was a sequencing hazard: the four indexed documentation surfaces this wave rewrites sat between runs B and C, where a documentation ranking shift is indistinguishable from the graph regression run C exists to detect. It confirmed the mandated order has no circular dependency, because the evaluator module is not itself bound as production identity. All actionable notes are folded into the change documents. One of its notes rested on a stale premise about uncommitted predecessor edits, which were committed earlier the same day.

  **performance-reviewer: changes-required at review, repaired and cleared.** Measured rather than estimated. The complete persisted order adds about forty-four kilobytes compressed against a ceiling with roughly eight times that headroom, so the size gate is a runaway guard rather than a growth detector. Rebuild timeouts carry four to eight times headroom against measured stage costs. Both hot paths this wave touches are unmeasurable against work already in the same call. Its blocking finding was that the security seat's fence-cost observation had been recorded in this record but never carried into the requirement, which still mandated full hashing around every call: measured at roughly one hundred and thirty times the cost of a token check the evaluator already performs after every repetition, over an artifact set that omitted the two vector stores actually serving the measured results, injecting a hundred-megabyte page-cache read between repetitions whose warm floor sits well under the contention threshold, and exceeding the requirement's own report-size caps at the call ceiling it enforces. The requirement now specifies the token around each call and full digests at start and end only, extended to both vector stores, with the index-state digest recorded for provenance only because that store is write-ahead-logged. It also corrected a headroom justification that was wrong by about two orders of magnitude.

## Completion Criteria

- Every required AC in both admitted changes is `[x]` or operator-rationalized `[~]`.
- Named phantom edges are absent, positive controls remain, and filtered reports fill their limits.
- Full/incremental graph equivalence, framework tests, and docs validation pass.

## Handoff or Next-Wave Notes

- The corrected graph becomes the baseline for `1wpih` mixed-artifact fidelity evaluation and evidence-community isolation.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 391 | 6,804,346 |
| implement | 89 | 2,640,079 |
| review | 244 | 7,044,101 |
| **Total** | **724** | **16,488,526** |

<!-- wave:context-efficiency-state {"generation":563,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":89,"content_source_credit":2857710,"derived_artifact_credit":0,"direct_net":2640079,"estimated_tokens_saved":2640079,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2392,"response_debit":216838,"source_credit_count":68,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1599},"plan":{"calls":391,"content_source_credit":7265169,"derived_artifact_credit":6934,"direct_net":6804346,"estimated_tokens_saved":6804346,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":26830,"response_debit":912942,"source_credit_count":334,"source_credit_drop_count":0,"structural_source_credit":459749,"workflow_prompt_credit":12266},"review":{"calls":244,"content_source_credit":7694451,"derived_artifact_credit":974,"direct_net":7044101,"estimated_tokens_saved":7044101,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":31640,"response_debit":621573,"source_credit_count":288,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":724,"content_source_credit":17817330,"derived_artifact_credit":7908,"direct_net":16488526,"estimated_tokens_saved":16488526,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":60862,"response_debit":1751353,"source_credit_count":690,"source_credit_drop_count":0,"structural_source_credit":459749,"workflow_prompt_credit":15754},"wave_id":"1wpig graph-correctness-and-trust-contracts"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 2 | 1,578,674 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":1578674,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
