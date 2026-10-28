# Wave Record

Owner: Engineering
Status: implementing
Last verified: 2026-10-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21u6x profile-source-history-censuses`
Title: Profile Source History Censuses

## Objective

Restore source-history census coverage under both default and renamed layouts without skipping checks or weakening corruption detection.

<Describe the shared outcome of the admitted changes in 1–3 sentences: who benefits, what observably improves, and the material boundaries. This text is displayed in the dashboard wave card.>

## Changes

Change ID: `21szl-bug profile-source-history-censuses`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

## Wave Summary

<Describe the purpose and scope of this wave in 1–3 sentences.>

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
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-10-27: Delivery complete: required code/QA and Council approved, no findings, intent establishes, unanimous/maxseveritynone. Standard3stance2question isolated primer, fixedarchitecture/code sharedcontext, separateQA/security/reality, rotatingdocs, explicit alternativeweigh, anonymous-first synthesis, redteamclosing all performed. Chair positive2tests/0.048s, QApositive2/0.042s; chair/code/QA independently detected both old-root mutants (each1assertionfailure/0errors/skips). Security/reality/docs source-only; sharedprimer concerns correlated. Localhelpers preferred because carrier excludes plans/live/archive while ledger unionslive/archive. Falsification: emptyfixtures could hidevacuity, but real334ledger corpus threshold/parser/schema retained and archivedcorruption caught. AllACs/tasks complete, no intentionaldeferrals. Scopegapcheck none; fullcompatibility matrices belong packaging, not this change. Operatorclosure/commit unrequested.

2026-10-27: Intent outcome: achieved in controlled default and renamed-profile execution. Carrier census excludes configured record/archive trees and still detects malformed active and prefix-sibling carriers; ledger census validates334real histories and catches archived corruption without weakening its >100 threshold. Focused20default/20renamed pass0skips/errors; old-assumption mutants each fail meaningful assertion. Canonical12,290tests/214files/12skips/554.293s passed. QA independently checks this outcome at delivery. Full compatibility matrices remain a separate packaging gate; no nativeWindows execution claimed.

2026-10-27: Readiness complete on48260890dfd897da4e39, standard3stance2question primer, fixedarchitecture/security/QA/reality plus rotatingdocs, explicit alternative weighing, anonymous-first synthesis and red-teamclosing. Unanimous/no findings. Code and architecture share one disclosed independent context; QA separate. Chair original-root probe reproduces20carriers/9missing vs archive-aware8/0 and0liveledgers vs334live/archive; active securityrole/prefixsibling retained. No productionbehavior changed. Implementation focused20default and20renamed pass, two old-assumption mutants caught, gateclosed.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 62 | 348,389 |
| implement | 52 | 0 |
| review | 10 | 3,820 |
| **Total** | **124** | **352,209** |

<!-- wave:context-efficiency-state {"generation":81,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":52,"content_source_credit":21445,"derived_artifact_credit":515,"direct_net":-33926,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3104,"response_debit":55702,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2920},"plan":{"calls":62,"content_source_credit":483353,"derived_artifact_credit":2107,"direct_net":348389,"estimated_tokens_saved":348389,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3665,"response_debit":138459,"source_credit_count":27,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5053},"review":{"calls":10,"content_source_credit":12127,"derived_artifact_credit":303,"direct_net":3820,"estimated_tokens_saved":3820,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":643,"response_debit":7967,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":124,"content_source_credit":516925,"derived_artifact_credit":2925,"direct_net":318283,"estimated_tokens_saved":352209,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7412,"response_debit":202128,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7973},"wave_id":"21u6x profile-source-history-censuses"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
