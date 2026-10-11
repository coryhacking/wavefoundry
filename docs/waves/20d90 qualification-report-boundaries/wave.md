# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20d90 qualification-report-boundaries`
Title: Qualification Report Boundaries

## Objective

Qualification report refusal and publication boundaries. Scope and verification are owned by the admitted change; this wave coordinates one bounded follow-up repair.

## Changes

Change ID: `20cyo-bug qualification-report-boundaries`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (root coordinator)
- Write-owning roles: implementer (Python stdlib and regression controls; narrow cross-cutting builder lane)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-11

## Wave Summary

Wave `20d90` (Qualification Report Boundaries) delivered one change: Qualification report refusal and publication boundaries.

**Changes delivered:**

- **Qualification report refusal and publication boundaries** (`20cyo-bug qualification-report-boundaries`) — 5 ACs completed. Key decisions: Request only material specialist review lanes.; Required divergent pre-plan completed.
## Watchpoints

- Follow-up: block activation until current typed readiness exists and the prior wave is paused; retry only within admitted scope.
- One write owner per source/test/doc target; reviewers read only. No commits, push, close, new evidence folder or permanent report.
- Preserve current source/protected surfaces and generic fixture boundaries; read the change for exclusions and known execution limits.
- Do not open this wave while any other wave occupies the OPEN slot. Pause completed implementation only through the coordinator's authorized lifecycle path.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 47 | 470,359 |
| implement | 110 | 1,354,076 |
| review | 123 | 0 |
| **Total** | **280** | **1,824,435** |

<!-- wave:context-efficiency-state {"generation":268,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":110,"content_source_credit":939625,"derived_artifact_credit":0,"direct_net":1354076,"estimated_tokens_saved":1354076,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3721,"response_debit":245715,"source_credit_count":70,"source_credit_drop_count":0,"structural_source_credit":661100,"workflow_prompt_credit":2787},"plan":{"calls":47,"content_source_credit":582208,"derived_artifact_credit":808,"direct_net":470359,"estimated_tokens_saved":470359,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12040,"response_debit":104422,"source_credit_count":31,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":123,"content_source_credit":414267,"derived_artifact_credit":669,"direct_net":-232275,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13107,"response_debit":636960,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":280,"content_source_credit":1936100,"derived_artifact_credit":1477,"direct_net":1592160,"estimated_tokens_saved":1824435,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28868,"response_debit":987097,"source_credit_count":157,"source_credit_drop_count":0,"structural_source_credit":661100,"workflow_prompt_credit":9448},"wave_id":"20d90 qualification-report-boundaries"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 24 | 0 | 17 | 14,008,736 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":17,"estimated_exploration_avoided":14008736,"surfaced_events":24} -->
<!-- wave:exploration-avoided end -->
## Product intent

Optional release diagnostics should refuse malformed observations and unsafe targets clearly while preserving existing canonical test-receipt authority. Governing context: `docs/contributing/build-and-verification.md`, Optional compact qualification reports.

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

Required code, QA, architecture, security and docs-contract readiness approvals plus Council are recorded. Owned/unowned report controls, actual nonce correlation, decoder failures and late-link substitutions discriminate the current repair boundary beside legitimate cases. The strongest challenge is judged owned-final identity and lexical parent/final validation on every successful branch, including unchanged bytes and mode-only work; Requirements 2 and AC-2/AC-3 already govern these cases. Exclusive-new report names were rejected because they break required owned reuse and do not authenticate workers. Optional diagnostics remain separate from canonical receipt authority.

Falsification check: future publication transitions remain unexecuted; the explicit branch-wide contract and disclosed final check-to-commit platform limits make the plan feasible without claiming delivery success. Native Windows and the complete repaired interleaving matrix remain unrun.

### Delivery review — frozen report boundary

Primer depth: full, because capped decoding, report ownership/path publication and diagnostic authority are trust boundaries. An isolated red-team primer applied adversarial, constructive, simplicity, first-principles and analogical stances. Fresh architecture, security, QA and reality seats formed artifact-first priors before receiving it; code review was separate, architecture and docs-contract supplied distinct required-lane judgments, and the rotating fifth seat sought the strongest alternative. The chair retained workflow status, which supplied no independent seat authority. One security context accidentally saw implementation narration and was discarded; a fresh replacement supplied the actual security approval.

