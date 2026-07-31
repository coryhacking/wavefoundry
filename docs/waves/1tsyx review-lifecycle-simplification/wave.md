# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-31
review-evidence-source: events.jsonl

wave-id: `1tsyx review-lifecycle-simplification`
Title: Review Lifecycle Simplification

## Objective

Establish the pre-implementation claim ONCE, in Prepare, and close the four enforcement defects that
the duplicated review pass was masking. Removing a review pass is only a simplification if the gates
it shadowed actually hold; this wave does both halves together, and defers the broader review-policy
and delivery-evaluator restructuring to a separate change.

## Changes

Change ID: `1tr85-enh single-pass-review-lifecycle`
Change Status: `completed`

Completed At: 2026-07-28

## Wave Summary

Wave `1tsyx` (Review Lifecycle Simplification) delivered one change: Single-Pass Review Lifecycle. Notable adjustments during implementation: Single-Pass Review Lifecycle: Cycle 4 scope correction supersedes the two prose-migration attempts below. The original contract required seed 160's retired-gate backfill and success criterion to be removed; it did not require an agent-interpreted migration of every previously installed target prompt. The carrier matrix and its narrower duplicated validation were therefore withdrawn. The repository-wide executable census remains the current-tree control, with the previously vacuous backticked `prepare-council` literal corrected and additional rich-carrier phrases pinned individually. Complete downstream replacement and its production validation move to `1tsbu` as one shared mechanism.; Single-Pass Review Lifecycle: Delivery repair cycle 3 follow-up closed the two uncleared QA objections and the verifier's three mechanical notes. Legacy malformed prose now positively asserts `prepare_council_verdict_invalid` through both Prepare-create and Implement; AC-7 now builds three real typed waves through canonical wave/event producers and reports each state inside its own `subTest`; the redundant current-signoff disjunct is removed. Requirement 6 and the AC-6 rationale now describe the total audit honestly as defense in depth because the public append boundary already rejected anchorless reverifications. Seed 160 now names both retired headings literally and checks their post-upgrade absence; the residue census permits only those two count-bounded removal/validation references.; Single-Pass Review Lifecycle: Delivery repair cycle 3 accepted all eight second-review findings. Added real-authority AC-7 coverage, positive legacy Prepare/Implement pins, and the missing Review-side `initial_delivery` pin; corrected AC-6 polarity claims. Reverted the isolated readiness-rerun doctrine rewrite, reconciled three live reviewer-loop prompts, added upgrade removal guidance for previously installed gate sections, corrected AGENTS.md, and documented declared-wave seat alignment as an intentional legacy-only boundary whose typed successor is deferred to `1tsbu`.

**Changes delivered:**

- **Single-Pass Review Lifecycle** (`1tr85-enh single-pass-review-lifecycle`) — 10 ACs completed. Key decisions: Supersede the attempted prose migration bridge: `1tsyx` removes seed 160's backfill/verification claims and does not promise to rewrite already-installed downstream carriers; `1tsbu` owns one production reconciler whose vocabulary and scope are shared with its tests.; Complete `1tsyx` with a carrier-by-carrier prose migration matrix and exact-section/count validation; put a mechanical, idempotent lifecycle-section reconciler in `1tsbu`.
## Watchpoints

- Watchpoint: this is a simplification wave, not a relaxation wave: credible external, credential,
  concurrency, corruption/interruption, migration, destructive, and cross-ownership risks retain
  full adversarial treatment.
- Watchpoint: Prepare must remain a substantive fresh independent critique of the proposed design,
  not a document-completeness checklist or a self-review by the plan author.
- Watchpoint (cleared 2026-07-27): wave `1to78 preship-events-authority-hardening` owned overlapping
  lifecycle/evidence files and blocked this wave from opening. It is now CLOSED, so the operational
  dependency is satisfied and no wave holds those surfaces. Follow-up FU4 from that wave (the
  content-driven indexer predicate in `review_evidence.py`) also landed, so re-read that file rather
  than the 1to78 wave record for its current shape.
