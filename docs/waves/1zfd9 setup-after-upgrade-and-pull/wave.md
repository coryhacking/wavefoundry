# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-29
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zfd9 setup-after-upgrade-and-pull`
Title: Setup After Upgrade And Pull

## Objective

A framework version that adds a required package (psutil, wave 1zc7n) leaves every repository with the package installed or a clear `wf setup` recommendation, whether it arrived through `wf upgrade` or a `git pull` of a committed upgrade. Needed before the release that ships psutil.

## Changes

Change ID: `1zcm3-enh setup-after-upgrade-and-pull`
Change Status: `implementing`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: security-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-09-29

## Wave Summary

Wave `1zfd9` (Setup After Upgrade And Pull) delivered one change: Setup Follows An Upgrade And A Pull. Notable adjustments during implementation: Setup Follows An Upgrade And A Pull: Delivery repair round 1 (seven findings). Startup review: DEL-STARTUP-ENTRY-UNTESTED (end-to-end tests now run the real `__main__` entry via runpy; background-failure case; found and fixed a real race: the background thread now publishes the reassessment before recording its final status). Operator-pasted review: DEL-INSTALL-LOCK-OWNERSHIP (lock errors fail closed; `ensure_deps` / `ensure_migration_deps` take the lock before `_bootstrap_venv`; venv creation and the uv bootstrap pass the carrier on POSIX), DEL-UV-CONFIG-ISOLATION (`_uv_config_args`: operator user/system `uv.toml` via `--config-file`, else `--no-config`; verified against uv 0.12.4 that an explicit file skips discovery), DEL-SETUP-COMMAND-QUOTING (`setup_readiness.format_command`). Upgrade review: DEL-TRANSITION-NOTE-WRONG (CHANGELOG, seed 160, prompt), DEL-PHASE4-TESTS-REACH-INSTALLER (`test_upgrade_wavefoundry` stubs the metadata read module-wide), DEL-UPGRADE-COVERAGE-GAPS (tests for the cleanup flag, delegated summary, oversized bounding, pending-migration raise, no stamp after a dependency failure). Advisories adopted: gate falls back on any exception, lock-wait message, psutil diagnostic during an install, `CalledProcessError` caught, failed-phase flag, spec `restart_required`, code-span backticks (summary value now `run wf setup`). Declined: council alternative to drop the in-process upgrade step (operator-approved design; recorded for the operator). Plan Requirements 1.4 and 1.6 aligned (receipt rotates). Mutants: all reviewer survivors and a revert of each repair are caught (startup 3, lock/config/quoting 5; M5-M9 rerun below). Model choice for the next reverification: most capable model (judges real defects); requested explicitly, observed unknown. Earlier reviewers this wave: requested none (inherited), observed unknown.; Setup Follows An Upgrade And A Pull: Full framework suite green on a quiet tree (10100 tests, receipt recorded). The first run failed only `test_tree_kill_routing` (the new installer's timed call was not in the census); registered as routed. Added a gate test for a reported-successful install that still reassesses blocked (AC-3).; Setup Follows An Upgrade And A Pull: Readiness round 1: code, release, docs-contract, security, architecture and the council (red-team, docs-contract) blocked with corrections, all folded in: trigger accepts non-blocking reasons a pull produces; install exactly the reported specs without `_bootstrap_venv`; fd-level stdout; one lock for every installer; flat summary fields from the cleanup process; corrected transition disclosure; upgrade dependency failure handled; expanded docs list. Operator decided: background install when the server can run without the packages, absent or wrong-version packages, uv only, no opt-out.

**Changes delivered:**

- **Setup Follows An Upgrade And A Pull** (`1zcm3-enh setup-after-upgrade-and-pull`) — 10 ACs completed. Key decisions: Install in the background when every missing package is deferrable; before starting otherwise; Startup installs absent and version-incompatible packages
## Watchpoints

- Watchpoint: nothing may reach stdout before the MCP transport starts (installer output goes to stderr).
- Watchpoint: the upgrade dependency step lags one upgrade on the default path of both `wf upgrade` and `wf_upgrade()` (Phase 4 runs in the old-code orchestrator); the summary's setup fields come from the new-code `--cleanup` process and apply on the installing upgrade; the `wf_upgrade` next step applies after `wf_reload_mcp` or a restart.
- Watchpoint: seed edits need `seed_edit_allowed`; framework edits need `framework_edit_allowed`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-INSTALL-LOCK-OWNERSHIP | do_now | no | completed | code-reviewer, security-reviewer, wave-council-delivery |
| DEL-LOCK-LINK-REFUSAL | do_now | no | completed | code-reviewer, architecture-reviewer, wave-council-delivery |
| DEL-LOCK-PATH-ADVISORIES | do_now | no | completed | code-reviewer, security-reviewer, wave-council-delivery |
| DEL-PHASE4-TESTS-REACH-INSTALLER | do_now | no | completed | code-reviewer, wave-council-delivery |
| DEL-SETUP-COMMAND-QUOTING | do_now | no | completed | code-reviewer, wave-council-delivery |
| DEL-STARTUP-ENTRY-UNTESTED | do_now | no | completed | code-reviewer, wave-council-delivery |
| DEL-TRANSITION-NOTE-WRONG | do_now | no | completed | release-reviewer, docs-contract-reviewer, wave-council-delivery |
| DEL-UPGRADE-COVERAGE-GAPS | do_now | no | completed | code-reviewer, wave-council-delivery |
| DEL-UV-CONFIG-ISOLATION | do_now | no | completed | security-reviewer, code-reviewer, wave-council-delivery |

*Machine review state — 9 findings; current: do_now 9, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Post-advisory current-tree check — 2026-09-30 UTC: code verdict APPROVE; bookkeeping still incomplete.** The coordinator verified full-base `realpath` resolution in `dependency_install_lock_path`, lock construction inside the `OSError` handlers in `install_requirement_specs` and `_held_install_lock`, and the no-install recovery messages. Ran `python -B -m unittest -v test_startup_install.LockOwnershipTests` from the framework tests directory with the shared tool interpreter: 10 passed, no skips. The canonical runner reports a current green receipt for 10,122 tests at 2026-09-30 03:26:04 UTC; the full suite was not repeated here. Source hashes: `setup_index.py` `47966ca7a32dcedd5706944215616cca8fc41501`; `tests/test_startup_install.py` `a25135cdcdb4f7090c77d92cd040644d629ea0d3`; `upgrade_wavefoundry.py` `02014ec095715799100846a6ad8559bf10316830`.
  - The `1zfd9-delivery-r3` code, security and council approval evidence confirms these fixes and records four caught scratch mutants. These two caveats in the previous checkpoint are now repaired; native Windows execution remains unverified. No replacement defect was found in this focused check.
  - The pending-migration follow-up is supported by the existing unguarded provisioning calls in `phase_index_update` and `setup_reconciliation.session.prepare`; the calls predate this wave, and `setup_reconciliation.py` is unchanged. This check does not implement or waive that follow-up. The lock failure remains fail-closed; the gap is structured migration/upgrade error reporting.
  - Ledger reconciliation is still needed: `DEL-LOCK-PATH-ADVISORIES` remains `repair_execution_state=pending`, `terminal=false` at its cycle-0 finding head, even though approval evidence says the fixes are complete. Approval events do not themselves complete a finding's repair/reverification chain. The guided review reports only `operator-signoff`, which belongs to the operator, not this reviewer. No operator approval, closure or commit was recorded. The original council narrative provenance gap below has not been filled by this focused check.

- **Post-repair current-tree audit — 2026-09-30 UTC: no new blocking code finding.** This is a focused follow-up, not a replacement council or a claim of freshly spawned repair-approval contexts. The coordinator checked the typed ledger: all eight finding heads have completed repairs and reverifications; all five required delivery lanes and both council signoffs are current. The guided delivery action remaining is operator-signoff; no closure or commit was authorized or performed.
  - Focused reviewers: code-reviewer (lock ownership, bootstrap serialization, carrier inheritance and linked-parent behavior), qa-reviewer (required AC evidence and upgrade/startup regressions), and red-team (uv configuration provenance and producer-contract consistency); coordinator checked documentation, ledger and test-receipt currency. Reviewers did not implement this wave, but retained earlier review context. Their overlapping targeted baseline batches passed 13, 44 and 6 tests respectively, without skips. Known-bad controls caught missing carrier inheritance, unresolved linked-parent locking, missing uv configuration isolation, operation without lock ownership, heavy imports before executable startup assessment and unquoted spaced-root commands. Real uv probes used offline settings/dry-run mode, not package installation.
  - Reviewed source hashes remained unchanged: `setup_index.py` `efe4f46e943fa28e619d5ebc00c8557f1d8ccf4d`; `upgrade_wavefoundry.py` `02014ec095715799100846a6ad8559bf10316830`; `server.py` `7c760d0e289e27a0ffbb104af8cb48ab9ad7f916`; `process_info.py` `ad3be48770e75b4c3b575d9665112599db9eab65`; `tests/test_startup_install.py` `a9772d673adec276b62f16126450b38d4ad9d4ca`. The canonical runner reported the current 10,120-test green receipt from 2026-09-30 02:40:41 UTC; this audit did not repeat the full suite.
  - Reproduction anchors: from `.wavefoundry/framework/scripts/tests`, the shared tool interpreter ran `python -B -m unittest test_startup_install.LockOwnershipTests -v` and `python -B -m unittest test_startup_install.UvConfigIsolationTests -v`. Negative controls were in-memory replacements in a fresh process, not shared-tree edits: `_lock_passing_kwargs` returning `{}` failed `test_bootstrap_children_inherit_the_lock_carrier`; an unresolved sibling lock path failed `test_a_linked_per_user_base_locks_at_its_resolved_path`; `_uv_config_args` returning `[]` failed `test_no_operator_config_means_no_config_discovery`. Each had one intended assertion failure, no errors or skips. The path-error fixture injected `OSError` at `_dependency_install_lock` before any child execution and invoked the real `_startup_install_gate` with a dependencies-missing assessment for `numpy`.
  - Caveat reconciliation: resolving the base parent handles a linked per-user `.wavefoundry` folder, not all aliases of a linked environment folder itself. An injected lock-construction `OSError` escapes the installer helper's local handler, but the actual foreground startup wrapper catches it, retains the blocked assessment and reports recovery guidance; an unhandled foreground startup crash was not reproduced. Native Windows/junction execution remains unverified. No material disagreement arose among the focused reviewers.
  - Narrative provenance gap: the recorded delivery council approval (`1zfd9-delivery-r2`) summarizes the eight resolved findings and these advisories, but the original delivery seat roster, rotating-seat brief and disagreement synthesis are not present in this wave's checkpoints. The coordinator requested the original report rather than inventing those details. Existing typed approvals were not overwritten, and this focused roster must not be represented as the original council roster.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the shared tool venv lets two repositories on framework versions with different pins re-pin each other at every host start, and on Windows a re-pin fails while another host, index build or the dashboard has the package loaded; accepted by the operator, Requirement 1.7 names what to stop; strongest-alternative: install in the background only for absent deferrable packages and install version-incompatible ones before `server_impl` is imported, removing the `process_info` gate but narrowing the operator's background decision)
- **Prepare-phase Wave Council [prepare-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: Requirement 1.6 said lock errors fail closed everywhere, so a check that changes nothing failed under a linked per-user `~/.wavefoundry`; 1.6 now takes no lock for a no-op check and opens the lock at the resolved parent of the base; strongest-alternative: resolve the whole base rather than its parent, so two spellings of a linked venv directory share one lock; pre-existing edge, advisory)
- **Delivery-phase Wave Council [delivery-council] — 2026-09-30: REQUEST CHANGES** (moderator: wave-council; primer-depth: standard; seats: docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the in-process dependency step lags one upgrade on both default paths, so the release that introduces psutil still misreports an offline install as an index publication failure, and the step adds an in-orchestrator network install that caused C1 and the uncaught-exception gap; strongest-alternative: drop the in-process step, classify dependency failure from the new-code Phase 4 child's own `ensure_deps` exit code and rely on the new-code cleanup's `setup_status`/`setup_command`, at the cost of the older parent's publication-failed label on the transition run; disagreements: none. Provenance: synthesized in the original upgrade-side delivery review (release, docs-contract and upgrade-side code lanes); the red-team seat was not run as a separate pass in this round. Blocking items R1, C1, C2, C3 became DEL-TRANSITION-NOTE-WRONG, DEL-PHASE4-TESTS-REACH-INSTALLER, DEL-SETUP-COMMAND-QUOTING, DEL-UPGRADE-COVERAGE-GAPS. The alternative was put to the operator, who kept the in-process step (2026-09-30).)
- **Delivery-phase Wave Council [delivery-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the round-1 lock repair made every dependency check take the install lock, so a linked per-user `~/.wavefoundry` broke `wf setup`, index builds and the upgrade even with nothing to install (DEL-LOCK-LINK-REFUSAL), now read-only without the lock and locking at the resolved base; strongest-alternative: drop the in-process upgrade step (declined by the operator); disagreements: none. Provenance: red-team and docs-contract seats ran in the independent round-2 recheck (context 1zfd9-reverify-r2); the operator-requested A1/A2 fixes (DEL-LOCK-PATH-ADVISORIES) were confirmed in context 1zfd9-reverify-r3. All nine findings are terminal; full suite 10122 OK. Follow-up outside this wave: `phase_index_update` and `setup_reconciliation` call `ensure_deps`/`ensure_migration_deps` without a local `SystemExit` catch on the migration-required branch.)
  - red-team: rounds 1 and 2 blocked (trigger never fired on a real pull; install timing vs host timeouts; stale server cannot see new requirements; lock scope; version replacement of an already-loaded psutil); all resolved in the plan text; final PASS.
  - docs-contract-reviewer: round 1 blocked on the unnamed spec line, ADR 1u49j flat fields, parity and hook re-render, the 1zc7n CHANGELOG note and architecture docs; round 2 on the wave-record watchpoint; all resolved; final PASS.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 35 | 226,624 |
| implement | 105 | 52,826 |
| review | 168 | 1,772,364 |
| **Total** | **308** | **2,051,814** |

<!-- wave:context-efficiency-state {"generation":321,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":105,"content_source_credit":246499,"derived_artifact_credit":0,"direct_net":52826,"estimated_tokens_saved":52826,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2624,"response_debit":192223,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1174},"plan":{"calls":35,"content_source_credit":272996,"derived_artifact_credit":3171,"direct_net":226624,"estimated_tokens_saved":226624,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3092,"response_debit":52962,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":168,"content_source_credit":2291736,"derived_artifact_credit":3999,"direct_net":1772364,"estimated_tokens_saved":1772364,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25618,"response_debit":500069,"source_credit_count":131,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":308,"content_source_credit":2811231,"derived_artifact_credit":7170,"direct_net":2051814,"estimated_tokens_saved":2051814,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":31334,"response_debit":745254,"source_credit_count":182,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10001},"wave_id":"1zfd9 setup-after-upgrade-and-pull"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 15 | 0 | 9 | 8,325,321 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":8325321,"surfaced_events":15} -->
<!-- wave:exploration-avoided end -->
