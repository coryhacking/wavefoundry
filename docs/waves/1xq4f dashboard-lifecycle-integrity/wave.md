# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xq4f dashboard-lifecycle-integrity`
Title: Dashboard and Index Lifecycle Integrity

## Objective

Make dashboard lifecycle outcomes truthful and unified-index reads and recovery reliable across macOS, Windows and Linux. Dashboard processes must remain identifiable to their management tools; graph reads must describe one generation, failed builds must release database handles, runtime failures must explain recovery, and inventory tests must tolerate unavailable symlink privileges.

## Changes

Change ID: `1xpo1-bug dashboard-process-identity-and-lifecycle-honesty`
Change Status: `complete`

Change ID: `1xoye-bug unified-index-compatibility-and-recovery`
Change Status: `complete`

Change ID: `1x81v-debt files-seam-deletes-unlisted-rows`
Change Status: `complete`

Change ID: `1xs59-bug upgrade-bootstrap-and-tracked-ignore-hygiene`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (dashboard L1–L3; compatibility C1–C4; targeted-build T1–T2)
- Requested review lanes: security-reviewer, performance-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-09-12

## Wave Summary

Wave `1xq4f` (Dashboard and Index Lifecycle Integrity) delivered 4 changes: Dashboard Process Identity and Lifecycle Honesty, Unified Index Compatibility and Recovery, Preserve Unlisted Content During Targeted Index Builds, and Upgrade Bootstrap and Tracked-Ignore Hygiene.

**Changes delivered:**

- **Dashboard Process Identity and Lifecycle Honesty** (`1xpo1-bug dashboard-process-identity-and-lifecycle-honesty`) — 6 ACs completed. Key decisions: Tag the child process with its resolved root, and pair that with honest restart and start reporting.
- **Unified Index Compatibility and Recovery** (`1xoye-bug unified-index-compatibility-and-recovery`) — 4 ACs completed. Key decisions: Select focused repairs within unified SQLite and keep native qualification separate.; Track the four findings as one separate bug change in `1xq4f`.
- **Preserve Unlisted Content During Targeted Index Builds** (`1x81v-debt files-seam-deletes-unlisted-rows`) — 3 ACs completed. Key decisions: Keep `files=` as a partial update; preserve unlisted content.; Refuse selection plus whole-index rebuild requirements.
- **Upgrade Bootstrap and Tracked-Ignore Hygiene** (`1xs59-bug upgrade-bootstrap-and-tracked-ignore-hygiene`) — 5 ACs completed. Key decisions: Skip upgrade-only bootstrap extraction at both current and old-runner boundaries.; Warn using Git's matching of canonical patterns; never untrack automatically.

All 18 ACs and all tasks are complete; there are no `[~]` AC deferrals. All seven specialist lanes, readiness and delivery councils, and operator signoff are reconciled in typed evidence. Both review findings were repaired and independently reverified. Final validation passed 8,902 tests (12 skips) with a matching receipt and clean docs gate.

Retrospective and memory checkpoint: prevent bootstrap extraction before writes even with an old active coordinator; preserve Git ownership; describe automatic schema reconciliation before the real docs-gate recovery point. These lessons are retained in canonical code and seed160. The post-reconciliation memory proposal returned zero candidates, so no pending validation or new promotion remains. Reports are consolidated in `upgrade-fixes-evidence.json`. Handoff is idle. Native platform execution and the out-of-wave watchpoints remain release/follow-up work.

## Watchpoints

- The wave `1rswx` control must not be loosened: an `os.kill`-alive but cmdline-unverified process is never signalled, because a recycled process id is indistinguishable from a scan-missed dashboard without the cmdline check. AC-5 pins it, and `security-reviewer` is requested for that reason.
- Tests in this area start and stop real dashboard processes. Any lane that leaves one running holds a port in the configured range and will make a later test climb to the next port, so every launch needs a matching teardown.
- Compatibility C2 shares `server_impl.py`, `dashboard_lib.py`, `dashboard_server.py` and dashboard tests with dashboard L1/L2: serialize edits with one owner per file. C4 and L3 also share architecture documentation.
- Wave `1xny6` is closed. The operator authorized preparation, review and implementation of the initial three-change wave; all four admitted changes are now closed. The current “finish it” request authorizes closure after the required checks.
- Follow-up, deliberately deferred out of this wave: the browser UI consumes neither the `upgrade_paused` snapshot field nor the `upgrade_status` SSE event, so the pause is invisible to anyone not reading `dashboard.log`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DELIVERY-001 | do_now | no | completed | architecture-reviewer, wave-council-delivery |
| schema-guidance-promises-unavailable-edit-window | do_now | no | completed | docs-contract-reviewer, wave-council-delivery |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- Operator closure authorization: current “finish it” request; typed operator-signoff recorded after supplied destination validation.

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 369 | 2,713,857 |
| implement | 265 | 2,902,325 |
| review | 254 | 4,307,925 |
| **Total** | **888** | **9,924,107** |

