# Dashboard Title Uses Repository Name Only

Change ID: `12kh4-enh dashboard-title-repo-only`
Change Status: `complete`
Owner: Engineering
Status: ready
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard tab title should use the repository name followed by `Wavefoundry`, without the extra `Dashboard` suffix. The repository already distinguishes the tab; keeping `Wavefoundry` preserves product identity while avoiding the longer label that gets truncated in narrow browser tabs.

## Requirements

1. The dashboard title should use the repository name followed by `Wavefoundry` when the repository name is available.
2. The shared browser-side and server-side title paths should agree.
3. The fallback title should remain useful when the repository name is unavailable.
4. Regression coverage should verify the repository-only title.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing any dashboard metrics or tile behavior
- Changing the repo-first title fallback behavior beyond the suffix removal
- Changing local prompt surfaces

## Acceptance Criteria

- The tab title shows the repository name followed by `Wavefoundry` without the `Dashboard` suffix.
- The server-side HTML title and the browser-side `document.title` logic match.
- A fallback title still renders when the repository name is missing.
- Regression coverage asserts the new title string.

## Tasks

- Update the browser title helper to render `<repo> - Wavefoundry`
- Update the server-side title helper to render `<repo> - Wavefoundry`
- Update the title regression to expect the repo-plus-brand form

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The title should be shorter and cleaner |
| AC-2 | required | Both title paths must stay aligned |
| AC-3 | required | A fallback still needs to exist |
| AC-4 | required | Regression coverage should lock the title string in place |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Removing the suffix may reduce explicit context in a single tab | The repository name plus `Wavefoundry` keeps the product identity while staying short |
| A blank repository label could produce an empty title | Keep a fallback title for the missing-name case |
