# Close Change Refuses Ambiguous Wave Records

Change ID: `21cw2-bug close-change-dependency-gate-reads-last-status`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-21
Wave: 21cw4 windows-pack-setup-root-and-record-hardening

## Rationale

A downstream distribution reported (their Y9), and reading the code at `1c5ba851` confirms, three record shapes that make `wf_close_change` act on the wrong facts:

- `_parse_change_records` (`.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py:1127`) reads status and id lines inside fences; only `Depends On:` skips them (wave `1zoju`), so that close-wave's union of recorded statuses stays fail-closed.
- The close-change dependency gate (`wf_server/server_impl.py`, `wf_close_change_response`) reads only a dependency's last status value, so a fenced `complete` example after a real `planned` reads as done.
- A fenced id line between a member's status and its `Depends On:` starts a new record that takes the dependency.
- With an id listed twice, the lookup (`by_id`) uses the last record while `_close_change_rewrite_block` rewrites the first block.

`wf_close_wave` is not affected: it fails closed on any not-done recorded status.

## Product Intent

`wf_close_change` acts only on a wave record it can read unambiguously. Before: an example inside a fence, or a duplicated member, can let a change close while its dependency is unfinished, or rewrite a different block from the one checked. After: close-change refuses with a diagnostic naming the ambiguity whenever a record has more than one status value, a fenced id line, or a duplicate id. Boundaries: the parser and close-wave are unchanged; unambiguous records close exactly as today. AC-1 with AC-3 tests whether the intent was established.

## Requirements

1. Close-change acts only on a wave record in which every record `_parse_change_records` returns is unambiguous, and refuses, before any write, with a diagnostic naming the record id and the cause, when:
   - an id is returned more than once (cause "duplicate record");
   - a record has more than one status value, from any lines the parser attributes to it, fenced or not, under any heading (cause "multiple status lines");
   - a fenced id line starts a record (cause "fenced record line").
2. Fenced `Depends On:` examples stay ignored, as wave `1zoju` designed (the parser already skips them); its pinned tests are unchanged.
3. With Requirement 1 holding, every status reader in close-change (its own closable gate, the dependency gate, the dependent-activation check and `_close_change_in_memory_violations`) reads a record's single status, so no reader can see a value the others do not.
4. Unambiguous records produce the same result and writes as today.

## Scope

**Problem statement:** close-change can check one record and act on another, or read an example as a real status.

**In scope:**

- The ambiguity refusal in `wf_close_change_response`.
- Tests for each reported shape and an unchanged clean close.

**Out of scope:**

- Changing `_parse_change_records` fence handling (it would loosen close-wave).
- New docs-lint rules.

## Acceptance Criteria

- [x] AC-1: A dependency recorded `planned` followed by a fenced `complete` example inside the member section is refused with the multiple-status-lines cause; on the current code the close succeeds.
- [x] AC-2: A `planned` change whose member block is followed, under a later heading, by a fenced closable status example is refused with the multiple-status-lines cause, and its status line is not rewritten; on the current code the close succeeds.
- [x] AC-3: A fenced id example between a member's status and its `Depends On:` line is refused with the fenced-record-line cause.
- [x] AC-4: A member id listed twice, or an id that also appears as a `Change ID:` line outside the member section, is refused with the duplicate-record cause, and no block is rewritten.
- [x] AC-5: A clean wave record closes with the same writes as today, and the existing fenced-`Depends On:` tests from wave `1zoju` pass unchanged.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the ambiguity refusal (duplicate record, multiple status lines, fenced record line) in `wf_close_change_response` before any gate or planned write.
- [x] Add the ambiguity refusal to the Gates list of `docs/prompts/close-change.prompt.md` and to its source seed, if the seed carries the same list (open `seed_edit_allowed` for the seed edit).
- [x] Add the shape fixtures and the clean-close regression.
- [x] CHANGELOG Unreleased entry (Fixed).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                       |
| ---------- | ----------- | ---------- | --------------------------- |
| fix        | implementer | none       | ambiguity refusal           |
| tests      | implementer | fix        | shape fixtures              |


## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/`, `docs/prompts/close-change.prompt.md`

## Affected Architecture Docs

N/A for architecture docs: stricter input checks inside one lifecycle tool; no boundary, flow or verification seam changes. The close-change prompt's Gates list is updated (Tasks).

## Platform Behavior

Text parsing only; identical on native Windows, macOS, Linux and WSL2, including CRLF records (fence detection uses the existing line helper).

## AC Priority


| AC   | Priority | Rationale                    |
| ---- | -------- | ---------------------------- |
| AC-1 | required | fenced status in members     |
| AC-2 | required | fenced status after members  |
| AC-3 | required | fenced id shape              |
| AC-4 | required | duplicate id shape           |
| AC-5 | required | clean close unchanged        |
| AC-6 | required | change-local verification    |


## Progress Log


| Date       | Update  | Evidence                                          |
| ---------- | ------- | ------------------------------------------------- |
| 2026-10-21 | Planned | distribution follow-up Y9, verified at `1c5ba851` |
| 2026-10-21 | Readiness amendments round 1: duplicates checked across the whole record; fenced `Depends On:` left to the 1zoju design; union rule in all three status readers; distinct causes; Gates list task. | readiness qa-reviewer, code-reviewer and docs-contract-reviewer findings |
| 2026-10-21 | Readiness amendment round 2: one ambiguity rule replaces the separate fence and union checks, because the parser spans headings and the closing change's own gate read the last status (AC-2). | readiness code-reviewer and red-team recheck |
| 2026-10-21 | Implementation notes from readiness: an unreadable status-label line counts as a status value (fails closed) and the diagnostic says a line was unreadable; `Previous Change Status:` is not a status value (regression test). | readiness red-team and qa-reviewer recheck |
| 2026-10-21 | Implemented: `_close_change_ambiguity_messages` and a `wave_record_ambiguous` refusal at the top of `wf_close_change_response`, before every gate and planned write (duplicate record, multiple status lines incl. unreadable count, fenced record line with line number); parser and close-wave unchanged. Gate text added to `docs/prompts/close-change.prompt.md`, its install baseline `install/lifecycle-prompts/close-change.prompt.md`, seed-190 Close change gates and seed-100 close-change bullet (seed gate opened/closed around the seed edit). | `AmbiguousWaveRecordTests` (7 tests) in `test_close_change.py`: against HEAD `server_impl.py` the AC-1/2/3/4 shapes return `dry_run` (would close), the unreadable shape is refused only as `change_status_unreadable`, the two helper tests error; after: 47 ok, `--profile second` 47 ok; 1zoju `FencedDependsOnTests` unchanged and green; test_lifecycle_baseline_drift, test_mcp_tool_registry, test_render_agent_surfaces, test_reconcile_scan, test_distribution_seams ok; wf_validate_docs ok |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-21 | One ambiguity rule in close-change: duplicate records, more than one status value, or a fenced id line | Fails closed for every status reader at once; leaves the shared parser and close-wave untouched | Separate duplicate, fence and union checks (readiness round 1: missed the closing change's own gate); fence-check the parser (loosens close-wave's union) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A real record carries a fenced example in its member section | The refusal names the line; moving the example out of the member section restores closing |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
