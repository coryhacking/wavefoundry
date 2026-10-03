# Council Verdict Location Hint

Change ID: `1zltv-enh council-verdict-location-hint`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-02
Wave: 1zls7 waveforge-defect-fixes

## Rationale

`_prepare_council_verdict_info` in `wf_server/server_impl.py` reads the prepare-phase Wave Council verdict only from the `## Review Checkpoints` section of `wave.md`. Waveforge reported that agents often write the structured `[prepare-council]` line somewhere else: in an admitted change document (usually its Progress Log or Decision Log) or under another `wave.md` heading (`## Watchpoints`, `## Review Evidence`). Prepare and Implement then return a plain `prepare_council_verdict_missing` saying no verdict was found, and the agent, which can see the line it wrote, loops or rewrites it in the same wrong place.

On waves whose review authority is typed (declared waves), a prose verdict is not readiness authority at all: readiness is the `wave-council-readiness` approval recorded through `wf_review_event`, and a missing one is reported as `missing_wave_council_signoff`. A misplaced prose line there points at the same misunderstanding.

An advisory that says where the line was found and where it belongs ends the loop without changing any gate.

## Requirements

1. **Find misplaced verdict lines.** A helper scans, for a wave, (a) `wave.md` outside its `## Review Checkpoints` section, where that section ends exactly where `_prepare_council_verdict_info` ends it (at the next heading of any level, `#{1,6}`), so a verdict under a `###` heading inside Review Checkpoints is outside the read section and gets a hint, and (b) each admitted change document of that wave, for verdict-shaped lines: a list item whose text contains the bracketed token `[prepare-council]` outside inline code, outside fenced code blocks (using the fence helper `1zltr` adds to `change_doc_checklist`, not a second fence reader). Each hit records the repository-relative file path and the nearest preceding heading of any level (`#{1,6}`), matching the section boundary above, so a verdict under a `###` inside Review Checkpoints is named by that `###` heading. Bare mentions of the word prepare-council in prose or in inline code are not hits. An unreadable change document is skipped silently here (other gates already report it).
2. **Advisory where a verdict is missing.** Wherever `prepare_council_verdict_missing` is emitted (`wf_prepare_wave_response`, both the mutating and dry-run branches; `wf_implement_wave_response`, the prose-authority branch) and at least one misplaced line is found, an additional advisory diagnostic `prepare_council_verdict_misplaced` is appended. Its message names each location found (path and heading, at most five, with a count of the rest) and says the verdict belongs in `wave.md` under `## Review Checkpoints`.
3. **Typed-authority pointer.** On a wave whose review authority is typed, wherever `missing_wave_council_signoff` is reported for readiness (`wf_implement_wave_response`'s typed branch, and `wf_prepare_wave_response` when its readiness gates return that code) and a misplaced or in-section prose verdict line is found, the same advisory code is appended with a message that says a prose verdict is not readiness authority on this wave and that readiness is recorded as `wave-council-readiness` through `wf_review_event`; it names where the prose line was found.
4. **Advisory only.** The new diagnostic is `advisory=True`; it never changes a status, a blocking result, `_blocked_envelope_hint`'s chosen remedy, `next_tools`, or any written state, and no file is edited by the server. `_prepare_council_verdict_info`'s result and the verdict parsing (`_PREPARE_COUNCIL_VERDICT_RE`) are unchanged.
5. **Docs.** `docs/specs/mcp-tool-surface.md` lists the new advisory code beside `prepare_council_verdict_missing`; the CHANGELOG gains an Unreleased `### Added` bullet.

## Scope

**Problem statement:** a council verdict written in the wrong place is reported as missing with no hint, so agents loop.

**In scope:**

- `wf_server/server_impl.py`: the scanning helper and the advisory at the sites in Requirements 2 and 3.
- Tests in the lifecycle server tests (for example `tests/test_server_tools_lifecycle.py`) for each placement and authority mode.
- `docs/specs/mcp-tool-surface.md` and the CHANGELOG.

**Out of scope:**

- Accepting a verdict from any location other than `## Review Checkpoints`, or moving lines automatically.
- Changing `prepare_council_verdict_missing`, `prepare_council_verdict_invalid` or `missing_wave_council_signoff` messages or severities.
- `lifecycle_gates.readiness_gate` itself (the advisory is appended by `wf_prepare_wave_response` after the gates run).

## Acceptance Criteria

- [x] AC-1: On a legacy (prose-authority) wave with a valid verdict line only in an admitted change document's `## Progress Log`, `wf_prepare_wave` (dry run and `mode='create'`) and `wf_implement_wave` (dry run) return `prepare_council_verdict_missing` plus an advisory `prepare_council_verdict_misplaced` that names that document's repository-relative path and `## Progress Log`, and names `## Review Checkpoints` as the location it belongs in.
- [x] AC-2: The same holds for a verdict line under `wave.md`'s `## Watchpoints`, naming `wave.md` and `## Watchpoints`, and for a verdict line under a `###` heading nested inside `## Review Checkpoints`, naming that `###` heading.
- [x] AC-3: On a typed-authority wave missing `wave-council-readiness`, with a prose verdict line present, `wf_implement_wave` and `wf_prepare_wave` add the advisory whose message names `wf_review_event` and `wave-council-readiness`.
- [x] AC-4: No advisory is added when there is no misplaced line, when the only mentions are in prose or inline code or inside a fenced block, or when a valid verdict is present in `## Review Checkpoints`; and in every case the response status, blocking diagnostics, `next_tools` and `usage` equal those of the same call without the misplaced line (or without the change).
- [x] AC-5: `docs/specs/mcp-tool-surface.md` and the CHANGELOG describe the advisory.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write failing-first tests for AC-1 to AC-3 and the negative cases in AC-4.
- [x] Add the scanning helper (wave.md outside `## Review Checkpoints`, admitted change docs, fence and inline-code aware).
- [x] Append the advisory at the Requirement 2 and 3 sites.
- [x] Update `docs/specs/mcp-tool-surface.md` and the CHANGELOG.
- [x] Run the change's suites and docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| verdict-hint | implementer | `1zltr` (fence helper in `change_doc_checklist`) | server_impl.py prepare and implement responses, tests, spec; serialize `server_impl.py` with `1zlts` and `1zlu0`, and `test_server_tools_lifecycle.py` with `1zlu0` |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A: an advisory diagnostic on two existing tool responses; no boundary, flow or authority change.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported loop: a verdict in a change document. |
| AC-2 | important | The other common placement. |
| AC-3 | important | Declared waves need the typed path, not a relocation hint. |
| AC-4 | required | The hint must never change a gate or fire on prose. |
| AC-5 | nice-to-have | Reference docs and release notes. |
| AC-6 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Delivery-review repair: `_verdict_line_headings` took the nearest heading from a fenced `## ` line, so a verdict after a fenced example was named under the example's heading. A fenced line is now neither a heading nor a verdict line. Test `test_a_fenced_heading_does_not_name_the_location` (unit and through Prepare and Implement, envelope unchanged apart from the advisory); failing-first `scratchpad/1zls7-repair-others/failing-first-1zltv.txt` (named `## Fenced Example`). Mutations in a scratch copy (`scratchpad/1zls7-repair-mutations.txt`), 18 of 18 killed: heading read before the fence check. Suites (scratch copy of the repaired tree, `scratchpad/1zls7-repair-suite-*.txt`): `run_tests.py --no-cache` 10722 tests across 156 files OK, 34 skipped; `--profile second` 10719 run, 0 of 156 files failed; `--profile declared` 10722 run, 0 of 156 files failed. | `scratchpad/1zls7-repair-*`, 2026-10-02 |
| 2026-10-02 | Implemented in `server_impl.py`: `_verdict_line_headings` (a list item whose text outside inline code carries `[prepare-council]`, outside fences read with `change_doc_checklist.fenced_line_flags` from `1zltr`; headings found with the same `#{1,6}` rule as `_prepare_council_verdict_info`, so a `###` inside Review Checkpoints names that heading), `_prepare_council_verdict_locations` (wave record outside Review Checkpoints, or including it on a typed wave, plus each admitted change document at its wave path or plans path; absent or unreadable documents skipped), and `_prepare_council_location_advisory`, which appends `prepare_council_verdict_misplaced` with `advisory=True` only when `prepare_council_verdict_missing` (prose) or `missing_wave_council_signoff` (typed) is already present, naming at most five locations and a count of the rest. Sites: `wf_prepare_wave_response` through one closure called before the first blocking return, before the `ready_for_council_review` return, after the dry-run missing advisory and after the readiness gates; `wf_implement_wave_response` after its typed and prose emits. The verdict parser and its regex are unchanged. `docs/specs/mcp-tool-surface.md` documents the code in the Prepare entry; `test_advisory_tags_appear_only_at_the_sanctioned_sites` gains the one new sanctioned site. Tests (`test_server_tools_lifecycle.py`): `CouncilVerdictLocationHintTests` (4) and `TypedExclusiveGateDerivationTests.test_typed_wave_missing_readiness_points_a_prose_verdict_at_wf_review_event`; every case compares the envelope with the same call with the helper patched to return None (status, `next_tools`, `usage` and every other diagnostic equal). AC map: AC-1 `test_verdict_in_a_change_document_progress_log` (prepare dry_run and create, implement dry_run); AC-2 `test_verdict_under_watchpoints_and_under_a_nested_heading`; AC-3 the typed test (implement and prepare); AC-4 `test_no_hint_for_prose_inline_code_fences_or_a_valid_verdict` (none, prose, inline code, fenced, valid in place) plus the baseline comparison in every test; AC-5 the spec entry and the CHANGELOG `### Added` bullet. Failing-first against HEAD `server_impl.py` (`scratchpad/1zls7-1zltv-failing-first.txt`): 6 errors across the 5 tests (no helper and no advisory). Mutations, all killed: fenced lines scanned and inline code not stripped (`test_no_hint_for_prose_inline_code_fences_or_a_valid_verdict`), section ending only at H2 (`test_verdict_under_watchpoints_and_under_a_nested_heading`), typed path disabled (`test_typed_wave_missing_readiness_points_a_prose_verdict_at_wf_review_event`). Gapfill: shell grep located the spec entry; `code_keyword` over `*.md` was then used for the code names. Suites (scratch copy of the whole wave tree, `run_tests.py --no-cache`): 10689 tests across 156 files OK, 34 skipped; `--profile declared` 10689 OK; `--profile second` 10686 run with one failure, `test_blockquoted_and_unusual_mark_items_are_markable`, whose fixture wrote an unlocalized `Wave ID:` line that the second profile reads as a member id; the fixture now goes through `_loc` and `--profile second --file test_server_tools_lifecycle.py` passes. An earlier full run caught a decorator displaced onto the inserted `_mark_item_block_end` helper (wf_mark layout refusals) and vocabulary and literal census hits; all fixed before the counted run. | `scratchpad/1zls7-1zltv-*`, 2026-10-02 |
| 2026-10-02 | Planned. Verified: `_prepare_council_verdict_info` scans only the `## Review Checkpoints` section; `prepare_council_verdict_missing` is emitted in `wf_prepare_wave_response` (mutating and dry-run branches) and in `wf_implement_wave_response` (prose-authority branch); the typed branch of `wf_implement_wave_response` emits `missing_wave_council_signoff`; `lifecycle_gates.PREPARE_READINESS_GATES` contains `readiness_gate`, which also emits `missing_wave_council_signoff`. | Planning read, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Detect only list items carrying the bracketed `[prepare-council]` token | Change documents mention prepare-council in prose often; the bracketed token is the verdict header's shape and avoids false hints | Any line containing prepare-council; only lines matching the full verdict regex (misses slightly malformed lines) |
| 2026-10-02 | Readiness amendments: the misplaced-verdict scanner uses the same section boundary as `_prepare_council_verdict_info` (ends at any `#{1,6}` heading), so a verdict under a `###` inside Review Checkpoints gets a hint (AC-2 extended); fences are read with `1zltr`'s helper, so `1zltr` lands first | Readiness review: a verdict the parser never reads would otherwise get no hint, and a second fence reader would drift | Scan Review Checkpoints to the next `##` (rejected: disagrees with the parser it explains) |
| 2026-10-02 | Advisory only, appended in server_impl after the gates | The hint must not alter readiness or close semantics, and keeping it out of `readiness_gate` leaves the gate contract unchanged | Make a misplaced verdict blocking; accept it from other locations |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Scanning admitted change docs adds read cost to Prepare and Implement | It runs only when a verdict or readiness approval is already missing, and reads documents those calls already read |
| A verdict example in documentation triggers the hint | Inline code and fenced blocks are excluded (AC-4) |
| Platform behaviour | Text scanning with repository-relative paths printed with forward slashes; identical on Windows, macOS, Linux and WSL2 |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
