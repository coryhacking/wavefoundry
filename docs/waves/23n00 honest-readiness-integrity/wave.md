# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-16
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23n00 honest-readiness-integrity`
Title: Honest Readiness Integrity

## Objective

Specialist reviewers can record an honest readiness approval when no relevant surface in their lane is affected, using an explicit not-applicable known-bad check and scope rationale. Preserve delivery and council requirements, other integrity checks and historical evidence.

## Changes

Change ID: `23mzz-bug readiness-known-bad-not-applicable`
Change Status: `implemented`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer, technical-writer (confirm during Prepare)
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-11-16

## Wave Summary

Wave `23n00` (Honest Readiness Integrity) delivered one change: Allow an honest not-applicable control at specialist readiness.

Intent outcome: the implemented specialist readiness exception achieves the bounded behavior in 23mzz and this wave Objective in registered-path tests: an explicit known-bad null with scope rationale records, survives ledger reading and Prepare, and remains distinct from delivery approval. Negative tests and 16 assertion-killed mutants protect phase, identity, field and rationale boundaries. Default and renamed-profile focused checks pass. The canonical suite passed 12,847 tests across 250 files (12 skips), and all five specialist delivery lanes and council approved with no findings. This is local automated evidence, not a replay of the downstream incident or proof of reviewer honesty or Windows execution.

**Changes delivered:**

- **Allow an honest not-applicable control at specialist readiness** (`23mzz-bug readiness-known-bad-not-applicable`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: Allow explicit null only for unaffected specialist readiness checks; Put the rationale in the existing detection-method field.

## Watchpoints

- Watchpoint: do not treat a clean review, an unrun check or missing evidence as proof that a lane has no affected surface. Null must remain explicit and justified; no automatic waiver or historical ledger rewrite.

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
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-16: Closure retrospective and cleanup: the field-specific exception must be applied to both persisted null typing and executed-evidence checks; this is captured in maintained tests and seed 209, so no duplicate memory is needed. `memory_propose` returned no eligible candidates. Retain the 5.9 KB mutation probe/result under `evidence/` because they reproduce the guard-deletion claims; the receipt snapshot is disposable. No AC or task was deferred. Final scope introduces no additional review lanes.

2026-11-16: Final qualification: canonical suite passes 12,847 tests / 250 files / 12 skips; green receipt recorded. All five specialist delivery approvals and council-delivery remain current; no findings. Full docs validation passes. No close, commit or release performed.

### Delivery review — 2026-11-16

Full-depth delivery Council and all five required lanes approve the bounded implementation. Seats: isolated red-team primer and closing reconciliation; fixed architecture, security, QA and reality-checker; rotating docs-contract; additional required code reviewer. Initial delivery run and approvals are recorded in the typed ledger. No findings, repair round or challenge round; agreement unanimous, maximum severity none. Intent fit establishes: the registered test demonstrates explicit specialist readiness null, retained scope rationale, idempotent retry and Prepare consumption, while adjacent phase/identity/field controls remain restricted.

Independent seat evidence: architecture ran the registered fixture and killed an effective-phase mutant (2 assertion failures); security ran six tests and killed broad-null mutation (4); QA ran six tests and killed removal of specialist support (1); reality ran six tests and caught invented missing rationale (1); code ran six tests and caught removed rationale validation (1); docs ran schema/refusal plus registered tests and caught the old-schema mutation (1). All mutation outcomes were assertion failures, not test errors. Chair independently ran five boundary tests and caught a phase-ignoring mutant (2); primer caught phase/council-key broadening (4). Source/test hashes remained `5a2ffd27…` / `36cfb4ea…` throughout. Reproducers are the named methods in `test_readiness_known_bad.py`, with in-memory mutations only.

The anonymized merit pass found consistent evidence of the narrow exception, not evidence that a rationale is true. Role identities were reattached without changing authority. The primer was included in seat briefings, so no blind pre-primer read is claimed; shared host/model family and common fixtures limit independence. No Windows execution or downstream incident replay was performed.

| Recommendation | Verdict | Reason |
| --- | --- | --- |
| Keep explicit null plus existing method rationale | Accepted | Corrects the reported constraint without adding another lifecycle state |
| Introduce a typed applicability record | Deferred outside scope | Better structured querying, but extra schema/migration machinery and no authentication of truth; fixed seats and rotating seat agree |
| Finish the canonical frozen-suite receipt | Required completion follow-up | All 12,847 test workers passed, but concurrent review recording invalidated the aggregate receipt; AC-5 remains pending until the coordinator reruns after this review is frozen |

### Delivery Falsification Check

Working verdict PASS: the strongest counterargument is that an invented rationale can falsely claim unaffected scope. This does not change the verdict because the admitted contract explicitly validates presence/type, retains independent review of adequacy and never claims authenticated truth. Tested field, identity and phase restrictions prevent the demonstrated broader exception failures. Red-team closing found no concealed blocker in the empty finding set. Final canonical test receipt remains a completion condition, not a council waiver.

2026-11-16: Intent outcome: the implemented specialist readiness exception achieves the bounded behavior in 23mzz and this wave Objective in registered-path tests: an explicit known-bad null with scope rationale records, survives ledger reading and Prepare, and remains distinct from delivery approval. Negative tests and 16 assertion-killed mutants protect phase, identity, field and rationale boundaries. Default and renamed-profile focused checks pass. The first full run exposed only stale contract fixtures, now repaired and checked; settled full-suite rerun and independent delivery reviews remain pending. This is local automated evidence, not a replay of the downstream incident or proof of reviewer honesty or Windows execution.

### Prepare review — 2026-11-16

Readiness verdict: approved; intent fit establishes for change 23mzz and the wave Objective, conditional on the required implementation evidence. AC-1 proves honest recording, AC-2 limits the exception, AC-3 preserves durable meaning, AC-4 makes the route usable, and AC-5 protects existing behavior. The served-path regression outcomes remain inspectable after release. No implementation or downstream incident replay is claimed.

The chair selected full primer depth because this changes a lifecycle evidence boundary across writing, reading and readiness consumption. The isolated red-team primer ran first. Fixed seats architecture, security, QA and reality-checker then assessed the plan independently; docs-contract supplied the rotating alternative assessment, and code-reviewer ran the additional required lane. All required specialist approvals bind `review-policy-49a4d4a297ab75dca3ce`. Bounded work allocation: role-specific source/contract inspection and registered read-only approval previews; no suite or delivery probes. The existing model and host were used; model diversity was not established.

The primer identified two implementation hazards: the broad operator null flag could exempt all five checks, and stored `phase=delivery` differs from effective `approval_phase=readiness`. Seats confirmed these hazards are covered by Requirements 1–4 and AC-1–3. Architecture checked actor mismatch, a valid approval and the null baseline; security and code checked false rejection beside current-source validation, with code also checking a valid preview; QA checked null refusal and its otherwise identical valid preview; docs-contract checked false, true and null. Reality assessed feasibility from source without a separate dynamic probe. These are readiness controls, not execution of the proposed exception.

The first synthesis weighed anonymized seat conclusions before reattaching roles. Agreement was unanimous; highest finding severity none; no typed findings or repair round. Shared primer concerns count as one shared signal, not independent rediscovery. The primer was present in seat task context, so independent pre-primer exposure is not claimed; independent assessments and explicit primer effects were retained. Red-team closing reconciliation confirmed the empty finding set.

The strongest alternative was a typed no-surface record. All fixed seats weighed the rotating seat's assessment: it makes applicability structurally explicit but adds schema and lifecycle work while still relying on reviewer judgment. Explicit null plus the existing rationale field is sufficient for this bounded change; message-only repair would not solve the refusal.

Implementation notes: use a field-specific predicate rather than widening `allow_not_applicable`; preserve existing operator-finding evidence as well as operator approvals; exercise both the persisted null-type check and executed-evidence all-true check; absent specialist `approval_phase` remains delivery. These clarify existing requirements and add no scope.

### Falsification Check

Working verdict: the plan can establish honest specialist readiness without weakening delivery. The strongest contrary argument is that a nonempty rationale can be false. The plan explicitly limits validation to shape and assigns adequacy to independent review; it neither authenticates the assertion nor repairs historical dishonesty. That boundary does not defeat the intended outcome. The chair's registered dry-run control rejected `intent_fit=does_not` for council readiness and accepted the matching `establishes` preview.

Limits: one host and model family, correlated shared briefing, no implementation tests, historical-ledger replay or cross-platform execution. MCP reported changed setup inputs; current-source reads and registered previews succeeded, and setup was not run. User direction authorizes this policy correction and readiness review; it grants no implementation, closure or release authority here.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 114 | 1,681,613 |
| implement | 69 | 1,238,140 |
| review | 46 | 787,147 |
| **Total** | **229** | **3,706,900** |

<!-- wave:context-efficiency-state {"generation":154,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":69,"content_source_credit":1307626,"derived_artifact_credit":3814,"direct_net":1238140,"estimated_tokens_saved":1238140,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2331,"response_debit":74674,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3705},"plan":{"calls":114,"content_source_credit":1955753,"derived_artifact_credit":2884,"direct_net":1681613,"estimated_tokens_saved":1681613,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9463,"response_debit":273063,"source_credit_count":76,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5502},"review":{"calls":46,"content_source_credit":885174,"derived_artifact_credit":1860,"direct_net":787147,"estimated_tokens_saved":787147,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3832,"response_debit":99831,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":229,"content_source_credit":4148553,"derived_artifact_credit":8558,"direct_net":3706900,"estimated_tokens_saved":3706900,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15626,"response_debit":447568,"source_credit_count":148,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12983},"wave_id":"23n00 honest-readiness-integrity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 10 | 0 | 7 | 5,935,294 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":5935294,"surfaced_events":10} -->
<!-- wave:exploration-avoided end -->
