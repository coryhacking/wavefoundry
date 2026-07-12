# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-12

wave-id: `1seaw retrieval-intent-golden-queries`
Title: Retrieval Intent Golden Queries

## Objective

Make retrieval-quality work repeatable and gated: build the standing golden-query eval suite (Recall@k, nDCG, abstention correctness, latency/size — the permanent replacement for the bespoke AC-8/AC-10 gates each ranking change has rebuilt and discarded), then land the review-validated classifier improvements THROUGH it — artifact/path anchoring before phrase signals, a distinct assessment/review intent, and a bounded low-information-path penalty (ignore files, lockfiles, manifests, generated surfaces — exempt when the query names them). The live failure being fixed: broad review queries ("where are the gaps…") classified as navigational and ranking `.aiignore` comments above implementation evidence. No ranking edit merges without the suite showing improvement-without-regression.

## Changes

Change ID: `1sear-enh golden-query-retrieval-eval-suite`
Change Status: `planned`

Change ID: `1seas-enh question-classifier-artifact-anchoring`
Change Status: `planned`

## Wave Summary

Two ordered changes: the standing retrieval eval suite (golden corpus over eight query classes including verbatim misranked queries and abstention controls, one-command local run, recorded baseline), then eval-gated classifier/ranking improvements whose merge evidence IS the suite's before/after report.

## Journal Watchpoints

- Watchpoint (ordering is the contract): `1seas` is BLOCKED on `1sear`'s recorded baseline — no classifier or ranking edit before the gate exists and has scored the status quo. This ordering is the wave's reason for being.
- Watchpoint (regression tolerance): the suite's run-to-run tolerance must be measured and documented BEFORE it gates anything — an unreproducible gate gates nothing.
- Watchpoint (exemption fidelity): the low-information-path penalty must keep direct questions working (a query naming `.aiignore` surfaces it top-ranked) — the review itself flagged this as the boundary.
- Watchpoint (anecdotes become cases): the quality-log memory items (constant-value ranking, multi-token summary-first, review-session misrankings) are encoded as suite cases, not left as prose.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-12: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, architecture-reviewer; rotating-seat: qa-reviewer; strongest-challenge: an unreproducible eval gates nothing — retrieval scores can vary run-to-run (reranker nondeterminism, index drift), so a naive before/after diff could pass noise as improvement or block real gains as regression; resolved structurally by AC-3: the tolerance is MEASURED (two same-index runs) and documented BEFORE the suite gates anything, reports record the index meta signature, and comparisons are valid same-signature only; strongest-alternative: skip the standing suite and run another bespoke gate for `1seas` — rejected because this is the third ranking change to need one (1p41o, 1p4hj precedents) and the anecdote backlog in the quality log is exactly the corpus a standing suite executes)
- Council seat notes: reality-checker — the classifier claim is source-verified (`"where are"` in `navigational_signals` at ~17148, phrase check preceding artifact anchoring), the two live misrankings occurred in the review session against this repo, and the bespoke-gate precedents are real (AC-8 gated OUT `code_risk_score` v1 on measured degeneracy; AC-10 ran an 8-query recall comparison) — both were then discarded, proving the standing-suite gap. red-team — pressed overfitting (a suite tuned to this repo's quirks): accepted explicitly for the gate's purpose (this repo IS the dogfood; consumer packs extend later via p4ea) and recorded in the change doc; pressed the exemption boundary hardest: the penalty must not break \"what does .aiignore exclude?\" — AC-2 pins the named-artifact exemption with fixtures; pressed gaming-the-gate (tuning `1seas` to the suite): bounded by the suite covering ALL eight classes with tolerance-gated non-regression, not just the targeted queries. qa-reviewer — the eight query classes are enumerated with negative controls, the misranked queries are encoded VERBATIM, and the suite is deliberately outside the hermetic unit run (needs a built index + cached models) with its own one-command entry; the ordering contract (`1seas` blocked on the recorded baseline) is the wave's serialization point and is fixture-independent (a process gate, enforced at review). architecture-reviewer — the suite becomes the standing gate documented in the contributing/review surfaces (replacing per-change bespoke harnesses), which is an architecture-of-process improvement with the same shape as the docs gate; the classifier changes mirror proven mechanics (`_demote_doc_results` down-weight, never exclusion) and stay heuristic — the ML-classifier alternative is parked unless the suite shows heuristics plateauing. seat_agreement: unanimous.
- AC priority: confirmed at prepare as proposed (all required across both changes). Product-owner acknowledgment: operator-directed 2026-07-12 ("build these waves now"); sequenced after `1seav` by priority.

## Review Evidence

- wave-council-readiness: approved 2026-07-12 — prepare council synthesis verdict READY: the ordering contract (suite baseline before any ranking edit) is the structural control, reproducibility is a measured precondition rather than an assumption, and the exemption boundary is fixture-pinned. Seats unanimous; full synthesis in Review Checkpoints.
- operator-signoff: approved when operator confirms closure

## Dependencies

- No external wave dependencies. Sequenced after `1seav` by priority, not necessity. CI scheduling of the suite is a separate operator infra decision.
