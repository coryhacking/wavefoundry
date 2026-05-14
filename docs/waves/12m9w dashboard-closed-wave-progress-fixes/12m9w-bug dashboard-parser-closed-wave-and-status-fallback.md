# Dashboard Parser: Closed-Wave Force-Done and Status Field Fallback

Change ID: `12m9w-bug dashboard-parser-closed-wave-and-status-fallback`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12m9w dashboard-closed-wave-progress-fixes`

## Rationale

Three Python-side parsing bugs caused the dashboard tile metrics to disagree with the progress bars. First, `_wave_only_metric_counts` had no closed-wave force-done logic — changes, tasks, and ACs from closed-wave staged plan docs were counted as pending even though the wave was closed. Second, `_CHANGE_STATUS_PATTERN` only matched `Change Status: \`...\`` — projects using `Item Status: \`...\`` got zero changes surfaced (the zip collapsed to empty). Third, the status parser in `dashboard_lib.py` had no fallback for projects that omit the `Change` prefix and backticks entirely, causing all statuses to parse as `"unknown"`.

## Requirements

1. `_wave_only_metric_counts` must treat changes, tasks, and ACs from closed/completed waves as done, matching the JS bar's force-done logic.
2. `_CHANGE_STATUS_PATTERN` must match both `Change Status:` and `Item Status:` field names.
3. The change doc status parser must fall back to `Status: <value>` (plain, no backticks) when `Change Status: \`...\`` is absent.

## Scope

**Problem statement:** Python tile metrics disagreed with JS progress bars for closed-wave plan docs; projects using `Item Status:` or bare `Status:` fields were invisible to the dashboard.

**In scope:**

- `_wave_only_metric_counts` in `dashboard_lib.py`: compute `closed_wave_ids`; force changes/tasks/ACs done when `wave_id` is in closed/completed set.
- `_CHANGE_STATUS_PATTERN` in `server.py`: extend to `(?:Change|Item) Status:`.
- Status parse fallback in `dashboard_lib.py` (`_read_change_doc_info`): `server._CHANGE_STATUS_PATTERN.search(text) or server._STATUS_PATTERN.search(text)`.

**Out of scope:**

- JS-side fixes — covered in the companion change.
- Fixing the zip fragility in `_parse_wave_record` (separate wave, lower priority).

## Acceptance Criteria

- AC-1: Tile pending count for a closed-wave staged plan doc (e.g. `1n3dq`) matches the bar (counted as done, not pending).
- AC-2: A wave doc using `Item Status: \`planned\`` surfaces its changes in the dashboard (not zero).
- AC-3: A change doc using bare `Status: planning` (no backticks, no `Change` prefix) parses a non-`"unknown"` status.

## Tasks

- [x] Add `closed_wave_ids` to `_wave_only_metric_counts`; inline force-done for changes, tasks, and ACs.
- [x] Extend `_CHANGE_STATUS_PATTERN` regex to `(?:Change|Item) Status:`.
- [x] Add `or server._STATUS_PATTERN.search(text)` fallback in `_read_change_doc_info`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| py-fixes   | implementer | — | Three targeted edits across dashboard_lib.py and server.py |

## Serialization Points

- N/A

## Affected Architecture Docs

N/A — confined to dashboard metric parsing internals; no boundary or flow changes.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Tile/bar agreement — core correctness |
| AC-2 | required  | Projects using Item Status are completely invisible without this fix |
| AC-3 | important | Graceful handling of looser format; prevents silent unknown status |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | All three Python fixes applied; 1161 tests pass; verified in 14c–14d packages | `python3 run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Extend regex with `(?:Change\|Item)` rather than a second pattern | One pattern, zero call-site changes | Separate `_ITEM_STATUS_PATTERN` — more explicit but requires updating all call sites |
| 2026-05-14 | Fallback to `_STATUS_PATTERN` at call site rather than modifying `_CHANGE_STATUS_PATTERN` | Keeps server.py pattern focused on canonical format; fallback is a display concern | Widen `_CHANGE_STATUS_PATTERN` — would affect all server.py call sites |

## Risks

| Risk | Mitigation |
|------|------------|
| `Status: active` (doc-level header) mistaken for change status | Only triggered when `Change Status:` is absent; acceptable for pure change docs without the wavefoundry header |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
