# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1w047 review-plan-naming`
Title: Review Plan Naming

## Objective

Rename the optional pre-implementation plan review to the clearer **Review plan** / `wf-review-plan` identity across canonical seeds, prompts, rendered skills, upgrade behavior, and public carriers. Preserve use before or after admission, preserve the legacy natural-language phrases as aliases, retire the old skill name, and keep **Review wave** / `wf-review-wave` semantically unchanged.

## Changes

Change ID: `1w046-enh review-plan-command-rename`
Change Status: `implemented`



## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-08-22

## Wave Summary

Wave `1w047` (Review Plan Naming) delivered one change: Rename Plan Review to `wf-review-plan`. Notable adjustments during implementation: Rename Plan Review to `wf-review-plan`: Readiness cycle 2 expanded the recognized legacy migration from three identity lines to seven exact contract lines and moved it before both skill rendering and baseline materialization, preventing a renamed prompt from retaining pre-admission-only semantics.; Rename Plan Review to `wf-review-plan`: **Reflect:** Cycle 3 replaced substring migration with exact logical-line recognition while preserving physical line endings, added a seven-field embedded-prefix/suffix rejection matrix, updated the canonical council registry/body to make **Review plan** primary with both aliases secondary, regenerated all three host skills, and extended the live routing regression to cover the council consumer.; Rename Plan Review to `wf-review-plan`: **Reflect:** Cycle 3 now preflights every lexical component of active skill roots, stale cleanup paths, and generated skill targets before any mutation, with declared-root and same-root-parent regressions added to the existing outside-root/final-file matrix. The README paragraph was moved below the complete skills table without changing its contract text.

**Changes delivered:**

- **Rename Plan Review to `wf-review-plan`** (`1w046-enh review-plan-command-rename`) — 7 ACs completed. Key decisions: Use **Review plan** and `wf-review-plan` as the primary public identity.; Keep **Interrogate this plan** and **Stress-test this plan** as natural-language aliases, but remove the `wf-interrogate-plan` skill.
## Watchpoints

- Stage Gate: no framework source, seed, renderer, upgrade, or test edits until Prepare records readiness for this wave.
- Downstream lifecycle prompts are project-owned after materialization; run the fresh-code pre-baseline recognized-old/customized-old/new/both/neither migration matrix and make customized-old or dual-file conflicts non-successful without altering either file.
- Remove only the generated `wf-interrogate-plan/SKILL.md` in all three hosts and remove an empty parent, but retain **Interrogate this plan** and **Stress-test this plan** as natural-language aliases and preserve unrelated sibling content.
- Preserve closed wave archives, earlier changelog entries, and retained benchmark results; classify living stale references rather than applying a blind repository-wide replacement.
- `wf-review-wave`, typed review evidence, and lifecycle gates are protected and remain behaviorally unchanged.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-READY-OLD-RUNNER-001 | dont_do_later | no | not_required | architecture-reviewer, wave-council-readiness |
| CODE-DEL-1 | do_now | no | completed | code-reviewer |
| FIELD-DOWNSTREAM-LEGACY-PROMPT-001 | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer |
| PREP-AGENT-CARRIER-EXISTENCE-006 | do_now | no | completed | wave-council-readiness, code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer |
| PREP-BENCHMARK-PROVENANCE-004 | do_now | no | completed | wave-council-readiness, release-reviewer, qa-reviewer, code-reviewer |
| PREP-IMPLEMENTATION-MAP-002 | do_now | no | completed | wave-council-readiness, code-reviewer, docs-contract-reviewer, qa-reviewer, architecture-reviewer, release-reviewer |
| PREP-MIGRATED-PROMPT-SEMANTICS-005 | do_now | no | completed | wave-council-readiness, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer |
| PREP-PLAN-SEMANTICS-001 | do_now | no | completed | wave-council-readiness, code-reviewer, docs-contract-reviewer |
| PREP-QA-FALSIFIABILITY-003 | do_now | no | completed | wave-council-readiness, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer |
| PREP-TECHDOCS-EXCLUDE-POLARITY-007 | do_now | no | completed | wave-council-readiness, qa-reviewer, docs-contract-reviewer, release-reviewer |
| PREP-UPGRADE-PRUNE-FAILURE-SNAPSHOT-007 | do_now | no | completed | wave-council-readiness, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer |
| QA-DEL-1 | do_now | no | completed | qa-reviewer |
| QA-DEL-2 | do_now | no | completed | qa-reviewer |

*Machine review state — 13 findings; current: do_now 12, maybe_later 0, dont_do_later 1, not_issue 0*
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

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: lexical no-symlink preflight and the prompt move intentionally cover a local non-concurrent renderer, not an adversarial post-preflight filesystem path swap; strongest-alternative: use descriptor-anchored no-follow traversal/atomic exchange, or retain the old prompt path behind the new skill as a compatibility shim; resolution: red-team favored documenting the concurrency limit, while docs-contract rejected the compatibility shim because it preserves split vocabulary and judged descriptor plumbing disproportionate to the local renderer boundary; both seats agree the pre-mutation all-path preflight, five containment polarities, exact seven-line fail-closed migration, single new skill, supported phrase aliases, Review wave authority boundary, terminal repair chains, zero living retired-reference census, and frozen provenance meet the objective with no unresolved finding.)

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 406 | 3,477,203 |
| implement | 85 | 1,327,408 |
| review | 1,302 | 22,628,962 |
| **Total** | **1,793** | **27,433,573** |

<!-- wave:context-efficiency-state {"generation":1598,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":85,"content_source_credit":1414052,"derived_artifact_credit":0,"direct_net":1327408,"estimated_tokens_saved":1327408,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3688,"response_debit":88724,"source_credit_count":88,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5768},"plan":{"calls":406,"content_source_credit":4878669,"derived_artifact_credit":2032,"direct_net":3477203,"estimated_tokens_saved":3477203,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":47078,"response_debit":1368686,"source_credit_count":505,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12266},"review":{"calls":1302,"content_source_credit":27338779,"derived_artifact_credit":9580,"direct_net":22628962,"estimated_tokens_saved":22628962,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":173082,"response_debit":4549889,"source_credit_count":1081,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3574}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1793,"content_source_credit":33631500,"derived_artifact_credit":11612,"direct_net":27433573,"estimated_tokens_saved":27433573,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":223848,"response_debit":6007299,"source_credit_count":1674,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":21608},"wave_id":"1w047 review-plan-naming"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 165 | 0 | 21 | 110,443,705 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":21,"estimated_exploration_avoided":110443705,"surfaced_events":165} -->
<!-- wave:exploration-avoided end -->
