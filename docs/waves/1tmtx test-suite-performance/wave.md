# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-27
review-evidence-source: events.jsonl

wave-id: `1tmtx test-suite-performance`
Title: Test Suite Performance
review-policy-reprepare-required: false
## Objective

Reduce the canonical framework suite's measured critical-path wall time without
weakening its per-file subprocess isolation or delivery authority. The wave adds
per-file timing and a cache-safe focused repair mode, selects scheduling through
a controlled comparison, and splits the dominant server-tool test module only
if the measured critical path proves the split worthwhile.

## Changes

Change ID: `1tm6d-enh test-suite-critical-path-acceleration`
Change Status: `complete`

Completed At: 2026-08-27

## Wave Summary

Wave `1tmtx` (Test Suite Performance) delivered one change: Canonical Test Suite Critical-Path Acceleration. Notable adjustments during implementation: Canonical Test Suite Critical-Path Acceleration: Re-prepare after the review-policy receipt lapsed (evaluator v7; targeted council: red-team primer, docs-contract-reviewer). Fresh census: 64 test files; `test_server_tools.py` at 37,610 lines and roughly 1,742 tests; the only import-level consumers remain `test_graph_query.py` and `test_render_platform_surfaces.py`; path-literal couplings found in `test_events_only_residue_census.py` and the self-referential basename filter. Eight prose repairs applied: census-predicate extension, residue-census scope addition, exception-map pre-identification, activation-checkpoint trigger replacing the stale `1tmb1` condition, alphabetical-fallback tense fix, `--no-cache` advisory-read disclosure, forced-skip control scoping, and the caller census supporting Requirement 9.; Canonical Test Suite Critical-Path Acceleration: Thought then Observe: telemetry (Task 2) implemented as `FileResult` (name, returncode, output, test_count, elapsed_s, skip_count), child-elapsed measured around the worker invocation, skip counts parsed from the unittest result tail, bounded top-10 and worker-service-time summary added on both success and failure paths; existing summary lines byte-identical. Eight regressions added in `test_run_tests_cache.py` (focused run 45/45 green). Level 1 finding on the first instrumented series: all four runs failed with one error, the pre-existing 4-tuple unpack of `_run_file` in `test_run_tests_lock.RunFileEncodingTests` (a runner-API consumer the plan census, scoped to `test_server_tools` couplings, did not cover). Fixed to consume `FileResult`; focused lock file green; failed series archived at `evidence/logs/attempt1/`; instrumented series re-running on the corrected frozen source. Reflect: internal-API shape changes need a callers grep across the whole tests tree, not only the census scoped to the file being decomposed.; Canonical Test Suite Critical-Path Acceleration: Observe: Tasks 4 and 6 landed (advisory `durations_s` persistence with independent validation and single cache read; strict argv parsing; benchmark-only `--schedule-control` interface; focused `--file` mode with complete hash/cache/timing isolation and canonical-seam call-order proofs); 47 new regressions, focused file 92/92 green, end-to-end smoke of focused/usage/exclusivity passed, full canonical suite green. Level 2 finding while verifying: the runner's per-file count parse took the FIRST unanchored "Ran N tests" match from merged output, so `test_run_tests_cache.py`'s mock main() output ("Ran 42 tests across 1 files", the default `tests_run=42`) had been read as the file's count, inflating the suite total by 5 (reported 7,499 versus the census-true 7,494). Repaired in `_run_file` by anchoring count and skip parsing to the LAST unittest summary ("Ran N tests? in X.XXXs") and the tail after it; two known-bad regressions added; focused file 94/94 green. Post-fix totals are true counts and will differ from historical runner-reported totals.

**Changes delivered:**

- **Canonical Test Suite Critical-Path Acceleration** (`1tm6d-enh test-suite-critical-path-acceleration`) — 9 ACs completed. Key decisions: Deliver telemetry and focused mode; select scheduling and physical sharding only after controlled measurement.; Preserve file-level subprocess isolation and the six-worker cap.
## Participants

- Coordinator/moderator: primary Codex coordinator / wave-council
- Review seats: red-team, architecture-reviewer, security-reviewer,
  qa-reviewer, reality-checker, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer
- Implementation owners: framework-engineer, test-engineer,
  performance-reviewer, docs-contract-reviewer

## Watchpoints

- Blocking: at the first implementation checkpoint after activation, confirm no
  concurrent writes to the runner/test corpus remain, then freeze the digest,
  exact identity/fingerprint inventory, skips, environment, and original-source
  external baseline before any runner edit; telemetry-only evidence then
  establishes the pre-optimization distribution.
- Watchpoint: longest-first is a hypothesis, not an approval claim; compare it with the
  current schedule because starting several heavy shards together may saturate
  CPU or I/O.
- Blocking: physical sharding is also a hypothesis. Proceed only if measured
  tail time and the feasibility bound support it; permit one measured rebalance,
  then require an operator disposition rather than expanding the design.
- Blocking: focused runs are diagnostic only and must never read or update the complete
  suite's last-green cache evidence.
- Watchpoint: couplings to `test_server_tools.py` are path-shaped, not only
  import-shaped: `test_events_only_residue_census.py` pins its path in five
  allowance frozensets and a scope non-vacuity assertion, and one reader-census
  test filters grep hits by its own basename. On the sharding branch these are
  expected mechanical re-points under the census predicate; see Requirement 6
  and Requirement 7 in the change doc.
