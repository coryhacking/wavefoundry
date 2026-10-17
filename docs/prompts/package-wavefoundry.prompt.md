# Package Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-10-17

Shortcut: **`Package Wavefoundry`** | Legacy: **`Package wave framework`** / **`Package wave context`**

## Purpose

Build the semver Wavefoundry feature package and its optional, independently
versioned model-set asset. An optional combined ZIP embeds that same model asset
and can be used directly for upgrades. The lean package remains available.

## Run

From the repository root:

```bash
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH

# Local non-release builds may omit models. Release modes always include them.
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH --with-models
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH --with-models --release-dry-run
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH --with-models --release

# Additional directly upgradeable ZIP, plus the lean ZIP and standalone models.
python3 .wavefoundry/framework/scripts/build_pack.py --version MAJOR.MINOR.PATCH --with-embedded-models
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

5. Consume the current default qualification (or run the full suite if its receipt is stale):

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py --qualification-report .wavefoundry/cache/qualification/default.json
```

   Then qualify the compatibility inventory under the second vocabulary and layout profile. This uses the existing temporary profile fixture and never writes the source test receipt:

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py --qualify-profile second --qualification-report .wavefoundry/cache/qualification/second.json
```

   Every selected file must pass; a skip beyond the matching default workers' skips must come from a test marked `default_profile_only`. This run is a release check, not delivery evidence for a wave. Then run `python3 -B .wavefoundry/framework/scripts/run_tests.py --qualify-profile declared --qualification-report .wavefoundry/cache/qualification/declared.json` the same way, which qualifies the compatibility inventory with a sample distribution tool declaration (a plain and a parameter-mapped alias) and must pass with the same exact skip IDs and reasons as the matching default workers.

   The reviewed file-level inventory is `tests/fixtures/profiles/qualification/coverage.json` under the scripts folder. Initially only `test_check_version.py` is proven independent; every other file remains required or uncertain (186 of 187 workers per profile). Unknown workers, changed profile assets, changed pinned dependencies or invalid claims automatically expand to the full profile. This is deliberately a small first reduction; the main immediate saving is reusing the default run. `--profile NAME` remains the full reference run, while `--file` remains diagnostic and cannot satisfy this comparison. After a substantive coverage expansion, qualify its claims against one full reference matrix and bounded negative controls; do not run a second almost-identical matrix just to restamp selected observations.

   Compare the execution-origin reports with the deterministic reader:

```bash
python3 -B .wavefoundry/framework/scripts/qualification_report.py --compare .wavefoundry/cache/qualification/default.json .wavefoundry/cache/qualification/second.json --profile second
python3 -B .wavefoundry/framework/scripts/qualification_report.py --compare .wavefoundry/cache/qualification/default.json .wavefoundry/cache/qualification/declared.json --profile declared
```

   `--release` and `--release-dry-run` require these three reports: as the last preflight step, before the docs gate or any build, they refuse unless `default.json` passes, is a full run and carries the current framework inputs hash, and `second.json` and `declared.json` each pass `qualification_report.py --compare` against it. The hash is checked again just before the build. A failing but current, complete and well-formed `second` or `declared` report can ship only with `--accept-qualification-exception PROFILE=REASON` (one line, at most 500 characters, once per profile; never for `default`, and never for a missing, stale or malformed report). The release notes gain a `### Qualification` section listing each profile's result and any accepted exception with its reason. The gate prevents accidents and is not an attestation: any process running as you can write these reports. Reports are otherwise release evidence only: one bounded report per requested run, with worker return codes, exact executed skip IDs/reasons and completeness; no transcripts or copied source. Paths must be under the repository's `.wavefoundry/cache/qualification/`, outside framework hashing and the packed payload. Linked, special, protected and unowned existing targets are refused; owned reports are replaced atomically. Complete successful default runs automatically retain one bounded `last-default.json` in this ignored cache. A current green cache hit can reuse that report at the requested output path only when its source identity and discovered worker inventory match exactly; otherwise it reports unavailable executed detail. It never launches workers on a cache hit or reconstructs detail from aggregate counts. Focused, profile, schedule-control and unsuccessful runs preserve the last-successful default detail; optional retention failures are reported separately from the canonical receipt. If exact detail is required, explicitly authorize and run `--no-cache --qualification-report ...` for the default suite. Profile reports export the actual applied profile and original source identities before cleanup and never write the source framework receipt. Missing, duplicate, malformed, contradictory or reason-changed evidence fails comparison. Consumer upgrades never invoke this facility.

