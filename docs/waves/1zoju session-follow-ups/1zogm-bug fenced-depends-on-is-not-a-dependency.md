# A Fenced Depends On Line Is Not A Dependency

Change ID: `1zogm-bug fenced-depends-on-is-not-a-dependency`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-03
Wave: 1zoju session-follow-ups

## Rationale

Follow-up F6 from wave `1zlu1` (change `1zlu2`, left as is at delivery review): a `Depends On:` line inside a fenced code block in a wave record's member list is read by `wave_validators._parse_change_records` as a real dependency. The parser strips each line and matches `DEPENDS_ON_LINE_PATTERN` with no fence awareness. Two effects follow:

- `wf_close_change` treats the record as a dependent of the closed change and ACTIVATES it (moves it from `planned` or `blocked` to `ready`) when its other dependencies are done. That is a write driven by an example.
- docs-lint's dependency rule (`check_wave_docs`) reports an unmet or unknown dependency for the example, and the `Depends On` backtick syntax check fails an example line that has no backticks.

A fenced block is an example by Markdown's own meaning, and the framework already sets fenced code aside elsewhere: `change_doc_checklist.fenced_line_flags` (wave `1zls7`, `1zltr`) is the shared reading for headings and checklist items, with CommonMark fence rules, blockquote awareness, and an unterminated fence read as ordinary lines (fail closed).

The 1zls7 close-status fix (`1zlu0`) deliberately reads fenced STATUS lines: `_close_open_work_records` treats a record as open when any status line attributed to it, fenced or not, is not done, so an example can never hide an open change from close. That property must survive this change, and the Decision Log reasons out why the two lines are treated differently.

Corpus measurement on 2026-10-03: 15 `Depends On:` lines across every `docs/waves/*/wave.md`, none fenced; no column-0 `Depends On:` line in any change document under `docs/waves/` or `docs/plans/`. The change alters no current record.

## Requirements

1. `_parse_change_records` and `_parse_legacy_item_records` skip a `Depends On:` line that `change_doc_checklist.fenced_line_flags` flags as fenced. Every other branch of both parsers (record ids, `Change Status`, `Previous Change Status`, status-labelled lines, `Item Status`) is unchanged and still reads fenced lines.
2. Census of `Depends On` readers (predicate: every framework script, tests excluded, that reads a `Depends On:` line or `WorkRecord.depends_on`; found with `code_keyword` for `depends_on`, `Depends On:` and `DEPENDS_ON_LINE_PATTERN` on 2026-10-03). Each agrees after the change:
   - `wave_validators._parse_change_records` and `_parse_legacy_item_records`: Requirement 1.
   - `wave_validators.check_wave_docs` dependency rule and self-dependency check: read `record.depends_on`, so they follow Requirement 1 with no edit.
   - `wave_validators.check_wave_docs` backtick syntax check (raw lines starting `Depends On:`): skips fenced lines, using the same flags.
   - `server_impl._close_change_in_memory_violations`, and `wf_close_change_response`'s dependency gate and dependent activation: read `record.depends_on`, so they follow Requirement 1 with no edit.
   - `wf_close_change_response`'s legacy change-document reader (`dependencies_not_in_wave_record` advisory, `DEPENDS_ON_LINE_PATTERN` over the change document): skips fenced lines.
   - `wf_implement_wave_response`'s own member-section parser (`wave_dependencies`, column-0 `^Depends On:` lines after a member id line) and its legacy change-document fallback (`fullmatch` on `Depends On:` lines): skip fenced lines. The member-section parser currently extracts `## Changes` with `(?=^## |\Z)`, so a `## ` line inside a fence truncates the section. The parser therefore computes fence flags over the WHOLE wave text, ends the section only at an unfenced `## ` heading, and maps the flags to the section's lines. The legacy fallback computes flags over the whole change document.
3. docs-lint WARNS (not fails) for each fenced `Depends On:` line inside a wave record's member section, saying it is inside a fenced block and is not read as a dependency, so a dependency fenced by mistake is visible.
4. The status reading is untouched: `_close_open_work_records` (close-status union), `lifecycle_gate_support`'s admitted-id union for the close checklist gate, and `_collect_wave_state` see the same records, ids and status values as before, because only the `Depends On` branch changes.
5. Platform behaviour: `fenced_line_flags` works on lines after `splitlines()`, so LF and CRLF records read the same; no path or filesystem behaviour is involved. Identical on Windows, macOS, Linux and WSL2.

## Scope

**Problem statement:** an example `Depends On:` line in a fenced block is acted on as a declaration, including a status write.

**In scope:**

