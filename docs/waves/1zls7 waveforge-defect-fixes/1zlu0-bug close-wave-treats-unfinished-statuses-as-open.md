# Close Wave Treats Unfinished Change Statuses As Open

Change ID: `1zlu0-bug close-wave-treats-unfinished-statuses-as-open`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-02
Wave: 1zls7 waveforge-defect-fixes

## Rationale

Waveforge reported that `wf_close_wave` closes a wave while one of its changes is still `blocked`, `review` or `retry`. The cause is in `wf_close_wave_response`: it reads every `Change Status` (and legacy `Item Status`) value from the wave record and raises `open_changes_remaining` only for the hardcoded set `open_statuses = {"stub", "planned", "ready", "active"}`. Every other status passes, including the ones that plainly mean "not finished". The framework already has an authoritative list of finished statuses, `TERMINAL_CHANGE_STATUSES` in `wave_lint_lib/constants.py` (`complete`, `completed`, `done`, `deferred`, `moved`, `superseded`), which docs-lint uses to decide whether a dependency is satisfied. Close keeps a second, inverted list that drifted from it.

The operator decided (2026-10-02): close refuses while ANY change is in a non-terminal status; the check is derived from the lint terminal set (one source), not a second hardcoded list; an unknown status counts as open.

Brief: the consumer is every operator and distribution closing a wave; success is that close cannot report a wave closed while a change in it is unfinished, and that the definition of "finished" lives in one place.

## Requirements

1. **One done source.** `wave_lint_lib/constants.py` defines, next to `TERMINAL_CHANGE_STATUSES` (a tuple), `DONE_CHANGE_STATUSES = frozenset(TERMINAL_CHANGE_STATUSES) | {"implemented"}` and one predicate beside it (for example `is_done(status, anchor_type)`): a `change` record is done when its status is in `DONE_CHANGE_STATUSES`; a legacy `item` record is done when its status is in `TERMINAL_ITEM_STATUSES` (unchanged for items); a record with no status is not done. `wf_close_wave_response` decides openness only through that predicate (or set), and docs-lint's dependency rule reads the same one (Requirement 6). The hardcoded `open_statuses` set is removed; no other status list is introduced in the close path.
2. **Close reads the lint record parser.** The close check iterates `wave_validators._parse_work_records(text, rel)` over the wave record, which yields each record's id, status and `anchor_type` (`change` or legacy `item`) and strips surrounding whitespace from every line, so an indented `Change Status` line is read (today's `server_impl._CHANGE_STATUS_PATTERN` is column-0 only and id-less, so an indented record was silently skipped). It no longer uses `_CHANGE_STATUS_PATTERN` for this check (other callers of that pattern are unchanged). **Unknown means open:** a record whose status is not done is open, including a value no framework status defines and a record whose status line the lint parser cannot read (it accepts only lower-case `[a-z0-9-]+`, so `Complete` or a value with a space leaves the status unset). This replaces today's lower-casing: an upper-case terminal value now refuses close, which is the fail-closed reading of the operator's unknown-means-open decision; lint already rejects such a value.
3. **Refusal content.** The `open_changes_remaining` diagnostic keeps its code and recovery tool, and its message names each open change id with its current status (not only the de-duplicated status values), so an operator can see which change blocks close. It applies in `dry_run` and `create` alike, and close writes nothing when it fires (existing hard-gate behaviour, unchanged).
4. **Unchanged behaviour.** Changes in a terminal status still pass; the other close gates, their order and their diagnostic codes are unchanged; `CLOSURE_ONLY_DIAGNOSTIC_CODES` in `lifecycle_gates.py` keeps `open_changes_remaining`.
5. **Census before the change lands.** The implementer re-runs the census in the Progress Log (predicate below) against the tree at implementation time and records the result; any live wave that would newly fail goes to the operator before the code change, per the sibling `1zltr` precedent.
6. **`implemented` does not block wave close and satisfies dependencies (operator decision 2026-10-02).** Wave close treats a change in `implemented` as done (Requirement 1). `implemented` is NOT added to `TERMINAL_CHANGE_STATUSES` and stays non-terminal: a change is closed only when it is closed (`complete`, through `wf_close_change` in wave `1zlu1`). docs-lint's dependency rule in `wave_validators` (the check that fails a progressable record whose `Depends On` target is not finished) reads the Requirement 1 predicate, so an `implemented` change dependency satisfies a dependent; legacy item dependencies keep `TERMINAL_ITEM_STATUSES`. The change-record failure message becomes: "`<rel>`: change `<id>` is `<status>` but dependency `<dep>` is still `<dep status>`. The dependency must reach a done status (terminal, or `implemented`); allowed: " followed by the backticked values of `DONE_CHANGE_STATUSES` in sorted order (built by the existing `allowed_values_suffix`); the item-record message is unchanged. The census is re-run against this rule: live waves holding only `implemented` or terminal changes still close.
7. **Pinned text moves with the contract.** The `open_changes_remaining` message is pinned in `tests/fixtures/lifecycle-gate-golden.json` and `tests/fixtures/lifecycle-gate-pre-configured-golden.json` (six occurrences each today, "Wave has unresolved change statuses: planned."). Only `lifecycle-gate-golden.json` (the fixture `check_golden` writes) is regenerated with `WF_UPDATE_LIFECYCLE_GOLDEN=1 WF_OVERWRITE_LIFECYCLE_GOLDEN=1`, and the diff is reviewed and recorded in the Progress Log. `lifecycle-gate-pre-configured-golden.json` is the frozen extraction baseline that `test_only_declared_observability_additions_since_extraction_golden` reads as `before`; it is never regenerated or hand-edited. That test instead declares the delta by reverting the new `open_changes_remaining` message onto the old one in its walk (for example by adding the code to `hint_message_codes` or an equivalent message revert), so exactly that message change is declared and no other envelope field moves. `tests/test_docs_lint.py` (around line 1956, which pins "The dependency must reach a terminal status; allowed:" and loops over `TERMINAL_CHANGE_STATUSES`) is updated to the Requirement 6 message and loops over `DONE_CHANGE_STATUSES`.