The primer challenged any claim that checkpoint refusal excludes every later same-user rename. Each fixed seat distinguished detected substitutions from the accepted final check-to-replace interval, verified generic safe-link compatibility, and retained diagnostic nonce authority. Source judgments agreed, with no findings. Anonymized merit assessment preceded attributed synthesis; repeated controls count as one correlated semantic signal. Required lanes retain their own authority. The empty `initial_delivery` run seals zero candidates; red-team closing held that universe with no waiver or new finding. Source agreement is unanimous, maximum severity none; overall delivery still requires the coordinator's canonical proof, full docs gate and actual QA/Council events, rather than conditional approval prose.

Independent code review ran 33 report tests in 22.085s with zero skips and killed six focused mutants covering decoder normalization, strict commit, final/held/initial-parent identity and byte-change return semantics. Architecture/docs ran 14 boundary/nonce controls and the 33-test report file with zero skips, killed six targeted guard mutants, and observed the documented moved-directory publication interval and fallback moved-temporary limit. Fresh security ran seven public probe cells and five selected tests without skips, including faithful decoder and final-owned-inode link controls. Reality ran six selected tests in 2.169s without skips plus independent generic-link and fix-absent decoder probes. QA ran 33 tests in 33.632s without skips and eight independent preservation/compatibility/decoder/nonce probe families; three already-completed whole-file mutant runs departed from the targeted-first rule and produced 2/24/13 intended failures, and one directly targeted initial-parent mutant failed. That deviation is disclosed; no duplicate broad sweep followed. All fourteen added tests ran without skips. An isolated follow-symlink mutant survived because another `lstat` guard retained protection; targeted plus whole-file replay established the redundancy, and faithful combined policy removal failed the same-owned-inode link test.

Reproduce the report baseline with `env -u PYTHONPYCACHEPREFIX PYTHONDONTWRITEBYTECODE=1 WAVEFOUNDRY_DISABLE_BYTECODE_CACHE=1 python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_qualification_report.py`. Durable boundary oracles are `ReportBoundaryTests`, `ProtocolOwnershipTests.test_worker_nonce_is_visible_to_executed_test_code`, and the ordinary-run/profile receipt-preservation cases in `QualificationCLITests`; typed approvals carry the lane-specific mutation mapping. Scratch captures remain outside the repository. Independent references were the admitted ACs and byte/mode/inode preservation invariants, rather than implementation narration. An early scratch lexical-root alias refusal was excluded; the corrected resolved-root fixture reached publication.

The rotating alternative was immutable, exclusively created per-run reports: simpler replacement authorization and preserved observation history, but changed required owned replacement/stable-path cache reuse, added discovery/retention work and retained the parent rename interval. Every fixed seat explicitly weighed it and retained its judgment. A dedicated strict publisher would improve local API clarity but duplicate publication, modes and cleanup without strengthening the admitted guarantee. Neither justified scope expansion. No new long-run evidence artifact or memory candidate was warranted.

Frozen Git objects, rechecked by the lanes and chair:

| Reviewed path | Git object |
| --- | --- |
| `.wavefoundry/framework/scripts/qualification_report.py` | `2eb7bcf4bb900e4baee3773947d5fcbe81ae1e06` |
| `.wavefoundry/framework/scripts/contained_files.py` | `d64c85074ffea9abae4e0d4006c60b9fac1b629f` |
| `.wavefoundry/framework/scripts/qualification_worker.py` | `1406871bceb65320406f61c293cd74f9779ff453` |
| `.wavefoundry/framework/scripts/tests/test_qualification_report.py` | `57477d250d6c47856fb59be88b53b3538d67893f` |
| `docs/contributing/build-and-verification.md` | `7aeed69b7b84d0bb7a525c6d36d040bad1e61ed6` |
| `docs/architecture/testing-architecture.md` | `dd09786b5f879c0b2fc4ef2252d1953269f752b9` |
| `docs/architecture/cross-cutting-concerns.md` | `887b250821de4057fa1c85d4faf59114316c800a` |

### Falsification Check

The working source verdict is approval within admitted limits. The strongest contrary argument is that a parent rename after final validation can still redirect descriptor publication into the moved directory, while path fallback can lose cleanup access to a moved temporary. Independent probes observed those outcomes and the three guidance surfaces state them; they do not disprove detected precommit substitution refusal. Native Windows, universal race exclusion and independent attestation against same-process test code remain unqualified. Canonical qualification and current final docs validation are coordinator-owned; their actual results and final typed authority, not this source checkpoint, establish completion.
