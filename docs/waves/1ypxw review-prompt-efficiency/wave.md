# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ypxw review-prompt-efficiency`
Title: Review Prompt Efficiency

## Objective

Act on the independent reviews of the Review wave prompt and the implementation review step: make receipt rotation name the document that moved and stop needless delivery re-approvals (tooling), remove duplicated and locally contaminated reviewer guidance from the generic seeds while adding the four missing generic sentences (seeds), and fix the wrong delivery-council gate sentence and bring the packaged review template up to the rule it exists to satisfy (surfaces). Now because four recent waves show sixty percent of approvals were re-approvals and a quarter of evidence rows cite temp paths.

## Changes

Change ID: `1yoy2-bug review-ledger-tool-gaps`
Change Status: `complete`

Change ID: `1ypxu-enh review-guidance-seed-gaps`
Change Status: `complete`
Depends On: `1yoy2-bug review-ledger-tool-gaps`

Change ID: `1ypxv-doc review-wave-surface-cleanup`
Change Status: `complete`
Depends On: `1ypxu-enh review-guidance-seed-gaps`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (tools, owned-block producer, tests, seeds), technical-writer (local surfaces, packaged template, role docs, CHANGELOG)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-22

## Wave Summary

Wave `1ypxw` (Review Prompt Efficiency) delivered 3 changes: Review Ledger Tool Gaps, Review Guidance Seed Gaps, and Review Wave Surface Cleanup. Notable adjustments during implementation: Review Ledger Tool Gaps: Readiness round (red-team, code, qa, architecture, docs-contract, all fresh): per-document attribution is not derivable from persisted data (one aggregate digest, closed receipt schema) and `review_policy_receipt_superseded` with `receipt_supersession_attribution` already exists with message pins; adopted the optional non-semantic `policy_inputs` field with the prepare-envelope projection stripped so the goldens stay unchanged; section-level attribution dropped; the status-row wording keyed on `receipt_binding_applies` inside the projection; the ephemeral predicate given a token grammar, a root list and a layering; the owned block keeps the three code names in one sentence so the `1tmb2` cross-pin and fresh-tree pins hold; the registry symbol corrected to `REVIEW_PROTOCOL_CARRIER_REGISTRY` plus native wrappers; seven test modules and the spec added to serialization points.; Review Guidance Seed Gaps: Readiness round (red-team, code, qa, architecture, docs-contract, all fresh): the Typed authoring shrink would have deleted the writing-hand sentence `1ypy6` adds, so the removed sentences are enumerated and everything else kept; the mutation-table cut is pinned by a `1wuju` seed test now named and rewritten; `tree_fingerprint` is already a required packet field; the `agent-team-workflow.md` reference is an expected carrier in seven seeds and the item is withdrawn; "exceptional" has three sites and the Review-wave statement one literal plus three paraphrases; seed 212's opening and the tool-posture lines are recorded in the census predicate; the de-localization rules are stated.

**Changes delivered:**

- **Review Ledger Tool Gaps** (`1yoy2-bug review-ledger-tool-gaps`) — 5 ACs completed. Key decisions: Operator clarification: only each lane's latest readiness approval prolongs the receipt advisory; only a durable repository path suppresses a temporary-only path warning.; Optional non-semantic `policy_inputs` on the receipt; projection stripped from the prepare envelope.
- **Review Guidance Seed Gaps** (`1ypxu-enh review-guidance-seed-gaps`) — 6 ACs completed. Key decisions: Depend on `1ypy6` rather than merge into it.; No delivery-round bound.
- **Review Wave Surface Cleanup** (`1ypxv-doc review-wave-surface-cleanup`) — 5 ACs completed. Key decisions: Keep the Wavefoundry-specific reviewer passages in the role docs, not the seeds.; Template grows to carry the seed 100 rule, with the packet as a pointer.
## Watchpoints

