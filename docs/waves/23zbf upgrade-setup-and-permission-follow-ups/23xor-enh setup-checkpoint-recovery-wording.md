# A Failed Setup Names One Resume Command and Its Recorded Phase

Change ID: `23xor-enh setup-checkpoint-recovery-wording`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 23zbf upgrade-setup-and-permission-follow-ups

## Rationale

Field feedback against v1.46.0 (item 5, fifth bullet, in `.wavefoundry/work/23zbf/eval/waveforge-feedback-v1.46.0.md`, evaluated in section 5.3 of `.wavefoundry/work/23zbf/eval/upgrade-and-backlog.md`) reports that a failed `wf setup` leaves the operator with two different diagnostics and no command. The operator accepted the evaluator's DO verdict on 2026-11-21.

When `wf setup` fails while it owns a storage checkpoint, three things are true today. Each was executed against a temporary root on 2026-11-21 (probe scripts and output under `.wavefoundry/work/23zbf/planning/23xor/`):

- The upgrade refuses with `storage_setup_resume_required: resume the recorded wf setup continuation`, on the apply route, the dry-run route and with an explicit `--pack`. No route prints a command.
- The readiness check reports `recovery_unproven` with the message `pending recovery has no validated continuation; inspect its owning checkpoint`. The status is `indeterminate` and the result carries no action. Because the result carries no action, `_setup_needs_agent_notice` stays false, so an agent session gets no `setup_not_ready` notice at all.
- The checkpoint records a storage or indexing phase, which can cover several setup steps: `setup_reconciliation.session.__exit__` writes `failed_phase`, `failed_at` and `setup_failure`. No code reads `setup_failure`, and neither message shows `failed_phase`.

This lands on the operator at the worst moment: setup is broken, the upgrade refuses, and the check says the state cannot be determined. It is most likely on a new workstation or a new Python, and most likely on native Windows.

Planning also traced a case the evaluator left open. When a framework defect causes the setup failure, the operator cannot install the release that fixes it: the upgrade refuses the setup-owned checkpoint, and setup refuses changed framework bytes with `storage_setup_source_changed`. The trace is recorded in the Decision Log. No supported route exists today, and no message or document says what to do.

## Product Intent

After setup fails, the upgrade refusal, readiness check, index health and session-start hook identify the recorded phase and the same next step. An ordinary resumable failure gives the operator a launcher command. A legacy storage failure that requires recovery of a compatible duplicate tells the operator to do that first and to stay paused if the inputs are unavailable. The original index and receipts stay intact. A later host-stop pause can require a separate continuation. A repeatable defect after conversion starts can leave no automatic route to a fixing release. The upgrade prompt in this release explains what to preserve and send to maintainers. Older installations receive this guidance with the upgrade.

Boundaries: the diagnostic codes keep their names, every storage and ownership guard keeps its behaviour, and the change adds no reason code, action kind or tool.

AC-1, AC-3 and AC-4 require consistent commands for resumable records and consistent prerequisite-first guidance when the legacy source needs recovery. AC-8 tests the documented recovery route.

## Requirements

Terms used below:

- **Setup-owned record**: `.wavefoundry/upgrade-in-progress.json` whose `entry_path` is `setup`, or `.wavefoundry/index/sqlite-migration.json` whose `entry_path` is `setup` and whose `state` is not `complete`.
- **Recorded failure**: the checkpoint's `failed_phase` is a string that fully matches `[A-Za-z0-9_]{1,64}`.
- **Recorded continuation**: the action dictionary that `setup_readiness._owner` reads today (`action_required` on the checkpoint, otherwise `restart_action` on the pending receipt).
- **Launcher argv**: `repository_launcher_argv(root, 'setup', '--root', str(root))` from `setup_commands.py`.
- **Legacy-source prerequisite**: a validated pending setup migration with a recorded failure from an existing diagnostic that requires compatible duplicate recovery, including `storage_legacy_source_unreadable` and `storage_vector_invalid`. Recognize the diagnostic before excerpting the cause, in the legacy raw and new exception-class-prefixed forms. The guidance comes from maintained instructions. Never execute text from a checkpoint.

1. **One producer.** One function in `setup_readiness.py` resolves the resume guidance for a setup-owned record: the resume argv, the recorded setup phase and the displayable cause. `assess_setup`, the three refusals in `upgrade_wavefoundry.py` (two in `_pending_upgrade`, one in the setup-ownership guard of `main`) and the refusal in `sqlite_storage_migration.prepare_upgrade` take the command and the recorded setup phase from that function. No site builds the command or reads `failed_phase` itself.
2. **Resume argv rule.** A legacy-source prerequisite suppresses immediate resume, including a previously recorded continuation. For every other record the producer selects the argv as follows.
   1. When the record carries a recorded continuation that passes the validation `_owner` applies today, the argv is that continuation. This is existing behaviour and stays unchanged.
   2. When the record carries no action dictionary and passes the action-independent ownership checks, the argv is the launcher argv. The action-independent ownership checks are every check `_owner` performs today that does not read the action dictionary. At planning time those are: the receipt shape and identity block, the checkpoint `root_identity` match against the live root, agreement of the checkpoint `storage_migration_id` with the pending receipt `migration_id` when both exist, no `pack_path` or `zip_path` on the record, and a 64-character lowercase hex `installed_framework_sha256`. The rule governs; the list is today's enumeration.
   3. Otherwise the producer returns no validated argv.
   4. The launcher argv holds no value read from the record. Saved `setup_args` are not replayed.
