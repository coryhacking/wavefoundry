# Package Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-10-03

Shortcut: **`Package Wavefoundry`** | Legacy: **`Package wave framework`** / **`Package wave context`**

## Purpose

Build the semver Wavefoundry feature package and, when the model set has
changed, its independently versioned model-set asset. The feature zip carries the executable
protocol-bridge entry point used by **Upgrade Wavefoundry**; it remains the
only automatically selectable framework-upgrade artifact.

## Run

From the repository root:

```bash
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH

# Local non-release builds may omit models. Release modes always include them.
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH --with-models
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH --with-models --release-dry-run
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH --with-models --release
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
3. Review the uv bootstrap pin: `UV_BOOTSTRAP_REQUIREMENT` in `.wavefoundry/framework/scripts/setup_index.py` is the exact uv that `wf setup` installs only when neither the tool environment nor `PATH` has a uv. When a newer uv release has been public for at least the 21-day package-age window and publishes wheels for Windows, macOS and Linux, bump the pin in this release; otherwise keep it. Bumping `UV_BOOTSTRAP_REQUIREMENT` also replaces `UV_BOOTSTRAP_WHEEL_SHA256` beside it with every `bdist_wheel` entry's `filename` and `digests.sha256` from `https://pypi.org/pypi/uv/<version>/json`; the reviewer confirms the wheel count against the release's file list on PyPI, and the version and hashes change in the same commit (the suite fails on a recorded filename for another version). Keeping the pin keeps the hashes. An existing uv is never replaced.
4. Optional, when network access is available: verify the vendored dashboard scripts against the npm registry:

```bash
python3 -B .wavefoundry/framework/scripts/verify_vendored_scripts.py
```

   A mismatch or missing file (exit 1, which wins over any package that could not be checked), a line labelled `refused:` (a non-registry URL, a redirect that left the registry or a tarball over the size cap, exit 2) or an unparseable vendor README (a missing or repeated table header, a table row that does not match its format, an indented row, a row missing its leading pipe, or a row after a blank line inside a table, exit 2, naming the line) stops the release until it is resolved. When the check cannot be run or cannot reach the registry (a line labelled `download failed:`, exit 2), say so in the release hand-off.

5. Run framework tests:

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py
```

   Then run the suite under the second vocabulary and layout profile, which copies the tree into a temporary repository and never writes the test receipt:

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py --profile second
```

   Every file must pass; a skip beyond the default run's must come from a test marked `default_profile_only`. This run is a release check, not delivery evidence for a wave. Then run `python3 -B .wavefoundry/framework/scripts/run_tests.py --profile declared` the same way, which runs the suite with a sample distribution tool declaration (a plain and a parameter-mapped alias) and must pass with no skips beyond the default run's.

6. **Update root `CHANGELOG.md`** — the canonical release history. The wavefoundry repo's root `CHANGELOG.md` is the single source of truth; `build_pack.py` copies it into the pack zip at `.wavefoundry/CHANGELOG.md` so consumer projects receive an in-tree changelog on every upgrade (offline-readable, MCP-indexable, no GitHub fetch required). The wavefoundry repo does NOT carry `.wavefoundry/CHANGELOG.md` — root is the only place release history is maintained.

   **Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).** Each release uses `## [MAJOR.MINOR.PATCH]` (date filled in at release time) with `### Added / Changed / Deprecated / Removed / Fixed / Security` subsections. Bullets are git-commit-message-style — terse, operator-impact-focused, not chronological. Two cases:

   - **Semver bumps** (e.g., `1.2.0` → `1.2.1`): prepend a new `## [MAJOR.MINOR.PATCH]` section; group bullets under the appropriate subsection.
   - **Semver unchanged, only build changes** (re-packaging a release with a fresh build): append bullets to the current open section under the appropriate subsection. No build numbers in the file — `+XXXX` lives in git history, the `VERSION` file, and the dist zip filename, not the changelog.

   **Quality criteria:** operator impact (not chronology); required-action callouts surfaced as standalone bullets (cache invalidation, `GRAPH_BUILDER_VERSION` bumps, MCP server restart needs, breaking changes with migration guidance); each bullet ends with the owning wave/change for traceability (e.g., "Wave 1p3dk / 1p3ho.").

   **Do not skip this step** — `CHANGELOG.md` is the only release surface that travels with the package and the only place an offline consumer can read what just changed. **Changelog-first is mechanically enforced:** `build_pack.py` refuses ANY versioned build — test builds included — when `CHANGELOG.md` has no `## [MAJOR.MINOR.PATCH]` section for the version being built, and refuses a build whose packed section carries a version-constant claim (`CHUNKER_VERSION` / `WALKER_VERSION` / `GRAPH_BUILDER_VERSION`) that does not match the live code constant (wave `1wip2`; the docs gate runs the same claims engine over the `[Unreleased]` top section only, so dated release history is never checked). Create the entry (a skeleton is fine early in a cycle) before the first pack; keep it current as changes land.

   **Changelog completeness and amendments:** the entry must be COMPLETE — covering every landed change for the version — before the final pack that goes out for field testing, so the archive's internal changelog matches what ships. If the changelog is amended after a pack was built (late fixes, post-test additions), rebuild before publishing: a released zip must never carry a stale internal changelog. When only the changelog changed, the rebuild differs from the tested archive in that one file, which keeps ship-what-you-tested honest. For the actual publish, prefer `build_pack.py --release`: its preflight requires a clean tree on `main` with the matching changelog section and then builds fresh, so the uploaded archive cannot lag the repo.
   - Also list every sensor registered `advisory` without a `decided_wave` in `.wavefoundry/framework/scripts/wave_lint_lib/constants.py` (`SENSOR_POLARITY_REGISTRY`) with its introducing wave, and decide each; a flip to `blocking`, or a decision to keep it advisory, is a recorded change in a later wave, never a release-day edit. Entries with a `decided_wave` are settled and are not re-raised.