- Watchpoint: wave `1ypy6` edits seeds 180 and 209 and the owned-region rules; this wave opens only after `1ypy6` closes, and the seed inventory re-verifies every anchor against the landed text before the first seed edit.
- Watchpoint: propagation is explicit; `wf render-surfaces` does not copy seed prose into existing prompts, so the seed change carries a per-sentence propagation table and the surface change owns the authored reconciliation of Wavefoundry's own surfaces; a destination with no mechanism is recorded as not propagated.
- Watchpoint: every new seed sentence names no Wavefoundry artifact; the docs-contract lane greps each one for wave ids, wave-folder paths, test names, receipt paths, module and symbol names before delivery approval; seeds 214 and 221 lose their Wavefoundry passages and the role docs keep them; pre-existing tool-posture "Wavefoundry MCP" lines, "(wave 1wuju)" parentheticals and seed 212's opening are recorded as remaining, not new.
- Watchpoint: the owned-block re-render is marker-region only, so it does not collide with the role-doc prose edits of `1ypy6` or this wave; the receipt record gains one optional non-semantic field and the prepare envelope strips it, so receipt ids, ledgers and both lifecycle goldens stay unchanged.
- Watchpoint: the `seed_edit_allowed` gate is open only for the seed edit window and closed before the surface rewrite begins.
- Watchpoint: `server_impl.py` is a production retrieval module and the bug change edits it, so the wave owes a before-and-after retrieval receipt pair on a stable completed index (same generation at start and end), before-receipt before the first `server_impl.py` edit; the changed paths are not reachable from the measured tools, so the pair is expected (not pre-decided) to compare as drift rather than regression; the disposition path is the one the contributing guide prescribes: reverse-patch digest proof plus reachability closure, then operator review.
- Watchpoint: the ephemeral-artifact check is an advisory, never a refusal; the receipt-delta diagnostic is advisory on every envelope; nothing unconditional joins the prepare, delivery-review or close envelopes the lifecycle golden captures.
- Follow-up: a typed shape for `tree_moved_under_review` and a scope-neutral currency re-approval mode are recorded, not built.
- Follow-up: the index reaper defect (policy-ineligible paths re-stripped every generation) still needs its own plan before receipts on this store are trusted across generations.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| C-1 | do_now | no | completed | code-reviewer, qa-reviewer |
| C-2 | do_now | no | completed | qa-reviewer, docs-contract-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer, code-reviewer, qa-reviewer, architecture-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the receipt-delta requirement promised a per-document attribution the receipt cannot yield from persisted data while the tool already emits an honest not-attributable message, and two cuts contradicted wave 1tmb2 and 1wuju landing pins; strongest-alternative: persist per-change digests as one optional non-semantic receipt field so attribution is exact without moving receipt identity, keep the three code names in one sentence and rewrite the 1wuju pins to pointer wording, adopted; per-seat evidence in `readiness-review.md`)

## Dependencies

- External: wave `1ypy6 implement-prompt-efficiency` must close before this wave opens (it edits seeds 180 and 209 and the readiness wording this wave's seeds build on).
- Intra-wave order is declared by the `Depends On:` lines in the Changes section: `1yoy2` tools, then `1ypxu` seeds, then `1ypxv` surfaces.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 101 | 3,817,953 |
| implement | 194 | 4,068,243 |
| review | 73 | 1,271,224 |
| **Total** | **368** | **9,157,420** |

<!-- wave:context-efficiency-state {"generation":388,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":194,"content_source_credit":4457515,"derived_artifact_credit":67904,"direct_net":4068243,"estimated_tokens_saved":4068243,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8031,"response_debit":453069,"source_credit_count":89,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3924},"plan":{"calls":101,"content_source_credit":4096148,"derived_artifact_credit":1317,"direct_net":3817953,"estimated_tokens_saved":3817953,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5974,"response_debit":282988,"source_credit_count":194,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9450},"review":{"calls":73,"content_source_credit":1375329,"derived_artifact_credit":1280,"direct_net":1271224,"estimated_tokens_saved":1271224,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13288,"response_debit":94413,"source_credit_count":47,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":368,"content_source_credit":9928992,"derived_artifact_credit":70501,"direct_net":9157420,"estimated_tokens_saved":9157420,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":27293,"response_debit":830470,"source_credit_count":330,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15690},"wave_id":"1ypxw review-prompt-efficiency"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 41 | 0 | 19 | 28,627,369 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":19,"estimated_exploration_avoided":28627369,"surfaced_events":41} -->
<!-- wave:exploration-avoided end -->