3. **Readiness result.** Validate ownership first. For a legacy-source prerequisite, report `recovery_pending`, no immediate action and the advice in Requirement 4.5. A recorded failure cannot establish that the operator has restored the duplicate. Unproven ownership keeps its existing refusal. For this actionless recovery obligation, ensure the agent notice carries the bounded recovery advice without an empty recommended-command label. A transient actionless indeterminate state still suppresses the notice. For ordinary resumable records use the following rules.
   1. Recorded failure, no action dictionary, rule 2.2 satisfied: reason code `recovery_pending`, one action `{'kind': 'resume', 'argv': <launcher argv>}`, and the existing limitation line for recovery commands. The status follows the existing rule, so it is `action_required` unless another reason makes it `indeterminate`.
   2. Valid recorded continuation: reason and action as today. When the checkpoint also has a recorded failure, the reason message names the recorded setup phase.
   3. No recorded failure and no action dictionary: `recovery_unproven` with today's message, status `indeterminate`, no action. A running setup, or a process stopped before recording a failure, stays in this state.
   4. Every record that fails a check keeps `recovery_unproven` exactly as today.
4. **Recorded setup phase and cause display.** Both surfaces show the step and cause by one rule.
   1. Name the stored `failed_phase` as a phase. For example, `setup_storage` covers early steps such as rendering before conversion. The setup output identifies the exact failed step.
   2. The cause is the checkpoint's `setup_failure` when it is a non-empty string that `lifecycle_lock.path_free_text(text, root)` accepts. Non-printable characters become spaces and the text is cut at 120 characters. Omit an empty cause or the generic sentinel `setup did not complete`. When the checkpoint lacks a specific cause, direct the operator to the original setup output.
   3. No displayed text contains an absolute path taken from `setup_failure`.
   4. For ordinary resumable errors, the readiness reason message places the step and cause before its other guidance, so the session-start hook's 240-character line keeps them.
   5. For the legacy-source prerequisite, lead with the action to stop hosts and recover a duplicate using a compatible older framework and runtime on that duplicate. Preserve the original storage, auxiliary state and receipts. If the compatible inputs are unavailable, remain paused. Refer to the existing legacy-source instructions for the manual retry after recovery. Keep the prerequisite and pause condition visible within the hook’s 240-character line; the 120-character cause excerpt never substitutes for them.
5. **Upgrade refusal text.** Each of the four `storage_setup_resume_required` sites keeps its code prefix, its exit code and its closing clause (`preserve its checkpoint`, `preserve its receipt`, `upgrade has changed nothing`). Each adds the following.
   1. With a recorded failure: a statement that a `wf setup` run did not finish, with the recorded setup phase and the cause when displayable.
   2. Without a recorded failure: a statement that a `wf setup` run is recorded, has not finished and records no failure, so it may still be running.
   3. A pointer to the upgrade prompt section named in Requirement 8, for the case where setup stops again at the same step.
   4. For a legacy-source prerequisite, print the same recovery advice with no immediate retry command. For other records, append the validated argv or the existing launcher fallback, formatted with `format_command`. Text read from the record never enters a locally built command.
   5. When the producer is missing or raises, preserve the refusal, direct the operator to the setup output and the documented recovery procedure, and omit an immediate retry command. The unavailable producer cannot establish that retrying is appropriate.
