# Pre-Extraction Discoverability And JVM Type Coverage

Change ID: `1p35p-enh pre-extraction-discoverability-and-jvm-type-coverage`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p35d install-flow-two-phase-with-log-and-audit`

## Rationale

Two unrelated-in-implementation but adjacent-in-time defects from the consumer install retrospective, bundled for delivery efficiency:

### Pre-extraction discoverability

The consumer's install actually failed at "agent + zip" BEFORE seed-010 ever ran. Sequence: operator copied `wavefoundry-X.Y.Z.zip` to repo root → asked Claude (no MCP yet) to install Wavefoundry → Claude didn't recognize the zip-at-root pattern as actionable → operator manually extracted and pointed Claude at `.wavefoundry/` to find install instructions. All in-zip artifacts (INSTALL.md, install-wavefoundry.md, the install log) are visible only AFTER extraction; the bootstrap gap is **before** extraction.

The only surfaces that can address this are **outside the zip**: the GitHub repo README, the Releases page description, and possibly an outside-the-zip sibling file in the release assets. This change rewrites the GitHub repo README install section so an agent (or operator) finding the repo via Releases sees:

1. **What to do with the zip** (extract at repo root)
2. **The exact shortcut phrase to type** (`Install Wavefoundry`)
3. **Where to type it** (the AI agent's chat, not a shell)
4. **What "the AI agent" means** (Claude Code, Cursor, Codex, etc., with the repo as the working directory)

The same content goes into the Releases page description so the agent-or-operator browsing Releases sees the install steps right next to the download link.

### JVM type-coverage heuristic

The `harnessability` checker reports "no type config detected" for Spring Boot projects because it doesn't look for `pom.xml`, `build.gradle`, or `*.java`. False-negative on Java repos. Same pattern applies to other strongly-typed-but-not-Python ecosystems (Kotlin, Scala, possibly Go). This change adds JVM-aware detection: presence of `pom.xml` OR `build.gradle*` OR `*.java`/`*.kt`/`*.scala` files signals type config. Lightweight heuristic, no compiler invocation, no JVM dependency.

The two defects are bundled because they're both small, both consumer-reported, both 1.5.0-shippable, and neither warrants its own delivery-council pass. Splitting would create two micro-changes with redundant ceremony.

## Requirements

### Pre-extraction discoverability

1. **GitHub repo README install section is rewritten** with explicit zip-at-root → extract → shortcut-phrase flow in agent-readable terms.
2. **The install section includes:** prerequisite (Python 3.11+), download link, extraction instruction with macOS hidden-folder note, exact shortcut phrase in a copy-pasteable code block, "type in your AI agent's chat" clarification, list of supported agents (Claude Code, Cursor, etc.).
3. **Releases page description aligned.** Future `build_pack.py --release` invocations pull a section from CHANGELOG that includes the install steps OR the README's install section gets mirrored into the Releases description template. Decision: the simpler path is a `--release` flag that prepends an `## Install` block to the notes body before uploading; the source is a template file.
4. **Existing in-zip surfaces (`install-wavefoundry.md`, INSTALL.md) are NOT used to solve pre-extraction discoverability** — they can't, because they're not visible until extraction. This requirement is a fence: do not move pre-extraction content into in-zip files.

### JVM type-coverage heuristic

5. **Harnessability type-coverage check recognizes JVM build files.** Detection signals: `pom.xml`, `build.gradle`, `build.gradle.kts`, `settings.gradle*`, `*.java`, `*.kt`, `*.scala` files anywhere under the project root. Presence of any → type-coverage signal flips from "low (no type config detected)" to "high" (or whatever the equivalent "covered" signal is).
6. **Detection does not require compiler invocation.** Pure file-presence check; no JVM dependency, no shell-out to `javac`.
7. **Test verifies** Java fixture repo reports type coverage as covered; Kotlin fixture reports covered; pure-Python fixture continues to report uncovered.

## Scope

**In scope:**

- GitHub repo README install-section rewrite
- Releases page description template (for `build_pack.py --release` to prepend)
- JVM file-presence heuristic in `harnessability` checker
- Tests for the JVM heuristic

**Out of scope:**

