# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20d91 migration-repair-boundedness`
Title: Migration Repair Boundedness

## Objective

Bound migration cleanup, preview extraction and exact link repair. Scope and verification are owned by the admitted change; this wave coordinates one bounded follow-up repair.

## Changes

Change ID: `20d8y-bug migration-repair-boundedness`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (root coordinator)
- Write-owning roles: implementer (Python stdlib and regression controls; narrow cross-cutting builder lane)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-10-11

## Wave Summary

Wave `20d91` (Migration Repair Boundedness) delivered one change: Bound migration cleanup, preview extraction and exact link repair. Notable adjustments during implementation: Bound migration cleanup, preview extraction and exact link repair: Integration failures corrected within admitted source/test scope; no waiver or receipt claim.

**Changes delivered:**

- **Bound migration cleanup, preview extraction and exact link repair** (`20d8y-bug migration-repair-boundedness`) — 9 ACs completed. Key decisions: Request only material specialist review lanes.; Use source-present pre-move lifecycle link edits and existing registered-marker confirmation only.
## Watchpoints

- Follow-up: block activation until current typed readiness exists and the prior wave is paused; retry only within admitted scope.
- One write owner per source/test/doc target; reviewers read only. No commits, push, close, new evidence folder or permanent report.
- Preserve current source/protected surfaces and generic fixture boundaries; read the change for exclusions and known execution limits.
- Do not open this wave while any other wave occupies the OPEN slot. Pause completed implementation only through the coordinator's authorized lifecycle path.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 20d91-qualification-fixture-legacy-census | do_now | no | completed | qa-reviewer |
| 20d91-qualification-fixture-observation-clock | do_now | no | completed | qa-reviewer |
| 20d91-qualification-fixture-valid-archive | do_now | no | completed | qa-reviewer |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- Operator authorized preparation, review and implementation of this scope; operator authorized terminal closure in the current request.

## Dependencies

- Execution ordering: finish/pause existing open work before this wave activates; qualification-report-boundaries then migration-repair-boundedness then distribution-test-and-lint-seams. Readiness is independent and ready-only.
- No external semantic wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 21 | 43,710 |
| implement | 135 | 1,890,081 |
| review | 446 | 2,781,498 |
| **Total** | **602** | **4,715,289** |

<!-- wave:context-efficiency-state {"generation":637,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":135,"content_source_credit":2284677,"derived_artifact_credit":0,"direct_net":1890081,"estimated_tokens_saved":1890081,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4414,"response_debit":392407,"source_credit_count":65,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2225},"plan":{"calls":21,"content_source_credit":88139,"derived_artifact_credit":860,"direct_net":43710,"estimated_tokens_saved":43710,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13834,"response_debit":35260,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":446,"content_source_credit":4051636,"derived_artifact_credit":1846,"direct_net":2781498,"estimated_tokens_saved":2781498,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":45458,"response_debit":1229382,"source_credit_count":142,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":602,"content_source_credit":6424452,"derived_artifact_credit":2706,"direct_net":4715289,"estimated_tokens_saved":4715289,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":63706,"response_debit":1657049,"source_credit_count":225,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8886},"wave_id":"20d91 migration-repair-boundedness"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 70 | 0 | 32 | 31,754,017 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":32,"estimated_exploration_avoided":31754017,"surfaced_events":70} -->
<!-- wave:exploration-avoided end -->
## Product intent

Supported migration moves and exact current-document links should converge predictably, with truthful dry-run and partial-progress diagnostics. Existing project-authored prose and history remain protected. Context: `docs/ARCHITECTURE.md`, `docs/architecture/data-and-control-flow.md` and `docs/contributing/build-and-verification.md`.

## Agent Execution Graph

| Phase | Owner | Depends on | Output |
| --- | --- | --- | --- |
| Ready-only preparation | wave-coordinator | Complete admitted doc | Full docs validation, current independent specialist and Council readiness. |
| Reproduce and repair | implementer | Typed readiness and single-OPEN activation | Ordered regression, minimal repair, scoped docs, change-local evidence. |
| Delivery review | independent specialist lanes and council-chair | Current repair inputs | QA required-row reconciliation; read-only independent findings and Council synthesis. |
| Pause/handoff | wave-coordinator | Scoped verification and review | Durable pending-close state; no terminal closure. |

## Knowledge Transfer Plan

