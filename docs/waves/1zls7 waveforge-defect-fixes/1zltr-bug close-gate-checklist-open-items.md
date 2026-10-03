# Close Gate Sees Every Open Checklist Item

Change ID: `1zltr-bug close-gate-checklist-open-items`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-02
Wave: 1zls7 waveforge-defect-fixes

## Rationale

The close-time hard gate (`lifecycle_gate_support._collect_silent_unchecked_items_for_close`) must refuse a wave while any acceptance criterion or task is still open. It reads change documents through the shared parser `change_doc_checklist` (`CHECKLIST_ITEM_RE`, `section_bodies`, `has_section`, `section_items`), and three shapes of open item pass it today (each reproduced by the collector returning `[]` for a document that plainly has open work):

1. **Blockquoted items.** `> - [ ] write the test` is not an item: `CHECKLIST_ITEM_RE` allows only spaces and tabs before the list marker.
2. **Unusual marks.** `- [-] step` or `- [/] step` is not an item at all: the mark class is `[ xX~]`, so any other single character makes the line plain text, and plain text is never open.
3. **Headings inside fenced code.** A `## ` line inside a fenced code block (a pasted shell transcript, a Markdown example) ends the section in `section_bodies`, so every item after the fence is outside `## Tasks` or `## Acceptance Criteria`.

Each is a way to close a wave with unfinished work and no signal. Waveforge reported the class; the parser is shared by close, Prepare (`lifecycle_gates.change_sections_gate`, through `lifecycle_gate_support._missing_required_change_sections`, `_noncanonical_checklist_items` and `_noncanonical_checklist_headings`) and docs-lint (`wave_lint_lib/wave_validators.py`), so the fix is made once, in the parser, and every consumer is checked against it.

Operator decision (2026-10-02): any single-character mark other than `x`, `X` or `~` counts as OPEN (it blocks close), and lint reports the unusual mark so the author fixes it. A leading blockquote prefix (one or more `>`, with optional spaces) is accepted. Fenced code (backtick and tilde fences) is set aside when reading sections.

## Requirements

