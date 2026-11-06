# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `22lwp full-betterleaks-offline-rules`
Title: Full Betterleaks Offline Rules

## Objective

Teams receive the full pinned Betterleaks offline rule inventory with qualified Python detection and bounded cost. Preserve local execution, explicit policy, redaction and classification history; no imported provider action or shipped executable helper is authorized.

## Changes

Change ID: `22o94-enh adopt-current-betterleaks-ruleset`
Change Status: `implemented`

## Participants

- Coordinator: delegated lifecycle coordinator; root owns implementation integration
- Write-owning roles: root integration implementer and explicitly assigned parser/tokenizer specialists after readiness; lifecycle coordinator owns plans and readiness records
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, performance-reviewer, docs-contract-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-11-06

## Wave Summary

Wave `22lwp` (Full Betterleaks Offline Rules) delivered one change: Adopt the current Betterleaks ruleset with verified local behavior. Notable adjustments during implementation: Adopt the current Betterleaks ruleset with verified local behavior: Created the follow-up after the operator requested the full newer ruleset. Planning only; no admission, readiness or added implementation.; Adopt the current Betterleaks ruleset with verified local behavior: The operator requested Prepare, review and implementation after closing/committing/pushing 22o92 and 22o93. Completed upstream construct census and temporary offline-helper feasibility work before selecting implementation scope.; Adopt the current Betterleaks ruleset with verified local behavior: Narrow scope amendment: add only test_tree_kill_routing.py to classify the new worker's exact bounded cleanup wait in the existing timed-call census. Requirements and ACs are unchanged. This permits an explicit justified leaf-process classification, not a wildcard exclusion or weaker census assertion.

Intent outcome: achieved within the measured scope. The complete pinned 474-rule Python offline inventory is qualified through 9,330 reference cases, independent near-misses, actual consumer policy/history controls, bounded worker failure probes and frozen synthetic cost. Runtime-directory exclusions work before content/hash reads with distribution-owned declarations and both-owner cache/history refresh. QA and Council independently confirm intent fit establishes. Final canonical qualification passed 12,485 tests across 221 modules with 12 expected skips; current receipt e73306cd71805a94dfdb36ebfc10ececa6be33d04a282f8e2979bc3b7f1c7ffc. Native Windows execution, actual downstream installation, field precision and field cost remain unestablished. See evidence/delivery-review-summary.json, relocation-review-summary.json and runtime-review-summary.json; no required AC is deferred.

**Changes delivered:**

- **Adopt the current Betterleaks ruleset with verified local behavior** (`22o94-enh adopt-current-betterleaks-ruleset`) — 6 ACs completed. Key decisions: Plan full offline adoption as a follow-up, with engine qualification before publication.; Keep external action blocks inactive.
## Watchpoints

- Watchpoint: no automatic partial adoption: unqualified required rules or unmet ordinary-workload budgets return to the operator.
- Parse, compile and evaluation run inside bounded Python worker ownership; no unbounded serial fallback or clean cache on incomplete work.
- Keep imported network/validation/revocation instructions inert and preserve scanner classification authority.
- Go/reference tooling is temporary research only; shipped runtime remains Python with no new dependency.
- Prior closed waves and unrelated public-documentation edits remain unchanged.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 22lwp-ca1-worker-reload-retention | do_now | no | completed | code-reviewer, architecture-reviewer, qa-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-06: Closure reconciliation: the operator explicitly directed closing 22lwp, then committing/pushing and building a local test package. All required lanes and Council remain current, all six ACs/tasks are complete, and no new delivered-scope lane is required. No intentionally unmet AC exists. The operator confirmed the remaining scanner observations as false positives; docs/scan-findings.json retains per-entry reasons, confirmer and date (284 false positives, zero unresolved). Existing matching green framework receipt e73306cd71805a94dfdb36ebfc10ececa6be33d04a282f8e2979bc3b7f1c7ffc is reused without a repeated suite.

