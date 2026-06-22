# Spacing

Owner: Engineering
Status: active
Last verified: 2026-06-22

Extracted from `.wavefoundry/framework/dashboard/dashboard.css` (`1p6z6-enh`). Tokens: `space.*` in `tokens/primitives.tokens.json` and `tokens/semantic.tokens.json`.

## Scale

Seven-step rem-based scale (not re-themed across modes).

| Token | Semantic | Value | Typical use |
|---|---|---|---|
| `--space-1` | `space.1` | `0.25rem` | Smallest gap / padding |
| `--space-2` | `space.2` | `0.5rem` | Badge padding, small gap |
| `--space-3` | `space.3` | `0.75rem` | Timeline item padding, section gap |
| `--space-4` | `space.4` | `1rem` | Compact card padding |
| `--space-5` | `space.5` | `1.5rem` | Default panel padding, section gap |
| `--space-6` | `space.6` | `2rem` | Hero card padding |
| `--space-7` | `space.7` | `3rem` | Page bottom margin |

## Layout constants (primitive-only)

Layout dimensions are extracted as `layout.*` primitives (no semantic role yet — see `gaps.md` G3):

| Token | Value | Use |
|---|---|---|
| `--rail-w` | `56px` | Collapsed sidebar icon-rail width |
| `--view-max` | `1760px` | Contained view max-width |
| `--view-max-wide` | `1760px` | Wide view max-width (Graph canvas) |
