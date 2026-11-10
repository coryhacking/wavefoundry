# Keep a Deferral Reason From Splitting a Multi-Line Acceptance Criterion

Change ID: `23042-bug mark-ac-reason-splits-multiline-criterion`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-10
Wave: 23041 writing-guide-concrete-precision

## Rationale

`wf_mark_ac(state="~", reason=...)` writes the reason as ` *<reason>*` at the end of the acceptance criterion's first line, even when the criterion continues on indented lines below it. Observed in wave 23041: AC-3 of `23040-enh writing-guide-concrete-precision` has a first line ending "The result is one of:" followed by three numbered outcome lines. After `wf_mark_ac(ac_id="AC-3 (intent check, with a control)", state="~", reason="Failed by the rule decided at readiness: a tie. ...")`, the line reads "The result is one of: *Failed by the rule decided at readiness: a tie. ...*" and the numbered outcomes follow the reason. Expected: the criterion's text stays intact and the reason follows the whole criterion.

Cause, in `_mark_change_item_response` (`.wavefoundry/framework/scripts/wf_server/server_impl.py`): the deferral branch edits only `lines[index]`, inserting the reason at `match.end("text")`. The same function computes the item's end with `_mark_item_block_end` but uses it only to match the target and to build `matched_text`, not to place the reason.

A second defect blocks the obvious repair. The docs-lint rule that requires a note on a required-priority `[~]` criterion, `_check_tilde_required_ac_has_inline_note` in `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`, reads items through `_lint_ac_items`, which returns only each item's first line. A note written on a continuation line is invisible to it, so a criterion with a short first line and its note below would fail lint with "lacks an inline status note".

## Product Intent

Agents and operators who defer a multi-line acceptance criterion get a record in which the criterion reads as written and the reason follows it, and docs-lint accepts that reason. Single-line criteria keep their current form. The fix also repairs the one misplaced note it was found in.

## Requirements

1. When `wf_mark_ac` defers a criterion with a reason and the criterion has continuation lines (`_mark_item_block_end(lines, index) > index + 1`), the reason is written as one new line immediately after the item's last continuation line: the item's blockquote prefix (empty, or the `>` prefix of its first line), then two spaces, then `*Status: <reason>*`, then the line ending the document's other lines carry (`\r\n` in a CRLF document, `\n` otherwise). The first line and every continuation line are otherwise byte-identical; only the checkbox mark changes.
2. When the criterion has no continuation lines, the existing behavior is unchanged: ` *<reason>*` is appended to the end of the first line.
3. `matched_text` in the response includes the inserted `*Status:*` line. Dry-run previews, the `dry_run_not_written` recovery text and the receipt refresh are otherwise unchanged.
4. `_mark_item_block_end` moves from `server_impl.py` to `.wavefoundry/framework/scripts/change_doc_checklist.py` as a public function with the same continuation rule, and both `_mark_change_item_response` and the lint rule call it. `_lint_ac_items` and its return value are unchanged.
5. `_check_tilde_required_ac_has_inline_note` keeps its two existing first-line checks (an italic segment matching `_INLINE_ITALIC_RE`, or at least `_INLINE_NOTE_MIN_CHARS` (40) characters of prose after the label) unchanged. It also accepts a criterion when one of its continuation lines, after its blockquote prefix, matches `^\s*\*Status:\s*[^*\n]{4,}\*\s*$`. No other continuation text counts: neither italic text in the criterion's own wording nor the length of its continuation lines.
6. In `docs/waves/23041 writing-guide-concrete-precision/23040-enh writing-guide-concrete-precision.md`, the AC-3 note is moved by hand, after the lint change lands, to the position Requirement 1 defines, gaining the `Status: ` prefix; the rest of its wording is unchanged. A Progress Log row in that document records the move and that it changes 23040's review digest.
7. The two existing tests that pin first-line placement for wrapped criteria, `test_quoted_wrapped_criterion_marks_by_its_logical_label_with_reason` and `test_marking_a_crlf_document_changes_only_the_mark` in `test_server_tools_lifecycle.py`, are updated to the Requirement 1 output.

## Scope

**Problem statement:** a deferral reason splits a multi-line acceptance criterion, and docs-lint cannot see a reason placed anywhere but the first line.

**In scope:**

- `_mark_change_item_response` deferral branch in `.wavefoundry/framework/scripts/wf_server/server_impl.py`.
- `_check_tilde_required_ac_has_inline_note` in `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`, accepting a `*Status:*` continuation line.
- `_mark_item_block_end` moved into `.wavefoundry/framework/scripts/change_doc_checklist.py`.
- Tests in `test_server_tools_lifecycle.py`, `test_docs_lint.py` and `test_change_doc_checklist.py` under `.wavefoundry/framework/scripts/tests/`.
- The AC-3 note move in `23040` (Requirement 6) and one CHANGELOG `[Unreleased]` / Fixed bullet.

