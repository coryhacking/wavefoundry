# Prompt Numbering Philosophy

## Purpose

Explain how the shared Wave Framework uses numbering so the highest-value conceptual docs stay visible at the top of the folder while leaving room for future insertions.

## Core Rules

- Reserve `000` for a future top-of-folder insertion when a new framework entry doc becomes necessary.
- Use zero-padded numeric prefixes so files sort consistently across editors and platforms.
- Keep shared conceptual overview docs in the `001-009` range.
- Keep executable prompt docs in later numeric bands grouped by lifecycle area.
- Prefer inserting into an existing range instead of renumbering the whole pack.

## Current Range Intent

- `001-009`: framework overview and subsystem overviews
- `010-090`: bootstrap, discovery, and generation prompts
- `100-149`: prompt-surface generation, memory bootstrap, and reindex prompts
- `150-169`: update and upgrade prompts
- `170-199`: feature lifecycle prompts
- `200-249`: wave, journal, and migration helper prompts

## Why The Framework Uses This Scheme

- It keeps the conceptual entry docs visible before the operational prompt pack.
- It creates insertion room for future docs without forcing churn across every cross-reference.
- It helps maintainers infer purpose from filename ranges before opening a file.
- It separates overview artifacts from executable prompts while keeping one consistent ordering model.

## Placement Guidance

- Add a new shared overview doc in the lowest unused `00x` slot that matches its importance and relationship to the existing conceptual entry docs.
- Add a new prompt in the numeric band that matches its lifecycle role instead of creating a one-off number outside the current range model.
- Only use renumbering when the information architecture has materially changed and the benefit clearly outweighs link churn.

## Related Docs

- `.wavefoundry/framework/README.md`
- `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`
- `.wavefoundry/framework/seeds/002-wave-framework-seeding-overview.md`