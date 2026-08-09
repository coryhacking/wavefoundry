# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uprb review-authority-mutation-on-failure`
Title: Review Authority Mutation On Failure

## Objective

Stop review authority from lapsing for reasons that are not claim changes, and start telling the operator which policy input moved when it legitimately does. Today `wf_review_event` binds an approval to whatever receipt is in the ledger without recomputing the inputs, so an approval recorded after a plan edit is dead on arrival and still returns `ok`; nothing on any surface names the input that changed. In wave `1ur6o` that cost six recordings of the same readiness approval. Nothing in the receipt publication path changes.

## Changes



Change ID: `1urlc-bug recordkeeping-edits-still-lapse-review-approvals`
Change Status: `implemented`

## Participants

- Coordinator: session agent (Claude Code)
- Write-owning roles: implementer. `1upba`: red-test, refuse-path, attribution, signal-surfaces, close-gate. `1urlb`: rule-text, seed-edits, surface-render. `1urlc`: red-tests, handoff-exclusion, whitespace, changes-sort, census, seed-and-docs.
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-08-08

## Wave Summary

Wave `1uprb` (Review Authority Mutation On Failure) delivered one change: Recordkeeping Edits Still Lapse Review Approvals.

**Changes delivered:**

- **Recordkeeping Edits Still Lapse Review Approvals** (`1urlc-bug recordkeeping-edits-still-lapse-review-approvals`) — 15 ACs completed. Key decisions: Yes
## Watchpoints

