# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-02
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1u8r2 memory-consolidation-and-drift-parser`
Title: Memory Consolidation And Drift Parser

## Objective

Reduce long-term memory/index clutter through reviewed consolidation and retention, repair drift evaluation for space-containing framework paths, and make the memory-review workflow reusable across upgrades and future projects.

## Changes

Change ID: `1u8r1-enh memory-retention-archive-cleanup`
Change Status: `implemented`

Change ID: `1u91n-bug drift-diff-parser-drops-tab-terminated-paths`
Change Status: `implemented`

Change ID: `1u75c-enh memory-review-shortcut`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-08-03

## Wave Summary

Wave `1u8r2` (Memory Consolidation And Drift Parser) delivered 3 changes: Consolidate related memory, then archive only retired evidence, Drift Diff Parser Keeps Git's Tab Terminator on Space-Containing Paths, Killing Evaluation on Every Conforming Repo, and Review Memories Shortcut. Notable adjustments during implementation: Consolidate related memory, then archive only retired evidence: Expanded by operator direction: archive register must be compact and non-semantic; a reviewed retention decision must archive only history-worthy records and purge the rest.; Consolidate related memory, then archive only retired evidence: Field-ran `Review memories`: consolidated the exact runner-identity decision pair into `1uamr-mem runner-identity-capture-and-testing-contract`, then purged both non-historic superseded source bodies. Repaired protected consolidation so `eligibility_confirmed` reaches each source archive transaction.; Consolidate related memory, then archive only retired evidence: Upgrade feedback showed two newly added memory tools were re-registered server-side but not callable in the same Claude Code turn. Follow-up established that current reload output can label an active-loop `create_task(...)` as sent before completion and cannot prove client adoption; fold an honest dispatch-state and fresh-turn recovery contract into this change before delivery review.

**Changes delivered:**

- **Consolidate related memory, then archive only retired evidence** (`1u8r1-enh memory-retention-archive-cleanup`) — 11 ACs completed. Key decisions: Keep full archive bodies, but replace the per-record pointer directory with one searchable archive manifest.; Use the archive register only as an explicit lookup index; archive only reviewed history-worthy records and purge the rest.
- **Drift Diff Parser Keeps Git's Tab Terminator on Space-Containing Paths, Killing Evaluation on Every Conforming Repo** (`1u91n-bug drift-diff-parser-drops-tab-terminated-paths`) — 4 ACs completed. Key decisions: Fail closed on C-quoted `+++` targets.
- **Review Memories Shortcut** (`1u75c-enh memory-review-shortcut`) — 6 ACs completed. Key decisions: Canonical phrase is `Review memories`; `Memory review` is an alias.; Invocation is apply-oriented and explicitly authorizes eligible purge.
## Watchpoints

- Watchpoint: archive only history-worthy retired memories; purge low-value retired records after reviewed confirmation.
- Watchpoint: treat server re-registration and notification dispatch as distinct from client tool-schema adoption.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| current-receipt-retention-gaps | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, wave-council-readiness |
| final-readiness-contract-gaps | do_now | no | completed | docs-contract-reviewer, wave-council-readiness |
| legacy-pointer-upgrade-index-leak | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, wave-council-readiness |
| purge-disposition-not-repo-durable | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, wave-council-readiness |
| purge-register-publication-data-loss | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, wave-council-readiness, wave-council-delivery |
| reload-guidance-cross-surface-contradiction | do_now | no | completed | docs-contract-reviewer, release-reviewer, wave-council-readiness |
| upgrade-doc-constant-drift-created-by-pack | do_now | no | completed | release-reviewer, docs-contract-reviewer, wave-council-delivery |
| upgrade-doc-constant-snapshot-not-recovery-durable | do_now | no | completed | architecture-reviewer, qa-reviewer, code-reviewer, release-reviewer, docs-contract-reviewer, wave-council-delivery |

*Machine review state — 8 findings; current: do_now 8, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 133 | 2,972,573 |
| implement | 331 | 5,201,721 |
| review | 474 | 9,889,891 |
| **Total** | **938** | **18,064,185** |

<!-- wave:context-efficiency-state {"generation":971,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":331,"content_source_credit":5850894,"derived_artifact_credit":2551,"direct_net":5201721,"estimated_tokens_saved":5201721,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16360,"response_debit":636795,"source_credit_count":306,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":133,"content_source_credit":3167324,"derived_artifact_credit":1297,"direct_net":2972573,"estimated_tokens_saved":2972573,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4941,"response_debit":200619,"source_credit_count":72,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9512},"review":{"calls":474,"content_source_credit":10989657,"derived_artifact_credit":8915,"direct_net":9889891,"estimated_tokens_saved":9889891,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":60098,"response_debit":1049929,"source_credit_count":395,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":938,"content_source_credit":20007875,"derived_artifact_credit":12763,"direct_net":18064185,"estimated_tokens_saved":18064185,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":81399,"response_debit":1887343,"source_credit_count":773,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12289},"wave_id":"1u8r2 memory-consolidation-and-drift-parser"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 42 | 0 | 12 | 18,422,479 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":12,"estimated_exploration_avoided":18422479,"surfaced_events":42} -->
<!-- wave:exploration-avoided end -->