1. **Blockquoted items are items.** `CHECKLIST_ITEM_RE` accepts an optional blockquote prefix before the list marker: any run of `>` characters, each optionally followed by spaces or tabs, after optional leading whitespace (`> - [ ] x`, `>> - [ ] x`, `> > - [x] x`, `  >- [ ] x`). The `marker`, `mark` and `text` groups are unchanged in meaning.
2. **Any single-character mark is an item, and only `x`, `X` and `~` close it.** The `mark` group accepts any single character other than `]`, `\r` and `\n`. `[]` (no character) and multi-character marks stay non-items, as today. The close gate treats an item as open unless its mark is `x`, `X` or `~` (today it skips every mark other than a space); an unusual mark is reported with its mark so the operator can see why (for example `[-]`). The existing `not-this-scope` AC exemption is unchanged.
3. **Fenced code is set aside.** A fenced code block opens on a line whose first non-blank characters (after an optional blockquote prefix, up to three spaces of indent) are three or more backticks or three or more tildes, and closes on the next line that carries a fence of the same character and at least the same length with nothing after it but whitespace (CommonMark). Inside a closed fence, a `## ` line is not a heading (for `section_bodies`, `has_section` and `near_miss_headings`) and a checklist line is not an item (for `section_items` and the close gate). **An unterminated fence is not a fence:** when no closing line exists, the opening line and everything after it are read as ordinary lines, so a stray fence can never hide headings or open items (fail closed). **A fence opened inside a blockquote ends at the first line that lacks that blockquote prefix** (red-team R7), so a quoted fence cannot run on into unquoted headings or items. The fence helper is exposed by `change_doc_checklist` for reuse (`1zltv` reuses it); `gardener_metadata._fenced_line_flags` already exists and is either reused as the basis or recorded in the census as a second reading.
4. **One reading of items for the close gate.** The close gate reads items through a parser function that applies Requirement 3 (for example a `checklist_items(body)` helper that `section_items` also uses) rather than calling `CHECKLIST_ITEM_RE.finditer` on a raw section body. The `_CLOSE_GATE_CHECKBOX_LINE_RE` alias stays importable (it is re-exported by `wf_server/server_impl.py` and pinned by `test_server_tools_lifecycle.py`) and remains `change_doc_checklist.CHECKLIST_ITEM_RE`. The close gate's `## AC Priority` read (`_extract_close_gate_section`) also sets fenced code aside.
4a. **Near-miss headings normalise case and whitespace (red-team R5).** `near_miss_headings` detects a near-miss `Acceptance Criteria` or `Tasks` heading regardless of case and of the amount of whitespace after the hashes or inside the title, and when the ATX heading is indented by up to three spaces (`##  Tasks`, `## Acceptance criteria`, `   ## Tasks`), so such a section is read and reported rather than silently skipped.
5. **Lint reports unusual marks.** docs-lint reports every item in an exact or near-miss `## Acceptance Criteria` or `## Tasks` section whose mark is not a space, `x`, `X` or `~`, naming the file, the section, the mark and the item text, and saying to use `[ ]`, `[x]` or `[~]`. It is a failure in the same class as `_check_checklist_list_markers` (a deterministic shape rule, not a heuristic sensor, so the advisory-first sensor rule does not apply). Prepare's `_noncanonical_checklist_items` lists the same items, so Prepare refuses them regardless of lint scope.
6. **Lint reads sections the same way.** The lint rules that count or classify AC and task items (`_check_checkbox_ac_syntax`, `_check_checkbox_task_syntax`, `_check_checklist_list_markers`, `_check_ac_priority_alignment` through `_parse_ac_items_for_lint`, and `_check_tilde_required_ac_has_inline_note`) read the two sections through `change_doc_checklist` so that a fenced `## ` line, a fenced example item, a blockquoted item and an unusual mark are read as the close gate reads them. Their messages and the documents they accept are otherwise unchanged; in particular a `- [-] step` task stops being reported as "plain bullet format" and is reported by the Requirement 5 rule instead.
7. **Consumer census.** The implementer records, in the Progress Log, every consumer of `change_doc_checklist` and of `_CLOSE_GATE_CHECKBOX_LINE_RE` (predicate: a non-test module under `.wavefoundry/framework/scripts/` that imports `change_doc_checklist` or names `_CLOSE_GATE_CHECKBOX_LINE_RE`), with what each reads and whether its behaviour changes. Known on 2026-10-02: `lifecycle_gate_support.py` (close gate, Prepare section helpers), `lifecycle_gates.py` (via those helpers), `wave_lint_lib/wave_validators.py` (lint), and `wf_server/server_impl.py` (`_wave_objective_unpopulated` reads `## Objective` of `wave.md` through `section_bodies`, so a fenced `## ` line inside an Objective stops ending it; the re-export of the close-gate names). The census also covers checklist readers that do not import `change_doc_checklist` (second predicate: a non-test module under `.wavefoundry/framework/scripts/` that matches checklist lines with its own pattern): `_mark_change_item_response` in `wf_server/server_impl.py` (around line 6942; matches only `\s*-\s*\[[ x~X]\]`, so `wf_mark_ac` and `wf_mark_task` cannot mark a blockquoted or unusual-mark item), the review-policy digest normaliser `gardener_metadata.normalize_checkbox_tracking` (`_CHECKBOX_LINE_RE`), and the `dashboard_lib.py` checklist parsers (`_TASK_ITEM_START_RE`, `_AC_ITEM_START_RE`, used by `_parse_tasks` and `_parse_ac_items`); for each, what it reads and whether it diverges from the shared parser.
7a. **The mark tools read through the shared parser.** `_mark_change_item_response` (behind `wf_mark_ac` and `wf_mark_task`) finds items through `change_doc_checklist` (the shared parser chosen at readiness), so a blockquoted item or an unusual-mark item that blocks close can be marked; marking rewrites only the mark character and keeps the item's blockquote prefix, list marker and text. Its section boundary follows the shared parser too.
7b. **The collector finds changes with lint's record parser.** `lifecycle_gate_support._collect_silent_unchecked_items_for_close` finds change ids through `wave_validators._parse_work_records` (the parser change `1zlu0` adopts for the status check) instead of the column-0 `_CHANGE_ID_PATTERN`, so an indented `Change ID:` block cannot escape the open-item gate (red-team R4). It keeps only records with `anchor_type == "change"`, since the parser falls back to legacy item records and those ids would otherwise come back as missing change documents. A test plants an indented change block with an open AC and asserts close refuses.
8. **Document census.** Before the code change lands, the implementer runs a census of existing change documents and records the predicate, the count and every hit in the Progress Log. Predicate: a change document under the live waves root, the plans root or the archive root whose exact or near-miss `## Acceptance Criteria` or `## Tasks` section contains (a) a blockquoted item, (b) an item with a mark other than space, `x`, `X` or `~`, or (c) a fenced block with a `## ` line inside it, or (d) an unterminated fence; and for each hit, whether it newly fails close (only relevant for an open wave), Prepare or lint under the new parser. Any live document that would newly fail is listed for the operator with the proposed one-line repair; archived and closed records are not edited (they are history), and the census states whether lint reaches them.

