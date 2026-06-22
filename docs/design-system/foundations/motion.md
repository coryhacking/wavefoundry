# Motion

Owner: Engineering
Status: active
Last verified: 2026-06-22

Reviewed against `.wavefoundry/framework/dashboard/dashboard.css` (`1p6z6-enh`).

## Token status: null (no motion tokens in source)

There are **no** duration or easing CSS custom properties defined in `:root` or any theme block. Per the "extract, don't invent" rule, no motion tokens are fabricated and `tokens/motion.tokens.json` is left unpopulated (`null` values where a future scale would sit).

Motion in the dashboard is applied inline per rule, not via tokens — e.g.:

- `transition: width 0.6s cubic-bezier(0.4,0,0.2,1)` (progress fill).
- `transition: flex-basis 0.15s ease, width 0.15s ease` (sidebar collapse/expand).
- `transition: border-color 0.15s, box-shadow 0.15s` (cards).
- `pulse` keyframe, `2.4s` (live state dot).

## Gap

A tokenized motion scale (durations + easing curves) is **absent from source**. Not invented here. If `tokens/motion.tokens.json` is later populated with non-null values, the Split B reduced-motion validator requires `foundations/media-motion.md` to also carry reduced-motion fallback guidance.
