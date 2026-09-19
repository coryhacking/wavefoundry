# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-18
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0h0 typed-phase-gates`
Title: Typed Phase Gates

## Objective

When this wave closes, the prepare, review, and close checks are named gate units in ordered per-phase lists, and a target repository can require additional named sensors per phase through a typed `phase_gates` configuration block, with no repository code loaded by the server and nothing executed in dry-run. This is the second wave that unblocks Waveforge's adoption.

## Changes

Change ID: `1y044-ref extract-lifecycle-gate-units`
Change Status: `complete`

Change ID: `1y0bd-enh config-declared-phase-gates`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-18

## Wave Summary

Wave `1y0h0` (Typed Phase Gates) delivered two changes: Extract Lifecycle Gate Checks Into Named Units and Config-Declared Phase Gates. Notable adjustments during implementation: Extract Lifecycle Gate Checks Into Named Units: Observe: focused lifecycle/lock corpus covered 571 cases. One source-inspection pin initially ran while import formatting shifted line positions; its fresh two-test class passed after the tree froze. All 27 new behavioral/structural/golden tests pass together. Existing tests repointed in `test_server_tools_lifecycle.py`, `test_lifecycle_mutation_lock.py`, `test_record_layout_lifecycle.py`; 99 original direct/patch sites migrated, AST seam/advisory/evaluator pins expanded. All moved mocks have call assertions; the review-prepare subcase explicitly asserts its council neutralizer is not called because that branch never checks council (other cases prove calls). Full 106-file suite is running on the frozen tree.; Extract Lifecycle Gate Checks Into Named Units: Observe: pre-extraction golden replay failed with 74 differences caused by time-derived fixture IDs and their receipt digests. Reflect: three rapid runs did not prove clock independence. Fixed only producer inputs in `build_fixtures`: frozen UTC clock and scoped allocation-state reset/restore. Original golden bytes unchanged (`e72420b5…`); three tests pass including future-clock/prior-allocation isolation and known-bad diagnostic detection. Extraction began only after this baseline was green.; Extract Lifecycle Gate Checks Into Named Units: Readiness repair: four lanes blocked. Line-number citations replaced with symbol names and re-verified after `8545c4f9`; the "interleaving is overstated" claim corrected (prepare is interleaved, review and close are not) and the size estimate re-scoped; `GateResult` and the context field list added to Requirement 1; prepare split into four staged tuples in Requirement 2; the import-direction rule and its test added (Requirement 3, AC-8); the single-OPEN guard, lint-translation, checkbox-completeness, and `_force_gates_closed` boundaries stated; the AC-1 oracle moved from "the current repository" to three `_make_repo` fixtures with a committed golden; AC-4 made a new pickup test; AC-6 given its AST mechanism. Operator decisions recorded in `1y0bd`: sensors execute only in `create`/`apply`, and `phase_gates` carries `required_sensors` only

**Changes delivered:**

- **Extract Lifecycle Gate Checks Into Named Units** (`1y044-ref extract-lifecycle-gate-units`) — 9 ACs completed. Key decisions: Flat sibling module with static phase tuples, no discovery; Extract close first, then review, then prepare
- **Config-Declared Phase Gates** (`1y0bd-enh config-declared-phase-gates`) — 9 ACs completed. Key decisions: Config-declared typed gates; no imported policy code; Dedicated `phase_gates` key rather than fields inside `review_policies`
## Watchpoints

- `1y044` must land before `1y0bd`; the configured gates append to the phase tuples the refactor creates.
- Evidence authority stays `events.jsonl` through `read_review_event_ledger`; the facade-only test in `1y044` is the guard.
- The `review_policies` config key is digested but never parsed; do not give it semantics here. `phase_gates` is a separate key.
- Dry-run executes nothing (operator decision 2026-09-18): prepare `dry_run`/`evaluate` and close `dry_run` list each gate as `would_run` and emit one advisory `phase_sensor_not_executed` per gate. Sensor execution in prepare `ready`/`create` and close `create` is the same trust boundary as `wf_run_sensors`, restricted to list-form commands (no `shell=True`; a non-list command is refused before any spawn), with `configured_gates` provenance on every phase response.
- Documenting `phase_gates` in seeds and rendered `AGENTS.md` for target repositories is a seed-gated follow-up.
- Golden tool-surface fixture from `1y0do` must remain unchanged.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| RT-F1 | do_now | no | completed | — |
| RT-F3 | do_now | no | completed | — |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- `1y0do tool-surface-snapshot` should close first.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| credit_history_unavailable | 0 | 0 |

<!-- wave:context-efficiency-state {"generation":233,"measurement_status":"credit_history_unavailable","pending":false,"schema_version":1,"stages":{"implement":{"calls":38,"content_source_credit":1081013,"derived_artifact_credit":1148,"direct_net":977462,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1035,"response_debit":105901,"source_credit_count":33,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2237},"plan":{"calls":151,"content_source_credit":2870969,"derived_artifact_credit":1346,"direct_net":2657373,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10902,"response_debit":208622,"source_credit_count":124,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4582},"review":{"calls":40,"content_source_credit":670691,"derived_artifact_credit":2041,"direct_net":565957,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14777,"response_debit":94000,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":229,"content_source_credit":4622673,"derived_artifact_credit":4535,"direct_net":4200792,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":26714,"response_debit":408523,"source_credit_count":191,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8821},"wave_id":"1y0h0 typed-phase-gates"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 4 | 5,236,181 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":5236181,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the sensor-execution reuse path was an unnamed, unfalsifiable proposition; strongest-alternative: name the function and its shared-module home directly in the requirement, applied in-session).
- **Prepare-phase Wave Council [prepare-council] — 2026-09-18: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the wave answered repeated enumeration defects by replacing enumerations with derivations, but a derivation recorded in a document is not a gate, and two of the checks introduced to fix that were self-scoping with no floor and so were green on a tree where the mechanism was never implemented; strongest-alternative: make the runtime obligation the binding half, since an uncalled mock fails whether or not a scanner found the site, and give every remaining derived scope a floor that names members rather than deferring to a count its own author records, both applied in-session)

## Extraction implementation checkpoint

2026-09-18: `1y044` complete. Close, review, and four prepare stages moved to named gate units; original lifecycle and tool-surface goldens remain byte-identical. Framework suite: 9,304 tests across 106 files, 12 skips, green current receipt. All 16 units have positive/negative coverage and diagnostics-suppression mutants killed; structural/reload tests pass. Implementation lanes: generic implementer for production extraction, two QA implementation lanes for computational behavioral/structural verification, coordinator for fixture repair and integration. These checks do not claim the independent delivery approvals required after the companion change.

`1y0bd` remains planned and is next; the wave remains implementing. No wave closure or commit performed.
