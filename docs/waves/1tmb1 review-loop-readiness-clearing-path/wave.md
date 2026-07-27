# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-26
review-evidence-source: events.jsonl

wave-id: `1tmb1 review-loop-readiness-clearing-path`
Title: Review Loop Readiness Clearing Path

## Objective

Make code-grounded verification a tenet of **creating, reviewing, and implementing** plans, rather
than a review-phase rule only. When this wave closes, an author must verify a load-bearing claim about
existing code before it becomes a Requirement, an Acceptance Criterion, or a Decision Log rationale,
and an implementer must exercise a plan's premise before building on it. Now, because the review-only
version of this rule was hardened in wave `1p9pk` after a plan carrying a no-op mechanism, a
nonexistent cited helper, and a wrong caller census reached review, and all three shapes recurred on
2026-07-26.

> **The wave-id and Title are stale and frozen.** They name "review loop readiness clearing path",
> which described `1tmb0` before that change moved to wave `1tj0l` and was implemented there. This
> wave now carries only the code-grounded verification tenet. The lifecycle freezes the id; the
> Objective above is the authority on what the wave does.

## Changes


Change ID: `1tmb4-enh code-grounded-verification-as-core-tenet`
Change Status: `implemented`

Completed At: 2026-07-26

## Wave Summary

Wave `1tmb1` (Review Loop Readiness Clearing Path) delivered one change: Code-Grounded Verification As A Core Tenet Of Creating, Reviewing, And Implementing. Notable adjustments during implementation: Code-Grounded Verification As A Core Tenet Of Creating, Reviewing, And Implementing: **Delivery cycle 3 repairs (operator-commissioned independent closure review).** The reviewer landed a third-round falsification: AC-8(c) claimed the anti-drift tests sweep the named live copies, but no test read `docs/prompts/council-review.prompt.md:46`; mutating its rule line left all guards green (reproduction re-executed by the implementer before recording). Also: the AC-5 signature missed Markdown-equivalent markers (`*`/`+` bullets, `N)` numbering), proven by evading plants. Repairs: the seed 237 pin test now also pins the live copy (guarded by existence for target repos), and the signature regexes accept the marker classes. Both proven red by the exact reproductions, reverts sha256-verified, full module green. Accepted limits recorded: a fully prose-paraphrased order with no list structure evades the structural signature (F3-adjacent); AC-1's anti-duplication is exact-string and phase-seed-scoped, weaker than Requirement 8's "no seed" (F3); repo-root `AGENTS.md` carries a project-authored Quick chooser tripping the bullet signature without the distinction, outside AC-5's domain (F4) — flagged for the deferred mechanical-consistency change rather than silently absorbed.; Code-Grounded Verification As A Core Tenet Of Creating, Reviewing, And Implementing: **Delivery cycle 2 repairs.** The delivery council raised two blocking findings against the guards themselves, one falsified by execution: it planted a paraphrased exploration-order copy in seed 215 and the AC-5 test passed with it present (hardcoded file list keyed on the prose phrase, violating AC-5's own signature-keyed contract); and the AC-3 pairing pin asserted only the 170 side, so deleting 209's Reviewing statement left the suite green. Repairs: AC-5 test rewritten as a structural-signature scan (numbered `code_*` list, Quick Rules heading, or `- Use `code_` bullet run) over all seeds plus live guru.md, with a non-vacuity guard requiring the known carriers to trip the signature; a mention-count signature was measured and REJECTED because it trips 26 point-do-not-restate posture leads. AC-3 pin extended to 209's Reviewing bullet. Both repaired guards proven by known-bad probes: planted copy in 215 makes AC-5 FAIL (sha256-identical revert), deleting the Reviewing bullet makes AC-3 FAIL (restore verified in original bullet order). Full suite 6248 OK after repairs.; Code-Grounded Verification As A Core Tenet Of Creating, Reviewing, And Implementing: **Implemented.** Guard phase first: exact-value pins added at both sites; each demonstrated failing against a mutation the pre-existing substring tests survive ("each plan's" to "each artifact's" at the server string: substring test OK, pin FAILED, reverted, pin OK; "the artifact's" to "the plan's" in seed 237: same shape), then the four anti-drift tests confirmed red before any seed edit. Canonical tenet statement added to seed 209 ("Code-Grounded Verification (All Phases)") reusing `execution_status`; authoring obligation with the three claim shapes and the fix-absent AC rule added to 170; premise-exercise with stop-and-report added to 180; reading-vs-executing distinction added to 180, 211 and the live `guru.md` copy; cross-refs added to 237 (below the pinned rule, which stayed byte-identical) and 215; `review-and-evals.md:101` reconciled to reference; `agent-team-workflow.md:106` stale pointer corrected. Render confirmed byte-stable (diff-stat identical before/after). All six anti-drift tests green; full suite 6248 tests OK; both gates opened and closed around their tasks.

**Changes delivered:**

- **Code-Grounded Verification As A Core Tenet Of Creating, Reviewing, And Implementing** (`1tmb4-enh code-grounded-verification-as-core-tenet`) — 9 ACs completed. Key decisions: AC-7: do not extend seed 175's interrogation contract to unexecuted load-bearing claims.; Keep the two review-side sites' divergent wording ("each plan's" / "the artifact's") rather than unifying them into one shared constant rendered into both.
## Watchpoints

- ~~Blocking: `1tj0l` holds the single OPEN slot.~~ **Resolved:** `1tj0l` closed 2026-07-26; this
  wave now holds the OPEN slot (`transitioned_to_active` at prepare-create).
