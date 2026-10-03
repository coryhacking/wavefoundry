# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-02
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zlu1 lifecycle-features-for-distributions`
Title: Lifecycle Features For Distributions

## Objective

Add three lifecycle features a downstream distribution (Waveforge) asked for: close one change inside an open wave and move its newly unblocked dependents to `ready`, create a wave under a parent folder in the nested record layout, and scope project review lanes to readiness or delivery through `phase_gates`.

## Changes

Change ID: `1zlu2-enh close-one-change-and-activate-dependents`
Change Status: `implemented`

Change ID: `1zlu3-enh create-wave-parent-folder`
Change Status: `implemented`

Change ID: `1zlu4-enh phase-scoped-project-review-lanes`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-03

## Wave Summary

Wave `1zlu1` (Lifecycle Features For Distributions) delivered 3 changes: Close One Change And Activate Its Dependents, Create A Wave Under A Parent Folder, and Phase-Scoped Project Review Lanes. Notable adjustments during implementation: Close One Change And Activate Its Dependents: Delivery-review repair F5: `implemented` is now reachable, added to the allowed transitions from `ready`, `active` and `review` in `ALLOWED_CHANGE_STATUS_TRANSITIONS`; new lint test `test_implemented_is_reachable_from_ready_active_and_review` (`tests/test_docs_lint.py`, beside the transition-table test) shows a block with `Previous Change Status: active` and `Change Status: implemented` linting clean and the same block refused with the transition removed. Follow-up recorded (F6, left as is): a `Depends On:` line inside a fenced block of the wave record's member list is read by `_parse_change_records`, so it activates the dependent; this matches docs-lint, which reads the same line.; Close One Change And Activate Its Dependents: Implemented. `wf_close_change_response` beside `wf_close_wave_response` in `wf_server/server_impl.py` (decorated `@_fail_closed_on_record_layout("wf_close_change")`), the `wf_close_change` tool (publication lock on create), `wave_lint_lib/constants.py` gains `"implemented": {"implemented", "complete", "completed"}` (1zlu0 had added only `DONE_CHANGE_STATUSES`). Registry census (predicate: every literal `wf_close_wave` or `wf_mark_ac` in `.wavefoundry/framework/scripts/`, tests excluded, quoted or bare): `_LIFECYCLE_MUTATION_LOCK_TOOLS` added; `mcp_tool_roster.TOOL_TIERS` added (`TIER_WRITE`); `PUBLICATION_WRITER_REGISTRY` added (`lifecycle`, `fail_fast`); `_LIFECYCLE_CONTEXT_STAGES`, `_TRACKING_CONTEXT_TOOLS`, `_lifecycle_milestone_completed` (`if tool_name == "wf_close_wave"`) and `_COST_EXEMPT_TOOLS` none (the tool is not a stage transition and records no lifecycle context, so it takes the default first-party cost accounting like `wf_mark_ac`); `context_efficiency.LIFECYCLE_PROMPT_MAP` none (no lifecycle prompt of its own, as `wf_mark_ac`); `render_platform_surfaces` legacy rename map none (no legacy name); `render_agent_surfaces`, `wave_lint_lib/cli.py`, `wave_lint_lib/secrets_validators.py`, `wave_lint_lib/wave_validators.py`, `change_doc_checklist.py` none (prose about close or marking only); `wf_server/edit_gate_handlers.py` has no literal in the current tree. Hand-listed tables updated: `tests/test_archive_root.py` (12 writers), `tests/test_record_layout_lifecycle.py` (both wrapper lists), `tests/test_server_context_efficiency.py` `SERIALIZED_WAVE_WRITERS`, `tests/test_server_tools.py` expected set; `tests/test_lifecycle_mutation_lock.py` has no enumerated list, so the busy refusal is pinned in `tests/test_close_change.py`. Goldens: tool-surface golden adds the `wf_close_change` entry; handler digests add `wf_close_change`; label census adds one `writer` entry (the wave-record previous-status line). Roster counts and digests re-measured in `test_server_tools.py`, `test_server_tools_retrieval.py`, `test_extension_tool_modules.py` (lock tools 11 to 12). Advisory sanctioned set gains `close_change_lint_preexisting` and `dependencies_not_in_wave_record`. Docs-lint was confirmed lock-free (no lock use in `docs_lint.py` or `wave_lint_lib/`); the scoped lint runs in process. Deviations: dry-run reports `planned_writes` beside the empty `written`; refusal codes are `wave_not_open`, `change_not_admitted`, `change_doc_missing`/`change_doc_unreadable`, `change_status_not_closable`, `change_status_drift`, `silent_unchecked_items`, `dependencies_not_done`, `close_change_transition_invalid`, `close_change_lint_failed`, `close_change_write_failed`; AC-7 is exercised by writing every fixture in the loaded profile and running the suite under `--profile second`.; Phase-Scoped Project Review Lanes: Delivery-review repairs. F2: `wf_review_wave_response` computes its own roster only for the prepare phase; the implementation phase's `required_review_lanes_empty` advisory now reads `shared["required_lanes"]`, the roster the delivery gate enforces; `test_review_status_fails_when_executable_approval_is_missing` no longer patches the two server-level readers the implementation phase stopped calling. New test `test_delivery_only_roster_is_not_reported_empty_at_review` (no base lanes, `phase_gates.close.required_lanes = ["release-review"]`): Prepare writes `Required delivery lanes: release-review` and implementation-phase review reports no `required_review_lanes_empty` (prepare-phase review still does). F4b: spec, CHANGELOG and cross-cutting-concerns now say Implement, Review and Close report `required_review_lanes_invalid` and Prepare refuses through the policy-state config error. Nit: `normalize_phase_gates` strips a lane before the duplicate check; case `[" x", "x"]` added.

**Changes delivered:**

- **Close One Change And Activate Its Dependents** (`1zlu2-enh close-one-change-and-activate-dependents`) — An `implemented` dependency satisfies its dependents (activation and lint use `DONE_CHANGE_STATUSES` from `1zlu0`); `implemented` is closable by `wf_close_change` (to `complete`) and stays non-terminal
- **Create A Wave Under A Parent Folder** (`1zlu3-enh create-wave-parent-folder`) — 8 ACs completed. Key decisions: Optional `parent` on `wf_create_wave`, relative to the waves root; The parent must already exist
- **Phase-Scoped Project Review Lanes** (`1zlu4-enh phase-scoped-project-review-lanes`) — 8 ACs completed. Key decisions: Extend `phase_gates` with `required_lanes`; `required_review_lanes` keeps meaning both phases; One helper, `project_lanes_for_phase`, for every union site including the second loader
## Watchpoints

- Watchpoint: all three changes edit `wf_server/server_impl.py` and `1zlu2` and `1zlu4` both touch lifecycle support code; serialize those edits. Script edits need `framework_edit_allowed`; the seed 007 edit in `1zlu4` needs `seed_edit_allowed`.
- Watchpoint: `1zlu2` depends across waves on `1zlu0` (wave `1zls7`): it reuses the close-gate checklist collector that `1zltr` changes, and its closable-status set follows the `1zlu0` decision on the non-terminal `implemented` status. Implement `1zlu2` after `1zls7` lands; cross-wave dependencies are not declared.
- Watchpoint: `1zlu2` and `1zlu3` add or change MCP tool signatures, so the tool-surface golden and handler digests are regenerated once, after both land, and the MCP server is reloaded or restarted before verifying the new surface.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZLU1-PARENT-SWAP-AND-OVERRIDE-COMPAT | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-02: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: wf_close_change as first planned activated every planned change with no dependencies, unrelated to the closed one; resolved by limiting activation to changes whose Depends On names the closed change; strongest-alternative: store both review rosters in the receipt so delivery sites read the receipt, declined to keep the evaluator version at 7, with every roster reader enumerated by phase instead)
- Prepare council seat evidence (2026-10-02): one independent reviewer ran both seats and the code, qa, architecture and docs-contract lanes; round one found five blocking plan gaps (activation scope, unreachable archive refusal, helper placement, roster readers by phase, refusal before id mint) and eleven non-blocking items, all applied; red-team re-attacked the amendments (unrelated activation, symlink swap, deleted delivery line, malformed lane config) and found each refused; the docs-contract seat confirmed the shipped implement-wave sources are covered.

## Dependencies

- Ordering constraint (cross-wave, not declarable as a `Depends On:` line): `1zlu2` needs change `1zlu0` of wave `1zls7` implemented first, because it uses `DONE_CHANGE_STATUSES` and the docs-lint dependency rule that `1zlu0` introduces (and reuses the close-gate checklist collector that `1zltr` in the same wave changes). `1zlu3` and `1zlu4` have no external dependency.
- No intra-wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 48 | 3,588,823 |
| implement | 102 | 0 |
| review | 10 | 48,888 |
| **Total** | **160** | **3,637,711** |

<!-- wave:context-efficiency-state {"generation":146,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":102,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-19087,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3881,"response_debit":21034,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5828},"plan":{"calls":48,"content_source_credit":3659467,"derived_artifact_credit":5167,"direct_net":3588823,"estimated_tokens_saved":3588823,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3452,"response_debit":78870,"source_credit_count":111,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":10,"content_source_credit":73172,"derived_artifact_credit":1213,"direct_net":48888,"estimated_tokens_saved":48888,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3613,"response_debit":24200,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":160,"content_source_credit":3732639,"derived_artifact_credit":6380,"direct_net":3618624,"estimated_tokens_saved":3637711,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10946,"response_debit":124104,"source_credit_count":127,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14655},"wave_id":"1zlu1 lifecycle-features-for-distributions"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
