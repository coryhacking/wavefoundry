# Removing a change from a wave also removes its Depends On lines

Change ID: `216g8-bug remove-change-leaves-depends-on-line`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-20
Wave: 216ga remove-change-depends-on-and-override-tolerant-tests

## Rationale

Waveforge (X8, against `7ab3963d`) reported that removing a change from a wave leaves its `Depends On:` line behind. Verified at `cd3d2043`: `wf_remove_change_response` removes the entry with `_change_block_pattern` (`wf_server/server_impl.py`), which matches the ID line, an optional previous-status line and the status line, and nothing after them. A `Depends On:` line written under the removed entry then sits under the entry above it, and docs-lint fails on that entry (or silently gives it a dependency it never had).

## Product Intent

- **Anyone who removes a change from a wave:** the whole entry goes, so the wave record stays valid and no other change inherits a dependency.
- **Boundaries:** only the entry being removed is affected; other entries and their `Depends On:` lines are unchanged.

## Requirements

1. `wf_remove_change` in `create` mode removes the entry's ID line, optional previous-status line, status line, and every consecutive column-0 `Depends On:` line directly after the status line, including a last one at end of file with no trailing newline. That is the canonical shape every writer produces and every record under `docs/waves/` uses (25 of 25 lines at `cd3d2043`). `Depends On:` lines placed elsewhere in an entry (indented, before the status line, or after a blank line) are left as today.
2. Lines after the removed block, including the next entry and its own `Depends On:` lines, are unchanged.
3. An entry with no `Depends On:` line is removed exactly as today.
4. The pattern stays on one source line and keeps the fragment `tests/test_label_reader_census.py` allowlists. `Depends On` is a fixed label (`vocabulary_profile.FIXED_LABELS`), so the literal is deliberate.

## Scope

**Problem statement:** removal leaves the removed entry's dependency lines in the wave record.

**In scope:**

- `_change_block_pattern` in `wf_server/server_impl.py`.
- A test in `tests/test_server_tools_lifecycle.py`.
- One CHANGELOG bullet in a new `[Unreleased]` section (1.33.0 is released).

**Out of scope:**

- `Depends On:` lines outside the canonical shape (Requirement 1).

- Rewriting other entries' `Depends On:` lines that name the removed change (lint reports those; the operator decides).
- Any other wave-record writer.

**Platform behaviour:** a text edit through the existing record write path. The same on Windows, macOS, Linux and WSL2, including records with CRLF line endings: the existing read (`read_text`) turns them into `\n` before matching, and the write path is unchanged.

## Acceptance Criteria

- [x] AC-1: A test builds a record with entries `a`, `b` (`Depends On: a`) and `c` (`Depends On: a`). Removing `b` (middle) leaves no line of `b` and leaves `a` and `c` byte-identical, and docs-lint over the record reports no dependency error. The same test also removes an entry with a `Depends On:` line in first position and in last position (followed by the next `##` section, and at end of file), leaving every other line unchanged. Each case fails against the current pattern. Oracle: the pre-fix pattern in a scratch copy.
- [x] AC-2: The existing remove test (`test_wave_add_and_remove_change`) and the label census (`test_label_reader_census`) still pass.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Extend the pattern to take the trailing `Depends On:` lines.
- [x] Add the dependent-entry removal test and run it against the old pattern in a scratch copy.
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          | server_impl.py and one test |


## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`

## Affected Architecture Docs

N/A. One regular expression in an existing writer; no boundary, flow or verification seam changes.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported defect. |
| AC-2 | required | No regression in the existing remove path. |
| AC-3 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-20 | Planned on operator request after the Waveforge note against `7ab3963d`. | `_change_block_pattern` read at `cd3d2043`. |
| 2026-10-20 | Readiness round 1: code-reviewer, qa-reviewer, red-team and docs-contract-reviewer PASS, no blockers. Folded in before readying: Requirement 1 names the canonical shape and the end-of-file case; Requirement 4 keeps the census fragment; AC-1 covers first, middle and last positions with `c` depending on `a`; the CHANGELOG bullet opens `[Unreleased]`. QA executed the pre-fix pattern on the a/b/c record: `Depends On: a` stayed under `a`. | Readiness lane and seat reports. |
| 2026-10-20 | Implemented. `_change_block_pattern` appends `(?:\nDepends On:[^\n]*)*` after the status line, still on one source line, so the census fragment is unchanged. New `WaveLifecycleMutationTests.test_remove_change_takes_its_depends_on_lines` covers middle (a / b dep a / c dep a), first, last before `## Participants`, and last at end of file without a trailing newline; each case asserts the whole record text and the parsed dependencies (`_parse_change_records`). Blank-line handling around the removed entry is unchanged from today. Scratch mutant (pre-fix pattern): all 4 subtests fail, each showing a leftover `Depends On:` line. CHANGELOG `[Unreleased]` opened with the Fixed bullet. Gapfill: shell reads and a Python mutation driver used for mutant setup; MCP reads used for review claims. | `run_tests.py --file test_server_tools_lifecycle.py`: 653 tests OK; scratch log `/private/tmp/claude-502/-Users-coryhacking-Developer-wavefoundry/64d2b992-b50d-423e-985d-22b0c59dd1ac/scratchpad/216ga/mutants.log`. |
| 2026-10-20 | Delivery review: code-reviewer, qa-reviewer, red-team and docs-contract-reviewer PASS. Repaired the code-reviewer's minor finding before approvals: a fifth case, "indented line stays", pins Requirement 1's boundary; the widened `\s*` mutant that survived now fails that case. On the AC-1 wording (qa and red-team): the test checks the lint parser, so the real validator was also run in scratch on the a/b/c record: `wave_validators.check_wave_docs` reports `change 1200b-feat a cannot depend on itself` after the pre-fix removal and no dependency failure after the fixed one. Focused default run of the five touched files 1480 tests OK; `--profile second` 5 of 5 files passed. | Scratch `tools/lintprobe.py` output; delivery lane reports. |
| 2026-10-20 | Full suite run 1 failed one test: `test_profile_literal_census` flagged the literal `"wave.md"` passed as the label argument to `_parse_change_records` in the new test. Replaced with `vocabulary_profile.RECORD_FILENAME` (a label only; assertions unchanged). Full suite run 2 green; receipt written. | `run_tests.py`: 11977 tests across 202 files OK (12 skipped). |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-20 | Extend the existing pattern rather than parse entries into blocks. | Smallest change; the entry shape is fixed. | Parse the Changes section into entry blocks (more code and review). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The pattern eats a line that belongs to the next entry. | Only `Depends On:` lines directly after the status line match; AC-1 checks the next entry is byte-identical. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
