# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-02
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zls6 dependency-installs-uv-only`
Title: Dependency Installs Uv Only

## Objective

`wf setup` installs dependencies only through uv with its package-age guard: when uv is missing and the hash-pinned bootstrap fails, setup stops with recovery guidance instead of falling back to plain pip.

## Changes

Change ID: `1zli9-enh dependency-installs-uv-only`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-10-02

## Wave Summary

Wave `1zls6` (Dependency Installs Uv Only) delivered one change: Dependency Installs Go Through uv Only. Notable adjustments during implementation: Dependency Installs Go Through uv Only: Implemented. `_install_deps` now refuses when no uv is found and `_bootstrap_uv` returns `None`: it prints `_uv_required_message()` (Requirement 1 content; the Windows form names `.\.wavefoundry\bin\wf.cmd setup`, chosen by `os.name == "nt"` as elsewhere in `setup_index`) and raises `SystemExit(2)` before any install; the uv command, environment, working directory and deadline are unchanged. The `_bootstrap_uv` timeout comment and message no longer promise a fallback and say setup cannot continue without uv, keeping the `setup.uv_bootstrap_timeout_seconds` hint; `_uv_bootstrap_failed` unchanged. Timeout and failure messages name uv only; `ensure_deps` says "the installer wrote into a different environment". `install_requirement_specs` docstring verified unchanged (already says it never falls back to pip). Caller census confirmed: `_install_deps` is called only from `ensure_deps` and `ensure_migration_deps`, both inside `_held_install_lock`. Tests: the seven listed tests use an explicit `FAKE_UV` (and now assert the uv command ran exactly once); `test_pip_fallback_runs_from_the_venv_base` became `test_no_uv_refuses_without_running_any_install`; the `uv=None` half of `test_a_relative_interpreter_path_is_made_absolute` asserts the refusal; the end-to-end detector is `test_a_failed_hash_bootstrap_is_reported_and_setup_refuses_to_install` (real `_bootstrap_uv`, `_run_install_step` stubbed so pip fails: exactly one `--require-hashes` call, then `SystemExit(2)` and the refusal); the timeout test is renamed `test_bootstrap_uv_timeout_is_loud_and_promises_no_fallback`; new `test_the_refusal_names_the_windows_command_form`, `test_every_install_deps_caller_refuses_inside_the_held_lock` (both callers, lock released, no install) and the AC-4 AST guard `test_the_only_pip_install_is_the_hash_pinned_uv_bootstrap`; `test_every_installer_child_resolves_relative_path_settings_first` gets a uv. Census miss found by the full suite: `test_server_tools.FrameworkWideSubprocessIsolationGuard.test_setup_index_resolver_and_venv_bootstrap_keeps_unchanged` pinned the removed `cmd = [str(venv_python), "-m", "pip", "install"]`; repointed at the bootstrap spawn and the uv `--python` target (same intent: plain venv interpreter, no pythonw). Failing-first: 7 failures and 1 error in `test_setup_index.py` before the code change, all passing after (`test_setup_index.py` 193 OK, `test_startup_install.py` 61 OK, `test_server_tools.py` 375 OK). Full suite in a scratch copy: default `--no-cache` 10595 tests across 154 files OK, `--profile second` 10592 OK, `--profile declared` 10595 OK (the earlier run, before the `test_server_tools` repoint, failed only that guard in all three). Mutations in a scratch copy: restoring the plain-pip else-branch fails the AC-4 guard and the end-to-end detector (6 failures); restoring "Falling back to plain pip" in the timeout message fails the renamed timeout test; dropping the uv install link or the "do not install with pip by hand" sentence each fail 6 refusal tests; removing the fake uv from the seven listed tests fails all seven, and from the startup test fails it. Docs: README (two sentences), build-and-verification Package-age guard paragraph, threat-model uv bootstrap row, 1zcxi ADR dated note, `_install_deps` docstring, CHANGELOG `### Changed` bullet and the corrected 1zimd bullet; `wf_validate_docs` passes. Gapfill: shell grep used to locate the listed test definitions and to sweep the tests folder for remaining pip-command pins after the full-suite failure.

**Changes delivered:**

- **Dependency Installs Go Through uv Only** (`1zli9-enh dependency-installs-uv-only`) — 6 ACs completed. Key decisions: Remove the plain-pip dependency fallback; setup fails closed without uv; Keep the hash-pinned uv bootstrap through pip
## Watchpoints

- Watchpoint: script edits need `framework_edit_allowed`; follow-up candidates (binary-only installs, a hash-locked dependency set) were declined for this wave.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZLS6-UNPINNED-INSTALL-CONTROLS | do_now | no | completed | — |

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
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-02: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the plan's own test and doc census was incomplete (twelve tests reach the plain-pip path, README.md promises the fallback twice, one cited symbol did not exist), so implementing as written would fail verification or quietly drop dependency-deadline coverage; resolved by amending the plan; strongest-alternative: keep the pip fallback behind an explicit operator opt-in that prints the missing age guard on every run, declined by the operator in favour of outright removal)
- Prepare council seat evidence (2026-10-02): one independent reviewer ran both seats and the code, qa and architecture lanes; no design defect; four plan corrections (symbol name, test census, README, refusal guidance) applied.
- Seat findings (2026-10-02): red-team traced five routes to an unguarded dependency install and found all closed except an existing uv used as-is (operator-accepted); security-reviewer found no new bypass and asked that the refusal name official uv install methods, the mirror settings for pip and uv, and a warning against pip-installing dependencies by hand, all adopted in Requirement 1.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 14 | 9,806 |
| implement | 15 | 244,786 |
| review | 22 | 183,949 |
| **Total** | **51** | **438,541** |

<!-- wave:context-efficiency-state {"generation":55,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":15,"content_source_credit":262524,"derived_artifact_credit":0,"direct_net":244786,"estimated_tokens_saved":244786,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":229,"response_debit":17509,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":14,"content_source_credit":16036,"derived_artifact_credit":2199,"direct_net":9806,"estimated_tokens_saved":9806,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1431,"response_debit":13509,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":22,"content_source_credit":223104,"derived_artifact_credit":1252,"direct_net":183949,"estimated_tokens_saved":183949,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3686,"response_debit":39037,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":51,"content_source_credit":501664,"derived_artifact_credit":3451,"direct_net":438541,"estimated_tokens_saved":438541,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5346,"response_debit":70055,"source_credit_count":55,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8827},"wave_id":"1zls6 dependency-installs-uv-only"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 6 | 2,297,307 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":2297307,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->