6. **Update root `CHANGELOG.md`** — the canonical release history. The wavefoundry repo's root `CHANGELOG.md` is the single source of truth; `build_pack.py` copies it into the pack zip at `.wavefoundry/CHANGELOG.md` so consumer projects receive an in-tree changelog on every upgrade (offline-readable, MCP-indexable, no GitHub fetch required). The wavefoundry repo does NOT carry `.wavefoundry/CHANGELOG.md` — root is the only place release history is maintained.

   **Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).** Each release uses `## [MAJOR.MINOR.PATCH]` (date filled in at release time) with `### Added / Changed / Deprecated / Removed / Fixed / Security` subsections. Bullets are git-commit-message-style — terse, operator-impact-focused, not chronological. Two cases:

   - **Semver bumps** (e.g., `1.2.0` → `1.2.1`): prepend a new `## [MAJOR.MINOR.PATCH]` section; group bullets under the appropriate subsection.
   - **Semver unchanged, only build changes** (re-packaging a release with a fresh build): append bullets to the current open section under the appropriate subsection. No build numbers in the file — `+XXXX` lives in git history, the `VERSION` file, and the dist zip filename, not the changelog.

   **Quality criteria:** operator impact (not chronology); required-action callouts surfaced as standalone bullets (cache invalidation, `GRAPH_BUILDER_VERSION` bumps, MCP server restart needs, breaking changes with migration guidance); each bullet ends with the owning wave/change for traceability (e.g., "Wave 1p3dk / 1p3ho.").

   **Do not skip this step** — `CHANGELOG.md` is the only release surface that travels with the package and the only place an offline consumer can read what just changed. **Changelog-first is mechanically enforced:** `build_pack.py` refuses ANY versioned build — test builds included — when `CHANGELOG.md` has no `## [MAJOR.MINOR.PATCH]` section for the version being built, and refuses a build whose packed section carries a version-constant claim (`CHUNKER_VERSION` / `WALKER_VERSION` / `GRAPH_BUILDER_VERSION`) that does not match the live code constant (wave `1wip2`; the docs gate runs the same claims engine over the `[Unreleased]` top section only, so dated release history is never checked). Create the entry (a skeleton is fine early in a cycle) before the first pack; keep it current as changes land.

   **Changelog completeness and amendments:** the entry must be COMPLETE — covering every landed change for the version — before the final pack that goes out for field testing, so the archive's internal changelog matches what ships. If the changelog is amended after a pack was built (late fixes, post-test additions), rebuild before publishing: a released zip must never carry a stale internal changelog. When only the changelog changed, the rebuild differs from the tested archive in that one file, which keeps ship-what-you-tested honest. For the actual publish, prefer `build_pack.py --release`: its preflight requires a clean tree on `main` with the matching changelog section and then builds fresh, so the uploaded archive cannot lag the repo.
   - Also list every sensor registered `advisory` without a `decided_wave` in `.wavefoundry/framework/scripts/wave_lint_lib/constants.py` (`SENSOR_POLARITY_REGISTRY`) with its introducing wave, and decide each; a flip to `blocking`, or a decision to keep it advisory, is a recorded change in a later wave, never a release-day edit. Entries with a `decided_wave` are settled and are not re-raised.
