# Test run tolerates concurrent planning

Change ID: `23nqu-enh test-run-tolerates-concurrent-planning`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-17
Wave: 23p89 retained-work-and-test-run-tolerance

## Rationale

A full framework test run refuses to record a passing receipt when any tracked or non-ignored file in the repository changes while it runs. The guard exists to catch a test that writes into the real repository instead of a temporary folder. It cannot tell that from a person or another agent session planning new work, so writing a plan document during a run costs a rerun of about ten minutes. On 2026-11-17 a run on wave `23lxd` executed all 12,873 tests, passed them, and was refused because another session created a plan under `docs/plans/` during it.

The receipt itself covers only the framework tree: a documentation edit made after a run never invalidates it. The guard is therefore stricter during the run than the receipt is afterwards.

The runner already has an operator-reviewed way to accept a refused run, `--reconcile`. It accepts a known edit-gate closure and an edit to an existing Markdown file under `docs/` that is not a record: wave records, specs, ledgers and plans are refused as canonical authority, and added or deleted files are refused.

The operator's direction: "We need to allow this in the docs folder unless it directly impacts the current work. I want to be able to plan new work while an existing wave is being worked on without invalidating everything." And: "I think we can tolerate more than just md files."

In this spec the documentation root is the `docs/` directory at the repository root, the same literal the runner's reconcile path and the gardener use.

## Product Intent

Someone can plan new work (write or edit a spec, create a wave, admit a spec, update the handoff) while a full test run is in progress, and the run still records its receipt without an operator step. Changes to the framework tree, the edit-gate file, the wave being worked on and the project's policy files still refuse the run. A test that writes under the documentation root through Python is stopped at the write; the protection that is given up is stated.

## Requirements

1. A file of any type under the documentation root that is created, modified or deleted during a test run does not refuse the run, unless Requirement 2 or 3 applies. This includes the record and ledger of a wave created during the run, plan documents, the session handoff, prompt and reference documents, manifests and recorded data. The run's output lists each such path under a heading that says the files changed during the run and were tolerated.
2. These changes still refuse the run, as today:
   1. Any path under the framework tree, and the edit-gate file.
   2. Any path under the folder of a wave that was open at the start of the run, other than the changes the existing bookkeeping rule already allows (an unchanged spec body, an append-only ledger without a new review-policy receipt, a telemetry-only wave record change). Open means the wave record's status, read from the record bytes captured in the snapshot taken when the run started, is one of the framework's open statuses (`OPEN_CONTAINER_STATUSES`). The folder is the record's parent directory with everything under it. The records are found through the runner's record layout, so a renamed vocabulary profile and a nested layout are covered. Consequences, all intended: a wave that becomes open during the run is not in the set, so changes in its folder are tolerated and listed; planned, readied and paused waves are not open; pausing or closing a wave that was open at the start changes its record and refuses the run; admitting a spec to a wave that was open at the start refuses the run.
   3. The project's policy files under the documentation root: the workflow configuration, the repository profile, the contributors file, the scan rules and the reconcile dispositions file.
   4. Any path outside the documentation root. A waves or plans root configured outside the documentation root gets no tolerance.