## Scope

**Problem statement:** three checklist shapes let a wave close with open work, because the shared parser does not see them as open items.

**In scope:**

- `change_doc_checklist.py`: the blockquote prefix, the open mark class, fence handling in `section_bodies`, `has_section`, `near_miss_headings` and item iteration, and the module docstring.
- `lifecycle_gate_support.py`: the close gate's open-item test, item iteration and `## AC Priority` read; `_noncanonical_checklist_items`.
- `wave_lint_lib/wave_validators.py`: the unusual-mark rule and the section reading in the rules named in Requirement 6.
- `wf_server/server_impl.py`: `_mark_change_item_response` reading items through the shared parser (Requirement 7a).
- Tests: `tests/test_change_doc_checklist.py` (parser cases), a close-gate test per shape that builds a wave with one admitted change document and asserts `_collect_silent_unchecked_items_for_close` reports the item, lint tests for the unusual-mark rule, and unchanged-behaviour tests for valid documents.
- The consumer and document censuses (Requirements 7 and 8).

**Out of scope:**

- Changing the canonical marks (`[ ]`, `[x]`, `[~]`) or the `[~]` inline-note rule.
- Indented code blocks (four-space indent) as fences; only backtick and tilde fences are set aside.
- Repairing archived or closed records.
- Other parsers of wave records that do not read change-document checklists (for example `_prepare_council_verdict_info`).

## Acceptance Criteria

- [x] AC-1: For each of four change documents, each with one open item and otherwise all items `[x]` (a blockquoted `> - [ ] x` task, a `- [-] x` task, a `- [/] AC-1: x` criterion at required priority, and a task listed after a fenced block containing a `## ` line), `_collect_silent_unchecked_items_for_close` returns exactly that item (the unusual-mark findings show the mark); each test fails against the parser as of 2026-10-02.
- [x] AC-2: A fenced example item (`- [ ] x` inside a closed fence in `## Tasks`) is not reported, and an unterminated fence hides nothing: a document whose `## Tasks` has an unclosed fence followed by `- [ ] x` reports that item, and `has_section` still finds a heading after the unclosed fence.
- [x] AC-3: docs-lint reports a `- [-]` task and a `- [/]` criterion with the Requirement 5 message (file, section, mark, text), no longer reports the `[-]` task as "plain bullet format", and Prepare's `_noncanonical_checklist_items` lists both.
- [x] AC-4: Valid documents behave as before: a document whose items are all `[ ]`, `[x]`, `[X]` or `[~]` with `-` markers and no fences produces the same close findings, Prepare result and lint output as before the change (pinned by the existing `test_change_doc_checklist.py` cases plus at least one new before/after comparison).
- [x] AC-5: The consumer census (Requirement 7) and the document census (Requirement 8) are recorded in the Progress Log with their predicates, counts and hits, and any live document that would newly fail is named for the operator.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-7: `wf_mark_ac` marks a blockquoted `> - [ ] AC-1: x` criterion and `wf_mark_task` marks a `- [-] x` task, each rewriting only the mark (prefix and text unchanged), after which the close gate no longer reports that item; a near-miss heading `##  Tasks`, `## Acceptance criteria` or one indented by up to three spaces is detected; and a fence opened inside a blockquote ends at the first unquoted line.

