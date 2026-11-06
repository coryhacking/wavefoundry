# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22o93 scanner-rule-corrections`
Title: Scanner Rule Corrections

## Objective

Operators can customize scanner rules effectively and distinguish qualified Sourcegraph credential shapes from ordinary source-control evidence. Preserve local execution, meaningful credential coverage, triage authority and visible import limitations; no wholesale upstream refresh or network credential validation is authorized.

## Changes

Change ID: `22o91-bug scanner-rule-compatibility-and-sourcegraph-noise`
Change Status: `implemented`

## Participants

- Coordinator: root
- Write-owning roles: root owns scanner engine/rules and validator tests; delegated coordinator owns actual cache-consumer tests and scoped documentation.
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-11-06

## Wave Summary

Delivered change22o91: effective project scanner overrides, the operator-selected prefixed-only Sourcegraph detector and bounded import-compatibility reporting. All four ACs and three tasks are complete, with no deferrals or actionable findings. Required technical lanes and Council approve. The operator explicitly authorized closure, commit and push; canonical closure succeeded on 2026-11-06 using the current green 12,411-test receipt. The owned work area was removed after preserving decisive evidence and the final delivery manifest. Broader ruleset adoption remains separate plan22o94.

## Watchpoints

- Watchpoint: preserve the operator-selected prefixed-only Sourcegraph coverage. Explicitly document the loss of legacy unprefixed detection, even in named credential settings; no whole-ruleset refresh is implied.
- Keep imported validation, analysis and revocation blocks inert. Public rule data grants no network or credential authority.
- Current local triage counts and synthetic detection results are bounded evidence, not scanner-wide precision or absence-of-secrets claims.
- Preserve local filters, policy, confirmation history and the existing full-rescan invalidation route. Unsupported newer CEL semantics remain explicit.
- Preserve prior README/documentation edits and paused wave 22o92. The operator deleted :memory:.ses; do not restore it. The operator now authorizes closure, commit and push of both waves; package and release remain outside this request. Broader ruleset plan22o94 remains outside this wave.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-06: Closure retrospective and memory checkpoint. The operator explicitly authorized closing both waves, then committing and pushing them. The current combined receipt passes 12,411 tests across 218 files, with 12 expected skips. Decisive consumer controls, negative controls, reviewer conclusions and limitations remain in these checkpoints, the admitted plans, typed ledger and maintained tests. The final delivery manifest is retained in evidence/delivery-manifest.json; detailed work-area logs and reviewer notes are disposable.

The MCP memory proposal call refused because its loaded index producer is stale; in-process reload did not clear that boundary. The same public memory_propose_response handler in a fresh process completed read-only for this wave and proposed zero candidates, omitting source records without a current contained source target. No actual wave-linked memory candidate exists. No proposal was forced or promoted: existing canonical contracts and maintained regression tests carry the actionable lessons. No setup, live index rebuild or model operation ran.

Non-obvious lesson: accepting imported rule syntax is not semantic qualification. The bounded compatibility inspector reports unsupported constructs while runtime action metadata remains inert; maintained tests exercise both actual rescan producers and preserved dispositions. The selected prefixed-only Sourcegraph rule deliberately loses legacy bare-token detection. Full upstream adoption remains separate plan22o94.

2026-11-06: Final delivery Council PASS, unanimous, intent_fit establishes for the change and Objective. All six technical approvals are current and there are no findings or deferred ACs/tasks. The settled canonical suite exits 0: 12,411 tests / 218 files / 12 expected skips / 614.796 seconds; inputs_hash 7ad25d4f851118e37ffb85dc82560b9e25438bd328aa61ee0d55d43c1b964161, ran_at 2026-11-06T09:05:21.019783+00:00. Manifest204cb832c7d8d804fbe23f9d93e89791d7114d2c remains unchanged. Full write/MCP freeze held through process exit. Native-platform, field-time, global-precision and full upstream-semantic claims remain excluded. Gates are closed; wave stays open with operator closure signoff recorded.

