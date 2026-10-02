# The Close Checkbox Gate Reads Every Checklist Item, Requires Both Sections and Takes the AC Id From the Start

Change ID: `1zimq-bug close-gate-checkbox-bypasses`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zime downstream-gap-fixes

## Rationale

The close-time hard gate (wave 1p31b, change 1p32k) requires every AC and every task of every admitted change to be `[x]` or `[~]` before `wf_close_wave` succeeds. `close_checkbox_gate` (`lifecycle_gates.py`) calls `_collect_silent_unchecked_items_for_close` (`lifecycle_gate_support.py`), which extracts `## Acceptance Criteria` and `## Tasks` with `_extract_close_gate_section`, matches items with `_CLOSE_GATE_CHECKBOX_LINE_RE` and resolves an AC's priority through the id that `_CLOSE_GATE_AC_ID_RE.search` finds. A downstream distribution reported three ways an open item passes. Each was reproduced on the current tree by calling the helper on a fixture change doc, together with the docs-lint checks close also runs (`_check_ac_priority_alignment`, `_check_checkbox_ac_syntax`, `_check_checkbox_task_syntax`, `_CHANGE_DOC_REQUIRED_SECTIONS`) and Prepare's `_missing_required_change_sections`:

- **List markers.** The regex accepts only `-` bullets. `* [ ] step`, `+ [ ] step`, `1. [ ] step` and `1) [ ] step` in `## Tasks` pass close and pass lint (the task syntax rule only inspects lines starting with `- `). The same markers in `## Acceptance Criteria` pass close; lint catches them only indirectly, when the AC Priority table keeps a row for the item and the row count no longer matches the `-` bullet count. Delete the row as well and nothing catches it.
- **Missing or misspelled headings.** The extractor needs a line that is exactly `## <heading>` plus whitespace; anything else yields an empty section, which passes. Three layers check headings, and each checks less than close needs. Prepare's `change_sections_gate` blocks on a missing `## Tasks` or `## Acceptance Criteria`, but by substring (`hdr not in change_text`) and only at Prepare, so a heading removed or renamed after readiness is not seen again. Lint's `_CHANGE_DOC_REQUIRED_SECTIONS` covers `## Acceptance Criteria` but not `## Tasks`, also by substring. So `## Tasks (remaining)` and `## Acceptance Criteria (revised)` pass Prepare, lint and close with every item open (verified), and `## Task` or a deleted `## Tasks` added after readiness passes close and lint. The coordinator's note that lint already catches a missing AC heading holds only for a heading that no longer contains the substring.
- **AC id anywhere in the item.** `_CLOSE_GATE_AC_ID_RE.search` takes the first `AC-...` token anywhere in the item text. `- [ ] Covers the remainder; see AC-2` with `AC-2` at `not-this-scope` is exempted and passes close and lint (verified).

The census found a fourth hole of the same kind that the report does not name. The extractor returns only the FIRST section with a heading. A change doc with two `## Tasks` (or two `## Acceptance Criteria`) sections has its second section ignored. Three closed change docs in wave `1t3ek` carry duplicated sections today.

**Census of consumers (predicate: code that parses checklist items, AC ids or the `## Acceptance Criteria` / `## Tasks` sections of a change doc, found by searching the framework scripts for the checkbox character class `[ xX~]`, the AC id pattern `AC-[\w\-]+`, and the two heading names, excluding tests):**

