# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20bw2 review-decision-log-churn`
Title: Review Decision Log Churn

## Objective

Reduce unnecessary readiness receipt rotation by directing routine implementation narration to existing excluded carriers, while keeping material amendments digested and independently reviewed.

## Changes

Change ID: `1us4q-bug decision-log-exclusion-gated-on-coverage-census`
Change Status: `implemented`

## Participants

- Coordinator: Engineering coordinator
- Write-owning roles: assigned implementer after readiness; coordinator owns wave records. Review roles are read-only.
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-11

## Wave Summary

Wave `20bw2` (Review Decision Log Churn) delivered one change: Route implementation narration without weakening review authority. Notable adjustments during implementation: Route implementation narration without weakening review authority: Divergent pre-plan and optional Review plan: selected phase-aware authoring with owning-section rule and existing managed refresh. Whole-log exclusion loses coverage; keyword guard false-fails narration and misses semantics; new structured decision subsystem adds unjustified migration/retention overhead. All current requirement/scope branches self-answered from current policy and August disproof. Stop condition: independent readiness, then no implementation until explicitly requested.; Route implementation narration without weakening review authority: WITHDRAWN and the implementation REVERTED at operator direction. Six independent lanes (four delivery, two readiness) all returned WITHHELD and all converged primarily on this change; the three siblings were clean or near-clean. The guard shipped and was removed from the tree: `check_excluded_region_triggers`, its `cli.py` registration on both paths, `census_exclusion_coverage.py`, the `EXCLUDED_REL_PATHS` entry, the seed 180 phase rule and carve-out, the two `REVIEW_POLICY_SURFACE_BLOCKS` edits, and both test classes. `review_policy.py` and the rendered prompt regions verified byte-identical to HEAD afterwards; Route implementation narration without weakening review authority: "Fails on zero documents today" was measured over the guard's real scope of 16 live documents, not the 824-document census corpus. At the historical base rate of 11.8%, P(zero across 16) is about 0.13. Observing zero was a coin flip, not evidence of quiet, and the decision to ship as an error rather than a warning rested on it

**Changes delivered:**

- **Route implementation narration without weakening review authority** (`1us4q-bug decision-log-exclusion-gated-on-coverage-census`) — 5 ACs completed. Key decisions: The P1 is answered by measurement rather than by abandoning the change: only 13 of the 214 append-after-plan-time rows (6.1%) are trigger-bearing, so 201 (93.9%) are redirectable with no coverage effect. A boundary carve-out (Requirement 2) protects the 6.1% and a mechanical guard (Requirement 3) makes the carve-out something other than author judgment; The hazard is ALREADY LIVE and this change now closes it. 97 documents carry 156 trigger-bearing `## Progress Log` rows that are inert for council triggering today, from the exclusion `1uhcb` shipped. Every one is in a CLOSED wave and zero live documents are affected, which is what makes an error-level guard implementable rather than a warning
## Watchpoints

- Watchpoint: current operator authorization permits admitted implementation, delivery review and pause; no close, commit or release. Keep source/seed edits within admitted authoring correction; no routine evidence folder or new upgrade qualification work.
- Serialize shared prompt/policy/index owners and current handoff writes across these three waves.

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
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 467 | 2,004,635 |
| implement | 355 | 2,009,595 |
| review | 194 | 1,480,782 |
| **Total** | **1,016** | **5,495,012** |

<!-- wave:context-efficiency-state {"generation":599,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":355,"content_source_credit":2822731,"derived_artifact_credit":3781,"direct_net":2009595,"estimated_tokens_saved":2009595,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17445,"response_debit":801854,"source_credit_count":138,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2382},"plan":{"calls":467,"content_source_credit":3546859,"derived_artifact_credit":455,"direct_net":2004635,"estimated_tokens_saved":2004635,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":27551,"response_debit":1518933,"source_credit_count":216,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":194,"content_source_credit":1958578,"derived_artifact_credit":195,"direct_net":1480782,"estimated_tokens_saved":1480782,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10078,"response_debit":470769,"source_credit_count":74,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1016,"content_source_credit":8328168,"derived_artifact_credit":4431,"direct_net":5495012,"estimated_tokens_saved":5495012,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":55074,"response_debit":2791556,"source_credit_count":428,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9043},"wave_id":"20bw2 review-decision-log-churn"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 58 | 0 | 22 | 15,143,686 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":22,"estimated_exploration_avoided":15143686,"surfaced_events":58} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Work allocation: coordinator retains the coupled 1us4q revision and public wave mutations; two domain planners independently investigate hook compatibility and historical eligibility. Inherited capable model selected for source-grounded ambiguity; actual runtime model/effort identity unavailable. Independent chair and isolated seat contexts supply readiness judgment; no planner self-approval.
- Primer depth: full; rotating best-alternative seat: docs-contract-reviewer. Readiness reviews current plans and safe controls, not future implementation. Optional Review plan branch outcomes stay inline; only typed current approvals authorize readiness.