6. **Path-free cause at the write site.** `setup_reconciliation.session.__exit__` records `setup_failure` as `lifecycle_lock.path_free_exception_text(exc, root)` when an exception ended the session, and keeps `setup did not complete` when none did. A failure while rendering the cause never prevents `failed_phase` and `failed_at` from being recorded.
7. **Machine contracts stay.** The codes `storage_setup_resume_required`, `recovery_pending` and `recovery_unproven` keep their names. The readiness result keeps its `schema_version`, its keys and its action kinds (`setup`, `resume`, `restart`). `STARTUP_INSTALL_EXCLUDED_REASONS` is unchanged. The texts of `storage_setup_source_changed` and of `publication_control._checkpoint_recovery_tail` are unchanged.
8. **Recovery guidance.** The section `## Setup after a clone or pull` in seed 160 and in `docs/prompts/upgrade-wavefoundry.prompt.md` gains guidance with this content.
   1. For ordinary resumable failures use the command from the upgrade refusal or readiness check. Stop the repository’s hosts first.
   2. When setup stops again at the same step because of a framework defect and a newer release fixes it, the upgrade and setup refuse each other. The operator rechecks the checkpoint immediately before moving it and may clear the block only when every condition holds: the checkpoint's `entry_path` is `setup` and it records `failed_phase`; `.wavefoundry/index/sqlite-migration.json` is absent or its `state` is `complete`; no setup or upgrade is running; every Wavefoundry host for the repository is stopped.
   3. The steps are: move `.wavefoundry/upgrade-in-progress.json` out of the repository and keep it; run the ordinary upgrade to the fixing release; run setup; delete the kept file once setup completes.
   4. A pending conversion requires the recorded framework. Preserve the original and receipts and restore changed framework files. When setup reports a legacy-source prerequisite, follow the existing duplicate recovery procedure before retrying; remain paused without compatible inputs. For a repeated defect send the recorded phase, cause and both files to maintainers.
9. **Platforms.** The locally built command is correct for the platform that prints it.
   1. Native Windows: `<root>\.wavefoundry\bin\wf.cmd` in the PowerShell form `& '<launcher>' 'setup' '--root' '<root>'`, with each single-quote character doubled.
   2. macOS and Linux: `<root>/.wavefoundry/bin/wf setup --root <root>`, quoted by `shlex.join`.
   3. WSL2: the POSIX form with the WSL path, because the command is built from the live root when it is printed and is not stored.
10. **Release notes and reference text.** `CHANGELOG.md` gains one Unreleased bullet. The sentence in `.wavefoundry/framework/README.md` that describes the `wf setup --check` actions and the `setup_readiness.py` paragraph in `docs/architecture/domain-map.md` describe the failed-setup resume. The release notes distinguish the first resume command, a possible separate host-stop continuation and the absence of an automatic fixing-release route once conversion has begun. They also distinguish a required compatible-duplicate recovery from an ordinary resumable failure, and identify which guidance ships only in the new release.

## Scope

**Problem statement:** After a failed `wf setup`, the upgrade and the readiness check report two different codes, neither prints a command, the stored recorded setup phase is never shown, and an operator blocked by a framework defect has no stated route to the fixing release.

**In scope:**

- One shared producer for the resume command, recorded setup phase and cause.
- The readiness result for a failed setup that recorded no continuation.
- The text of the four `storage_setup_resume_required` refusals.
- Path-free recording and display of the failure cause.
- Recovery guidance in seed 160 and the self-hosted upgrade prompt.
- Tests, a changelog bullet, one README sentence and one architecture sentence.

**Out of scope:**

- DECLINE: renaming or merging the two codes. They report different facts (an ownership refusal and a readiness assessment), a test matches each, and matchers outside this repository are unverified.
- DECLINE: an automatic takeover of a failed setup checkpoint by the upgrade, or setup accepting changed framework bytes. Either relaxes an ownership or source-binding guard, which is an integrity change that needs its own security and architecture review, and the manual route is two steps for a rare state. Operator decision 2026-11-21: no in-code takeover of a failed setup checkpoint.
- DECLINE: rewording `publication_control._checkpoint_recovery_tail`. It already names the command by the same rule, its text is pinned by an exact-equality test, and the reported symptom does not involve it.
- DECLINE: rewording the three `storage_setup_source_changed` messages. Exact-equality and anchored-regex tests pin them, and the new guidance section covers the state they report.
- DECLINE: finer-grained setup phases. Recording more steps means instrumenting the setup run, which is a new mechanism; a nonzero return can leave only a broad recorded phase. Point to the setup output for the exact failed step.
- DECLINE: a process-liveness probe so that a killed setup with no recorded failure also reports a resume action. It adds a platform-specific probe to a bounded read-only check, and the upgrade refusal already prints the command for that state.
- DECLINE: a `cmd.exe` form of the command. Every setup recovery command uses the one PowerShell formatter on native Windows; a second dialect here would fork it.
- DECLINE: replaying saved `setup_args` in the locally built command. A plain setup run resumes the checkpoint (executed), and replaying record values would weaken the rule that no record text enters a locally built command.

## Acceptance Criteria

Fixtures come from the real producer: a `setup_reconciliation.session` that fails, not hand-written checkpoint JSON, except where a criterion names a tampered record.