| Consumer | Markers | AC id | Sections | Role | Shares a bypass |
| --- | --- | --- | --- | --- | --- |
| `_collect_silent_unchecked_items_for_close` (`lifecycle_gate_support.py`) | `-` only | search anywhere | first exact heading only | close hard gate | all four (fixed here) |
| `_missing_required_change_sections` (`lifecycle_gate_support.py`), Prepare's `change_sections_gate` | n/a | n/a | substring, six headings | Prepare gate | heading substring (fixed here for the two headings close reads) |
| `wave_validators._check_checkbox_task_syntax`, `_check_checkbox_ac_syntax`, `_check_ac_priority_alignment` (docs-lint, run by Prepare, review and close) | `-` only | search anywhere (`_parse_ac_items_for_lint`) | exact heading, last duplicate wins | lint | markers and id (fixed here); duplicates and headings are left to the close gate |
| `wave_validators._check_tilde_required_ac_has_inline_note` (`[~]` without a note) | `-` only | search anywhere | exact heading | lint | a `* [~]` required AC skips the note rule; an id cited later can borrow another AC's priority (fixed here through the shared parser) |
| `wave_validators._CHANGE_DOC_REQUIRED_SECTIONS` | n/a | n/a | substring; no `## Tasks` | lint | left as is: the close gate now owns the exact-heading check |
| `_mark_change_item_response` (`wf_mark_ac`, `wf_mark_task`) | `-` only | label prefix (`AC-1:`) | exact heading | writer | cannot mark a non-dash item; consistent once lint requires `-` (Requirement 5) |
| `gardener_metadata.normalize_checkbox_tracking` (review-policy digest) | `-` only | n/a | exact heading, fence-aware | receipt digest | none once lint requires `-`; changing it would move receipt digests, so it is left alone |
| `dashboard_lib` (`_TASK_ITEM_START_RE`, `_AC_ITEM_START_RE`, `_AC_ID_RE`, `_extract_section`) | tasks `-`; ACs `-` and `N.` | search anywhere | first exact heading | display | display only, never a gate; out of scope |
| `_generate_wf_close_wave_summary` (`server_impl.py`) | `-` only | n/a | substring `find` | close summary prose | display only; out of scope |
| `render_platform_surfaces._ac_progress` (rendered status line) | `- [ ] AC` prefix | n/a | whole file | display | display only; out of scope |

**Counts from the existing change docs** (1,033 documents carrying a `Change ID:` line under `docs/waves/*/` and `docs/plans/`: 1,009 in closed waves, 11 in open waves, 13 staged plans):

- Checklist items in `## Acceptance Criteria` or `## Tasks` using `*`, `+` or an ordered marker: 0.
- Documents without an exact `## Tasks` heading: 2, both in closed waves (`12awg mcp-tool-cleanup/12ayn-maint wave-close-operator-gate.md`, `12mns code-ask-retrieval-quality/12n0e-enh two-hop-symbol-expansion.md`). Neither has a near-miss heading; both predate the Prepare section check. Documents without an exact `## Acceptance Criteria` heading: 0. Near-miss headings (`## Task`, a suffixed heading, an H3): 0.
- Documents whose `## Tasks` section holds no checklist item: 138, all in closed waves. An empty Tasks section is legitimate.
- Documents with a duplicated `## Tasks` and `## Acceptance Criteria`: 3, all in closed wave `1t3ek`.
- AC checklist items (dash form): 5,622 start with `AC-<id>`; 10 start with `**AC-<id>**` (closed wave `1p75h`); 16 carry no AC id at all (14 closed, 2 in a staged plan); 0 cite an AC id later in the text without one at the start. Taking the id from the start therefore changes the outcome for no existing document.

## Requirements