7. Ensure `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches the packaged revision unless you intentionally use `--skip-manifest-check`.
8. Run the packaging command once. It stamps `.wavefoundry/framework/VERSION` and creates the lean `wavefoundry-<version>.zip`. With `--with-embedded-models`, it also creates `wavefoundry-<version>.with-models.zip` with the same framework bytes and build identity. Both carry the executable upgrade entry. No framework index is built or shipped (framework seeds fold into each project's docs index at setup/upgrade).
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

- Every pack carries `.wavefoundry/framework/BUILD-PROVENANCE.json` with exactly `schema_version`, `release_version`, `build_id`, `source_commit` (the 40-hex `HEAD` it was built from, or `null` outside its own checkout), `source_tree_clean` (gardener output makes it false) and `release_tag` (`vX.Y.Z` under `--release` only). In a release, `source_commit` is the parent of the stamp commit the tag points at. The file is removed from the source tree after every build.
- `--release` also uploads `SHA256SUMS`, one `<sha256>  <filename>` line per asset, written outside the repository and the output folder; `--release-dry-run` prints those lines. A failed upload keeps the notes and `SHA256SUMS` and names both in the recovery command. The checksums let a consumer check a download against the same release; they are not a signature.

- `MAJOR.MINOR.PATCH` is the required semver release version passed via `--version`.
- `<build>` is a standalone 4-character base36 pure-time build suffix (5-minute buckets on a pinned build epoch), computed automatically by `build_pack.py` — independent of the lifecycle-ID policy.
- `VERSION` is stamped to `MAJOR.MINOR.PATCH+<build>` before zip creation, and manifest `framework_revision` must match unless `--skip-manifest-check` is used.
- Optional `wavefoundry-MAJOR.MINOR.PATCH.<build>.with-models.zip` contains the same framework and one byte-exact standalone model ZIP under `payload/models/`, described by `payload/models.json`.
- Discovery accepts lean and combined variants, preferring lean when both have the same version/build. Existing ordering between distinct builds is unchanged; an explicit pack path selects that exact variant.
- The `wavefoundry-models-*` asset is never independently selected as a framework upgrade. It contains only validated model sources, provenance, hashes, attribution, and license notices. The selected feature ZIP declares the required model-set version; upgrade locates that exact asset in its standard distribution directories and setup rejects a set that does not match the declaration.

## Options

- `--version <MAJOR.MINOR.PATCH>`: required semver release version.
- `--output <dir>`: write zip to an existing directory instead of `~/.wavefoundry/dist/`.
- `--skip-manifest-check`: skip the `framework_revision` consistency check.
- `--skip-docs-gate`: skip the docs-gardener / docs-lint pre-flight gate.
- `--accept-qualification-exception PROFILE=REASON`: release modes only; publish despite a failing, current `second` or `declared` report and record REASON in the release notes.
- `--verbose` / `-v`: print index build progress.
- `--with-models`: build the declared offline model-set asset from the warmed
  local model cache. It never downloads missing model files during packaging.
  Required with `--release` and `--release-dry-run`; optional for non-release
  local builds.
- `--with-embedded-models`: implies `--with-models` and additionally builds the combined ZIP. With either release mode, the declared asset set is lean, combined and standalone models. It uses the warmed cache and never downloads models during packaging.

## Operator Recovery When Model Download Is Unavailable

If `wf setup` cannot download a required model, first retry the same command when network access is available. When that is not possible, the operator can manually obtain the exact `wavefoundry-models-<set>.zip` asset from the same release (or an approved internal distribution), leave it zipped, and place it in the target repository root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`. Rerun `wf setup`; it discovers only the exact declared model-set asset and validates the model set, component hashes, and licenses before replacing the cache. An invalid archive does not replace a verified cache.

## Upgrade Path Coverage

After packaging, target repositories should consume the pack via **Upgrade Wavefoundry** so the upgrade flow can:

- adopt the highest semver `wavefoundry-*.zip` from the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/` (Step 0),
- regenerate host surfaces (`.cursor/mcp.json`, `.mcp.json`, `.junie/mcp/mcp.json`) through `wf render-surfaces`,
- keep the cross-OS `wf` / `wf.cmd` dispatcher (and its `wf docs-lint` / `wf docs-gardener` subcommands) aligned with the packaged scripts,
- validate MCP recovery paths (`wf_audit`, `index_build`) plus docs gate.

A supported protocol-1 target consumes the matching executable ZIP after explicit host quiescence; internal bridge pieces remain private build inputs. An existing 1.31.0 runner does not discover the new combined filename automatically. Use the incoming combined ZIP's executable entry after stopping the target's dashboard and attached MCP servers: `python3 <combined.zip> --root <repo> --confirm-hosts-stopped`. Its fresh protocol-2 runner receives the verified retained outer archive. Follow the returned continuation on a pause; do not delete retained upgrade assets.

The combined source is also accepted by setup's `--model-bundle` option. A matching canonical cache avoids embedded extraction and model loading. For optional manual recovery, extract only the declared companion (currently `unzip -p <combined.zip> payload/models/wavefoundry-models-3.zip > wavefoundry-models-3.zip`) and give that ZIP to setup; do not unpack its model files into the repository. Cache reuse verifies canonical component identities and hashes; it does not claim to hash embedded bytes that are never consumed. An invalid declared envelope or consumed payload is refused rather than silently falling back to download.

## Notes

- Zip archives are transport artifacts; do not commit them.
- Use **Upgrade Wavefoundry** (not init) in already-seeded target repositories.