- [x] AC-1: Test an ordinary resumable setup failure before conversion (case A) and with a pending receipt and no recorded action (case B). For these fixtures readiness reports one validated resume command under sub-points 1–5. Sub-point 6 holds the pending receipt constant and changes the cause to one that requires recovery before retry.
  1. The reasons include `recovery_pending` and do not include `recovery_unproven`.
  2. The actions are exactly one `resume` action whose argv equals the launcher argv.
  3. The status is `action_required` and `exit_code` returns 1.
  4. Every reason code and action kind in the result already exists in the current vocabulary, and `schema_version` is unchanged.
  5. On each conversion-required fixture run the printed command through the setup entry point. It reaches the host-stop pause (exit 3), records a continuation and the next readiness check reports that validated continuation.
  6. Compare the ordinary pending fixture with the same valid receipt and the saved B2 unreadable-source diagnostic, in both stored cause formats. The readiness result, upgrade refusals, session-start hook and agent diagnostic must instruct the operator to recover a duplicate first and stay paused if compatible inputs are unavailable. No surface recommends an immediate retry or emits a runnable resume action. Full guidance explains how to retry manually after recovery and preserve the original and receipts. Include a stored continuation on one prerequisite fixture and a separate `storage_vector_invalid` control. A host-stop prompt alone fails this test.
- [x] AC-2: The recorded setup phase and cause appear without absolute paths. Unit tests on the readiness reason message and on the upgrade refusal text are the oracle. An implementation that prints the stored text unfiltered fails sub-point 2, and one that omits the step fails sub-point 1.
  1. With a path-free cause, both texts contain the `failed_phase` token and the cause.
  2. With a stored cause that names the repository root or another absolute path, both step-and-cause clauses name the phase and omit the absolute path. The command still includes the trusted launcher and root.
  3. With an empty cause (an interrupted run), both texts contain the step and no empty cause clause.
  4. A cause longer than 120 characters is cut at 120.
  5. Make setup Step 1 return 1 without raising, through the public entry point. The checkpoint records `setup_storage` and the generic sentinel. Both diagnostics identify the broad phase and point to the setup output. Neither presents the sentinel as a specific cause or identifies conversion as the failed operation.
- [x] AC-3: Every upgrade route reports the next action and the recorded setup phase. A test that drives `upgrade_wavefoundry.main` on the apply route, the dry-run route and with an explicit `--pack`, and a test on `sqlite_storage_migration.prepare_upgrade` with a non-setup context, are the oracle. Today no route prints a command.
  1. Each route exits 3 and its output contains `storage_setup_resume_required`, the recorded setup phase and its existing closing clause.
  2. For both AC-1 cases, the output line ends with `format_command` of the same launcher argv readiness returns.
  3. The repository files are byte-identical before and after each route.
  4. The existing test `test_setup_owned_checkpoint_is_refused_by_both_routes` passes unmodified.
  5. With the producer made unavailable, and with the producer raising, each route still exits 3, contains `storage_setup_resume_required`, points to the original output or documented recovery procedure and omits an immediate retry command.
- [x] AC-4: For an ordinarily resumable failure with a valid recorded continuation, both surfaces print that continuation. The fixture is a setup that pauses for the host stop, followed by its `--confirm-hosts-stopped` continuation failing. A test comparing the two surfaces is the oracle. An implementation that hardcodes the launcher command in the upgrade refusal fails sub-point 2.
  1. The readiness `resume` action argv equals the recorded continuation, and the reason message names the recorded setup phase.
  2. The upgrade refusal ends with `format_command` of that same argv.
- [x] AC-5: The new readiness path is bounded to a recorded failure on a record that passes the ownership checks. Unit tests are the oracle. An implementation that reports `resume` for every setup-owned checkpoint fails sub-points 1 and 2, and sub-point 4 fails without the change.
  1. A setup-owned checkpoint with no `failed_phase` and no action dictionary still returns `recovery_unproven`, `indeterminate` and no action.
  2. A failed-setup checkpoint with a mismatched `root_identity`, with a `zip_path`, with no framework fingerprint, or with a `failed_phase` that does not match the token pattern, still returns `recovery_unproven` and no action. On the otherwise valid case B fixture, change only the checkpoint’s `storage_migration_id` so that it differs from the receipt’s `migration_id`; assert the same refusal.
  3. A failed-setup checkpoint whose action dictionary is present but invalid still returns `recovery_unproven`.
  4. For the states in sub-points 1 and 3, the upgrade refusal ends with the launcher command, states that no failure is recorded where none is, and contains no text from the tampered action.
  5. With extra tokens in the checkpoint's `setup_args`, the readiness argv equals the four-element launcher argv.
  6. The existing tests `test_indeterminate_preserves_the_complete_absolute_manual_check`, `test_malformed_ownership_suppresses_setup` and `test_real_setup_continuation_requires_checkpoint_root_identity` pass unmodified.
- [x] AC-6: Agents and the session-start hook receive the command for ordinary resumable failures. AC-1.6 covers prerequisite-first guidance. A test that runs the real rendered hook body in a subprocess, and a test on `setup_not_ready_diagnostic`, are the oracle. Today the hook prints two lines that start `could not be determined (recovery_unproven` and no notice is raised.
  1. The hook output contains a `- recovery_pending:` line that names the recorded setup phase, a `Recommended:` line with the AC-1 command, the stop-hosts line and the ask-the-operator line.
  2. `_setup_needs_agent_notice` is true for the result and the `setup_not_ready` message contains the command.