3. The guard fails closed. When the record layout cannot be read, when a wave record in the start snapshot cannot be read or is a link, or when a record's status cannot be parsed, nothing under the documentation root is tolerated for that run: every changed path refuses, as today.
4. The in-worker write guard protects the documentation root of the real repository in addition to the configured waves and plans roots it protects today. A test that writes there through Python fails at the write. Tests that write under a fixture repository's own roots are unaffected, and the guard's existing allowance for creating an already existing directory is kept.
5. The limit is stated in the changelog, the build-and-verification guidance and the runner's output heading: a write under the documentation root that bypasses the in-worker guard (a child process started without the guard, a shell or git command, a native write) is no longer caught by the end-of-run comparison unless it lands in a wave that was open at the start or in a policy file. Before this change the end-of-run comparison caught it.
6. The test receipt records the tolerated paths as an informational list: sorted, bounded, absent when nothing was tolerated, and read by no gate.
7. `--reconcile` behaves for a refused run exactly as it does today. The recovery record of a refused run is built from the changed list as it stands before documentation tolerance is applied, so inspection accepts and refuses the same paths as before. A refused run that also contains a created or deleted documentation file therefore still cannot be reconciled, as today; making such a run reconcilable is not part of this change.
8. The full, focused and schedule-control run modes follow the same rule; they share one code path. A profile run executes on a temporary copy and does not observe the real repository, as today.
9. The documents that state today's rule are updated:
   1. `docs/contributing/build-and-verification.md`: the passages that say to finish plan edits before a run and to update the session handoff outside it, and the reconcile section's statements about which documentation is eligible.
   2. `docs/architecture/testing-architecture.md`: the repository-state guard paragraph, the statement that the session handoff has no filename exemption, the in-worker guard's protected-roots paragraph, the statement that unclassified changes still fail, the reconcile eligibility text, and the line that tests write only under temporary roots.
   3. The seeds that tell agents to update the session handoff outside a run or that there is no filename-based exemption: the agent harness core seed, the close-wave seed and the implement-spec seed.
   4. The runner's refusal message. The `--help` text for `--reconcile` needs no change.
10. `CHANGELOG.md` Unreleased states:
    1. For operators: planning during a run no longer refuses it; tolerated paths are listed in the output and the receipt; what still refuses.
    2. The limit of Requirement 5, and that a test reading a live document may see it change during the run.
    3. For distributions: the receipt gains an informational field; the in-worker guard now protects the whole documentation root, so a distribution's test that writes under the real documentation root now fails at the write.

## Scope

**Problem statement:** planning in parallel with a test run invalidates the run.

**In scope:**

- The end-of-run comparison in `run_tests.py` and its message.
- The in-worker write guard's protected roots.
- The receipt field of Requirement 6.
- Existing tests that pin today's refusals and must be re-based on a path that still refuses, or rewritten to assert the new behaviour, each logged: in `tests/test_run_tests_repo_guard.py`, `test_full_run_fails_when_a_test_creates_a_non_ignored_file`, `test_unregistered_or_new_ledger_does_not_gain_an_exemption` and `test_exec_and_fork_descendants_refuse_but_isolated_raw_write_limit_is_explicit`; in `tests/test_run_tests_reconciliation.py`, the cases whose refused run depends only on a documentation change.
- New tests, the changelog entry, and the documents of Requirement 9.

**Out of scope:**

- Hashing documents into the receipt.
- Isolating the suite from the live repository's documents. Tests that read live documents keep doing so.
- Any change to what `--reconcile` accepts, including making a refused run with a tolerated new file reconcilable.
- The close gate's receipt check.

## Acceptance Criteria

AC-1 and AC-3 together establish the intent.