- Wiring actual Java-side feedback-harness sensors (compile-check, test-runner integration) — separate follow-on wave once the heuristic surfaces these projects as candidates
- The other type-system ecosystems beyond JVM (Go, Rust, etc.) — if needed, add in a follow-on; scope is just the Java/Spring Boot false-negative the consumer reported
- The macOS Finder hidden-folder content (already lives in `install-wavefoundry.md` from C1's rename)

## Acceptance Criteria

- [x] AC-1: GitHub repo README install section explicitly describes the zip-at-root → extract → shortcut-phrase flow. (Adds explicit "do not extract the zip yourself — the agent unpacks it" callout above the walkthrough and within step (a).)
- [x] AC-2: README install section names the exact shortcut phrase (`Install Wavefoundry`) in a copy-pasteable code block.
- [x] AC-3: README install section clarifies "type in your AI agent's chat" (explicit "chat message, not a shell command" callout) and lists supported agents inline at the prompt block (in addition to the existing `## Host support` table).
- [x] AC-4: A Releases page description template exists at `.wavefoundry/framework/release/install-block.md` (the AC's "or equivalent path" — matches the `framework/install/` and `framework/scripts/` per-purpose-dir convention better than a generic `templates/` dir would).
- [x] AC-5: `build_pack.py --release` reads the template and prepends it to the CHANGELOG-extracted notes via the new `_assemble_release_notes()` helper before calling `gh release create`.
- [x] AC-6: Test verifies the release notes generated by `--release` include the install block at the top; also asserts graceful fallback when the block file is missing or empty.
- [x] AC-7: Harnessability type-coverage check recognizes `pom.xml`.
- [x] AC-8: Harnessability type-coverage check recognizes `build.gradle`, `build.gradle.kts`, and `settings.gradle*`.
- [x] AC-9: Harnessability type-coverage check recognizes `*.java`/`*.kt`/`*.scala` source files as a fallback when no build file is present.
- [x] AC-10: Detection requires no compiler invocation — file-presence only.
- [x] AC-11: Test fixture covering pure-Python (negative), Maven, Gradle (both Groovy and Kotlin DSL), pure-Java, pure-Kotlin, pure-Scala, mixed-JVM, and JVM+Python combinations exercises the heuristic.
- [x] AC-12: CHANGELOG 1.5.0 entry includes both fixes.
- [x] AC-13: docs-lint passes.
- [x] AC-14: Full framework test suite passes.

## Tasks

- [x] Open `framework_edit_allowed` gate (README + harnessability checker)
- [x] Rewrite README install section
- [x] Create `.wavefoundry/framework/release/install-block.md` (chosen over `templates/` to match the existing `framework/install/`, `framework/scripts/` per-purpose-dir layout)
- [x] Update `build_pack.py --release` to prepend the template to release notes (via `_assemble_release_notes` + `_read_release_install_block` helpers)
- [x] Update harnessability checker for JVM detection
- [x] Add tests for the heuristic with multiple fixtures (9 cases)
- [x] Add tests for the release-notes prepend behavior (4 cases including graceful-fallback)
- [x] Update CHANGELOG + `docs/references/release-flow.md`
- [x] Run framework test suite (2400 tests pass)
- [x] Run docs-lint (clean)
- [x] Close gate

## Affected Architecture Docs

`N/A` — operator-facing prose update + a checker rule addition; no boundary or component changes.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (README zip-extract-shortcut flow) | required | The agent-readable install path. |
| AC-2 (exact shortcut phrase in code block) | required | Copy-paste affordance for operators. |
| AC-3 (agent + supported-host clarification) | required | Disambiguates "type in chat" vs "shell command". |
| AC-4 (release-notes-install-prepend template exists) | required | Source of truth for the prepended install block. |
| AC-5 (`--release` prepends template to notes) | required | Mechanism that gets the install block onto every release. |
| AC-6 (test: release notes include install block) | required | Regression discipline; release-time generation must work. |
| AC-7 (detection recognizes `pom.xml`) | required | Maven projects. |
| AC-8 (detection recognizes `build.gradle*`) | required | Gradle projects. |
| AC-9 (detection recognizes `*.java`/`*.kt`/`*.scala`) | required | Source-file presence as fallback signal. |
| AC-10 (no compiler invocation) | required | Cross-platform, no JVM runtime dependency. |
| AC-11 (multi-fixture test) | required | Regression discipline + verification across language variants. |
| AC-12 (CHANGELOG) | required | Discoverability. |
| AC-13 (docs-lint passes) | required | Standard hygiene. |
| AC-14 (framework test suite passes) | required | Regression discipline. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Solve pre-extraction discoverability via GitHub repo README + Releases description (not in-zip files) | Pre-extraction content must live outside the zip because the zip hasn't been extracted yet. The repo README is what an agent or operator sees on GitHub. | Add a "where the zip should go" prompt inside `install-wavefoundry.md` — rejected; it's only visible post-extraction. |
| 2026-06-03 | Releases install block via build_pack template (auto-prepended to release notes) | The notes already get assembled at release time; prepending the install block to every release keeps it current with the prompt surface. | Manual edit on each release — rejected; drifts. |
| 2026-06-03 | JVM detection is file-presence, not compiler-invoked | Cross-platform; no JVM runtime needed; runs everywhere harnessability already runs. | Shell out to `javac --version` — rejected; introduces a runtime dependency we don't need. |
| 2026-06-03 | Bundle the two unrelated fixes in one change | Both are small, both consumer-reported, both 1.5.0-shippable. Separating would add ceremony without delivery benefit. | Two separate changes — rejected; one delivery-council pass covers both. |

## Risks

| Risk | Mitigation |
|---|---|
| README install section drifts out of sync with the actual shortcut phrase or seed naming | The shortcut phrase is stable (`Install Wavefoundry`); doc references it by phrase, not by seed number. |
| The releases install block is misleading for consumers using a different agent than Claude Code | The block lists supported agents (Cursor, Codex, etc.) so it's not Claude-specific. Each host has its equivalent of "type this in the chat." |
| JVM heuristic false-positives on a repo with a stray `*.java` test fixture but no actual Java source | False positives bias toward "covered" which is the more permissive answer; better than the current false-negative bias. |
| Detection misses Scala or other JVM languages | Scala is included via `*.scala`. Future JVM language additions extend the pattern; trivially additive. |

## Related Work

- **`1p347` (build_pack `--release` mode)** — adds the release-orchestration that this change extends with the install-block prepend.
- **`1p35f` (install-wavefoundry.md)** — handles the post-extraction discoverability. This change handles the pre-extraction surface. The two are complementary, not overlapping.
- **`docs/references/release-flow.md`** — operator-facing release-flow doc updated to mention the new install-block prepend behavior.

## Late Additions — Enterprise Deployment Hardening (2026-06-04)

After the C6 delivery-council PASS verdict, an explicit enterprise-deployment review surfaced five issues in shipped code that would fail in the target audience's repo shapes. All five are <50 LOC, no contract change, and were folded into C6 in-session per the "Fix now, not later" rule. C6 scope was extended without re-running council. The original 14 ACs remain `[x]`; the additions below are recorded as in-scope enterprise hardening rather than as new ACs.

| # | Issue | Resolution | Files |
|---|---|---|---|
| 1 | JVM source-pattern detection used `next(root.rglob("*.java"))` — walked the entire repo, false-positived on any vendored 3rd-party Java sources anywhere in the tree | Extracted `_detect_jvm_source_evidence` helper. Walks canonical project roots only (`src/main/{java,kotlin,scala,groovy}`, `src/`, `app/`, `lib/`, repo top-level iterdir). Skips `_JVM_SOURCE_WALK_IGNORE_DIRS` (vendor, node_modules, target, build, dist, .git, .gradle, .mvn, .idea, .vscode, .settings, build/cache artifacts). Bounded by `_JVM_SOURCE_WALK_FILE_BUDGET=5000` files. 4 new helper-direct tests + 4 new harnessability-level tests including vendored-Java-doesn't-signal regression guard. | `server_impl.py`, `test_server_tools.py` |
| 2 | `LINT_EXCLUDED_TRANSIENT_DIRS` had no operator-visible documentation; enterprise security review needs to audit excluded patterns without grepping source | New `docs/references/docs-lint-exclusions.md` with per-pattern table (generated-by tool, why-excluded rationale), "what `docs-lint` still flags" section, "adding to the exclusion list" criteria, and history table. Regression test (`test_exclusion_doc_exists_and_lists_each_pattern`) asserts every pattern in the constant appears in the doc — drift guard. | `docs/references/docs-lint-exclusions.md`, `core_validators.py` (docstring), `test_docs_lint.py` |
| 3 | README hardcoded `coryhacking/wavefoundry` GitHub URL in 3 places; enterprise forks would ship wrong links | New `## For enterprise forks` section enumerates every hardcoded location (README version badge, Releases link, `release/install-block.md` link) with redirection instructions. Framework intentionally does not auto-detect the host so air-gapped operators can still read install surfaces. | `README.md` |
| 4 | `LINT_EXCLUDED_TRANSIENT_DIRS` covered only `__pycache__`; universal Python transients (`.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.tox`, `.coverage`) would produce the same recurring blocker class on enterprise repos using those tools | Expanded `LINT_EXCLUDED_TRANSIENT_DIRS` to include all five. Each gitignored by ecosystem convention; lint defers to `.gitignore`. Test asserts each pattern is in the constant. | `core_validators.py`, `test_docs_lint.py`, `docs-lint-exclusions.md` |
| 5 | JVM detection missed Groovy; Spring Boot Groovy apps would false-negative | Added `*.groovy` to the source-pattern frozenset and `src/main/groovy` to the canonical-roots tuple. Test fixture verifies signal. | `server_impl.py`, `test_server_tools.py` |
| 6 | When the agent runs at a monorepo workspace parent (Nx, Lerna, pnpm, Bazel, Pants, Buck, npm/yarn workspaces, Cargo workspaces, Maven multi-module), `_audit_harnessability` was root-only and missed all sub-project type config. Reported "low / no type config detected" on heavily-typed monorepos. | New `_detect_monorepo_subprojects` recognizes 10 workspace markers including parsed-detection of `package.json` `workspaces` field, `Cargo.toml` `[workspace]` section, and Maven multi-module parent POM shape. New `_collect_subproject_type_evidence` walks each sub-project's `tsconfig.json` / `mypy.ini` / `pom.xml` / `build.gradle*` / `Cargo.toml` / `go.mod` plus the bounded JVM source-pattern helper. Aggregated evidence appears in the `type_coverage` evidence string as `monorepo (N sub-projects scanned, M typed): services/auth/pom.xml, …`. Bounded by `_MONOREPO_SUBPROJECT_BUDGET=100` per call; sub-projects in ignore-dirs (`node_modules`, `vendor`, `target`, etc.) skipped. 13 new tests including positive cases for each workspace tool, negative cases (plain `package.json`/`Cargo.toml`/`pom.xml` without workspace markers don't trigger), and a single-project regression guard. | `server_impl.py`, `test_server_tools.py` |

**Tests added**: 6 harnessability hardening cases + 4 helper-direct cases + 2 lint-exclusion cases + 13 monorepo cases + 4 monorepo-aggregation cases = 29 new tests on top of the original C6 13. Final suite 2400+29 = 2429 tests pass.

**Out of scope for these additions** (queued for the post-1p35d wave):

- C4-DC-1 (persona-coverage harder gate)
- C6-DC-1 (README dual-source host-list drift)
- `--release` install-block customization escape hatch (`--no-install-block` flag)
- `no_agent_role_docs` advisory severity escalation
- **`wave_audit(scope=<subpath>)`** — narrowing a monorepo audit to one specific sub-project. The Part-1 aggregation above honestly reports monorepo state; per-sub-project scoping is a tool-surface contract change.
- Extending boundary_clarity / harness_coverage / harness_coherence checks for per-sub-project monorepo behavior — Part 1 covered type_coverage only because it had the most acute misleading-answer failure mode.

Each above requires deliberate design or contract change beyond the in-session-fix threshold.

## Session Handoff

Admitted to `1p35d` as the independent final change. Can implement at any sequencing point (no dependencies on C1–C5). Late additions (above) folded in after delivery-council PASS verdict per "Fix now, not later" rule; council not re-run because each addition was <50 LOC with no contract change.
