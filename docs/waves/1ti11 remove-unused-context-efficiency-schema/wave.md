# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-25
review-evidence-source: events.jsonl

wave-id: `1ti11 remove-unused-context-efficiency-schema`
Title: Remove Unused Context Efficiency Schema

## Objective

Stop shipping the unused Context Efficiency pair JSON Schema while preserving
the scorer-backed paired-evaluation workflow and a clean upgrade path for
projects that received the file from an earlier pack.

## Changes

Change ID: `1th3p-maint remove-unused-context-efficiency-schema`
Change Status: `implemented`

Change ID: `1tj0k-bug reopen-wave-forces-implement-stage-attribution`
Change Status: `implemented`

Completed At: 2026-07-25

## Wave Summary

Wave `1ti11` (Remove Unused Context Efficiency Schema) delivered two changes: Remove the unused Context Efficiency pair schema and wf_reopen_wave forces implement-stage CE attribution even when reopening to review. Notable adjustments during implementation: Remove the unused Context Efficiency pair schema: Readiness council added a release-note requirement.; Remove the unused Context Efficiency pair schema: Removed the schema and replaced its positive distribution expectations with absence and upgrade-pruning coverage.; Remove the unused Context Efficiency pair schema: Independent delivery review re-tested the premise instead of accepting it: 19 mutation probes confirm `score_pairs` still rejects every constraint the deleted schema encoded (and is stricter on three), `mode="scaffold"` preserves the producer-facing shape from the same constants, and the prune test genuinely removes an installed copy plus the emptied directory. The emptied local `evals/` directory was removed; it was untracked, so it never reached the repository.

**Changes delivered:**

- **Remove the unused Context Efficiency pair schema** (`1th3p-maint remove-unused-context-efficiency-schema`) — 4 ACs completed. Key decisions: Remove rather than retain the schema as a source-only artifact.; Preserve closed-wave references.
- **wf_reopen_wave forces implement-stage CE attribution even when reopening to review** (`1tj0k-bug reopen-wave-forces-implement-stage-attribution`) — 8 ACs completed. Key decisions: Use an explicit `purpose` parameter; reject status-based inference.; Make `purpose` REQUIRED; delete `REOPEN_LEGACY_STAGE`, the omitted-purpose fallback, the `legacy_default` vocabulary, its compatibility test, and `focus_stage_source`.
## Watchpoints

- Watchpoint: preserve `score_context_efficiency_pairs.py` and scorer-derived scaffold
  behavior as the only executable contract.
- Watchpoint: exercise an old-pack-to-new-pack pruning fixture; a fresh-pack absence check
  alone does not prove existing target projects are cleaned.
- Watchpoint: keep closed wave history intact and leave the CHANGELOG unchanged
  per operator direction.

- **Independent delivery review — 2026-07-25: premise VERIFIED, no blocking findings.** The plan's load-bearing claim was re-tested rather than accepted:
  - **Constraint parity proven by mutation, not assertion.** The plan asserted the scorer is the executable contract; this review recovered the deleted schema from git and mutation-probed `score_pairs` with 19 payloads, one per schema constraint (`const` schema_version, minLength ids, `additionalProperties:false` at artifact/applicability/pair/arm/quality levels, all required-key sets, `minItems:1` pairs, integer 0-4 rubric bounds, non-negative token counts, integer `assisted_direct_net`). Every one is rejected by the scorer, and the scorer is STRICTER in three places the schema left open (`usage_source == provider_reported`, `quality_scored_blind is True`, strict bool `completed`). No validation was lost.
  - **Discoverability preserved and improved.** `wf_context_efficiency_eval(mode="scaffold")` writes a producer-facing skeleton derived from the scorer's own `ARM_KEYS`/`QUALITY_KEYS`/`PAIR_KEYS`, with placeholders that deliberately FAIL `score_pairs` until filled. Wave 1t72b built it with an explicit "no parallel schema" rationale, so the schema was already superseded by design rather than merely unused.
  - **Upgrade path is real.** `test_removed_context_efficiency_schema_is_pruned_on_upgrade` seeds the schema, omits it from the new MANIFEST, and asserts both the file and the emptied `evals/` directory are removed and reported. Not vacuous. `test_prune_framework` 17/17, `test_build_pack` 101/101.
  - **Census independently reproduced:** no live `.py` references the filename; remaining references are the negative packaging pins and closed-wave history, which the plan intentionally preserves.
  - **Cleanup applied:** the emptied `.wavefoundry/framework/evals/` directory was removed locally. It was untracked (git does not track empty directories) and the schema was the only file ever added under it, so this was local cruft rather than a repository or distribution defect.
  - **Open for operator confirmation (not a defect):** AC-5 and its task are `[~]` citing operator direction that this cleanup is not a release-note item, which overrode a readiness-council release-note requirement after the red-team seat challenged removing an intentionally shipped file. That direction is recorded consistently in three places but cannot be verified from this session's context; it is the one claim this review takes on trust and has referred back to the operator before close.