2026-11-06: All required technical seats support delivery of the frozen candidate, conditional on the final canonical receipt. Security independently executes 14 tests, supplemental zero-attempt process/socket/shell traps and two detector mutants; source inspection covers serial and worker metadata handling. Docs-contract executes three compatibility controls and verifies the exact contract/provenance/coverage limits. Reality independently observes two actual-loader outcomes and verifies the target identities, attributing other seats' broader evidence. Four fixed contexts are distinct; code/architecture/performance share one context and rotating docs-contract is separate. The chair first weights anonymized merits, then receives identities; unanimous conditional PASS, no actionable finding, intent_fit establishes within synthetic/local evidence limits. A broad importer/engine refresh is less proportionate for this admitted repair and is staged separately in22o94. All source remains manifest204cb832c7d8d804fbe23f9d93e89791d7114d2c. Gates are closed; final qualification freezes all nonignored paths and MCP/lifecycle accounting through process exit.

2026-11-06: Intent outcome: achieved for the bounded objective, independently assessed by QA. Actual loading/scanning establishes effective project customization and distinguishes ordinary Sourcegraph commit evidence from the three selected prefixed credential forms. Both real cache producers consume changed rules without losing existing disposition history. Unsupported import semantics remain explicit and inert. This supports less unnecessary classification work; actual operator time saved and scanner-wide precision were not measured. Lost bare-hex credential detection remains an explicit coverage limit, not a claim that unmatched values are safe. Final canonical qualification remains pending.

2026-11-06: Code and architecture approve the frozen candidate, with supplemental performance approval from the same disclosed nonauthor context. Fourteen selected tests pass; an independent old-loader mutant fails one intended assertion with zero errors. Twenty-five actual scans at each size through 64 KiB short-line files show no actionable prefix/near-miss cost regression; the largest aggregate timings were 0.003337/0.034189 seconds, not an asymptotic guarantee. QA independently runs 39 maintained tests without skips, the old/current seven-case matrix, removed-detector positives and four unsupported-filter probes. All four ACs pass bounded verification and all 11 target identities remain unchanged. Security, docs-contract, reality and final qualification are pending.

2026-11-06: Candidate frozen at manifest204cb832c7d8d804fbe23f9d93e89791d7114d2c across 11 declared targets. Existing CEL tests stay in test_secrets_validators.py; the optional test_cel_filter.py was not added. Root's six focused scanner modules pass 250 tests in 29.362 seconds. ActualRulesChangeConsumers exercises both real cache producers, unchanged-file detection after a rule-only edit, preserved classification/confirmation history, redaction and old-fingerprint mutants. TestLoadMergedRuleset, SourcegraphPrefixedRuleTests and RulesetCompatibilityInspectionTests retain the detector/loader/import controls. Baseline729c069b2cacb5f698cffcbc9cc83fee5b158f56 old override, bare detector and blind compatibility controls each fail one assertion; removed detector fails 27 positives, all without errors. These maintained tests and recorded outcomes preserve proof beyond disposable logs.

2026-11-06: Independent chair selected full primer depth. Isolated red-team primer independently verified all 11 target identities, 31 consumer tests, seven exact format cases and four unsupported-filter probes with no demonstrated new defect. All five stances and three decisive questions cover actual override precedence, selected credential formats and bounded inert compatibility. The main challenge is avoiding a claim that within_checked_subset proves upstream semantics, cost or complete credential coverage. Required seats now assess that candidate independently; the final canonical suite is pending. No live credential/provider action ran.

2026-11-05: Prepare wave — focused readiness verdict PASS on review-policy-7548f109ea0a8d6cfaac. All six required lanes approved: code and architecture shared readiness_codearch_22o9; QA readiness_qa_22o9; security readiness_security_22o9; docs-contract readiness_docs_22o9; performance readiness_perfrelease_22o9. Distinct fixed reality readiness_reality_22o9 approved; independent readiness_chair_22o9 synthesized unanimous focused agreement, no remaining blocker, worst intent_fit establishes for the change and wave Objective. These are fresh focused turns by the initial reviewers, none authored the plan amendment. The original full primer and anonymous-merit-before-identity chronology remain evidence; this is focused completion of the operator-choice condition, not a fresh full Council or technical repair loop. Typed current approvals are in events.jsonl.

