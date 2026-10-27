# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21fgr audit-detector-and-skill-invocation-policy`
Title: Audit Detector And Skill Invocation Policy

## Objective

Improve agent-environment audit accuracy and ship documented Codex invocation metadata for operator-owned skills. Preserve tool permissions, custom configuration and other host behavior.

## Changes

Change ID: `21fgp-bug audit-non-tool-identifier-false-positives`
Change Status: `implemented`

Change ID: `21fgq-enh codex-explicit-invocation-skill-policy`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-27

## Wave Summary

Wave `21fgr` (Audit Detector And Skill Invocation Policy) delivered two changes: Suppress confirmed non-tool audit false positives and Render explicit-invocation policy for operator skills. Notable adjustments during implementation: Suppress confirmed non-tool audit false positives: Final canonical run completed red: 12,072 tests across206files,12skips,1056.567s. All five original failing files now pass. Two other files fail: registered reload ownership reports second writer; TechDocs escaping-symlink fixture lacks unsafe_survivor_targets. Fresh independent QA/code/security/docs reviews found no new admitted-scope blocker; repaired findings are terminal, but delivery approvals and qualification ACs remain pending the required green suite. No test waiver, threshold change or unchanged retry.; Render explicit-invocation policy for operator skills: Readback: extend the existing registry renderer with literal Codex explicit-invocation sidecars for eligible operator-only skills in active .codex and .agents roots. Before, wf-close-wave has only SKILL.md on those roots; after, agents/openai.yaml declares allow_implicit_invocation false. AC-1–3 preserve skill bytes, custom sidecars and doc/host gates, and reject nested/leaf symlinks before any host writes. Scope is renderer, focused tests, generated sidecars and platform mapping; this is invocation metadata, not tool authorization or a host-runtime guarantee.; Render explicit-invocation policy for operator skills: Initial canonical qualification failed: 12,067 tests across 206 files, 12 existing skips, 710.965s. Five files report one failure each: declared-extension skill output roster, actor-token census, profile-literal census, legacy session-start timeout assertion and renamed-skill cleanup. Source-wave completion/approval remains pending repair; no failures waived. Earlier progress sampling missed three FAIL lines; final tracebacks are authoritative.

**Changes delivered:**

- **Suppress confirmed non-tool audit false positives** (`21fgp-bug audit-non-tool-identifier-false-positives`) — 3 ACs completed. Key decisions: Use the existing explicit exclusion set
- **Render explicit-invocation policy for operator skills** (`21fgq-enh codex-explicit-invocation-skill-policy`) — 5 ACs completed. Key decisions: Add the documented Codex sidecar with conservative custom-file preservation
## Watchpoints

- Watchpoint: Source edits require typed readiness and the framework edit gate. Pause after delivery; closure and commits remain operator-owned.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| QA-A9-FIXTURES-1 | do_now | no | completed | qa-reviewer |
| QA-A9-RENAME-1 | do_now | no | completed | qa-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
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
| plan | 80 | 695,719 |
| implement | 75 | 579,591 |
| review | 135 | 1,778,320 |
| **Total** | **290** | **3,053,630** |

<!-- wave:context-efficiency-state {"generation":257,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":75,"content_source_credit":746652,"derived_artifact_credit":0,"direct_net":579591,"estimated_tokens_saved":579591,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2364,"response_debit":170723,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6026},"plan":{"calls":80,"content_source_credit":844758,"derived_artifact_credit":2604,"direct_net":695719,"estimated_tokens_saved":695719,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19733,"response_debit":139448,"source_credit_count":50,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7538},"review":{"calls":135,"content_source_credit":2185622,"derived_artifact_credit":928,"direct_net":1778320,"estimated_tokens_saved":1778320,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16937,"response_debit":394982,"source_credit_count":74,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3689}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":290,"content_source_credit":3777032,"derived_artifact_credit":3532,"direct_net":3053630,"estimated_tokens_saved":3053630,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":39034,"response_debit":705153,"source_credit_count":146,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":17253},"wave_id":"21fgr audit-detector-and-skill-invocation-policy"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 47 | 0 | 14 | 24,131,493 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":14,"estimated_exploration_avoided":24131493,"surfaced_events":47} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

Readiness: isolated adversarial primer, fixed architecture/security/QA/reality seats and rotating docs-contract alternative completed, with all fixed seats weighing alternatives. All required lane and council-readiness approvals recorded; no blocking design finding. Code/architecture shared one independent context, disclosed. Existing exact scanner exclusions and conservative missing-only skill metadata favored over parser/YAML-merge expansion. Modernization remains context-only and requires actual plugin observation. Morning maintained-source adoption remains an unmet prerequisite, not waived by a staged patch or browser capability check. Current scanner owner is `_audit_harness_coherence`; one historical readiness narrative mistakenly called it `_audit_seed_text_coherence`, while its inspected range and public audit observation were correct. No immutable evidence was rewritten.

Implementation checkpoint: A8 public-path regression passes (four tests; original and four mutants detected). A9 renderer file passes 178 tests, eight sidecars generated, all 48 SKILL.md files preserved and repeat render unchanged. Paused to free the OPEN slot for 21a5a; final canonical qualification and independent delivery remain pending. No closure or commit.
