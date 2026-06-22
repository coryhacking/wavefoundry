# exports/


Owner: Engineering
Status: stub
Last verified: 2026-06-22

This directory contains generated token outputs (CSS custom properties, Tailwind theme, TypeScript constants, flat JSON). These files are **generated** — do not edit them directly.

## Subdirectories

- `css/` — CSS custom properties (`tokens.css`)
- `tailwind/` — Tailwind theme config (`theme.config.js`)
- `ts/` — TypeScript token constants (`tokens.ts`)
- `json/` — Flat resolved token map (`tokens.json`)

## Generating outputs

Run the token-build pipeline (wave `12atj-feat design-token-build-pipeline`):

```sh
docs/design-system/bin/build-tokens
```

The pipeline reads `docs/design-system/build.config.json` (`tool`, `version`, `targets`) and the DTCG token source under `../tokens/`, then writes the four outputs above. It is mode-aware (CSS dark override block, TS per-mode maps, Tailwind dark variants), deterministic, and idempotent.

`build.config.json` `tool` may be `style-dictionary` (run `npm install -D style-dictionary`), `custom` (with a `command`), or `builtin` (the bundled pure-Python transform — no Node required). Re-run after editing any `../tokens/*.json` source file. `manifest.json` records `exportsGenerated`, `exportsAt`, and `exportsStale`; docs-lint warns when exports are stale.