Read the admitted change's Requirements, Serialization Points, Decision Log and Progress Log before work. Report regression names, AC completion, blocking/invalidated assumptions and partial-progress diagnostics to the coordinator as they occur. Final evidence and limitations go in existing records; temporary captures remain outside the repository.

## Persona Review Plan

QA is mandatory for the bug. Material specialist lanes cover the scoped operator concerns; separate persona/product-owner/factor passes are not blanket requirements. Preserve any policy-derived lanes and Council. Additional factor roles (Category: factor) or personas require Prepare selection or a material finding.

## Wave Readiness Plan

Entry: complete change, admission, explicit AC priorities, protected file plan and independent required specialist/Council readiness; final `wf_prepare_wave(mode='ready')` succeeds. Coordinator owns decision rights and activation after the OPEN slot is free. No source edits occur during planning. Existing implementation authorization applies after the plan is surfaced; materially expanded scope returns to planning.

Exit: every admitted AC/task is reconciled with this change's evidence; required delivery lanes, QA scope reconciliation and Council are current; scoped docs validate and canonical qualification obligations are satisfied. Pause for operator-owned closure. A blocked prerequisite prevents its dependent work; retain the same change ID for retry unless materially different scope needs a new plan.

## File ownership and protected surfaces

The change's Serialization Points declare the exact intended targets. Implementer owns source/tests and named docs; all review/persona lanes are read-only. Seeds, generated platform/agent surfaces, root AGENTS.md, workflow policy, history, Git and test/qualification receipts are protected. Cross-wave shared modules serialize; coordinator resolves findings and expands scope only explicitly. No whole-upgrade work or extra artifacts are admitted.

Review routing note: requested lanes are scope-specific; Prepare's actual policy-derived requirements and current Council gate remain authoritative. Product-owner and other unrequested specialties are not independently mandatory absent policy selection or a justified material finding.

## Review checkpoints

### Prepare wave — readiness allocation

Primer depth: full. A fresh isolated red-team primer precedes artifact-first independent architecture, security, QA and reality seats; docs-contract supplies the rotating alternative. Separate code review covers each wave, and performance review applies only to migration. Each seat batches clearly separated wave assessments, with a finite five-to-eight-minute target and honest unrun limits; no whole-suite rerun is selected for readiness. Shared source paths stay frozen during their review. Scratch probes are local and disposable. Required lane selection follows the actual Prepare receipt; Council readiness remains required for every wave. Readiness establishes plan feasibility against current code, not future implementation success.


### Prepare wave — sealed readiness synthesis

Fixed architecture, security, QA and reality seats formed sealed artifact-first priors before the primer; docs-contract supplied the rotating alternative. Separate fresh code review covered this wave. Every fixed seat explicitly weighed the alternative and retained its own verdict. Anonymized merit synthesis preceded attributed typed approvals; final red-team closing held with an empty candidate universe. Repeated admitted baselines and primer observations count as one correlated signal, not votes or proof of future fixes. A rejected missing-integrity dry-run supplied the chair's protocol negative control. Chair workflow-history context was excluded from independent priors; a source-scoped replacement supplied code review after unrelated context exposure. Shared source facts were sealed before releasing the renderer hold.

Required code, QA, architecture, security, docs-contract and independent performance readiness approvals plus Council are recorded. Real cleanup, empty-candidate renderer, byte/mode-preserving lifecycle move and incoming-preview controls discriminate the admitted defects. Independent no-follow censuses agree and detect an omitted-site negative control; measured scripts and docs fit the finite proposed caps. Actual preview accepts both 1,999 and 2,001 small selected members, detecting the missing count bound without target writes.

The strongest challenge is cross-pair failure ordering: finish all relevant readable lifecycle edits at existing paths before any lifecycle source move, retain sources on planned-write failure, and copy current edited bytes/mode. Requirements 5–7 already govern this ordering and narrow retry authority. A durable transaction journal was rejected because it adds artifacts and recovery authority beyond the admitted truthful partial-progress model.

Falsification check: complete bounded scheduler, counters, aggregate/decompressed limits, mixed retry and native Windows behavior remain delivery-unexecuted. Current feasibility and finite headroom do not substitute for those tests.

### Review wave — independent delivery and full Council

Phase: delivery. Verdict: PASS WITH IN-SESSION FIXES. Primer depth: full; seat_agreement_aggregate: unanimous / low. Artifact-first requirements priors preceded outcomes and the isolated five-stance primer. Its three questions challenged failed-write source retention/retry, later-readable links versus registered manual-repair authority, and complete incoming preflight plus finite shared-walk limits.

