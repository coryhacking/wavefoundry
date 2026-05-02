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
python3 .wavefoundry/framework/scripts/build_pack.py
```

## Required Packaging Order

Before the final zip build:

1. Finish the framework changes that should ship in the package.
2. Determine the next package revision using the same rule as `build_pack.py`:
   - date defaults to today unless you intentionally pass `--date`
   - suffix is the next letter after the highest existing suffix for that date in the output directory
3. Run framework script tests:

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py
```

4. Run `python3 .wavefoundry/framework/scripts/build_pack.py` once to stamp `.wavefoundry/framework/VERSION`, rebuild `.wavefoundry/framework/index/`, and create the zip.
5. If the computed revision changes between planning and packaging, rebuild so the zip filename and `.wavefoundry/framework/VERSION` match.
6. After packaging and verification, hand off the diff plus a suggested commit message unless the operator explicitly instructs you to finalize the commit in the current request after reviewing that scope.

## What It Produces

A zip file at the repository root named:

```text
wavefoundry-YYYY-MM-DDx.zip
```

`YYYY-MM-DD` is today's local calendar date in ISO format unless you pass `--date`. `x` is a lowercase letter suffix. The script scans the output directory for existing `wavefoundry-<same-date><letter>.zip` files and picks the letter after the highest suffix already present. It does not backfill lower gaps.

Immediately before building the archive, the script writes `.wavefoundry/framework/VERSION` to a single line `<YYYY-MM-DD><letter>`, the same string embedded in the zip filename between `wavefoundry-` and `.zip`. It also rebuilds `.wavefoundry/framework/index/`, a packaged semantic index for the canonical framework docs and seeds, so target repositories do not need to re-embed the framework corpus after install or upgrade.

## Options

| Flag | Meaning |
| --- | --- |
| `--output <dir>` | Write the zip to `<dir>` instead of the repository root. The directory must already exist. |
| `--date <YYYY-MM-DD>` | Use this date instead of today for the filename, `VERSION` stamp, and suffix scan. Use this for tests or exceptional re-builds only; normal packaging should rely on today's date. |
| `--skip-framework-index` | Skip rebuilding `.wavefoundry/framework/index/`. Use only for emergency packaging when index dependencies are unavailable and the operator accepts that target repositories will rebuild framework search locally. |

## Examples

```bash
# Default: write to repo root with today's date
python3 .wavefoundry/framework/scripts/build_pack.py

# Write to a staging directory
python3 .wavefoundry/framework/scripts/build_pack.py --output ~/Desktop

# Build under a specific date, for example to re-issue a named release
python3 .wavefoundry/framework/scripts/build_pack.py --date 2026-04-10
```

## Zip Layout

Every entry inside the zip begins with `.wavefoundry/framework/`, so extracting with:

```bash
unzip -o wavefoundry-YYYY-MM-DDx.zip -d <repo-root>
```

restores files to `.wavefoundry/framework/` inside the target repository root.

In target repositories, run the **Upgrade wave framework** prompt after unpacking to apply post-unpack reconciliation steps.

## Excluded From The Zip

- `__pycache__/` directories
- `.pytest_cache/` directories
- `*.pyc` files
- `.DS_Store` files
- `scripts/tests/tmp/` directories

`.wavefoundry/framework/index/` is intentionally included when present. It is generated during packaging and tied to the packaged framework version.

`.wavefoundry/framework/MANIFEST` is always included. It lists every file delivered by the pack (one path per line, relative to `.wavefoundry/framework/`). The upgrade workflow saves the old MANIFEST before `unzip` and then runs `prune_framework.py --old-manifest` to delete files that were in the old pack but absent from the new one. Only pack-delivered files are ever pruned — user-created files (locally regenerated indexes, local overrides) are never listed in any MANIFEST and are never touched.

## When To Use

Run `Package Wavefoundry` when you want to snapshot the current canonical framework source for distribution, transfer, archival, or rollback before experimental framework changes.

Target-repository install and upgrade behavior is a separate concern. Wavefoundry packages the canonical `framework/` source; install and upgrade tooling may later translate that source into rendered project-local surfaces.
