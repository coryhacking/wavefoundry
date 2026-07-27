# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-27
review-evidence-source: events.jsonl

wave-id: `1tmtx test-suite-performance`
Title: Test Suite Performance

## Objective

Reduce the canonical framework suite's measured critical-path wall time without
weakening its per-file subprocess isolation or delivery authority. The wave adds
per-file timing and a cache-safe focused repair mode, selects scheduling through
a controlled comparison, and splits the dominant server-tool test module only
if the measured critical path proves the split worthwhile.

## Changes

Change ID: `1tm6d-enh test-suite-critical-path-acceleration`
Change Status: `planned`

## Wave Summary

The planning snapshot was 6,235 tests and roughly 290 seconds, with
`test_server_tools.py` the largest indivisible file. Those figures are not a
baseline while `1tmb1` is changing the same corpus. After that work settles,
this wave freezes the exact inventory and environment, measures the real
critical path, and targets a 25% median improvement while preserving every
safety, cache, lock, and full-suite gate.

## Participants

- Coordinator/moderator: primary Codex coordinator / wave-council
- Review seats: red-team, architecture-reviewer, security-reviewer,
  qa-reviewer, reality-checker, performance-reviewer, docs-contract-reviewer
- Implementation owners: framework-engineer, test-engineer,
  performance-reviewer, docs-contract-reviewer (after `1tmb1` completes)

## Watchpoints

- Blocking: wait for `1tmb1` and all concurrent writes to the runner/test corpus
  to finish, then freeze the digest, exact identity/fingerprint inventory, skips,
  environment, and original-source external baseline before any runner edit;
  telemetry-only evidence then establishes the pre-optimization distribution.
- Watchpoint: longest-first is a hypothesis, not an approval claim; compare it with the
  current schedule because starting several heavy shards together may saturate
  CPU or I/O.
- Blocking: physical sharding is also a hypothesis. Proceed only if measured
  tail time and the feasibility bound support it; permit one measured rebalance,
  then require an operator disposition rather than expanding the design.
- Blocking: focused runs are diagnostic only and must never read or update the complete
  suite's last-green cache evidence.
- Follow-up boundary: preserve the six-worker cap and one-subprocess-per-file model; per-file result
  caching, monolithic discovery, distributed execution, and deleted coverage are
  explicitly outside this wave.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 3 records; 1 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- The initial readiness approval record was premature: it predated the final
  red-team and docs-contract seats. It is superseded by the post-repair council
  checkpoint recorded below and remains history rather than current authority.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-26: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: do not infer the critical path or preselect scheduling/sharding from file size while `1tmb1` is changing the corpus—freeze and measure first, then bootstrap a complete post-layout timing manifest before comparing schedules; strongest-alternative: if feasibility cannot support the 25% target or alphabetical wins, ship telemetry and focused mode, preserve alphabetical scheduling, and omit performance-only scheduling/sharding complexity.)

## Dependencies

- Readiness may proceed without running tests or taking the OPEN slot. Baseline
  capture, activation, and implementation wait for the separately active
  `1tmb1` work to finish and for the shared runner/test corpus to be stable.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 53 | 661,585 |
| review | 3 | 0 |
| **Total** | **56** | **661,585** |

<!-- wave:context-efficiency-state {"generation":24,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":53,"content_source_credit":844790,"derived_artifact_credit":133,"direct_net":661585,"estimated_tokens_saved":661585,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3860,"response_debit":182669,"source_credit_count":41,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"review":{"calls":3,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-496,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":31,"response_debit":465,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":56,"content_source_credit":844790,"derived_artifact_credit":133,"direct_net":661089,"estimated_tokens_saved":661585,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3891,"response_debit":183134,"source_credit_count":41,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"wave_id":"1tmtx test-suite-performance"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
