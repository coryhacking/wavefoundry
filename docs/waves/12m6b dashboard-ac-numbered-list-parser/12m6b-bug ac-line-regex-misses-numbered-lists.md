# Dashboard: AC Parser Misses Numbered List Items

Change ID: `12m6b-bug ac-line-regex-misses-numbered-lists`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12m6b dashboard-ac-numbered-list-parser`

## Rationale

`_AC_LINE_RE` in `dashboard_lib.py` only matches bullet list lines (`- item`). Change docs that use ordered lists (`1. item`, `2. item`) produce zero AC items, causing the ACs progress bar and dialogs to show 0/0. Projects with numbered-list AC sections are invisible to the dashboard.

## Requirements

1. `_AC_LINE_RE` must match ordered list items (`\d+\.`) in addition to bullet list items (`-`).
2. Checkbox marks (`[x]` / `[ ]`) on numbered items must be parsed correctly when present.
3. Existing bullet-list parsing must be unchanged.

## Scope

**Problem statement:** `_AC_LINE_RE` regex does not handle ordered list syntax.

**In scope:**

- Extend `_AC_LINE_RE` to match `^\s*(?:-|\d+\.)\s+` as the line prefix.

**Out of scope:**

- Migrating existing change docs from numbered to bullet lists.
- Fixing the `Change Status` vs `Status` field mismatch (separate lower-priority issue).

## Acceptance Criteria

- AC-1: A `## Acceptance Criteria` section using `1.` / `2.` numbered items is parsed and returns AC items.
- AC-2: A `## Acceptance Criteria` section using `-` bullet items is still parsed correctly.
- AC-3: Checkbox marks on numbered items (`1. [x] text`) are recognized as done.

## Tasks

- Extend `_AC_LINE_RE` in `dashboard_lib.py` to match `(?:-|\d+\.)` as the list prefix.
- Add / extend tests for numbered-list AC parsing.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| regex-fix  | implementer | — | One-line regex change + test coverage |

## Serialization Points

- N/A

## Affected Architecture Docs

N/A — confined to change-doc parser internals.

## AC Priority

| AC   | Priority | Rationale |
|------|----------|-----------|
| AC-1 | required | Core correctness for numbered-list projects |
| AC-2 | required | Must not regress bullet-list projects |
| AC-3 | important | Checkbox inference on numbered items |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Root cause confirmed via analysis; regex fix identified | Analysis report |
| 2026-05-14 | `_AC_LINE_RE` extended to `(?:-|\d+\.)` prefix; two new tests added; 1161 tests pass | `python3 run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Extend parser (Option A) rather than mandate bullet lists | Zero migration cost; projects with numbered ACs work immediately | Mandate bullet lists (Option B) — requires doc migration |

## Risks

| Risk | Mitigation |
|------|------------|
| Numbered list items without checkbox marks default to `done=False` | Correct — same as bullet items; closed-wave credit handles completion |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
