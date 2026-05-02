# Design System Agent Rules


Owner: Engineering
Status: stub
Last verified: 2026-05-01

## Before building any UI component
1. Check `components/_index.json` — use an existing component if one matches.
2. Never create a duplicate component without checking the index first.
3. If no match exists, append a proposal to `proposed-additions.md`.

## Before writing any hard-coded value
1. Check `tokens/semantic.tokens.json` for the appropriate semantic token.
2. Reference semantic tokens only — never primitives or raw hex/px/z-index/duration.
3. Token naming follows dot-path convention: `category.subcategory.scale.variant`.

## Token usage
- Use semantic token references (`{color.action.primary.background}`), not raw values.
- Never bypass semantic layer to reference primitives directly.
- Never use raw hex codes, px values, z-index integers, or duration ms in component code.

## Extract, don't invent
- When source evidence is missing, record `null` + a `gaps.md` entry.
- Do not silently default to a value not found in evidence.
- Low-confidence items (`source-map.json` confidence: low) must have a corresponding gap.

<!-- Split B will extend this file with: microcopy lookup rules (content/microcopy.json),
     icon lookup rules (icons/_index.json), form validation rules, state pattern rules. -->
