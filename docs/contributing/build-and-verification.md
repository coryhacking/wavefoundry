# Build and Verification

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Verification Commands

Run these from the repository root to verify the Wavefoundry self-hosted surface is healthy:

```bash
# Docs gate (metadata + prompt surface + manifest validation)
./docs-gardener && ./docs-lint

# Framework script tests (no bytecode)
python3 .wavefoundry/framework/scripts/run_tests.py
```

## Docs Gate

`./docs-lint` validates:
- Required prompt docs exist under `docs/prompts/`
- `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches `.wavefoundry/framework/VERSION`
- Required metadata fields (`Owner:`, `Status:`, `Last verified:`) on canonical docs
- Wave and journal root directories exist

`./docs-gardener` refreshes stale metadata timestamps.

Both wrappers forward to `.wavefoundry/framework/scripts/` directly.

## Framework Script Hygiene

Run tests without writing bytecode:

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py
```

Or use the run_tests.py wrapper which already sets `-B`. If `__pycache__` directories appeared anyway, clean them:

```bash
find .wavefoundry/framework/scripts -type d -name '__pycache__' -prune -exec rm -rf {} \;
```

## Wave Framework Pack Upgrade Verification

When a new framework version is available, upgrade using this procedure:

**Bring the pack in:**

Option A (zip drop): Place a `wavefoundry-<date><letter>.zip` at the repository root and run **Upgrade wave framework**. The upgrade seed (`seed-160`) unpacks the lexicographically greatest zip into `.wavefoundry/framework/`, runs `render_platform_surfaces.py`, and continues full reconciliation.

Option B (direct merge): Merge or copy into `.wavefoundry/framework/` then run **Upgrade wave framework**.

**What the unpack step ignores:** archives with other names (e.g. `agent-workflows.zip`) and zips outside the repository root.

**After bringing in the pack:**

```bash
# Run framework tests
python3 .wavefoundry/framework/scripts/run_tests.py

# Run docs gate
./docs-gardener && ./docs-lint

# Review diff of pack changes, hooks, docs/prompts/, manifests
# Then commit (operator-owned — see Git commits below)
```

**For full upgrade procedure:** see `docs/prompts/upgrade-wavefoundry.md` and `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`.

**`build_pack.py` semantics:** default zip date is today (local ISO); letter suffix is the next letter after the maximum suffix already present for that date in the output directory (not the first missing gap). The script stamps `.wavefoundry/framework/VERSION` to `<date><letter>` before writing the archive. Use `--date` only for tests or exceptional rebuilds.

## Git Commits

**Operator-owned.** Agents must not run `git commit` unless the operator explicitly instructs them to finalize that commit in the **current** request after reviewing the diff. Default agent behavior is to hand off a suggested commit message and diff for the operator to commit locally.

This policy applies to all changes: framework source edits, self-hosted docs changes, platform surface renders, and packaging builds.
