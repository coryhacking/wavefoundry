# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-29
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zc7n process-info-psutil`
Title: Process Info Psutil

## Objective

Process information in tool-environment code comes from `psutil` through one `process_info` module with a standard-library fallback (ADR `1z9df-adr psutil-process-info`). Windows is heavily used by enterprise consumers, and today its process queries are untested `tasklist` and PowerShell spawns on the MCP status path; CR-L1 (wave `1zc7l`) builds on this.

## Changes

Change ID: `1zc7m-enh process-info-module-backed-by-psutil`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: architecture-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer

Completed At: 2026-09-29

## Wave Summary

Wave `1zc7n` (Process Info Psutil) delivered one change: Process Information From One Module Backed By psutil. Notable adjustments during implementation: Process Information From One Module Backed By psutil: Delivery repair round 1. DEL-DASHBOARD-CARRIER-RACE (QA, architecture; inherited race): stop probed the dashboard lock, then deleted the carrier, so a dashboard that locked it in between kept a deleted inode while a second dashboard locked a fresh file. Repair keeps the carrier inode, as DEL-F3 did for the index lock: `_clear_dashboard_metadata` replaces `_remove_dashboard_metadata` and `_dashboard_lock_state`; it takes the same lock non-blocking (`RuntimeFileLock`, flock style, `_LOCK_BYTE_OFFSET`), rewrites the metadata to `{}` while holding it and releases, retrying a busy lock for up to 2 s after a stop; held or a lock error leaves it untouched and reports `dashboard_lock_unverified`. Response key `metadata_removed` is now `metadata_cleared`. Requirement 3 and AC-6 reconciled to the new contract (re-Prepare). DEL-CR-WINDOWS-QUOTING (code): the two command-line tests now expect `subprocess.list2cmdline` rendering on Windows and the joined rendering on POSIX, keeping the spaced-argument coverage. Docs-contract corrections: CHANGELOG pid-reuse claim qualified to readable start times and the dashboard sentence rewritten; ADR positive consequence reworded (start time is an observation; reuse is each caller's comparison). Tests: carrier inode unchanged on both branches, a dashboard contending during cleanup is refused, forced lock error keeps metadata on both branches; four `test_dashboard_server` assertions now check cleared metadata instead of a deleted file. Scratch mutants: re-adding the delete fails both inode tests; writing after releasing the lock fails the contention test (`['acquired'] != ['busy']`). AC-11 reopened by review until the suite is rerun; Process Information From One Module Backed By psutil: Observe: code/QA/architecture request changes; security approves its selected domain. Council blocked. Two typed findings deduplicated: Windows test quoting (`DEL-CR-WINDOWS-QUOTING`) and inherited dashboard carrier race (`DEL-DASHBOARD-CARRIER-RACE`). Three independent contexts and coordinator reproduced live-carrier unlink with two canonical lifetime-lock holders. Scoped 24-file hash snapshot unchanged; current 10,067-test receipt verified.; Process Information From One Module Backed By psutil: Implemented. `psutil>=6.1,<8` declared in `setup_requirements` (`PSUTIL_REQUIREMENT`, `PSUTIL_MIN_VERSION`) and `pyproject.toml`; `wf setup` (operator-approved network) installed psutil 7.2.2. New `process_info.py` (loader with floor check and cache invalidation, `ProcessInfoUnavailable`, `pid_state`/`is_zombie`/`cmdline`/`cwd`/`create_time`/`available`, every call guarded, single `_process` construction site). `indexer._pid_is_running`/`_process_is_zombie`/`_process_cmdline` and `server_impl._pid_is_running` moved onto it, their `tasklist`/`ps`/PowerShell code deleted (indexer's now-unused `_run_tree_kill`, `subprocess` and `subprocess_util` imports removed, census keys moved); unavailable maps to not running / None. `index_handlers`: lock-first `_index_build_active`, `_pid_started_after` guard in `_index_build_active`, the foreground status branch and (found during implementation) the shared `_pid_is_live_index_build`, with `background-build.pid`'s modification time as the stamp: under the new policy a reused pid owned by another user with an unreadable command line read as a running build, which an `index_health` test exposed through a mock root whose pid became 1 (that test now uses a real root). `dashboard_handlers`: `_posix_pid_exited` (reap, `os.kill(pid, 0)`, zombie) for termination, `_dashboard_lock_state` probe with a 2 s re-probe after a stop, `dashboard_lock_unverified` keeps the carrier on both removal paths. `upgrade_lib` getattr resolver, timed `tasklist`, timeout means running; `dashboard_lib` `ps -axww` timed and routed. `process_info` diagnostic in `index_health`, `index_build_status`, `wf_server_info`; `process_info.py` in `SOURCE_FILES`. The framework-wide process-pool guard exempts the `psutil.Process` handle site by name. Tests: new `test_process_info.py` (11) and `test_process_info_callers.py` (14); pin and agreement census in `test_setup_index`; three indexer and four server mechanism tests replaced on the seam. Scratch mutants, each caught: no lock-first; metadata removed on unknown; no pid-reuse guard; unavailable raised from the server wrapper; zombie not excluded; POSIX exit via liveness; upgrade timeout read as not running. Setup's own index build stopped with `index_runtime_stale` because `indexer.py` was edited while it ran (index preserved; rebuild after the suite). Gapfill: code was read with shell `grep`/`sed` because the running MCP server serves pre-change code for the files being edited and `server_impl.py` is over the 1 MB `code_pattern` limit.

**Changes delivered:**

- **Process Information From One Module Backed By psutil** (`1zc7m-enh process-info-module-backed-by-psutil`) — 11 ACs completed. Key decisions: Unavailable `psutil` reads as "not running" in every liveness wrapper; health reports it with the `wf setup` remedy; `psutil` is required with no hand-rolled fallback inside `process_info`; a missing or broken install is a clear `process_info_unavailable` error
## Watchpoints

- Watchpoint: installing `psutil` into the shared tool environment needs network access (`wf setup`); ask the operator before running it. The full suite stays red on `test_real_required_imports_no_false_positives` until it is installed.
- Watchpoint: never add `import psutil` to a module in `upgrade_protocol.MANDATORY_FEATURE_MODULES` or any pre-dependency module; `upgrade_protocol._validate_imports` walks function-local imports.
- Watchpoint: wave `1zc7l` (CR-L1, change `1zc7k`) depends on this wave; ready it after this one closes.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-CR-WINDOWS-QUOTING | do_now | no | completed | code-reviewer, qa-reviewer |
| DEL-DASHBOARD-CARRIER-RACE | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, wave-council-delivery |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Delivery review — 2026-09-29: BLOCKED.** Frozen inputs: 24 changed implementation, test, manifest and documentation paths. `git hash-object` over each sorted path, then `git hash-object --stdin` over the LF-terminated hash list: `217f37584cdda7df9f26f674451d3e943be11279`. Reviewers and coordinator confirmed unchanged hashes at completion. Runner verified the current receipt: 10,067 tests, `result=ok`, run at 2026-09-29 22:39:45 UTC; host evidence does not qualify native Windows.
- **Code reviewer:** request changes, `DEL-CR-WINDOWS-QUOTING`. `ContractOnHostTests.test_cmdline_cwd_and_create_time_of_a_live_child` and `IndexBuildLockTests.test_process_cmdline_comes_from_process_info` require unquoted POSIX substrings on Windows. Production rendering matched `list2cmdline`, but both assertion predicates were false; quoted positive control passed. All 25 process-info tests and 60 additional focused tests passed on this host; sandbox-blocked `ps` parity passed after escalation. Three known-bad controls detected: dependency floor removed, unknown carrier treated as free, PID-reuse guard disabled. No code approval while the finding is open.
- **QA reviewer:** request changes, `DEL-DASHBOARD-CARRIER-RACE`. 33 targeted tests passed without unintended skips; disabled PID-reuse, unknown-owner preservation and POSIX exit controls each failed the intended assertion. Canonical lifetime-lock producers reproduced free probe → concurrent acquisition → carrier unlink → second acquisition while the first holder remained alive. Literal AC-6 static cases pass; the selected lifetime-lock ownership invariant fails. Root cause predates this wave. No QA approval while the findings remain open.
- **Architecture reviewer:** request changes for the same deduplicated carrier finding, independently reproduced. Domain-map specifies a persistent carrier and in-place metadata; `RuntimeFileLock.release` preserves it, but stop unlinks after an observational probe. Dashboard tools are excluded from `_LIFECYCLE_MUTATION_LOCK_TOOLS`. Mandatory current modules passed the real upgrade import validator; direct/function-local `psutil` mutants were rejected. Both import-guard tests and all 14 caller tests passed; server/indexer use one `process_info` instance. No architecture approval while ownership finding remains open.
- **Security reviewer:** selected security boundary approved with limitations in typed evidence. Own threat-model/source assessment, three stable-state shutdown/timeout tests, and held-as-free known-bad control confirmed the selected controls; a separate public-stop interleaving confirmed the correctness defect. Same-user operator state confers no new authority. Approval does not approve concurrent cleanup correctness or native Windows. No changed confinement/regex input paths or composed authority escalation identified in scoped review.
- **Reality checker:** independently reproduced the inherited race. Start coordination excludes stop; the new guard narrows the old failure but does not eliminate concurrent inode loss. Readable creation time outside the two-second tolerance is needed to establish PID reuse; unknown time skips that protection. Retains Windows test blocker; no duplicate finding.
- **Docs-contract reviewer (rotating fifth seat):** changed MCP spec agrees with normal and invalid-layer responses, including forced loader failure; both response shapes executed. Correct CHANGELOG's absolute PID-reuse/held-carrier claims alongside repair, and ADR's “Every consumer gets pid-reuse protection” to distinguish observations from caller comparisons. This seat reused QA context with the intentional full-seat briefing; it is not a fresh second independent approval.
- **Delivery Wave Council [delivery-council]: BLOCKED.** Full-depth red-team primer used five stances and three questions: concurrent acquisition, unavailable observation versus mutation authority, PID identity limits. Actual fixed seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: docs-contract-reviewer. Code-reviewer also ran. First convergence weighed randomized anonymized outputs; required blocking attribution remained attached. Seat agreement: majority; max severity: medium. Agreement: race is real and inherited. Reality-checker distinguishes absence of a new regression from architecture/QA's persistent-carrier contract obligation; Council retains the obligation because this wave explicitly modifies that ownership mechanism. No delivery approval recorded. Inherited model/effort selected for cross-platform process and lock semantics; actual runtime identity unknown. Host thread ceiling prevented additional contexts; existing delivery-only contexts served architecture after primer and reality after code, with no implementation/repair retained and no other fixed-seat outcomes shared before assessment.
- **Strongest alternative / next action:** preserve lifetime carrier inode and clear metadata under a proved lifecycle protocol. Separate persistent carrier/removable metadata requires another file and upgrade cutover; retaining the current carrier is smaller. Locking then unlinking alone is insufficient for contenders already holding the old inode. Correct Windows tests using platform rendering while preserving spaced-argument coverage. Cleanup-contract changes need owning requirements reconciled and re-Prepare; review did not implement repairs.
- **AC scope gap / handoff:** AC-11 reopened for Windows test oracles. AC-6 literal static-state evidence remains valid; concurrent ownership gap is an unresolved typed finding, not a silent deferral. Native Windows execution and stronger durable PID identity remain outside delivered evidence. Memory curation awaits resolved finding heads. Operator signoff, delivery Council approval, code/QA/architecture approvals, repair, closure and commit remain pending.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: a required dependency used only for observation must never stop the build it observes or delete a live lock carrier; resolved by the single rule (unavailable psutil reads not running, the OS locks decide) plus lock-first checks in index_handlers._index_build_active and dashboard stop; strongest-alternative: psutil optional with the hand-rolled code as a fallback, rejected by the operator in favour of a required dependency like apsw). Security seat: PASS (read-only queries, capped spec with the 21-day age guard, AccessDenied maps to unknown, air-gapped and application-control operator notes). Red-team seat: PASS after the build-path and dashboard-carrier fixes; blocked-extension case reported with the wf setup remedy.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: just after a successful stop the dashboard lock can still read held while the OS closes handles, so a clean stop would report unverified; answered by a bounded re-probe in the after-stop branch; strongest-alternative: stop takes the dashboard lock itself before removing the file, rejected because a locked file cannot be deleted on Windows and it races a starting dashboard). Re-readiness after the operator's correction: metadata is removed only when the lock probe reports not held; held or unknown preserves it and reports shutdown unverified. Security seat: PASS (no carrier deletion while held or unknown; probe opens nothing new). Red-team seat: PASS.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 27 | 33,220 |
| implement | 53 | 796,804 |
| review | 174 | 1,907,050 |
| **Total** | **254** | **2,737,074** |

<!-- wave:context-efficiency-state {"generation":222,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":53,"content_source_credit":823933,"derived_artifact_credit":0,"direct_net":796804,"estimated_tokens_saved":796804,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1443,"response_debit":96671,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":69811,"workflow_prompt_credit":1174},"plan":{"calls":27,"content_source_credit":56457,"derived_artifact_credit":2560,"direct_net":33220,"estimated_tokens_saved":33220,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3494,"response_debit":28814,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":174,"content_source_credit":2356734,"derived_artifact_credit":3051,"direct_net":1907050,"estimated_tokens_saved":1907050,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":21615,"response_debit":433436,"source_credit_count":118,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":254,"content_source_credit":3237124,"derived_artifact_credit":5611,"direct_net":2737074,"estimated_tokens_saved":2737074,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":26552,"response_debit":558921,"source_credit_count":179,"source_credit_drop_count":0,"structural_source_credit":69811,"workflow_prompt_credit":10001},"wave_id":"1zc7n process-info-psutil"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 10 | 0 | 9 | 7,039,082 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":7039082,"surfaced_events":10} -->
<!-- wave:exploration-avoided end -->