Fixed architecture examined shared-plan and pre-extraction boundaries; the primer extended its later-readable/manual distinction. Its distinct hook control and renderer counters found no product issue. Fixed security examined raw ZIP names and selected-set limits; the primer extended retry authority. Real incoming preview and guard-removal controls found no product issue. Fixed QA examined failed-write source retention and exact retry bytes/modes; it originated the archive qualification finding and reconciled all nine required ACs. Separate fresh reviewers cleared all three repairs. Fixed reality examined truthful partial-progress guidance; the primer confirmed its concern, and renderer recovery evidence supports the admitted retry boundary. Rotating docs-contract advocated private temporary spooling of planned payloads near the caps. Every fixed seat explicitly weighed it and retained the finite in-memory plan: the memory gain is unmeasured, while disk ownership, cleanup and failure states add complexity without demonstrated need.

Content-first anonymized merit synthesis preceded attributed authority; role labels did not override required QA findings. Reused experiments count once. Code/docs-contract/performance shared one fresh context; clean replacement security/reality shared another, so those signals are correlated. A security draft exposed to implementation narration before its prior was excluded. An overbroad clock briefing was stopped before outcomes/probes and replaced with a clean requirements-only prior. Default host models supply no model-diversity claim.

| Recommendation | Disposition and executed resolution |
| --- | --- |
| Valid-control archive fixture | real / do_now / completed: 44 original index-handoff tests pass without skips after two distinct valid ZIP producers replace invalid placeholders; deliberate corruption remains. Original BadZipFile setup errors prove a qualification defect only. |
| Protected legacy-token fixture | real / do_now / completed: unchanged census and combined renderer pass two tests without errors/skips; table-derived producers preserve default bytes, newlines, modes and inventory. |
| Shared observation-time fixture | real / do_now / completed; pre-existing, introduced_or_worsened_by_wave=false: a realistic 20ms rounding crossing reproduces the original age-only mismatch. Both original real build cases pass under a read-scoped shared clock; removing only that binding fails their original freshness assertions. All original assertions, production clocks, fields and budgets remain. |
| Private payload spooling | Retain current plan; no measured benefit or within-cap failure. This alternative is neither a finding nor a mandatory deferral. |
| Observable transition verification | Retain existing success, failure/retry, skipped-authority and aggregate-refusal cells for targeted diagnosis; no additional artifact or sweep. |

Typed repair_start preceded each edit, and independent QA cleared every required head. No finding was waived, deferred or relabeled not_issue. Final cycle-2 clearance atomically derived the convergence checkpoint; all three heads have no unresolved lanes. All nine ACs and five tasks are complete, with no [~] rows.

Genuine final qualification ran `python3 .wavefoundry/framework/scripts/run_tests.py` against the matching frozen tree: exit 0, 12,321 tests across 185 files, 12 aggregate skips, 769.255 seconds. The actual green receipt was transferred byte-identically to `.wavefoundry/framework/test-cache.json`; its inputs_hash matches current framework `78b932974d651666233577f7a80a8baefda3bc680ea11871af91117658df2c94`, ran_at 2026-10-11T10:18:14.495813+00:00. Twelve scoped file identities remain frozen. Earlier red runs did not qualify; no timing budget or product-clock change was used to obtain green. Aggregate skips do not establish skip-identity parity.

Isolated red closing held the repaired dispositions and primer rebuttal, then reconciled the pre-existing clock finding without a new candidate or authority contradiction. Closing used sealed observations without another suite sweep. Six lanes and Council support delivery approval; typed publication follows the coordinator's current full documentation boundary. Review Evidence remains authoritative; operator signoff remains pending.

Falsification: focused states can pass while complete upgrade integration fails. The genuine whole result establishes repository qualification; the actual post-extraction renderer control on a populated fixture is narrower than extraction and rendering in one invocation. Public failure/retry, complete incoming preflight and pre-extraction hook controls, with faithful ordering, metadata/member-guard and hook-removal mutants, substantiate the admitted boundaries without setup/import errors as product discriminators. No survivor required a broader sweep. Registered authority supports its declared cases; later unconfirmed links remain manual work.

Limits: finite counters establish bounded work, not speedup or peak-memory measurements. Native Windows/reparse execution, arbitrary same-user atomicity, universal transaction/convergence and end-to-end extraction qualification are unclaimed. Root owns final documentation validation and authorized pause; operator signoff and closure remain pending.
