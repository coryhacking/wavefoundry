# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uhcb review-cycle-churn`
Title: Review Cycle Churn

## Objective

Remove the false approval invalidation caused by repair tracking. Today the Progress Log row that `AGENTS.md` requires of every repairer is digested into the review-policy receipt, so recording a repair supersedes the receipt and lapses every recorded approval, including lanes that raised no finding. Excluding that one section from the digest makes a trivial finding cost a trivial repair instead of a full re-record of the signoff roster. Legitimate re-review is untouched and must stay that way: when the plan or the implementation actually changes, approvals still lapse and lanes still run again.

## Changes

Change ID: `1ugk9-bug progress-log-appends-lapse-unrelated-approvals`
Change Status: `implemented`

## Participants

- Coordinator: session agent (Claude Code)
- Write-owning roles: implementer (fix workstream)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-08-05

## Wave Summary

Wave `1uhcb` (Review Cycle Churn) delivered one change: Logging a Repair Lapses the Approvals of Everything the Repair Did Not Touch.

**Changes delivered:**

- **Logging a Repair Lapses the Approvals of Everything the Repair Did Not Touch** (`1ugk9-bug progress-log-appends-lapse-unrelated-approvals`) — 10 ACs completed. Key decisions: Exclude progress-tracking sections from the digest rather than adding a finding-severity class or a cycle cap; Keep lane selection out of this change
## Watchpoints

- Blocking: exactly ONE section is excluded, `## Progress Log`. An independent review recommended narrowing from the original two and it is adopted: `## Session Handoff` stays digested, because no validator references it, roughly thirty change docs already deviate from its supposed fixed-pointer invariant, and it is not the observed source of repair-tracking churn (the corpus gap proves the invariant is broken; it does NOT prove nobody edits the section, and an earlier draft overreached by claiming that). AC-3a pins that editing Session Handoff still moves the digest, so the boundary cannot widen silently.
- Watchpoint: the exclusion is HASH-ONLY. The section stays in the file. The Progress Log has a real production reader (`_retrieval_posture_gap` greps the doc for `Gapfill:` at `server_impl.py:15934`) and a test must prove it still clears.
- Blocking: the seed passage must carry BOTH the stop condition and narrate-not-amend. Without the second, the digest exclusion opens a real hole, because this repo announces scope changes in Progress Log rows today (six examples in Requirement 2b, including a hard-break envelope change).
- Watchpoint: the evaluator bump is a LABELING choice, not the mechanism. The digest moves either way and nothing branches on the value. Do not revert the bump expecting the churn to stop.
- Watchpoint: three carriers move together on the bump: the constant, its deliberate boundary pin in `test_review_policy.py:343`, and a new v2-to-v3 case shaped like `test_server_tools.py:27913`. Update the pin, never delete it.
- Watchpoint: one-time re-Prepare for readied and open waves at upgrade time, disclosed in the CHANGELOG. Closed waves are untouched. This is not the config-migration path, so 1uf69's no-op guard does not apply. No compatibility shim.
- Watchpoint: this change is scoped to ONE review pass. Its own Requirement 6 stop condition applies to itself: after the delivery pass, only a correctness or contract defect opens another cycle.
- Note: this wave's own roster demonstrates the deferred defect three times over, and the record is kept HERE rather than in the change doc precisely because `wave.md` bytes are not digested, so writing it down cannot inflate the roster again.
  1. The release lane fired on `risk trigger: upgrade_wavefoundry.py, build_pack.py`. The change touches neither; the plan quotes those filenames as evidence for the follow-up.
  2. The code lane's reasons include `.js` although nothing here involves JavaScript, because `.js` is a substring of `events.jsonl`, which the plan names repeatedly as the review authority.
  3. Folding the council's census findings escalated the roster from three lanes to five. The census had concluded that `docs/architecture/` and `docs/specs/` need NO correction, and writing that conclusion down is what required an architecture-reviewer and a docs-contract-reviewer. **Reporting a surface as clean recruits a reviewer for it.**
  All three left uncorrected on purpose. Gaming the evaluator by deleting load-bearing evidence from a plan would be the wrong fix, and the right fix belongs to the deferred follow-up. Treat this list as that follow-up's specimen set.