2026-11-06: Retrospective and memory checkpoint: the non-obvious lessons are that detector semantics require consumer-level cache/history qualification, module eviction must release worker ownership, and runtime exclusions must precede content hashing while policy changes invalidate both cache owners. These are retained in maintained regression tests and the current architecture/build guidance; duplicating them as memory adds no distinct next action. memory_propose dry-run returned zero eligible candidates and created nothing; its four omissions lacked a current contained source target. No new memory was selected. Unique proof is retained under evidence/: full inventory/oracle and cost summaries, guard and lifetime mutants, historical manifests, downstream package probe and runtime-selection/history/currency review. Routine reviewer notes, raw green logs and disposable probes may be removed by canonical owned-work cleanup; their decisive observations are preserved in maintained tests, typed evidence and concise summaries. No other wave or unrelated document is cleanup scope.

2026-11-06: Final runtime-policy delivery: all seven actual affected lane approvals and Council delivery are recorded on readiness d5e41abe17220c1c704c. Root verified canonical exit 0: 12,485 tests / 221 modules / 12 expected skips / 746.812 seconds, receipt e73306cd71805a94dfdb36ebfc10ececa6be33d04a282f8e2979bc3b7f1c7ffc at 2026-11-06T19:57:41.052892+00:00. All 39 reviewed blobs stayed unchanged. QA and Council confirm intent fit establishes for all required ACs, including AC-6, and the wave Objective. Original full review and focused CA-1, relocation and runtime effects evidence remain separately attributed; grouped roles are correlated. Each reviewer confirmed the final factual qualification without another review cycle. All ACs/tasks are complete; the wave remains OPEN. Native Windows, actual downstream deployment, field precision and speedup remain unqualified; three scanner observations remain pending operator-owned disposition. No source, rule, exclusion or classification changed during final continuation.

2026-11-06: Intent outcome: the R8 / AC-6 outcome is supported by actual scanner consumers and independently confirmed by QA; final integrated qualification remains pending. Root passed 72 focused tests and nine assertion-failing mutants with zero errors. Independent QA passed 12 controls including both-owner unchanged-content history/currency replay and a pre-hash omission mutant; code/architecture passed two consumer controls; security/docs passed three controls and rejected a blanket-namespace mutant. Performance/release found no additional delivery or cost obligation for the unchanged engine/assets and existing packaged constants module. All 39 manifest blobs remained fixed through review. Four nonauthor contexts cover seven remits, with grouped roles explicitly correlated; earlier full-engine, CA-1, relocation and runtime readiness/primer evidence is retained. See evidence/runtime-review-summary.json and evidence/runtime-exclusion-mutants.json. The current candidate does not inherit the predecessor green receipt. No native Windows, field speedup, actual Waveforge installation or safety of excluded content is claimed.

2026-11-06 — Final delivery: all seven actual lane approvals and Council delivery are current after the unchanged relocated candidate passed 12,479 tests / 221 files / 12 expected skips / 718.427 s. Green receipt 01c05756dc2a0ab377eae98f63f7f1d6ded2421de0acde086d90f13013f515b2 was recorded at 2026-11-06T18:23:25.553563+00:00. Relocated manifest af79e3d24e8e725dc201969cef4f0531ca9a8aede90dd192fe97191b81d4fbfa is unchanged. QA and Council independently conclude intent fit establishes for all admitted Requirements/ACs and the wave Objective. The earlier red and pre-relocation results below remain historical; neither was relabelled. Actual review contexts, original and repair coverage, targeted relocation proof and limits are retained in the typed ledger and evidence summaries. Code/architecture share one context; performance/release share one; security and narrow relocation-docs effects share one while the original full docs specialist remains separately attributed. No native Windows, actual Waveforge installation, field precision or field cost claim. All edit gates are closed. Findings 22nx0-sec and 22nx1-sec retain independent false-positive advice pending operator confirmation; 22lh8-sec matches a public pinned asset digest and awaits classification/confirmation. No history/exclusion was changed. The wave remains OPEN, uncommitted and unbuilt.

