# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-29
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zep5 migration-reader-provisioning`
Title: Migration Reader Provisioning

## Objective

A failed install of the legacy storage-migration reader during an upgrade is reported like any other dependency failure (`dependency_provisioning_failed`, naming `wf setup`) on every upgrade path, instead of a generic index failure or an escaping exit. Follow-up recorded at the close of wave `1zfd9`.

## Changes

Change ID: `1zfda-bug upgrade-migration-reader-provisioning`
Change Status: `complete`

## Participants

- Coordinator: wave coordinator (main session)
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-09-30

## Wave Summary

Wave `1zep5` (Migration Reader Provisioning) delivered one change: Upgrade Reports Migration-Reader Provisioning Failures Like the Dependency Step. Notable adjustments during implementation: Upgrade Reports Migration-Reader Provisioning Failures Like the Dependency Step: Readiness review (code, QA, release lanes; council red-team and security). B1 adopted via the council alternative: `ensure_deps` is not redundant (the metadata precheck cannot see a venv that needs rebuilding), so it stays and both branch calls share the dependency step's classification; former AC-3 (remove `ensure_deps`) replaced. B2 adopted: AC-1 now names the lock fields, output line, exit and `wf_upgrade` envelope, since no structured summary is produced on this failure. Advisories adopted: raise regardless of receipt state (Requirement 2), `SystemExit` behaviour wording (Requirement 4), `--update-index` and exit-1 scoping (Requirement 3), exact exception set, `test_sqlite_storage_migration.py` added, CHANGELOG amendment detail.

**Changes delivered:**

- **Upgrade Reports Migration-Reader Provisioning Failures Like the Dependency Step** (`1zfda-bug upgrade-migration-reader-provisioning`) — 5 ACs completed. Key decisions: Keep the branch's `ensure_deps` and route both branch calls through a helper extracted from the dependency step
## Watchpoints

- Watchpoint: `upgrade_wavefoundry.py` is a fragile file (memory `1u8q3-mem`): exercise the Phase 4 test cluster, and stub installs module-wide (memory `1zfii-mem`).
- Transition lag: like the 1zfd9 step, this runs in the Phase 4 orchestrator and takes effect from the upgrade after the one that installs it.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-AC1-ENVELOPE-UNTESTED | do_now | no | completed | qa-reviewer, code-reviewer, wave-council-delivery |

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
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the plan's premise that the migration branch's `ensure_deps` was redundant was wrong, since the dependency step's metadata precheck cannot see a venv that needs rebuilding; the call now stays and both branch calls share the dependency step's classification; strongest-alternative: also make the precheck skip the installer only when `setup_index._venv_needs_bootstrap()` is False, so non-migration paths get the dependency classification too; recorded as a possible later change, not required here)
- Prepare council seat evidence (2026-09-30): red-team blocked the round-1 premise that the migration branch's `ensure_deps` was redundant (the metadata precheck cannot see a venv that needs rebuilding) and approved the revised plan; security-reviewer found no trust or integrity concern (the raise precedes `migrate_legacy` and publication, the caught set is exact, the reader keeps uv with the age guard and the `==0.33.0` pin) and approved.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 30 | 398,586 |
| implement | 29 | 840,325 |
| review | 14 | 91,999 |
| **Total** | **73** | **1,330,910** |

<!-- wave:context-efficiency-state {"generation":69,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":29,"content_source_credit":906194,"derived_artifact_credit":0,"direct_net":840325,"estimated_tokens_saved":840325,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1056,"response_debit":64813,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":30,"content_source_credit":441916,"derived_artifact_credit":2207,"direct_net":398586,"estimated_tokens_saved":398586,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1721,"response_debit":50327,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":14,"content_source_credit":112326,"derived_artifact_credit":2250,"direct_net":91999,"estimated_tokens_saved":91999,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4315,"response_debit":20578,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":73,"content_source_credit":1460436,"derived_artifact_credit":4457,"direct_net":1330910,"estimated_tokens_saved":1330910,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7092,"response_debit":135718,"source_credit_count":75,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8827},"wave_id":"1zep5 migration-reader-provisioning"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 4 | 4,456,582 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":4456582,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