- Blocking: Requirement 8 closes a FOURTH churn instance this wave caught live, and it is the one Requirement 1 cannot fix. Filling the Prepare-owned AC Priority table superseded receipt `511e88f7` and lapsed the readiness approval recorded moments earlier, forcing a re-record under `38a14e80`. The remedy is ordering, not exclusion: AC Priority and the Tasks list are requirement-bearing and must stay digested, so they get populated BEFORE the council runs. Three carriers: the scaffold placeholder at `server_impl.py:16745`, `docs/plans/plan-template.md:60`, and the ordering rule in `seeds/170-plan-feature.prompt.md:80`. Leave the `ac_priority_unpopulated` check in place as the backstop and pin that it still fires. Checkbox STATE stays deferred and must not be bundled in.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-05: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: red-team disproved the plan's safety argument as written by censusing real change docs and finding that this repository ANNOUNCES scope changes in Progress Log rows as sanctioned practice, six examples including `12as6-enh:276`'s hard-break envelope change and both scope extensions in the wave released the same day, so excluding the section from the digest would have let a scope expansion recorded only there stop lapsing approvals; folded by promoting narrate-not-amend from an unstated assumption to a stated seed rule alongside the stop condition, and by reframing the Risks row away from the adversarial smuggling case it had wrongly assumed. Red-team also found the Progress Log has a production reader the plan never mentioned and that the plan nowhere said the exclusion is hash-only. Docs-contract ran the census the plan had deferred and found the sole carrier is a memory record rather than a doc, yielding the scope lesson that censuses must include `docs/agents/memory/`; strongest-alternative: exclude the Session Handoff pointer only and leave the Progress Log digested, which preserves the current safety property with no new convention to enforce; rejected because the Progress Log append is the mandated act that drives the loop, so that option fixes nothing. Clean on the remainder: nothing branches on `evaluator_version`, no other production reader of Progress Log content, and no architecture or spec surface asserts that any change-doc edit supersedes the receipt. One pass, coordinator-run on read-only MCP retrieval during an Agent-tool outage, proportionate to a single-section change and consistent with the stop condition this wave proposes)

- **Independent plan review [independent] — 2026-08-05: RESOLVED, appropriately scoped** (reviewer independent of both the author and the council; opened as PROCEED-after-narrowing, and on re-reading the narrowed plan the reviewer confirmed their only substantive concern resolved and the boundary correct: Progress Log excluded as the required repair-tracking surface and proven source of false invalidation, Session Handoff left load-bearing with an explicit regression pin against widening the exception, and real scope, requirement, AC, task, and implementation changes still invalidating approvals. The reviewer specifically endorsed the corpus count as making the Session Handoff decision strong, since the assumption was not merely unenforced but already false in practice, and endorsed the 1uhfy counterexample for anchoring this as fewer re-recordings when nothing reviewable changed rather than fewer reviews. Full detail of the two recommendations and their verification below; endorsed the core fix as justified and appropriately narrow, and confirmed the mechanism at `gardener_metadata.py:48`. Contributed an analysis the plan had not used: 1uhfy's 27 review records and six readiness approvals were mostly LEGITIMATE, earned by three real scope expansions, which independently confirms the fix is correctly scoped and that narrate-not-amend is load-bearing, since those expansions were announced in Progress Log rows. Two recommendations, both ADOPTED: (1) drop the `## Session Handoff` exclusion and narrow to the Progress Log only, on the grounds that it has no demonstrated churn benefit, no validator enforces it as a fixed pointer, and a second exception carries a weaker safety case. Verified rather than accepted, and the evidence is stronger than the reviewer had: zero references to the section anywhere in `wave_lint_lib`, and the corpus already carries about 710 headings against about 678 canonical pointer sentences, so roughly thirty docs deviate today. (2) restate the objective as removing false approval invalidation rather than stopping the review loop, because legitimate re-review still occurs whenever the plan or implementation genuinely changes. Requirement 2 now records the non-exclusion as a decision, AC-3a pins that Session Handoff edits still move the digest, and the objective and problem statement are restated)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| crlf-change-doc-bypasses-progress-log-exclusion | do_now | no | completed | — |
| false-shipped-claims-and-unpinned-boundaries | do_now | no | completed | — |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 90 | 3,873,807 |
| implement | 80 | 1,787,656 |
| review | 112 | 3,693,274 |
| **Total** | **282** | **9,354,737** |

<!-- wave:context-efficiency-state {"generation":222,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":80,"content_source_credit":1996475,"derived_artifact_credit":267,"direct_net":1787656,"estimated_tokens_saved":1787656,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3213,"response_debit":207304,"source_credit_count":87,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":90,"content_source_credit":4013763,"derived_artifact_credit":3865,"direct_net":3873807,"estimated_tokens_saved":3873807,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9978,"response_debit":149502,"source_credit_count":175,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15659},"review":{"calls":112,"content_source_credit":3901610,"derived_artifact_credit":3904,"direct_net":3693274,"estimated_tokens_saved":3693274,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":28158,"response_debit":185428,"source_credit_count":131,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":282,"content_source_credit":9911848,"derived_artifact_credit":8036,"direct_net":9354737,"estimated_tokens_saved":9354737,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":41349,"response_debit":542234,"source_credit_count":393,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":18436},"wave_id":"1uhcb review-cycle-churn"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 16 | 0 | 7 | 8,105,086 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":8105086,"surfaced_events":16} -->
<!-- wave:exploration-avoided end -->
