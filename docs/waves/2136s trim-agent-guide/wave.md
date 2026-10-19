# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-18
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2136s trim-agent-guide`
Title: Trim Agent Guide

## Objective

Cut the always-loaded root AGENTS.md to at most 36,500 bytes by moving or deleting reference material that already lives in its destination docs, keeping every rule, and measure the whole startup reading set before and after.

## Changes

Change ID: `2136p-enh trim-always-loaded-agent-guide`
Change Status: `implemented`

## Participants

- Coordinator: Claude Code session coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-10-19

## Wave Summary

Reduced AGENTS.md from 46,932 to 36,374 bytes (22.50%) while preserving behavioral instructions and linking reference detail to existing documentation. Delivery review caught five removed instructions; all were restored, and fresh affected-lane verification cleared the finding.

One change delivered; all five ACs completed. The required rule census retains the unique baseline and dispositions; routine probes and reports remain temporary. This is a first startup-context reduction, not proof of improved agent adherence. No in-wave deferrals.

## Watchpoints

- Watchpoint: implement after waves 2136j and 2136r land: both edit `AGENTS.md` (2136l edits the skills paragraph). The rule census and the AC-1 baseline come from that post-2136r file.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-CODE-2136S-1 | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer, council-delivery |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 170 | 4,988,769 |
| implement | 36 | 128,462 |
| review | 16 | 1,001,030 |
| **Total** | **222** | **6,118,261** |

<!-- wave:context-efficiency-state {"generation":194,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":36,"content_source_credit":227651,"derived_artifact_credit":0,"direct_net":128462,"estimated_tokens_saved":128462,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":748,"response_debit":100727,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2286},"plan":{"calls":170,"content_source_credit":5404329,"derived_artifact_credit":3148,"direct_net":4988769,"estimated_tokens_saved":4988769,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":23811,"response_debit":402275,"source_credit_count":290,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7378},"review":{"calls":16,"content_source_credit":1018800,"derived_artifact_credit":0,"direct_net":1001030,"estimated_tokens_saved":1001030,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":509,"response_debit":20475,"source_credit_count":15,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":222,"content_source_credit":6650780,"derived_artifact_credit":3148,"direct_net":6118261,"estimated_tokens_saved":6118261,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25068,"response_debit":523477,"source_credit_count":323,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12878},"wave_id":"2136s trim-agent-guide"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 14 | 0 | 11 | 14,572,881 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":11,"estimated_exploration_avoided":14572881,"surfaced_events":14} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- 2026-10-18: Independent delivery council ran isolated lightweight red-team primer, fixed architecture/security/QA/reality, rotating docs-contract and chair synthesis. Code shared the QA context; the other seats were separate, shared the primer intentionally, and explicitly weighed restoring instructions rather than weakening the preservation contract. Anonymous merits were synthesized before roles were reattached; falsification and red-team closing reconciliation retained one finding. QA-CODE-2136S-1 blocks code, QA and docs-contract: five imperative sentences were absent despite Requirement 1. No security authority expansion was found. Initial full docs validation passed; focused unchanged assertion controls and three mutants behaved as expected. The existing 11,906-test run was read as separate evidence, not rerun by the council.
- Implementer recorded repair_start before edits, restored the five original sentences verbatim and shortened descriptive pointers only. Guide is 36,374 bytes; census and startup counts were corrected, map regenerated. Original requirements, 36,500-byte ceiling and readiness receipt are unchanged. Fresh affected-lane reverification is pending; no operator approval or closure is inferred.

- Fresh focused review completed: independent code/QA context and independent docs/focused-chair context verified current source, baseline coverage, destination labels and mutation controls. Every affected lane cleared QA-CODE-2136S-1; all required delivery lanes and council approved. Original full council was not repeated because no scope or authority changed. Code/QA remits shared one worker; docs/chair remits shared another, neither implemented the repair. The required rule census is retained as the unique baseline/disposition proof under Requirement 5; temporary reports and probes remain outside the repository. Final combined suite and full docs validation remain pending; only operator approval may authorize closure.

- 2026-10-18: Final canonical qualification: `/Users/coryhacking/.wavefoundry/venv/bin/python .wavefoundry/framework/scripts/run_tests.py --no-cache` passed 11,911 tests across 200 files in 764.084 seconds, with 12 reported skips. Green receipt matches current framework inputs `de1645bfd5b392a8a9bb5b71d98df4fc5ddd8e05f5e0b46a597447420aa722cd`. Full `wf_validate_docs` passed with zero errors/warnings and `git diff --check` is clean. The earlier sandboxed attempt was interrupted after a localhost-bind refusal; it is not qualification evidence, and no tests or thresholds were changed to bypass it. This one completed run qualifies all four settled waves; no duplicate full profiles were added. Every admitted AC/task is complete and required delivery approvals are current; only operator approval/closure remains. Both edit gates are closed. No commit, push or package was made in this continuation.

- 2026-10-19: Operator explicitly instructed: "go ahead and close and commit these changes." This authorizes closure of 2124l, 2136j, 2136r and 2136s and a commit of their reviewed changes, without push or closure of concurrent wave 212yk. Current green qualification covers 11,914 tests with framework inputs `e042b2c77fa84c9194b8d7e768ff03dcc605947106afed1b161dcf4b39668463`; routine closure recording reuses it. Retrospective/memory checkpoint: `memory_propose(mode="dry_run")` returned no candidates. The useful lessons (intent is distinct from implementation proof; preserve imperative sentences during reference trimming; source and rendered pointers must agree) already live in the canonical guidance and these records, so no duplicate memory was created. Cleanup retains only canonical wave/change/ledger files and the explicitly required, unique 2136s rule census; temporary reports and probes remain outside the repository. Concurrent setup-readiness work is excluded from this closure and commit.