**Out of scope:**

- Rewriting notes already placed in closed waves.
- `wf_mark_task`, which takes no reason.
- Changing how the close gate reads checkbox state.
- Seed 170's wording "on the same line" for the inline note; its own example already places a note on a continuation line, and changing it needs a seed edit outside this fix. Recorded in the Decision Log.
- Rejecting a reason that contains `*` or a newline; that risk exists today and is unchanged.

**Platform behavior:** text handling only. The function splits the raw text on `\n`, so in a CRLF document each line keeps its trailing `\r`; only a document with a lone `\r` is normalized to `\n` first. The new line carries the document's own line ending (Requirement 1), so a CRLF document stays CRLF. Behavior is the same on Windows, macOS, Linux and WSL2.

## Acceptance Criteria

- [x] AC-1: A test in `test_server_tools_lifecycle.py` defers a criterion whose first line ends with a colon and is followed by three numbered lines indented three spaces. After `create`, the first line and the three numbered lines are byte-identical to before except for the checkbox mark, the next line is exactly `  *Status: <reason>*`, and `matched_text` ends with that line. The same case in a CRLF document gives `  *Status: <reason>*\r\n` and no line without `\r`. Run against the current code, both cases fail because the reason lands at the end of the first line.
- [x] AC-2: In `test_server_tools_lifecycle.py`, a single-line criterion deferred with a reason gives exactly today's output (` *<reason>*` at the end of the line). A blockquoted two-line criterion gives exactly `>   *Status: <reason>*` as its new line, and running `_check_tilde_required_ac_has_inline_note` on the result reports no failure. The two existing wrapped-criterion tests are updated to the Requirement 1 output and pass.
- [x] AC-3: Tests in `test_docs_lint.py` for a required-priority `[~]` criterion whose first line has fewer than 40 characters after the label: with a `  *Status: <reason>*` continuation line it passes; with continuation lines of 40 or more characters but no `*Status:*` line it fails with "lacks an inline status note"; with an italic phrase of 4 or more characters in a continuation line but no `*Status:*` line it fails; a criterion labelled `AC-3 (intent check, with a control):` with its note on a `*Status:*` line passes. Run against the current lint, the first and last cases fail.
- [x] AC-4: `test_change_doc_checklist.py` covers the moved `_mark_item_block_end` with the existing continuation rule (indented line continues; blank line, heading, next checklist item and a line at another blockquote depth end the block). The AC-3 note in `23040` sits on a `  *Status: ...*` line after its numbered outcome lines, its other text unchanged, and `wf_validate_docs` passes.
- [x] AC-5: `test_server_tools_lifecycle.py`, `test_docs_lint.py` and `test_change_doc_checklist.py` pass, every test this change adds passes, and the documents this change edits validate. The whole suite runs last before close as the wave's close gate.

## Tasks

