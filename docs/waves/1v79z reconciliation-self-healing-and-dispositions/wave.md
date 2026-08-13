# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1v79z reconciliation-self-healing-and-dispositions`
Title: Reconciliation Self Healing And Dispositions

## Objective

Close two gaps the 1.16.2 field run exposed in the reconciliation surface. A renderer-managed generated file drifts from its framework default permanently and in both directions because nothing reconciles it and the scan excludes it; and the scan's only disposition is "unresolved", so a finding that is correct as written can be silenced only by rewriting a record the framework's own seeded policy protects.

## Changes

Change ID: `1v7a0-bug generated-manifest-never-reconciles-against-default`
Change Status: `implemented`

Change ID: `1v7a1-bug reconciliation-findings-have-no-historical-record-disposition`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (gardener reconciliation, scan disposition), qa (drift fixtures, per-finding suppression assertions)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-08-12

## Wave Summary

Wave `1v79z` (Reconciliation Self Healing And Dispositions) delivered two changes: Generated Manifest Never Reconciles Against Its Default and Reconciliation Findings Have No Historical-Record Disposition. Notable adjustments during implementation: Generated Manifest Never Reconciles Against Its Default: **Readiness council: AC-3's hazard is concrete, not theoretical.** The manifest keys the default does not own have real consumers OUTSIDE the gardener, so a wholesale payload replacement would break working behaviour rather than merely lose metadata: `framework_revision` is written by `build_pack` and read by `check_version` and `dashboard_lib`; `wave_root` is read by `wave_lint_lib` (`wave_validators`, `cli`), so clobbering it would break docs-lint itself; `upgrade_merge_notes` is referenced by `reconcile_scan` as the rationale for excluding this file from the scan. The merge MUST be scoped to the keys `default_manifest_payload` owns.

**Changes delivered:**

- **Generated Manifest Never Reconciles Against Its Default** (`1v7a0-bug generated-manifest-never-reconciles-against-default`) — 6 ACs completed. Key decisions: Fix by reconciling in the gardener rather than by removing the file from the scan's exclusion set.; Do NOT hand-edit this repository's manifest ahead of the fix.
- **Reconciliation Findings Have No Historical-Record Disposition** (`1v7a1-bug reconciliation-findings-have-no-historical-record-disposition`) — 6 ACs completed. Key decisions: Follow the `scan-findings.json` disposition model rather than designing a new one.; Sequence this change BEFORE widening the journal patterns.
## Watchpoints

- **Sequencing (recorded as a decision in `1v7a1`):** widening the journal patterns to further morphological variants (`journal distillation`, `journals distilled`, `distilling journal lessons`; roughly 12 sites in this repo) comes AFTER `1v7a1` lands. Broader patterns without a disposition multiply exactly the unresolvable findings `1v7a1` exists to fix, and would ship as noise to every downstream repo at once. File it; do not fold it in.
- **Watchpoint:** `1v7a0`'s merge must be scoped to the keys `default_manifest_payload` owns. Non-default keys have live consumers outside the gardener — `wave_root` is read by `wave_lint_lib`, so clobbering it breaks docs-lint itself; `framework_revision` is read by `check_version` and `dashboard_lib`. A wholesale payload replacement is a working-behaviour regression, not just metadata loss.
- **Watchpoint:** do NOT hand-edit `docs/prompts/prompt-surface-manifest.json`. Its stale `agent_journals` entry and three missing `generated_artifacts` entries are `1v7a0`'s local reproduction, and AC-5 proves the fix against that real artifact.
- **Watchpoint:** `1v7a1` must not auto-classify a finding as historical. The channel is report-only so that judgment stays with the operator; a heuristic that guessed wrong would fail silently in both directions.
- **Follow-up (do not expand this wave):** `generated_personas` also has no Python reader. It was NOT exhaustively searched across non-Python surfaces, so it must not be swept in with `agent_journals`; it needs its own census.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| manifest-reconcile-never-reaches-steady-state | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-12: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: PASS is conditional on two corrections already applied to the plans before this verdict was recorded, not on a clean first read; both changes originate in a downstream field report, so the risk is approving a plan whose load-bearing claims were checked only against the reporter's prose; every claim was therefore re-derived here, which confirmed both defects, corrected one citation, and turned up a hazard neither the report nor the first draft named: the manifest keys the default does not own have live consumers, so a wholesale payload replacement would break docs-lint rather than merely lose metadata; strongest-alternative: un-exclude `prompt-surface-manifest.json` from the scan so the drift is at least reported, rejected because the file is renderer-managed and an operator cannot fix the drift by editing it — the next render rewrites it, so reporting it would be recurring homework with no resolution, which is the same defect `1v7a1` exists to remove)

Seat evidence:

- **red-team** — verified code-grounded, not from the report. `ensure_manifest` performs only two `setdefault` calls plus a `last_gardened_at` stamp on an existing file and never consults `default_manifest_payload`; `prompt-surface-manifest.json` is excluded from the scan by basename. Both halves of the reported defect hold. Two findings the report did NOT contain. First, drift is BIDIRECTIONAL: this repository's `generated_artifacts` is missing `docs/waves/README.md`, `docs/agents/personas/README.md` and `docs/reports/`, all present in the current default, so a repo installed before those were added never receives them — the framework's own picture of what it generates is wrong, which is worse than a stale entry nobody reads. Second, AC-3's preservation requirement is a concrete regression risk, not a hygiene note: `wave_root` is read by `wave_lint_lib` (`wave_validators`, `cli`), so a wholesale merge would break docs-lint itself, and `framework_revision` is read by `check_version` and `dashboard_lib`. Confirmed `enabled_internal_features` has no reader anywhere in the repository across `.py`, `.md` and `.json`. Flagged `generated_personas` as a possible second dead key but explicitly did NOT clear it: only Python surfaces were searched, so it must not be swept in with `agent_journals`.
- **docs-contract-reviewer** — one correction, applied before approval. `1v7a1` attributed the sentence "retiring a file removes the file, not the historical record of it" to `AGENTS.md` **Cleanup and Destructive Operations**. That exact sentence is not in `AGENTS.md`; it is in seed-160 and seed-220, and `AGENTS.md` carries the equivalent rule in its own wording under **Historical reference preservation**. The citation is corrected in the plan. This strengthens the change rather than weakening it: because the rule is SEEDED, every target repository inherits it, so the conflict between the scan's suggestion text and the framework's own policy is shipped to every consumer rather than being a local quirk of this repo. No blocking finding.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 13 | 0 |
| implement | 3 | 0 |
| review | 20 | 72,450 |
| **Total** | **36** | **72,450** |

<!-- wave:context-efficiency-state {"generation":36,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":3,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-194,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19,"response_debit":175,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":13,"content_source_credit":6022,"derived_artifact_credit":2147,"direct_net":-1489,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1735,"response_debit":11429,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":20,"content_source_credit":112251,"derived_artifact_credit":2071,"direct_net":72450,"estimated_tokens_saved":72450,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9560,"response_debit":33658,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":36,"content_source_credit":118273,"derived_artifact_credit":4218,"direct_net":70767,"estimated_tokens_saved":72450,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11314,"response_debit":45262,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4852},"wave_id":"1v79z reconciliation-self-healing-and-dispositions"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