- Watchpoint (cleared 2026-07-28): every changed behavior has a POSITIVE failure obligation with a red-first
  proof; already-working gates use green-on-arrival regression pins. An AC shaped as a prohibition or
  an equivalence is satisfied by deleting the behavior it asserts about, which is exactly what this
  wave does; that shape is what blocked the previous scope at readiness.
- Watchpoint: the four masked enforcement defects are required scope, not follow-ups. Removing the
  duplicated pass while leaving them open converts this wave from a simplification into a relaxation.
- Watchpoint: closed ledgers remain readable history. This wave retires NO run kind and adds no
  read/write compatibility layer; 41 closed ledgers carry `repair_start` and `convergence_checkpoint`
  records that docs-lint validates corpus-wide.
- Watchpoint: no test is deleted unless it first FAILS against the new code. A test that still passes
  unchanged is pinning a surviving invariant, not retired ceremony.
- Follow-up: deferred scope is recorded at
  `docs/plans/1tsbu-enh review-policy-and-delivery-evaluator.md` and must not be pulled back in.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ac4a-ac6-and-ac7-coverage-claims-overstated | do_now | no | completed | wave-council-delivery |
| ac7-stale-readiness-fix-is-mock-shadowed | do_now | no | completed | wave-council-delivery |
| agents-md-still-documents-retired-prepare-contract | do_now | no | completed | wave-council-delivery |
| council-seat-alignment-degated-on-declared-waves-undocumented | do_now | no | completed | wave-council-delivery |
| declared-prepare-still-gates-on-prose-verdict | do_now | no | completed | wave-council-delivery |
| disabled-policy-activation-bypasses-readiness | do_now | no | completed | wave-council-delivery |
| legacy-prose-activation-branches-unpinned | do_now | no | completed | wave-council-delivery |
| narrative-declaration-token-bypasses-legacy-prepare-lint | do_now | no | completed | wave-council-delivery |
| populated-roster-enforcement-mislabeled-red-first | do_now | no | completed | wave-council-readiness |
| projection-scope-contradicts-deferral | do_now | no | completed | wave-council-readiness |
| readiness-rerun-doctrine-changed-in-one-carrier-only | do_now | no | completed | wave-council-delivery |
| retired-ladder-route-survives-in-live-agent-prompts | do_now | no | completed | wave-council-delivery |
| roster-extractor-divergence-claim-is-false | do_now | no | completed | wave-council-readiness |
| routine-review-and-prose-gate-carriers-escape-census | do_now | no | completed | wave-council-delivery |
| upgrade-removal-names-wrong-heading-and-validates-clean | do_now | no | completed | wave-council-delivery |
| upgrade-retires-gate-without-removing-installed-carriers | do_now | no | completed | wave-council-delivery |
| wave-record-pulls-deferred-policy-back-into-execution | do_now | no | completed | wave-council-readiness |

*Machine review evidence — 178 records; 53 runs; 17 findings; current: do_now 17, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Operational dependency (satisfied 2026-07-27): overlapping work from wave `1to78` is closed and
  landed as commit `3f59e379`, so no wave holds the shared lifecycle/evidence files.
- Coordination dependency: wave `1tmtx` owns test-runner performance; this wave does not change test
  cadence and must not absorb runner-acceleration scope.

## Participants

- Coordinator: `wave-coordinator`
- Write-owning roles: `implementer`, `docs-contract-reviewer`
- Independent review roles: selected under the current workflow from `code-reviewer`, `qa-reviewer`,
  `architecture-reviewer`, `security-reviewer`, `performance-reviewer`, and
  `docs-contract-reviewer` according to the affected surfaces and watchpoints. The new policy matrix
  remains deferred to `1tsbu`.

## Current Assumptions

- Review quality is valuable; repeated review of an unchanged claim is the defect.
- `events.jsonl` remains the sole machine-readable authority and supports non-Git repositories.
- Fresh installs and upgrades should converge to one current workflow without runtime fallback to
  the retired workflow.