## Tasks

- [x] Run the document census (Requirement 8) against the tree before changing the parser; record predicate, count and hits.
- [x] Write the failing-first close-gate tests for the four shapes and the fence cases.
- [x] Extend `CHECKLIST_ITEM_RE` (blockquote prefix, open mark class) and add fence-aware section and item reading in `change_doc_checklist.py`.
- [x] Switch the close gate to the fence-aware item reader and the x/X/~ closed test; set fences aside in the `## AC Priority` read.
- [x] Add the lint unusual-mark rule; move the Requirement 6 lint rules onto the shared section and item reading; extend `_noncanonical_checklist_items`.
- [x] Record the consumer census (Requirement 7, both predicates) and update the module docstring.
- [x] Move `_mark_change_item_response` onto the shared parser (Requirement 7a); add near-miss heading normalisation (Requirement 4a) and the blockquote fence end (Requirement 3), with tests for AC-7.
- [x] Run the change's suites and docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| checklist-parser | implementer | none | change_doc_checklist.py, lifecycle_gate_support.py, wave_validators.py, server_impl.py (`_mark_change_item_response`) and their tests; lands before `1zltv` and `1zlu0` |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/change_doc_checklist.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/tests/test_change_doc_checklist.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`

## Affected Architecture Docs

N/A: the parser's contract tightens (more shapes are read as items, fences are respected) inside one module and its existing consumers; no boundary, flow or ownership change. The change-doc rules in `.wavefoundry/framework/seeds/170-plan-feature.prompt.md` already name only `[ ]`, `[x]` and `[~]` and need no edit.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The three bypasses are the defect. |
| AC-2 | required | Fence handling must not open a new way to hide items. |
| AC-3 | important | Authors need to see and fix unusual marks before close. |
| AC-4 | required | Valid documents must not change behaviour. |
| AC-5 | important | The parser is shared; consumers and existing documents must be known before it changes. |
| AC-6 | required | Standard verification. |
| AC-7 | required | An item that blocks close must be markable, and near-miss headings and quoted fences must not hide items. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Delivery-review repair. N2a: `test_column_zero_id_outside_the_lint_shape_is_still_checked` pins the column-0 id union in `_close_gate_change_ids` (a change id only `_CHANGE_ID_PATTERN` finds, with an open AC, is reported). N2b: `test_a_line_at_another_blockquote_depth_ends_the_item` pins the blockquote-depth stop in `_mark_item_block_end` (a deeper and a shallower quoted line each end the item). CRLF: `_mark_change_item_response` read the document with `read_text`, so marking rewrote every CRLF line ending; it now reads the bytes, finds items on the document's own lines and writes them back with only the mark (and an AC deferral's inline reason) changed, while the tilde check, the review-policy override and the publication compare use the universal-newline text every other reader sees; `_publish_prepare_policy_state` accepts an optional fourth element per change update, the text to write. A document with a lone carriage return keeps the old rewrite. Tests: `test_marking_a_crlf_document_changes_only_the_mark` (byte-for-byte except the mark, plain write) and `test_a_crlf_deferral_refreshes_the_receipt_and_keeps_line_endings` (receipt-publishing path). Failing-first: the CRLF plain-write test failed against the pre-repair tool (`scratchpad/1zls7-repair-others/failing-first-crlf.txt`); N2a and N2b pin existing code, so their evidence is the mutations. Mutations in a scratch copy (`scratchpad/1zls7-repair-mutations.txt`), 18 of 18 killed: column-0 id union removed, depth stop removed, plain write normalised, receipt write normalised. Follow-up (recorded, not fixed): the Requirement 8 document census predicate did not cover the `## AC Priority` join; three closed-wave documents in `1t3ek` change their failure count under the new reading, and closed records are not linted per change. Suites (scratch copy of the repaired tree, `scratchpad/1zls7-repair-suite-*.txt`): `run_tests.py --no-cache` 10722 tests across 156 files OK, 34 skipped; `--profile second` 10719 run, 0 of 156 files failed; `--profile declared` 10722 run, 0 of 156 files failed. | `scratchpad/1zls7-repair-*`, 2026-10-02 |
| 2026-10-02 | Implemented. Document census (Requirement 8), run BEFORE the parser change with an independent prototype scanner (`scratchpad/1zls7-1zltr-census.py`, sanity-checked on a planted file that hit all four shapes). Predicate: a change document (a `.md` other than `wave.md` carrying a `Change ID:` line) under the live waves root `docs/waves` (recursive, so closed waves are included) or the plans root `docs/plans`; no archive root is configured (`record_paths.ARCHIVE_ROOT` is None); hit when an exact or near-miss `## Acceptance Criteria` or `## Tasks` section holds (a) a blockquoted item, (b) a single-character mark other than space, x, X or ~, (c) a fence with a `## ` line inside, or (d) an unterminated fence. Result: 1048 change documents scanned, 0 hits, so no live document newly fails close, Prepare or lint and nothing goes to the operator. Lint's per-change rules reach only change documents of ready, active or implementing waves (closed records are not linted per change). Code: `change_doc_checklist.py` gains the blockquote prefix and open mark class in `CHECKLIST_ITEM_RE`, `CLOSED_MARKS`, `is_open_mark`, `is_canonical_mark`, `split_blockquote`, `fenced_line_flags` (CommonMark fences, unterminated is not a fence, a quoted fence is unterminated when an unquoted line comes first), `unfenced_text`, `checklist_items`, `section_text`, `section_line_indexes`, fence-aware `section_bodies`, `has_section` and `near_miss_headings`, and near-miss detection by casefolded, whitespace-collapsed title with up to three spaces of ATX indent (a heading line now also ends a section when indented up to three spaces or written with a tab). `lifecycle_gate_support.py`: the close gate reads items through `checklist_items`, treats every mark but x, X and ~ as open and shows an unusual mark in `item_text` (`[-] step`); `_extract_close_gate_section` reads through the shared parser with fences blanked; `_close_gate_change_ids` takes change records from `wave_validators._parse_work_records` (anchor `change` only) and keeps column-0 `_CHANGE_ID_PATTERN` ids the lint parser does not accept, so no id read before is dropped (deviation note: a union rather than a pure replacement, to stay fail-closed for ids outside the lint shape); `_noncanonical_checklist_items` also lists unusual marks. `wave_validators.py`: `_check_checklist_list_markers` reports an unusual mark (file, section, mark, text, `use [ ], [x] or [~]`); the AC and task syntax, priority alignment and tilde-note rules read the sections through `section_text` and a shared `_lint_ac_items` reading. `server_impl.py`: `_mark_change_item_response` finds items and section bounds through the shared parser (near-miss sections included) and rewrites only the mark character; new `_mark_item_block_end` folds continuation lines at the item's blockquote depth. Consumer census (Requirement 7). Predicate 1, a non-test module under `.wavefoundry/framework/scripts/` that imports `change_doc_checklist` or names `_CLOSE_GATE_CHECKBOX_LINE_RE`: 3 modules. `lifecycle_gate_support.py` (close gate, `_missing_required_change_sections`, `_noncanonical_checklist_headings`, `_noncanonical_checklist_items`; behaviour changes as above); `wave_lint_lib/wave_validators.py` (five lint rules; changes as above); `wf_server/server_impl.py` (`_wave_objective_unpopulated` reads `## Objective` through `section_bodies`, so a fenced `## ` line no longer ends it and an indented H2 now does; the re-exports of `_CLOSE_GATE_CHECKBOX_LINE_RE` and `_extract_close_gate_section` are unchanged; `_mark_change_item_response` now a consumer). `lifecycle_gates.py` reaches the parser only through the `lifecycle_gate_support` helpers. Predicate 2, a non-test module matching checklist lines with its own pattern: `gardener_metadata.normalize_checkbox_tracking` (`_CHECKBOX_LINE_RE`, `-` marker and the four canonical marks only, no blockquote: diverges, so marking a blockquoted or unusual-mark item moves the review-policy digest; follow-up), `dashboard_lib.py` `_TASK_ITEM_START_RE` and `_AC_ITEM_START_RE` (display only, `-` marker and canonical marks: diverges, follow-up), `install_log_lib.py` (install-log checklists, not change documents: outside the predicate's subject). `gardener_metadata._fenced_line_flags` is recorded as a second fence reading (it honours unterminated fences, the fail-open reading), not reused. Tests: `test_change_doc_checklist.py` (`BlockquoteAndMarkTests`, `FenceTests`, `NearMissHeadingTests`, `CloseGateShapeTests`, `LintAndPrepareMarkTests`; the old `- [?]` non-item case moved to the item side), `test_server_tools_lifecycle.py` `MarkChangeItemRecoveryTests` (three new). AC map: AC-1 the four `CloseGateShapeTests` shape tests; AC-2 `test_fenced_example_item_is_not_reported`, `test_unterminated_fence_hides_nothing`, `FenceTests.test_unterminated_fence_hides_no_heading_or_item`; AC-3 `test_unusual_marks_are_reported_by_lint_and_prepare`; AC-4 `test_valid_document_findings_are_unchanged`, `test_valid_document_lints_clean` (passes before and after) plus the existing parser cases; AC-7 `test_blockquoted_and_unusual_mark_items_are_markable`, `test_quoted_wrapped_criterion_marks_by_its_logical_label_with_reason`, `NearMissHeadingTests`, `test_quoted_fence_does_not_run_on`. Failing-first against the HEAD parser, gate, lint and server (`scratchpad/1zls7-1zltr-failing-first.txt`): 42 of 46 parser, gate and lint tests failed or errored, and 2 of the 3 new mark tests failed (`test_mark_reads_near_miss_sections` passed before, since the old mark pattern accepted `##  Tasks`). Mutations (`scratchpad/1zls7-mutations-mine.txt`), all killed: no blockquote prefix (`test_blockquoted_task_is_open` and 4 more), only space open (`test_dash_mark_task_is_open_and_shows_its_mark`), unterminated fence honoured (`test_unterminated_fence_hides_nothing` and 6 more), column-0 ids only (`test_indented_change_block_cannot_escape`), quoted fence runs on (`test_quoted_fence_does_not_run_on`), old dash-only mark pattern (`test_blockquoted_and_unusual_mark_items_are_markable`). Gapfill: shell grep listed the lint rule callers and `item_text` renderers in one sweep; `code_keyword` queries would have answered it. Suites (scratch copy of the whole wave tree, `run_tests.py --no-cache`): 10689 tests across 156 files OK, 34 skipped; `--profile declared` 10689 OK; `--profile second` 10686 run with one failure, `test_blockquoted_and_unusual_mark_items_are_markable`, whose fixture wrote an unlocalized `Wave ID:` line that the second profile reads as a member id; the fixture now goes through `_loc` and `--profile second --file test_server_tools_lifecycle.py` passes. An earlier full run caught a decorator displaced onto the inserted `_mark_item_block_end` helper (wf_mark layout refusals) and vocabulary and literal census hits; all fixed before the counted run. | `scratchpad/1zls7-1zltr-*`, 2026-10-02 |
| 2026-10-02 | Planned from the Waveforge report and the operator's decisions (unusual marks are open and reported by lint; a blockquote prefix is accepted; fenced code is set aside). Symbols verified against the tree: `CHECKLIST_ITEM_RE`, `section_bodies`, `has_section`, `near_miss_headings`, `section_items` in `change_doc_checklist.py`; `_CLOSE_GATE_CHECKBOX_LINE_RE`, `_collect_silent_unchecked_items_for_close`, `_extract_close_gate_section`, `_noncanonical_checklist_items` in `lifecycle_gate_support.py`; `change_sections_gate` in `lifecycle_gates.py`; the five lint rules named in Requirement 6; `_wave_objective_unpopulated` in `server_impl.py`. Observed: `_check_checkbox_task_syntax` already fails a `- [-]` task as "plain bullet format", while the AC rule only fails a section with no checkbox at all. | Planning read, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Requirement 7b: the close checklist collector reads change ids through `_parse_work_records` | Recheck correction: adopting the lint parser only for the status check (1zlu0) left an indented change block escaping the open-item gate | Keep the column-0 `_CHANGE_ID_PATTERN` |
| 2026-10-02 | Any single-character mark other than x, X or ~ is open and blocks close | Operator decision: an unknown mark must never read as done | Treat unusual marks as non-items (today's behaviour, the defect) |
| 2026-10-02 | Lint reports unusual marks as a failure, and Prepare lists them with the non-canonical items | Operator asked that lint report them so authors fix them; a deterministic shape rule is the class of `_check_checklist_list_markers`, not an advisory-first heuristic sensor | An advisory warning only |
| 2026-10-02 | Items inside a closed fence are not items; an unterminated fence is not a fence | A fenced example is not work, but a stray fence must never hide headings or open items | Count fenced items too (examples would block close); honour unterminated fences (CommonMark, but fails open) |
| 2026-10-02 | Readiness amendments: the Requirement 7 census adds readers outside `change_doc_checklist` importers (`_mark_change_item_response`, `gardener_metadata.normalize_checkbox_tracking`, the `dashboard_lib.py` checklist parsers); `wf_mark_ac` and `wf_mark_task` read through the shared parser (Requirement 7a, the shared parser chosen over having lint and Prepare report blockquoted items) so every item that blocks close can be marked; near-miss heading detection normalises case, whitespace and up to three spaces of ATX indent (red-team R5, Requirement 4a); a line without the fence's blockquote prefix ends the fence (R7); the fence helper is exposed for `1zltv`; AC-7 added. Red-team R6: multi-character marks such as `[  ]` or `[ x]` stay non-items by intent (plain text, as today), not open items | Readiness review: the mark tools could not mark items the close gate now blocks on, and heading and fence edge cases could still hide items | Lint and Prepare report blockquoted items instead of the tools reading them (rejected by the readiness choice); treat multi-character marks as open items (rejected: Requirement 2 keeps single-character marks only) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| An existing live change document newly fails close, Prepare or lint | The Requirement 8 census runs first and names every such document with a one-line repair for the operator |
| A fenced example in a live document is newly read differently by lint | Requirement 6 makes lint read as close reads; AC-4 pins valid documents unchanged |
| CRLF documents | The parser already treats a trailing carriage return as whitespace; the new fence and blockquote patterns must do the same, with a CRLF case in the tests. Behaviour is identical on Windows, macOS, Linux and WSL2 (pure text parsing, no filesystem or process differences) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
