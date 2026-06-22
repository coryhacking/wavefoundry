# Color

Owner: Engineering
Status: active
Last verified: 2026-06-22

Extracted from `.wavefoundry/framework/dashboard/dashboard.css` (`1p6z6-enh`). Tokens: `tokens/primitives.tokens.json` (`color.*`), semantic roles in `tokens/semantic.tokens.json`, per-mode values in `tokens/modes/{light,dark}.tokens.json`.

## Palette (light / dark)

| Token | Semantic role | Light | Dark |
|---|---|---|---|
| `--page-bg` | `color.surface.page` | `#F8F9FA` | `#111214` |
| `--panel-bg` | `color.surface.panel` | `#FFFFFF` | `#151719` |
| `--panel-border` | `color.surface.border` | `#DEE2E6` | `#3a4150` |
| `--ink` | `color.ink.primary` | `#212529` | `#e4e2de` |
| `--muted` | `color.ink.muted` | `#6C757D` | `#8a929e` |
| `--accent` | `color.accent.base` | `#1976d2` | `#40A3E9` |
| `--accent-soft` | `color.accent.soft` | `#E3F0FC` | `#0a1a2e` |
| `--accent-mid` | `color.accent.mid` | `#91C2F2` | `#142a48` |
| `--footer-accent` | `color.accent.footer` | `#2B6CB0` | `#7FB2F0` |
| `--warn` | `color.feedback.warn` | `#C25800` | `#e09040` |
| `--warn-soft` | `color.feedback.warnsoft` | `#FEF3E8` | `#2a1a06` |
| `--danger` | `color.feedback.danger` | `#C62828` | `#d86b62` |
| `--danger-soft` | `color.feedback.dangersoft` | `#FFEBEE` | `#2a0f0e` |
| `--neutral` | `color.feedback.neutral` | `#495057` | `#495057` (not re-themed) |
| `--neutral-soft` | `color.feedback.neutralsoft` | `#F1F3F5` | `#22262c` |
| `--draft-color` | `color.feedback.draft` | `#1565C0` | `#7ab0d8` |
| `--draft-soft` | `color.feedback.draftsoft` | `#E3F2FD` | `#0f1e30` |

The palette is cool-neutral (gray surfaces) with a blue action accent. `--neutral` is the only color custom property **not** re-themed in dark mode (its light value carries forward) — recorded in `gaps.md` context and `tokens/modes/dark.tokens.json`.

## Status-color semantics

See `foundations/dashboard.md` → Status Semantics for how `.status-*` classes map lifecycle states to color pairs (accent, neutral, warn, draft, danger, muted).

## Known gaps

- Undefined-but-referenced `--text` / `--border` / `--surface` / `--surface-raised` color family — `gaps.md` G1.
- Hardcoded agent-role brand palette + per-component dark hex overrides bypass tokens — `gaps.md` G2.
