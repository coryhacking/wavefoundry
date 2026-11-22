# Guru description refresh misses a departing vocabulary profile

Change ID: `241l2-bug guru-description-refresh-misses-departing-profile`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-22
Wave: 242yp extension-loader-and-guru-refresh

## Rationale

The Waveforge distribution reported this against v1.47.0, and it is still present at v1.49.0. When a render finds an existing `.claude/agents/guru.md`, `_refresh_guru_description` in `.wavefoundry/framework/scripts/render_agent_surfaces.py` replaces the `description:` line only when its value equals a member of `previous_guru_descriptions(shortcut)`. That tuple fills the lifecycle shortcut names from the active vocabulary profile. It does not contain the current template (`_CLAUDE_GURU_TEMPLATE_DESCRIPTION`) filled with another profile's shortcuts.

Observed failure, reproduced on the current tree by calling `_refresh_guru_description` directly:

1. Input: a header whose description is the current template filled with `Plan wave`, `Implement set`, `Close set` and `Prepare set` (the departing profile), rendered under the default profile.
2. Actual result: the header is returned unchanged, because the renderer treats the description as customized.
3. Expected result: the description is replaced with the current text, as for any other managed description.

In the distribution this leaves the departing profile's shortcut names in the subagent description, and `test_render_agent_surfaces.RoutingGuidanceTextTests.test_rendered_subagent_description_matches_the_renderer` fails.

## Product Intent

A maintainer of a distribution that changes its vocabulary profile, or of a project upgraded across a default shortcut rename, gets the current Guru subagent description on the next render without passing the departing profile or editing the line by hand. A description an operator customized outside the shortcut names is still kept. AC-1 and AC-4 establish the intent; AC-2, AC-3 and AC-5 establish that the broader match does not take over customized or current text.

## Requirements

1. `_refresh_guru_description` must treat a `description:` value as managed when it fully matches the current template or any earlier shipped form, with any text in each shortcut slot. The slots are `@PLAN@`, `@IMPLEMENT@`, `@CLOSE@` and `@PREPARE@` in the current template and the `{plan}`, `{implement}`, `{close}` and `{prepare}` placeholders in the earlier forms.
2. Each shortcut slot must match either of two alternatives, and the whole value must match under `fullmatch`:
   1. the active profile's own shortcut for that slot, as an escaped literal;
   2. the generic slot pattern: one or more characters, none of which is `,`, `(`, `)`, a carriage return or a line feed.

   An empty slot must not match. A departing profile whose shortcut contains `,`, `(` or `)` matches neither alternative, so its text is kept as customized (fails safe).
3. Every character outside the slots must match the form exactly. A value that differs anywhere outside the slots is customized and must be kept byte for byte, with no stderr notice.
4. Every text that `previous_guru_descriptions` recognizes today, under the default profile or under a renamed shortcut table, must still be replaced.
5. A value equal to the current description must be left unchanged, with no stderr notice.
6. The existing header guards stay as they are: a single plain unindented `description:` key, no indented continuation line, a valid frontmatter block, and preservation of the line ending and every other byte.
7. The hand-filled shortcut entries in `previous_guru_descriptions` are replaced by the forms themselves, since slot matching covers them. The short form's literal `Implement wave` and `Close wave` become `{implement}` and `{close}` slots, which keeps both literal texts recognized. Interface: `previous_guru_descriptions()` takes no argument and returns the earlier forms with `{plan}`-style placeholders. The matcher takes an optional `shortcut` callable for the active profile's names, which defaults to `vocabulary_profile.shortcut`.

## Scope

**Problem statement:** the managed-description check compares against texts filled with the active profile's shortcuts, so a description rendered under any other profile is mistaken for a customization.

**In scope:**

- Slot-based matching of managed Guru descriptions in `.wavefoundry/framework/scripts/render_agent_surfaces.py`, replacing the hand-filled shortcut entries.
- Tests in `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`, including updates to `GuruDescriptionRefreshTests` and `test_a_profile_that_kept_the_earlier_plan_shortcut_is_recognised`, which call `previous_guru_descriptions` with a shortcut table. `test_placeholder_form_follows_a_non_default_vocabulary` asserts that a renamed-profile text is kept under the default profile; that assertion inverts, because the text is now managed.
- One `[Unreleased]` bullet in `CHANGELOG.md`.

**Out of scope:**

- Seed 160 prose and its rendered upgrade prompt. Both say a description "equal to a previously shipped Guru description" is replaced, which stays accurate: a text rendered under another profile was shipped under that profile.
- Seed 050, which holds only the template description and no refresh sentence.
- Recognizing a departing profile whose shortcut contains `,`, `(` or `)`. Such a text is kept as customized. `vocabulary_profile._shortcut_problem` allows these characters, but no profile shipped in this repository uses them.
- `.claude/agents/guru.md` in this repository. It already carries the current description, so a render leaves it unchanged. No golden fixture, digest pin or other rendered surface in this repository contains the description (census: a whole-tree search for the description's opening words finds only the renderer, its test, seed 050, this repository's `.claude/agents/guru.md` and the closed wave 237ei record).
- The Cursor auto-Guru rule, which has no managed-description refresh.

