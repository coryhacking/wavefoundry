# Docs gardener re-stamps documents that have not changed since their last stamp

Change ID: `23qfz-bug gardener-restamps-unchanged-docs`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-18
Wave: 23p9u close-record-folder-extras

## Rationale

The docs gardener's default mode stamps `Last verified` with today's date on every Markdown document that differs from `HEAD`, on every run. A document edited once and not yet committed is therefore stamped again on each later day a gardening pass runs (Prepare, `wf_garden_docs`, the Close docs gate), although its content did not change again. Each re-stamp is a Git diff with no content behind it.

Observed on 2026-11-18: `docs/references/scan-findings-format.md` was last edited on 2026-11-17 (uncommitted wording changes from a closed wave) and carried `Last verified: 2026-11-17`. A Prepare pass on 2026-11-18 re-stamped it to 2026-11-18. Its shipped copy under `.wavefoundry/framework/docs/` kept 2026-11-17, so `test_shipped_reference_docs` failed a full framework run twice in one session, with no content change in either file. Read in the code: `docs_gardener.collect_changed_markdown_paths` selects by `git diff --name-only HEAD`, and `docs_gardener.refresh_last_verified` writes the date whenever it differs.

The operator's direction, 2026-11-18, quoted: "they shouldn't be tagged unless they change to reduce git churn, etc."

## Product Intent

Anyone reading a diff or committing after several days of uncommitted work sees a `Last verified` change only on documents whose content changed since they were last stamped. Before: every uncommitted changed document is re-dated on each new day a gardening pass runs. After: a document is stamped when its content differs from `HEAD` outside the date line and it changed since its current stamp, and left alone otherwise. Boundaries: explicit requests to stamp named documents or all documents are unchanged, and no new state file is introduced.

## Requirements

1. In the default mode (no explicit paths, not the all-documents mode), the gardener stamps a Git-changed document only when both of these hold:
   1. (a) Its content differs from its `HEAD` version outside the `Last verified` line. A document with no readable `HEAD` version, for example one newly added to the index, counts as differing. A failure to read `HEAD` also counts as differing, so a failure never suppresses a stamp.
   2. (b) It changed since its stamp: the local calendar date of its modification time is later than its stamp date, or its stamp date is later than the run's date value (a stamp in the future), or its modification time cannot be read.

   Otherwise the file is left byte-identical and is not reported as updated.
