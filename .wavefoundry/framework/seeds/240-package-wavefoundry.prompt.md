# Package Wavefoundry Prompt

Owner: Engineering
Status: active
Last verified: 2026-06-01

## Purpose

Shortcut prompt for building a semver distribution zip of Wavefoundry's canonical `framework/` tree from the current repository state.

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
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH
```

## Required Packaging Order

Before the final zip build:

1. Finish the framework changes that should ship in the package.
2. Determine the release version using the semver bump policy:
   - choose `MAJOR.MINOR.PATCH`
   - use the rightmost 4 characters of the current lifecycle prefix as the build suffix; `build_pack.py` derives it automatically
3. Run framework script tests:

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py
```

4. **Update `.wavefoundry/CHANGELOG.md`** — the operator-visible release history that ships with the zip at the project-level path. Sections are structured **by version, not by build**. Decide which case applies:

   - **Semver bumps from the prior release** (e.g., `1.2.0` → `1.2.1`, `1.2.1` → `1.3.0`): **prepend a new section** at the top. Header format `## MAJOR.MINOR.PATCH — YYYY-MM-DD`. The section is **cohesive narrative prose** — what the version delivers to operators, not when each piece landed. Cover the headline change, any action required on upgrade (`GRAPH_BUILDER_VERSION` bumps, MCP server restart needs, breaking changes with migration guidance), and a one-line wave reference for full per-change docs. Read the prior release's section for shape; mirror it.

   - **Semver unchanged, only the build number changes** (e.g., re-packaging `1.2.1+3134` as `1.2.1+3137`): **rewrite that version's section** as cohesive narrative covering the most important points across all builds of the version. Do NOT append a delta-style "build XXX added Y" log. Do NOT add a per-build subsection. The section should read as a unified story for the release.

   **Quality criteria for every section:**

   - **Operator impact, not chronology.** Describe what the version *delivers* to the operator (capabilities, fixes, breaking changes, required actions), not when each piece landed.
   - **No build numbers in the file.** Build numbers (`+XXXX`) live in git history, the `VERSION` file, and the dist zip filename. They do NOT appear in `CHANGELOG.md` — not as sub-sections, not as footers, not inline. The structural unit is the version.
   - **Required-action callouts are explicit.** Cache invalidation (`GRAPH_BUILDER_VERSION` bumps), MCP server restart needs, breaking changes get their own sub-section or callout — operators reading the section must be able to skim and find "do I need to do anything?" without parsing prose.
   - **Wave reference at the end.** "Full per-change docs: wave `<wave-id>`." One line; traceability into the wavefoundry repo.
   - **NOT Keep-a-Changelog format.** The community `CHANGELOG.md` convention often prescribes structured `Added / Changed / Deprecated / Removed / Fixed / Security` sub-sections. Wavefoundry deliberately departs — sections are cohesive narrative prose per version, not delta categories.

   **Do not skip this step** — `CHANGELOG.md` is the only release surface that travels with the package.

   `build_pack.py` emits a diagnostic warning when a version section looks chronological (heuristic: more than two `build` occurrences inside the section body, or any `+XXXX` build-number reference). Address the warning before packaging; if the warning is a false positive, document the rationale in your commit message.

5. Ensure `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches the packaged revision unless you intentionally use `--skip-manifest-check`.
6. Run `python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH` once to stamp `.wavefoundry/framework/VERSION`, update `.wavefoundry/framework/index/`, compact the LanceDB tables, and create the zip.
7. Review the produced zip name and stamped `VERSION` for consistency. Spot-check that `CHANGELOG.md` is in the zip (`unzip -l <zip> | grep CHANGELOG`) and that the latest section matches the version just stamped.
8. After packaging and verification, hand off the diff plus a suggested commit message unless the operator explicitly instructs you to finalize the commit in the current request after reviewing that scope.

## What It Produces

A zip file under `~/.wavefoundry/dist/` by default (or `--output <dir>`) named:

```text
wavefoundry-MAJOR.MINOR.PATCH.<build>.zip
```

`MAJOR.MINOR.PATCH` is the required semver release version passed via `--version`. `<build>` is the rightmost 4 characters of the lifecycle prefix generated by `lifecycle_id.py --prefix-only`.

Immediately before building the archive, the script writes `.wavefoundry/framework/VERSION` to `MAJOR.MINOR.PATCH+<build>` and expects `docs/prompts/prompt-surface-manifest.json` `framework_revision` to match the same revision unless `--skip-manifest-check` is explicitly used. It also updates and compacts `.wavefoundry/framework/index/`, a packaged semantic index for the canonical framework docs and seeds, so target repositories do not need to re-embed the framework corpus after install or upgrade.

## Options

| Flag | Meaning |
| --- | --- |
| `--version <MAJOR.MINOR.PATCH>` | Required semver release version for the package. |
| `--output <dir>` | Write the zip to `<dir>` instead of `~/.wavefoundry/dist/`. The directory must already exist. |
| `--skip-framework-index` | Skip updating and compacting `.wavefoundry/framework/index/`. Use only for emergency packaging when index dependencies are unavailable and the operator accepts that target repositories will build framework search locally. |
| `--skip-manifest-check` | Skip the `framework_revision` consistency check. Use only when the manifest is intentionally out of sync. |
| `--skip-docs-gate` | Skip the docs-gardener / docs-lint pre-flight gate. Exceptional use only. |
| `--skip-changelog-diagnostic` | Skip the chronological-section diagnostic on `CHANGELOG.md`. Use only when the warning is a known false positive. |
| `--verbose` / `-v` | Print index build progress during packaging. |

## Examples

```bash
# Default: write to ~/.wavefoundry/dist/
python3 .wavefoundry/framework/scripts/build_pack.py --version 1.0.0

# Write to a staging directory
python3 .wavefoundry/framework/scripts/build_pack.py --output ~/Desktop

# Write to a staging directory
python3 .wavefoundry/framework/scripts/build_pack.py --version 1.0.0 --output ~/Desktop
```

## Zip Layout

Most entries inside the zip begin with `.wavefoundry/framework/`. Two project-level entries sit outside the framework directory:

- `.wavefoundry/README.md` — project-owner orientation doc.
- `.wavefoundry/CHANGELOG.md` — operator-visible release history (canonical at the project level, not framework-internal).

Extracting with:

```bash
unzip -o wavefoundry-MAJOR.MINOR.PATCH.<build>.zip -d <repo-root>
```

restores files to their respective paths inside the target repository root.

In target repositories, run the **Upgrade wave framework** prompt after unpacking to apply post-unpack reconciliation steps. For normal operator flows, leave semver packs in the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/` and let the upgrade workflow adopt the highest semver zip automatically.

**Migration note (one-time, when upgrading FROM a pre-relocation pack):** earlier packs shipped `RELEASE_NOTES.md` at `.wavefoundry/framework/RELEASE_NOTES.md` (framework-internal). The MANIFEST-based prune step removes the old path during upgrade; the new `CHANGELOG.md` lands at `.wavefoundry/CHANGELOG.md`. Consumer projects do not edit either file — it's a wavefoundry-managed snapshot of release history.

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
