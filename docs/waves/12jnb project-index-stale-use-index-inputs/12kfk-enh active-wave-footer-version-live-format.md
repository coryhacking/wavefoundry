# Active Wave Footer Version Live Format

Change ID: `12kfk-enh active-wave-footer-version-live-format`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard footer should surface the Wavefoundry version up front, keep the live indicator visible, and leave the updated timestamp readable as secondary context.

## Requirements

1. The footer must include the current Wavefoundry version.
2. The live indicator must remain visible in the footer.
3. The updated timestamp must remain visible in the footer.
4. The footer layout should remain compact and readable on mobile.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/dashboard/dashboard.css`
- wave documentation updates needed to track the footer copy/layout change

**Out of scope:**

- Metric tile values
- Detail dialog ordering
- Wave lifecycle semantics

## Acceptance Criteria

- The footer begins with the Wavefoundry version label.
- The live indicator stays visible beside the version when connected.
- The updated timestamp remains visible and readable.
- The footer stays usable on mobile.

## Tasks

- Update footer markup to surface the version first
- Add footer styles for the left/right layout
- Sync the wave record with the footer change

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The version should be surfaced up front. |
| AC-2 | required | The live state should remain obvious. |
| AC-3 | required | The update timestamp must stay visible. |
| AC-4 | required | The footer must remain usable on smaller screens. |
