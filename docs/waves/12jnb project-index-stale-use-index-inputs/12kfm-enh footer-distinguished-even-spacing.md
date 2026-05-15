# Footer Distinguished Even Spacing

Change ID: `12kfm-enh footer-distinguished-even-spacing`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard footer should feel more intentional and balanced. A footer line with even vertical spacing, softer blue brand text, and no header version clutter will give the live state and timestamp a more distinguished presentation.

## Requirements

1. The footer should keep the Wavefoundry version visible in mixed case.
2. The live indicator and updated timestamp should remain visible.
3. The footer should use even top and bottom spacing.
4. The footer should read as a distinct footer line rather than a tile/card.
5. The footer brand should stay medium-weight, not bold, and match the live label size.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/dashboard/dashboard.css`
- wave documentation updates needed to track the footer styling change

**Out of scope:**

- Footer content
- Metric tiles
- Wave lifecycle semantics

## Acceptance Criteria

- The footer has a more distinguished footer-line presentation with balanced vertical spacing and a softer visual weight than the header.
- The version, live state, and updated time remain readable.
- The version text remains mixed case and blue, matching the LIVE indicator weight, without a pill background.
- The footer brand and LIVE label use the same font size.
- Mobile layout remains usable.
- The header does not repeat the framework version.

## Tasks

- Update footer markup if needed for balanced spacing
- Style the footer as a distinct framed element
- Keep the header free of footer version clutter
- Sync the wave record with the footer style change

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The footer needs a more deliberate footer-line look. |
| AC-2 | required | Vertical spacing should be even and tighter below. |
| AC-3 | required | The footer version text must stay mixed case, blue, and match the LIVE indicator weight. |
| AC-4 | required | The footer brand and LIVE label must share the same font size. |
| AC-5 | required | The mobile layout must remain usable. |
| AC-6 | required | The header should not repeat the version; the footer owns it. |
