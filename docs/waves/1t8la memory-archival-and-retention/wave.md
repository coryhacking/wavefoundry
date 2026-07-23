# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-23
review-evidence-source: events.jsonl

wave-id: `1t8la memory-archival-and-retention`
Title: Memory Archival And Retention

## Objective

Move inactive agent-memory bodies into a version-controlled local archive while
keeping compact active pointers for deliberate historical discovery. Default
memory retrieval must become smaller and more trustworthy without losing the
evidence, provenance, or recovery guarantees of prior learning.

## Changes

Change ID: `1t8l9-enh memory-archival-and-retention-lifecycle`
Change Status: `implemented`

Completed At: 2026-07-23

## Wave Summary

Wave `1t8la` (Memory Archival And Retention) delivered one change: Memory archival and retention lifecycle. Notable adjustments during implementation: Memory archival and retention lifecycle: Independent delivery review found two adjacent pending-archive gaps after the rename crash window: docs lint blocked without naming the retry, and unfiltered/history loads hid the source disposition so proposal/backfill could regenerate it. Repair: lint now identifies the pending state and exact reconcile recovery; the loader surfaces it only as `pending_archive_body` to unfiltered/history consumers, preserving default advisory/index isolation. Added direct lint, loader/history, proposal-suppression, and ambiguous-both-bodies regressions.

**Changes delivered:**

- **Memory archival and retention lifecycle** (`1t8l9-enh memory-archival-and-retention-lifecycle`) — 7 ACs completed. Key decisions: Use a physical, local archive plus compact active pointers.; Archive only by explicit reconciliation.
## Watchpoints

- Archive bodies must be excluded from every normal docs, graph, and advisory
  path; status filtering alone is insufficient.
- Every move must be a state-derived, fenced rename with interruption recovery;
  do not use copy/delete or an in-memory migration map.
- Preserve source-event dispositions so backfill and close-time proposal never
  regenerate archived learning.

## Participants

- Product owner: operator — selected physical Git-visible archival with active
  pointers and authorized planning/readiness work.
- Council moderator: wave-council.
- Readiness seats: red-team, docs-contract-reviewer.
- Builder lane: implementer — owns the coordinated memory schema, transaction,
  retrieval-isolation, and upgrade contract.
- Implementation review lanes: code-reviewer, architecture-reviewer,
  qa-reviewer, docs-contract-reviewer, performance-reviewer, security-reviewer.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: moving records under an archive folder does not by itself remove their bodies from normal docs, graph, or advisory retrieval, so an apparent archive could still pollute the active corpus; strongest-alternative: status-only archival — rejected because it leaves the bodies where default indexing can reach them)
- Council evidence: the plan makes full-path exclusion, active pointers, fenced state-derived rename recovery, and upgrade/backfill coherence required acceptance criteria. Red-team required crash-window coverage and rejected status-only archival; docs-contract-reviewer found the archive-body/pointer distinction, retention protections, and explicit history contract consistent across requirements, scope, ACs, and decision log.
- pre-implementation-review: passed (2026-07-22) — highest risk is a
  false archive caused by recursive active-corpus loaders or stale semantic
  rows still reaching the moved body; the implementation packet therefore
  treats active records, archive pointers, and archived bodies as three
  explicit path classes and verifies each loader/index/graph boundary.

## Pre-Implementation Review

**Pre-mortem**

1. A recursive memory or docs walk continues to ingest archive bodies after the
   move.
2. A crash between status rewrite, rename, and pointer publication leaves two
   bodies, no pointer, or a retry path that depends on lost process state.
3. Proposal/backfill duplicate detection stops seeing archived source events
   and regenerates old learning.
4. The public MCP contract exposes archival through an ambiguous status change
   without a required reason or protected-kind review cue.
5. Tests prove the happy path but miss stale-index, restart, or second-call
   convergence.

**Packet completeness**

- The admitted change has complete requirements, required-priority ACs,
  explicit out-of-scope retrieval scoring, architecture targets, and a test
  matrix.
- MCP code retrieval identified the coordinated surfaces in
  `memory_records.py`, `server_impl.py`, `indexer.py`, `graph_indexer.py`,
  memory proposal/backfill, docs lint, and upgrade publication.