- **Prepare-phase Wave Council [prepare-council] — 2026-07-25: PASS (delta: late admission of `1tj0k`)** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: an explicit `purpose` parameter fixes the tool but leaves every existing caller on the legacy default, so attribution stays wrong wherever the canonical guidance is followed — resolved by expanding scope to the guidance surfaces that teach the flow, after code-grounded confirmation that seed 190 line ~112 instructs a bare `wf_reopen_wave(wave_id)` followed by `wf_review_wave` and repeats an incorrect closed-only claim that `wf_reopen_wave_response` contradicts with its `("closed", "paused")` guard; strongest-alternative: infer the stage from admitted change statuses so no caller has to change — rejected because reopening a fully-implemented wave to fix a late defect is legitimately implement work, so inference would guess, and a guessed default is what caused this defect)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| invalid-purpose-test-misses-focus-and-seal | do_now | no | completed | wave-council-delivery |
| reopen-failure-envelope-undocumented-and-unpinned | do_now | no | completed | wave-council-delivery |
| reopen-plan-retains-rejected-polarity | do_now | no | completed | wave-council-delivery |
| reopen-reports-unapplied-focus | do_now | no | completed | wave-council-delivery |

*Machine review evidence — 49 records; 15 runs; 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare seat evidence — red-team — 2026-07-25:** challenged the compatibility impact of removing an intentionally shipped file despite the zero-runtime-consumer census; the operator later narrowed the response to artifact and regression cleanup with no CHANGELOG entry.
- **Prepare seat evidence — docs-contract-reviewer — 2026-07-25:** no further findings after confirming closed wave history remains untouched and AC-5 records the operator-directed CHANGELOG exclusion.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-25: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: removing an intentionally shipped file could break an undisclosed out-of-tree harness even though no project tool consumes it; operator direction confines the response to artifact and regression cleanup with no CHANGELOG entry; strongest-alternative: retain and generate the schema from scorer constants as a documented public integration contract, rejected because no current tool or reference exposes that contract and the operator chose removal)

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: approved 2026-07-25 — operator ran an independent implementation review, returned APPROVED with zero code or contract findings, and directed closure.

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 7 | 0 |
| implement | 38 | 1,563,484 |
| review | 314 | 5,773,038 |
| paused | 1 | 0 |
| **Total** | **360** | **7,336,522** |

<!-- wave:context-efficiency-state {"generation":333,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":38,"content_source_credit":1624277,"derived_artifact_credit":0,"direct_net":1563484,"estimated_tokens_saved":1563484,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":997,"response_debit":62942,"source_credit_count":31,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3146},"paused":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-151,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10,"response_debit":141,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":7,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2216,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":77,"response_debit":5330,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"review":{"calls":314,"content_source_credit":6753958,"derived_artifact_credit":1520,"direct_net":5773038,"estimated_tokens_saved":5773038,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":40137,"response_debit":945353,"source_credit_count":240,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3050}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":360,"content_source_credit":8378235,"derived_artifact_credit":1520,"direct_net":7334155,"estimated_tokens_saved":7336522,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":41221,"response_debit":1013766,"source_credit_count":271,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9387},"wave_id":"1ti11 remove-unused-context-efficiency-schema"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 1 | 134080 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":134080,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
