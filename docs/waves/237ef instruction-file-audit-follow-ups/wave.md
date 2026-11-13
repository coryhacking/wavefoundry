# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `237ef instruction-file-audit-follow-ups`
Title: Instruction File Audit Follow Ups

## Objective

Agents in every Wavefoundry project may call `code_*` retrieval tools directly and are asked whether a question needs Guru instead of being told to stop; they ask the operator only when intent is genuinely unclear. Operators get a `wf-upgrade` checklist that uses the gate tools, without retired journal wording. Existing projects receive the changes on upgrade with their own additions preserved. In this repository, the MCP tool spec becomes the complete, test-enforced tool reference, replacing the duplicate tool list `AGENTS.md` loads every session. No lint, gate, hook or tool behavior changes.

## Changes

Change ID: `237eg-enh permit-direct-retrieval-and-trim-dated-instructions`
Change Status: `implemented`

Change ID: `237eh-enh tool-spec-as-the-enforced-tool-inventory`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (serial ownership of seeds 050, 160, 211 and the renderer constants)
- Requested review lanes: docs-contract-reviewer, code-reviewer, qa-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-12

## Wave Summary

Wave `237ef` (Instruction File Audit Follow Ups) delivered two changes: Permit Direct Retrieval And Trim Dated Instructions and Tool Spec As The Enforced Tool Inventory.

**Changes delivered:**

