# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-27
review-evidence-source: events.jsonl

wave-id: `1tsyx review-lifecycle-simplification`
Title: Review Lifecycle Simplification

## Objective

Make Wavefoundry establish each lifecycle claim once, repeat review only when later work
invalidates that claim, and re-review only the affected scope and lanes. Preserve the independent
readiness, delivery, repair-verification, high-risk adversarial, and operator-close controls that
protect quality while removing duplicate ceremony before the 1.15 line is finalized.

## Changes

Change ID: `1tr85-enh single-pass-review-lifecycle`
Change Status: `planned`

## Wave Summary

This wave consolidates one strong independent critical plan review into Prepare, makes
implementation builder-owned, runs one risk-selected independent delivery review, simplifies
repair/reverification loops, and makes Review and Close share one delivery-state evaluator.
Selected lanes are authoritative; Wave Council becomes operator-invoked rather than an automatic
gate. The wave also keeps `events.jsonl` as the only machine authority and provides clean
fresh-install and one-way upgrade behavior without requiring Git.

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
- Watchpoint: freeze the scope to one contract, one policy mode, one evidence authority, one delivery
  evaluator, and one bounded repair loop. Do not add new receipts, hashes, sidecars, reviewer
  labels, or compatibility layers while removing the old ones.
- Watchpoint: closed ledgers remain readable history; the retired mutation grammar is not kept alive for new
  or reopened work.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 0 records; 0 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | pending | no current executed approval | record approval evidence for wave-council-readiness |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Operational dependency: close or explicitly hand off overlapping work from wave `1to78` before
  opening this wave.
- Coordination dependency: wave `1tmtx` owns test-runner performance; this wave changes test
  cadence only and must not absorb runner-acceleration scope.

## Coordinator and Participants

- Coordinator: `wave-coordinator`
- Write-owning roles: `implementer`, `docs-contract-reviewer`
- Independent review roles: risk-selected from `code-reviewer`, `qa-reviewer`,
  `architecture-reviewer`, `security-reviewer`, `performance-reviewer`, and
  `docs-contract-reviewer` according to the new matrix.

## Current Assumptions

- Review quality is valuable; repeated review of an unchanged claim is the defect.
- `events.jsonl` remains the sole machine-readable authority and supports non-Git repositories.
- Fresh installs and upgrades should converge to one current workflow without runtime fallback to
  the retired workflow.

## Outputs Produced or Expected

- One canonical lifecycle/review matrix and risk-to-depth table, including the required critical
  plan-review dimensions.
- Simplified lifecycle orchestration, evidence grammar, and shared delivery evaluator.
- One-way review-config upgrade plus regenerated public carriers.
- Executable lifecycle, install, upgrade, concurrency, known-bad, and depth-selection coverage.

## Review Checkpoints

- Readiness: a fresh independent critical review challenges the proposed design, alternatives,
  assumptions, scope/ACs, failure paths, affected consumers, install/upgrade behavior,
  verification strategy, and credible threats before code edits.
- Delivery: one independent risk-selected review after implementation and the first full suite.
- Repair: only affected lanes reverify unless the repair changes a named full-review boundary.
- Optional Council: run only when the operator explicitly requests broader synthesis or conflict
  resolution; it never replaces or waives required lanes.

## Completion Criteria

- All ACs and tasks in `1tr85` are terminal with executed evidence.
- Fresh install, upgrade, non-Git, risk-depth, repair-loop, shared-gate, concurrency, and residue
  fixtures pass.
- The canonical full suite, docs lint, and generated-surface drift checks are clean.
- Operator confirms that the resulting path is simpler to follow and does not weaken review.

## Handoff or Next-Wave Notes

- Treat adjacent improvements as separate work unless they are required to make the canonical
  lifecycle internally consistent. In particular, leave test-runner acceleration to `1tmtx`.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 1 | 1,179 |
| **Total** | **1** | **1,179** |

<!-- wave:context-efficiency-state {"generation":1,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":1179,"estimated_tokens_saved":1179,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15,"response_debit":114,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1308}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":1179,"estimated_tokens_saved":1179,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15,"response_debit":114,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1308},"wave_id":"1tsyx review-lifecycle-simplification"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