- `wave_lint_lib/wave_validators.py` (Requirement 1, the syntax check, the warning).
- `wf_server/server_impl.py` (the implement-wave parser, its legacy fallback, the close-change legacy reader).
- Tests in `tests/test_docs_lint.py`, `tests/test_close_change.py` and `tests/test_server_tools_lifecycle.py`.
- `docs/specs/mcp-tool-surface.md` where `wf_close_change` and `wf_implement_wave` describe reading `Depends On:`, and a CHANGELOG bullet.

**Out of scope:**

- A fenced `Change ID:` line still starts a record (existing behaviour, fail closed for close status). Separately, a non-fenced line after a fenced id can attach to the fenced record; that parser quirk is recorded, not fixed here.
- Fenced status lines: unchanged by design (Requirement 4).

## Acceptance Criteria

- [x] AC-1: Reproducer, failing first: in a wave record whose member B has no unfenced `Depends On:` line but has a fenced block containing `` Depends On: `A` ``, change A is closed through `wf_close_change(A, mode='create')`; B is NOT activated (its status stays `planned`). On the current tree B is activated.
- [x] AC-2: The same record lints with no dependency failure for B; the warning of Requirement 3 names B's fenced line. A fenced `Depends On: A` without backticks raises no syntax failure.
- [x] AC-3: A non-fenced `Depends On:` still activates and still gates (the existing `tests/test_close_change.py` activation and dependency-gate tests pass unchanged), and an UNTERMINATED fence leaves the line read as a dependency.
- [x] AC-4: Status fail-closed is preserved: a wave record whose member reads `complete` with a fenced `` Change Status: `active` `` line under it is still reported open by `_close_open_work_records` and blocks `wf_close_wave`, asserted in the same test module as the fenced-dependency case.
- [x] AC-5: `wf_implement_wave`'s context reports `depends_on: []` for a member whose only `Depends On:` line is fenced, and the resolved dependency for a non-fenced one.
- [x] AC-6: A parity test feeds one wave record to `_parse_change_records`, the implement-wave parser and the close-change path, and asserts all three see the same dependency set. The record has fenced and non-fenced dependency lines, plus a fenced block holding a `## ` line placed BEFORE a later member's unfenced `Depends On:` line, so a fence-unaware section split would drop that dependency.
- [x] AC-7: The change's own test files and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write the AC-1 reproducer and confirm B is activated on the current tree.
- [x] Apply Requirement 1 to both record parsers.
- [x] Apply the fence skip to the syntax check, the implement-wave parser, its legacy fallback and the close-change legacy reader.
- [x] Add the Requirement 3 warning.
- [x] Add the AC-2 to AC-6 tests.
- [x] Update the spec wording and the CHANGELOG; run the full suite in a scratch copy and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reproducer | implementer | none | AC-1, failing first |
| parsers | implementer | reproducer | Requirement 1, AC-2, AC-3, AC-4 |
| server-readers | implementer | parsers | AC-5, AC-6 |
| docs | implementer | server-readers | spec and CHANGELOG |

## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`, `.wavefoundry/framework/scripts/tests/test_close_change.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `docs/specs/mcp-tool-surface.md`
- The CHANGELOG at the repository root is edited too.

## Affected Architecture Docs