- Independent Council: isolated red-team primer at full (five stances / three primer questions); fixed architecture/security/QA/reality seats, rotating docs-contract and separate code reviewer. No actionable findings. Structured intent tags add schema/migration without detecting hidden semantic amendments; retain-all narration preserves the unwanted churn. Existing authoring correction remains the selected bounded approach.
- Source `999b1003`; current plan SHA256 `8f8abe49924f0247d3872035220138257de67aae6415d65f0aae2160ddd9d32f`; receipt `review-policy-d0418142de7233c2ef62`. Inherited capable model; runtime identity/effort unavailable. Fixed artifact-first priors showed distinct emphasis, without verbatim primer echo. Original rotating early-primer attempts are excluded as conforming prior evidence; their executed controls remain honestly attributed. Shared fixtures/primer facts count as correlated evidence, not independent votes.

| Seat | Artifact read, primer effect and outcome |
| --- | --- |
| Architecture | Managed authoring correction preserves authority. Primer extended duplicate-heading/handoff counterexamples. No findings in my lane. |
| Security | Excluded narration must not conceal amendment. Primer confirmed canonical-carrier/manual-discipline limits. No findings in my lane. |
| QA | Real producer/carrier controls are feasible. Primer extended ambiguous-heading and substantive-handoff sensitivity. No findings in my lane. |
| Reality | Guidance works when narration and contract changes differ. Primer confirmed those operational limits. No findings in my lane. |

- Controls: Current declared/legacy digest, lane and council channels distinguish canonical Progress observations from Decision/material/duplicate-heading/substantive-handoff changes. Existing managed-carrier runtime prose substitutions preserve customization and converge; future wording/profile/history delivery remains pending. Durable anchors: review_policy.policy_input_snapshot/select_required_review_lanes; gardener_metadata.canonical_review_policy_body; lifecycle_gate_support.canonical_change_texts; render_agent_surfaces.reconcile_review_policy_surfaces.
- Synthesis: anonymized Seat 1–6 merit pass preceded attributed specialist authority; required docs blocking authority was preserved throughout. Fixed seats explicitly weighed rotating alternatives; red-team closing reconciled the sealed candidate set and changed the original hook carrier inference. No substantive split required a challenger round. Actual required-lane approvals bind to this receipt; typed ledger remains sole authority.

### Falsification Check

Strongest contrary case: a material amendment hidden only in canonical Progress is not automatically detected. Existing controls demonstrate that limitation; the plan requires amendment of owning digested sections and independent re-Prepare, without claiming semantic detection. Chair current-packet identity checks passed; deliberate council-chair-as-code-reviewer dry-run approvals were rejected without append.

Readiness only: all implementation ACs/tasks remain unchecked; no delivery, activation, native-host/live-index, universal platform/census or adherence qualification. Temporary seat/probe reports stay outside the repository; reproducible fixtures and limits are retained here and in typed evidence. Approval authority uses `approval_phase: readiness`; the tool's generic evidence `phase` default is `delivery`, so observations explicitly distinguish current readiness from future delivery.


- Ordered rotating-docs replacement: new isolated context `bw2-fresh-artifact-docs-contract-20261010-9304w9n6` read current artifact/source and ran its own declared/undeclared, unsupported-heading and two-managed-carrier controls before actual primer exposure. Sealed prior: feasible canonical Progress authoring correction if material owning-section edits remain authoritative and inertness claims stay precise. Primer confirmed that prior; all three questions and structured-tags/retain-all alternatives were explicitly addressed. No findings in my lane. Current `ev-approval-docs-contract-reviewer-2` supersedes the early-primer approval as conforming review evidence. Initial added expectation errors were corrected/excluded from green evidence; Stage 2 container exposure to other-wave primer/alternative packets was disclosed and not used. Reused fixtures count as correlated proof.

- Final Council readiness: actual `ev-approval-council-readiness-2` is current on `review-policy-d0418142de7233c2ef62`; all required specialist approvals are current, no unresolved blocking lane remains, and successful typed publication returned zero readiness actions. Council has completed review only; coordinator owns final prepare-without-opening and handoff.

### Delivery review — 2026-10-11

- Full primer depth selected for the cross-surface review-authoring contract. Independent red-team primer applied all five stances and three questions. Fresh fixed architecture, security, QA and reality seats sealed current-artifact priors before receiving the primer; rotating docs-contract and separate code contexts independently reviewed the current tree. Inherited capable models fit the boundary/coverage judgment; observed runtime model and effort identities are unknown.

