# Design System Agent Rules


Owner: Engineering
Status: stub
Last verified: 2026-06-22

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

## Referencing tokens in code (consume the generated exports)

The DTCG token source under `tokens/` is transformed into framework-specific
outputs under `exports/` by the build pipeline. Reference the exports — never
hard-code values:

- **CSS** — use the custom property: `color: var(--ds-color-action-primary);`
  (light base + dark override blocks live in `exports/css/tokens.css`).
- **TypeScript** — import the typed constants:
  `import { tokens, tokensByMode } from "exports/ts/tokens.ts";`
  then `tokens["color.action.primary"]` (or `tokensByMode.dark[...]` for a mode).
- **Tailwind** — extend your config from `exports/tailwind/theme.config.js`
  (`theme.extend` is the light palette; `theme.extendDark` holds dark variants).
- **Flat JSON** — `exports/json/tokens.json` is a resolved key→value map for any
  other consumer.

`exports/` contents are **generated — do not edit them by hand.** After editing
any file under `tokens/`, regenerate with:

```sh
docs/design-system/bin/build-tokens
```

The pipeline is configured by `docs/design-system/build.config.json`
(`tool`, `version`, `targets`). `manifest.json` records `exportsGenerated`,
`exportsAt`, and `exportsStale`; docs-lint warns when `exportsStale` is `true`,
which means the token source is newer than the exports — re-run `build-tokens`.

## Extract, don't invent
- When source evidence is missing, record `null` + a `gaps.md` entry.
- Do not silently default to a value not found in evidence.
- Low-confidence items (`source-map.json` confidence: low) must have a corresponding gap.

<!-- Split B will extend this file with: microcopy lookup rules (content/microcopy.json),
     icon lookup rules (icons/_index.json), form validation rules, state pattern rules. -->