7. Ensure `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches the packaged revision unless you intentionally use `--skip-manifest-check`.
8. Run the packaging command once. It stamps `.wavefoundry/framework/VERSION` and creates one self-contained `wavefoundry-<version>.zip`: normally extractable as the feature pack and directly executable for protocol-1→2 upgrades. No framework index is built or shipped (framework seeds fold into each project's docs index at setup/upgrade).
9. Review the feature ZIP, its model-set asset when requested, and stamped `VERSION` for consistency. Spot-check that `CHANGELOG.md` is present in the feature ZIP (`unzip -l <feature-zip> | grep CHANGELOG`), that the latest section matches the version just stamped, and that the model-set manifest declares the intended set version, fingerprint, component revisions, hashes, and licenses. Internal bridge composition files must be removed from `dist/` after assembly.
10. Hand off diff + suggested commit message unless the operator explicitly asks to finalize the commit in this request.

## Output

The default non-release command writes one operator-facing feature package.
`--release` and `--release-dry-run` require `--with-models` and write both the
feature package and independently versioned model-set asset under
`~/.wavefoundry/dist/`:

```text
wavefoundry-MAJOR.MINOR.PATCH.<build>.zip
wavefoundry-models-MODEL.SET.zip
```

- `MAJOR.MINOR.PATCH` is the required semver release version passed via `--version`.
- `<build>` is a standalone 4-character base36 pure-time build suffix (5-minute buckets on a pinned build epoch), computed automatically by `build_pack.py` — independent of the lifecycle-ID policy.
- `VERSION` is stamped to `MAJOR.MINOR.PATCH+<build>` before zip creation, and manifest `framework_revision` must match unless `--skip-manifest-check` is used.
- The feature zip is both the normal feature pack and the protocol-bridge executable. It is the sole `wavefoundry-*.zip` candidate selected by upgrade discovery.
- The `wavefoundry-models-*` asset is never independently selected as a framework upgrade. It contains only validated model sources, provenance, hashes, attribution, and license notices. The selected feature ZIP declares the required model-set version; upgrade locates that exact asset in its standard distribution directories and setup rejects a set that does not match the declaration.

## Options

- `--version <MAJOR.MINOR.PATCH>`: required semver release version.
- `--output <dir>`: write zip to an existing directory instead of `~/.wavefoundry/dist/`.
- `--skip-manifest-check`: skip the `framework_revision` consistency check.
- `--skip-docs-gate`: skip the docs-gardener / docs-lint pre-flight gate.
- `--verbose` / `-v`: print index build progress.
- `--with-models`: build the declared offline model-set asset from the warmed
  local model cache. It never downloads missing model files during packaging.
  Required with `--release` and `--release-dry-run`; optional for non-release
  local builds.

## Operator Recovery When Model Download Is Unavailable

If `wf setup` cannot download a required model, first retry the same command when network access is available. When that is not possible, the operator can manually obtain the exact `wavefoundry-models-<set>.zip` asset from the same release (or an approved internal distribution), leave it zipped, and place it in the target repository root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`. Rerun `wf setup`; it discovers only the exact declared model-set asset and validates the model set, component hashes, and licenses before replacing the cache. An invalid archive does not replace a verified cache.

## Upgrade Path Coverage

After packaging, target repositories should consume the pack via **Upgrade Wavefoundry** so the upgrade flow can:

- adopt the highest semver `wavefoundry-*.zip` from the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/` (Step 0),
- regenerate host surfaces (`.cursor/mcp.json`, `.mcp.json`, `.junie/mcp/mcp.json`) through `wf render-surfaces`,
- keep the cross-OS `wf` / `wf.cmd` dispatcher (and its `wf docs-lint` / `wf docs-gardener` subcommands) aligned with the packaged scripts,
- validate MCP recovery paths (`wf_audit`, `index_build`) plus docs gate.

A protocol-1 / 1.14 target moving to protocol 2 / 1.15 consumes the matching `.pyz` directly after
explicitly stopping attached hosts. The bundle verifies and executes the embedded feature zip in
one invocation; do not publish or instruct the operator to coordinate the internal bridge pieces.

## Notes

- Zip archives are transport artifacts; do not commit them.
- Use **Upgrade Wavefoundry** (not init) in already-seeded target repositories.