- [x] AC-7: The command is correct on native Windows and on POSIX. Tests that select each dialect through the formatter's `windows` switch are the oracle, with a root that contains a space and an apostrophe. An implementation that prints a bare `wf setup` or a fixed relative launcher fails.
  1. Windows dialect: the readiness text and the upgrade refusal both contain `& '<root>\.wavefoundry\bin\wf.cmd' 'setup' '--root' '<root>'` with the apostrophe doubled.
  2. POSIX dialect: `shlex.split` of the printed command equals the launcher argv.
- [x] AC-8: The upgrade prompt states the defect route and the stated route works. A reader test on seed 160 and on `docs/prompts/upgrade-wavefoundry.prompt.md`, plus an executed test of the route, are the oracle. The reader test fails without the change; the executed test pins the behaviour the guidance depends on.
  1. Both documents, inside `## Setup after a clone or pull`, name the four conditions, the steps and the conversion-begun case of Requirement 8.
  2. On a failed-setup fixture with no conversion receipt and changed framework bytes, setup refuses with `storage_setup_source_changed` and the upgrade refuses with `storage_setup_resume_required`. After the checkpoint file is moved away, `_pending_upgrade` returns no refusal and a setup session enters.
  3. On a failed-setup fixture whose conversion receipt is pending, moving the checkpoint file away changes neither refusal.
  4. Each upgrade refusal names the section. The documented pending-conversion route requires recovering a duplicate before retrying and staying paused if compatible inputs are unavailable.
- [x] AC-9: A new failure records a path-free cause. A unit test on the checkpoint written by a failing session is the oracle. Today the stored text is `str(exc)` with its absolute path.
  1. After a session ends with an `OSError` whose filename lies under the root, `setup_failure` names the error class and the repository-relative file and contains no absolute path.
  2. When rendering the cause raises, the checkpoint still records `failed_phase` and `failed_at`.