- Follow-up boundary: preserve the six-worker cap and one-subprocess-per-file model; per-file result
  caching, monolithic discovery, distributed execution, and deleted coverage are
  explicitly outside this wave.

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
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- The initial readiness approval record was premature: it predated the final
  red-team and docs-contract seats. It is superseded by the post-repair council
  checkpoint recorded below and remains history rather than current authority.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-26: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: do not infer the critical path or preselect scheduling/sharding from file size while `1tmb1` is changing the corpus—freeze and measure first, then bootstrap a complete post-layout timing manifest before comparing schedules; strongest-alternative: if feasibility cannot support the 25% target or alphabetical wins, ship telemetry and focused mode, preserve alphabetical scheduling, and omit performance-only scheduling/sharding complexity.)
- **Prepare-phase Wave Council [prepare-council] — 2026-08-27: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the shard-census predicate covered only imports and dynamic execution while today's couplings are path-shaped, five `TEST_ALLOWANCES` pins plus a scope non-vacuity assertion in `test_events_only_residue_census.py` and a self-referential basename filter, with the repair site outside licensed scope; repaired at prepare by extending the census predicate, adding the census file to scope narrowly, and pre-identifying the exception-map entry; strongest-alternative: class-level unittest dispatch of the dominant file's TestCase classes into the existing worker pool instead of physical sharding; recorded and dispositioned in the Decision Log, revisitable by operator direction if the feasibility gate rejects sharding.)

- **Delivery review [initial_delivery] — 2026-08-27: PASS** (lanes: code-reviewer, qa-reviewer, architecture-reviewer, each an independent fresh-context reviewer with executed probes; no delivery council required by the current policy receipt). All three lanes returned APPROVE. Findings and resolutions: qa F1 (unarchived focused-shard-log citation) repaired inline by archiving `evidence/logs/focused-shards.log` and re-pointing the citation; architecture F1 (census predicate blind to package-qualified `tests.test_*` imports, hiding a second pre-existing coupling) repaired by widening the predicate and disclosing `test_techdocs_audit_lib.py` importing `tests.test_render_agent_surfaces`, verifier re-run green; architecture F2 (stale docstring pointer in `test_review_policy.py`) re-pointed to the lifecycle shard; architecture F3 (evidence bytecode) deleted; code finding 1 (dead `Guard._SPAWN_ATTRS` literal) repaired by aliasing the support set object; code finding 3 (non-dict cache JSON crash, inherited) repaired with an `isinstance` guard and a new regression. Code findings 2 (post-summary stderr could corrupt advisory telemetry; structural fix out of proportion) and 5 (an in-tree timings manifest fails closed with a misleading message) are recorded `dont_do_later`; finding 4 (empty-directory executor edge, pre-existing) is `not_issue`. All repairs were independently re-verified by their originating lanes before the typed approvals were recorded; post-repair canonical suite 7,554 tests across 66 files green with 3 skips. No material disagreements between lanes.
- Per-seat evidence for the 2026-07-26 full council (red-team,
  architecture-reviewer, security-reviewer, qa-reviewer, reality-checker,
  performance-reviewer, docs-contract-reviewer): each seat's findings and the
  three plan-repair passes they drove are summarized in the change doc's
  2026-07-26 Progress Log rows and in `events.jsonl`
  (`ev-approval-wave-council-readiness`, `ev-approval-wave-council-readiness-2`);
  that checkpoint is history superseded by the 2026-08-27 targeted council
  above, whose seat evidence (red-team, docs-contract-reviewer) lives in the
  change doc's 2026-08-27 re-prepare Progress Log row and `run-readiness-2`.

## Dependencies

- Readiness may proceed without running tests or taking the OPEN slot. Baseline
  capture happens at the first implementation checkpoint after activation, once
  no concurrent writer to the runner/test corpus remains. (`1tmb1`, the
  planning-time concurrent writer, is closed; the corpus still grew afterward,
  so activation-time freshness is the operative condition, not any wave's
  closure.)

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 97 | 2,035,983 |
| implement | 54 | 0 |
| review | 36 | 101,749 |
| **Total** | **187** | **2,137,732** |

<!-- wave:context-efficiency-state {"generation":151,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":54,"content_source_credit":12005,"derived_artifact_credit":0,"direct_net":-6158,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2418,"response_debit":19767,"source_credit_count":7,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4022},"plan":{"calls":97,"content_source_credit":2289761,"derived_artifact_credit":309,"direct_net":2035983,"estimated_tokens_saved":2035983,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10486,"response_debit":251172,"source_credit_count":91,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7571},"review":{"calls":36,"content_source_credit":165716,"derived_artifact_credit":493,"direct_net":101749,"estimated_tokens_saved":101749,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5790,"response_debit":60016,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":187,"content_source_credit":2467482,"derived_artifact_credit":802,"direct_net":2131574,"estimated_tokens_saved":2137732,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18694,"response_debit":330955,"source_credit_count":115,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12939},"wave_id":"1tmtx test-suite-performance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 4 | 4,896,621 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":4896621,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
