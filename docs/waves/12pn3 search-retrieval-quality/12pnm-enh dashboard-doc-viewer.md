# Dashboard Document Viewer

Change ID: `12pnm-enh dashboard-doc-viewer`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-17
Wave: 12pn3 search-retrieval-quality

## Rationale

Wave IDs and change IDs are displayed throughout the main dashboard page but clicking them does nothing. Reading a wave doc or change doc requires leaving the browser and opening the file in an editor. This friction breaks the "glance at the dashboard to understand project state" workflow. Clicking a wave ID or change ID should open the markdown document inline, rendered with the same `renderMarkdownish` function already used for agent detail panels.

## Requirements

1. `GET /api/doc?type=wave&id={wave_id}` returns the raw text of `docs/waves/{wave_id}/wave.md`. Returns 404 if the file does not exist.
2. `GET /api/doc?type=change&id={change_id}&wave={wave_id}` returns the raw text of `docs/waves/{wave_id}/{change_id}.md`. Returns 404 if the file does not exist.
3. Both endpoints validate that the resolved file path stays within `docs/waves/` under the repo root — path traversal returns 403.
4. In the Waves card, `wave_id` text (both in active `OpenWaveCard` and pending `PendingWaveRow`) is rendered as a clickable element.
5. In the Changes table, each row's change ID and title cell is clickable.
6. Clicking a wave ID opens a `DocDialog` showing the fetched wave.md rendered with `renderMarkdownish`.
7. Clicking a change ID/title opens a `DocDialog` showing the fetched change doc rendered with `renderMarkdownish`.
8. The `DocDialog` shows a loading state while the fetch is in flight and an error message if the fetch fails or the server returns a non-2xx status.
9. The dialog is closable via the × button, Escape key, and clicking the backdrop — consistent with all other dialogs.
10. The dialog is wide enough to comfortably read a full change doc (min 600px content width where viewport allows).

## Scope

**Problem statement:** Wave and change documents are not accessible from the dashboard; users must open files in an editor to read specs and status.

**In scope:**

- New `/api/doc` GET endpoint in `dashboard_server.py`
- `DocDialog` React component in `dashboard.js`
- Clickable wave IDs in `OpenWaveCard` and `PendingWaveRow`
- Clickable change ID+title cell in `ChangesTable`
- CSS for `doc-dialog` width and clickable-id hover styles

**Out of scope:**

- Clickable IDs in metric dialogs (WavesDialog, ChangesDialog, AcsDialog, TasksDialog) — follow-on work
- Editing documents from the dashboard
- Syntax highlighting in code blocks
- Support for `docs/plans/` staged change docs (follow-on; only in-wave docs for now)

## Acceptance Criteria

- AC-1: `GET /api/doc?type=wave&id=12pn3+search-retrieval-quality` returns the text of `docs/waves/12pn3 search-retrieval-quality/wave.md` with status 200.
- AC-2: `GET /api/doc?type=change&id=12pn3-enh+hybrid-fts-retrieval&wave=12pn3+search-retrieval-quality` returns the text of the corresponding change doc with status 200.
- AC-3: A path-traversal request (e.g., `id=../../AGENTS`) returns 403.
- AC-4: Clicking the wave ID in an active wave card opens a dialog displaying the wave document title (`# Wave Record` heading visible).
- AC-5: Clicking a change row in the Changes table opens a dialog displaying that change's document.
- AC-6: The dialog shows "Loading…" before the fetch completes and an error string if the server returns a non-2xx status.
- AC-7: The dialog closes on Escape, × button, and backdrop click.

## Tasks

- Add `parse_qs`, `unquote` to `urllib.parse` import in `dashboard_server.py`
- Add `_handle_doc()` method to `DashboardHandler`; route `GET /api/doc` to it
- Add `DocDialog` component to `dashboard.js` (uses `DialogFrame`, fetches on mount, renders with `renderMarkdownish`)
- Add `onWaveClick` prop to `WavesCard`, `OpenWaveCard`, `PendingWaveRow`; render wave_id as a `<button className="id-link">` that calls the handler
- Add `onChangeClick` prop to `ChangesTable`; make change ID+title `<td>` clickable
- Wire handlers in `Dashboard`: `setDocView({ title, url })` state; render `DocDialog` when `docView` is set
- Add `.id-link` CSS (button reset + underline-on-hover) and `.doc-dialog` width override to `dashboard.css`

## Agent Execution Graph

| Workstream    | Owner              | Depends On | Notes                                     |
| ------------- | ------------------ | ---------- | ----------------------------------------- |
| backend-api   | framework-engineer | —          | /api/doc endpoint in dashboard_server.py  |
| frontend-js   | framework-engineer | —          | DocDialog + clickable IDs in dashboard.js |
| frontend-css  | framework-engineer | frontend-js | .id-link and .doc-dialog styles          |

## Serialization Points

- `dashboard.js` changes are self-contained; `dashboard_server.py` changes are self-contained — can be developed in parallel

## Affected Architecture Docs

N/A — dashboard is a local dev tool with no boundary or data-flow impact on the indexer or MCP server.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  |           |
| AC-2 | required  |           |
| AC-3 | required  |           |
| AC-4 | required  |           |
| AC-5 | required  |           |
| AC-6 | required  |           |
| AC-7 | required  |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-17 | Implemented. `/api/doc` endpoint, `DocDialog`, clickable wave IDs in WavesCard, clickable change rows in ChangesTable, `.id-link` / `.doc-dialog` CSS. 1326 tests pass. | `run_tests.py` OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-17 | Fetch markdown on dialog open, not pre-loaded in snapshot | Keeps snapshot payload small; docs are only needed on demand | Pre-load all wave/change markdown in snapshot (large payload) |
| 2026-05-17 | Use DialogFrame for DocDialog | Consistent UX — Escape, backdrop click, × button already handled | Custom dialog implementation |
| 2026-05-17 | Scope to main dashboard page first | WavesCard and ChangesTable are the primary surfaces; metric dialogs are secondary | All surfaces at once (more risk, same value) |
| 2026-05-17 | Path confined to docs/waves only | Staged changes (docs/plans/) are rare; in-wave docs cover active work | Also serve docs/plans/ (added complexity, low immediate value) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Path traversal via crafted wave_id or change_id | Resolve path and assert it is under docs/waves/ before reading; return 403 on violation |
| Missing change doc (file deleted after wave admission) | Return 404; DocDialog shows error state |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
