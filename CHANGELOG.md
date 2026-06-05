# Changelog

All notable changes to this project are documented in this file and in
the individual wave records under [`docs/waves/`](docs/waves/).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-06-05

### Changed

- **Chunker per-kind size caps.** Doc, seed, JSON, YAML, TOML, HTML, XML chunks now respect the embedder's 512-token budget — previously only code chunks were capped, so the bottom 45-62% of every structured chunk was silently invisible to semantic search. Markdown lists and tables decompose at logical boundaries; section breadcrumbs preserved on every split. `CHUNKER_VERSION` bumped; indexer auto-rebuilds on mismatch.
- **Self-repairing indexer.** Cross-checks `file_meta` against Lance chunks every update and re-chunks drifted files. Closes the legacy mega-chunk pattern that left some files indexed-but-empty until their mtime changed.
- **`Upgrade wave framework` is one step, end-to-end.** Auto-migrates 1.4.x → 1.5.0 (backfills `Role:` in `docs/agents/*.md`, removes orphan `.claude/hooks/pycache-cleanup*` launchers, strips the stale `PostToolUse` row from `.claude/settings.json`). Always runs the index update at the end of the main flow — no separate `--update-index` invocation. Framework version transitions (`CHUNKER_VERSION` / `WALKER_VERSION` / `GRAPH_BUILDER_VERSION`) logged prominently; MCP server reloads in-process after extract. `--dry-run` previews everything with zero filesystem mutations. Supported upgrade floor is now 1.4.0.
- **MCP code-navigation polish.** `code_read` enriched for the read-then-edit flow — range-aware streaming, `read_invocation` hint (exact args for the built-in `Read` tool), `mtime`, `marker_regions`, `edit_governance`, and a `structural` field with containing-symbol + mid-construct flags + clean-range suggestion. Tree-sitter parses share a single LRU cache across all navigation tools — `code_definition` → `code_outline` → `code_callhierarchy` on the same file parses once. `code_keyword` defaults to `limit=50` (matching `code_pattern` / `code_references`); response includes `truncated` and `total_matches_found` when capped. `code_pattern`'s `max_results` parameter renamed to `limit` for cross-tool consistency (alias retained).
- **Auto-Guru routing strengthened.** Pre-flight intent question, positive/negative examples table anchored on the verbatim failure-mode phrase, and a retrieval-intent backstop catching misses the pre-flight skipped. MCP-first rule extends to literal-identifier sweeps across docs, config, and prompts (not only source-code navigation); legitimate shell exceptions (`git status`/`diff`/`log`, byte-level file-state checks, key-presence verification) named explicitly.
- **Drift-convergence lint family.** `docs-lint` warns on retired role slugs (`council-moderator` → `wave-council`; `code-insight-agent` → `guru`) in hand-authored project docs; warns when `docs/workflow-config.json` satisfies a required-keys alias via the legacy spelling (e.g., `wave_council_policy` vs canonical `wave_review`); fails on duplicate seed numeric prefixes; defers all transient Python caches (`__pycache__`, `.pytest_cache`, `.mypy_cache`, etc.) to `.gitignore`. `docs/agents/specialists/` location downgraded from `MUST` to fresh-install convention — established flat-layout repos may keep their existing location. Back-compat preserved everywhere (warnings are informational; returncode unchanged on alias-key usage).
- **Wave MCP tool polish.** Every write-side tool reports post-write `docs-lint` state in `data.lint` (`{clean, error_count, warning_count, first_errors}`); failures don't block the structural write. `wave_create_wave` produces lint-clean output with a pre-populated journal stub. Lifecycle IDs no longer burned by dry_run — `next_available_prefix` and `build_id` gain a `commit: bool` parameter; preview followed by apply returns the same ID.
- **Build & release.** Root `CHANGELOG.md` is now the single canonical release-history source; `build_pack.py` copies it into the pack zip at `.wavefoundry/CHANGELOG.md` so consumers still receive an in-tree changelog on upgrade. `Package Wavefoundry` seed removed from the consumer pack — packaging is wavefoundry-internal; consumer installs auto-prune via MANIFEST-prune. GitHub Release notes prepend an `## Install` block so the install steps appear alongside the download link.
- **JVM and monorepo harnessability detection.** `_audit_harnessability` recognizes JVM build files (`pom.xml`, `build.gradle*`) and source files (`*.java`/`.kt`/`.scala`/`.groovy`) in canonical roots — Spring Boot and JVM-ecosystem projects now report actual type coverage. Monorepo workspace detection added: Nx, Lerna, Rush, pnpm, Bazel, Pants, Buck, npm/yarn workspaces, Cargo workspaces, Maven multi-module POMs.
- **README install walkthrough restructured.** Two-phase shape (Phase 1 harness bootstrap → MCP restart → Phase 2 project discovery) reflects the actual install seeds. Claude Code and Codex CLI recommended as first-install hosts. `For enterprise forks` section names every upstream URL that needs redirecting.
- **Reality-checker routes to the new code-correctness patterns.** `seed-216` (reality-checker) gains a `## State And Assumption Correctness Patterns (Cross-Reference)` section listing the 7 patterns from `seed-221` with their applies-when hints and pointing to `seed-221` for full definitions. Cross-reference, not duplicate — code-reviewer owns the canonical pattern definitions; reality-checker routes assumption-audit findings to them when assumption-falsifiability is the dominant concern.
- **Config-key renames now converge.** `canonical-names.json` sets `removed_in: "2.0.0"` for both `wave_council_policy` → `wave_review` and `wave_execution` → `wave_implement`. `wave_upgrade` runs an unconditional convergence migration in `post_extract` (no `from_version` gate, idempotent) that rewrites legacy keys to canonical in `docs/workflow-config.json`; when both spellings are present, canonical wins and the legacy entry is dropped with its value captured in `.wavefoundry/logs/upgrade-convergence-migration.log` so operators can recover from the log without consulting git history. Dry-run writes `.wavefoundry/logs/upgrade-convergence-migration.preview.log` (parity with the 1.4 → 1.5 migration preview-report shape). Stderr summaries distinguish rename from drop so the both-present case isn't mislabeled. `docs-lint` adds `check_workflow_config_removed_keys` — at or past `removed_in`, legacy spellings produce an ERROR (returncode flips); below, they continue to produce the existing WARNING (now annotated with the removal version). VERSION-file degraded modes (missing / unparseable) defer to no-escalation. Role renames stay at `removed_in: null` — config-key scope only. Closes the indefinite-deprecation gap in Solaris field-feedback item #1.
- **Canonical-names manifest is the single source for framework renames.** `.wavefoundry/framework/canonical-names.json` (schema v1) declares every role-slug and config-key rename with its deprecated alias and an optional `removed_in` semver for bounded deprecation. `wave_lint_lib/canonical_names.py` provides the loader (fail-safe to empty on missing/malformed input — `docs-lint` stays operational). `constants.RETIRED_ROLE_NAMES` and `constants.WORKFLOW_REQUIRED_KEYS` now derive from the manifest at module-load time; public surface unchanged for backward compat. Required-key list (`agent_memory`, `project_persona_generation`, etc.) stays in code — manifest scope is renames only. Enables downstream consumers (renderers, upgrade migrator) to migrate to the manifest incrementally. Wave 1p3iv prep for the convergence half of `wave_council_policy` → `wave_review`.
- **Red-team routes to the new failure-path patterns.** `seed-225` (red-team) gains a `## Failure Path And Boundary Correctness Patterns (Cross-Reference)` section listing the 6 patterns from `seed-221` with their applies-when scopes and a one-line adversarial-probe framing per pattern (e.g., "what unbounded input would exhaust a resource?"). Reviewers in `abuse-path-review`, `failure-pressure-test`, and `council-adversarial-primer` modes anchor probes to the canonical patterns without leaving `seed-225`. Cross-reference, not duplicate.
- **Code-reviewer review surface expanded.** `seed-221` `## What to Check` gains 13 generic code-correctness review patterns across two new sections — **State And Assumption Correctness** (7 patterns: re-entrancy, convergence after correction, legitimate-state enumeration, idempotence, cache-key completeness, schema evolution, negation correctness) and **Failure Path And Boundary Correctness** (6 patterns: error handling, resource cleanup, diagnostic quality, boundary arithmetic, trust-boundary input validation, failure-path test coverage). Each pattern carries an "applies when" hint so reviewers route effort by PR scope.