2026-11-06: Delivery review executed all seven technical lanes, four distinct fixed Council seats and rotating docs-contract after a full-depth isolated primer. Code/architecture share one context; performance/release share one, with correlation disclosed. The sole elected source repair CA-1 is independently verified and terminal; source target a27f6c50d310eeef5912a198c9dd8381802e9c6f624ec849cc062a3272527070 differs only in worker/test. QA, security, docs and performance effects checks preserve the original evidence. Closing red-team found no new blocker. AC-1 through AC-5 have specific actual evidence; final approval task remains open for the canonical green receipt and actual final attestations. Two public-rule-ID scanner findings remain pending operator confirmation. Unique proof and limits are retained in evidence/delivery-review-summary.json; no closure, commit, package or release was performed.


2026-11-06: Intent outcome: partially established pending independent review and final canonical qualification. The candidate adopts all 474 pinned offline rules with explicit Python profile/legacy separation; full reference, independent near-miss, worker failure and actual 280-to-474 consumer controls support broader detection with preserved policy/history. Frozen synthetic cost is within admitted bounds. The first full suite was red on three integration obligations; their focused repairs are being verified, so no current green receipt or completed delivery is claimed. Native Windows execution, field precision and operator-time savings remain unestablished. QA owns the independent intent check against AC-1 through AC-5 and the wave Objective.


2026-11-06: Focused readiness refresh passed on review-policy-54c0b3ca97cf5b0a9d55 after adding only the exact test_tree_kill_routing.py target. All seven technical lanes and Council re-recorded approvals; no findings, no Requirements/AC/authority/budget changes. Four independent nonauthor contexts covered the seven lanes, with code/architecture and docs/performance/release correlation disclosed. Actual census and worker controls verify the one-count cleanup key and reject additional calls. The chair reused the prior full-depth primer/reality evidence; merits preceded explicit mapping, but inherited identity exposure prevents a pristine-blind claim. Canonical Prepare ready succeeded with no diagnostics or pending lanes. Root now owns the exact census row and copied-fixture dependency repairs; final delivery qualification remains pending.


2026-11-06: The 474-rule default is activated after engine/profile qualification. The same-line pending-history regression is repaired, and a separate optional-only suspicion was retracted after matching source/reference results. Shipped-candidate synthetic cost stays within the frozen limits; the plan records measurements and attribution. Remaining consumer controls and independent delivery review are not yet complete.

2026-11-06: Root activated the readied wave and opened the framework gate. Intermediate engine, expression, tokenizer and worker qualification is recorded in the change Progress Log, including the frozen-corpus cost arithmetic. These are implementation observations, not delivery approvals. A same-line pending-history regression remains under repair; the 280-rule default has not yet been replaced. Required independent delivery reviews await a stable candidate.

2026-11-06: Prepare wave succeeded in ready mode on review-policy-0e02ab82d0ff04cbd241, with no pending readiness lanes and no diagnostics. Full-depth Council PASS is unanimous; intent_fit establishes for change22o94 and the Objective. All seven technical approvals and the typed Council approval are current. Anonymous merits preceded identity restoration; closing red-team found no blocker. No repair, challenge round or extra approval gate was added. This is readiness, not delivered-engine qualification. Framework and seed gates remain closed; root owns activation and source implementation.

2026-11-06: Full-depth readiness technical review completed with no findings. Seven required lane approvals are current on review-policy-0e02ab82d0ff04cbd241. Four fixed contexts are distinct: architecture/code, QA, security and reality. Supplemental performance/release share one context; rotating docs-contract is separate. All formed nonauthor judgments; the rotating seat intentionally received the primer first. The independent chair is completing anonymous merits before identity restoration and final synthesis.

Decisive readiness evidence: actual loader/raw-scanner controls preserve overrides/disables but lose global expressions; both cache hash producers ignore asset changes while TOML changes invalidate them. Public synthetic scanning produces a redacted finding with action metadata and zero trapped external attempts; invalid containers refuse. Independent corpus recount verifies 9,330 full-config cases, 430 top-level plus 43 component IDs and all 37 component parents. Deliberate census omissions fail. The 474th rule, polymarket-address, is deliberately suppressed and unreferenced: retain full-config nonreporting and isolated detectability as separate qualified behavior. The 169 rules without upstream negative fixtures still need independent delivery controls.