N/A: the wave-record grammar gains one rule (fenced dependency lines are examples) applied identically by its existing readers; no component boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect: a write driven by an example |
| AC-2 | required | Lint agrees with close |
| AC-3 | required | Real dependencies keep working; unterminated fences stay read |
| AC-4 | required | The 1zls7 fail-closed status property is the constraint on this change |
| AC-5 | important | The third reader agrees |
| AC-6 | required | Every reader must agree, asserted once |
| AC-7 | required | Suite and lint gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-03 | Reverification R1: the parity fixture's E became `complete` in the repair, so a sibling test now keeps E `planned` and asserts the close path activates only C and reports D `dependencies_not_done` with dependencies `[E]` exactly once, so a dropped or fenced-duplicated dependency on the close path is visible. | `FencedDependsOnTests.test_the_close_path_reads_each_unfenced_dependency_once`; `test_close_change` 40 OK |
| 2026-10-03 | Delivery repair F1: `_close_change_member_section` (which `_close_change_block` reads) and `_insert_change_block_into_changes_section` (`wf_add_change`) ignore headings inside a closed fenced block, both for the member heading and for the section end; the AC-6 parity test now asserts `activated == [C, D]` with no `not_activated` entry | Tests: `test_close_change.FencedDependsOnTests.test_fenced_heading_after_a_member_does_not_end_the_member_list`, `test_fenced_member_heading_example_does_not_start_the_member_list`, `test_admission_never_inserts_inside_a_fence`, and the tightened `test_every_reader_sees_the_same_dependency_set`. Failing-first on the pre-repair tree: C stayed unactivated, A was refused (`error`), the new block landed inside the fence or above the real heading, and parity got `[]`. Mutations R1 to R4 (each fence check removed singly) killed. Full suite `--no-cache` in a fresh scratch copy, plus `--profile second` and `--profile declared`: 10,930 tests across 157 files OK (34 skipped); second 10,927 OK; declared 10,930 OK. The first repaired run failed only `test_label_reader_census` (its allowlist entry for the old `wf_current_wave` message became stale and was removed) |
| 2026-10-03 | Implemented: both record parsers, the `Depends On` syntax check, the implement-wave member parser (now `_wave_member_dependencies`, fence flags over the whole record, section ends only at an unfenced `## ` heading), its change-document fallback and the close-change legacy reader skip fenced `Depends On:` lines; docs-lint warns per fenced line in the member section (`fenced_member_dependency_lines`); spec and CHANGELOG updated | Tests: `test_close_change.FencedDependsOnTests` (AC-1 to AC-4, AC-6, Requirement 2 and 5), `test_server_tools_lifecycle.ImplementDependencyProducerTests.test_fenced_dependency_is_not_reported` (AC-5 and the fallback), `test_docs_lint.FencedMemberDependencyLineTests`. Failing-first on HEAD 6ec1cce0: AC-1 activated B, AC-2, AC-5 and AC-6 failed; AC-3 and AC-4 passed as preservation checks. Mutations M1 to M7 (each reader's fence skip, the section end, the warning) all killed. full suite `run_tests.py --no-cache` in a scratch copy: 10,925 tests, 157 files, OK; `--profile second` and `--profile declared` OK (second 10,922 tests, declared 10,925; the final run, after every code change; 34 tests skipped in the full run). Found while testing, out of scope: `_close_change_member_section` ends the member list at a fenced `## ` line, so `wf_close_change` refuses (`change_status_unreadable`) to activate a member after it; fail-closed. Gapfill: retrieval used grep and sed over the scripts tree instead of the MCP code tools, because the edits needed exact multi-line anchors in a 25,000-line module and the attached MCP server runs the pre-change code |
| 2026-10-03 | Planned from `1zlu1` follow-up F6 | Reader census in Requirement 2; corpus probe: 15 wave-record `Depends On:` lines, none fenced |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-03 | Readiness amendment F11: the implement-wave parser takes fence flags over the whole wave text and ends `## Changes` only at an unfenced heading | Its `(?=^## |\Z)` split cuts the section at a fenced `## ` line, which would drop later members' dependencies and break parity with the record parser | Flags over the extracted section only (rejected: the truncation happens before the flags are computed) |
| 2026-10-03 | Skip fenced `Depends On:` lines in every reader, but keep reading fenced status lines | The two lines fail in opposite directions. A status line is read so that an open change cannot be HIDDEN from close: reading an example status as open can only block a close, never allow a wrong one, so reading it is fail-closed. A dependency line drives a WRITE: `wf_close_change` activates the dependents it names, so reading an example as a dependency makes an example move a change to `ready`, which is fail-open. Not reading an example dependency costs nothing real: it was never a declaration, and the Requirement 3 warning makes a mistaken fence visible | Skip fenced lines for every field (rejected: lets a fenced example `complete` hide an open change, undoing 1zlu0); keep reading fenced dependencies everywhere (rejected: example-driven activation); skip them only for activation while lint and the gates still read them (rejected: the readers would disagree, and lint would keep failing an example) |
| 2026-10-03 | Reuse `change_doc_checklist.fenced_line_flags` | One CommonMark-faithful fence reading already shared by headings and checklist items, with the unterminated-fence fail-closed rule and blockquote handling | A local fence regex (rejected: a second fence definition) |
| 2026-10-03 | Warn on a fenced dependency inside the member section | Turns a silent non-declaration into a visible one at zero corpus cost | Fail (rejected: an example is legitimate); stay silent (rejected: a mistaken fence would quietly drop a real dependency) |
| 2026-10-03 | Leave fenced `Change ID:` lines starting records | That reading feeds the close-status union and the checklist id union, both fail-closed; changing it is a separate decision | Fold it in (rejected: widens the change into the status contract) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| An author fences a real dependency by mistake and it stops gating | Requirement 3 warning names the line |
| A reader is missed and disagrees | Requirement 2 census plus the AC-6 parity test |
| The status fail-closed property regresses | AC-4 pins it beside the fenced-dependency test |
| Platform behaviour | Line-based text reading; identical on Windows, macOS, Linux and WSL2 (Requirement 5) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
