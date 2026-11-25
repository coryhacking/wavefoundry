# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-24
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `248o5 behavior-contracts-and-spec-vocabulary`
Title: Behavior contracts and spec vocabulary

## Objective

Engineers use a spec to plan one delivery and find standing behavior contracts through the architecture hub and TechDocs. Fresh installs create the new layout, and upgrades migrate existing projects while preserving their content and publication choices. Engineers use `/wf-contract` to document verified behavior and `/wf-plan-spec` to propose work. Agents follow the same vocabulary from skill discovery through MCP calls, with a documented migration for existing callers and projects control which contracts they publish.

## Changes

Change ID: `248o4-enh publish-behavior-contracts-in-techdocs`
Change Status: `implemented`

Change ID: `248o6-enh prefer-spec-in-tools-and-skills`
Change Status: `implemented`
Depends On: `248o4-enh publish-behavior-contracts-in-techdocs`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer and technical writer
- Requested review lanes: none
- Required review lanes: code-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-11-24

## Wave Summary

Wave `248o5` (Behavior contracts and spec vocabulary) delivered two changes: Publish behavior contracts in TechDocs and Use spec names in lifecycle tools and skills.

Intent outcome: Achieved on the reviewed local install and upgrade paths. The independent docs-contract reviewer confirmed the contract migration preserves visible links, hidden comments and custom MkDocs metadata on the repaired fixtures. Fresh and v1.51.0-upgraded installations created records with the new spec labels and retrieved them using the identifier returned by the shipped planning workflow. The previous package failed the same result-key assertion. A downstream alias retained its configured schema. No hosted Backstage deployment or additional OS was exercised.

**Changes delivered:**

- **Publish behavior contracts in TechDocs** (`248o4-enh publish-behavior-contracts-in-techdocs`) — AC-1, AC-2, AC-3, AC-4, AC-5 and AC-6 completed. Key decisions: Use a named contracts collection under architecture.
- **Use spec names in lifecycle tools and skills** (`248o6-enh prefer-spec-in-tools-and-skills`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6 and AC-7 completed. Key decisions: Superseded initial plan to retain stock compatibility aliases; Remove all five legacy stock names when the spec tools ship.

## Watchpoints

- Land contract discovery and the folder migration first. Move the tool reference before editing its vocabulary. Verify effective publication scope and downstream tool permissions before recommending migration.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-248O6-ALIAS-COLLISION | not_issue | no | not_required | architecture-reviewer |
| DEL-248O4-COMMENT-LINK | not_issue | no | not_required | code-reviewer, architecture-reviewer |
| DEL-248O4-RESUME-REFERENCE | not_issue | no | not_required | code-reviewer |
| DEL-248O4-YAML-EXTRA | not_issue | no | not_required | architecture-reviewer |
| DEL-248O6-PACK-VERIFICATION | not_issue | no | not_required | docs-contract-reviewer, release-reviewer |
| DOCS-248O4-INTERMEDIATE-PUBLICATION | not_issue | no | not_required | docs-contract-reviewer |
| R1-248o4-first-upgrade-preview | not_issue | no | not_required | release-reviewer, council-readiness |

*Machine review state — 7 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 7*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | Phase | State | Why | Next action |
| --- | --- | --- | --- | --- |
| council-readiness | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| release-reviewer | readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| release-reviewer | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

2026-11-24: Intent outcome: Achieved on the reviewed local install and upgrade paths. The independent docs-contract reviewer confirmed the contract migration preserves visible links, hidden comments and custom MkDocs metadata on the repaired fixtures. Fresh and v1.51.0-upgraded installations created records with the new spec labels and retrieved them using the identifier returned by the shipped planning workflow. The previous package failed the same result-key assertion. A downstream alias retained its configured schema. No hosted Backstage deployment or additional OS was exercised.

2026-11-24: Delivery review initially withheld approval for two broken-link cases, a rewrite outside MkDocs navigation and an outdated installed-package verification. All four findings passed independent reverification in cycle 2. The code, architecture, docs-contract and release reviewers recorded typed delivery approvals. Installed-package evidence is in [the verification record](evidence/installed-spec-verification.json). Framework-wide qualification and operator signoff remain separate from these scoped approvals.

The operator subsequently chose immediate removal of the five stock change-named calls. The earlier approval covered compatibility aliases; re-prepare the revised plan before implementation.

The operator requested the new layout, spec-facing tools, and install/upgrade coverage. For readiness, the coordinator allocated migration and host compatibility checks to independent release, docs, architecture and code reviewers. The red-team primer challenged publication at intermediate states, preview drift and downstream name collisions.

Verify the built pack in a fresh target and an upgraded legacy target. Check the resulting paths, published links and installed tools and skills in each.

## Close retrospective

The full framework suite ran 13,563 tests across 261 modules with 13 skips and passed. Keep [the installed-package verification](evidence/installed-spec-verification.json) as evidence of fresh-install and upgrade behavior. The model benchmark tests already enforce the original fixture hashes, and the tool-schema tests cover both initial registration and reload. Those checks preserve the lessons from qualification.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 71 | 472,931 |
| implement | 78 | 0 |
| review | 132 | 4,853,657 |
| **Total** | **281** | **5,326,588** |

<!-- wave:context-efficiency-state {"generation":271,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":78,"content_source_credit":15166,"derived_artifact_credit":0,"direct_net":-7728,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2137,"response_debit":26889,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6132},"plan":{"calls":71,"content_source_credit":704130,"derived_artifact_credit":3771,"direct_net":472931,"estimated_tokens_saved":472931,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15252,"response_debit":235010,"source_credit_count":55,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15292},"review":{"calls":132,"content_source_credit":5173306,"derived_artifact_credit":3900,"direct_net":4853657,"estimated_tokens_saved":4853657,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":27024,"response_debit":303454,"source_credit_count":113,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6929}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":281,"content_source_credit":5892602,"derived_artifact_credit":7671,"direct_net":5318860,"estimated_tokens_saved":5326588,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":44413,"response_debit":565353,"source_credit_count":176,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":28353},"wave_id":"248o5 behavior-contracts-and-spec-vocabulary"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 11 | 0 | 10 | 7,706,628 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":10,"estimated_exploration_avoided":7706628,"surfaced_events":11} -->
<!-- wave:exploration-avoided end -->
