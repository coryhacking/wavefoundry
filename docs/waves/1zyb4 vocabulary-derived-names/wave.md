# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zyb4 vocabulary-derived-names`
Title: Vocabulary Derived Names

## Objective

Let a distribution's vocabulary profile rename the generated lifecycle prompt and skill names (defaults unchanged, already-rendered files migrated), and write vocabulary-neutral council signoff keys while accepting the old keys forever when reading ledgers.

## Changes

Change ID: `1zxnw-enh vocabulary-derived-prompt-names`
Change Status: `implemented`

Change ID: `1zxnx-enh neutral-council-signoff-keys`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-07

## Wave Summary

Wave `1zyb4` (Vocabulary Derived Names) delivered two changes: Vocabulary-Derived Lifecycle Prompt and Skill Names and Neutral Council Signoff Keys. Notable adjustments during implementation: Vocabulary-Derived Lifecycle Prompt and Skill Names: Delivery repair DEL-1b: new `test_reverting_to_the_defaults_drops_the_record` renders under the profile, then twice under the defaults, asserting the prompts move back, `prompt_names` is removed from the manifest, and the second render writes nothing.; Vocabulary-Derived Lifecycle Prompt and Skill Names: Delivery repair DEL-1c: exclusive byte copies (both prompt moves, this change and 1zyc5, share `_write_review_carrier_text`) now go through `_write_bytes_atomic_exclusive`: a temporary file in the destination folder, then a hard link that refuses an existing target (Windows without hard links renames, which also refuses an existing target; other platforms without hard links fall back to the exclusive create), so an interruption never leaves a truncated target. New `test_a_locked_source_rolls_the_copy_back` (the source unlink raises as a locked Windows file does: copy removed, source kept, no `prompt_names`, tree byte-identical, rerun converges) and `AtomicPromptCopyTests` (interrupted copy leaves nothing; exact bytes; refusal with and without hard links).

**Changes delivered:**

- **Vocabulary-Derived Lifecycle Prompt and Skill Names** (`1zxnw-enh vocabulary-derived-prompt-names`) — 12 ACs completed. Key decisions: Explicit override map keyed by today's slug, with a fixed default table and an empty single-line override constant.; Only the eleven tier-named lifecycle prompts are mapped.
- **Neutral Council Signoff Keys** (`1zxnx-enh neutral-council-signoff-keys`) — 11 ACs completed. Key decisions: Rename the keys only; keep actor and role `wave-council`.; Canonicalize at comparison, render history as recorded.
## Watchpoints

- Watchpoint: last of five sequential waves; implemented on wave D's tree (1zxnu skill rendering).
- Follow-up: retire the old council keys as tool input in a later release; rename the wave-council role only if requested.
- Follow-up (implementation, 1zxnw): a fresh install under a prompt-name profile with a rename chain has no manifest `prompt_names` record, so a later render can conflict; record `prompt_names` when the manifest is first created. The reconcile scan reports retired shortcuts but not their aliases.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | pending | — |
| DEL-2 | do_now | no | pending | — |
| DEL-3 | do_now | no | pending | — |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 26 | 12,754 |
| implement | 13 | 29,894 |
| review | 11 | 72,370 |
| **Total** | **50** | **115,018** |

<!-- wave:context-efficiency-state {"generation":50,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":13,"content_source_credit":39247,"derived_artifact_credit":4683,"direct_net":29894,"estimated_tokens_saved":29894,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1547,"response_debit":12489,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":26,"content_source_credit":33849,"derived_artifact_credit":1578,"direct_net":12754,"estimated_tokens_saved":12754,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2224,"response_debit":26956,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6507},"review":{"calls":11,"content_source_credit":96954,"derived_artifact_credit":1271,"direct_net":72370,"estimated_tokens_saved":72370,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3397,"response_debit":24842,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":50,"content_source_credit":170050,"derived_artifact_credit":7532,"direct_net":115018,"estimated_tokens_saved":115018,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7168,"response_debit":64287,"source_credit_count":44,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8891},"wave_id":"1zyb4 vocabulary-derived-names"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
