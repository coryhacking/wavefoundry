# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-24
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `21ilh dashboard-start-failure-diagnostics`
Title: Dashboard Start Failure Diagnostics

## Objective

Operators and maintainers see why a dashboard child failed to start, and the identity test stops depending on a free default port range. Boundaries: the spawn stays all-DEVNULL and detached on every platform, including the Windows creation flags; no pipe is added.

## Changes

Change ID: `21ilg-bug dashboard-start-hides-child-startup-failure`
Change Status: `implemented`

## Participants

- Coordinator: implementer
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-10-24

## Wave Summary

Wave `21ilh` (Dashboard Start Failure Diagnostics) delivered one change: Dashboard Start Hides the Child's Startup Failure. Notable adjustments during implementation: Dashboard Start Hides the Child's Startup Failure: Readiness round 1 amendments. From red-team's strongest challenge: the catch widened to the whole pre-serve section, with an explicit lock release; the residual import-time failures are stated. From security: exact line format, 500-character cap, line treated as data. From qa and code: AC-1 sets `preferred_port` and the range to a held `127.0.0.1` port with no metadata port; AC-2 simulates Windows on the handler module's `os`, with `create=True` constants; AC-3 also checks the metadata `port` and the catch's lock release; AC-4 holds ports in try/finally and accepts `EADDRINUSE`. Requirement 6's claim of existing spawn pins was corrected: none exist. The leaked dashboards came from cleanup that Waveforge's sandbox could not complete, which is out of scope.

Intent outcome: achieved here, not yet established downstream. With every port in the range held, a real dashboard child now exits with `dashboard_child_exited` and the message carries its `startup failed: RuntimeError: No free dashboard port available ...` line; a lock that cannot be taken is logged the same way, and the failure path closes the server and releases the lock even when `server_close` fails. `--port 0` records the bound port, and the identity test runs on an ephemeral port with 43127-43129 held. The spawn stays all-DEVNULL and detached, pinned exactly on POSIX and simulated Windows (`0x08000208`). Full suite 12113 tests OK. The measure of success is the distribution's next report, which cannot be read yet. Limitations: failures before `main` runs (import or venv) cannot reach the log; leftover dashboards for other repositories are not reaped.

**Changes delivered:**

- **Dashboard Start Hides the Child's Startup Failure** (`21ilg-bug dashboard-start-hides-child-startup-failure`) — 6 ACs completed. Key decisions: Keep the all-DEVNULL detached spawn; surface the reason through the existing `dashboard.log`; Fix the identity test with `port=0` and record the bound port
## Watchpoints

- Watchpoint: the spawn kwargs must stay unchanged; Windows handle inheritance was fixed in wave 2134v.
- Watchpoint: framework edits need `framework_edit_allowed`.

## Review Checkpoints

Intent outcome: achieved here, not yet established downstream. With every port in the range held, a real dashboard child now exits with `dashboard_child_exited` and the message carries its `startup failed: RuntimeError: No free dashboard port available ...` line; a lock that cannot be taken is logged the same way, and the failure path closes the server and releases the lock even when `server_close` fails. `--port 0` records the bound port, and the identity test runs on an ephemeral port with 43127-43129 held. The spawn stays all-DEVNULL and detached, pinned exactly on POSIX and simulated Windows (`0x08000208`). Full suite 12113 tests OK. The measure of success is the distribution's next report, which cannot be read yet. Limitations: failures before `main` runs (import or venv) cannot reach the log; leftover dashboards for other repositories are not reaped.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| RED-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 87 | 4,094,721 |
| implement | 17 | 145,430 |
| review | 14 | 31,222 |
| **Total** | **118** | **4,271,373** |

<!-- wave:context-efficiency-state {"generation":112,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":17,"content_source_credit":179612,"derived_artifact_credit":0,"direct_net":145430,"estimated_tokens_saved":145430,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":337,"response_debit":33845,"source_credit_count":7,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":87,"content_source_credit":4247936,"derived_artifact_credit":2173,"direct_net":4094721,"estimated_tokens_saved":4094721,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4352,"response_debit":155493,"source_credit_count":112,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4457},"review":{"calls":14,"content_source_credit":60182,"derived_artifact_credit":1079,"direct_net":31222,"estimated_tokens_saved":31222,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4106,"response_debit":29168,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3235}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":118,"content_source_credit":4487730,"derived_artifact_credit":3252,"direct_net":4271373,"estimated_tokens_saved":4271373,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8795,"response_debit":218506,"source_credit_count":135,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7692},"wave_id":"21ilh dashboard-start-failure-diagnostics"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 1 | 56,659 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":56659,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
