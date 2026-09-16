# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y3og setup-local-reconciliation`
Title: Setup Local Reconciliation

## Objective

Make plain wf setup reconcile the installed checkout and local indexes after a clone or git pull, retaining safe migration and recovery while core search can proceed with memory curation pending.

## Changes

Change ID: `1y3hc-enh setup-local-index-reconciliation`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: coordinator / senior-data-engineer; implementer (setup memory)
- Requested review lanes: architecture-reviewer, security-reviewer, qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-09-15

## Wave Summary

Plain `wf setup` reconciles fresh and Git-updated checkouts without an archive or manual purge. `wf setup --check` supplies read-only readiness and owner-specific recovery advice through CLI, MCP startup/monitor and index health. Agent guidance checks health after checkout-changing Git operations, including conflict stops, without automatic repair.

All eleven ACs and tasks completed; no `[~]` deferrals. Recovery retains source and owner identity; pending memory curation does not block core search. Three delivery findings were repaired and independently reverified; all six lanes and delivery council approved. Final full suite passed 9,096 tests across 94 modules (21 intentional skips), with a current green receipt. Full docs validation and close gates passed. Native Windows/Linux execution remains unverified.

Retrospective: test observers with actual producer output and share the setup parser. Promoted memory `1y5tz-mem validate-setup-readiness-against-canonical-producers` and project-context-memory record this lesson. Wave closed on 2026-09-15; changes remain uncommitted and unpackaged.

## Watchpoints

- Watchpoint: storage ownership, source drift, live old hosts, publication failure and pending memory must remain explicit. Coordinator serializes shared seams; independent specialists review current evidence.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| SETUP-ARGS-003 | do_now | no | completed | architecture-reviewer, qa-reviewer, wave-council-delivery |
| SETUP-OWNER-002 | do_now | no | completed | docs-contract-reviewer, architecture-reviewer, wave-council-delivery |
| SETUP-SURFACE-001 | do_now | no | completed | code-reviewer, qa-reviewer, wave-council-delivery |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
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
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- Operator authorized review and closure in the current request, 2026-09-15; typed signoff records that authority after review.

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 117 | 2,124,605 |
| implement | 386 | 4,230,310 |
| review | 77 | 517,611 |
| **Total** | **580** | **6,872,526** |

<!-- wave:context-efficiency-state {"generation":454,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":386,"content_source_credit":4953032,"derived_artifact_credit":1981,"direct_net":4230310,"estimated_tokens_saved":4230310,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14449,"response_debit":712157,"source_credit_count":146,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1903},"plan":{"calls":117,"content_source_credit":2400530,"derived_artifact_credit":2837,"direct_net":2124605,"estimated_tokens_saved":2124605,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6211,"response_debit":283031,"source_credit_count":70,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10480},"review":{"calls":77,"content_source_credit":641221,"derived_artifact_credit":1962,"direct_net":517611,"estimated_tokens_saved":517611,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":22954,"response_debit":104620,"source_credit_count":52,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2002}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":580,"content_source_credit":7994783,"derived_artifact_credit":6780,"direct_net":6872526,"estimated_tokens_saved":6872526,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":43614,"response_debit":1099808,"source_credit_count":268,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14385},"wave_id":"1y3og setup-local-reconciliation"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 29 | 0 | 19 | 25,981,519 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":19,"estimated_exploration_avoided":25981519,"surfaced_events":29} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-15: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; scope: AC-7–11). Independent source-grounded seats resolved bootstrap, stamp authority, stale rules and SQLite coordination concerns. Metadata-only inspection was explicitly weighed and rejected because it cannot establish current live-WAL schema/publication state. Operator permits coordination sidecars; check_final red-team closing reconciliation confirms final dispositions. Council synthesis approves implementation; historical maximum concern high, no remaining design blocker. No delivery behavior claimed. Code/docs/release planning lanes approved by check_council; architecture/security by dedicated contexts; QA by check_qa with final constraint recheck.

