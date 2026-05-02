# exports/


Owner: Engineering
Status: stub
Last verified: 2026-05-01

This directory contains generated token outputs (CSS custom properties, Tailwind theme, TypeScript constants, flat JSON). These files are **generated** — do not edit them directly.

## Subdirectories

- `css/` — CSS custom properties (`tokens.css`)
- `tailwind/` — Tailwind theme config (`theme.config.js`)
- `ts/` — TypeScript token constants (`tokens.ts`)
- `json/` — Flat resolved token map (`tokens.json`)

## Generating outputs

Run the token-build pipeline configured in `docs/design-system/build.config.json` (see plan `12atj-feat design-token-build-pipeline`).
The contents of these subdirectories are **out of scope** for wave `12as1 design-system-extraction`.