- [x] Write the AC-1 to AC-3 tests first and confirm the named cases fail on the current code.
- [x] Move `_mark_item_block_end` into `change_doc_checklist.py`; change the deferral branch and the lint rule; update the two existing wrapped-criterion tests.
- [x] After the lint change, move the AC-3 note in `23040`, add its Progress Log row, and add a `### Fixed` subsection with one bullet to CHANGELOG `[Unreleased]`, before `### Changed`.
- [x] Run the three test files and `wf_validate_docs`, then, last, the full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Tests, tool and lint fix | implementer | readiness | One writer |
| Review | code-reviewer, qa-reviewer | fix | Fresh read-only contexts |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/change_doc_checklist.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_change_doc_checklist.py`

The root `CHANGELOG.md` is a documentation edit made by the same writer.

## Affected Architecture Docs

N/A: no boundary, flow or verification change. The tool and lint rule keep their roles; only where a note is written and read changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The observed defect |
| AC-2 | required | Single-line and blockquoted criteria must not change |
| AC-3 | required | Without it, the fix produces lint failures |
| AC-4 | required | Repairs the observed instance |
| AC-5 | required | Regression check; the full suite still runs last before close as a gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-10 | Planned from the misplaced AC-3 note in wave 23041. Cause read in `_mark_change_item_response` (deferral branch edits only `lines[index]`) and `_lint_ac_items` (returns first lines only). | `server_impl.py` `_mark_change_item_response`, `_mark_item_block_end`; `wave_validators.py` `_check_tilde_required_ac_has_inline_note`, `_lint_ac_items` |
| 2026-11-10 | Readiness review round 1: docs-contract and code approved; red-team approved with notes; QA blocked on the false CRLF claim, two unnamed existing tests that pin the old placement, a lint rule that could weaken, and a weak blockquote check. Revised: the new line carries the document's line ending; the two tests are named; the lint accepts only a `*Status:*` continuation line and keeps its first-line checks; `_mark_item_block_end` moves to `change_doc_checklist`; `matched_text` includes the new line; exact blockquote output and a lint check; the moved 23040 note gains the `Status:` prefix; test files and the 40-character constant named. | Readiness reports from this session |
| 2026-11-10 | Readiness round 2: QA, code, docs-contract and red-team approved; no blocking findings. Corrections and implementation commitments from their notes: (a) Scope is inaccurate on reasons containing `*`: on a multi-line criterion the tool's own lint check refuses such a reason (nothing is written, with the existing "lacks an inline status note" message); a test pins that refusal, and a clearer message is out of scope. (b) The Requirement 1 prefix is the blockquote marker including its following space (`> `), so AC-2's `>   *Status:` line is exact. (c) The lint walks the AC section lines with their indexes, using `CHECKLIST_ITEM_RE` then `_AC_LINE_RE` in the same order as `_lint_ac_items`, so the positional priority fallback stays aligned. (d) `block_end` is incremented after the insertion so `matched_text` includes the new line. (e) Re-deferring a deferred multi-line criterion adds a second `*Status:*` line, as today's first-line form duplicates; not changed. (f) A criterion on the last line of a file with no trailing newline is out of scope for the CRLF rule. (g) The seed 170 example passes lint through its first-line prose; its "same line" wording remains accurate for that form, and a `*Status:*` continuation line is an additional accepted form. | Readiness round-2 reports from this session |
| 2026-11-10 | Implemented. Tests written first; before the fix 5 tool tests failed (the three new multi-line, CRLF and blockquote cases and the two pinned wrapped-criterion tests), 2 lint tests failed (Status continuation line; parenthesised label) and 4 checklist tests errored (no shared helper). The block-end helper moved to `change_doc_checklist.item_block_end` (same rule; server copy removed); the deferral branch writes `<prefix>  *Status: <reason>*` after the item with the document's line ending and increments `block_end` so `matched_text` includes it; `_ac_items_with_status_line` walks the AC section with the same matches as `_lint_ac_items` and the rule accepts a `*Status:*` continuation line. After the fix: `test_change_doc_checklist.py` 58 OK, `test_docs_lint.py` 355 ok and `test_server_tools_lifecycle.py` 671 ok; both runs were refused only by the stray-change guard because another session was editing wave `230k8` at the same time. The 23040 AC-3 note moved; docs-lint passes. CHANGELOG `### Fixed` bullet added. `wf_reload_mcp` reloaded the server implementation. | Focused runs with `run_tests.py --file`; `wf_validate_docs` pass |
| 2026-11-10 | Delivery review: docs-contract, code and QA approved; red-team approved with notes. All four confirmed the readiness verdict after the 23040 note move. Repaired from the notes: a criterion whose continuation contains a closed fenced block now keeps the first-line reason form (the lint blanks fenced lines and would end the item at the fence, so the tool refused that deferral; a new test pins success); the asterisk test now uses a reason of 4 or more characters so it shows the asterisk causes the refusal. Accepted as is: a CRLF document ending on a multi-line criterion with no final newline (already out of scope), and a two-space Status indent under tab- or number-indented items (renders as a lazy continuation, per Risks). `MarkChangeItemRecoveryTests` 20 OK after the repair; `wf_reload_mcp` reloaded the server. | Delivery review reports from this session |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-10 | Write the note as a new `*Status: ...*` line after the item's block, and teach the lint rule to read the block. | Keeps the criterion's text intact; the "Status:" prefix separates the note from a trailing numbered line. | Append to the last continuation line: merges the note into the last numbered outcome; insert right after the label: still interrupts the criterion. |
| 2026-11-10 | Accept only a `*Status:*` continuation line in the lint rule, and share the continuation rule from `change_doc_checklist`. | Readiness review: reading the whole block would let a criterion's own italics or length satisfy the rule; a copy of the continuation rule in the lint could drift from the tool's. | Read the whole block: weakens the rule; copy the rule: drift. |
| 2026-11-10 | Leave seed 170's "on the same line" wording unchanged. | Its own example already places a note on a continuation line, and the lint rule is the enforced contract; a seed edit is outside this bug fix. | Edit seed 170 under the seed gate: more scope than the defect needs. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A rendered Markdown view joins the new line to the last numbered item as a lazy continuation, so a rendered page can read as if the reason belonged to that item | Accepted: only a blank line would separate it, and a blank line ends the item for every tool. The fix is correct in source, which the lint, close gate and reviewers read; the `Status:` prefix marks the line in both views |
| Loosening the lint rule so a criterion's own italics or length counts as a reason | Requirement 5 accepts only a `*Status:*` continuation line; AC-3 negative cases |
| Other readers of AC text assume single-line notes | Code review found none affected: `CHECKLIST_ITEM_RE` and `_AC_LINE_RE` do not match a `*` line, the close gate reads only marks, the dashboard folds continuation text into the item |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
