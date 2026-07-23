# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-22
review-evidence-source: events.jsonl

wave-id: `1tbvp retire-reindex-reports`
Title: Retire Reindex Reports

## Objective

Retire the daily reindex-report artifact: the docs gardener stops writing `docs/reports/reindex-<date>.md` (no consumer exists; drift/lint/scan all special-case-ignore them), seeds stop teaching it, and this repository's 30 accumulated dated reports are deleted (operator decision, 2026-07-22).

## Changes

Change ID: `1tbvo-change retire-reindex-reports`
Change Status: `implemented`

Change ID: `1tb4z-ref finding-synthesis-projection-cleanup`
Change Status: `implemented`

Completed At: 2026-07-22

## Wave Summary

Wave `1tbvp` (Retire Reindex Reports) delivered two changes: Retire the Daily Reindex Report Artifact and Finding Synthesis Projection Cleanup (Plain Summary, wave- Class). Notable adjustments during implementation: Retire the Daily Reindex Report Artifact: Implemented: report-writing path and `render_report` removed from `gardener_run` (stamping run now prints `stamped N doc(s)`; empty-run output unchanged); new `test_stamping_run_writes_no_reindex_report` pins no-report + `render_report` absence; seeds 140/190 updated; pre-deletion census zero references; 30 dated reports deleted, 4 other reports remain; docs gate clean.; Retire the Daily Reindex Report Artifact: Operator mid-implementation directive: remove tests that are no longer relevant. Removed `test_empty_run_leaves_existing_report_untouched` (tested the retired empty-run-vs-existing-report interaction) and simplified the empty-run test to `test_empty_run_prints_nothing_to_report` (its no-report assertion is subsumed by the stronger stamping-run test). Kept the reindex-named FIXTURES in `test_doc_drift`/`test_docs_lint`: they exercise the retained `docs/reports/` prefix exemptions, which stay live for other report types. Gardener+drift+lint modules: 927 tests OK.; Finding Synthesis Projection Cleanup (Plain Summary, wave- Class): Implemented: external-ledger render sites emit `*<summary>*` plain line (`review_evidence_plain_summary`); inline sites keep `<details>` with class `wave-review-evidence`; canonicalizer collapses bodyless details blocks (either class spelling) to the plain line and normalizes the legacy class on bodied blocks. Four regressions added (plain-form render, legacy bodyless-form freshness equality, bodied-inline non-collapse, class normalization); `test_review_evidence` 92 OK. Live convergence verified on this wave's own projection at the next ledger write; docs gate clean over all old-form archives with zero rewrites.

**Changes delivered:**

- **Retire the Daily Reindex Report Artifact** (`1tbvo-change retire-reindex-reports`) — 3 ACs completed. Key decisions: Stop writing reindex reports entirely; delete the backlog.; Keep `docs/reports/` and all its exemptions.
- **Finding Synthesis Projection Cleanup (Plain Summary, wave- Class)** (`1tb4z-ref finding-synthesis-projection-cleanup`) — 3 ACs completed. Key decisions: Plain markdown summary line on the external path; details retained only where it collapses a real JSONL body.; Normalize legacy forms in the canonicalizer; never rewrite archives.
## Watchpoints

- Watchpoint: delete the local backlog only after the producer change lands, so a mid-wave gardener run cannot mint a fresh report; follow-up in-wave if any doc references a dated report by name (census before deletion).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| lifecycle-upgrade-miss-canonicalization | do_now | no | completed | wave-council-delivery |
| run-garden-parses-bounded-output | do_now | no | completed | wave-council-delivery |
| run-garden-stdout-contract-break | do_now | no | completed | wave-council-delivery |

*Machine review evidence — 36 records; 12 runs; 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-22 (delta, late admission 1tb4z): PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the canonicalizer's bodyless-details collapse matching a bodied inline block and silently hiding machine records from validation — resolved by requiring summary-close immediately followed by details-close (whitespace only; the inline form always carries a jsonl fence between them) with both shapes pinned by regression; strongest-alternative: a JSON state comment mirroring wave:context-efficiency-state — rejected with recorded rationale, events.jsonl is the machine authority and nothing parses the summary prose.)