- The known risk is accepted only with a state-derived filesystem transaction:
  no in-memory rename map and no copy/delete sequence.
- Pre-implementation memory advisories require current-code verification around
  `server_impl.py` instrumentation and hot reload; the implementation will not
  add a new sibling module and will live-probe the public tool after reload.

**Ordered lane sequence**

1. implementer — define the three path/schema classes and archive eligibility.
2. implementer — add the fenced, state-derived rename/recovery operation.
3. implementer — isolate default search, briefs, docs indexing, graph
   extraction, proposal/backfill, and upgrade publication.
4. implementer — add interruption, idempotency, retrieval, lint, and upgrade
   regressions; reconcile docs and lifecycle guidance.
5. code, architecture, QA, docs-contract, performance, and security reviewers —
   challenge the completed implementation during **Review wave**.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| pending-archive-disposition-invisible | do_now | no | completed | — |
| pending-archive-docs-gate-has-no-recovery | do_now | no | completed | — |

*Machine review evidence — 45 records; 13 runs; 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

Independent delivery review, 2026-07-22 (reviewer session distinct from the implementing session; claims verified with executed probes, never against the implementation's own prose):

- code-reviewer: the archive transaction is rename-first (`Path.replace`, no copy/delete anywhere), state-derived, and fenced through the shared cross-process lock; corpus isolation holds at all three boundaries (`walk_repo`, the incremental `files=` seam, graph extraction) with the WALKER_VERSION 7-to-8 bump evicting archived bodies from existing indexes; lint's archive/pointer path-class rules are strict for completed archives.
- qa-reviewer: adversarial probes beyond the shipped tests all passed — both-bodies ambiguity refuses (now also pinned by regression at the reviewer's suggestion), a retry with a different reason after a rename-window crash converges adopting the retry's reason, completed archives keep their source_event visible to propose dedup, and briefs/advisories exclude bodies and pointers structurally. Two crash-window P2s were found by reviewer reproduction and repaired in-wave: the pending-archive state failed the docs gate with no recovery route (now a diagnostic naming the exact `memory_reconcile` retry), and the window body was invisible to unfiltered loads so propose/backfill dedup could regenerate it (now surfaced as `pending_archive_body` to history/disposition consumers while default surfacing stays isolated). Both chains terminal with dual-lane (code + QA) independent reverification and pinned regressions.
- architecture-reviewer: the three path-class model (active, archive body, pointer) is carried consistently through parser, loader, lint, index, graph, and MCP contract; the accepted ADR records the physical-archive decision with alternatives; no boundary drift found.
- docs-contract-reviewer: memory README, MCP spec, five architecture surfaces, close/review prompts, and the finalize seed reflect the shipped contract; the live-tool contract was probe-verified post-reload (with the known reload-survivor caveat: sessions attached before the change need a reconnect to pass the new `memory_reconcile` parameters by schema).
- Verification: reviewer-run full suite 6,168 tests across 59 files OK (independently matching the implementation's claim); docs gate clean; live post-reload probes executed.

Synthesis verdict: PASS — all seven ACs verified with independent evidence; the two reviewer-found P2s are repaired, reverified, and pinned.
- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 36 | 106,972 |
| implement | 71 | 1,484,915 |
| review | 51 | 502,566 |
| **Total** | **158** | **2,094,453** |

<!-- wave:context-efficiency-state {"generation":138,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":71,"content_source_credit":1792459,"derived_artifact_credit":0,"direct_net":1484915,"estimated_tokens_saved":1484915,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2862,"response_debit":306255,"source_credit_count":40,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1573},"plan":{"calls":36,"content_source_credit":150005,"derived_artifact_credit":1056,"direct_net":106972,"estimated_tokens_saved":106972,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":812,"response_debit":48542,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5265},"review":{"calls":51,"content_source_credit":561519,"derived_artifact_credit":2222,"direct_net":502566,"estimated_tokens_saved":502566,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12877,"response_debit":51348,"source_credit_count":45,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3050}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":158,"content_source_credit":2503983,"derived_artifact_credit":3278,"direct_net":2094453,"estimated_tokens_saved":2094453,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16551,"response_debit":406145,"source_credit_count":109,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9888},"wave_id":"1t8la memory-archival-and-retention"} -->
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
