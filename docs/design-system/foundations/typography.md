# Typography

Owner: Engineering
Status: active
Last verified: 2026-06-22

Extracted from `.wavefoundry/framework/dashboard/dashboard.css` (`1p6z6-enh`). Tokens: `font.*` in `tokens/primitives.tokens.json`, semantic `font.*` in `tokens/semantic.tokens.json`.

## Font families

| Token | Semantic | Stack | Use |
|---|---|---|---|
| `--font-body` | `font.body` | `-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif` | Body text, meta labels |
| `--font-heading` | `font.heading` | (identical system-sans stack to body) | Panel h2, metric values, dialog title |
| `--font-mono` | `font.mono` | `ui-monospace, "SF Mono", "Cascadia Code", "Fira Code", "Consolas", monospace` | IDs, version strings, code, framework label |

`--font-heading` resolves to the same system-sans stack as `--font-body` in the shipped CSS (no separate display/serif face). The base `html` font-size is `106.25%` (~17px), so all `rem` sizes scale proportionally. Body `line-height: 1.5`.

## Type scale

There are no dedicated font-size tokens; sizes are raw `rem` values applied per role. See `foundations/dashboard.md` → Typography for the role/size/weight table (panel heading `1.1rem/700`, metric value `2rem/800`, body/table `0.92rem/400`, eyebrow `0.72rem/700 uppercase`, etc.).

## Gap

A dedicated font-size / line-height / weight token scale is **not present in source** (sizes are inline per rule) — `$value: null` for any such scale; not invented here.