## Scope

**Problem statement:** close treats `blocked`, `review`, `retry` and any unknown status as finished because it checks a hardcoded open list instead of the lint terminal set.

**In scope:**

- The open-status check in `wf_close_wave_response` and its diagnostic message, reading `wave_validators._parse_work_records`.
- `wave_lint_lib/constants.py`: `DONE_CHANGE_STATUSES` and the done predicate; `wave_lint_lib/wave_validators.py`: the dependency rule and its message (Requirement 6).
- Tests: a reproducer per status class (`blocked`, `review`, `retry`, an unknown token, an indented record, a legacy `Item Status` record), the done statuses passing, the dependency rule, and a source guard that the close path holds no literal status list.
- The pinned text in Requirement 7: `lifecycle-gate-golden.json` regenerated, the declared-delta revert in `test_only_declared_observability_additions_since_extraction_golden` (the frozen pre-configured baseline is left untouched), and `tests/test_docs_lint.py`.
- The `docs/specs/mcp-tool-surface.md` close entry, if it describes which statuses block close, and a CHANGELOG `### Fixed` bullet.

**Out of scope:**

- The dashboard's own status sets: `_TERMINAL_CHANGE_STATUSES = {"complete", "completed", "closed"}` in `dashboard_lib.py` (lacks `done`, `deferred`, `moved`, `superseded`; includes `closed`, a wave status), `DONE_STATUSES` in `dashboard/dashboard.js` (around line 127; already includes `implemented`, `approved` and `closed`) and the badge status lists in `dashboard/ds/wfds.js` (around line 119). Recorded as a follow-up; not aligned here because their effect is display classification and their callers were not censused.
- Status drift between `wave.md` and a change document's own `Change Status` at close (red-team R8): close reads `wave.md` only. Recorded as a follow-up.
- Rewriting statuses in closed wave records.
- Reopening a closed wave.

## Acceptance Criteria

