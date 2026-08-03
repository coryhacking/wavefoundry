# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1u8o5 rename-summary-schema-version-key`
Title: Rename Summary Schema Version Key

## Objective

Rename the upgrade delegation envelope key `summary_schema` to `summary_schema_version` (matching the repo-wide `schema_version` convention) before the official 1.15.0 release freezes the contract for every downstream repository. Pre-release, the rename costs one benign marked-degradation run on the two operator test repos; post-release it would cost every fielded repo the same run.

## Changes

Change ID: `1u8o4-ref rename-summary-schema-to-schema-version`
Change Status: `implemented`

## Participants

- Coordinator: session agent (Claude Code)
- Write-owning roles: implementer (fix workstream)
- Requested review lanes: code-reviewer, qa
- Required review lanes: code-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, qa

Completed At: 2026-08-02

## Wave Summary

Wave `1u8o5` (Rename Summary Schema Version Key) delivered one change: Rename the Delegation Envelope Token to summary_schema_version Before 1.15.0 Ships. Notable adjustments during implementation: Rename the Delegation Envelope Token to summary_schema_version Before 1.15.0 Ships: Readiness council ran (red-team + docs-contract-reviewer, both code-grounded): conditional PASS; census gaps and two false premises folded into Requirements 4-5, Scope, Serialization Points, and Affected Architecture Docs in-phase.; Rename the Delegation Envelope Token to summary_schema_version Before 1.15.0 Ships: All Requirement 4 doc surfaces renamed: spec :919 (both occurrences), ADR 1u49j :36, layering-rules :28, seed-160 :83 under the open `seed_edit_allowed` gate with the mirror :57 paragraph kept byte-identical (diff-verified), CHANGELOG Fixed bullet in-place plus the Upgrading item 8 two-population disclosure (unmarked pre-mechanism run vs one marked pg8h/pg9m run with the false-report-stopping sentence), session-handoff hook :235/:296 re-pointed to the new key and the marked-then-unmarked expectation. docs-lint passes. AC-3 met.

**Changes delivered:**

- **Rename the Delegation Envelope Token to summary_schema_version Before 1.15.0 Ships** (`1u8o4-ref rename-summary-schema-to-schema-version`) — 4 ACs completed. Key decisions: Rename to `summary_schema_version`, now; Fold the readiness-council census into Requirement 4 verbatim
## Watchpoints

- Blocking: implementation waits on wave 1u8o2's operator signoff and close (single-OPEN rule); this wave may be fully readied in parallel.
- Blocking: must land before the official 1.15.0 release build; the pg9m prerelease pack predates this rename by design.
- Watchpoint: the fielded pg8h/pg9m runners take exactly one marked-degradation run on their next upgrade; the CHANGELOG rename sentence discloses it so nobody files it as a delegation failure.
- Watchpoint: seed-160 names the key at line 83 (council-verified), so the edit requires the `seed_edit_allowed` gate (open before, close immediately after), followed by regenerating the rendered mirror `docs/prompts/upgrade-wavefoundry.prompt.md`.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the plan's doc-surface enumeration missed the living layering-rules row, the rendered seed-160 mirror, the four functional `test_server_tools.py` literals, and the session-handoff verification hook, and two premises were false (CHANGELOG item 8 does not name the key; memory records carry no `schema_version`); all folded into the plan in-phase before the receipt mint; strongest-alternative: keep `summary_schema` forever, since a key rename degrades old parents as `unrecognized_schema_token_None` which can read as malformed output rather than versioned evolution; rejected because the fielded population is two operator-controlled repos, AC-2 pins that exact None-clamp path red-first, and the rename option disappears permanently at release)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 20 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| qa | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 23 | 680,868 |
| implement | 34 | 1,085,520 |
| review | 94 | 2,182,235 |
| **Total** | **151** | **3,948,623** |

<!-- wave:context-efficiency-state {"generation":159,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":34,"content_source_credit":1151830,"derived_artifact_credit":528,"direct_net":1085520,"estimated_tokens_saved":1085520,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":962,"response_debit":67307,"source_credit_count":45,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":23,"content_source_credit":713146,"derived_artifact_credit":607,"direct_net":680868,"estimated_tokens_saved":680868,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5907,"response_debit":32392,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5414},"review":{"calls":94,"content_source_credit":2403205,"derived_artifact_credit":998,"direct_net":2182235,"estimated_tokens_saved":2182235,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7754,"response_debit":215560,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":151,"content_source_credit":4268181,"derived_artifact_credit":2133,"direct_net":3948623,"estimated_tokens_saved":3948623,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14623,"response_debit":315259,"source_credit_count":121,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8191},"wave_id":"1u8o5 rename-summary-schema-version-key"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 18 | 0 | 9 | 10,829,614 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":10829614,"surfaced_events":18} -->
<!-- wave:exploration-avoided end -->