- **Delivery-phase Wave Council [delivery-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the readiness plan promised the empty-run tests would "stay as-is" but implementation found one of them tested a retired interaction — resolved honestly by the operator's mid-implementation prune directive, recorded in the Progress Log with the kept-fixtures rationale; strongest-alternative: renaming the reindex-named fixtures in drift/lint tests — declined, they exercise retained prefix exemptions and renaming is cosmetic churn.)

- **Prepare-phase Wave Council [prepare-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a hidden consumer of the reports appearing after removal — resolved by the zero-consumer census plus the fact that three subsystems already carry explicit ignore/exempt code for the prefix; strongest-alternative: rolling single report or N-day retention — both rejected by operator, they preserve upkeep of an artifact nothing reads.)

## Prepare Review Evidence

Readiness council pass, 2026-07-22 (single change; claims verified against the tree):

- reality-checker: the producer claim is real (`docs_gardener.py:282` writes `docs/reports/reindex-<date>.md` from `gardener_run`); the zero-consumer claim was censused (`code_keyword` over `reindex-`, `docs/reports`, `reindex_report` across scripts, seeds, and dashboard — no reader); the three ignore sites resolve (`DRIFT_EXEMPT_PREFIXES` in `index_state_store.py:3393` with the false-positive-tail comment, `_SKIP_PREFIXES` in `link_validators.py:23`, `metadata_validators.py:14`, `reconcile_scan.py:123`); 30 of 34 files in `docs/reports/` are the dailies.
- red-team: strongest challenge — something consumes the reports invisibly (dashboard, upgrade path, a target-repo flow); answered by the census and by history: the drift subsystem's only relationship to these files was being HURT by them (false-positive tail, patched by exemption). Second — deleting the backlog breaks links; answered by the pre-deletion reference census and the docs gate (which itself skips link checks under the prefix, so any reference would live outside it and be caught). Third — seed 190's archival contract references reindex reports; the change updates the example wording while keeping general report archival, so other report types keep their flow.
- qa-reviewer: ACs are falsifiable (fixture stamping run writes no report and `render_report` is gone; seed census; zero dated files locally with other reports intact; full suite). The existing empty-run tests already pin no-report behavior and stay as-is.
- docs-contract-reviewer: the operator decision and both rejected alternatives (rolling report, retention; plus archival-into-wave-folders) are recorded in the Decision Log; keeping `docs/reports/` and its exemptions is an explicit scoping decision with rationale.

Synthesis verdict: READY.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

Delivery council pass, 2026-07-22 (single change; claims verified against the tree and the suite):

- reality-checker: the postcondition is real — zero `docs/reports/reindex-*.md` files remain, the four other reports are intact, `gardener_run` writes nothing under `docs/reports/` (stamping run prints `stamped N doc(s)`), and `render_report` is gone (pinned by `assertFalse(hasattr(dg, "render_report"))`).
- red-team: strongest challenge — a hidden consumer breaking after removal; the zero-consumer census held through implementation, and the full suite passed with the producer removed, which would have caught any code-path reader. Deletion-breaks-links was answered by the zero-reference pre-deletion census plus a clean docs gate after.
- qa-reviewer: the new `test_stamping_run_writes_no_reindex_report` fails by construction against the pre-change code; the retired-interaction test was removed and the empty-run test simplified per the operator's prune directive; gardener+drift+lint modules 927 OK; full suite 6,138 tests across 59 files OK in a single post-change run.
- docs-contract-reviewer: seeds 140/190 no longer teach the artifact while seed 190's general report archival stays; tracking is real-time with the prune directive and the Gapfill recorded; the readiness claim that the empty-run tests would stay unchanged was corrected in the Progress Log rather than silently.

Synthesis verdict: PASS.

Second operator review + repair cycle and late admission, 2026-07-22: the operator's second independent review (P1 confirmed fixed) found P2 `run-garden-parses-bounded-output` — `run_garden` parsed contract records from the BOUNDED output, so a 6,000-record reproduction reported 2,273 with a corrupted final path. Repaired per the operator's required shape: records now parse from the COMPLETE stdout, the 200k bound applies only to the human-facing output field, and the over-cap regression pins the reproduction case (fixture asserted larger than the real bound). Chain terminal at cycle 2 with the auto-derived convergence checkpoint freezing both findings. In the same session the operator directed the late admission of `1tb4z` (projection cleanup, delta council recorded): external-ledger projections now carry a plain italic summary line instead of the vestigial details wrapper, the retained inline-path class renamed to `wave-review-evidence`, legacy forms normalized in the canonicalizer with zero archive rewrites — live convergence proven on this wave's own projection, docs gate clean over all old-form archives. The full-suite run for 1tb4z live-caught a fourth consumer the census missed (the dashboard's projection-freshness comparison used raw text; fixed with the same canonicalization seam, with the old-form fixture as the regression). Final suite: 6,147 tests across 59 files OK in a single run.

Operator review + repair cycle, 2026-07-22 (post-council): the operator's independent review found P1 `run-garden-stdout-contract-break` — the gardener stdout change broke `run_garden()`'s implicit 'wrote'-grep contract, so `wf_garden_docs` reported files_updated 0 on stamping runs and stopped triggering the background docs-index refresh; the delivery council missed it because `RunGardenTests` fed a hand-written fixture instead of canonical producer output (the recorded fixture-echo class). Repaired per the operator's required shape: stable `docs-gardener: updated <path>` per-path output contract documented on both sides, exact-prefix parsing, canonical-producer integration tests running the real gardener subprocess, a prose/legacy negative test, and refresh-trigger assertions (stamping triggers, empty does not). Chain terminal (implementer repair_start, qa-reviewer reverification with live post-reload MCP probes: stamping probe files_updated 1 with the doc listed and stamp self-restored, empty probe 0); post-repair suite 6,143 OK single run; `wave-council-delivery` re-approved with fresh independent context. Lesson promoted as memory `1tax0-mem stdout-is-a-contract-when-something-parses-it`.
- operator-signoff: approved 2026-07-22 (operator ran three independent review rounds, verified all repairs including live probes against 1slep and a copied archive, and pre-approved close conditional on the dry-run reporting only this signoff; condition met after the projection replay)

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 12 | 828,427 |
| implement | 14 | 7,355 |
| review | 122 | 4,479,201 |
| **Total** | **148** | **5,314,983** |

<!-- wave:context-efficiency-state {"generation":144,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":14,"content_source_credit":11672,"derived_artifact_credit":257,"direct_net":7355,"estimated_tokens_saved":7355,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1425,"response_debit":3149,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":12,"content_source_credit":834668,"derived_artifact_credit":786,"direct_net":828427,"estimated_tokens_saved":828427,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":831,"response_debit":9387,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"review":{"calls":122,"content_source_credit":4619442,"derived_artifact_credit":2009,"direct_net":4479201,"estimated_tokens_saved":4479201,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12212,"response_debit":131133,"source_credit_count":146,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1095}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":148,"content_source_credit":5465782,"derived_artifact_credit":3052,"direct_net":5314983,"estimated_tokens_saved":5314983,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14468,"response_debit":143669,"source_credit_count":180,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4286},"wave_id":"1tbvp retire-reindex-reports"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