- Seed edits require `seed_edit_allowed`, opened and closed around the seed task. `1tmb0`'s seed `209`
  edit already landed via `1tj0l` at a **different section** (`~:157-162`) from this wave's target
  (`~:75-126`); there is no concurrent-edit hazard, but read the current file rather than the plan's
  line numbers.
- The review-side rule exists at **two sites with different wording** (`_build_prepare_council_brief`
  in `server_impl.py` says "each plan's"; seed `237:49` says "the artifact's"). Anchor by symbol and
  quoted string, not line number. Two pins are required; one cannot cover both.
- **The render pipeline does not propagate seed body edits.** Marker regions regenerate; the live
  restatement sites in `council-review.prompt.md`, `guru.md`, and `review-and-evals.md` are
  hand-reconciled per `1tmb4` AC-8.
- Tests already exist at both pin sites from wave `1p9pk` AC-5 and assert substring presence only.
  Running them proves nothing about this change. Each new pin must be shown to **fail against a
  mutated string**.
- **Follow-up:** this wave ships the prose half of `1p9pk`'s pattern. That wave paired prose with a
  mechanical backstop; the mechanically-detectable sibling here (cross-section contract consistency) is
  **deferred** to a separate change by operator direction. Recurrence is the honest test of whether
  prose alone suffices, and that follow-up is where the enforceable subset would land if it does not.
- Readiness-born findings **do** withhold readiness since `1tmb0` landed: the live guard at
  `review_evidence.py:1199` bars only *delivery*-born findings from reopening readiness. Clear
  readiness findings through the same-phase repair loop (`repair_start` at cycle >= 1, then an
  independent lane reverification).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 1tmb1-R1-plan-citations-do-not-resolve | do_now | no | completed | — |
| 1tmb1-R2-ac6-pin-premise-false-tests-already-exist | do_now | no | completed | — |
| 1tmb1-R3-serialization-names-a-cochange-not-in-this-wave | do_now | no | completed | — |
| 1tmb1-R4-wave-record-objective-is-an-unfilled-placeholder | do_now | no | completed | — |
| 1tmb1-R5-seed-180-census-miscounted-in-the-r1-repair | do_now | no | completed | — |
| 1tmb1-R6-repairs-not-applied-to-every-site-carrying-the-claim | do_now | no | completed | — |
| 1tmb4-ac3-consistency-pin-one-sided | do_now | no | completed | — |
| 1tmb4-ac5-signature-misses-markdown-equivalent-markers | do_now | no | completed | — |
| 1tmb4-ac5-test-not-signature-keyed | do_now | no | completed | — |
| 1tmb4-ac8-live-copy-sweep-claim-unexecuted | do_now | no | completed | — |

*Machine review evidence — 109 records; 33 runs; 10 findings; current: do_now 10, maybe_later 0, dont_do_later 0, not_issue 0*
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

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-26: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: AC-8 rested on an unverified render-model claim — the renderer upserts only its hardcoded marker block and fresh-only baselines, so seed body edits never reach `docs/prompts/`, and two live restatement sites (`council-review.prompt.md:46`, `guru.md` retrieval loop) would have silently missed the tenet; strongest-alternative: name the hand-reconciliation sites explicitly in Scope and extend the AC-1/AC-5 anti-drift sweeps to the live copies, adopted verbatim)

Seat evidence:

- **red-team: PASS.** Quoted both current pin strings exactly; grep-swept the full test tree proving the specified mutation ("each plan's" to "each artifact's") survives every pre-existing `1p9pk` assertion, so AC-6's exact-value pins are a genuine buildable delta. Verified the seed `209` insertion point is compatible (the protocol header already mandates the point-do-not-restate pattern), all seed censuses exact, and the "Product Intent" divergence correctly out of scope. Two staleness notes (symbol drifted to `:12504`, one Progress Log cite shifted) folded as advisory, symbol+string as anchor; its unrecorded unify-wording alternative is now a Decision Log rejection.
- **docs-contract-reviewer: FAIL, then PASS on reverified repairs.** Falsified AC-8's render-model premise by reading the pipeline (`reconcile_review_protocol_surfaces:1076` hardcodes the block; `reconcile_lifecycle_prompt_baselines:1115` is fresh-only); found the two out-of-region live restatement sites and the stale `agent-team-workflow.md:106` pointer. Repairs verified at every site carrying the claim, marker ranges re-confirmed, the one new citation (`211:116ff`) resolves; seat closed with objections dissolved.

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 121 | 1,552,350 |
| implement | 6 | 323,464 |
| review | 360 | 3,984,806 |
| **Total** | **487** | **5,860,620** |

<!-- wave:context-efficiency-state {"generation":370,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":6,"content_source_credit":325119,"derived_artifact_credit":0,"direct_net":323464,"estimated_tokens_saved":323464,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":68,"response_debit":1587,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":121,"content_source_credit":1783469,"derived_artifact_credit":2125,"direct_net":1552350,"estimated_tokens_saved":1552350,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35614,"response_debit":200821,"source_credit_count":102,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"review":{"calls":360,"content_source_credit":5203831,"derived_artifact_credit":139,"direct_net":3984806,"estimated_tokens_saved":3984806,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":41198,"response_debit":1179178,"source_credit_count":519,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1212}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":487,"content_source_credit":7312419,"derived_artifact_credit":2264,"direct_net":5860620,"estimated_tokens_saved":5860620,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":76880,"response_debit":1381586,"source_credit_count":622,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4403},"wave_id":"1tmb1 review-loop-readiness-clearing-path"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 524297 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":524297,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
