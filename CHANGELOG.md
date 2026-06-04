# Changelog

All notable changes to this project are documented in this file and in
the individual wave records under [`docs/waves/`](docs/waves/).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0]

### Changed

- docs-lint no longer flags `__pycache__` directories under `.wavefoundry/framework/scripts/`. `.gitignore` is the source of truth for this pattern; duplicating the check produced a recurring blocker for the MCP server flow, which generates pycache on every Python import. `check_pycache` is now a documented no-op; `__pycache__` is in the named `LINT_EXCLUDED_TRANSIENT_DIRS` constant for discoverability.
- Repo README install section rewritten so an agent or operator landing on GitHub before extracting the zip sees the explicit `zip-at-root → do-not-extract → "Install Wavefoundry" → agent unpacks` flow. The shortcut phrase appears in a copy-pasteable code block with a `chat message, not a shell command` clarification and an inline list of supported AI agent hosts.
- `build_pack.py --release` now prepends an `## Install` block to every release's notes before calling `gh release create`. Source of truth is `.wavefoundry/framework/release/install-block.md`. Operators browsing the Releases page see the install steps alongside the download link.
- `_audit_harnessability` type-coverage detection recognizes JVM build files (`pom.xml`, `build.gradle`, `build.gradle.kts`, `settings.gradle*`) and source files (`*.java`, `*.kt`, `*.scala`, `*.groovy`) in canonical project roots (`src/main/{java,kotlin,scala,groovy}`, `src/`, `app/`, `lib/`, or repo top-level only). Spring Boot and other JVM-ecosystem projects previously read as "no type config detected"; they now report the actual signal. File-presence only — no compiler invocation, no JVM runtime dependency. Walk skips vendored / build / archive directories (`vendor`, `node_modules`, `target`, `build`, `dist`, `.git`, `.gradle`, `.idea`, etc.) and is bounded by a per-call file budget so detection stays sub-second on enterprise monorepos.
- `LINT_EXCLUDED_TRANSIENT_DIRS` expanded to cover universal Python-ecosystem caches (`.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.tox`, `.coverage`) alongside `__pycache__`. Each is gitignored by ecosystem convention; lint defers to `.gitignore` as the source of truth. Operator-visible documentation at [`docs/references/docs-lint-exclusions.md`](docs/references/docs-lint-exclusions.md) enumerates every excluded pattern with its generated-by tool and rationale — discoverable for security audit without grepping source.
- README adds a `## For enterprise forks` section naming every place that hardcodes the upstream `coryhacking/wavefoundry` URL (README version badge, Releases link, `release/install-block.md` link). Forks own the redirection step; the framework intentionally does not auto-detect the host so air-gapped operators can still read the install surfaces.
- **`Upgrade wave framework` auto-migrates 1.4.x → 1.5.0 breaking changes.** A new `post_extract` hook in `upgrade_extensions.py` runs three migrations automatically when the installed revision predates 1.5.0: (1) inserts `Role: <slug>` into every `docs/agents/*.md` missing the field (matches the new lint enforcement); (2) deletes orphan `.claude/hooks/pycache-cleanup*` launcher files; (3) strips the stale `PostToolUse` Bash → pycache-cleanup hook row from `.claude/settings.json`. Each migration is idempotent, version-gated (skips entirely on 1.5.0+), and isolated (failure in one doesn't abort others). Consolidated migration report written to `.wavefoundry/logs/upgrade-migration-1.5.0.log` when at least one migration performed work. Operators upgrading from 1.4.x get a clean 1.5.0 state in one step rather than hitting docs-lint failures + stale-hook silent errors and having to manually clean up.
- `_audit_harnessability` recognizes monorepo workspaces and aggregates type-coverage signals across sub-projects. Workspace markers detected: `nx.json`, `lerna.json`, `rush.json`, `pnpm-workspace.yaml`, Bazel `WORKSPACE` / `WORKSPACE.bazel` / `MODULE.bazel`, Pants `pants.toml`, Buck `.buckconfig`, npm/yarn workspaces (`package.json` with `workspaces` field), Cargo workspaces (`[workspace]` section), and Maven multi-module parent POMs (`<packaging>pom</packaging>` + `<modules>`). Sub-project parents walked: `services/`, `apps/`, `libs/`, `packages/`, `crates/`, `modules/`, `subprojects/`, `components/`, `projects/`. Per-sub-project type signals (tsconfig, mypy, pyrightconfig, JVM build files, Cargo.toml, go.mod, JVM source-pattern fallback) feed back into the aggregate score. Capped at 100 sub-projects per call; sub-projects under `node_modules`, `vendor`, `target`, `build`, etc. are skipped. Agents invoked from a monorepo workspace root no longer report "no type config detected" when sub-projects are heavily typed.

### Removed

- Retire the `pycache-cleanup` Claude Code hook surface. The previous `PostToolUse` Bash hook row in `.claude/settings.json` (and its `.claude/hooks/pycache-cleanup*` launchers) is no longer rendered. Existing consumer installs may delete leftover `.claude/hooks/pycache-cleanup*` files after re-running `Refresh wave framework`. The rendered hook helper source also drops the unused `maybe_cleanup_pycache` function and the `shutil` import it required.

## [1.4.1] - 2026-06-03

### Fixed

- Published GitHub Release zips now include the pre-built framework semantic index (`.lance` embeddings, graph state, manifest). Prior 1.4.0 release was missing the index because CI lacked the index-build dependencies (`numpy`/`fastembed`/`lancedb`); consumers had to rebuild the framework index locally on first `docs_search` call. Releases now come from the maintainer's machine via `build_pack.py --release`, which always includes the optimized + vacuumed index.

### Changed

- `build_pack.py` is now the official release CLI. The new `--release` flag handles tag, push, and GitHub Release upload after a successful local build, with pre-flight refusals on dirty working tree, non-main branch, existing tag, missing CHANGELOG section, or unauthenticated `gh`. Bare `build_pack.py --version X.Y.Z` is unchanged for testing and local-only builds. A `--release-dry-run` mode walks the entire pipeline without side effects for smoke-testing.
- `docs/references/release-flow.md` added — operator-facing documentation for the release command, pre-flight gates, and partial-state recovery paths.

### Removed

- `.github/workflows/release.yml` deleted. The CI workflow shipped a strictly worse artifact (no framework index) than the maintainer's local build; replaced by `build_pack.py --release`. PR-tests CI (scoped to lint/tests, not publishing) may be added in a future change if/when needed.

## [1.4.0] - 2026-06-03

### Fixed

- Runtime Wave Council policy reader now accepts the new `wave_review` key in `workflow-config.json` with a legacy fallback to `wave_council_policy`. Consumers who follow upgraded seed guidance and rename the key keep their Wave Council enforcement; consumers who haven't migrated yet continue to work unchanged. A one-line deprecation note fires to stderr at most once per process on legacy-key read.
- docs-lint required-keys check accepts either `wave_implement` (new canonical name) or `wave_execution` (legacy) in `workflow-config.json`. Error message names both acceptable keys when neither is set so the migration path is discoverable inline.

### Changed

- `WORKFLOW_REQUIRED_KEYS` data structure generalized to support alias-tuple entries — future seed-prose key renames can add back-compat without changing the validator logic.
- Active operational docs migrated to the canonical renamed config-key names (`wave_review`, `wave_implement`); two high-traffic operator surfaces carry a `(formerly wave_council_policy)` annotation for migrating-operator discoverability. Historical wave records left untouched per the no-retrofit principle.
- Self-host `docs/workflow-config.json` top-level keys renamed to the canonical names — dogfoods the back-compat fix end-to-end against the canonical example.
- Framework project skeleton now ships `wave_review: { enabled: true }` by default so the Wave Council surface is available in every new install. Enforcement (`required_for_all_waves: true`) stays operator opt-in — the council is enabled, not enforced. Mirrors how red-team is wired in as an always-available council seat. docs-lint required-keys check now names `wave_review` (with `wave_council_policy` as the legacy alias) so installs missing the section fail discoverably.
- Review surfaces unified as specialist agents. The Wave Council moderator role moves from `docs/agents/council-moderator.md` to `docs/agents/specialists/wave-council.md` (named after the surface, matching `red-team.md`). A new `docs/agents/specialists/archetype-council.md` makes the operator-invoked Archetype Council discoverable as a peer — applicable to any artifact (plans, design docs, code, prose, decision narratives, naming, AC formulation) where orthogonal stance-based lenses are what the work rewards, not text-only. Role-string identity flips from `council-moderator` to `wave-council` across seeds, code, tests, and active docs. Historical wave records and in-flight 1p337 council-verdict text preserved verbatim per the no-retrofit principle. No behavior change — verdict shape and protocol mechanics are unchanged.

## [1.3.32] - 2026-06-03

### Added

- Public-launch README rewrite: symptom-first opening, audience qualifier, install walkthrough with named operator-visible signals, "Your first wave" three-turn transcript with intentional close-gate refusal, "What is installed" tree with per-directory roles and gitignore footnote, host coverage table, Design principles, "For teams" evaluation answers, Built-with-Wavefoundry as Contributing introduction
- Auto-syncing version badge derived from GitHub Releases
- Archetype Council review surface — stance-based council with five canonical seats (Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman) and documented Hemingway / Munger swap-ins; optional, operator-invoked; complements Wave Council
- New shortcut phrase `Archetype review` / `Archetype council` added to public command catalog and AGENTS.md
- `[~]` AC and task checkbox state for "intentionally not met" — required-priority `[~]` ACs lint-require an inline status note; tasks accept `[~]` without note (asymmetric per priority weight)
- `wave_close` close-time hard gate: every AC and task across admitted changes must be `[x]` or `[~]` before close; silent `[ ]` blocks with `silent_unchecked_items_at_close` diagnostic naming change-id + item-type + identifier; `not-this-scope` priority ACs exempt
- Dashboard renders `[~]` items with distinct glyph (`~`), italic muted text, "deferred" badge replacing the priority badge, and "· N deferred" suffix on progress fractions
- Dashboard progress denominators exclude `[~]` items so a fully-met change with deferred ACs renders as complete
- `wave_index_build` response carries `stranded_rows_reaped` and `stranded_rows_reaped_by_table`

### Changed

- `docs/prompts/index.md` opening framing rewritten without internal seed-IDs; Public Commands table and Legacy Aliases table preserved verbatim
- `docs/references/project-overview.md` refreshed
- AC dialog and Task dialog glyphs are bold and slightly larger (1rem) so all three states stand out

### Fixed

- LanceDB orphan-row reaper on incremental index update — reconciles the LanceDB row set against the current eligible set on every `mode='update'` so rows for paths excluded by workflow-config narrowing are removed without requiring a full rebuild; reaps both `docs` and `code` tables regardless of `content` arg
- Project-layer audit eligibility filter (`_layer_current_hashes`) now honors workflow-config `project_include_prefixes` opt-ins, matching the indexer's actual `files_for_meta` computation; eliminates false-positive "removed paths" signal when a repo opts in framework paths via `code.project_include_prefixes`

## [1.0.0] - 2026-05-24

### Added

- Full Wave Framework lifecycle: plan, create, prepare, implement, review, close
- Local MCP server with 47 tools across wave lifecycle, docs/code search, audit, and framework navigation
- Semantic search index built on fastembed and BAAI/bge-base-en-v1.5 (fully offline)
- Three-dimension feedback harness: maintainability (computational sensors), architecture and security/performance (inferential sensor lanes)
- Wave Council protocol for multi-reviewer governance
- 214 seed prompts covering the full agent operating surface
- Stage gates enforced by the server: prepare gate, required reviewer lanes, operator signoff
- Distribution packaging (`build_pack.py`) and upgrade flow (`upgrade_wavefoundry.py`)
- Multi-host agent support: Claude Code, Cursor, Codex, Copilot, Junie, Windsurf, Air, Warp
- Semver versioning with lifecycle-prefix build metadata
- Python tool venv at `~/.wavefoundry/venv` (no system Python modification)
- Dashboard server for portfolio visibility

