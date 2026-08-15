# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ve3e cleanup-review-followups`
Title: Cleanup Review Followups

## Objective

Land the two verified follow-ups from the 2026-08-15 codebase cleanup review: correct the `accel_embedder` docstring that falsely labels the live offline/CA resident fallback as unreachable dead code (the sweep's original removal verdict was falsified at plan time and is withdrawn), and fix seed 160's dangling references to nonexistent `docs/prompts/agents/` bodies. When this wave closes, neither false claim can misdirect a future sweep or upgrade agent.

## Changes

Change ID: `1ve3c-bug accel-resident-branch-docstring-false-unreachability`
Change Status: `implemented`

Change ID: `1ve3d-doc seed-160-dangling-agents-prompt-references`
Change Status: `implemented`

## Participants

- Coordinator: agent session coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, docs-contract-reviewer

Completed At: 2026-08-15

## Wave Summary

Wave `1ve3e` (Cleanup Review Followups) delivered two changes: accel_embedder docstring falsely claims the resident branch is unreachable and Seed 160 references agents-prompt bodies that do not exist. Notable adjustments during implementation: Seed 160 references agents-prompt bodies that do not exist: Implemented under one `seed_edit_allowed` cycle: the specialist-bodies preamble now states the optional when-present semantics ("absence is a valid state, never a backfill obligation") governing all four bullets, so the architecture-reviewer entry stays as a reconcile-when-present member; the ghost `docs/prompts/agents/upgrade-wavefoundry.md` reference removed from the upgrade-contract line. Mirror check: the rendered `docs/prompts/upgrade-wavefoundry.prompt.md` never carried either dangling reference (grep 0), so no mirror edit was needed. Sweep: no seed names a `prompts/agents/` member as expected-present that this repo lacks. `test_shipped_reference_docs` 12/12 OK.

**Changes delivered:**

- **accel_embedder docstring falsely claims the resident branch is unreachable** (`1ve3c-bug accel-resident-branch-docstring-false-unreachability`) — 2 ACs completed. Key decisions: Withdraw the cleanup review's `remove` verdict; fix the docstring instead and keep the branch.
- **Seed 160 references agents-prompt bodies that do not exist** (`1ve3d-doc seed-160-dangling-agents-prompt-references`) — 3 ACs completed. Key decisions: Correct the seed to when-present semantics rather than backfilling the missing body.
## Watchpoints

- **Watchpoint, the withdrawn verdict is the story:** the cleanup review recommended removing the resident branch and the operator approved it; plan-time verification falsified the premise against the code and tests. `1ve3c` records the withdrawal; nothing in this wave deletes code.
- **Watchpoint, `1ve3c` must stay comment-only:** no executable line of `accel_embedder.py` changes; the diff is the proof.
- **Watchpoint, `1ve3d` seed edits** run under one `seed_edit_allowed` cycle, with a rendered-doc mirror check on `docs/prompts/upgrade-wavefoundry.prompt.md`.
- **Follow-up (outside this wave):** the broader `docs/prompts/agents/` pruning stays referred to Framework config review per the cleanup report's F2.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the wave exists because its own predecessor claim failed adversarial verification, so the residual risk is overcorrection, a docstring so hedged it stops warning against real dead code, mitigated by `1ve3c` AC-1 requiring both concrete routes into the branch to be named rather than vague caution; strongest-alternative: proceed with the operator-approved removal of the resident branch, rejected because the plan-time census falsified its premise against `_resolve_clean_onnx`'s degradation path and the executed offline-fallback tests)

Seat evidence (code-grounded, verified against the tree 2026-08-15):

- red-team: every plan claim resolves against HEAD: the `_resolve_model_files` docstring carries the false "unreachable" sentence; `_resolve_clean_onnx`'s except path prints "falling back to the resident model path" and returns `None` for registered models on fetch failure; `test_resolve_downloads_resident_model_on_cold_cache` and `test_resolve_none_when_resident_unavailable_after_fetch` execute the branch; seed 160 names `docs/prompts/agents/architecture-reviewer.prompt.md` in the backfill list and `docs/prompts/agents/upgrade-wavefoundry.md` in the upgrade-contract line while neither file exists; the directory README declares members optional non-public helpers. No findings beyond the plans' own content.
- docs-contract-reviewer: `1ve3d`'s when-present correction matches the directory README's declared semantics and the sibling code-reviewer bullet's existing phrasing; the mirror-check obligation on the rendered upgrade prompt is an explicit AC; no `docs/specs/` surface changes in either plan; AC Priority populated at plan time in both docs. No findings.

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
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 16 | 13,395 |
| implement | 25 | 0 |
| review | 10 | 11,635 |
| **Total** | **51** | **25,030** |

<!-- wave:context-efficiency-state {"generation":47,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":25,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-4315,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":879,"response_debit":4158,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":722},"plan":{"calls":16,"content_source_credit":24341,"derived_artifact_credit":2684,"direct_net":13395,"estimated_tokens_saved":13395,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2282,"response_debit":14854,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":10,"content_source_credit":22485,"derived_artifact_credit":823,"direct_net":11635,"estimated_tokens_saved":11635,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1979,"response_debit":11040,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":51,"content_source_credit":46826,"derived_artifact_credit":3507,"direct_net":20715,"estimated_tokens_saved":25030,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5140,"response_debit":30052,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5574},"wave_id":"1ve3e cleanup-review-followups"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