- [x] AC-1: A wave whose record holds one change in `blocked`, `review` or `retry` (one fixture per status) is refused by `wf_close_wave` in `dry_run` and `create` with `open_changes_remaining`, and `create` writes nothing; against the current code each of these fixtures closes (the reproducer fails before the fix).
- [x] AC-2: A change status that is not a lint status (an unknown token) and a legacy `Item Status` value outside `TERMINAL_ITEM_STATUSES` are each refused the same way.
- [x] AC-3: A wave whose changes are all in `DONE_CHANGE_STATUSES` passes the open-change check; a test asserts `DONE_CHANGE_STATUSES - set(TERMINAL_CHANGE_STATUSES) == {"implemented"}`, and a test that patches `DONE_CHANGE_STATUSES` to drop a status makes that status refuse close, proving the check reads the lint constant rather than a copy. A wave whose only open change has an indented `Change Status` line refuses close.
- [x] AC-4: The `open_changes_remaining` message names each open change id with its status.
- [x] AC-5: A source guard on `wf_close_wave_response` finds no literal set, frozenset or tuple of status names and no reference to `_CHANGE_STATUS_PATTERN`; reintroducing `{"stub", "planned", "ready", "active"}` fails it. Status names live only in `wave_lint_lib/constants.py`.
- [x] AC-6: The census in Requirement 5 is recorded in the Progress Log with its predicate; the Requirement 7 golden diff is recorded; and tests show a wave whose changes are all `implemented` or terminal closes while one with a `review`, `blocked`, `retry` or unknown-status change refuses, and a `ready` or `active` change whose dependency is `implemented` lints clean while one whose dependency is `active` still fails with the Requirement 6 message.
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Re-run the live-wave census and record it.
- [x] Write the failing reproducers (AC-1, AC-2) against the current code.
- [x] Add `DONE_CHANGE_STATUSES` and the done predicate to `wave_lint_lib/constants.py`.
- [x] Replace `open_statuses` with the predicate over `_parse_work_records` and extend the diagnostic message with change ids.
- [x] Switch the dependency rule to the predicate with the Requirement 6 message; update `tests/test_docs_lint.py`.
- [x] Add the constant-patch test (AC-3) and the source guard (AC-5).
- [x] Regenerate only lifecycle-gate-golden.json (the pre-configured fixture is the frozen baseline), add the declared-delta entry, and record the reviewed diff.
- [x] Update the tool-surface spec if it lists blocking statuses; add the CHANGELOG bullet.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| close-open-status | implementer | `1zltr` edits to `wave_validators.py` and the close gate landed | `wave_lint_lib/constants.py`, `wave_lint_lib/wave_validators.py`, `wf_server/server_impl.py`, `tests/test_server_tools_lifecycle.py`, `tests/test_docs_lint.py`, lifecycle golden fixtures |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_golden.py`
- `.wavefoundry/framework/scripts/tests/fixtures/lifecycle-gate-golden.json`
- `docs/specs/mcp-tool-surface.md`

- The CHANGELOG at the repository root is edited too.

## Affected Architecture Docs

N/A: the change corrects one predicate inside the existing close gate, makes it and the lint dependency rule read one done set defined beside the lint constants, and adds no status value; no boundary, flow or test topology moves.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported defect. |
| AC-2 | required | Unknown statuses are open by operator decision. |
| AC-3 | required | Proves the one-source rule. |
| AC-4 | important | Makes the refusal actionable. |
| AC-5 | important | Keeps a second list from returning. |
| AC-6 | required | The census and the `implemented` decision decide whether the fix breaks normal closes. |
| AC-7 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Reverification follow-up (reviewer A F1, F2). F1: the line walk now also checks a parsed record's statuses, so an `Item Status` line inside a change record keeps it open (HEAD refused it; the first repair skipped every parsed id). F2: the loose id patterns now require a backticked id, so a prose `Change ID:` line starts no record and no longer refuses close. | `CloseWaveOpenStatusTests.test_an_item_status_line_inside_a_change_record_is_read`, `test_a_prose_id_label_starts_no_record`; both mutations (skip parsed ids; optional id) killed in a scratch copy; census over all 348 `wave.md` records unchanged against the first repair; `CloseWaveOpenStatusTests` and `test_change_doc_checklist` 61 OK. |
| 2026-10-02 | Delivery-review repair. B1 (blocking): the record parser attached every later stripped status line to the current record and the last one won, so a `planned` or `active` record followed by a duplicate `Change Status: complete`, a fenced example under a later heading or an indented list line reading `complete` closed cleanly. Status is now read as a union, failing closed: `wave_validators.WorkRecord` gains `status_values` (every status line the parser attributes to the record, in order, `None` for a status-labelled line the strict pattern cannot read; `status` keeps its last-wins meaning for lint), and `_close_open_work_records` reports a record open when any of those values is not done, when one is unreadable or when there is none; a looser line walk (new `CHANGE_ID_LABEL_LINE_PATTERN`, `ITEM_ID_LABEL_LINE_PATTERN`, `CHANGE_STATUS_LABEL_LINE_PATTERN`, `ITEM_STATUS_LABEL_LINE_PATTERN` in `wave_lint_lib/constants.py`) adds records whose id the lint parser rejects (the column-0 reading HEAD used, as the checklist collector keeps such ids) and a status line before any id line (reported as `a status line outside any record`). `DONE_CHANGE_STATUSES` and `is_done` stay the single source; no status list in the close path (the AC-5 source guard passes). N2c: a dependency with no status is not done and the message now reads `has no readable status` instead of `is still None`. N4: the dependency requirement wording is built by the new `_unmet_dependency_message`, keyed on the DEPENDENCY's anchor type as `is_done` is. CHANGELOG `Fixed` sentence rewritten for the union reading. Census (predicate: every `docs/waves/*/wave.md`, open records under the pre-repair last-wins reading versus the union reading): 348 records, 0 differ, live waves `1zls7` (0 open), `1zls8` (3), `1zlu1` (3) unchanged (`scratchpad/1zls7-repair-b1/census.txt`). Tests: `CloseWaveOpenStatusTests` gains `test_a_later_done_status_line_cannot_hide_an_open_one` (V2 duplicate, V4 fenced, V5 indented, each for `planned` and `active`, dry_run and create), `test_a_record_with_no_status_line_stays_open`, `test_an_unreadable_status_line_beside_a_done_one_is_open`, `test_an_id_outside_the_lint_shape_is_read_by_the_line_walk`, `test_a_status_line_outside_every_record_is_open`; `test_docs_lint.py` gains `test_a_dependency_with_no_status_is_not_done` and `test_dependency_wording_follows_the_dependency_anchor_type`. Failing-first (`scratchpad/1zls7-repair-b1/failing-first.txt`): 16 subtest failures across the V2/V4/V5, unreadable-line and orphan-line tests (the no-status test passed before, as a pin). An intermediate union that refused every status line no lint record claimed broke 9 existing close tests whose fixtures use non-lint ids; the line walk now attributes those lines to their own id records. Mutations in a scratch copy (`scratchpad/1zls7-repair-mutations.txt`), 18 of 18 killed: parser reading last-wins, unreadable line not attributed, line walk dropped, orphan line ignored, dependency wording keyed on the dependent, no-status dependency treated as done. Suites (scratch copy of the repaired tree, `scratchpad/1zls7-repair-suite-*.txt`): `run_tests.py --no-cache` 10722 tests across 156 files OK, 34 skipped; `--profile second` 10719 run, 0 of 156 files failed; `--profile declared` 10722 run, 0 of 156 files failed. | `scratchpad/1zls7-repair-*`, 2026-10-02 |
| 2026-10-02 | Implemented. Census re-run (Requirement 5) before the change, predicate: every `docs/waves/*/wave.md` whose `Status:` is not `closed`, with its `Change Status`/`Item Status` values. Result: 3 live waves. `1zls7` (active): 7 `planned` and 1 `implemented` (`1zlu5`, added to the record after planning); `implemented` is done under Requirement 6 and `planned` already refused close. `1zls8` and `1zlu1` (planned): only `planned`. No live wave newly fails close (`1zls6` is now closed). Code: `wave_lint_lib/constants.py` gains `DONE_CHANGE_STATUSES = frozenset(TERMINAL_CHANGE_STATUSES) | {"implemented"}` and `is_done(status, anchor_type)` (change: in the done set; item: in `TERMINAL_ITEM_STATUSES`; no status: not done). `server_impl.py`: new `_close_open_work_records` iterates `wave_validators._parse_work_records` and keeps every record that `is_done` rejects; `wf_close_wave_response` no longer holds `open_statuses` or reads `_CHANGE_STATUS_PATTERN`, and `open_changes_remaining` names each open change with its status (or `has no readable status`). `wave_validators.py`: the dependency rule reads `is_done` for the dependency record; the change-record message is the Requirement 6 text with the sorted `DONE_CHANGE_STATUSES`; the item message is unchanged. Requirement 7: `lifecycle-gate-golden.json` regenerated through `check_golden` with both variables (the test itself passes an empty environment); reviewed diff = exactly the 6 `open_changes_remaining` messages, `Wave has unresolved change statuses: planned.` becoming e.g. ``Wave has unresolved change statuses: `0exxlz-ref fixture-change` is `planned`.`` (`scratchpad/1zls7-1zlu0-golden-diff.txt`); `lifecycle-gate-pre-configured-golden.json` untouched; `test_only_declared_observability_additions_since_extraction_golden` declares the delta by adding `open_changes_remaining` to `hint_message_codes`; `test_docs_lint.py` pins the new message and loops over `DONE_CHANGE_STATUSES`. The spec's close entry does not list blocking statuses, so it is not edited. Tests: `test_server_tools_lifecycle.py` `CloseWaveOpenStatusTests` (7) and `test_docs_lint.py` `test_implemented_dependency_satisfies_a_dependent_change` plus the updated `test_blocked_dependency_names_which_statuses_would_unblock_it`. AC map: AC-1 `test_blocked_review_and_retry_refuse_close` (dry_run and create, create writes nothing); AC-2 `test_unknown_status_and_legacy_item_refuse_close`, `test_unreadable_status_refuses_close`; AC-3 `test_done_statuses_pass_the_open_change_check`, `test_close_reads_the_lint_done_set` (patches `DONE_CHANGE_STATUSES`), `test_indented_record_refuses_close`; AC-4 the message assertions in each refusal test; AC-5 `test_close_path_holds_no_status_list` (AST walk of `wf_close_wave_response` and `_close_open_work_records`); AC-6 the census above, the golden diff, `test_done_statuses_pass_the_open_change_check` and the docs-lint dependency tests. Failing-first against HEAD (`scratchpad/1zls7-1zlu0-failing-first.txt`): 14 failures and 3 errors in `CloseWaveOpenStatusTests` (each reproducer closed), and both docs-lint dependency tests failed. Mutations, all killed: the old `open_statuses` literal reintroduced (`test_close_path_holds_no_status_list`), `implemented` dropped from the done set (`test_done_statuses_pass_the_open_change_check`, `test_close_reads_the_lint_done_set`), close reading the old open set (`test_blocked_review_and_retry_refuse_close` and 5 more), dependency rule terminal-only (`test_implemented_dependency_satisfies_a_dependent_change`). Gapfill: shell grep located the close check, the census statuses and the docs naming the codes; `code_keyword` would have served the code lookups. Suites (scratch copy of the whole wave tree, `run_tests.py --no-cache`): 10689 tests across 156 files OK, 34 skipped; `--profile declared` 10689 OK; `--profile second` 10686 run with one failure, `test_blockquoted_and_unusual_mark_items_are_markable`, whose fixture wrote an unlocalized `Wave ID:` line that the second profile reads as a member id; the fixture now goes through `_loc` and `--profile second --file test_server_tools_lifecycle.py` passes. An earlier full run caught a decorator displaced onto the inserted `_mark_item_block_end` helper (wf_mark layout refusals) and vocabulary and literal census hits; all fixed before the counted run. | `scratchpad/1zls7-1zlu0-*`, 2026-10-02 |
| 2026-10-02 | Planned. Census, predicate: every `docs/waves/*/wave.md` whose `Status:` is not `closed`; for each, the `Change Status`/`Item Status` values in the record. Result: 4 live waves. `1zls6` (active) holds one change in `implemented`, which is not terminal, so it would newly fail close under the decided rule. `1zls7`, `1zls8` and `1zlu1` (planned) hold only `planned` changes, which already fail close today. Wider census, predicate: closed wave records (`Status: closed`) holding at least one change status outside the lint terminal set: 238 of 344. Repository-wide status counts across all wave records: `implemented` 639, `complete` 347, `implementing` 12, `done` 10, `deferred` 4, `review` 4, `completed` 2, `landed` 2, `partially-implemented` 2, `planned` 13, `admitted` 1, `reconsidered-and-reverted` 1. `implemented` is the normal pre-close status here (recent closes `1zicq` through `1zli8` all carry it), so the open question in Requirement 6 was raised. | Shell census over `docs/waves/*/wave.md`, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Recheck repairs: regenerate only `lifecycle-gate-golden.json` and declare the message delta by a revert in the extraction test; the checklist collector (1zltr) reads change ids through the same `_parse_work_records`, closing red-team R4 for both close gates | The pre-configured fixture is the frozen extraction baseline read as `before`; regenerating it would destroy what the declared-delta test protects. One record parser for status and checklist gates means an indented change block cannot escape either | Regenerate both fixtures; keep the column-0 `_CHANGE_ID_PATTERN` in the collector |
| 2026-10-02 | Close refuses while any change is in a non-terminal status; unknown statuses count as open | Operator decision: a wave must not report closed while work in it is unfinished | Add `blocked`, `review`, `retry` to the hardcoded open list (rejected: keeps two lists that drift, and still passes unknown statuses) |
| 2026-10-02 | Derive the check from `TERMINAL_CHANGE_STATUSES` (and `TERMINAL_ITEM_STATUSES` for legacy item records) | Operator decision: one source for "finished", the one docs-lint already uses for dependencies | Move the list into a new shared module (rejected: the lint constant already is the shared definition) |
| 2026-10-02 | Escalate the `implemented` census finding to the operator before Prepare (Requirement 6) | The decided rule refuses the status 238 closed waves and the active wave `1zls6` carry; shipping it without a decision would block the next normal close | Silently add `implemented` to the terminal set (rejected: changes the lint vocabulary without a decision); ship as decided (rejected: breaks current practice unannounced) |
| 2026-10-02 | Dashboard terminal set left as a follow-up | Its effect is display classification and its callers were not censused | Align it here (only if the operator asks) |
| 2026-10-02 | Readiness amendments: Requirement 1 now defines `DONE_CHANGE_STATUSES = frozenset(TERMINAL_CHANGE_STATUSES) \| {"implemented"}` and one done predicate beside the lint constants, read by close and the lint dependency rule; close iterates `wave_validators._parse_work_records` (ids, statuses, anchor types, whitespace-stripped, fixing indented records, red-team R4) instead of `_CHANGE_STATUS_PATTERN`; AC-3 patches the done set and pins the `implemented`-only difference; AC-5 also forbids `_CHANGE_STATUS_PATTERN`; Requirement 7 brings the two lifecycle golden fixtures, the declared-delta entry and `test_docs_lint.py` into scope with the new dependency message; `wave_validators.py` added to review targets; pending-decision residue removed; dashboard `DONE_STATUSES` and `wfds.js` named in the follow-up; red-team R8 (wave.md versus change-doc status drift) recorded as a follow-up | Readiness review: Requirements 1 and 6 and AC-3 and AC-5 contradicted each other, and pinned text outside the named files would have failed | Keep two definitions (rejected: the drift this change fixes); keep the column-0 server pattern (rejected: misses indented records and cannot name ids) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The fix blocks the next close of any wave whose changes are `implemented` | Resolved by Requirement 6: `implemented` does not block wave close |
| A distribution with its own status values finds them treated as open | Intended (unknown means open); the refusal names each change and status so the remedy is visible |
| The sibling `1zltr` edits the same close gate area and `wave_validators.py` | Different functions (`_collect_silent_unchecked_items_for_close`, the checklist parser and the checklist lint rules, not the status check or dependency rule); `1zltr` lands first per the wave watchpoint |
| An upper-case or spaced status that closed before now refuses | Intended (unknown means open, Requirement 2); lint already rejects those values, and the refusal names the change |
| Platform behaviour | Pure string comparison over the record text; identical on Windows, macOS, Linux and WSL2 (status values are lower-cased; line endings do not affect the existing pattern) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
