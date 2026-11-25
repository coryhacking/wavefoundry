# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-25
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

Completed At: 2026-11-25

## Wave Summary

Wave `24buu` (Memory Revalidation Upgrade Delivery) delivered 5 changes: Deliver memory revalidation guidance and signals through upgrade, Migrate spec-tool permissions during upgrade, Release zip entry fails on a missing module, Replace unedited lifecycle prompts during upgrade, and CLI upgrade runs cleanup itself.

Intent outcome: Achieved on the offline Apple Silicon upgrade fixture. The 1.53.0 test build requested by the operator delivers the behavior originally planned for 1.52.0. A fresh MCP session reported the existing active memory and its revalidation counts after upgrade. The prompt renderer delivered the keep rule, preserved the verification date and removed retired tool references. All five stock spec routes appeared and the fixture retained its local grants and deny rule. The original memory and review ledger kept their bytes. The tests also cover edited prompts and unreadable or externally constrained policies.

**Changes delivered:**

- **Deliver memory revalidation guidance and signals through upgrade** (`24but-enh deliver-memory-revalidation-through-upgrade`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6 and AC-7 completed. Key decisions: Plan this as its own change in arc 244cm and release 1.52.0 after it; Selected: read-only counts in `memory_brief` plus seed 160 guidance. Efficacy: replaying this repository, the brief would report 7 unresolved and 98 churned, and the new rule would recommend Review memories where today's rule (174 active, cap 50) also fires; for a project under the cap the old rule stays silent and the new one fires. It advises only: the upgrade summary is what a maintainer acts on. It can over-fire in an old project where most records churn on first read; that backlog is real and the recommendation is one line. Most of the value comes from data `_memory_ranked` already computes. Measured after release by whether upgraded projects run Review memories (Risks).
- **Migrate spec-tool permissions during upgrade** (`24ax3-enh migrate-spec-tool-permissions-during-upgrade`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11 and AC-12 completed. Key decisions: Upgrade migrates permissions and records the verification; Write only repository settings; read user-level settings and recommend.
- **Release zip entry fails on a missing module** (`24bn7-bug release-zip-entry-missing-contained-files`) — AC-1, AC-2, AC-3 and AC-4 completed. Key decisions: Plan this in wave 24buu; Selected: resolve framework imports from the zip's own framework scripts, keeping the member set. Efficacy: replaying the rehearsal, `contained_files` imports from the zip and the materializer still sees today's members, so the documented command proceeds; it also covers future imports.
- **Replace unedited lifecycle prompts during upgrade** (`24bn8-enh replace-unedited-lifecycle-prompts-during-upgrade`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7 and AC-8 completed. Key decisions: Plan this in wave 24buu; Selected: perform the prescribed overwrite in the Phase 1 render child for copies whose recorded digest still matches, rendering the owned regions. Efficacy: replaying the rehearsal, all five prompts and the plan template would be replaced before the docs gate and index, removing every retired-tool reference and adding the keep rule with no agent step. It controls the outcome; it cannot help an edited copy, which keeps the agent merge.
- **CLI upgrade runs cleanup itself** (`24bn9-enh cli-upgrade-runs-cleanup`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9 and AC-10 completed. Key decisions: The CLI runs cleanup itself; Selected: a fresh cleanup child after a clean primary phase, skipped for retained continuations and when the MCP handler passes `--no-auto-cleanup`. Efficacy: replaying the rehearsal shape on a 1.52.0-to-later hop, the primary published the index with no continuation, so cleanup would run and the manual step disappears; on the 1.51.0 hop the old primary prints today's message, which the release notes cover. It controls the outcome on the CLI and leaves MCP sequencing intact.

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
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

- Retained [review and rehearsal evidence](evidence/README.md) maps the ledger’s temporary paths to the durable reports, probes, implementation logs and six route results. On the final repair, an independent reviewer demonstrated that the preliminary progress message omitted a parent-only skipped scan location. Both CLI paths now print the complete primary payload before cleanup. The real-child regression retains the observed location and requires exactly one terminal sentinel.

- Release watchpoint. The operator selected 1.53.0. Before building the official release, move the local q5u1 and q5u9 preview ZIPs out of the upgrade discovery directory and verify the official artifact by its published checksum. The Waveforge preview letter is an unsent operator draft.

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
| review | 259 | 5,428,909 |
| **Total** | **437** | **7,089,322** |

<!-- wave:context-efficiency-state {"generation":432,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":104,"content_source_credit":267906,"derived_artifact_credit":0,"direct_net":251367,"estimated_tokens_saved":251367,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3033,"response_debit":24341,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10835},"plan":{"calls":74,"content_source_credit":1911547,"derived_artifact_credit":2169,"direct_net":1409046,"estimated_tokens_saved":1409046,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":43502,"response_debit":467466,"source_credit_count":106,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6298},"review":{"calls":259,"content_source_credit":5954256,"derived_artifact_credit":7306,"direct_net":5428909,"estimated_tokens_saved":5428909,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":38023,"response_debit":501559,"source_credit_count":142,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6929}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":437,"content_source_credit":8133709,"derived_artifact_credit":9475,"direct_net":7089322,"estimated_tokens_saved":7089322,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":84558,"response_debit":993366,"source_credit_count":266,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":24062},"wave_id":"24buu memory-revalidation-upgrade-delivery"} -->
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
