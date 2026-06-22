# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-06-22

wave-id: `1p79y factor-surface-integrity`
Title: Factor Surface Integrity

## Objective

Close the silent-breakage gap in the factor-review agent surface that downstream field feedback exposed: make `docs-lint` detect an `applicable` factor missing its canonical `docs/agents/factor-<nn>-<name>.md` (or a `.claude/agents/factor-*.md` wrapper without a source / without frontmatter), stop the Config Review (`seed-238`) from giving advice that contradicts the `seed-050` generation contract, and have Upgrade (`seed-160`) repair a drifted factor surface. When this closes, a wrappers-without-sources / frontmatter-less factor surface becomes an actionable gate finding instead of passing clean.

## Changes

Change ID: `1p79x-enh factor-surface-integrity`
Change Status: `planned`

## Wave Summary

One change (`1p79x-enh`): a `factor_review`-keyed "declared-but-missing" validator in `wave_lint_lib/wave_validators.py` (canonical-source existence + orphan-wrapper + wrapper-frontmatter checks, replacing the static 4-factor list), reconciliation of `seed-238` (treat factor docs as a governed canonical+wrapper pair, not orphans to relocate), a merge-safe `seed-160` factor-surface backfill (regenerate missing canonical from the `seed-050` template + re-render wrappers), and a `render_platform_surfaces.py` factor-wrapper frontmatter audit. Reuses the `1p799` external-reference declared-but-missing pattern.

## Journal Watchpoints

- **From downstream field feedback** (Java-agent consumer, pack `1.8.0+p79p`); a **pre-existing** gap (~1.6.x onward), independent of the closed `1p75h`. All three reported issues were verified against the code before planning.
- **Sequencing watchpoint (highest-leverage first):** the validator (`#1`) is the anchor — it converts silent breakage into a gate finding that drives the `seed-238` (`#2`) and `seed-160` (`#3`) fixes. This ordering is **blocking**: land the validator contract before the seed text references it (serialization point).
- **Self-hosting guard (blocking watchpoint):** replacing the static `_AGENT_ROLE_REQUIRED_PATHS` factor list with a `factor_review`-keyed check must NOT regress this repo's own surface — confirm wavefoundry's `factor_review` marks `03/05/12/13` applicable and their canonical docs exist (AC-4).
- **Merge-safe backfill:** `seed-160` regenerates a canonical factor doc only when **absent**; never overwrite operator-refined content.
- **Vendor-neutrality guard:** new test fixtures must introduce no external-project names (`aceiss`/`teton`/`solaris` grep stays 0).
- **Gates:** `framework_edit_allowed` for `wave_validators.py` + renderer + tests; `seed_edit_allowed` for `seed-238`/`seed-160`/`seed-050`.

## Review Evidence

- operator-signoff: approved when operator confirms closure

## Dependencies

- No external wave dependencies. Reuses the `1p799` (closed `1p75h`) declared-but-missing validation pattern as a template.
