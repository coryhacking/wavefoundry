# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-18
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2136r agent-guidance-best-practices`
Title: Agent Guidance Best Practices

## Objective

Adopt four Claude Code best-practice items: the run contract forbids suppressing a failing check and asks for evidence behind pass or fail claims, operator-owned skills become manual-only on Claude, the root bridge tells Claude what to keep through compaction, and rendered Claude settings turn off the commit co-author trailer.

## Changes

Change ID: `2136k-enh run-contract-no-suppression-and-evidence`
Change Status: `implemented`

Change ID: `2136l-enh claude-operator-owned-skills-manual-only`
Change Status: `implemented`

Change ID: `2136m-enh claude-compaction-guidance`
Change Status: `implemented`

Change ID: `2136n-enh claude-commit-attribution-hook`
Change Status: `implemented`

## Participants

- Coordinator: Claude Code session coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-10-19

## Wave Summary

Added failure-suppression and verification-evidence guidance, made four operator-owned skills manual-only on the supported host, preserved authorization and verification context through compaction, and used the host setting to suppress automatic commit attribution. Existing operator authority and other hosts remain unchanged.

Four changes delivered; all ACs completed. Fresh-host observations verified skill routing and attribution behavior; prose delivery does not establish universal agent adherence. No in-wave deferrals.

## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

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

## Review Checkpoints

- 2026-10-18: Continuation inspected current source/settings/bridge diffs and existing delivery evidence. `wf_review_wave(phase="implementation")` confirms current code, QA, docs-contract and council-delivery approvals, no findings, with only operator signoff pending. Existing focused skill/bridge/settings tests and negative controls are recorded in the member Progress Logs. Fresh-host dogfood recorded no commit trailer with `attribution.commit=""`, versus a co-author trailer without the setting; a fresh host routed close through the prompt while excluding the four skills from automatic invocation. These are observed host checks, not a claim that manual-only skills prevent direct tool use.
- Qualification: settled 2136r run recorded 11,907 tests OK; after 2136s retargeting, the combined tree passed 11,906 tests across 200 files (12 skips). The latter receipt matched current framework inputs `354ad5ae04910e38dd37382cdf158d01d6fdb60a32d599a92481acb430a89369` before 2124l source implementation. Reuse final combined qualification once 2124l settles. Wave remains paused; no operator approval, closure, commit or push is inferred from the request to finish implementation and validation.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 15 | 3,980 |
| implement | 288 | 4,744,829 |
| review | 8 | 19,117 |
| **Total** | **311** | **4,767,926** |

<!-- wave:context-efficiency-state {"generation":327,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":288,"content_source_credit":5439211,"derived_artifact_credit":0,"direct_net":4744829,"estimated_tokens_saved":4744829,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9896,"response_debit":688244,"source_credit_count":219,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3758},"plan":{"calls":15,"content_source_credit":23911,"derived_artifact_credit":1436,"direct_net":3980,"estimated_tokens_saved":3980,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4097,"response_debit":21538,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4268},"review":{"calls":8,"content_source_credit":31616,"derived_artifact_credit":1108,"direct_net":19117,"estimated_tokens_saved":19117,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1823,"response_debit":14998,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3214}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":311,"content_source_credit":5494738,"derived_artifact_credit":2544,"direct_net":4767926,"estimated_tokens_saved":4767926,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15816,"response_debit":724780,"source_credit_count":241,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11240},"wave_id":"2136r agent-guidance-best-practices"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 30 | 0 | 22 | 13,954,742 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":22,"estimated_exploration_avoided":13954742,"surfaced_events":30} -->
<!-- wave:exploration-avoided end -->
- 2026-10-18: Final canonical qualification: `/Users/coryhacking/.wavefoundry/venv/bin/python .wavefoundry/framework/scripts/run_tests.py --no-cache` passed 11,911 tests across 200 files in 764.084 seconds, with 12 reported skips. Green receipt matches current framework inputs `de1645bfd5b392a8a9bb5b71d98df4fc5ddd8e05f5e0b46a597447420aa722cd`. Full `wf_validate_docs` passed with zero errors/warnings and `git diff --check` is clean. The earlier sandboxed attempt was interrupted after a localhost-bind refusal; it is not qualification evidence, and no tests or thresholds were changed to bypass it. This one completed run qualifies all four settled waves; no duplicate full profiles were added. Every admitted AC/task is complete and required delivery approvals are current; only operator approval/closure remains. Both edit gates are closed. No commit, push or package was made in this continuation.

- 2026-10-19: Operator explicitly instructed: "go ahead and close and commit these changes." This authorizes closure of 2124l, 2136j, 2136r and 2136s and a commit of their reviewed changes, without push or closure of concurrent wave 212yk. Current green qualification covers 11,914 tests with framework inputs `e042b2c77fa84c9194b8d7e768ff03dcc605947106afed1b161dcf4b39668463`; routine closure recording reuses it. Retrospective/memory checkpoint: `memory_propose(mode="dry_run")` returned no candidates. The useful lessons (intent is distinct from implementation proof; preserve imperative sentences during reference trimming; source and rendered pointers must agree) already live in the canonical guidance and these records, so no duplicate memory was created. Cleanup retains only canonical wave/change/ledger files and the explicitly required, unique 2136s rule census; temporary reports and probes remain outside the repository. Concurrent setup-readiness work is excluded from this closure and commit.
