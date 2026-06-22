# Elevation

Owner: Engineering
Status: active
Last verified: 2026-06-22

Extracted from `.wavefoundry/framework/dashboard/dashboard.css` (`1p6z6-enh`). Tokens: `shadow.*` primitives in `tokens/primitives.tokens.json`, semantic `elevation.*` in `tokens/semantic.tokens.json`. Re-themed in dark mode (darker, higher-opacity shadows).

| Token | Semantic | Light | Dark | Use |
|---|---|---|---|---|
| `--shadow-sm` | `elevation.sm` | `0 1px 3px rgba(33,37,41,.10)` | `0 2px 8px rgba(0,0,0,.35)` | Hover lift on metrics and wave cards |
| `--shadow` | `elevation.base` | `0 1px 4px rgba(33,37,41,.12), 0 2px 8px rgba(33,37,41,.07)` | `0 8px 24px rgba(0,0,0,.50), 0 1px 3px rgba(0,0,0,.30)` | Default panel elevation |
| `--shadow-lg` | `elevation.lg` | `0 4px 16px rgba(33,37,41,.14), 0 1px 4px rgba(33,37,41,.08)` | `0 20px 48px rgba(0,0,0,.65), 0 2px 8px rgba(0,0,0,.40)` | Modal / dialog overlay |

All three shadow tokens diverge between light and dark — captured in `tokens/modes/{light,dark}.tokens.json`. Several dark-mode component cards (`.hero-card`, graph cards) hardcode bespoke shadows instead of the tokens (see `gaps.md` G2).
