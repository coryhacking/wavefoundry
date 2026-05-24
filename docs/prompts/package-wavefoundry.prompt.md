# Package Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-05-23

Shortcut: **`Package Wavefoundry`** | Legacy: **`Package wave framework`** / **`Package wave context`**

## Purpose

Build a semver distribution zip of the canonical framework tree so other repositories can adopt it through **Upgrade wave framework**. The only exception is the one-time `0.9.0` bridge release, which keeps the old date-style artifact name for legacy adoption while still stamping semver internally.

## Run

From the repository root:

```bash
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH
```

## Required Packaging Order

1. Ensure intended framework changes are already complete.
2. Determine the release version:
   a. Read `.wavefoundry/framework/VERSION` to get the current version.
   b. Run `git log` to list commits since `VERSION` was last changed (use `git log -1 --format="%H" -- .wavefoundry/framework/VERSION` to find that commit, then `git log <hash>..HEAD --oneline`).
   c. Classify the changes against the bump policy in `docs/architecture/decisions/12tm5-adr semver-versioning-contract.md`:
      - **PATCH** — bug fixes, doc corrections, invisible internal changes
      - **MINOR** — new MCP tools, new seeds, new config options, new features (backward-compatible, no operator action needed on upgrade)
      - **MAJOR** — config field removals/renames, directory structure changes, tool/seed removals, Python minimum version bump, anything that breaks an operator who skips the release notes
   d. State the current version, the recommended new version, and the highest-impact change driving the recommendation.
   e. Ask the operator to confirm the version or specify a different one before continuing. Do not proceed to step 3 until the operator confirms.
3. Run framework tests:

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py
```

4. Ensure `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches the packaged revision unless you intentionally use `--skip-manifest-check`.
5. Run the packaging command once. It stamps `.wavefoundry/framework/VERSION`, updates `.wavefoundry/framework/index/` by default, compacts the LanceDB tables, and creates the zip.
6. Review the produced zip name and stamped `VERSION` for consistency.
7. Hand off diff + suggested commit message unless the operator explicitly asks to finalize the commit in this request.

## Output

The command writes a zip under `~/.wavefoundry/dist/` by default:

```text
wavefoundry-MAJOR.MINOR.PATCH.<build>.zip
```

- `MAJOR.MINOR.PATCH` is the required semver release version passed via `--version`.
- `<build>` is the rightmost 4 characters of the lifecycle prefix generated automatically by `lifecycle_id.py --prefix-only`.
- `VERSION` is stamped to `MAJOR.MINOR.PATCH+<build>` before zip creation, and manifest `framework_revision` must match unless `--skip-manifest-check` is used.
- **Bridge exception:** when `--version 0.9.0` is used, the artifact keeps the old date-style name (`wavefoundry-YYYY-MM-DDx.zip`) so legacy pre-semver upgrade flows can adopt it by filename. The internal stamped `VERSION` and manifest revision remain `0.9.0+<build>`.

## Options

- `--version <MAJOR.MINOR.PATCH>`: required semver release version.
- `--output <dir>`: write zip to an existing directory instead of `~/.wavefoundry/dist/`.
- `--skip-framework-index`: skip updating and compacting `.wavefoundry/framework/index/` (emergency use only).
- `--skip-manifest-check`: skip the `framework_revision` consistency check.
- `--skip-docs-gate`: skip the docs-gardener / docs-lint pre-flight gate.
- `--verbose` / `-v`: print index build progress.

## Upgrade Path Coverage

After packaging, target repositories should consume the pack via **Upgrade wave framework** so the upgrade flow can:

- adopt the highest semver `wavefoundry-*.zip` from the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/` (Step 0), with the one-time `0.9.0` bridge pack still using the old date-style artifact name at repository root for legacy adoption,
- regenerate host surfaces (`.cursor/mcp.json`, `.mcp.json`, `.junie/mcp/mcp.json`) through `render_platform_surfaces.py`,
- keep `.wavefoundry/bin/docs-lint` and `.wavefoundry/bin/docs-gardener` aligned with the packaged scripts,
- validate MCP recovery paths (`wave_audit`, `wave_index_build`) plus docs gate.

## Notes

- Zip archives are transport artifacts; do not commit them.
- Use **Upgrade wave framework** (not init) in already-seeded target repositories.
