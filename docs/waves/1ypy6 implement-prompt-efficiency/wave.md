# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ypy6 implement-prompt-efficiency`
Title: Implement Prompt Efficiency

## Objective

Act on the independent review of the Implement wave prompt surface: close two generic guidance gaps in the seeds (string-named owners after a move; measurement pairs across a changed substrate), fix three seed sentences that contradict the enforced lifecycle, repair three tool gaps (dependency parsing, retained-context independence audit, mark-tool hints), and cut Wavefoundry's local surface to pointers plus exit criteria. Now because the last two handler-split waves paid for each gap with a repair cycle and the next one is readied.

## Changes

Change ID: `1ypy4-bug implement-wave-tool-gaps`
Change Status: `complete`

Change ID: `1yobp-enh implement-guidance-seed-gaps`
Change Status: `complete`
Depends On: `1ypy4-bug implement-wave-tool-gaps`

Change ID: `1ypy5-doc implement-wave-surface-cleanup`
Change Status: `complete`
Depends On: `1yobp-enh implement-guidance-seed-gaps`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (seeds, renderer, tools, tests), technical-writer (local surfaces, packaged template, role-journal history document, CHANGELOG)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-22

## Wave Summary

Wave `1ypy6` (Implement Prompt Efficiency) delivered 3 changes: Implement Wave Tool Gaps, Implement Guidance Seed Gaps, and Implement Wave Surface Cleanup. Notable adjustments during implementation: Implement Wave Tool Gaps: Readiness round (red-team, code, qa, architecture, docs-contract, all fresh): the first-draft predicate ("any earlier row") would have refused the second lane approval of every council round and every currency refresh, and would have failed this wave's own close; narrowed to any earlier `repair_start` context, with the finding-then-approve shape made visible instead. The table and prose parsers were dropped for the lint-validated wave-record line the tool never read. Added: advisory on the success envelope, replay placement, both close call sites, the lifecycle envelope golden, the `context_summary` schema, the full-id usage hint, the correct architecture doc.; Implement Wave Tool Gaps: Observe / Reflect: full-suite advisory census detected the two admitted sites missing from its strict expected set (QA-DEL-1). Recorded repair start, added only those exact triples; independent QA reverified and killed both tuple-removal and extra-site controls. Keep exact site censuses in the changed-contract inventory.; Implement Guidance Seed Gaps: Readiness round (red-team, code, qa, architecture, docs-contract, all fresh): the retired-journal block is project prose in six role docs, not renderer output, and `memory-archive.md` is machine-regenerated, so the local move went to `1ypy5` and only the seed 210 and 160 wording stays here; `code_patterns` has no producer, so the pin is static; "immediately preceding" also lives in seed 050 and five local surfaces; seed 100 carries no checkbox copy; added the seed 209 writing-hand, `recommended_fix` and code-enumeration sentences, the seed 180 docs-gate sentence, and the seed 110 and 160 notes the sibling changes rely on.

**Changes delivered:**

- **Implement Wave Tool Gaps** (`1ypy4-bug implement-wave-tool-gaps`) — 5 ACs completed. Key decisions: Predicate: any earlier `repair_start` context.; Read the wave record's validated `Depends On:` line; drop the table and prose parsers.
- **Implement Guidance Seed Gaps** (`1yobp-enh implement-guidance-seed-gaps`) — 6 ACs completed. Key decisions: One sentence per gap, in the seed section that already owns the pattern.; Docs-gate sentence goes in seed 180, not the seed 160 trigger list.
- **Implement Wave Surface Cleanup** (`1ypy5-doc implement-wave-surface-cleanup`) — 5 ACs completed. Key decisions: Pointers to seed sections instead of restated text, except pinned carrier passages.; New history document, not `memory-archive.md`.
## Watchpoints

