# Wave Record

Owner: Engineering
Status: implementing
Last verified: 2026-11-24
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `24buu memory-revalidation-upgrade-delivery`
Title: Memory Revalidation Upgrade Delivery

## Objective

Maintainers who upgrade a target repository to 1.52.0 learn how many of its memory records need revalidation, and its agents follow the new keep rule in Review memories and Close wave. Upgrade still never curates records. Existing installations also keep the renamed spec tools after upgrading, because upgrade migrates their repository permission rules and records the review. Track 5 of arc `244cm-arc memory-quality`, plus the spec-tool permission fix for the same release.

## Changes

Spec ID: `24but-enh deliver-memory-revalidation-through-upgrade`
Spec Status: `implemented`

Spec ID: `24ax3-enh migrate-spec-tool-permissions-during-upgrade`
Spec Status: `implemented`

Spec ID: `24bn7-bug release-zip-entry-missing-contained-files`
Spec Status: `implemented`

Spec ID: `24bn8-enh replace-unedited-lifecycle-prompts-during-upgrade`
Spec Status: `implemented`

Spec ID: `24bn9-enh cli-upgrade-runs-cleanup`
Spec Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (one at a time; all five specs share upgrade_wavefoundry.py or seed 160)
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

## Wave Summary

Deliver the 249ar keep rule and revalidation signals through upgrade: read-only revalidation counts in `memory_brief`, and seed 160 guidance that merges the keep rule into existing prompts and recommends Review memories on unresolved or churned targets. Also migrate spec-tool permission rules inside the checkout during upgrade, recommend user-level changes without making them, and record the review so the five spec tools stay available. Fix the release zip's direct entry (`24bn7`) and have upgrade replace unedited lifecycle prompts and templates (`24bn8`), and have the CLI upgrade run cleanup itself (`24bn9`), from the 1.51.0 to 1.52.0 upgrade rehearsal.

## Watchpoints

- Watchpoint: wave `248o5` (closed and committed in `cbc69fb8`) last edited seed 160, `memory_handlers.py` and the tool-surface contract; reread them before editing.
- Follow-up: run Review memories (arc 244cm item 7) separately; this wave changes no record.
- Watchpoint: before delivery review, rerun the 1.51.0 to 1.52.0 upgrade rehearsal (`.wavefoundry/work/24buu/upgrade-rehearsal.md`) on the implemented tree for two hops: 1.51.0 to the 1.52.0 candidate (CLI and MCP `wf_upgrade` paths) and that candidate to a later candidate (where `24bn9` takes effect), and record each remaining intervention.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| AR-1 | do_now | no | completed | architecture-reviewer |
| AR-2 | do_now | no | completed | architecture-reviewer |
| AR-3 | do_now | no | completed | architecture-reviewer |
| ARCH-D1 | do_now | no | completed | architecture-reviewer |
| CR-1 | do_now | no | completed | code-reviewer |
| CR-2 | do_now | no | completed | code-reviewer |
| CR-D1 | do_now | no | completed | code-reviewer |
| DC-1 | do_now | no | completed | docs-contract-reviewer |
| DC-2 | do_now | no | completed | docs-contract-reviewer |
| DC-3 | do_now | no | completed | docs-contract-reviewer |
| DC-4 | do_now | no | completed | — |
| DOC-D1 | do_now | no | completed | docs-contract-reviewer |
| QA-1 | do_now | no | completed | qa-reviewer |
| QA-2 | do_now | no | completed | qa-reviewer |
| QA-3 | do_now | no | completed | qa-reviewer |
| QA-4 | do_now | no | completed | qa-reviewer |
| QA-5 | do_now | no | completed | qa-reviewer |
| QA-6 | do_now | no | completed | qa-reviewer |
| QA-7 | do_now | no | completed | — |
| SEC-1 | do_now | no | completed | security-reviewer |

*Machine review state — 20 findings; current: do_now 20, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| release-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| security-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | withheld | repaired findings require fresh approval: DC-1, DC-2, SEC-1, DC-3, CR-1, QA-1, AR-1, CR-2 (+10 more; see events.jsonl) | record a fresh independent approval for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-24: Intent outcome: Achieved on the offline Apple Silicon upgrade fixture. The 1.53.0 test build requested by the operator delivers the behavior originally planned for 1.52.0. A fresh MCP session reported the existing active memory and its revalidation counts after upgrade. The prompt renderer delivered the keep rule, preserved the verification date and removed retired tool references. All five stock spec routes appeared and the fixture retained its local grants and deny rule. The original memory and review ledger kept their bytes. The tests also cover edited prompts and unreadable or externally constrained policies.

Two-hop rehearsal: starting at 1.51.0, the direct ZIP, installed CLI and live MCP each applied 1.53.0+q5u0 and then 1.53.0+q5u1. Six post-upgrade inspections passed all 108 checks, including setup and documentation validation, and each hop produced one completion summary. The direct ZIP completed cleanup on both hops. The installed 1.51.0 CLI required one explicit cleanup on the first hop. MCP used explicit cleanup on both. When discovery was unavailable, the indexer refused an implicit conversion from int8 to full precision. Selecting the original CPU provider allowed the offline upgrades to proceed. The rehearsal used a Phase 1 fixture with sufficient project docs for validation. Native Windows, Linux and a complete Phase 2 installation remain outside this rehearsal.

Delivery repairs: the real index guard writes a record even when no host stop is required. Automatic cleanup now recognizes that validated decision and preserves genuinely pending checkpoints. If checkpoint publication fails during prompt replacement, retry finishes the exact intended bytes, restores generated guidance and preserves later operator edits. The architecture docs distinguish proven upgrade replacement from ordinary missing-only rendering. The upgrade guide identifies external host policies that Wavefoundry cannot inspect.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 74 | 1,409,046 |
| implement | 104 | 251,367 |
| review | 227 | 4,309,746 |
| **Total** | **405** | **5,970,159** |

<!-- wave:context-efficiency-state {"generation":400,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":104,"content_source_credit":267906,"derived_artifact_credit":0,"direct_net":251367,"estimated_tokens_saved":251367,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3033,"response_debit":24341,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10835},"plan":{"calls":74,"content_source_credit":1911547,"derived_artifact_credit":2169,"direct_net":1409046,"estimated_tokens_saved":1409046,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":43502,"response_debit":467466,"source_credit_count":106,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"review":{"calls":227,"content_source_credit":4788108,"derived_artifact_credit":6626,"direct_net":4309746,"estimated_tokens_saved":4309746,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":36277,"response_debit":448711,"source_credit_count":132,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":405,"content_source_credit":6967561,"derived_artifact_credit":8795,"direct_net":5970159,"estimated_tokens_saved":5970159,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":82812,"response_debit":940518,"source_credit_count":256,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":17133},"wave_id":"24buu memory-revalidation-upgrade-delivery"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 23 | 0 | 13 | 18,401,800 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":13,"estimated_exploration_avoided":18401800,"surfaced_events":23} -->
<!-- wave:exploration-avoided end -->