## Acceptance Criteria

- [x] AC-1: A `.claude/agents/guru.md` whose description is the current template filled with another profile's shortcuts (for example `Plan wave`, `Implement set`, `Close set`, `Prepare set`), rendered under the default profile, has its description replaced with the current text and the stderr notice printed. The current code keeps it. The cases also cover an in-slot routing exclusion, `Prepare wave or security reviews` in the `@PREPARE@` slot, which is replaced as a documented case.
- [x] AC-2: A description that matches a form in every slot but differs by one character outside the slots is kept byte for byte, with no notice. The cases cover:
  1. an edit inside the fixed prose;
  2. under the default profile, a slot value that contains `,` or `(`;
  3. trailing text after the closing `.)`.
- [x] AC-3: A description with one empty shortcut slot, for example `(, Implement wave, Close wave, Prepare wave, etc.)`, is kept byte for byte, with no notice.
- [x] AC-4: Every text that the current `previous_guru_descriptions` returns, copied into the test as literal strings before the edit, is replaced in LF, CRLF and BOM files. The current code keeps the renamed-table texts in case 2. The cases cover:
  1. the default profile's texts, rendered under the default profile;
  2. the texts for a table that renames all four keys (`Plan task`, `Build batch`, `Close batch`, `Prepare batch`), rendered under the default profile;
  3. the texts for a table whose plan shortcut is `Plan (spec)`, rendered under that table as the active profile.
- [x] AC-5: The current description, rendered under the default profile and under a renamed shortcut table, is left unchanged, with no notice.
- [x] AC-6: The change's own suites and every test it adds pass under the default, declared and second profiles; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

AC-1 and AC-4 fail under the current code. AC-2, AC-3 and AC-5 pass under the current code, because it keeps everything it does not recognize; they guard the broader match. Each must be shown to fail against a known-bad matcher: a slot pattern that accepts empty text or crosses `,` and `(` (AC-2, AC-3), and a matcher that drops the equality check for the current text (AC-5). A matcher with only the generic slot pattern must fail AC-4 case 3.

## Tasks

- [x] Replace the filled entries in `previous_guru_descriptions` with the earlier forms and add a slot matcher used by `_refresh_guru_description` for those forms and the current template.
- [x] Update `GuruDescriptionRefreshTests` and the earlier-plan-shortcut test for the new interface, invert the kept-under-default assertion, and replace the `len(known) >= 4` assertion with one that fits the forms.
- [x] Point `test_each_previously_shipped_description_is_replaced`, `test_other_descriptions_and_headers_are_kept` and `test_control_without_the_known_set_leaves_a_stale_description` at filled forms or the AC-4 literals, never at raw placeholder forms. The control must still fail when the earlier forms are removed, using an earlier-form text that the current template cannot match.
- [x] Add tests for AC-1 to AC-5, with the AC-4 texts as literal strings captured from the current code before the edit.
- [x] Run the known-bad matchers for AC-2, AC-3 and AC-5 and record that each fails.
- [x] Add one `[Unreleased]` bullet to `CHANGELOG.md`.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py --file test_render_agent_surfaces.py` under the default, declared and second profiles.

## Agent Execution Graph

1. Capture the AC-4 literal texts from the current code.
2. Implement the matcher and the tests.
3. Run the known-bad matchers, then the three profiles.

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| matcher-and-tests | implementer | none | One file pair; serial. |

## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`

## Affected Architecture Docs

N/A. The change is confined to one function's matching rule in the renderer, with no boundary, flow or verification-seam impact.

## Platform Behavior