Decisive focused evidence: code/architecture and QA separately executed actual scan_file_raw with only the pinned candidate Sourcegraph rule in synthetic temporary files. Both observed modern sgp_<40 hex>, local sgp_local_<40 hex> and instance sgp_<16 hex>_<40 hex> positives each producing one hit. Bare commit prose, an explicit bare-hex sourcegraph_token assignment, a short malformed form and glued leading/trailing boundary cases each produced zero. QA also executed the old rule: hash prose and bare-token assignments each produced one hit, failing the newly selected negative oracle. Other detectors were excluded. Earlier actual same-ID loader and inert-action controls remain relevant; no scanner/loader source fix exists yet. These results qualify the selected narrow format contract, not global precision/recall or complete scanner lifecycle behavior.

Fixed seats and chair explicitly weighed the rotating loader-first split: it was useful while coverage was undecided, but a separate wave no longer resolves an open decision. Loader-first remains a sensible implementation order. Unsupported filters and extraction semantics still prohibit claiming a wholesale import. Detailed disposable notes live in the wave work area; decisive observations and conclusions are retained here and in typed authority. No full suite, production rescan/triage, native-platform, live credential or network qualification ran.

2026-11-05: Operator selected "let's follow the new betterleaks rules" after the comparison of the pinned Sourcegraph rules. Recorded prefixed-only coverage in owning R2 and exact AC-2 matrix, including the bare-hex credential-assignment negative. The existing initial technical review remains evidence; publish the amended receipt and run one focused choice/delta verification by required lanes and Council. The loader-first alternative is no longer needed to await this decision. No source, gate or implementation action is authorized by the choice.

2026-11-05: Initial full-depth readiness review completed on review-policy-bb9e49a3f590b9490d9c. An isolated full red-team primer preceded four distinct fixed contexts (architecture/code, QA, security, reality); rotating docs-contract and supplemental performance followed. Independent chair first weighed anonymous merits, then restored identities. All seats found the plan technically credible but conditional on the operator's unresolved legacy unprefixed-token choice. No unconditional readiness approval is recorded. These actual reviewer contexts also reviewed 22o92; no cross-wave or model-family independence is claimed.

Decisive observations: actual same-ID loader input retained the framework rule instead of the project's replacement, with no error. Synthetic raw scanner controls showed current/candidate results of 1/0 for Git-hash prose and explicit bare-hex Sourcegraph assignments, and 1/1 for qualified prefixed forms; local and instance-specific prefixed controls passed in coordinator probes. Malformed short controls returned 0/0. A trapped imported-action control made zero network calls. Current rule syntax checks do not prove scanner-wide coverage: 17 of 428 newer upstream filters failed the local parser. No live credentials or external validation ran. The chair's verdict is unanimous conditional/not ready, not an additional technical blocker.

The rotating alternative is to split the verified loader repair from the detector compatibility decision. It is credible but unselected; this wave keeps its admitted scope pending operator direction. The pending question offers context-limited legacy detection or modern prefixed forms only. The latter intentionally drops bare-hex coverage, even in named Sourcegraph credential settings. Explaining or recommending an option does not select it. Record the answer in the owning requirement and AC, republish readiness and obtain focused current-receipt review before readying.

2026-11-05: Operator admitted scanner change 22o91 into its own wave and requested readiness review for both 22o92 and 22o93. The compatibility question is pending; independent work may continue, but approval must not silently choose the detector boundary.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 43 | 4,161 |
| implement | 41 | 161,373 |
| review | 93 | 304,966 |
| **Total** | **177** | **470,500** |

<!-- wave:context-efficiency-state {"generation":166,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":41,"content_source_credit":186616,"derived_artifact_credit":0,"direct_net":161373,"estimated_tokens_saved":161373,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1411,"response_debit":59796,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":32546,"workflow_prompt_credit":3418},"plan":{"calls":43,"content_source_credit":86109,"derived_artifact_credit":1390,"direct_net":4161,"estimated_tokens_saved":4161,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8117,"response_debit":80729,"source_credit_count":29,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5508},"review":{"calls":93,"content_source_credit":531089,"derived_artifact_credit":1961,"direct_net":304966,"estimated_tokens_saved":304966,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5931,"response_debit":222153,"source_credit_count":55,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":177,"content_source_credit":803814,"derived_artifact_credit":3351,"direct_net":470500,"estimated_tokens_saved":470500,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15459,"response_debit":362678,"source_credit_count":103,"source_credit_drop_count":0,"structural_source_credit":32546,"workflow_prompt_credit":8926},"wave_id":"22o93 scanner-rule-corrections"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 4 | 3,106,320 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":3106320,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