The actual package collector includes the nine declared module/rules/asset paths and excludes transient/development controls; an omitted asset fails membership. Frozen cost corpus identity controls reject changed inputs. Baseline times are attributed research evidence, not repeated by reviewers: effective candidate median limits are 10 seconds normal and 48.94806125 seconds adversarial, with 120-second and 512-MiB parent-plus-owned-worker bounds. No future engine, native Windows, field precision or delivered cost is approved at readiness.

The rotating alternative is engine/profile/worker qualification before full rules activation, as two implementation checkpoints within this wave. Each fixed seat explicitly weighed that alternative and kept its verdict. A separate engine-only wave adds delay and another integration boundary without demonstrated benefit. Red-team closing found no incorrect disposition or new blocker. No plan repair or additional review loop was needed.

2026-11-06: Operator acknowledgment selects full pinned offline adoption implemented in Python, with no shipped Go helper, and reports no custom detection rules in current downstream projects. Explicit legacy inputs remain supported separately; that report does not authorize guessing incompatible profiles. The operator authorized prepare, review and implementation after closing/committing/pushing22o92 and22o93; those predecessors are closed and pushed as b33211eb.

2026-11-06: Readiness allocation uses the inherited capable model for cross-cutting parser, security and operational analysis. Actual runtime model/effort is unverified. The chair selects primer depth; isolated red-team primer precedes four distinct fixed contexts and a rotating alternative seat. Code/architecture may share a context; performance/release may share a context with that correlation disclosed. No source edit or future delivery evidence is claimed by readiness.

2026-11-06: Intent outcome: achieved within the measured scope. The complete pinned 474-rule Python offline inventory is qualified through 9,330 reference cases, independent near-misses, actual consumer policy/history controls, bounded worker failure probes and frozen synthetic cost. Runtime-directory exclusions work before content/hash reads with distribution-owned declarations and both-owner cache/history refresh. QA and Council independently confirm intent fit establishes. Final canonical qualification passed 12,485 tests across 221 modules with 12 expected skips; current receipt e73306cd71805a94dfdb36ebfc10ececa6be33d04a282f8e2979bc3b7f1c7ffc. Native Windows execution, actual downstream installation, field precision and field cost remain unestablished. See evidence/delivery-review-summary.json, relocation-review-summary.json and runtime-review-summary.json; no required AC is deferred.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 167 | 1,749,049 |
| implement | 147 | 1,643,794 |
| review | 366 | 3,045,211 |
| **Total** | **680** | **6,438,054** |

<!-- wave:context-efficiency-state {"generation":629,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":147,"content_source_credit":1931628,"derived_artifact_credit":2271,"direct_net":1643794,"estimated_tokens_saved":1643794,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7529,"response_debit":287020,"source_credit_count":85,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4444},"plan":{"calls":167,"content_source_credit":1581910,"derived_artifact_credit":2012,"direct_net":1749049,"estimated_tokens_saved":1749049,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8201,"response_debit":273581,"source_credit_count":77,"source_credit_drop_count":0,"structural_source_credit":429137,"workflow_prompt_credit":17772},"review":{"calls":366,"content_source_credit":3804000,"derived_artifact_credit":10053,"direct_net":3045211,"estimated_tokens_saved":3045211,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":48046,"response_debit":724574,"source_credit_count":159,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3778}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":680,"content_source_credit":7317538,"derived_artifact_credit":14336,"direct_net":6438054,"estimated_tokens_saved":6438054,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":63776,"response_debit":1285175,"source_credit_count":321,"source_credit_drop_count":0,"structural_source_credit":429137,"workflow_prompt_credit":25994},"wave_id":"22lwp full-betterleaks-offline-rules"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 46 | 0 | 16 | 27,147,048 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":16,"estimated_exploration_avoided":27147048,"surfaced_events":46} -->
<!-- wave:exploration-avoided end -->
