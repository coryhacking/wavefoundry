# Package Wavefoundry Prompt

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Purpose

Shortcut prompt for building a dated distribution zip of Wavefoundry's canonical `framework/` tree from the current repository state.

## Terminology

Packaging is not upgrade/adoption.

- If the operator asked to upgrade a target repository from an existing package, stop and route to the target repository's upgrade workflow. Do not build a new zip as a substitute.
- Run packaging only when the operator explicitly asked to package or cut a distribution with `Package Wavefoundry`.

## Trigger Phrases

- `Package Wavefoundry`
- `Package wavefoundry`
- `Package wave framework` (legacy alias)
- `Package wave context` (legacy alias)

## Task

Run this from the Wavefoundry repository root:

```bash
python3 framework/scripts/build_pack.py
```

## Required Packaging Order

Before the final zip build:

1. Finish the framework changes that should ship in the package.
2. Determine the next package revision using the same rule as `build_pack.py`:
   - date defaults to today unless you intentionally pass `--date`
   - suffix is the next letter after the highest existing suffix for that date in the output directory
3. Run framework script tests:

```bash
python3 -B framework/scripts/run_tests.py
```

4. Run `python3 framework/scripts/build_pack.py` once to stamp `framework/VERSION` to the computed revision and create the zip.
5. If the computed revision changes between planning and packaging, rebuild so the zip filename and `framework/VERSION` match.
6. After packaging and verification, hand off the diff plus a suggested commit message unless the operator explicitly instructs you to finalize the commit in the current request after reviewing that scope.

## What It Produces

A zip file at the repository root named:

```text
wavefoundry-YYYY-MM-DDx.zip
```

`YYYY-MM-DD` is today's local calendar date in ISO format unless you pass `--date`. `x` is a lowercase letter suffix. The script scans the output directory for existing `wavefoundry-<same-date><letter>.zip` files and picks the letter after the highest suffix already present. It does not backfill lower gaps.

Immediately before building the archive, the script writes `framework/VERSION` to a single line `<YYYY-MM-DD><letter>`, the same string embedded in the zip filename between `wavefoundry-` and `.zip`.

## Options

| Flag | Meaning |
| --- | --- |
| `--output <dir>` | Write the zip to `<dir>` instead of the repository root. The directory must already exist. |
| `--date <YYYY-MM-DD>` | Use this date instead of today for the filename, `VERSION` stamp, and suffix scan. Use this for tests or exceptional re-builds only; normal packaging should rely on today's date. |

## Examples

```bash
# Default: write to repo root with today's date
python3 framework/scripts/build_pack.py

# Write to a staging directory
python3 framework/scripts/build_pack.py --output ~/Desktop

# Build under a specific date, for example to re-issue a named release
python3 framework/scripts/build_pack.py --date 2026-04-10
```

## Zip Layout

Every entry inside the zip begins with `framework/`, so extracting with:

```bash
unzip -o wavefoundry-YYYY-MM-DDx.zip -d <wavefoundry-root>
```

restores files to the canonical source layout.

In target repositories, do not extract this zip directly to the repository root as the final installed layout. Old-layout migration bridges should stage the archive's `framework/` tree under `.wavefoundry/framework/`, then read `.wavefoundry/framework/seeds/250-migrate-existing-wave-project.prompt.md` for post-unpack migration instructions.

## Excluded From The Zip

- `__pycache__/` directories
- `.pytest_cache/` directories
- `*.pyc` files
- `.DS_Store` files
- `scripts/tests/tmp/` directories

## When To Use

Run `Package Wavefoundry` when you want to snapshot the current canonical framework source for distribution, transfer, archival, or rollback before experimental framework changes.

Target-repository install and upgrade behavior is a separate concern. Wavefoundry packages the canonical `framework/` source; install and upgrade tooling may later translate that source into rendered project-local surfaces.