## Outputs Produced

- One pre-implementation review, owned by Prepare, with activation reading typed readiness evidence.
- An executable carrier census matching prose and token forms, covering seeds, install templates,
  rendered prompts, and platform surfaces.
- A total independence audit, an explicit non-blocking advisory when the required-lane roster is
  empty, enforced populated rosters, and a stale-readiness approval that blocks at close.
- Regenerated carriers with the dead review-policy flag removed and the misdescribing docs corrected.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-28: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer, all fresh independent contexts; rotating-seat: docs-contract-reviewer; five seats returned CHANGES REQUESTED on the original sixteen-requirement scope, unanimous, driving a re-scope to eight requirements with the policy and evaluator work deferred to a recorded plan; two reverification rounds by a further fresh seat, the first NOT READY and the second READY on two conditions now settled; the red-team seat then returned CHANGES REQUESTED on the re-scope and its four blocking findings were repaired in-phase; strongest-challenge: the acceptance criteria were shaped as prohibitions and equivalences, every one of which a simplification wave satisfies by deleting the behavior asserted about, so the wave could have completed fully green with materially less enforcement than it began with; this was proven twice to be non-hypothetical, once when a deletion-equivalent criterion was reintroduced under positive phrasing and again when the template-roster decision contradicted the acceptance criterion it was meant to settle, leaving the cheapest green as a repository-wide enforcement increase; strongest-alternative: scope to the genuinely duplicated pre-implementation pass plus the four enforcement defects that pass was masking, restate every criterion as a positive failure obligation, and name the honest deliverable as ending the SILENT vacuity of the lane gate rather than ending the vacuity, adopted in full)
- Readiness detail: the council refuted part of the original cost case against code, notably that no
  seed mandates a full-suite run at any lifecycle boundary and that the convergence checkpoint is
  appended by the tool at zero authoring cost. Its findings drove the re-scope recorded in the change
  doc, and the typed readiness approval in the ledger is the machine authority for this verdict.
- Delivery: one independent review after implementation and the full canonical suite.
- Repair: independent affected-lane reverification, with the independence audit made total by this
  wave rather than relaxed.

## Completion Criteria

- All ACs and tasks in `1tr85` are terminal with executed evidence, each red-first proof shown
  failing against pre-change code before it passes.
- The carrier census, the closed-ledger corpus check, and the legacy-parity fixtures pass.
- The canonical full suite, docs lint, and generated-surface drift checks are clean.
- Operator confirms the resulting path is simpler to follow and that no gate lost enforcement.

## Handoff or Next-Wave Notes

- Treat adjacent improvements as separate work unless they are required to make the canonical
  lifecycle internally consistent. In particular, leave test-runner acceleration to `1tmtx`.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 32 | 1,188,946 |
| implement | 228 | 4,535,813 |
| review | 663 | 13,100,461 |
| **Total** | **923** | **18,825,220** |

<!-- wave:context-efficiency-state {"generation":819,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":228,"content_source_credit":5580538,"derived_artifact_credit":551,"direct_net":4535813,"estimated_tokens_saved":4535813,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12952,"response_debit":1033897,"source_credit_count":487,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1573},"plan":{"calls":32,"content_source_credit":1260528,"derived_artifact_credit":140,"direct_net":1188946,"estimated_tokens_saved":1188946,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2177,"response_debit":72963,"source_credit_count":93,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3418},"review":{"calls":663,"content_source_credit":15397216,"derived_artifact_credit":2124,"direct_net":13100461,"estimated_tokens_saved":13100461,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":70914,"response_debit":2229208,"source_credit_count":911,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1243}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":923,"content_source_credit":22238282,"derived_artifact_credit":2815,"direct_net":18825220,"estimated_tokens_saved":18825220,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":86043,"response_debit":3336068,"source_credit_count":1491,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6234},"wave_id":"1tsyx review-lifecycle-simplification"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 18 | 0 | 4 | 11083840 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":11083840,"surfaced_events":18} -->
<!-- wave:exploration-avoided end -->