- [x] AC-10: The release notes and reference text describe the change. `CHANGELOG.md` has one Unreleased bullet that ends `Wave 23zbf / 23xor.` and tells the reader to restart running hosts; the `wf setup --check` sentence in `.wavefoundry/framework/README.md` and the `setup_readiness.py` paragraph in `docs/architecture/domain-map.md` cover the failed-setup resume. The release note states the limits in Requirement 10, including when the operator receives this guidance. Reading the three files is the oracle.
- [x] AC-11: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Open `framework_edit_allowed`. Re-run the consumer census in the Decision Log against the tree and confirm the exact-match oracles listed there before the first edit.
- [x] Add the shared producer to `setup_readiness.py` and route `_owner` and `assess_setup` through it (Requirements 1 to 4).
- [x] Record the path-free cause in `setup_reconciliation.session.__exit__` with the guarded fallback (Requirement 6).
- [x] Reword the two refusals in `upgrade_wavefoundry._pending_upgrade` and the one in the setup-ownership guard of `upgrade_wavefoundry.main` (Requirement 5).
- [x] Reword the refusal in `sqlite_storage_migration.prepare_upgrade` with a lazy import and the fallback of Requirement 5.5.
- [x] Add the paired ordinary and prerequisite-first controls in AC-1 and readiness tests for AC-2, AC-4, AC-5 and AC-7 to `test_setup_readiness.py`.
- [x] Add the upgrade route tests for AC-2, AC-3, AC-4, AC-5 and AC-7 to `test_upgrade_failure_surfacing.py`.
- [x] Adapt the focused agent-notice predicate and message to display the manual prerequisite without an empty command or a notice on unrelated transient statuses. Add the hook and notice tests for AC-6 to `test_session_start_hook.py` and `test_setup_readiness_integration.py`.
- [x] Add the write-site and executed-route tests for AC-8 and AC-9 to `test_setup_reconciliation.py`.
- [x] Open `seed_edit_allowed`, add the Requirement 8 guidance to seed 160 under `## Setup after a clone or pull`, close the gate. List the tests that read seed 160 before the edit and run them after it.
- [x] Add the same guidance to `docs/prompts/upgrade-wavefoundry.prompt.md` by hand. Surface rendering does not carry seed prose into this file.
- [x] Add the reader test for AC-8 sub-point 1.
- [x] Update the `wf setup --check` sentence in `.wavefoundry/framework/README.md` and the `setup_readiness.py` paragraph in `docs/architecture/domain-map.md`.
- [x] Add an Unreleased `CHANGELOG.md` bullet that ends `Wave 23zbf / 23xor.` and says to restart running hosts.
- [x] Close `framework_edit_allowed`. Run the touched test files in focused mode, then the declared second profile for the portability tests.
- [x] Record in the Progress Log what the Windows simulation covers and what stays unverified on native Windows.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| producer-and-readiness | implementer | none | `setup_readiness.py`, `setup_reconciliation.py` and their tests. |
| upgrade-refusals | implementer | producer-and-readiness | `upgrade_wavefoundry.py` and `sqlite_storage_migration.py`. The sibling change `23xoq` edits other functions in `upgrade_wavefoundry.py`; one write owner edits the file for both, in sequence. |
| guidance-and-docs | implementer | upgrade-refusals | Seed 160 under `seed_edit_allowed`, the self-hosted upgrade prompt, README, domain map and changelog. The sibling change `23xoq` also edits seed 160 and the upgrade prompt, in other sections. |
| verification | qa-reviewer | guidance-and-docs | Focused runs, the Windows simulation and the unverified list. |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/setup_reconciliation.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/sqlite_storage_migration.py`
- `.wavefoundry/framework/scripts/tests/test_setup_readiness.py`
- `.wavefoundry/framework/scripts/tests/test_setup_readiness_integration.py`
- `.wavefoundry/framework/scripts/tests/test_session_start_hook.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_failure_surfacing.py`
- `.wavefoundry/framework/scripts/tests/test_setup_reconciliation.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/README.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/architecture/domain-map.md`

## Affected Architecture Docs

`docs/architecture/domain-map.md`: the `setup_readiness.py` paragraph says the assessor validates recorded setup continuations. It gains one sentence: for a failed setup that recorded no continuation, the assessor builds the repository setup launcher command locally, and the upgrade runner and the storage migration module read that guidance from it. The storage migration module's import is new, lazy and made only when it refuses.

No other architecture document changes. No boundary, storage guard, data flow or test seam moves: the assessor stays read-only, and `docs/architecture/layering-rules.md` describes its SQLite constraints, which this change does not touch.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The readiness half of the reported symptom. |
| AC-2 | required | The recorded setup phase is the third part of the request, and the path-free rule protects tool responses. |
| AC-3 | required | The upgrade half of the reported symptom. |
| AC-4 | required | Proves one command when a continuation is recorded, the case a site-by-site fix gets wrong. |
| AC-5 | required | Keeps the new path from reporting a resume for a running setup or an unproven record. |
| AC-6 | required | The hook and the agent notice are how most operators see the result. |
| AC-7 | required | Native Windows is the likeliest platform for this failure. |
| AC-8 | required | The defect route is a real dead end without it. |
| AC-9 | important | Makes the cause survive display for the failure class that motivated the report. |
| AC-10 | required | Release notes and reference text must match shipped behaviour. |
| AC-11 | required | The change's own verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-21 | Implemented the shared ownership-validated recovery guidance for all four refusals, readiness, host hooks and agent notices. Ordinary failures return one launcher or the recorded continuation. Legacy-source failures suppress any immediate retry and put duplicate recovery and the pause condition first. A missing producer keeps the refusal and refers to the setup output. Documented both manual paths. | Five focused files: 187 tests passed on the default and second profiles. Public setup exercised return code 1, exit-3 host-stop, and a later validated continuation. Temporary roots proved fixing-release handoff before conversion and refusal with a pending receipt. In-memory mutants removing the recovery prerequisite, migration-ID check, or present-invalid action rejection each failed the paired readiness test. MCP docs lint passed. |
| 2026-11-21 | Portability and field limits: the formatter test checks PowerShell escaping and POSIX shell parsing on a path containing spaces and an apostrophe. Native Windows execution, moving a record between WSL2 and Windows, unknown external matchers, a complete fixing-archive install after manual handoff and field recovery remain unobserved. | Public readiness and upgrade refusal renderer comparison, second-profile focused run, and port-neutral unit tests. |
| 2026-11-21 | Readback: Give matching setup recovery guidance through readiness and the upgrade refusals. A validated ordinary failure offers the launcher; the same pending receipt with an unreadable legacy source offers compatible duplicate recovery first. Preserve authority, guarded resumes and the separate host-stop step. The obsolete Risks row about appending a launcher on producer failure is superseded by Requirement 5.5 and AC-3.5: preserve the refusal and refer to recovery instructions. | AC-1 to AC-11: setup readiness, reconciliation, storage and upgrade refusals, agent notice, seed 160, local docs and focused tests. |
| 2026-11-21 | The operator chose prerequisite-first guidance. Cutting the B2 cause to 120 characters loses the recovery instructions. AC-1.6 pairs B2 with an ordinary resumable failure. | Saved B2 report and the independent reality-check on the amended packet. |
| 2026-11-21 | Bounded readiness repair. The public setup entry returned 1 at render Step 1 while the checkpoint retained only `setup_storage` and a generic sentinel. The post-receipt rerun paused at exit 3 and recorded its host-stop continuation. The release notes, case-B checks and phase wording now reflect those observations. | Replayed `probe_main.py` and `probe2.py` against temporary roots; see AC-1, AC-2.5, AC-3.2, AC-5.2 and AC-10. |
| 2026-11-21 | Planned. Executed the current behaviour on temporary roots with the real modules: a setup that fails before its receipt (case A), after its receipt (case B), after a pause and a failed `--confirm-hosts-stopped` continuation (case C), with a completed receipt and a discovered host (case D), and an interrupted run (case E). | `.wavefoundry/work/23zbf/planning/23xor/probe.py`, `probe2.py`, `probe3.py` and their `-output.txt` files. |
| 2026-11-21 | Executed: case A and case B both give `recovery_unproven` with no action from `_owner`, and exit 3 with no command from the upgrade on the apply, dry-run and explicit-pack routes. Case C gives a `resume` action with the recorded continuation, and the upgrade still prints no command. | `probe-output.txt` A4 to A8, B3, B4; `probe2-output.txt` C3, C4. |
| 2026-11-21 | Executed: a plain setup run resumes case A and case B (each reaches the ordinary host-stop pause, exit 3, and records the continuation). Case B passes all four action-independent ownership checks. An interrupted run records `failed_phase` with an empty cause. | `probe-output.txt` A'1 to A'3; `probe2-output.txt` B'1 to B'3, E2; `probe3-output.txt`. |
| 2026-11-21 | Executed the Windows and POSIX command forms through the formatter's `windows` switch with a root containing a space and an apostrophe. | `probe-output.txt` COMMAND FORMS. |
| 2026-11-21 | Not executed, marked `inferred` or `unverified` in the Decision Log and Risks: a complete upgrade run after the checkpoint is moved away; native Windows execution of the printed command; WSL2 reading a record written from native Windows; matchers of the two codes outside this repository; the mixed-version fallback of Requirement 5.5. | See Risks. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-21 | Selected approach: one shared producer in `setup_readiness.py` that yields the resume argv, the recorded setup phase and the cause for both surfaces, with the new readiness path limited to a recorded failure. | It is the only approach that gives one command in every state, including a recorded continuation, and it reuses `_owner`, `setup_command` and the rule `publication_control._checkpoint_recovery_tail` already applies (recorded continuation, otherwise the repository launcher). | Rejected A, wording at each site (append `setup_command(root)` in the four refusals and return the launcher from `_owner` for any setup-owned record): two producers, a different command from the readiness check when a continuation is recorded (executed, case C), and a resume action reported while a setup is still running. Rejected C, remove the dead end in code by letting the upgrade take over or setup accept new bytes: it relaxes an integrity guard and goes far beyond wording. Rejected D, merge the two codes: breaks matchers. |
| 2026-11-21 | Mechanism efficacy. Replay: the reported state (cases A and B) gets `recovery_pending`, one command and the step on both surfaces. Control or advice: advice; the refusals remain the control. What makes someone act: the command is the last text of the line the operator is already reading, the hook prints it as `Recommended:`, and the `setup_not_ready` notice now fires. Misses: a killed setup with no recorded failure, and a record that fails an ownership check, stay `recovery_unproven` in the readiness check; the upgrade refusal still prints the command. Wrong flags: none found; a rerun clears `failed_phase` on entry (executed, A'2). Existing mechanisms give the value: no new mechanism, code or action kind. Measure after release: the reporting team sees `recovery_pending` with a command for a failed setup, and its next report of a failed setup quotes the step. | Seed 170 Mechanism efficacy, in proportion to a small change. | None. |
| 2026-11-21 | Keep all three diagnostic codes. Consumer census (grep over the working tree, excluding `.git`, `.wavefoundry/index`, `.wavefoundry/cache` and `.wavefoundry/work`). `storage_setup_resume_required`: four emit sites (`upgrade_wavefoundry.py:5787`, `:5816`, `:6130`, `sqlite_storage_migration.py:1204`), one matcher (`tests/test_upgrade_failure_surfacing.py:91`), three occurrences in the frozen old-runner fixture `tests/fixtures/upgrade_old_runner/upgrade_runner_v1_31_0.py.txt` (not edited), and closed wave records. No code branches on it; `wf_upgrade` forwards the CLI text (read, not executed). `recovery_unproven`: one emit site (`setup_readiness.py:491`), the set `STARTUP_INSTALL_EXCLUDED_REASONS` (`:643`), two matchers (`tests/test_session_start_hook.py:215`, `tests/test_setup_readiness.py:332`) and one closed spec. `recovery_pending`: one emit site (`:486`), the same set, and `tests/test_session_start_hook.py:205`. | Matchers outside this repository are `unverified`, so names stay and only wording and one state's result change. | Rename or merge: declined. |
| 2026-11-21 | Consumers of the readiness result for the changed state (census of `assess_setup` callers and action readers under `.wavefoundry/framework/scripts`, tests excluded): `setup_readiness.format_text` (`wf setup --check`, MCP stderr), `setup_wavefoundry.main` (`--check` and its exit code), `server.py` startup and the reload payload, the handler's `assess_setup` in `wf_server/server_impl.py` (`index_health` `data.setup_readiness`, the monitor), `_setup_needs_agent_notice` and `setup_not_ready_diagnostic`, the session-start hook body in `render_platform_surfaces.py`, and `upgrade_wavefoundry._setup_summary_fields`. Every reader already handles the `resume` kind for ordinary failures. The later prerequisite-first decision requires a targeted change to actionless agent notices. | The status for a failed setup moves from `indeterminate` to `action_required`: `wf setup --check` exits 1 where it exited 2, the hook prints the recommended command, and agents receive `setup_not_ready`. Startup blocking and the startup install are unchanged. | Operator decision 2026-11-21: accept `wf setup --check` exiting 1 with `setup_not_ready` for a failed setup. |
| 2026-11-21 | Exact-match oracles found before planning the wording: `test_setup_reconciliation.py` pins `storage_setup_source_changed` (one exact equality, two anchored regexes) and the string `resume the recorded wf setup continuation: RECORDED` from `publication_control`. No test pins the full text of `storage_setup_resume_required`, the `recovery_pending` message or `setup_failure`. | The pinned texts are left unchanged (Requirement 7). | Reword them: declined. |
| 2026-11-21 | Readiness reports a resume only for a recorded failure. | A checkpoint with no `failed_phase` and no action also describes a setup that is running now. A resume action there would raise an agent notice during an ordinary setup run. | A process-liveness probe: declined. |
| 2026-11-21 | Store the cause path-free and filter it again at display. | The stored text is `str(exc)` with absolute paths (executed, A2), and the readiness result reaches MCP responses and the hook. Records written by an older release still hold raw text, so display filters too. `setup_failure` has no reader (census: one write site, zero reads). | Operator decision 2026-11-21: accept storing the setup failure path-free. Alternative considered: display the step only. |
| 2026-11-21 | Fixing-release trace: a real dead end. Executed on case A: the upgrade refuses on every route; replacing framework bytes makes setup refuse with `storage_setup_source_changed`; restoring the recorded bytes brings back the defect. The installed runner makes the refusal before any code from the new pack runs. Executed escape for a conversion-free record (case A with no receipt, case D with a completed receipt): with the checkpoint file moved away, `_pending_upgrade` returns no refusal and a setup session enters on changed bytes. Executed for case B (pending receipt): moving the checkpoint changes neither refusal, so only the recorded framework can finish. `inferred`: a complete upgrade run after the move, because no pack exists in the scratch root. | Requirement 8 states exactly what the operator does in each case, and AC-8 pins the behaviour the guidance relies on. The route fails safe: a misjudged receipt condition unlocks nothing. | Operator decision 2026-11-21: no in-code takeover of a failed setup checkpoint; the documented operator steps are the route. Alternative considered: automatic takeover in code, declined in Scope. |
| 2026-11-21 | The motivating field state is `inferred` to be case A or case B. | The report quotes the two codes and not the checkpoint. Both cases produce exactly that pair (executed). | None. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The printed PowerShell command is verified by simulation only. Native Windows execution cannot run here. | AC-7 pins the string through the shared formatter that every other setup recovery command uses. Running the command in a real PowerShell session, and a real `WinError` cause through the path-free rendering, stay `unverified`; the Progress Log records them at delivery. |
| WSL2 and native Windows sharing one checkout: a record written on one side and read on the other. `inferred`, not executed. | The locally built command uses the reader's platform and live root. A recorded continuation names the writer's interpreter and fails the existing interpreter check, so the readiness check stays `recovery_unproven` and the upgrade prints the locally built command. |
| An older `setup_readiness` module cached in a mixed-version parent process lacks the producer. `inferred` from the existing `getattr` guards in the same modules. | Requirement 5.5 keeps the refusal and appends the launcher command; AC-3 sub-point 5 tests it with the producer removed and with the producer raising. |
| The exit code of `wf setup --check` changes from 2 to 1 for a failed setup. A script outside this repository may branch on it. `unverified`. | Operator decision 2026-11-21: accept the exit-code change. The changelog bullet names it. Exit 1 already means a recommended action exists. |
| An operator applies the checkpoint move with a conversion in progress. | The guidance lists the receipt condition first, and the move unlocks nothing in that state (executed, case B). |
| Sibling change `23xoq` edits `upgrade_wavefoundry.py`, seed 160 and the upgrade prompt. | Different functions and sections; one write owner edits them in sequence (Agent Execution Graph). |
| Editing `setup_readiness.py` and `setup_reconciliation.py` makes running hosts report `loaded_code_stale`. | Expected; the changelog bullet tells the reader to restart hosts. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
