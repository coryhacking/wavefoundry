# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1vbuu cleanup-review-reachability`
Title: Cleanup Review Reachability

## Objective

Close the two gaps the 1ve3e post-mortem isolated behind the false removal verdict: teach the cleanup review that a conditionally-guarded fallback branch is a condition-reachability question (read the sentinel producers and the module's tests; treat prose unreachability claims as hypotheses), and make `code_impact` say so when its empty test-caller result reflects invisibility rather than absence. When this wave closes, the sweep applies the right probe to fallback branches and the tool no longer reports a silent empty.

## Changes

Change ID: `1vbut-enh cleanup-review-condition-reachability-and-test-blindspot`
Change Status: `implemented`

## Participants

- Coordinator: agent session coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-08-15

## Wave Summary

Wave `1vbuu` (Cleanup Review Reachability) delivered one change: Cleanup review: condition-reachability rule and the test-coverage blind spot. Notable adjustments during implementation: Cleanup review: condition-reachability rule and the test-coverage blind spot: Implemented. Seed 221 gained the two-class reachability rule (node vs condition, three-step probe, prose-as-hypothesis, the accel case as the recorded example) under one `seed_edit_allowed` cycle; the repo-local cleanup prompt mirrors it. `code_impact` now attaches the advisory `test_callers_not_visible` exactly when `include_tests=true` and zero affected nodes are test-path (pure function of already-computed data, no extra traversal; `include_tests=false` path untouched). Three-state tests added to `TestCodeImpactIncludeTests` and passing. `docs/specs/mcp-tool-surface.md` gained one clause. Live find during implementation: the full suite's `test_advisory_tags_appear_only_at_the_sanctioned_sites` guard (1uugg AC-10c) correctly rejected the new `advisory=True` site, since the sanctioned set is a security control preventing silent softening of lifecycle gates; extended the sanctioned set with the new read-only site (`_code_impact_graph_response`, `test_callers_not_visible`) as a reviewed, deliberate addition with a comment stating why it can soften nothing. Full suite 7244 across 62 files OK; docs-lint clean.

**Changes delivered:**

- **Cleanup review: condition-reachability rule and the test-coverage blind spot** (`1vbut-enh cleanup-review-condition-reachability-and-test-blindspot`) — 4 ACs completed. Key decisions: Fix the RULE (two reachability classes) plus a visibility DIAGNOSTIC; do not extend the graph with path predicates.; Make the empty test-caller result a diagnostic, not a filled-in answer.
## Watchpoints

- **Watchpoint, the diagnostic must not be noise:** it fires only in the zero-test-affected state; the positive-control fixture (a repo whose test file IS indexed and hits) must show no diagnostic.
- **Watchpoint, `server_impl.py` is a fragile file:** follow the playbook memory (envelope seam + paired consumer) before editing.
- **Watchpoint, seed edits** under one `seed_edit_allowed` cycle; the repo-local cleanup prompt is hand-authored, so its mirror is a direct edit, not a render.
- **Follow-up (deferred by decision):** path predicates on call edges; revisit only if condition-reachability misfires recur.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the diagnostic could become ambient noise in every repository with an index-excluded test tree, since `include_tests=true` on any symbol without indexed test callers would fire it, mitigated by scoping to the zero-test-affected state, by the positive-control fixture (a hit suppresses it), and by making it advisory rather than error; strongest-alternative: extend the graph with path predicates so condition reachability becomes queryable, evaluated and deferred because the graph answered node reachability correctly and the failure was a reviewer applying the wrong class of rule, which a third overridable fact does not fix)

Seat evidence (code-grounded, verified against the tree 2026-08-15):

- red-team: every load-bearing claim resolves. Seed 221 `## Maintainability & Dead-Code` at line 82 with the "Zero static references does NOT mean dead" block at line 106; the repo-local cleanup prompt has exactly one script mention outside the skill registry (none writes it), so it is hand-authored; `code_impact_response` filters `affected_raw` by `_is_test_path` only when `include_tests` is false and builds `affected` at the OK path, so the zero-test-affected condition is computable at the response seam; `_is_test_path` is defined by directory segments and filename regex; `TestCodeImpactIncludeTests` already carries a fake-graph fixture with an indexed test caller, giving the positive control for free. Graph probe reproduced: 10,719 test-path nodes overall, 0 for `test_accel_embedder.py`, 3 non-test affected nodes for the accel helper. No findings.
- docs-contract-reviewer: seed 221 is the canonical owner of the safety rule and the plan edits it under `seed_edit_allowed`; the repo-local prompt mirror is a direct edit with the AC stating it; `docs/specs/mcp-tool-surface.md` may need one diagnostic-code line (plan flags the check at implement); AC Priority populated at plan time; serialization points are pure paths. No findings.

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
| plan | 15 | 388,176 |
| implement | 6 | 0 |
| review | 10 | 21,424 |
| **Total** | **31** | **409,600** |

<!-- wave:context-efficiency-state {"generation":27,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":6,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-328,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":52,"response_debit":276,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":15,"content_source_credit":404209,"derived_artifact_credit":2046,"direct_net":388176,"estimated_tokens_saved":388176,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2312,"response_debit":19273,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":10,"content_source_credit":34636,"derived_artifact_credit":1126,"direct_net":21424,"estimated_tokens_saved":21424,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2143,"response_debit":13541,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":31,"content_source_credit":438845,"derived_artifact_credit":3172,"direct_net":409272,"estimated_tokens_saved":409600,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4507,"response_debit":33090,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4852},"wave_id":"1vbuu cleanup-review-reachability"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