| Delivery seat | Evidence and outcome |
| --- | --- |
| Architecture | Keyword-free owning amendment moves the digest; hidden narration does not. Protected AST/files unchanged; two valid mutants caught, ineffective mapping replacement excluded. Primer extended the mixed-concession concern. No findings in my lane. |
| Security | Current operator-owned input creates no demonstrated attacker/authority delta; Requirements/Decision exclusion controls fail and mixed owning AC amendment remains sensitive. Primer extended the mixed repair case. No findings in my lane. |
| QA | All five required ACs have identified evidence; six added tests and five negative controls execute without skips/errors. Primer confirmed the hidden-amendment concern. Retained independent QA verified the genuine root-matching canonical receipt and unchanged reviewed inputs. No findings in my lane. |
| Reality | Concrete producer/carrier checks support correctly authored observation stability and intentional material rotation. Primer sharpened the mixed-concession probe. No findings in my lane. |
| Docs-contract (rotating) | Fresh copied default six tests and second-profile four routing tests pass without skips; seven normative/metamorphic cells and three guidance controls checked. Copied-helper guard refusal excluded from green evidence. Primer extended the mixed example. No findings in my lane. |
| Code (separate) | Six faithful mutations detect exclusion, heading, trigger, lane and carrier regressions; AST outside managed prose, canonicalizer and version unchanged. No findings in my lane. |

- Anonymized randomized Seat 1–6 merit assessment preceded attributed policy authority. Every fixed seat explicitly weighed the rotating alternative: a mixed repair/AC example would clarify the existing obligation but is optional wording. Structured tags add schema/migration while remaining truthfulness-dependent; retaining all narration preserves churn; excluding Decision Log loses material inputs. Unanimous source assessment, maximum severity none; no challenge round or required repair. Shared shipped fixtures and primer facts are correlated evidence, not independent votes. Red-team closing held the empty candidate set; typed `run-initial-delivery` seals it without invented finding rows. Typed ledger approvals carry the attributed lane authority; final QA/Council publication uses the genuine qualification below and the full docs gate.
- Independent chair checks reached actual policy producers and the production reconciler, killed empty Council/omitted release-lane controls, and exercised actual scratch `wf_reopen_wave_response`: closed to active while admitted historical member bytes stayed identical (SHA256 `6d54aa8af4b58624462681f0cb3c3b1f05b5d5662fda1c1f5f6ed123e108e368`). Only index-refresh scheduling was mocked and asserted; the earlier wrong-seam setup error is excluded. Named historical Decision Log bytes match HEAD (SHA256 `3a5aeaf51f674686ba9b3a55fa948a97f03fe4a800be982672f783d3e780003f`). Durable regression anchors: `ImplementationNarrationRoutingTests`, `ImplementationNarrationGuidanceTests`, `record_layout_support.apply_profile`, `review_policy.policy_input_digest`, `render_agent_surfaces.reconcile_review_policy_surfaces` and `wf_reopen_wave_response`.
- Frozen reviewed mapping SHA256 `85f9a3e2cd41c7f1be9a6d5c91f8b98e62829d6fe95cbe944f31d76a8e5db75c` hashes each Serialization Point path, a space, its `git hash-object`, and LF in the declared order; all eight identities stayed unchanged. Current framework inputs are `a2d87280f38a42a3788205ce78fb59994a72c3c5a429ec92ee46854400d0b76e`; standing receipt is `review-policy-d0418142de7233c2ef62`, policy digest `5820d14e8c2d7128072504fe505a1d1059097a9b4d119cf49034da6ee82f05d8`, evaluator 7. No required-priority deferral or important/nice-to-have AC outside admission was found.
- Independence limits: chair orientation accidentally exposed earlier readiness checkpoints; primer overbroad read exposed history; QA/docs searches incidentally exposed historical snippets. None supplied proof or a fixed-seat verdict. Fixed priors had distinct source-grounded emphasis without exact primer framing. Present guidance/profile contracts do not prove future adherence, semantic completeness, live host/index operation or release-profile qualification. No new stateful mechanism or concurrency boundary changed; selected existing transition cells cover carrier refresh/repeat and scratch reopen.

### Falsification Check

Source assessment passes. The strongest contrary case is a material concession hidden entirely in Progress Log. It is reachable and potentially material; guidance is not preventive containment. The delivered contract nevertheless conforms because it explicitly requires owning digested amendments and disclaims automatic discovery, as the executed controls show. Genuine canonical `run_tests.py --no-cache` qualification passed 12,272 tests across 185 files, with 12 aggregate skips, exit 0 in 688.019 seconds; ordinary cache defaults and approved local-socket/own-process execution were used with offline models. Receipt `ran_at` is `2026-10-11T07:07:14.797965+00:00`, SHA256 `fd976dc372f300a3d1c27b398c3a007490e46eecce793fae27e0bc294c3019b9`; root and isolated snapshot receipt bytes and current framework input hashes match the binding above. The snapshot includes the three pre-existing ignored benchmark reports authenticated by the runner. The earlier 814.300-second green run omitted them and its transfer was refused; it supplies no receipt authority. Exact skip identities were not logged, so identity parity is not claimed; the six added tests ran without skips. Final delivery approval requires the full docs gate after this checkpoint. No qualification waiver, closure, commit or release is claimed.