Windows, macOS, Linux and WSL2 behave identically: the matcher compares the value after the existing line-ending strip, and the existing CRLF and BOM tests cover the file encodings.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported defect. |
| AC-2 | required | Customized descriptions must survive the broader match. |
| AC-3 | required | Defines the slot boundary. |
| AC-4 | required | Keeps every currently recognized text recognized. |
| AC-5 | required | The current text must not be rewritten or reported. |
| AC-6 | required | Suite and validation evidence. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-22 | Planned. Failure reproduced by calling `_refresh_guru_description` with the departing-profile text: returned unchanged. | Direct call on the current tree |
| 2026-11-22 | Readiness repair cycle 1 for `242yp-cr-guru-slot-excludes-legal-shortcut-chars`: Requirement 2 now lets each slot match the active profile's own shortcut literally or the generic pattern; AC-4 adds the fully renamed table and a `Plan (spec)` table. Folded in: the in-slot routing exclusion as a replaced case in AC-1, the test-interface task, the seed 050 correction and the interface statement. | `.wavefoundry/work/242yp/review/code-reviewer-readiness.md`, `qa-reviewer-readiness.md`, `docs-contract-reviewer-readiness.md`, `red-team-primer.md` |
| 2026-11-22 | Implemented. `render_agent_surfaces.py`: `previous_guru_descriptions()` returns the long, investigation and short forms with `{plan}`-style slots; `_is_managed_guru_description(value, shortcut=None)` fullmatches the current template and each form, with each slot matching the active shortcut literally or `[^,()\r\n]+`; `_refresh_guru_description` uses it. Tests: AC-4 literals captured from the HEAD function before the edit (7 default, 4 renamed-table, 2 `Plan (spec)`); new AC-1, AC-2, AC-3, AC-4 case 3 and AC-5 tests; the three trap tests use the literals; `test_placeholder_form_follows_a_non_default_vocabulary` is folded into the AC-4 test. `python3 -B -m unittest test_render_agent_surfaces` from `scripts/tests`: 227 tests OK. Known-bad runs on a scratch copy, `GuruDescriptionRefreshTests`: generic-only slot fails AC-4 case 3 (8); empty-accepting slot fails AC-3 (2); `.+` slot fails AC-2 commas and parentheses (3); no equality check fails AC-5 (2); `match` for `fullmatch` fails AC-2 trailing text (2); the HEAD renderer fails AC-1 and AC-4 case 2 (25). Rendering a `git archive HEAD` export with the new renderer changed no file, and its `.claude/agents/guru.md` is byte-identical to this repository's. The three-profile `run_tests.py` run is left to the coordinator. | Scratch copies under the session scratchpad |
| 2026-11-22 | Gapfill: retrieval used `code_keyword` and `code_read` for the renderer and call sites; the test file sections, `small_change_lane.py` and the shortcut binding were read with `grep` and `sed` in the shell. | Session tool log |
| 2026-11-22 | The coordinator's partial full-suite run failed `test_distribution_seams.LiteralReconcileKeyTests.test_no_name_function_takes_a_key_built_at_run_time`: `_is_managed_guru_description` called `shortcut()` with a key looked up at run time. Fixed by calling it with the four literal keys and replacing `_GURU_SLOT_KEYS` with `_GURU_SLOT_PLACEHOLDERS`. `test_distribution_seams.py` and `test_render_agent_surfaces.py` pass through `run_tests.py --file`. | `run_tests.py --file` output in the coordinator session |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-22 | Match managed descriptions by form with any text in the shortcut slots. | Operator decision 2026-11-22: "DO, with a broader fix than the reporter asked for." Efficacy: replaying the reported text through the slot matcher replaces it, and no profile needs to be passed. It could wrongly take over a description customized only in its shortcut names; that is accepted, since those names are framework-owned. | (a) Add the current template filled with the departing profile's shortcuts to the tuple: needs the departing profile at render time, which the renderer does not know. (b) Fill the current template with every known profile's shortcuts: misses distribution profiles this repository does not ship. |
| 2026-11-22 | Drop the hand-filled shortcut entries and slot the short form's `Implement wave` and `Close wave`. | Planner default: slot matching recognizes every filled entry, so the entries add nothing; AC-4 proves no recognized text is lost. | Keep the filled entries alongside the matcher: redundant code to maintain. |
| 2026-11-22 | A slot excludes `,`, `(`, `)` and line breaks and must be non-empty. | Operator brief. The separators delimit the slots, so a slot cannot absorb a neighbor or extra list items. | Any non-empty text: a slot could swallow `, extra item` and accept a customized list. |
| 2026-11-22 | Each slot matches the active profile's own shortcut as an escaped literal, or the generic slot pattern, under `fullmatch`. | Coordinator decision (reversible default) on finding `242yp-cr-guru-slot-excludes-legal-shortcut-chars`: `vocabulary_profile._shortcut_problem` allows `,`, `(` and `)`, so the generic pattern alone would drop texts recognized today. The alternation keeps every one. A departing profile with those characters is kept (fails safe). | Narrow Requirement 4 and AC-4 to shortcuts without those characters: loses texts recognized today. |
| 2026-11-22 | Ordinary review in one wave with the sibling upgrade-extension-loader spec; the CHANGELOG bullet is part of this change. | Coordinator relaying the operator discussion of 2026-11-22. | Small-change lane: withdrawn by the same discussion. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A render replaces an operator edit made within a shortcut slot. This covers renamed shortcut names and also an in-slot routing exclusion with no comma or parenthesis, such as `Prepare wave or security reviews`. | Accepted: the file is tracked in Git, the render prints a stderr notice naming the file, and an exclusion added as a separate comma-listed item is kept. |
| A departing profile whose shortcut contains `,`, `(` or `)` is not recognized. | Its text is kept as customized (fails safe), and the operator edits the one line. No profile shipped in this repository uses these characters. |
| A downstream test calls `previous_guru_descriptions(shortcut)` with a table. | This repository's only callers are in `test_render_agent_surfaces.py`, which this change updates. A distribution's own copy of that test updates with the shipped file. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