1. **One shared checklist parser.** A new stdlib-only module `change_doc_checklist.py` owns three things used by every gate and lint rule this change touches:
   - an item pattern that accepts any CommonMark list marker (`-`, `*`, `+`, or one to nine digits followed by `.` or `)`), any indentation, a checkbox mark (` `, `x`, `X`, `~`), and the item text;
   - an AC id function that returns the id only when the item text STARTS with it, optionally wrapped in `**` or a backtick (`AC-1: ...`, `AC-1 (required): ...`, `**AC-1**: ...`, `` `AC-1` ... ``), using the id character class the AC Priority table parser already uses (`AC-[\w\-]+`); otherwise it returns no id;
   - a section function that returns the bodies of EVERY H2 section whose heading line is exactly `## <heading>` (trailing whitespace allowed), each running to the next `## ` line, and reports when there is none.

   `lifecycle_gate_support` and `wave_lint_lib.wave_validators` import it. `_CLOSE_GATE_CHECKBOX_LINE_RE` is rebound in `lifecycle_gate_support` (and through `server_impl`'s binding block) to the shared any-marker pattern, and `_CLOSE_GATE_AC_ID_RE` stays bound unchanged, so no existing name lookup breaks. Text only; LF and CRLF documents parse identically on Windows, macOS, Linux and WSL2, which matters because a Windows checkout with `core.autocrlf` delivers CRLF. `change_doc_checklist` is added to the module purge set in `wf_server/server_impl.py`, beside `gardener_metadata` and `review_evidence`, so `wf_reload_mcp` re-imports the parser together with the gate and lint modules that use it. `_CLOSE_GATE_AC_ID_RE` keeps its unanchored pattern for `_close_gate_parse_ac_priority`; the leading-id rule is the shared function, not a rebinding of that pattern (census: all 6,913 AC Priority first cells start with the id, so either reading leaves outcomes unchanged).
2. **Close reads every item.** `_collect_silent_unchecked_items_for_close` uses the shared item pattern, so an open item under any list marker blocks close exactly as a `-` item does. It reads every `## Acceptance Criteria` and every `## Tasks` section of the document, not only the first. Fenced content is treated as today (not excluded). Same behaviour on all four platforms.
3. **Close requires both sections.** An admitted change document with no exact `## Acceptance Criteria` heading or no exact `## Tasks` heading blocks close. A misspelled, suffixed or demoted heading counts as missing. The section may be empty: a change with no tasks keeps an empty `## Tasks` section, as the `wf_new_*` scaffold and seed 170's required-sections list already provide. The finding is a `change document` item that `close_checkbox_gate` renders as a `change_doc_missing_sections` diagnostic (the code Prepare already uses for the same condition), naming the change id and each missing heading, with `recovery_tools=["wf_get_change"]` and `recovery_usage` `wf_get_change(change_id=...)`. It is not counted among the unchecked items. Same behaviour on all four platforms.
4. **The AC id comes from the start of the item.** Close resolves an AC's priority only through the shared AC id function. An item with no leading id is `<unidentified>`, has priority `unknown`, and blocks close while unchecked, as today. An id cited later in the text never exempts the item. The AC Priority table parser (`_close_gate_parse_ac_priority`) is unchanged. Same behaviour on all four platforms.
5. **Lint names the canonical form.** Docs-lint fails, for a change doc in a ready, active or implementing wave (the scope its AC validators already have), any checklist item in `## Acceptance Criteria` or `## Tasks` whose list marker is not `-`, naming the item and the canonical `- [ ] ...` form. This keeps `wf_mark_ac`, `wf_mark_task`, the review-policy digest normaliser and the dashboard, which all read `-` items only, consistent with what the gate counts. Docs-lint's per-change rules run only for a ready, active or implementing wave, and a readied wave keeps `Status: planned`, so lint alone would first report a non-dash item during implementation. Prepare's `change_sections_gate` therefore also refuses, for every admitted change and regardless of wave status, any checklist item in `## Acceptance Criteria` or `## Tasks` whose marker is not `-`, as a blocking `change_doc_noncanonical_checklist` diagnostic naming the change, the item and the `- [ ] ...` form, with `recovery_tools=["wf_get_change"]`. The lint rule reads the two sections through the shared section function, so CRLF documents are checked as LF ones are. `_parse_ac_items_for_lint` and `_check_tilde_required_ac_has_inline_note` take an item's AC id from the shared function; positional fallback is unchanged. Same behaviour on all four platforms.
6. **Prepare checks the two headings exactly.** `_missing_required_change_sections` checks `## Acceptance Criteria` and `## Tasks` through the shared section function (exact heading line) instead of by substring, so a heading that close would refuse is refused at Prepare first. The other four required headings keep their substring check. Same behaviour on all four platforms.
7. **No other outcome changes.** A change doc that uses `-` items, exact headings and leading AC ids gets the same close, Prepare and lint result as today. The lifecycle golden fixture is unchanged.
8. **Docs.** `docs/specs/mcp-tool-surface.md`'s `wf_close_wave` section gains a bullet stating what the hard gate reads (every list marker, every section with the exact heading, the leading AC id, both headings required and possibly empty). CHANGELOG `## [Unreleased]` gains a `### Fixed` bullet. The rendered close prompt's wording ("every AC and every task") stays accurate, so no seed changes.

## Scope

**Problem statement:** the close-time hard gate lets an open AC or task through when it uses a list marker other than `-`, when its section heading is missing, misspelled or duplicated, or when the AC cites a not-this-scope AC later in its text.

**In scope:**

- `change_doc_checklist.py` (new); `lifecycle_gate_support.py` (`_collect_silent_unchecked_items_for_close`, `_missing_required_change_sections`, the two bound patterns); `lifecycle_gates.py` (`close_checkbox_gate` renders the missing-section finding; `change_sections_gate` refuses non-dash checklist items); `wf_server/server_impl.py` (reload purge set only); `wave_lint_lib/wave_validators.py` (marker rule, AC id at two sites).
- Close-path fixture documents in `test_server_tools_lifecycle.py` and `test_memory_records.py` gain the two empty headings (AC-8).
- Tests: a unit module for the parser; close cases in `test_server_tools_lifecycle.py`; lint cases in `test_docs_lint.py`; the Prepare heading case.
- The spec bullet.
- CHANGELOG bullet.

**Out of scope:**

- The dashboard, the close summary generator and the rendered status line: they display, they never gate.
- `wf_mark_ac` and `wf_mark_task` accepting non-dash items, and the digest normaliser: lint now keeps documents in the form they read.
- Excluding fenced lines from the gate (today a fenced `- [ ]` example counts as an open item, which over-blocks, never under-blocks).
- The four other Prepare section checks and lint's `_CHANGE_DOC_REQUIRED_SECTIONS`.
- Closed waves: close only evaluates the wave being closed, and no closed record is edited.
- Fence-aware section boundaries: a `## ` line inside a fenced block ends the section (and a fenced `## Tasks` line satisfies the heading check); no current document has a fenced H2.

## Acceptance Criteria

- [x] AC-1: through `wf_close_wave(mode='dry_run')` on a fixture wave whose only open item is a task written as `* [ ] step`, `+ [ ] step`, `1. [ ] step` or `1) [ ] step` (one fixture each), and one whose only open item is `* [ ] AC-1: ...` at required priority with its AC Priority row removed, the response carries `silent_unchecked_items_at_close` naming the item. Each assertion fails on the current tree. The same fixture with the item marked `[x]` carries no such diagnostic.
- [x] AC-2: a fixture change doc without a `## Tasks` heading, and one whose heading reads `## Task`, each make `wf_close_wave(mode='dry_run')` return `change_doc_missing_sections` naming the change and `## Tasks`, with `wf_get_change` recovery; the same holds for `## Acceptance Criteria (revised)` naming `## Acceptance Criteria`. Each fails on the current tree. A change doc with an empty `## Tasks` section and every AC checked carries neither diagnostic.
- [x] AC-3: a fixture whose open item reads `- [ ] Covers the remainder; see AC-2`, with `AC-2` at `not-this-scope`, blocks close as an `<unidentified>` AC; it fails on the current tree. Unit tests of the AC id function return the id for `AC-1: x`, `AC-1 (required): x`, `**AC-1**: x` and `` `AC-1` x ``, and no id for `Covers AC-1`.
- [x] AC-4: a fixture with a second `## Tasks` section holding `- [ ] step` blocks close; it fails on the current tree.
- [x] AC-5: each fixture in AC-1 to AC-4 saved with CRLF line endings gives the same close result as its LF form.
- [x] AC-6: docs-lint fails a ready-wave change doc with a `* [ ]` task and one with a `1. [ ]` AC, each message naming the `- [ ]` form; it fails on the current tree for the task case. A `[~]` AC at positional priority required whose text is `Deferred; see AC-2` with no note, where `AC-2` is at `not-this-scope`, is reported by the tilde-note rule; this case fails on the current tree.
- [x] AC-7: `wf_prepare_wave(mode='dry_run')` on a fixture whose Tasks heading reads `## Tasks (remaining)` returns `change_doc_missing_sections` naming `## Tasks`; it fails on the current tree. A fixture whose only mention of `## Tasks` is an inline code span in prose is refused the same way.
- [x] AC-8: no outcome changes for canonical documents: the lifecycle golden test passes without regeneration, and the existing Prepare and lint tests pass unchanged. Existing close-path tests whose admitted-document fixtures carry neither `## Acceptance Criteria` nor `## Tasks` (`_write_admitted_docs` and the secrets-gate and summary fixtures in `test_server_tools_lifecycle.py`, and the close fixture in `test_memory_records.py`; 31 tests at planning) are updated only by adding the two empty headings to the fixture document, and each keeps its original assertions; the Progress Log lists every fixture so changed.
- [x] AC-9: the spec bullet and the CHANGELOG `### Fixed` bullet state the gate's reading rules and the lint rule.
- [x] AC-10: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-11: `wf_prepare_wave(mode='dry_run')` on a `planned` fixture wave whose admitted change has a `* [ ] step` task returns `change_doc_noncanonical_checklist` naming the change and the `- [ ] ...` form; it fails on the current tree. The same fixture with `- [ ] step` carries no such diagnostic.

## Tasks

- [x] Add `change_doc_checklist.py` (item pattern, leading AC id, all-sections extractor) with unit tests, including CRLF.
- [x] Switch `_collect_silent_unchecked_items_for_close` to the shared parser; add the missing-section finding; rebind `_CLOSE_GATE_CHECKBOX_LINE_RE` to the shared any-marker pattern; leave `_CLOSE_GATE_AC_ID_RE` unanchored for `_close_gate_parse_ac_priority`.
- [x] Render the missing-section finding in `close_checkbox_gate` as `change_doc_missing_sections`.
- [x] Switch `_missing_required_change_sections` to the exact-heading check for the two headings.
- [x] Add the `change_doc_noncanonical_checklist` refusal to `change_sections_gate` through the shared parser.
- [x] Add the two empty headings to the close-path fixture documents named in AC-8 and list each in the Progress Log.
- [x] Add the lint marker rule and route the two lint AC id sites through the shared function.
- [x] Close, Prepare and lint fixtures for AC-1 to AC-7 and AC-11, each run red on the current tree first and the red result recorded in the Progress Log.
- [x] Add `change_doc_checklist` to the server_impl reload purge set; confirm `build_pack.py` ships the module and that after an edit to it `wf_reload_mcp` serves the edited parser.
- [x] Spec and CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Shared parser | implementer | readiness | new module and unit tests |
| Close and Prepare gates | implementer | shared parser | lifecycle_gate_support, lifecycle_gates; coordinate with 1ziml |
| Lint rule | implementer | shared parser | wave_validators |
| Red-first fixtures | implementer | none | write and run against the current tree before the gate edits |
| Review | code-reviewer, qa-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/change_doc_checklist.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`, `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/tests/test_change_doc_checklist.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`, `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A. The change tightens one gate's parsing and one lint rule inside the existing lifecycle and docs-lint modules; no boundary, flow or ownership changes, and the gate contract is documented in `docs/specs/mcp-tool-surface.md`, which is updated.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reported list-marker bypass |
| AC-2 | required | The reported missing or misspelled heading bypass |
| AC-3 | required | The reported AC id bypass |
| AC-4 | important | Same class of bypass, found by the census |
| AC-5 | important | Windows checkouts deliver CRLF |
| AC-6 | required | Keeps the writers and the digest consistent with what the gate counts |
| AC-7 | important | Refuses at Prepare what close would refuse later |
| AC-8 | required | Canonical documents keep their outcome |
| AC-9 | required | Distributions read the documented gate contract |
| AC-10 | required | Standard verification |
| AC-11 | required | Surfaces a non-dash item before readiness approvals bind |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Delivery-review repair round. Near-miss headings: `change_doc_checklist.near_miss_headings` names an H2 that starts with `## Tasks` or `## Acceptance Criteria` but is not exact; close reads its items (`section_bodies(..., include_near_miss=True)`), Prepare's `change_sections_gate` refuses it under `change_doc_noncanonical_checklist`, and lint fails it, so an empty exact `## Tasks` beside `## Tasks (remaining)` with an open item no longer passes (tests: `test_near_miss_section_beside_an_exact_empty_heading_blocks_close`, `test_prepare_refuses_a_near_miss_checklist_heading`, `test_near_miss_checklist_heading_fails`; census: no document under `docs/` has a near-miss heading). Added the AC case of the Prepare non-dash refusal (B5) and a direct `_parse_ac_items_for_lint` leading-id assertion (B8). Mutants killed: B5, B8, N1 to N4. Census re-derived with the shared parser: five closed change documents would now fail close if their wave were reopened: `12ayn` and `12n0e` (no `## Tasks`), and `1t2zq`, `1t3el` and `1t3s7` (a second `## Tasks` section holding open placeholder items). Close evaluates only the wave being closed, so nothing breaks today | `change_doc_checklist.py`, `lifecycle_gate_support.py`, `lifecycle_gates.py`, `wave_lint_lib/wave_validators.py`, `tests/test_server_tools_lifecycle.py`, `tests/test_docs_lint.py`, scratch mutation run |
| 2026-10-01 | Implemented. New `change_doc_checklist.py` (`CHECKLIST_ITEM_RE` with groups `marker`, `mark`, `text`; `leading_ac_id`; `section_bodies`, `has_section`, `section_items`). `_CLOSE_GATE_CHECKBOX_LINE_RE` is rebound to the shared pattern; `_CLOSE_GATE_AC_ID_RE` is unchanged. The close helper reads every exact-heading section and records a `missing_sections` finding that `close_checkbox_gate` renders as `change_doc_missing_sections`; `_missing_required_change_sections` checks the two headings exactly; `change_sections_gate` adds `change_doc_noncanonical_checklist`; docs-lint gains `_check_checklist_list_markers` and both lint AC id sites use `leading_ac_id`; `change_doc_checklist` is in the reload purge set and `build_pack.collect_files` ships it. Red first on the original tree: 26 failures and 1 error across the close, Prepare, lint and parser tests. The lifecycle golden passed without regeneration with only this change applied. Fixtures given the two empty headings (28 tests, 4 sites): `_write_admitted_docs` in `OperatorSignoffTests` (2 tests), the fixture in `WaveLifecycleMutationTests.test_wf_close_wave_create_succeeds_when_requirements_met` (1), the setUp fixture of `WaveCloseSecretsGateTests` (18), and `test_memory_records.MemoryAgentValidationTests.test_close_diagnostics_require_candidate_and_verdict_but_allow_zero_memory` (1); `_make_closeable_wave` in `WaveCloseSummaryGenerationTests` (6 tests) already had `## Acceptance Criteria` and gained only `## Tasks`. Each keeps its original assertions | `change_doc_checklist.py`, `lifecycle_gate_support.py`, `lifecycle_gates.py`, `wave_lint_lib/wave_validators.py`, `wf_server/server_impl.py`, `tests/test_change_doc_checklist.py`, `tests/test_server_tools_lifecycle.py` (`CloseGateChecklistBypassTests`), `tests/test_docs_lint.py`, `tests/test_memory_records.py` |
| 2026-10-01 | Planned from the downstream report. Reproduced by calling the close helper, the lint checks close runs and Prepare's section check on fixture docs: `*`, `+` and `1.` tasks pass all three; `*` and `1.` ACs pass close and are caught by lint only through the AC Priority row count; `## Tasks (remaining)` and `## Acceptance Criteria (revised)` pass all three with every item open; a missing or `## Task` heading passes close and lint and is caught only at Prepare; a cited not-this-scope AC passes close and lint. Census of consumers and counts recorded in the Rationale. Found that Prepare's `change_sections_gate` already requires `## Tasks` (by substring) and that the extractor ignores duplicated sections | scratch probes against `lifecycle_gate_support.py`, `wave_lint_lib/wave_validators.py`; census of `docs/waves/` and `docs/plans/` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Require both headings at close; allow an empty `## Tasks` section | Seed 170 lists `## Tasks` as required, the `wf_new_*` scaffold writes it, and Prepare already refuses a document without it; 138 closed changes have an empty Tasks section, which is legitimate; the two closed documents without the heading predate the Prepare check and are never closed again | Refuse only a near-miss heading (misses a deleted heading); require at least one task (refuses legitimate changes) |
| 2026-10-01 | Treat a misspelled, suffixed or demoted heading as missing rather than detecting near-misses | An exact-heading check catches every variant with one rule; a near-miss detector needs a fuzzy list and still misses unforeseen spellings | Edit-distance or prefix matching on headings |
| 2026-10-01 | Take the AC id only from the start, allowing a `**` or backtick wrapper | The 10 existing `**AC-n**` items keep their ids; no existing item cites an id later without a leading one, so no outcome changes for current documents | Strip all emphasis before matching (accepts forms nobody writes) |
| 2026-10-01 | The gate accepts every list marker, and lint requires `-` | The gate must not under-count, while the mark tools, the digest normaliser and the dashboard read `-` only; Prepare's per-change section gate refuses a non-dash item on a planned wave, before approvals bind, and lint keeps refusing it once the wave is implementing | Teach every reader every marker (changes receipt digests and the dashboard); refuse non-dash items only in the gate (a `* [x]` item would then block close with no way to tick it through `wf_mark_task`) |
| 2026-10-01 | One shared stdlib module rather than aligning each regex in place | The census found the same bypasses in the gate and in lint; one parser keeps them from diverging again | Patch each regex separately |
| 2026-10-01 | Read every section with the heading, not refuse duplicates | Fail-closed with no new refusal; three closed documents show duplicates happen | Refuse duplicate headings |
| 2026-10-01 | Leave fenced lines counted | Today's behaviour over-blocks for a fenced checklist item; a `## ` line inside a fence still ends the section and hides later items, an under-block that no current document exhibits (census: 0) and that correct fence detection would need CommonMark info-string rules to fix; recorded under Out of scope | Exclude fenced lines as the digest normaliser does |

## Risks

| Risk | Mitigation |
| --- | --- |
| A target repository's open wave has a change doc with non-dash checklist items or a near-miss heading, and lint or close now refuses it after upgrade | The refusal names the item or heading and the fix; zero such documents exist in this repository; the CHANGELOG bullet states it |
| Wave `1ziml` edits `lifecycle_gate_support.py`, `lifecycle_gates.py`, `test_server_tools_lifecycle.py` and the spec in this wave | Serialization points declared; the edits touch different functions (council brief and gate recoveries versus the close checkbox helper and section check); rebase on whichever lands first |
| The lifecycle golden captures the close or Prepare envelope and changes | AC-8 requires it unchanged without regeneration; 1ziml regenerates the golden for its own deltas, so land order is coordinated |
| `test_lifecycle_gates_structure` pins the module-level names of `lifecycle_gate_support` | The two bound pattern names are kept; any new name is added to the pinned set deliberately |
| `wf_server/server_impl.py` is shared with 1zimm, which edits the alias translator | This change touches the reload purge set only; rebase on whichever lands first |
| A new framework module is missed by packaging or by an MCP reload | It is imported at module load by `lifecycle_gate_support` and `wave_validators`, as `review_evidence` is; a task confirms `build_pack.py` ships it and that the gate works after `wf_reload_mcp` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
