# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-09
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1usqm citation-durability-and-receipt-integrity`
Title: Citation Durability And Receipt Integrity

## Objective

Stop the review ledger accepting readiness approvals that can never satisfy a gate, and make authored citations resolvable so review cycles stop being spent re-verifying drifted anchors. Both changes address the same underlying cost measured across this session's waves: recordkeeping and citation churn consuming review attention that should go to the work.

## Changes

Change ID: `1upba-bug failed-prepare-appends-receipt-and-lapses-approvals`
Change Status: `implemented`

Change ID: `1urlb-change plans-anchor-by-symbol-not-line-number`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-08-09

## Wave Summary

Wave `1usqm` (Citation Durability And Receipt Integrity) delivered two changes: A Readiness Approval Is Accepted Silently Against An Already-Stale Receipt and Plans And Reviews Anchor By Symbol, Not By Line Number.

**Changes delivered:**

- **A Readiness Approval Is Accepted Silently Against An Already-Stale Receipt** (`1upba-bug failed-prepare-appends-receipt-and-lapses-approvals`) — 12 ACs completed. Key decisions: Accept and document the raw-filesystem-writer race; keep the hard guarantee scoped to cooperating Wavefoundry publishers; Amend the `"absent"` expectation of `test_transition_policy_distinguishes_stale_absent_and_current_readiness` deliberately
- **Plans And Reviews Anchor By Symbol, Not By Line Number** (`1urlb-change plans-anchor-by-symbol-not-line-number`) — 7 ACs completed
## Watchpoints

- **Both changes edit files carrying other waves' uncommitted work.** `server_impl.py`, `review_evidence.py`, `review_policy.py` and seed 170 all have working-tree modifications. Confirm each seam is unmodified by a sibling before editing; re-read rather than trusting a line offset recorded earlier in the session.
- **`1urlb` requires the `seed_edit_allowed` gate** for seeds 170, 180 and 211. Open it immediately before the edits and close it immediately after.
- **`docs/agents/guru.md` does not regenerate from seed 211.** The renderer treats it as a precondition, not an output. It must be hand-updated at all five pinned sites or the wave ships its own consumer surface contradicting the seed it just edited.
- **`1upba` changes one pinned test deliberately.** `test_transition_policy_distinguishes_stale_absent_and_current_readiness`'s `"absent"` case must be amended; any OTHER suite failure is a regression.
- **Sequencing watchpoint:** the two changes are independent and touch disjoint files, so neither blocks the other. `1upba` is the larger and carries both of its own P1s from readiness review.
- **Follow-up, not in this wave:** review-evidence citation authoring lives in `209-agent-harness-core.prompt.md` and the lane seeds, outside `1urlb`'s declared surfaces. Requirement 1 names review evidence as in-domain, so that third is deferred to its own change rather than absorbed silently. `237-council-review.prompt.md` should be revisited in the same follow-up.
- **Follow-up watchpoint — known fragility shipping in `1upba`:** the dry-run pending-mint advisory rides a parallel list (`_prepare_stale_advisories`) that **each of three return sites in `wf_prepare_wave_response` must remember to splat**. Any return added later silently drops it and nothing fails. The root cause is that `if diagnostics:` conflates "there is something to say" with "this failed", so an informational diagnostic cannot sit on the shared list without turning a preview into an `error`. Deliberately not fixed here: the clean fix adds a severity field to `_diagnostic` and changes that gate's semantics for **every** prepare diagnostic and every tool's response envelope, which is a public MCP contract change needing its own census. Tracked as its own change; do not "tidy" this into the shared list without it.
- **Follow-up, not in this wave:** `docs/architecture/data-and-control-flow.md` carries three pre-existing drifts (sole-writer claim, canonicalizer understatement, "evaluator version 2" against a shipped 7). `1upba` declares the doc for reading and deliberately does not repair it.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-08: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `1upba`'s Requirement 9 remedy named one close-branch carve-out door while the branch has two, and the untouched exit is the normal end-state of a refused-then-delivered wave, so the fix would have shipped green while leaving the close gate more permissive than the defect it repairs; strongest-alternative: drop `1urlb`'s seed-180 scope item rather than pin it, since the seed has only one citation-adjacent site — declined in favor of naming that site as the insertion point, because the review-evidence third of Requirement 1 already had no landing surface and dropping 180 as well would have left the change addressing authoring only)
- **Seat evidence [red-team] — 2026-08-08:** WITHHELD with two P1s and six lower findings, all folded. P1-a: `_required_wave_council_signoffs`'s close branch has two exits that drop the readiness key (`if has_review_signoff and review_key: return [review_key]` and the fallthrough); executed against real handlers, a wave with a receipt, no readiness approval and a current delivery approval takes the first and returns `['wave-council-delivery']`. P1-b: `1urlc`, shipped earlier this session, added `ambiguous_excluded_headings` as a second cause into the same `errors` list Requirement 2 degrades to a warning, making the degradation an author-reachable bypass via a duplicate `## Progress Log` heading. Also found `wf_mark_ac_response` cited in `1upba` exists nowhere in the repository (real symbol `_mark_change_item_response`), AC-3's payload unbuildable at two of three emit sites, AC-5 pinning an empty diagnostic list on a path returning fixture-dependent `action_diagnostics`, and two of the plan's own evidence claims overstated. Verified correct and re-executed independently: the defect premise, the lock claim, `derive_receipt_id` anti-revival, the 1605-test blast radius, and the six-approval `1ur6o` census.
- **Seat evidence [docs-contract-reviewer] — 2026-08-08:** WITHHELD with two P1s and ten lower findings, all folded. P1-a (convergent with red-team's scope finding): `1urlb` AC-4 asserted a rendering mechanism that does not exist — seed 211 declares `Output path: docs/agents/guru.md` but `render_platform_surfaces.py` treats that file as a precondition for the agent-surface pass rather than an output, and all five strings AC-2 pins also live in `docs/agents/guru.md` (lines 471, 544, 587, 596, 691), so the change would have shipped with its own Guru role doc teaching the replaced rule. P1-b: seed 180 sat in Scope, a Task and the AEG with no AC pinning it. Also established by census that `170-plan-feature.prompt.md` contains zero citation-related text across 205 lines so AC-1's insertion point named nothing; that review-evidence citation authoring lives in `209-agent-harness-core.prompt.md`, not in any seed this change edits; that `prompt-surface-manifest.json` cannot reflect a seed-body edit; and that `1upba` carried no obligation for `docs/specs/mcp-tool-surface.md`, proven undetectable by AC-11 since docs-lint passes today against a spec naming evaluator version 6 against a shipped 7. Verified clean: all five AC-2 pins resolve verbatim and uniquely, both `## Serialization Points` blocks parse to exactly their intended paths, and no superseded "stays as it is" framing survives.
- **Fold disclosure:** every P1 and P2 above was folded into the change docs before this verdict was recorded. The seats did **not** re-review the folded text; the substantive re-verification is carried by the delivery-phase lanes (`code-reviewer`, `qa-reviewer`, `architecture-reviewer`, `docs-contract-reviewer`) and the required delivery council, which run against the implementation.
- **Delivery-phase Wave Council [delivery-council] — 2026-08-09: PASS** (moderator: wave-council; primer-depth: full; primer: red-team; fixed seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: docs-contract-reviewer; seat-agreement: unanimous after one targeted challenge round; max-severity: high; strongest-challenge: the in-lock recompute serializes cooperating Wavefoundry publishers but cannot linearize an ordinary raw filesystem edit, and `1urlb` initially required review-evidence citation guidance while deferring every carrier that could deliver it; strongest-alternative: mediate every supported change-document mutation behind one receipt-binding/CAS operation and extend symbol-first guidance through seed 209 plus council/lane carriers; resolution: the citation requirement was narrowed to the delivered carriers, and the operator accepted the raw-writer race as a low-likelihood bounded limitation for the mostly single-user, one-agent-per-wave model, with next-gate detection documented in Requirement 1, Scope, AC-1, Decision Log, Risks and the public MCP contract; no blocking findings remain)
- **Delivery seat evidence — 2026-08-09:** code-reviewer and architecture-reviewer APPROVE after independently reproducing the raw-writer race and verifying the narrowed guarantee; qa-reviewer APPROVES after 43 focused receipt-policy tests, six real-process serialization/crash-cut tests, eight killed mutants, repeated timing-test reruns, and AC reconciliation; docs-contract-reviewer APPROVES after the canonical Serialization Points parser returned all eight delivered citation surfaces and detected the known-bad omission; security-reviewer APPROVES WITH NOTES after a focused cooperating-publisher interleaving probe and no-lock known-bad control; reality-checker APPROVES after focused reverification of both contract repairs. The canonical 62-file run completed 7,041 tests, with 1,635/1,635 `test_server_tools` cases passing; two sub-millisecond warm-p95 overruns under six-worker load passed immediately and on three further paired reruns. `wf_validate_docs`: ok.
- **Delivery improvements recommended:** keep the exact raw-writer race probe as evidence of the accepted boundary; add a mediated/CAS authoring surface only if concurrent raw editing becomes supported; carry symbol-first review-evidence guidance through seed 209, seed 237 and lane carriers in the already-declared follow-up; reconcile seed 007 and the pre-existing architecture drift separately. These are explicit follow-ups, not hidden closure conditions for the narrowed delivered contracts.

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
| plan | 62 | 2,066,969 |
| implement | 455 | 1,374,840 |
| review | 186 | 3,725,969 |
| **Total** | **703** | **7,167,778** |

<!-- wave:context-efficiency-state {"generation":725,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":455,"content_source_credit":3753142,"derived_artifact_credit":1973,"direct_net":1374840,"estimated_tokens_saved":1374840,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18846,"response_debit":2364125,"source_credit_count":185,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2696},"plan":{"calls":62,"content_source_credit":2203715,"derived_artifact_credit":289,"direct_net":2066969,"estimated_tokens_saved":2066969,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3224,"response_debit":139507,"source_credit_count":55,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":186,"content_source_credit":4535294,"derived_artifact_credit":1406,"direct_net":3725969,"estimated_tokens_saved":3725969,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8219,"response_debit":803858,"source_credit_count":117,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":703,"content_source_credit":10492151,"derived_artifact_credit":3668,"direct_net":7167778,"estimated_tokens_saved":7167778,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":30289,"response_debit":3307490,"source_credit_count":357,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9738},"wave_id":"1usqm citation-durability-and-receipt-integrity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 45 | 0 | 9 | 24,408,636 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":24408636,"surfaced_events":45} -->
<!-- wave:exploration-avoided end -->