- Watchpoint: seed edits reach every target on upgrade; each new sentence names no Wavefoundry artifact and is reviewed by the docs-contract lane against that rule.
- Watchpoint: the `seed_edit_allowed` gate is open only for the seed edit window and closed before the surface rewrite begins.
- Watchpoint: `server_impl.py` is a production retrieval module; the bug change edits it, so the wave owes a before-and-after retrieval receipt pair, taken on a stable completed index (same generation at start and end), before-receipt before the first `server_impl.py` edit; wave `1ymzq` also owes receipts and must not interleave.
- Watchpoint: the retained-context audit predicate is any earlier `repair_start` context; batch council approvals from one context, a lane reverifying its own finding, and currency re-approvals after a receipt rotation stay legal, and the finding-then-approve shape is made visible in the list view rather than refused. `1ymzk` is closed (`4a8b8951`); the inventory census records whether any live ledger carries a flagged row.
- Watchpoint: the packaged template is missing-only; the template block reaches new installs, and existing targets receive the same clauses through seed 160's carrier clause, which triggers on the seed 180 and 209 edits in `1yobp` (and seed 160's repo-local prompt reconciliation fires on the seed 100 edit); the template itself is never read for existing targets.
- Watchpoint: propagation is explicit; `wf render-surfaces` does not copy seed prose into existing prompts, so `1yobp` carries a propagation table (seed anchor, destinations, mechanism) and `1ypy5` owns the authored reconciliation of Wavefoundry's own surfaces; a destination with no mechanism is recorded as not propagated.
- Watchpoint: the retained-context audit judges only currently authoritative rows at close, so a superseded flagged row never blocks an append-only ledger; regressions cover replacement, ordering and receipt rotation.
- Watchpoint: every new seed sentence names no Wavefoundry artifact; the docs-contract lane greps each one for wave ids, wave-folder paths, test names and receipt paths before delivery approval.
- Follow-up: the index reaper repeatedly re-stripping the same policy-ineligible paths is a separate defect and needs its own plan before any retrieval receipt on this store is trusted across generations.
- Follow-up: the Review wave prompt and the implementation review step are under the same kind of independent review; their findings become sibling waves, not additions here.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-DEL-1 | do_now | no | completed | qa-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer, code-reviewer, qa-reviewer, architecture-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the first-draft independence predicate would have refused the second lane approval of every council round and failed this wave's own close, while the shape that motivated it is not decidable without a trust assumption; strongest-alternative: scope the audit to any earlier repair_start context and make the finding-then-approve shape visible in the ledger list view instead of refusing it, adopted; per-seat evidence in `readiness-review.md`)

## Dependencies

- External: none. `1ymzk` is closed (`4a8b8951`). `1ymzq` holds the single OPEN slot while implementing; this wave opens after it pauses or closes, and its retrieval receipts must not interleave with `1ymzq`'s.
- Intra-wave order is declared by the `Depends On:` lines in the Changes section: `1ypy4` tools, then `1yobp` seeds, then `1ypy5` surfaces.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 354 | 5,268,932 |
| implement | 159 | 2,020,707 |
| review | 107 | 3,358,240 |
| **Total** | **620** | **10,647,879** |

<!-- wave:context-efficiency-state {"generation":573,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":159,"content_source_credit":2371070,"derived_artifact_credit":1172,"direct_net":2020707,"estimated_tokens_saved":2020707,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8884,"response_debit":347344,"source_credit_count":77,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4693},"plan":{"calls":354,"content_source_credit":5775922,"derived_artifact_credit":9446,"direct_net":5268932,"estimated_tokens_saved":5268932,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17352,"response_debit":704980,"source_credit_count":322,"source_credit_drop_count":0,"structural_source_credit":191060,"workflow_prompt_credit":14836},"review":{"calls":107,"content_source_credit":3520484,"derived_artifact_credit":2354,"direct_net":3358240,"estimated_tokens_saved":3358240,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13365,"response_debit":153549,"source_credit_count":79,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":620,"content_source_credit":11667476,"derived_artifact_credit":12972,"direct_net":10647879,"estimated_tokens_saved":10647879,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":39601,"response_debit":1205873,"source_credit_count":478,"source_credit_drop_count":0,"structural_source_credit":191060,"workflow_prompt_credit":21845},"wave_id":"1ypy6 implement-prompt-efficiency"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 55 | 0 | 18 | 38,274,685 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":18,"estimated_exploration_avoided":38274685,"surfaced_events":55} -->
<!-- wave:exploration-avoided end -->