- **Permit Direct Retrieval And Trim Dated Instructions** (`237eg-enh permit-direct-retrieval-and-trim-dated-instructions`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: One change covering seeds, the two renderer constants, local carriers and upgrade delivery; Remove all wave and change ID references from `AGENTS.md` and seed 050, not only the three headings.
- **Tool Spec As The Enforced Tool Inventory** (`237eh-enh tool-spec-as-the-enforced-tool-inventory`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: Make the spec the enforced inventory and point `AGENTS.md` at it; An explicit Tool Index checked for exact equality with the registration, instead of detecting entries in prose (readiness primer repair).

## Watchpoints

- Watchpoint: Planned only. Prepare, implementation, closure, commit and release each need explicit operator direction. Seed edits need `seed_edit_allowed`; renderer edits need `framework_edit_allowed`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ACCURACY-RDY-1 | do_now | no | completed | qa-reviewer |
| CHANGELOG-DEL-1 | do_now | no | completed | docs-contract-reviewer |
| DEFBULLET-DEL-1 | dont_do_later | no | not_required | — |
| INDEXSUMMARY-DEL-1 | dont_do_later | no | not_required | — |
| MERGELIST-DEL-1 | do_now | no | completed | qa-reviewer |
| PARSER-DEL-1 | do_now | no | completed | code-reviewer |
| PARSER-DEL-2 | do_now | no | completed | code-reviewer |
| PARSER-DEL-3 | do_now | no | completed | code-reviewer |
| PARSER-DEL-4 | do_now | no | completed | code-reviewer |
| PARSER-DEL-5 | do_now | no | completed | code-reviewer |
| PARSER-DEL-6 | do_now | no | completed | code-reviewer |
| PARSER-DEL-7 | do_now | no | completed | code-reviewer |
| READER-RDY-1 | do_now | no | completed | docs-contract-reviewer |
| ROUTING-RDY-1 | do_now | no | completed | code-reviewer, qa-reviewer |
| SIGSCOPE-RDY-1 | do_now | no | completed | qa-reviewer |
| SKIPPATH-DEL-1 | dont_do_later | no | not_required | — |
| SPECBEHAVIOR-DEL-1 | do_now | no | completed | code-reviewer |
| SUBAGENT-DEL-1 | do_now | no | completed | code-reviewer, docs-contract-reviewer |
| SUBAGENT-DEL-2 | do_now | no | completed | code-reviewer |
| UPGRADECHECK-DEL-1 | do_now | no | completed | docs-contract-reviewer |

*Machine review state — 20 findings; current: do_now 17, maybe_later 0, dont_do_later 3, not_issue 0*
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

- 2026-11-12: Operator decision after the focused verification round left SIGSCOPE-RDY-1 (raised by QA, corroborated by code) open: authorize one further bounded repair of change 237eh, scoping the exact both-ways parameter check to each tool's main signature, checking other call forms for unknown parameters only, naming the three measured mismatches and correcting the counts; followed by one focused verification by QA and code and re-recorded approvals from every required lane and the council.
- 2026-11-12: Intent outcome (coordinator draft, for independent QA check): partial pending delivery review. 237eg achieves its shipped-text intent. Every routing surface in seeds 050 and 211, `AGENTS.md`, `docs/agents/guru.md` and the rendered Cursor rule, Guru subagent and `wf-guru` skill permits direct `code_*` calls and frames Guru as the answer to how-or-why mechanism questions. Principle 1 asks only when intent is unclear, the `wf-upgrade` skill uses the gate tools, and seed 160 step 4 carries the change to existing projects. Evidence: `RoutingGuidanceTextTests`, failing on a `HEAD` copy and on two partial-fix mutants. Whether agents actually route fewer trivial lookups to Guru is a field observation this wave cannot measure. 237eh achieves completeness and drift enforcement: 92 index rows equal the live registration, 17 new entries exist, the 5 signature mismatches are fixed, `AGENTS.md` points to the index, and the index test and its 11 known-bad controls pass in three profiles. Its accuracy intent for the 17 new entries depends on the delivery code-reviewer's per-tool behavior cross-check (Requirement 4, AC-3), not yet run. Limitations: macOS only (text-only change, no platform-specific path); summaries truncate at the first sentence end, so a future description with an early abbreviation would be cut short.
- 2026-11-12: Intent outcome (after delivery review, incorporating QA's independent check): achieved for shipped and upgraded text, with field behavior unmeasured. 237eg: every routing surface, now including the rendered Claude Guru subagent description (SUBAGENT-DEL-1, which the first draft missed), permits direct `code_*` calls and keeps Guru for how-or-why mechanism questions; principle 1 asks only when intent is unclear; the `wf-upgrade` skill uses the gate tools. Seed 160 step 4 names the whole changed auto-Guru section (MERGELIST-DEL-1; a literal merge reproduces the delivered `AGENTS.md` section byte for byte), and step 6 tells upgraders to edit the subagent `description:` line the renderer keeps; that edit is an agent-applied manual step. 237eh: the Tool Index equals the live registration (92 tools), all 17 new entries are accurate against their handlers (code-reviewer cross-check; three corrected in delivery), the five signature mismatches are fixed, and the index test reports every real closing-paren deletion (85 of 85) after six delivery repair cycles (4 to 9) on its parser for seven findings. Seed 050's subagent template now carries the same description the renderer writes, so seed 160 step 6 names one target text (SUBAGENT-DEL-2). Accepted, not repaired: DEFBULLET-DEL-1 (19 definition-bullet tools are not parameter-checked, as Requirement 3.1 allows), SKIPPATH-DEL-1, INDEXSUMMARY-DEL-1. Whether agents route fewer lookups to Guru is a field observation; verified on macOS only, text-only change.
- 2026-11-12: Delivery council PASS, intent_fit establishes (artifact `.wavefoundry/work/237ef/council-delivery.md`). Seats: red-team (fixed primer, FAIL on the first delivery tree before repairs), docs-contract-reviewer (rotating, PASS after repair); required lanes code-reviewer and qa-reviewer, both PASS on the final tree. Material disagreement: red-team rated the definition-bullet parameter gap maybe_later, the ledger recorded dont_do_later (Requirement 3.1 exempts those bullets); the chair leans maybe_later, not blocking. Strongest remaining challenge: in upgraded projects the Claude Code fix relies on an agent editing the renderer-kept `description:` line, with no later drift check (accepted limitation). Strongest alternative: making that frontmatter key framework-owned in the renderer, rejected as a behavior change outside this wave. Chair notes for follow-up: the parser helper's cycle-5 and cycle-6 continuation layers are no longer load-bearing after the backtick rules, and the late parser cycles exceeded the measured real-spec risk.
- 2026-11-12: Operator decision after that verification measured 5 main-signature mismatches instead of 3 (QA and code): authorize a follow-up repair placing a complete main signature first for `wf_review_event`, `memory_consolidate` and `memory_reconcile` and restating AC-2's usage-example control as after the change, followed by a focused delta check by QA and code and the council synthesis.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 66 | 801,078 |
| implement | 74 | 617,130 |
| review | 102 | 7,919,625 |
| **Total** | **242** | **9,337,833** |

<!-- wave:context-efficiency-state {"generation":237,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":74,"content_source_credit":646840,"derived_artifact_credit":0,"direct_net":617130,"estimated_tokens_saved":617130,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3203,"response_debit":32196,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5689},"plan":{"calls":66,"content_source_credit":1029438,"derived_artifact_credit":4936,"direct_net":801078,"estimated_tokens_saved":801078,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16167,"response_debit":226716,"source_credit_count":69,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9587},"review":{"calls":102,"content_source_credit":8190428,"derived_artifact_credit":1349,"direct_net":7919625,"estimated_tokens_saved":7919625,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":33918,"response_debit":244583,"source_credit_count":175,"source_credit_drop_count":0,"structural_source_credit":2573,"workflow_prompt_credit":3776}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":242,"content_source_credit":9866706,"derived_artifact_credit":6285,"direct_net":9337833,"estimated_tokens_saved":9337833,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":53288,"response_debit":503495,"source_credit_count":262,"source_credit_drop_count":0,"structural_source_credit":2573,"workflow_prompt_credit":19052},"wave_id":"237ef instruction-file-audit-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 3 | 7,865,746 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":7865746,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