2. The stamp written is unchanged: the run's date value (today, or the `--date` override).
3. Consequences that must hold, each on real files:
   1. A changed document whose stamp is older than its last modification is stamped (today's first-edit behaviour is kept).
   2. Running the gardener again with the local today as the run's date, on the same day or on a later day, with no further edit to the document, changes nothing: the stamp write itself sets the modification time to the stamp day, so (b) does not hold.
   3. A document edited again after it was stamped, on a later day, is stamped again on the next run.
   4. A document whose only difference from a readable `HEAD` version is its `Last verified` line is never stamped in default mode, however that line was written (a gardener run, a hand edit, a restored date), because (a) does not hold. A document whose content also differs from `HEAD` is decided by (b), so a hand edit of its date line counts as a change and causes one stamp on the next run.
   5. A document whose stamp is later than the run's date and whose content differs from `HEAD` outside the date line is stamped with the run's date.
4. Explicit-path mode and the all-documents mode stamp as they do today, without either check, because the caller named the documents.
5. A document whose modification time cannot be read satisfies (b), so an unreadable time never suppresses a stamp on a document that differs from `HEAD`. A document with no `Last verified` line is untouched, as today.
6. Platform behaviour and stated edge cases. The comparison uses the same local date the gardener uses for today's value and the file system's modification time, which is available on Windows, macOS, Linux and WSL2. The `HEAD` read uses the same Git the gardener already runs to list changed documents. Line terminators are preserved as today. The tool reference states these edge cases:
   1. A Git operation that rewrites a changed file (stash pop, checkout of a conflicting path) can refresh its modification time and cause one extra stamp; that is the old behaviour.
   2. Runs in different time zones can alternate a stamp across a date boundary, because a stamp written in an eastern zone is a future stamp to a western-zone run; that is the old behaviour.
   3. A run that straddles local midnight can cause one extra stamp on the next run.
   4. On WSL2, a file on a Windows-mounted drive takes its modification time from the host clock.
   5. A run with a past `--date` on a changed document writes that date and sets the modification time to today, so the next run with a different date stamps it again. Requirement 3.2 therefore holds when the run's date is the local today, which is what every shipped caller passes (they pass no `--date`).
   6. A hand edit of the date line on a document whose content also differs from `HEAD` causes one stamp on the next run (requirement 3.4). This is a limit of the rule, not a defect it removes.
7. `wf_garden_docs`, Prepare, and any other caller of the default mode get the new behaviour through the same function; the stable `docs-gardener: updated <path>` output lines keep their format and list only documents actually written.
8. Shipped text that says the default mode stamps every Git-changed document is corrected to state the rule of requirement 1. The set is derived by searching the tool reference, `AGENTS.md`, the contributing guide and the seeds for descriptions of the gardener's default targets; text that only names the tool is not edited. The reviewers found these texts:
   1. Seed `050-agent-entry-surface-bootstrap.prompt.md`, the sentence "gardens Git-changed markdown by default", which is the source of the matching `AGENTS.md` sentence; both are edited to agree.
   2. Seed `080-mechanical-enforcement.prompt.md` and seed `190-close-wave.prompt.md` step 19, accurate today; each is touched only if its wording about what is stamped becomes wrong.
   3. The `wf_garden_docs` entry in `docs/specs/mcp-tool-surface.md`.

   The derived rule above still governs: any further text the search finds is corrected under the same test.

## Scope

**Problem statement:** The gardener re-dates uncommitted documents on every new day, producing diffs and a shipped-copy test failure with no content change.

**In scope:**

- The default-mode stamping decision in `docs_gardener.py`.
- Tests in `test_docs_gardener.py`.
- The tool reference entry for `wf_garden_docs`, the seed 050 sentence and its `AGENTS.md` copy, any other shipped sentence found under requirement 8, and the changelog.

**Out of scope:**

- Explicit-path and all-documents modes.
- A content hash or a sidecar state file.
- The `max_last_verified_age_days` threshold and the separate `Verified against:` stamp. No lint code implements that threshold; it is an agent check in the refresh seed (seed 150). Nothing in the lifecycle depends on a stamp on every run: docs lint checks only the date format, and the review digest masks the date line.
- Keeping `docs/references/` copies and their shipped framework copies dated alike on the first stamp after an edit; that pairing is a release-preparation step and is not changed here.
- The date lines already written in the working tree.

## Acceptance Criteria

AC-1 and AC-2 together test the intent: no stamp without a change since the last stamp, and a stamp when there is one.

- [x] AC-1: In a temporary Git repository, a committed document that is then edited is stamped by a default-mode run that uses the local today (no `--date`); a later default-mode run with a later date value and no further edit leaves the file byte-identical and reports nothing updated. The second half fails on the current code.
- [x] AC-2: Default-mode runs on real files decide these cases:
   1. The AC-1 document, edited again with a modification time on a day after its stamp, is stamped by the next run.
   2. A document differing from `HEAD` only in its date line, with a modification date later than its stamp (a hand edit of the date line), is not stamped. This case fails under a modification-date-only rule.
   3. A document with a stamp later than the run's date and a content change outside the date line is stamped with the run's date. This case fails under a modification-date-only rule.
   4. A document with no `HEAD` version that is in the default target set is stamped.
- [x] AC-3: Explicit-path mode and all-documents mode stamp a document whose modification date is not later than its stamp and whose only difference from `HEAD` is its date line, as before this change.
- [x] AC-4: When the modification time of a document that differs from `HEAD` outside its date line cannot be read, the document is stamped; the run does not raise.
- [x] AC-5: The `docs-gardener: updated <path>` lines list exactly the documents written, and `wf_garden_docs` reports the same set.
- [x] AC-6: The tool reference states the new default-mode rule and the edge cases of requirement 6, the seed 050 sentence and its `AGENTS.md` copy agree with the rule, any other sentence found under requirement 8 is corrected, and the changelog has an Unreleased entry. The documents this change authors or edits validate.

## Tasks

- [x] Add the `HEAD` comparison outside the date line and the modification-date test to the default-mode path in `docs_gardener.py`, leaving the explicit modes and `refresh_last_verified`'s terminator handling as they are.
- [x] Tests for AC-1 to AC-5 in `test_docs_gardener.py`, setting modification times with `os.utime` on real files in a temporary Git repository; mutation checks in a scratch copy.
- [x] Search for and correct shipped descriptions of the default targets, including seed 050 and `AGENTS.md`; update the tool reference and `CHANGELOG.md`.
- [x] Full framework suite last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| gardener-rule-and-tests | implementer | none | Needs `framework_edit_allowed` |
| reference-text | implementer | gardener-rule-and-tests | Seed edits, if any, need `seed_edit_allowed` |

## Serialization Points

- `.wavefoundry/framework/scripts/docs_gardener.py`
- `.wavefoundry/framework/scripts/tests/test_docs_gardener.py`
- `docs/specs/mcp-tool-surface.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`

The gardener runs inside Prepare and the Close docs gate, so no other change edits it at the same time. `AGENTS.md` and `CHANGELOG.md` are also edited.

## Affected Architecture Docs

N/A: the change is confined to one decision inside the gardener and crosses no module boundary, flow or verification seam.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect: a stamp with no change |
| AC-2 | required | A real later change must still be stamped |
| AC-3 | required | Explicit requests must keep working |
| AC-4 | important | Failure must not suppress a stamp |
| AC-5 | required | The output lines are a parsed contract |
| AC-6 | important | Reference accuracy |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-18 | Created with `wf_new_bug` and planned only. The re-stamp was observed twice in one session on `docs/references/scan-findings-format.md` (stamped 2026-11-18 by Prepare passes; `git diff` shows its last content change is the wording edit dated by its previous stamp, 2026-11-17). The mechanism was read in `docs_gardener.collect_changed_markdown_paths`, `refresh_last_verified` and `gardener_run`; the cross-day case follows from that code and is marked `inferred` until AC-1's test executes it. | `git diff -- docs/references/scan-findings-format.md`; code read |
| 2026-11-18 | Readiness repair pass and implementation notes. `READY-QFZ-DATE-ONLY-DIFF` (red-team): a hand-edited date-only diff was stamped by the modification-date rule, contradicting requirement 3.4; requirement 1 now also requires a difference from `HEAD` outside the date line, and 3.4 is exact for a document whose only difference is the date line. `READY-QFZ-FUTURE-STAMP` (code-reviewer): a future stamp blocked a real content change from being stamped; requirement 1(b) now also holds when the stamp date is later than the run's date, with requirement 3.5, an AC-2 case and the time-zone edge case added. Also: requirement 6 edge cases, requirement 8 named texts and the seed 050 serialization point, the `max_last_verified_age_days` scope correction, Risks rows. Binding notes for implementation: put the check in the default branch of `resolve_metadata_targets`, not inside `collect_changed_markdown_paths`, because `test_upgrade_rerun_reliability.test_docs_gate_gardens_only_changed_docs_and_retains_real_edits` patches that function. Tests set modification times with `os.utime` to local noon of a day built from a naive local datetime, never arithmetic from UTC midnight. The stamping run in AC-1 passes no `--date`. AC-4 patches only the one helper that reads the modification time, for the target path, to raise `OSError`, with removal of the fallback as the known-bad check. AC-5's fixture includes a Git-changed document that is skipped and asserts it is absent from both the stdout lines and the `wf_garden_docs` result through the real `run_garden` parser, with a normalized manifest and handoff committed first. Fix the `AGENTS.md` sentence by editing seed 050 and keeping `AGENTS.md` in step. The tool reference states the past-`--date`, future-stamp, time-zone, midnight and hand-edited-date-line cases. | `wf_review_event` repair_start records `ev-ready-qfz-date-only-diff-2`, `ev-ready-qfz-future-stamp-2` (cycle 3) |
| 2026-11-18 | Verification round and further implementation notes (coordinator record). Both findings were reverified by fresh contexts of the lanes that raised them (`code-reviewer` by executing 13 scenarios of the amended rule); `code-reviewer`, `qa-reviewer` and `docs-contract-reviewer` approved readiness against receipt `review-policy-104f11610834f300d61e`. The spec body is not edited after this. BINDING notes for the implementer, the reviewers' and coordinator's choices, not separately confirmed by the operator: (1) The `HEAD` comparison runs after the repository's checkout conversion: normalize CRLF to LF on both sides, or read `HEAD` through Git's checkout filters; with `core.autocrlf=true` a raw byte comparison sees every document as different and breaks requirement 3.4 on Windows. Add an AC-2 case 2 variant with `core.autocrlf=true` and a CRLF working copy; a raw comparison is its known-bad control. (2) One Git read per changed document through the existing `_run_tree_kill` with a timeout; a timeout or any failure counts as differing. A renamed document has no `HEAD` version at its new path and is decided by check (b). (3) Compute the run's date once in `gardener_run` and pass it to the default branch. (4) Test recipes: AC-2 case 1 runs with a date on or after the new modification day (a run whose date equals the current stamp writes nothing under either rule and proves nothing); AC-2 case 4 adds the new document to the index with `git add` and gives it a modification time later than its stamp; the AC-3 document and AC-5's skipped document carry a stamp earlier than the run's date so the old code would have stamped them; AC-4's fixture sets a modification date no later than the stamp and a run date different from the stamp, so only the fallback can cause the stamp. (5) Put the rule in the `wf_garden_docs` entry of the tool reference that holds the mode contract, and check that its two shorter summaries do not contradict it; re-read seed 080's sentence after the edit. | Reverifications `ev-ready-qfz-date-only-diff-3`, `ev-ready-qfz-future-stamp-3`; approvals `ev-approval-code-reviewer-4`, `ev-approval-qa-reviewer-4`, `ev-approval-docs-contract-reviewer-6` |
| 2026-11-18 | Implementation (implementer, second pass). `docs_gardener.py`: the default branch of `resolve_metadata_targets` (new `run_date` argument, passed once from `gardener_run`) keeps a Git-changed document only when `_changed_since_stamp` (modification date later than the stamp, stamp later than the run's date, or an unreadable time, stamp or run date) and `_differs_from_head_outside_date_line` hold. The `HEAD` read is one `git show HEAD:./<rel>` per document through `_run_tree_kill` with a 30 s timeout, evaluated only after the cheap check holds; both sides have CRLF normalized to LF and the first `Last verified` date masked with the gardener's own pattern; a non-zero exit, `OSError`, `ValueError` or any `SubprocessError` (timeout included) counts as differing. The modification time is read through the new helper `_modification_time`. Explicit modes and `refresh_last_verified` are unchanged. Tests, all executed (`DefaultModeStampRuleTests` in `test_docs_gardener.py`, real files in temporary Git repositories, times set with `os.utime` to local noon of a naive local day): AC-1 and AC-2 case 1 `test_edit_is_stamped_once_and_a_later_run_writes_nothing` (first run passes no `--date`); AC-2 case 2 `test_date_line_only_difference_is_never_stamped` and `test_date_line_only_difference_with_autocrlf_crlf_working_copy` (`core.autocrlf=true`, CRLF working copy, LF blob asserted as the raw-comparison control); case 3 `test_future_stamp_with_a_content_change_is_stamped_with_the_run_date`; case 4 `test_document_with_no_head_version_is_stamped`; `test_head_read_failure_or_timeout_counts_as_differing`; AC-3 `test_explicit_modes_stamp_without_either_check`; AC-4 `test_unreadable_modification_time_stamps_a_changed_document`; AC-5 `test_updated_lines_and_run_garden_list_exactly_the_written_documents` (real `run_garden` subprocess; `updated`, `files_updated` and the stdout lines name only the stamped document; the skipped one is byte-identical). Byte-exact oracle moved: the timed-call census in `test_tree_kill_routing.py` gains `("docs_gardener.py", "_differs_from_head_outside_date_line", "_run_tree_kill"): 1`, because the new `HEAD` read is a new bounded child. Prose: the `wf_garden_docs` entry of `docs/specs/mcp-tool-surface.md` (rule, explicit modes, the requirement 6 edge cases); seed 050 and the matching `AGENTS.md` sentence; `CHANGELOG.md` under Unreleased, Fixed. Seed 080, seed 160 ("still stamps genuinely changed documents"), seed 190 step 19, the contributing guide and the two short tool-reference summaries were re-read and remain accurate; no rendered copy of the seed 050 sentence exists under `docs/prompts/` or the host surfaces, and no test pins it. Mutation evidence (scratch copy, `python3 -B -m unittest`): dropping check (a), check (b), the future-stamp clause, the unreadable-time fallback (both returning false and letting it raise), the non-zero-exit fallback, the exception fallback, the CRLF normalization and the date-line masking each fail at least one new test; applying the checks in `--paths` mode or in `--all-docs` mode each fail the AC-3 test; the pre-change `HEAD` gardener fails the AC-1, AC-2 case 2 (both), AC-5 and AC-4 tests. Gapfill: shell `git grep` was used for the shipped-text sweep of requirement 8 and for pinned-text discovery, where exact substring scans across tracked files were the right instrument. Focused runs: 464 tests across 7 files OK and 733 tests across 9 files OK; `wf_validate_docs` passed; gates closed. Not verified: native Windows, WSL2, Python 3.11. | `run_tests.py --file` output, 2026-11-18; `wf_gate_status` |
| 2026-11-18 | Delivery repair pass 2 (implementer, cycle 4, context `23p9u-delivery-repair-2`). `DELIV-QFZ-RUN-DATE-UNPINNED`: new test `DefaultModeStampRuleTests.test_future_stamp_is_compared_with_the_run_date_not_the_local_today` commits a document stamped today, edits its body, sets its modification time to local noon today with `os.utime`, runs the default mode with `--date` two days earlier, and asserts the document is stamped with that earlier date and is the only path written. No change in `docs_gardener.py`. Mutation evidence (scratch copy, `python3 -B -m unittest tests.test_docs_gardener`): with `gardener_run` calling `resolve_metadata_targets(root, args)` without the run date, the new test fails (39 tests, failures=1) and no other test does; restored, 39 tests OK. Also: in the `wf_garden_docs` entry of `docs/specs/mcp-tool-surface.md`, "sets the modification time to the stamp day" now reads "to the day of the run", because the write is an ordinary file write and a `--date` run stamps a date other than the day the write happens. Focused run, gates closed: "Ran 194 tests across 4 files in 4.510s", OK. | `wf_review_event` repair_start `ev-deliv-qfz-run-date-unpinned-2`; `run_tests.py --file` output, 2026-11-18 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-18 | Stamp only when the document changed since its stamp. Operator's direction, quoted: "they shouldn't be tagged unless they change to reduce git churn, etc." | The operator asked for it. | Keep stamping every changed document: the reported churn. |
| 2026-11-18 | Detect "changed since its stamp" by comparing the file's modification date with the stamp date. Planner's choice, not separately confirmed by the operator. | No new state, one comparison, and the stamp write itself makes the document stable on later runs. It errs toward stamping when a time is refreshed or unreadable, which is the old behaviour. | Compare with the `HEAD` blob and stamp once per commit cycle: deterministic, but a second edit days later would not be stamped, which contradicts "unless they change". A content hash in a sidecar file: exact, but a new state file and a new thing to keep in step. |
| 2026-11-18 | Readiness repair pass: combine a `HEAD` comparison outside the date line with the modification-date test (requirement 1), and stamp a document whose stamp is later than the run's date. The repair's choices, not separately confirmed by the operator. | The modification-date test alone stamped a hand-written date-only diff (red-team) and left a future stamp in place over a real edit (code-reviewer). The `HEAD` comparison is red-team's alternative; precedent `gen_codebase_map._strip_date_line`. Together the two checks keep the one-stamp-per-change behaviour the earlier row chose and make requirement 3.4 exact. | Qualify requirement 3.4 to gardener-written date lines only: leaves hand-restored dates stamped. `HEAD` comparison alone: stamps every changed document on every new day, the reported churn. |

Mechanism efficacy (planner's assessment, revised in the readiness repair pass). Replay: `scan-findings-format.md` differs from `HEAD` in wording, so (a) holds and (b) decides. The first Prepare pass on 2026-11-18 would have been skipped only if the file's modification date was still 2026-11-17, which cannot be confirmed now. After the coordinator restored the date line by hand that day, the modification-date test alone would have re-stamped, and the `HEAD` comparison would not have helped either, because the content differs from `HEAD`. So the rule removes the every-new-day re-stamp, and a hand edit of a changed document's date line still causes one stamp on the next run; that is a stated limit (requirement 6.6). Control: the rule decides the write; nothing is advisory. Wrong stamps: a tool or Git operation that rewrites the file without changing content refreshes the time and causes one stamp, after which the document is stable again. Misses: an edit made on the same day as the stamp, after it, keeps that day's date, which is already correct. Existing mechanisms: none; the gardener has no memory of what it stamped. Measure after release: across a multi-day uncommitted wave, `git diff` shows no date-only changes on documents not edited that day.

## Risks

| Risk | Mitigation |
| --- | --- |
| A real change is not stamped. | A content write moves the modification time past an older stamp; a stamp in the future no longer blocks a stamp, because requirement 1(b) also holds when the stamp date is later than the run's date (AC-2 case 3); an unreadable time stamps; a document with no `HEAD` version counts as differing. AC-2 pins the later-edit case. |
| Modification times differ by platform or are coarse. | The comparison is by calendar date, not by second; Windows, macOS, Linux and WSL2 all expose the time; the WSL2 mounted-drive and time-zone cases are stated under requirement 6. |
| The `HEAD` read costs time or fails. | One Git read per Git-changed document, bounded by the changed set the gardener already lists; a failed read counts as differing, so it never suppresses a stamp. |
| The first stamp after an edit still dates a `docs/references/` copy differently from its shipped copy. | Out of scope and stated; that pairing is release preparation. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
