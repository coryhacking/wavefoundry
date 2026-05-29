# Changed Files Diff View

Change ID: `12xtd-enh changed-files-diff-view`
Change Status: `complete`
Owner: implementer
Status: planned
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The Changed Files dialog shows which files changed and their line counts, but gives no way to inspect what actually changed without leaving the dashboard. Clicking through to a terminal or editor breaks flow. A per-file diff view directly in the dashboard makes it fast to verify scope before implementing or reviewing a wave.

## Requirements

1. Each file entry in the Changed Files dialog gains a hover effect indicating it is clickable.
2. Clicking a file entry opens a Diff dialog that shows the unified diff for that file.
3. The diff is fetched from a new `/api/diff` server endpoint that runs `git diff HEAD -- <path>` for tracked files and returns the raw diff text.
4. New (untracked) files show their full content as additions (equivalent to `git diff --no-index /dev/null <path>`).
5. The diff dialog renders added lines in green, removed lines in red, hunk headers in a muted color, and context lines in the default text color, using a monospace font.
6. The diff dialog is dismissible via close button or backdrop click, and does not block interaction with the Changed Files dialog underneath.

## Scope

**Problem statement:** The Changed Files dialog lists modified files with line counts but provides no way to see the actual diff content without leaving the dashboard.

**In scope:**

- Hover cursor and subtle highlight on file rows in the Changed Files dialog
- Diff dialog component with syntax-colored unified diff output
- `/api/diff?path=<rel-path>` endpoint in `dashboard_server.py` / `dashboard_lib.py`
- Handling for new (untracked) files and deleted files

**Out of scope:**

- Side-by-side diff view
- Diff editing or staging from the dashboard
- Syntax highlighting beyond unified diff line colors (added/removed/context/hunk)

## Acceptance Criteria

- [x] AC-1: Hovering a file row in the Changed Files dialog shows a pointer cursor and a visible highlight
- [x] AC-2: Clicking a file row opens a Diff dialog showing the unified diff for that file
- [x] AC-3: Added lines render green, removed lines render red, hunk headers render muted, context lines render in default text color
- [x] AC-4: New (untracked) files show their full content as green addition lines
- [x] AC-5: Deleted files show their former content as red removal lines
- [x] AC-6: The diff dialog closes on close button click or backdrop click
- [x] AC-7: `/api/diff` returns a 400 if the path is outside the repo root (path traversal guard)

## Tasks

- [x] Add `/api/diff` endpoint to `dashboard_server.py` and supporting logic in `dashboard_lib.py`
- [x] Add hover styles to `.file-tree-file` in `dashboard.css`
- [x] Add `DiffDialog` component to `dashboard.js` with unified diff renderer
- [x] Wire click handler on `FileTree` leaf nodes to open `DiffDialog`
- [x] Handle new/untracked and deleted file edge cases in the diff endpoint and renderer

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| api | implementer | — | `/api/diff` endpoint + `dashboard_lib.py` helper |
| ui | implementer | api (interface stable) | CSS hover + `DiffDialog` component + FileTree wiring |

## Serialization Points

- `dashboard_lib.py` diff helper interface must be stable before the UI workstream wires the fetch call

## Affected Architecture Docs

N/A — change is confined to the dashboard layer (server endpoint + JS/CSS). No boundary, flow, or cross-cutting impact.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | The row affordance is the entry point for the diff workflow |
| AC-2 | required | Clicking a file must open the diff view to make the feature usable |
| AC-3 | required | Line coloring is the core readability contract for diff inspection |
| AC-4 | required | Untracked files are a common dashboard case and must be rendered correctly |
| AC-5 | required | Deleted-file history is part of the inspection use case |
| AC-6 | required | The dialog must be dismissible to avoid trapping the operator |
| AC-7 | required | The endpoint must preserve the repo-root confinement rule |

## Progress Log

| Date | Update | Evidence |
|------|--------|---------|
| 2026-05-27 | All 7 ACs implemented and verified; 134 dashboard server tests pass | `dashboard_lib.py` `get_file_diff`, `dashboard_server.py` `/api/diff` route, `dashboard.css` hover + diff styles, `dashboard.js` `DiffDialog` + `FileTree` click plumbing |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|-------------|
| 2026-05-27 | No loading state in `DiffDialog` | Diff endpoint is local git; latency is negligible in practice. Defer if slow IO ever becomes observable. | Show spinner while fetch is in flight |

## Risks

| Risk | Mitigation |
|------|-----------|
| Path traversal via crafted `path` param | Resolve path and assert it is under repo root before running git; return 400 otherwise |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