- Watchpoint: `1urlb` and `1urlc` both declare seed `180-implement-feature.prompt.md` AND seed `170-plan-feature.prompt.md`. Two shared seeds under one `seed_edit_allowed` gate, so one agent takes both or they serialize.
- Blocking: `1upba`'s fixtures must trigger a pending mint through a section that STILL churns after `1urlc` — `## Requirements` or `## Scope`. A fixture that churns via `## Session Handoff` silently stops working once `1urlc` excludes it, and the test would pass for the wrong reason.
- Watchpoint: run `1urlc`'s AC-5 corpus census LAST, after every edit in the wave has settled, since it measures the delta the canonicalizer produces.
- Watchpoint: implementation ORDER is a mild preference, not a constraint, and an earlier revision of this record overstated it as blocking. `1urlc` re-digests the corpus once and lapses recorded approvals, but approvals are recorded at readiness and at delivery, never between implementation edits, so either order costs one prepare and one re-record at the end. Measured at planning time: no **non-closed** wave in the tree holds a `review_policy_receipt`, which is the property that actually matters. Measured: 68 wave ledgers, 26 hold at least one receipt, and all 26 of those are closed. The three other `planned` waves (`1p6lp`, `1seaw`, `1tmtx`) each hold zero and this wave's ledger is empty, so the re-digest currently has no live approval to lapse anywhere. Mild preference is `1urlc` first, so the one-time cost lands while that is still true.
- Watchpoint: the `## Decision Log` exclusion is DEFERRED to `1us4q`, not dropped. Its disproof travels with it so the next attempt starts from the measurement.
- Blocking: `security-reviewer` is REQUESTED by judgment, not by path score. Path scoring rotated it out when the wave grew, but `1upba` changes review authority itself and that seat is the one that found the defect where the proposed fix would have made the close gate MORE permissive than the bug. A requested lane is always honored.
- Blocking: NOTHING in the receipt publication path changes. Both council seats executed the originally proposed write-suppression guard and it either readies the wave on a dead approval with a required lane and the delivery Council silently dropped, or wedges the receipt permanently with no force or confirm affordance on the tool. AC-6 pins the publication behavior positively so an implementer cannot drift back into it.
- Blocking: the stale-bind refusal must degrade to a WARNING when policy selection returns errors. A refusal on a malformed change doc would make an unparseable plan unapprovable, which is worse than the defect being repaired.
- Blocking: every staleness signal must NAME the transition and what moved. A bare diagnostic code reproduces exactly the confusion this wave exists to remove, so AC-3 asserts message content rather than the code.
- Watchpoint: the change ID and this wave's slug both record the original falsified hypothesis. Kept deliberately so the plan stays linked to its disproof; the banner at the top of the change doc carries the correction.
- Watchpoint: `server_impl.py`, `review_evidence.py` and `review_policy.py` all carry uncommitted work from sibling waves. Confirm each seam is unmodified by another wave before editing.
- Context: `wf_mark_ac(state='~')` is in scope for its SIGNAL only. Its receipt write is correct and stays.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-08: PASS (three-change wave)** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the security-reviewer LANE was additionally requested by judgment and contributed the close-gate permissiveness finding on the earlier scope; the council WITHHELD on every pass until this one, and each rejected design was disproved by EXECUTION rather than argument. On the expanded wave, `1urlc`'s proposed Decision Log exclusion was measured removing a full-council trigger from 21 documents and a required lane from 4, with three executed author attacks including one that reinterprets an approved AC while moving no digest at all; it was SPLIT OUT to `1us4q` gated on a differential census. Session Handoff was narrowed to boilerplate-only after a census found 39 of 732 sections carry substantive text including admission preconditions, and exact equality was then required after five documents were found that BEGIN with the template sentence and continue substantively. Two implementation-level defects were caught that reading could not have surfaced: a single trailing space is load-bearing for four space-terminated whole-document lane triggers, so the coordinator's 'harmless' whitespace normalization can silently drop a required lane while the corpus census reports zero forever; and the coordinator's 'fail loudly' instruction specified a raise at three call sites that have no handler, on a predicate conflating absent with duplicated, which would have broken the 89 of 825 documents that legitimately carry no Session Handoff section. The coordinator also fabricated a test name while converting line anchors to symbol anchors, which is precisely the failure the citation-durability change in this same wave exists to prevent, and asserted a false 'zero line citations remaining' count. strongest-alternative: ship only what measures harmless and defer the rest with its disproof attached. Adopted. Final differential across 825 documents and 208 waves: ZERO lane changes, ZERO council-trigger changes, ZERO seat moves, non-vacuity confirmed at 698 of 825 canonical bodies moved. Both seats APPROVE `1urlc` for implementation; `1urlb` carries two unfolded items and is explicitly NOT ready)
- **Prepare-phase Wave Council [prepare-council] — 2026-08-08: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the council WITHHELD three times before passing, and every rejected design was disproved by EXECUTION rather than argument. Round one: both seats independently showed the plan diagnosed an ordering defect where the code has an ACCEPTANCE defect, since prepare mints only when a policy input already moved — which a change-doc edit does, and which sibling change `1urlc` measured a canonicalizer edit also does with zero document edits, so the approval in the reproduction was dead on arrival. They then ran the proposed write-suppression guard and it produced two outcomes the plan had chosen neither of: as advisory it readies AND opens the wave on an approval bound to plan bytes that no longer exist, silently dropping a required lane and the delivery Council; as blocking it is idempotent and wedges the receipt permanently. It also collapsed an A-B-A' cycle to one receipt id, reintroducing the revival that Requirement 8 rejects digest binding for. Round two, the most consequential finding: the surviving refusal would have made the close gate MORE permissive than the defect it repairs, because `_required_wave_council_signoffs` keeps the readiness key required for a STALE approval but drops it for an ABSENT one, and the refusal converts stale into absent. Today's bug is accidentally self-healing and the fix would have removed the healing, so an operator who tried to do the right thing would have ended up with weaker review than one who never tried. Folded as Requirement 9 and AC-9. Round two also found AC-3 demanded per-document attribution the system discards, achievable only via an `evaluator_version` bump that would lapse every in-flight readiness approval in every target repository, a global instance of the exact harm being reduced; and that AC-6 was pinned at a mode where the outcome it guards is invisible. Round three found AC-9 and AC-11 in direct collision over a shipped test whose `absent` fixture publishes a receipt, caught a false-support citation the coordinator had written for that same test, and found the new predicate failed open on an unreadable ledger. The genesis-deadlock constraint was attacked hardest on explicit instruction, since disproving it would have revived the coordinator's first design, and it STOOD. Final state verified by execution: the remedy closes the inversion, the pre-policy population is not stranded, and the blast radius is exactly ONE deviation across 1605 tests, which the plan now amends deliberately with wave `1tsyx`'s own principle as authorization; strongest-alternative: ship the acceptance fix and the signal fixes only, touching nothing in the publication path. Executed and shown to converge in one prepare plus one approval per receipt-bound lane with ZERO duplicate approvals, which is the entire observed harm. Adopted as the plan)

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
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 105 | 2,210,626 |
| implement | 11 | 517,295 |
| review | 13 | 62,697 |
| **Total** | **129** | **2,790,618** |

<!-- wave:context-efficiency-state {"generation":99,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":11,"content_source_credit":520291,"derived_artifact_credit":0,"direct_net":517295,"estimated_tokens_saved":517295,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":255,"response_debit":2741,"source_credit_count":15,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":105,"content_source_credit":2426314,"derived_artifact_credit":3898,"direct_net":2210626,"estimated_tokens_saved":2210626,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4357,"response_debit":218612,"source_credit_count":53,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3383},"review":{"calls":13,"content_source_credit":85301,"derived_artifact_credit":2179,"direct_net":62697,"estimated_tokens_saved":62697,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5115,"response_debit":21014,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":129,"content_source_credit":3031906,"derived_artifact_credit":6077,"direct_net":2790618,"estimated_tokens_saved":2790618,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9727,"response_debit":242367,"source_credit_count":88,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4729},"wave_id":"1uprb review-authority-mutation-on-failure"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
2
