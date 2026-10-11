# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-10-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20cw2 host-hook-tool-compatibility`
Title: Host Hook Tool Compatibility

## Objective

Handle unrecognized tool names honestly within existing generated-hook interception boundaries and provide explicit Codex patch-policy coverage without inventing native enforcement.

## Changes

Change ID: `20dkh-bug host-hook-tool-name-compatibility`
Change Status: `planned`

## Participants

- Coordinator: Engineering coordinator
- Write-owning roles: assigned implementer after readiness; coordinator owns wave records. Review roles are read-only.
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

## Wave Summary

Planning and readiness review only. All implementation ACs/tasks remain pending; no source changes, delivery approval or closure is claimed.

## Watchpoints

- Watchpoint: stop before implementation; keep source/seed edit gates closed. No routine evidence folder or new upgrade qualification work.
- Serialize shared prompt/policy/index owners and current handoff writes across these three waves.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DC-20C-CARRIER | do_now | no | completed | docs-contract-reviewer, code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, council-readiness |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | withheld | repaired findings require fresh approval: DC-20C-CARRIER | record a fresh independent approval for council-delivery |
| code-reviewer | withheld | repaired findings require fresh approval: DC-20C-CARRIER | record a fresh independent approval for code-reviewer |
| qa-reviewer | withheld | repaired findings require fresh approval: DC-20C-CARRIER | record a fresh independent approval for qa-reviewer |
| architecture-reviewer | withheld | repaired findings require fresh approval: DC-20C-CARRIER | record a fresh independent approval for architecture-reviewer |
| docs-contract-reviewer | withheld | repaired findings require fresh approval: DC-20C-CARRIER | record a fresh independent approval for docs-contract-reviewer |
| security-reviewer | withheld | repaired findings require fresh approval: DC-20C-CARRIER | record a fresh independent approval for security-reviewer |
| operator-signoff | withheld | repaired findings require fresh approval: DC-20C-CARRIER | record a fresh independent approval for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 16 | 49,172 |
| review | 53 | 295,019 |
| **Total** | **69** | **344,191** |

<!-- wave:context-efficiency-state {"generation":69,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":16,"content_source_credit":98638,"derived_artifact_credit":126,"direct_net":49172,"estimated_tokens_saved":49172,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13325,"response_debit":40072,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":53,"content_source_credit":454346,"derived_artifact_credit":0,"direct_net":295019,"estimated_tokens_saved":295019,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1418,"response_debit":157909,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":69,"content_source_credit":552984,"derived_artifact_credit":126,"direct_net":344191,"estimated_tokens_saved":344191,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14743,"response_debit":197981,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"wave_id":"20cw2 host-hook-tool-compatibility"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Work allocation: coordinator retains the coupled 1us4q revision and public wave mutations; two domain planners independently investigate hook compatibility and historical eligibility. Inherited capable model selected for source-grounded ambiguity; actual runtime model/effort identity unavailable. Independent chair and isolated seat contexts supply readiness judgment; no planner self-approval.
- Primer depth: full; rotating best-alternative seat: docs-contract-reviewer. Readiness reviews current plans and safe controls, not future implementation. Optional Review plan branch outcomes stay inline; only typed current approvals authorize readiness.

- Independent Council: isolated red-team primer at full (five stances / three primer questions); fixed architecture/security/QA/reality seats, rotating docs-contract and separate code reviewer. DC-20C-CARRIER was the sole actionable finding: full current rendering never transferred seed050 policy to existing AGENTS. One cycle-1 plan repair selects the existing managed Implement wave workflow carrier; fresh independent docs reverification completed the repair with unresolved lanes empty. No second repair or new blocker.
- Source `999b1003`; current plan SHA256 `cb42f201f8d4061ca62d6623f3d8046d57208f1ebc4c37150be64e0fbe232711`; receipt `review-policy-add8353b5a8dd092a83d`. Inherited capable model; runtime identity/effort unavailable. Fixed artifact-first priors showed distinct emphasis, without verbatim primer echo. Original rotating early-primer attempts are excluded as conforming prior evidence; their executed controls remain honestly attributed. Shared fixtures/primer facts count as correlated evidence, not independent votes.

| Seat | Artifact read, primer effect and outcome |
| --- | --- |
| Architecture | Received-name handling preserves subscriptions. Primer extended path-only Claude-post boundary. Carrier repair satisfies explicit ownership/serialization. No findings in my lane. |
| Security | Supported-path guards and label-only output bound ambiguity. Primer extended native/adherence limits. Workflow-only repair retains protections. No findings in my lane. |
| QA | Generated handlers provide meaningful oracles. Primer extended unknown/malformed/post cases. Actual consumer assertions replace vacuous source-only presence. No findings in my lane. |
| Reality | Handler verdict differs from interception. Primer confirmed no-path/adherence limits. Existing workflow route avoids a new writer/pass. No findings in my lane. |

- Controls: Generated current pre/post controls distinguish known edits/reads, unknown and missing/malformed payloads; source-derived named-dispatcher census excludes path-only adapters. Fresh docs replayed actual full rendering and managed default/fork deliver-cycle carriers: CRLF customization and both serialized prose sentinels retained; second pass zero writes; skill pointer, version7/registry unchanged. Durable anchors: render_platform_surfaces.render_platform_entrypoints; review_policy.REVIEW_POLICY_SURFACE_BLOCKS[_implement_doc]; render_agent_surfaces.reconcile_review_policy_surfaces; wf-implement-wave/SKILL.md; amended R7/R8 and AC7/AC8.
- Synthesis: anonymized Seat 1–6 merit pass preceded attributed specialist authority; required docs blocking authority was preserved throughout. Fixed seats explicitly weighed rotating alternatives; red-team closing reconciled the sealed candidate set and changed the original hook carrier inference. No substantive split required a challenger round. Actual required-lane approvals bind to this receipt; typed ledger remains sole authority.

### Falsification Check

Strongest contrary case: workflow prompt presence could be mislabeled universal startup/native enforcement/adherence. The full-render known-bad refutes old root-entry propagation, and amended scope explicitly excludes that promise. Fresh profile/customization/idempotence controls establish current route feasibility only; future patch instructions and repaired handler behavior remain unimplemented. Chair current-packet identity checks passed; deliberate council-chair-as-code-reviewer dry-run approvals were rejected without append.

Readiness only: all implementation ACs/tasks remain unchecked; no delivery, activation, native-host/live-index, universal platform/census or adherence qualification. Temporary seat/probe reports stay outside the repository; reproducible fixtures and limits are retained here and in typed evidence. Approval authority uses `approval_phase: readiness`; the tool's generic evidence `phase` default is `delivery`, so observations explicitly distinguish current readiness from future delivery.

- Current carrier clearance uses fresh independent context `fresh-docs-carrier-reverify-20cw2-20261011-independent`, actual `ev-dc-20c-carrier-3` and `syn-dc-20c-carrier-1-2`; original rotating-docs early-order attempt is not claimed as a conforming prior. Its concrete full-render counterexample retains attributed required-lane authority, while the actual fresh focused repair controls/current approval supply present carrier feasibility. No extra repair round or expanded product claim.

- Final Council readiness: actual `ev-approval-council-readiness` is current on `review-policy-add8353b5a8dd092a83d`; all required specialist approvals are current, no unresolved blocking lane remains, and successful typed publication returned zero readiness actions. Council has completed review only; coordinator owns final prepare-without-opening and handoff.
