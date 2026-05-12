# Dashboard: Files Tile Should Show Files And Line Changes

Change ID: `12j2j-enh files-tile-lines-changed`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The current Files tile emphasizes `today` rather than the more useful git working-tree signal. At the same time, the header duplicates that higher-signal information in small pills (`files changed`, `+lines`, `-lines`). The dashboard would be more readable if the Files tile became the single place that summarizes the current changed-file and line-delta state, and the low-value duplicate pills were removed from the header.

## Requirements

1. The Files tile must summarize the current changed-file state from git, not just “files updated today”.
2. The Files tile must include line-change information using the existing added/removed line stats.
3. The header must remove the small pills that duplicate file-count and line-delta information.
4. The branch/commit identity pills must remain intact unless their information is intentionally relocated elsewhere.
5. Clicking the Files tile must still open the relevant changed-files dialog.
6. The resulting tile copy must favor durable “files changed” semantics over the low-signal `today` label.

## Scope

**Problem statement:** the Files tile uses a weak recency label while the more useful changed-file and line-delta signals are duplicated in small header pills.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
  - Rework the Files metric tile value/note content
  - Remove duplicate file-count / line-delta pills from the header
  - Keep the Files tile click behavior
- `.wavefoundry/framework/scripts/dashboard_lib.py`
  - Reuse or lightly reshape existing git stats if needed; avoid introducing a second git summary path
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add or update tests if the snapshot contract changes

**Out of scope:**

- Redesigning the whole dashboard header
- Changing the changed-files dialog payload beyond what the tile needs
- Replacing git stats with time-window analytics

## Acceptance Criteria

- AC-1: The Files tile no longer uses `today` as its primary note.
- AC-2: The Files tile shows changed-file count using current git working-tree data.
- AC-3: The Files tile shows added/removed line totals in the tile itself.
- AC-4: The duplicate header pills for changed-file count and line deltas are removed.
- AC-5: Clicking the Files tile still opens the changed-files dialog.
- AC-6: Existing branch/commit identity information remains available in the header.
- AC-7: The relevant dashboard verification passes.

## Tasks

- Audit the current Files tile and header git-pill responsibilities
- Move changed-file count and line-delta summary into the Files tile
- Remove duplicate file/diff pills from the header
- Preserve Files tile click-through to the files dialog
- Add or update tests as needed
- Run dashboard verification

## Affected Architecture Docs

N/A — UI signal-composition change only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Removes the low-value recency framing the operator explicitly called out |
| AC-2 | required | Core files-state signal for the tile |
| AC-3 | important | Makes the tile carry the useful diff information currently stranded in pills |
| AC-4 | required | Prevents duplicate summaries across header and tile |
| AC-5 | required | Preserve existing drill-down behavior |
| AC-6 | important | Avoids losing repo identity context while simplifying the header |
| AC-7 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created to replace the low-signal “files updated today” tile with a git-change summary tile and remove duplicate file/diff pills from the header. | Operator request; `dashboard.js`; `dashboard_lib.py` |
| 2026-05-11 | Reviewed the change doc against the current dashboard implementation and found no blocking design issues. Implemented the Files tile shift to working-tree file count plus line deltas, removed duplicate header file/diff pills, and pointed the tile to the all-changed-files dialog. | `dashboard.js`; `dashboard.css`; `node --check .wavefoundry/framework/dashboard/dashboard.js`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Reuse existing git working-tree stats rather than invent a new files-updated summary source | The dashboard already computes changed files and added/removed lines; the problem is presentation, not missing data | Add a second bespoke summary path (rejected: unnecessary duplication) |

## Risks

| Risk | Mitigation |
|------|------------|
| Tile copy becomes too dense after absorbing the diff summary | Keep the tile concise and push detail to the dialog |
| Removing pills also removes useful glanceable context | Preserve branch/commit pills; remove only the duplicated file/diff pills |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
