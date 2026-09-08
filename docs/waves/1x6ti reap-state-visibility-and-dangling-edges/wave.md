# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1x6ti reap-state-visibility-and-dangling-edges`
Title: Reap State Visibility And Dangling Edges

## Objective

Close the two residuals the `1x54z` delivery review disclosed and parked. When this wave closes, an operator using the registered tools can see that the index deferred a mass-absent reap or is serving a walk-shadowed subtree as of its last readable build (today both states are visible only in the Python build result and the logs), and the served graph carries no edge to a node that does not exist (today a fragment's edge into a deleted doc, or into a symbol renamed while its doc was unreadable, resurfaces on the next unrelated merge and stays until a full rebuild). Now, because both gaps were measured this week on this repository's own graph and the mechanisms are fresh.

## Changes

Change ID: `1x551-debt index-health-surfaces-reap-deferral-and-preservation`
Change Status: `implemented`

Change ID: `1x5pc-bug dangling-doc-link-edge-after-linked-doc-deletion`
Change Status: `implemented`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer
- Product-owner admission review: operator-approved on 2026-09-04 by the instruction to plan, prepare, review and implement the next wave after `1x54z` closed with these two follow-ons recorded.

Completed At: 2026-09-05

## Wave Summary

Wave `1x6ti` (Reap State Visibility And Dangling Edges) delivered two changes: Surface Reap Deferral and Preservation Through index_build_status and index_health and A Doc-Link Edge Into a Deleted Doc Resurfaces on the Next Unrelated Build. Notable adjustments during implementation: Surface Reap Deferral and Preservation Through index_build_status and index_health: Delivery review cycle 1. QA-DEL-3 (QA lane): the reader validated only the outer shape, so a hand-edited or future-schema value with odd per-table entries was served verbatim; `reap_state_for_index` now coerces each entry (a deferred entry must be a dict of two non-negative integers, a preserved entry a non-negative integer count; anything else is dropped, and a record with no well-formed entry reads as none), pinned by `test_malformed_per_table_entries_are_dropped_by_the_reader`. DOCS-DEL-3: the Scope bullet names all four status states. DOCS-DEL-5: the parked plan is named (`1x81v`). ARCH-DEL-1: the Risks row names the three production-identity modules and the gate's trigger. The Decision Log header rows were narrowed for the coordinate census (see the `1x5pc` row and plan `1x81x`). QA-DEL-1 and QA-DEL-2 recorded as equivalent mutants (the source-side check is unreachable on real inputs; widening the exemption to known paths is equivalent by construction). CODE-DEL-2 (a second write-open of the store on every zero-change build) accepted as designed.; Surface Reap Deferral and Preservation Through index_build_status and index_health: Mutations before review (scratch copies, `mut_1x551/run.py`), each a clean removal, all killed by named tests: A zero-change write removed (6 tests, led by `test_deferred_zero_change_build_records_the_reap_state`); B build-path write removed (`test_shadowed_build_path_run_records_preserved_counts_stamped_with_the_published_generation`, `test_full_rebuild_clears_the_reap_state_record`); C idle-maintenance write removed (first SURVIVED, because no test reached the idle return with a deferral; `test_deferred_idle_maintenance_pass_records_the_reap_state_after_its_finalize` added, dirtying the epoch through `begin_build_epoch` so the zero-change build takes the idle path, then killed); D clear removed (first SURVIVED, because the reader hides an empty record; the three clear tests now also assert the raw meta key is absent through `IndexStateStore.get_meta`, then killed by `test_reap_state_record_clears_on_the_next_clean_build`, `test_full_rebuild_clears_the_reap_state_record` and the shadowed recovery); E dry-run guard removed (`test_dry_run_leaves_the_reap_state_record_untouched`); F exception re-raised (`test_reap_state_write_failure_never_fails_the_build`); G generation stamp zeroed (the two stamp tests); H shared reader returns None (4 of 5 server tests); I status block removed (`test_status_carries_the_reap_block_in_every_state_and_omits_it_without_a_record`, `test_status_and_health_read_the_same_record`); J health block removed (2 tests); K deferred diagnostic removed, L preserved diagnostic removed, M diagnostics not attached (`test_health_carries_the_block_and_one_diagnostic_per_non_empty_map`, `test_health_one_sided_record_raises_one_diagnostic` each). Two survivors surfaced two test gaps, both closed before review.; Surface Reap Deferral and Preservation Through index_build_status and index_health: Prepare council repairs on admission (red-team RED-PREP-3, 4, 5; docs-contract DOCS-PREP-5, 6, 7, 8, 9): the writer skips `dry_run` builds, which reach the zero-change preflight without the lock; the generation stamp is the store's published generation at the write; the no-epoch precedents corrected to the drift clear and `_record_drift_failure`; the `files=` seam sentence corrected (it runs the build-path reap; its unlisted-row deletion parked separately); the status block covers running and interrupted; the diagnostics fire per non-empty map, mirror the indexer's two-half message and match the neighbours' flag; the tool docstrings and spec rows added to the docs task.

**Changes delivered:**

- **Surface Reap Deferral and Preservation Through index_build_status and index_health** (`1x551-debt index-health-surfaces-reap-deferral-and-preservation`) — 8 ACs completed. Key decisions: Persist the two summaries in the state store's `meta` table at both reap seams and read them in the two response functions through one shared reader (divergent pre-plan, selected).; The writer skips `dry_run` builds; the stamp is the store's published generation at the write (after the epoch finalize on the build path); the no-epoch precedents are the drift clear and `_record_drift_failure` (readiness council RED-PREP-3, RED-PREP-4, DOCS-PREP-7; lanes ARCH-PREP-3, CODE-PREP-1).
- **A Doc-Link Edge Into a Deleted Doc Resurfaces on the Next Unrelated Build** (`1x5pc-bug dangling-doc-link-edge-after-linked-doc-deletion`) — 8 ACs completed. Key decisions: The exemption is membership in the node map, the `external::` namespace, or the build's current-path set; the filter runs before the zero-edge doc prune (readiness council, RED-PREP-1 and RED-PREP-2).; Filter dangling endpoints at payload assembly, `external::` excepted, with a stat and a builder-version bump (divergent pre-plan, selected).
## Watchpoints

- **Both changes touch fragile files with memories.** `indexer.py` and `graph_indexer.py` carry the `1x54z` fragile-file records (every consumer of the walk output; three readers of the current set and a disk-touching rescan) and `server_impl.py` carries the playbook memory (identify the seam, verify its paired producer and consumer). Read them before the first edit.
- **Red first, both changes.** `1x5pc`: the deleted-linked-doc differential against a full rebuild fails before the filter exists. `1x551`: the deferred zero-change record test fails before the writer exists.
- **The filter's blast radius is measured, not assumed.** `1x5pc` Requirement 5: a full rebuild of this repository with the filter records the dropped-edge count and classes; a class beyond the two known variants is investigated before the change ships.
- **A visibility aid never fails a build.** `1x551` AC-5: the store write at either reap seam is wrapped so a store error is logged and the build result still carries the summaries.
- **One reader, two surfaces.** `1x551` Requirement 4: both response functions read the record through the same state-store helper so status and health cannot disagree.
- **Mutations before review.** Every guard in both changes is deleted in a scratch copy and must fail a named test; the tables go in the Progress Logs.
- **Sequencing.** `1x5pc` first (a bounded merge change with a differential oracle), then `1x551`; the full suite runs last after the final framework edit so the receipt binds the final tree.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | not_issue | no | not_required | — |
| ARCH-DEL-2 | not_issue | no | not_required | — |
| ARCH-DEL-3 | not_issue | no | not_required | — |
| ARCH-RV1-1 | do_now | no | completed | architecture-reviewer, docs-contract-reviewer |
| ARCH-RV1-2 | not_issue | no | not_required | — |
| CODE-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |
| CODE-DEL-2 | not_issue | no | not_required | — |
| CODE-DEL-3 | do_now | no | completed | — |
| CODE-RV1-1 | do_now | no | completed | code-reviewer, qa-reviewer |
| CODE-RV1-2 | do_now | no | completed | code-reviewer, qa-reviewer, docs-contract-reviewer |
| CODE-RV2-1 | dont_do_later | no | not_required | — |
| DOCS-DEL-1 | do_now | no | completed | docs-contract-reviewer |
| DOCS-DEL-2 | not_issue | no | not_required | — |
| DOCS-DEL-3 | not_issue | no | not_required | — |
| DOCS-DEL-4 | not_issue | no | not_required | — |
| DOCS-DEL-5 | not_issue | no | not_required | — |
| DOCS-RV1-1 | do_now | no | completed | docs-contract-reviewer |
| DOCS-RV1-2 | do_now | no | completed | docs-contract-reviewer, architecture-reviewer |
| DOCS-RV2-1 | not_issue | no | not_required | — |
| QA-DEL-1 | dont_do_later | no | not_required | — |
| QA-DEL-2 | not_issue | no | not_required | — |
| QA-DEL-3 | do_now | no | completed | qa-reviewer |
| QA-DEL-4 | not_issue | no | not_required | — |
| QA-RV1-1 | not_issue | no | not_required | — |
| QA-RV1-2 | do_now | no | completed | qa-reviewer, code-reviewer |
| QA-RV1-3 | do_now | no | completed | qa-reviewer |
| QA-RV1-4 | dont_do_later | no | not_required | — |
| QA-RV2-1 | dont_do_later | no | not_required | — |
| QA-RV2-2 | dont_do_later | no | not_required | — |

*Machine review state — 29 findings; current: do_now 11, maybe_later 0, dont_do_later 5, not_issue 13*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Follows wave `1x54z eligibility-reap-absence-guards` (CLOSED 2026-09-04), whose delivery review recorded both changes (SEC-DEL-1, SEC-RV1-1, RED-RV2-1, ARCH-RV3-1) and whose walk-shadow preservation `1x5pc` builds on.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-04: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `1x5pc`'s filter conflated an endpoint gone from the tree with an endpoint the graph never nodes, so a node-map-only exemption would have removed six real edges on this repository (links to files the graph never nodes, to scan-excluded docs, and memory targets into `docs/waves/`) from full and incremental builds alike, invisibly to an edge-key differential, and a filter placed after the zero-edge doc prune left an orphan node the oracle prunes; strongest-alternative: mint path nodes for node-less current paths, rejected because it changes the node set for every consumer for a class the graph deliberately does not node, in favour of exempting current-path endpoints and running the filter before the zero-edge doc prune with `assert_equivalent` as the oracle)
  - red-team seat (executed, temp repositories and a census of this repository's served graph): the deleted-linked-doc sequence reproduces the dangling edge through the real merge and a from-scratch oracle carries no such edge; the census found 11,027 `external::` endpoints and six non-external node-less edges in three classes, all with targets present on disk (RED-PREP-1, do_now, repaired on admission); a post-prune filter leaves a doc whose only link was deleted as a zero-edge node (RED-PREP-2, do_now, repaired: filter before the prune, `assert_equivalent` oracle); `build_index(dry_run=True)` reaches the zero-change preflight without the lock (RED-PREP-3, do_now, repaired: the writer skips dry runs); the named meta-write precedents are epoch-bound, the true no-epoch precedents are the drift clear and `_record_drift_failure` (RED-PREP-4, conforming, Rationale corrected); the `files=` seam does run the build-path reap and deletes every unlisted row, pre-existing and unreachable (RED-PREP-5, maybe_later: Scope corrected, parked as plan `1x81v`); the builder bump's two test pins, the synchronous first-query rebuild and the production-identity perturbation were undisclosed (RED-PREP-6, conforming, added). A full rebuild resets nothing in `meta`; no consumer enumerates `meta`; the stats file is server-derived from the log and nothing the indexer returns reaches the two tools.
  - docs-contract-reviewer seat: the proposed `reap` block and diagnostics fit the `_response` and `_diagnostic` conventions of the neighbouring health diagnostics (none set the advisory flag); item 15's follow-on sentence can become shipped behaviour without contradicting the rest of item 15; `graph-index-system.md`'s finalize output-pass order sentence and the retirement clause must change with `1x5pc` and `docs/RELIABILITY.md`'s builder-version claim is enforced by the claims engine (DOCS-PREP-1, 2, repaired); `1x5pc` AC-3 contradicted AC-4 (DOCS-PREP-3, repaired); the CHANGELOG Upgrading note counts builder moves (DOCS-PREP-4, added to the task); `1x551`'s diagnostics fire per non-empty map and the status block covers running and interrupted (DOCS-PREP-5, 6, repaired); the generation stamp is the store's published generation (DOCS-PREP-7, repaired); the registered tool docstrings and spec rows are contract surfaces (DOCS-PREP-8, added); the deferral message carries both halves (DOCS-PREP-9, repaired). Every AC in both plans asserts change-controlled outcomes; the AC Priority tables are complete.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 173 | 3,664,083 |
| implement | 69 | 542,040 |
| review | 338 | 10,431,671 |
| **Total** | **580** | **14,637,794** |

<!-- wave:context-efficiency-state {"generation":578,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":69,"content_source_credit":579890,"derived_artifact_credit":382,"direct_net":542040,"estimated_tokens_saved":542040,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10323,"response_debit":32820,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4911},"plan":{"calls":173,"content_source_credit":4201507,"derived_artifact_credit":1228,"direct_net":3664083,"estimated_tokens_saved":3664083,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6911,"response_debit":539627,"source_credit_count":105,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7886},"review":{"calls":338,"content_source_credit":11703803,"derived_artifact_credit":4397,"direct_net":10431671,"estimated_tokens_saved":10431671,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":62294,"response_debit":1216124,"source_credit_count":794,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":580,"content_source_credit":16485200,"derived_artifact_credit":6007,"direct_net":14637794,"estimated_tokens_saved":14637794,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":79528,"response_debit":1788571,"source_credit_count":916,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14686},"wave_id":"1x6ti reap-state-visibility-and-dangling-edges"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 26 | 0 | 7 | 9,812,542 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":9812542,"surfaced_events":26} -->
<!-- wave:exploration-avoided end -->
