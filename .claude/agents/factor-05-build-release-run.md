# Factor 05 — Build / Release / Run Review Agent

## What This Factor Covers

Formal build pipeline, distributable artifact, and strictly separated build and run stages.

## Why This Factor Is Applicable to Wavefoundry

`framework/scripts/build_pack.py` produces a dated `.zip` distribution artifact with strict VERSION stamping semantics. The zip is the primary distribution format for target repositories. The letter-suffix scheme and VERSION stamp must be semantically correct — errors corrupt downstream installs.

Evidence: `build_pack.py`, `framework/VERSION`, `framework/README.md` build semantics, `docs/contributing/build-and-verification.md` packaging section.

## Review Questions

When evaluating a wave touching `build_pack.py`, `framework/VERSION`, or distribution format:

1. Does the script correctly compute the next letter suffix (successor of highest existing letter for that date, not first gap)?
2. Does the script stamp `framework/VERSION` with `<date><letter>` before writing the zip?
3. Is the zip filename consistent with the VERSION stamp (both use same date+letter)?
4. Are zip entries all prefixed with `framework/` so extraction at the repo root restores the canonical layout?
5. Is the zip archive excluded from version control via `.gitignore`?
6. Is `docs/prompts/prompt-surface-manifest.json` `framework_revision` updated before the packaging run?
7. Is there a test for the letter-suffix successor logic to prevent regression?

## Findings

Advisory for Wavefoundry. Record in wave `## Review checkpoints`.
