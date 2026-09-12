# Wave Record

Owner: Engineering
Status: active
Last verified: 2026-09-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xq4f dashboard-lifecycle-integrity`
Title: Dashboard and Index Lifecycle Integrity

## Objective

Make dashboard lifecycle outcomes truthful and unified-index reads and recovery reliable across macOS, Windows and Linux. Dashboard processes must remain identifiable to their management tools; graph reads must describe one generation, failed builds must release database handles, runtime failures must explain recovery, and inventory tests must tolerate unavailable symlink privileges.

## Changes

Change ID: `1xpo1-bug dashboard-process-identity-and-lifecycle-honesty`
Change Status: `review`

Change ID: `1xoye-bug unified-index-compatibility-and-recovery`
Change Status: `review`

Change ID: `1x81v-debt files-seam-deletes-unlisted-rows`
Change Status: `review`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (dashboard L1–L3; compatibility C1–C4; targeted-build T1–T2)
- Requested review lanes: security-reviewer, performance-reviewer, release-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, performance-reviewer, security-reviewer

## Wave Summary

The admitted changes repair dashboard process identity/outcomes and the four demonstrated compatibility findings. The compatibility change retains unified SQLite and adds focused transaction, connection-lifetime, diagnostic and portable-fixture tests. Evidence: `compatibility-review.json`. Targeted `files=` builds also preserve unlisted content instead of treating a subset as the whole corpus. Native platform package qualification remains a separate outstanding release gate.

## Watchpoints

- The wave `1rswx` control must not be loosened: an `os.kill`-alive but cmdline-unverified process is never signalled, because a recycled process id is indistinguishable from a scan-missed dashboard without the cmdline check. AC-5 pins it, and `security-reviewer` is requested for that reason.
- Tests in this area start and stop real dashboard processes. Any lane that leaves one running holds a port in the configured range and will make a later test climb to the next port, so every launch needs a matching teardown.
- Compatibility C2 shares `server_impl.py`, `dashboard_lib.py`, `dashboard_server.py` and dashboard tests with dashboard L1/L2: serialize edits with one owner per file. C4 and L3 also share architecture documentation.
- Wave `1xny6` is closed. The operator authorized preparation, review and implementation of this three-change wave; it is now open. Closure still requires an explicit request.
- Follow-up, deliberately deferred out of this wave: the browser UI consumes neither the `upgrade_paused` snapshot field nor the `upgrade_status` SSE event, so the pause is invisible to anyone not reading `dashboard.log`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DELIVERY-001 | do_now | no | completed | architecture-reviewer, wave-council-delivery |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | withheld | repaired findings require fresh approval: ARCH-DELIVERY-001 | record a fresh independent approval for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 328 | 2,376,051 |
| implement | 224 | 2,634,363 |
| review | 84 | 1,280,106 |
| **Total** | **636** | **6,290,520** |

<!-- wave:context-efficiency-state {"generation":393,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":224,"content_source_credit":3641615,"derived_artifact_credit":258,"direct_net":2634363,"estimated_tokens_saved":2634363,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7143,"response_debit":1002452,"source_credit_count":45,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2085},"plan":{"calls":328,"content_source_credit":2921270,"derived_artifact_credit":2735,"direct_net":2376051,"estimated_tokens_saved":2376051,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13988,"response_debit":930667,"source_credit_count":116,"source_credit_drop_count":0,"structural_source_credit":388815,"workflow_prompt_credit":7886},"review":{"calls":84,"content_source_credit":1605503,"derived_artifact_credit":1527,"direct_net":1280106,"estimated_tokens_saved":1280106,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12103,"response_debit":314821,"source_credit_count":67,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":636,"content_source_credit":8168388,"derived_artifact_credit":4520,"direct_net":6290520,"estimated_tokens_saved":6290520,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":33234,"response_debit":2247940,"source_credit_count":228,"source_credit_drop_count":0,"structural_source_credit":388815,"workflow_prompt_credit":9971},"wave_id":"1xq4f dashboard-lifecycle-integrity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 12 | 0 | 8 | 8,133,053 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":8,"estimated_exploration_avoided":8133053,"surfaced_events":12} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

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
