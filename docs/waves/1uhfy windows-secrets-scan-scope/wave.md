# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-04
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1uhfy windows-secrets-scan-scope`
Title: Windows Secrets Scan Scope

## Objective

Ensure the secrets scanner excludes native Windows `.venv/Lib/site-packages` trees and Graphify's default `graphify-out/` generated artifacts before reading them, and the shared semantic-and-graph walker prunes the default Graphify output before descending into it, without widening scope to ordinary source files. The correction keeps the shipped Betterleaks prefilter and active Python allowlist aligned.

## Changes

Change ID: `1uhfx-bug windows-virtualenv-secrets-scan-exclusion`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-08-04

## Wave Summary

Wave `1uhfy` (Windows Secrets Scan Scope) delivered one change: Exclude Windows Virtual Environments from the Secrets Scan. Notable adjustments during implementation: Exclude Windows Virtual Environments from the Secrets Scan: Scope expanded to exclude Graphify's documented default output directory.; Exclude Windows Virtual Environments from the Secrets Scan: Scope extended to exclude Graphify's default output from the shared semantic-and-graph walker.

**Changes delivered:**

- **Exclude Windows Virtual Environments from the Secrets Scan** (`1uhfx-bug windows-virtualenv-secrets-scan-exclusion`) — 6 ACs completed. Key decisions: Add an optional dot to the existing venv-directory pattern, and exclude the exact default `graphify-out/` directory, in both shipped representations.; Add the exact default `graphify-out` directory to the shared index walker without changing its version.
## Watchpoints

- Watchpoint: update both duplicated venv and Graphify-output patterns together; the Python scanner only executes the `[allowlist]` copy today, but the Betterleaks prefilter must not drift.
- Watchpoint: exclude only Graphify's documented default `graphify-out/`; custom `GRAPHIFY_OUT` locations remain project-owned configuration.
- Watchpoint: verify the normal incremental update reaps prior Graphify artifacts from semantic and graph state; do not impose a full rebuild for this subtractive filter.

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
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 76 | 2,378,048 |
| implement | 21 | 98,915 |
| review | 27 | 185,859 |
| **Total** | **124** | **2,662,822** |

<!-- wave:context-efficiency-state {"generation":113,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":21,"content_source_credit":118228,"derived_artifact_credit":1006,"direct_net":98915,"estimated_tokens_saved":98915,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1972,"response_debit":19778,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":76,"content_source_credit":2514840,"derived_artifact_credit":1520,"direct_net":2378048,"estimated_tokens_saved":2378048,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4180,"response_debit":145693,"source_credit_count":52,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11561},"review":{"calls":27,"content_source_credit":206260,"derived_artifact_credit":2540,"direct_net":185859,"estimated_tokens_saved":185859,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3628,"response_debit":22738,"source_credit_count":27,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3425}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":124,"content_source_credit":2839328,"derived_artifact_credit":5066,"direct_net":2662822,"estimated_tokens_saved":2662822,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9780,"response_debit":188209,"source_credit_count":89,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":16417},"wave_id":"1uhfy windows-secrets-scan-scope"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 2 | 1,836,744 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":1836744,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