### Fixed

- **`code_search` finds re-export and barrel files.** The chunker gains a symbolless-code-file fallback: when a code file has no docstring AND no extractable symbols (re-export `__init__.py`, TypeScript barrel `index.ts`, Go single-file packages, Rust `mod.rs` re-exports, module-level constants files), it now emits a `kind="code"` module chunk with `id="<path>::__module__"` and the top-level non-comment lines so semantic search can find the public surface. Previously these files emitted zero chunks and were invisible to `code_search` (only `code_keyword` text-backed search found them). Per-language comment-prefix awareness (Python `#`, C-family `//`/`/*`, SQL `--`, HTML `<!--`); cap at 50 lines per module chunk. Files with even one extracted symbol use the existing docstring + symbols summary unchanged — fallback only fires when symbol extraction yields nothing. Marker-region-only files still emit zero chunks and remain outside semantic search. Wave 1p3iw `chunks_emitted` tracking stays accurate: post-fallback, re-export files record `chunks_emitted: 1` and exit the legitimate-zero set. `CHUNKER_VERSION` bumps from `"24"` to `"25"`; `indexer.py` auto-escalates incremental updates to a full rebuild on the version mismatch so consumer indexes regenerate transparently on upgrade.
- **Self-repairing indexer no longer thrashes on legitimately-empty files.** `file_meta` records `chunks_emitted` per file after each indexing run; drift detection skips paths with explicit `chunks_emitted == 0` (empty files, all-whitespace, marker-region-dominated content). Legacy entries (no field) go through the drift check once to learn the count, then skip silently. Real-drift convergence preserved.

### Removed

- **`pycache-cleanup` Claude Code hook surface.** The `PostToolUse` Bash row in `.claude/settings.json` and `.claude/hooks/pycache-cleanup*` launchers are no longer rendered. Existing consumer installs auto-clean on next `Upgrade wave framework`.

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