<!-- wave:context-efficiency-state {"generation":662,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":265,"content_source_credit":3924679,"derived_artifact_credit":258,"direct_net":2902325,"estimated_tokens_saved":2902325,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8236,"response_debit":1019006,"source_credit_count":50,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4630},"plan":{"calls":369,"content_source_credit":3329363,"derived_artifact_credit":2735,"direct_net":2713857,"estimated_tokens_saved":2713857,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15389,"response_debit":999553,"source_credit_count":131,"source_credit_drop_count":0,"structural_source_credit":388815,"workflow_prompt_credit":7886},"review":{"calls":254,"content_source_credit":5069077,"derived_artifact_credit":6303,"direct_net":4307925,"estimated_tokens_saved":4307925,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":34684,"response_debit":734660,"source_credit_count":196,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":888,"content_source_credit":12323119,"derived_artifact_credit":9296,"direct_net":9924107,"estimated_tokens_saved":9924107,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":58309,"response_debit":2753219,"source_credit_count":377,"source_credit_drop_count":0,"structural_source_credit":388815,"workflow_prompt_credit":14405},"wave_id":"1xq4f dashboard-lifecycle-integrity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 41 | 0 | 15 | 18,394,585 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":15,"estimated_exploration_avoided":18394585,"surfaced_events":41} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- **2026-09-12 final delivery: approved.** All seven specialist lanes and the targeted council are current for the four-change boundary. The schema-guidance finding is repaired and independently reverified in cycle 2. See `upgrade-fixes-evidence.json#/final_delivery` for exact shared-context disclosures, tests, mutants and limitations. Operator signoff is recorded. Final full suite passed 8,902 tests with 12 skips; the receipt hash was independently recomputed and matched. The initial 154 ms/150 ms timing failure and clean rerun are retained in evidence; no threshold was changed.

- **2026-09-11 delivery review: PASS (specialists and council).** All six required lanes approve; one architecture documentation finding (`ARCH-DELIVERY-001`) was repaired and independently reverified in cycle 1. The targeted council passed unanimously (standard primer; red-team and docs-contract-reviewer seats). Reports, mutations, shared-context disclosures and probe sources are consolidated in `delivery-review.json`; typed approvals and repair history are in `events.jsonl`. The canonical 8,898-test receipt remains current. Memory proposal produced zero candidates. Native Windows/Linux/Intel package qualification remains release gate G4. Operator signoff, closure and commit remain pending.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-11: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: partial work must not certify global currency or weaken exact-root signal authority; strongest-alternative: explicit scoped refusal instead of silently expanding to a complete walk). Refreshed receipt `review-policy-baa8d09a45eed5eb68ce`; independently executed current feasibility controls and per-seat evidence are in `delivery-review.json`. This refresh follows implementation-time document edits and is not retroactive preimplementation approval.

- **2026-09-11 implementation complete, ready for delivery review.** All three changes have completed ACs/tasks. The canonical suite passed 8,898 tests across 86 files (12 skips); its receipt matches the final framework hash. Twenty falsifying controls and the full validation record are consolidated in `implementation-evidence.json`. The first complete run's map-generator failure was repaired and the entire suite rerun. Docs/changelog are updated. Required delivery approvals, native package qualification and operator-owned closure remain pending.

- **2026-09-11 three-change readiness: PASS and activated.** The expanded wave passed Prepare, all six specialist readiness lanes and council approval (`ev-approval-wave-council-readiness-3`, receipt `review-policy-3594b1460c29848fe4c0`). Current reports are consolidated in `readiness-review.json`; earlier checkpoints below retain their historical scope. Implementation is underway, with focused results in `implementation-evidence.json`. Delivery approvals remain pending.

- **2026-09-11 additional admission:** operator approved `1x81v` targeted-build preservation and the documentation-only dashboard metadata path correction. Re-Prepare the three-change boundary. The upgrade-pause banner remains out of scope. T1 shares C1 ownership; no concurrent indexer writes.

- **2026-09-11 scope expansion — re-Prepare required.** The operator requested admission of all four compatibility findings as `1xoye`. The dashboard-only approval below is historical; it does not approve the expanded wave. Re-Prepare must refresh the review-policy receipt and obtain a new readiness review, including the requested performance and release coverage. No implementation or delivery approval is claimed.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-11: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: child cwd rebinding and native unquoted spaced roots defeat launcher-only identity; strongest-alternative: normalized argv plus bounded existing scanner repair and explicit lifecycle outcomes). Council roster follows the bound targeted policy. Supplemental QA and architecture/reality reviews passed; architecture and reality were two lenses in one reviewer context, not independent seats. The fresh independent moderator also performed code-grounded readiness validation.
- Dashboard-only seat agreement at the earlier review: unanimous; max remaining severity: none. Earlier plan gaps were repaired and independently re-read before approval. Consolidated report: `readiness-review.json`.
- Earlier dashboard-only plan review stop condition met: Requirements, AC and Scope branches resolved; no operator questions remain. Product-owner intent is the admitted dashboard repair and the operator's prepare/review request. Required delivery lanes are code, QA, architecture and security; no delivery approval is claimed.
- Readiness checks cover plan feasibility and selected native macOS process probes. Implementation, named mutation proofs, full lifecycle tests and native Windows/Linux execution remain future work.
