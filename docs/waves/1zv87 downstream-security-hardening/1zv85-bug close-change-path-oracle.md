# Lifecycle Tools Build Paths From An Unchecked Change Id

Change ID: `1zv85-bug close-change-path-oracle`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-05
Wave: 1zv87 downstream-security-hardening

## Rationale

Downstream report (Waveforge S4, confirmed by reading at `fdd8de15`): `wf_close_change_response` records `change_not_admitted` but keeps evaluating gates, building `_wave_change_doc_path(root, wave_md, change_id)` (`wave_md.parent / f"{change_id}.md"`) and calling `is_file()` and `read_bytes()`. An id like `../../x` or an absolute path makes the server stat and read any `*.md` path, and the diagnostics differ between missing, unreadable and present: an existence and readability oracle. No write is reachable there. The readiness review found the same pattern with a WRITE in `_mark_change_item_response` (`wf_mark_ac`, `wf_mark_task`): it builds `_wave_change_doc_path(root, wave_md, change_id)` from an unchecked id with no admission check, and a traversal id with `mode="apply"` rewrote a checkbox in a file outside the repository (reproduced in a scratch copy).

## Requirements

1. A shared `_change_id_shape_error(change_id)` refuses, with `invalid_arguments` and no filesystem access, a `change_id` that is empty, absolute (including a drive-letter form), or contains a path separator (`/` or `\`), a `..` component, or a NUL; `wf_close_change_response` and `_mark_change_item_response` call it before any path work.
2. `_mark_change_item_response` requires the change to be admitted to the wave (an id parsed from the wave record) before building the document path.
3. When the change is not admitted, `wf_close_change`'s document gates are skipped (no path is built from the id).
4. Admitted changes behave exactly as before in all three tools.
5. A census of `_wave_change_doc_path(` and `f"{change_id}.md"` call sites is recorded in the Progress Log (the review found the others take ids parsed from wave text or discovery).
6. CHANGELOG gets a bullet under `## [1.29.0]` `### Security`.

## Scope

**Problem statement:** lifecycle tools build file paths from an unchecked argument; one probes arbitrary paths and two write to them.

**In scope:**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py` `wf_close_change_response` and `_mark_change_item_response` (`wf_mark_ac`, `wf_mark_task`); tests; CHANGELOG.

**Out of scope:**

- Tools whose ids come from wave text or discovery (`wf_add_change`, `wf_get_change`, the lifecycle gate support readers).

## Acceptance Criteria

- [x] AC-1: `wf_close_change` with `../../outside/secret` and with an absolute id returns `invalid_arguments`, and the response is identical whether the target `.md` exists or not (no `change_doc_*` diagnostic and no filesystem access for the id path).
- [x] AC-2: A well-formed but unadmitted id returns `change_not_admitted` without `change_doc_missing`.
- [x] AC-2b: `wf_mark_ac` and `wf_mark_task` with a traversal id and `mode="apply"` return `invalid_arguments` and leave a planted outside file byte-identical; a well-formed unadmitted id is refused before any path is built; an admitted change is still marked.
- [x] AC-3: An admitted change still closes (existing tests green).
- [x] AC-4: Removing the shape check or the gate skip fails the tests (scratch copy).
- [x] AC-5: CHANGELOG Security bullet; docs validate.

## Tasks

- [x] Validate the id shape before any path work
- [x] Skip document gates when not admitted
- [x] Tests for traversal, absolute, unadmitted and admitted ids in all three tools
- [x] Show the mutants fail in a scratch copy
- [x] CHANGELOG Security bullet

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| close-change | implementer | — | server_impl only |


## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`

## Affected Architecture Docs

N/A: argument validation in one tool.

## Platform Behavior

Platform-neutral; both `/` and `\` count as separators, and a drive-letter id counts as absolute on every platform.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the reported oracle |
| AC-2 | required | skip document gates |
| AC-2b | required | the write found in readiness |
| AC-3 | required | no regression |
| AC-4 | required | pins catch a revert |
| AC-5 | required | release notes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-05 | Implemented: `_change_id_shape_error` (empty, NUL, absolute or drive form, separator, `..`) first in `_mark_change_item_response` and after mode validation in `wf_close_change_response`; mark path requires the id in `_extract_change_ids_from_wave_text` (existing `change_not_found`); close builds the document path only when admitted. Census: the other `_wave_change_doc_path` sites take ids from wave text, discovery, a wave-record match or `build_id`. Fixture in `test_server_tools_lifecycle.MarkChangeItemRecoveryTests` now lists its change (admission requirement). Tests `test_change_id_path_guard.py` | mutants (shape check, mark admission, close gate skip) fail |
| 2026-10-05 | Readiness review folded in: `wf_mark_ac` and `wf_mark_task` write through the same unchecked path (reproduced in scratch); shared shape check and admission check added | readiness F1 (blocking) |
| 2026-10-05 | Planned from the Waveforge private report S4 | `wf_close_change_response` continues past `change_not_admitted` to `_wave_change_doc_path` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-05 | Shape check plus gate skip | either alone closes the oracle; both make the intent explicit and survive future gate reordering | only `contained_path` on the built path |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A legitimate id with an unusual character is refused | the check rejects only separators, `..`, absolute forms and NUL, which no admitted id can contain |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