- [x] AC-1: In a fixture repository, with the change staged at a barrier while a runner run is in progress (the pattern of the existing guard tests' external publisher), a run during which a plan is created under the plans root, a planned wave is created (its record and ledger), the plan is moved into that wave, the session handoff is edited and a JSON file that is not a policy file changes under the documentation root, exits successfully, writes its receipt and lists each path as tolerated. Shown for a full run and for a focused run.
- [x] AC-2: Each case of Requirement 2 still refuses the run, each asserted by a test that fails when its case is tolerated:
  1. A framework file, and the edit-gate file.
  2. A spec body edit in the folder of a wave that was open at the start, paired with the same edit in a planned wave, which is tolerated.
  3. A new review-policy receipt in the ledger of a wave that was open at the start.
  4. Closing a wave that was open at the start.
  5. Each of the five policy files.
  6. A file outside the documentation root.

  A wave whose record changes from planned to an open status during the run does not join the refused set.
- [x] AC-3: In a nested runner on a fixture repository, a test that writes a file under that repository's documentation root, outside the waves and plans roots, fails at the write with the guard's refusal, and the file does not exist afterwards. The same test's write succeeds when the protected roots are returned to the waves and plans roots only.
- [x] AC-4: When the record layout cannot be read, and separately when a wave record's status cannot be parsed, a documentation change during the run refuses the run. The test fails when an undeterminable open-wave set is treated as empty.
- [x] AC-5: The existing bookkeeping allowances behave as before on a wave that was open at the start: a Progress Log edit in its spec, an append-only ledger write without a new receipt, and a telemetry-only wave record change are not reported as changes and do not appear in the tolerated list.
- [x] AC-6: The receipt of a run with tolerated paths lists them, the receipt of a run without any has no such field, and the close gate reads both as valid.
- [x] AC-7: For a refused run, `--reconcile` gives the same outcome as before this change: its existing suite passes with its assertions on outcomes unchanged, and a new case shows that a refused run holding a gate closure and a created plan file is refused by reconcile for the added file, as today.
- [x] AC-8: Each document of Requirement 9 states the new rule and no longer states that a session handoff edit or any other documentation change refuses a run; `CHANGELOG.md` Unreleased carries the three statements of Requirement 10.
- [x] AC-9: The change's own suites and every test it adds pass, including under `--profile second`; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Save the output of the guard and reconciliation suites and a probe of what the in-worker guard covers today, before the first edit; log it.
- [x] Open `framework_edit_allowed` and `seed_edit_allowed`; close both when done.
- [x] Decide the open-wave set from the start snapshot and classify changed paths per Requirements 1 to 3; report tolerated paths.
- [x] Add the documentation root to the in-worker guard's protected roots.
- [x] Record tolerated paths in the receipt; build a refused run's recovery record from the list before tolerance.
- [x] Re-base or rewrite the existing tests named in Scope; log each.
- [x] Add the tests of AC-1 to AC-7.
- [x] Update the documents of Requirement 9 and the changelog.
- [x] Run `wf_validate_docs`, then the framework test suite last, then `--profile second` on the runner's tests.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| guard-classification | implementer | (none) | One sequential workstream |


## Serialization Points

- `.wavefoundry/framework/scripts/run_tests.py`, `.wavefoundry/framework/scripts/test_worker_guard.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_repo_guard.py`, `.wavefoundry/framework/scripts/tests/test_run_tests_reconciliation.py`
- `docs/contributing/build-and-verification.md`, `docs/architecture/testing-architecture.md`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`, `.wavefoundry/framework/seeds/190-close-wave.prompt.md`, `.wavefoundry/framework/seeds/180-implement-spec.prompt.md`
- The changelog at the repository root is also edited.

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`: the passages listed in Requirement 9. The guard's verification boundary moves: the end-of-run comparison stops covering most of the documentation root and the in-worker guard starts covering it.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The intent: planning in parallel does not refuse a run |
| AC-2 | required  | The guard keeps refusing what affects the work under test |
| AC-3 | required  | The Python-level protection is extended, and the control shows it can fail |
| AC-4 | required  | The control must not loosen when its classifier is broken |
| AC-5 | required  | Existing allowances must not regress |
| AC-6 | important | A reader can see the run overlapped with document changes |
| AC-7 | required  | The shipped operator path keeps working |
| AC-8 | required  | The protection given up must be stated where agents and operators read it |
| AC-9 | required  | Verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-17 | Plan authored from a reading of `run_tests.py` (`repo_state_snapshot`, `_repo_state_changes`, `_bookkeeping_changes`, `_hash_inputs`); nothing executed. | Suite log of the refused run in the session scratchpad |
| 2026-11-17 | Red-team readiness primer, two blocking findings typed by the red-team seat before any repair: `READY-NQU-DETECTION` and `READY-NQU-RECONCILE`. Executed by the seat on a fixture: the in-worker guard refuses a write under the plans root and allows writes to the session handoff, the workflow configuration and a new Markdown file under the documentation root; a child started without the guard writes under the plans root. Repair start recorded for both, then this plan was amended. | `events.jsonl` (`ev-ready-nqu-detection`, `ev-ready-nqu-reconcile`, and their repair starts) |
| 2026-11-17 | First lane review. The red-team seat reverified `READY-NQU-DETECTION` and did not reverify `READY-NQU-RECONCILE`: the first repair's statement of what reconcile accepts was false, because wave records, specs, ledgers and plans are refused as canonical authority. Two more blocking findings were typed by their lanes: `READY-NQU-FAIL-OPEN-LAYOUT` (architecture-reviewer: an unreadable layout would have produced an empty open-wave set and tolerated everything) and `READY-NQU-DOC-COVERAGE` (docs-contract-reviewer: documents and a requirement without a criterion). `READY-DOCS-RECORD-INTEGRITY` covers this plan's Decision Log. Repair starts recorded, then this plan was amended in one pass: Requirement 3 and AC-4 (fail closed); Requirement 2.2 decides open status from the start snapshot and states the consequences; Requirement 4 adds the documentation root to the protected roots and keeps the record roots; Requirement 7 and AC-7 state reconcile's unchanged behaviour; Requirements 9 and 10 and AC-8 name the documents and the changelog statements; a fifth policy file; AC-1 uses a fixture with a staged change in full and focused mode; the existing tests to change are named. The code-reviewer lane found no blocking issue of its own. | `events.jsonl`; lane reports in the session |
| 2026-11-17 | Focused verification round: `READY-NQU-RECONCILE` (red-team), `READY-NQU-FAIL-OPEN-LAYOUT` (architecture-reviewer) and `READY-NQU-DOC-COVERAGE` (docs-contract-reviewer) reverified by fresh contexts; no new blocking finding. Executed by them: the reconciliation suite on a scratch copy (26 tests pass, and a refused run with a gate closure and a created plan file is refused for the added file today); the layout collapse (an unreadable layout yields an empty carrier map); a census of this repository (515 wave records, 514 closed, 1 planned, none open). Implementation notes carried from the lanes; they say how requirements are built and evidenced and change none. (1) Fail closed: an empty carrier map means both "layout unreadable" and "no records", so the classifier asks the layout and the wave-record matcher directly and records an explicit flag on the snapshot; a matcher of none counts as unreadable. (2) A wave record is unreadable when its snapshot entry is absent or carries no bytes (not a regular file, or under a linked ancestor). A status is unparseable when the bytes are not UTF-8, there is no `Status:` line or more than one, or the value, trimmed of spaces and backticks and lowercased, is not a known container status. Any of these fails the whole run closed. (3) AC-4's test must reach the classifier: the worker launch already fails every file when the layout is unreadable, so a full-run test could pass for that reason alone. Cover the unreadable-record and link cases in the same test or log them as the same branch. (4) Import the open-status set lazily inside the function; the close gate loads the runner by path. (5) The five policy paths have no shared constant the runner can import cheaply; the runner defines its own set and a test pins it to the producers' paths. `docs/scan-findings.json` is generated output and stays tolerated. (6) Requirement 7: keep the evidence the refused-run record is built from as the result of the existing change comparison, and apply tolerance only to the message and exit status. A tolerated plan, spec or wave record would otherwise land in the bookkeeping class and fail inspection with a different message. (7) The tolerated list needs its own state reset at the start of each execution, is printed on the success path too, and is written only when the receipt is published; bound it with a count and a truncation flag. It goes in the test receipt only, not the qualification report. (8) Requirement 4: add `docs` to the existing record-dirs tuple at the worker launch, keeping the waves and plans roots. The existing-directory allowance is `exist_ok` swallowing the guard's error; a bare directory creation that catches only `FileExistsError` under the real documentation root would now see a permission error, and a test that creates and deletes a file there now fails. (9) Scope's "reconciliation cases whose refused run depends only on a documentation change" is expected to be empty: every case in that suite includes a gate closure. Log it as empty. AC-7's new test asserts the added path, because the refusal message is a combined one. (10) AC-1 asserts full and focused mode; schedule-control shares the path and is not separately asserted. (11) On an open wave whose persisted status block is stale, the bookkeeping proof fails and the run refuses strictly; accepted. (12) Keep the refusal message's existing substrings. Cover nested layouts and a configured archive root with fixtures; only the flat layout was probed. | `events.jsonl`; lane reports in the session; `.wavefoundry/work/23p89/readiness-brief.md` |
| 2026-11-17 | Council chair: `council-readiness` PASS; intent fit for this change `establishes`. Readied. One more note from the chair. (13) AC-1's fixture also has a wave that is open at the start and receives telemetry-only record writes during the run, so it replays the run that was refused on wave `23lxd`. Open for the operator, from the chair: whether to accept giving up end-of-run detection of writes under the documentation root that bypass the in-worker guard, or take the reconcile alternative; the list of five policy files and that `docs/scan-findings.json` stays tolerated; that closing or pausing a wave that was open at the start still refuses the run. | `events.jsonl` (`ev-approval-council-readiness`) |
| 2026-11-18 | Implementer, before the first edit (executed): guard and reconciliation suites 73 tests OK; worker-guard probe on a fixture refuses writes under the waves and plans roots and allows the session handoff, a new Markdown file and the workflow configuration under `docs/`; receipt keys `durations_s, inputs_hash, ran_at, result, test_count`. After the change the same probe refuses all five `docs/` targets and still allows a path outside `docs/`. | `.wavefoundry/work/23p89/23nqu/` (`baseline-guard-suites.txt`, `probe-worker-guard-before.txt`, `probe-worker-guard-after.txt`, `receipt-keys-before.txt`) |
| 2026-11-18 | Implementer: implemented in `run_tests.py` (explicit `layout_known` flag on the snapshot; open-wave folders from the start snapshot's record bytes with the lazy status import; classification with the five policy paths; tolerated-path state reset per execution, printed on success and failure, receipt field `tolerated_changes` with paths, count and truncation flag; `docs` added to the worker's protected roots; recovery evidence kept as the comparison's own list). Existing tests changed (executed, each failed after the runner change and passes re-based): `test_full_run_fails_when_a_test_creates_a_non_ignored_file` re-based to `src/new.py`; `test_unregistered_or_new_ledger_does_not_gain_an_exemption` re-based to an unregistered ledger inside the open wave's folder and one outside `docs/`; `test_exec_and_fork_descendants_refuse_but_isolated_raw_write_limit_is_explicit` re-based on an open wave record in the written folder, plus the stated limit (a raw write to another `docs/` file is tolerated and listed). The reconciliation cases whose refused run depends only on a documentation change: none (every case includes a gate closure), so none changed. Also changed: the seed-209 contract phrase in `test_compact_review_artifacts.py`, because the seed sentence it pins was reworded. | Diff of `tests/test_run_tests_repo_guard.py`, `tests/test_compact_review_artifacts.py` |
| 2026-11-18 | Implementer: new tests in `test_run_tests_repo_guard.py` (`DocumentationToleranceTests`, `DocumentationToleranceFailsClosedTests`, two `CanonicalBookkeepingTests` cases, two `ProtectedWorkerTests` cases) and one reconciliation case. Mutation evidence executed on a scratch copy: eleven reverted behaviours (no tolerance, open folders not refused, policy files tolerated, undeterminable set treated as empty, `docs` not protected, recovery built after tolerance, receipt field written when empty, list unbounded, bookkeeping allowance dropped, any status accepted, linked or unreadable record ignored), each detected by its tests, zero undetected. AC-3's reverse control and AC-4's layout control run inside the tests. | `.wavefoundry/work/23p89/23nqu/mutation-log.txt`, `mutate.py` |
| 2026-11-18 | Implementer: documents of Requirements 9 and 10 updated (build-and-verification, testing-architecture, seeds 209, 190 and 180, the runner message, `CHANGELOG.md` Unreleased); the same handoff sentence was also updated in the rendered `docs/prompts/` counterparts and in `install/lifecycle-prompts/implement-wave.prompt.md`. `wf render-surfaces` rc 0; `wf_validate_docs` passed. Gates closed, final full suite `--no-cache`: 12893 tests across 250 files OK, receipt result ok. `--profile second` on the guard, reconciliation and compact-review files: first attempt failed one new test that assumed the shipped waves root exists (fixed, then the final full suite above was rerun); final 97 tests OK. | `.wavefoundry/work/23p89/23nqu/final-full-suite-summary.txt`, `profile-second-*.txt` |
| 2026-11-17 | Coordinator check of the implementer's report against the tree. Confirmed: all three gates closed; the test receipt reads `result: ok`, 12893 tests, and no framework file is newer than it; no stray bytecode folder under the framework tree; the saved evidence files exist; the runner has the policy-file set, the snapshot's layout flag, the tolerated-change classifier and the fail-closed reason, and the worker launch passes the waves root, the plans root and the documentation root; the coordinator reran the guard and reconciliation suites: "Ran 93 tests across 2 files in 13.155s", "OK". Not rerun by the coordinator: the full suite, the profile run, the mutations. All criteria and tasks marked; Change Status set to `implemented`. Carried to delivery review as open questions, not settled here: (1) the implementer reworded a seed 209 sentence about plan edits and updated a contract-phrase test that pins it; (2) it updated the handoff sentence in one shipped lifecycle template and three rendered prompts beyond Requirement 9's list; (3) the refusal message can show the tolerance-off reason when no documentation path changed; (4) archive-root records are not read for open status; (5) the open-wave folder match is a case-sensitive prefix; (6) schedule-control mode is not separately asserted and nothing ran on Windows. | `.wavefoundry/work/23p89/23nqu/`; `.wavefoundry/framework/test-cache.json` |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-17 | Operator: "We need to allow this in the docs folder unless it directly impacts the current work." | Planning new work in parallel must not invalidate a run. | Keep the strict guard. |
| 2026-11-17 | Operator: "I think we can tolerate more than just md files." Every file type under the documentation root is tolerated. | The first draft tolerated Markdown only, which would have refused creating a wave during a run, because a new wave writes a ledger file. | Markdown only. |
| 2026-11-17 | Automatic tolerance, with the in-worker guard extended and the remaining gap stated; `--reconcile` unchanged. Coordinator's recommendation. The operator replied "Ok, split and then prepare, review, and implement them both while I'm awawy" to a message that listed this recommendation among others; the operator has not separately confirmed this choice or the detection given up under Requirement 5. | The operator asked for planning in parallel without invalidating runs; an operator step per refused run would not deliver that. | Extend `--reconcile` to created and deleted documentation files and tolerate nothing automatically, which keeps the end-of-run control for writes that bypass the guard; snapshot only the documents tests read. |
| 2026-11-17 | What "directly impacts the current work" means: a wave open at the start of the run, the framework tree, the edit-gate file and five policy files. Coordinator's proposal with reviewers' additions; the operator has not confirmed the list. | Those are what a run or the wave under test depends on. The policy files set review, gate, attribution and scan behaviour. | Tolerate the policy files; also refuse the prompt surface manifest and recorded datasets; tolerate a wave closed during a run. |
| 2026-11-17 | `--reconcile` keeps today's behaviour exactly; a refused run with a tolerated new file stays unreconcilable. Coordinator's choice. | The smallest change: reconcile's proofs and its suite stay as they are. | Remove tolerated paths from the recovery record so such a run becomes reconcilable. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A write under the documentation root that bypasses the in-worker guard is no longer refused at the end of the run. | Requirement 5 states it; waves open at the start and policy files still refuse; the Python-level guard is extended (Requirement 4, AC-3). |
| A test that reads a live document sees it change during the run and gives a result that depends on timing. | Disclosed in the changelog; the tolerated paths are listed in the output and the receipt. |
| Extending the guard breaks a test or helper that writes, or creates and deletes, a file under the real documentation root. | None was found by search; the full suite run of AC-9 shows whether one exists. The guard's allowance for creating an existing directory is kept. |
| The classifier is broken and the guard loosens. | Requirement 3 and AC-4: fail closed. |
| A rendered prompt, a manifest or a recorded dataset under the documentation root changes during a run and a test reads it. | Same disclosure; the guidance says not to render during a run. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