- Operator requested plan, Prepare, review and implementation on 2026-09-15; no close/commit/release authority.
- **Prepare-phase Wave Council [prepare-council] — 2026-09-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: migration seams assume upgrade ownership; strongest-alternative: bounded owner adapter reusing existing fences). Red-team reviewed actual checkpoint/restart/publication seams; its five primer constraints were incorporated. Fresh QA/docs-contract and architecture/security advisory contexts re-read the live final constraints and approved feasibility. Evidence: setup_wavefoundry.main, sqlite_storage_migration.restore_checkpoint/restart_command/verify_migration/cleanup_legacy, publication_control.publication_checkpoint_reason. Counterexamples considered: foreign receipt without storage, empty DB with old host, fingerprint mutation, failed graph/verification, pending-memory authority leak. No implementation behavior claimed.
- Allocation: coordinator owns integration/guidance; senior-data-engineer owns setup reconciliation helper/shared migration seams; implementer owns setup memory orchestration/tests. Model overrides unavailable absent explicit configuration; use current capable model for storage judgment, bounded assignments and early useful-output checks.

## Implementation outcome

All eleven ACs and tasks are delivered. Final full suite passed 9,096 tests across 94 modules (21 intentional skips); three delivery findings were independently repaired and reverified. Native Windows/Linux execution is not claimed; shell/path fixtures are not native qualification. Edit gates are closed. Operator requested review and closure on 2026-09-15; no commit or package is authorized.

## Setup-check extension

Operator selected `wf setup --check` on 2026-09-15. AC-7 through AC-11 add shared read-only assessment at CLI/MCP startup and through the existing monitor. Expanded scope passed fresh typed readiness and activation before edits. All extension ACs/tasks have focused evidence, and full suite/documentation validation passed. Prior baseline evidence remains historical, and no delivery/closure approval is inferred.

## Final delivery evidence — 2026-09-15

Independent code/QA, architecture/security and docs/release contexts approve final snapshot `33c78644dbfe56d34e7a7adb9dcb3980ee2ca58931ec4d2a555d99bf05299b2e`. Reviewers did not implement repairs. The final two-document correction was separately checked; remaining 31 reviewed files were unchanged. Typed findings and lane rechecks live in events.jsonl.

| Restored defect / boundary | Executed control | Result |
| --- | --- | --- |
| Three-argument-only MCP validation | Real five-host renderers, two passes | 10 assertion failures with mutant; repaired path passes |
| Missing Cursor cwd observation | Changed cwd and stamp signature | Mutant rejected |
| Divergent setup option whitelist | Actual shared parser options and restart command | 10 assertion failures with mutant |
| Bypassed setup grammar | Invalid flags / values | Four assertion failures with mutant |
| Upgrade-only setup recovery advice | Runtime/WAL failures through setup.session | Two assertion failures with mutant; source retained |
| Upgrade-only legacy-reader docs | Final owner-contract paragraph control | Old restriction rejected |

Code/QA executed 230 focused tests; architecture/security nine focused controls; docs/release 28 setup and four archive controls. Full framework suite: 9,096 tests, 94 modules, 21 intentional skips, green. Controls used disposable fixtures or in-memory mutations; no production mutation. These establish local behavior and guidance propagation, not native Windows/Linux execution or universal host adherence.

- **Delivery Wave Council — 2026-09-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer). Strongest challenge: shared conversion machinery must preserve owner/source identity across real renderer and parser output. Strongest alternative: upgrade-only conversion plus separate grammar; rejected because it defeats plain setup and reproduces drift. Independent council executed twelve controls and two old-behavior mutants (ten assertion failures each); final 33-file snapshot matched. Readiness delta remains within existing ACs and authority. All required lanes approved, no outstanding review findings or wave deferrals. Memory candidate rewritten/promoted; retrospective complete.
