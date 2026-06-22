# Radius

Owner: Engineering
Status: active
Last verified: 2026-06-22

Extracted from `.wavefoundry/framework/dashboard/dashboard.css` (`1p6z6-enh`). Tokens: `radius.*` in `tokens/primitives.tokens.json` and `tokens/semantic.tokens.json`. Not re-themed across modes.

| Token | Semantic | Value | Use |
|---|---|---|---|
| `--radius-sm` | `radius.sm` | `4px` | Chips, code badges, table cells, focus ring |
| `--radius-md` | `radius.md` | `6px` | Metric tiles, timeline items, wave cards, mini-graphs |
| `--radius-lg` | `radius.lg` | `8px` | Hero card, full panels, agent dialog |

Pill shapes (progress track/fill, some pills) use `border-radius: 999px` directly rather than a token — an intentional non-tokenized "fully rounded" value, not a gap.
