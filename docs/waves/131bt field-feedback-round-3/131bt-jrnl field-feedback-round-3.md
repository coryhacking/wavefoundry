# Journal — Field Feedback Round 3

Owner: Engineering
Status: active
Last verified: 2026-06-01

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-06-01

wave-id: `131bt field-feedback-round-3`

## Operating Identity

- Role: wave-coordinator — coordinating six changes that close the deliberate exclusions from wave 13129 (`1319m` Go, `1319o` Python merge, `1319q` JS/TS/Python receiver-type), address the Solaris field report on construction-call edges (`1319s`), and bring the framework surface up to date with shipped capability (`131ar` MCP descriptions, `131at` CHANGELOG rename + relocate + cumulative).
- Responsibilities include: enforce Phase 0 audits on `1319s` before opening the framework gate; sequence `131at` before `131ar` so the changelog rename lands first; coordinate seed gate cycles for the docs-touching changes; ensure no `GRAPH_BUILDER_VERSION` double-bump if multiple graph-builder changes ship together.

## Salience Triggers

- **High:** Code edits on `1319s` started before Phase 0 audits complete — Phase 0a (explicit-`new` baseline behavior) and Phase 0b (`code_callhierarchy` walker double-counting risk) gate the framework_edit_allowed gate. Stop and run audits.
- **High:** `131ar` changelog entry written to `.wavefoundry/framework/RELEASE_NOTES.md` after `131at` has landed — should be at `.wavefoundry/CHANGELOG.md` with cumulative narrative shape. Confirms sequencing.
- **High:** `131ar` or `131at` editing seeds without `seed_edit_allowed` gate open — seed-first workflow gate.
- **Medium:** `GRAPH_BUILDER_VERSION` bumped more than once in this wave (e.g., both `1319s` and `1319o` bump it). Coordinate to single bump per shipped release.
- **Medium:** Build-number references (`+XXXX` pattern) appearing in `131at`'s migrated `CHANGELOG.md` sections — should be absent per the rule established in this conversation.
- **Medium:** Keep-a-Changelog category subsections (`Added / Changed / Deprecated / Removed / Fixed / Security`) appearing in `131at`'s migrated sections — deliberately rejected; cohesive narrative prose only.

## Distillation

- **Sequencing constraint: `131at` before `131ar`.** `131at` changes the changelog file name and location; `131ar` writes a changelog entry as part of its release-notes step. Land `131at` first to avoid a migration footnote on `131ar`.
- **Phase 0 audits on `1319s` are non-optional.** The change doc treats them as gating steps. Phase 0a determines whether AC-7 to AC-13 (Java/C#/TS/JS/PHP/Rust) are close-out confirmations or code extensions. Phase 0b determines whether construction edges direct to class node cause double-counting in `code_callhierarchy`.
- **Construction-edge work depends on PascalCase symbol-lookup precondition.** The bare-call invariant from `1319g` carries forward: helper fires only on bare-identifier / `new_expression` / `::new` shapes, never on navigation_expression / field_expression / member_expression. Required for false-positive guard.
- **`131at` migration is one-time.** Existing per-version content in `.wavefoundry/framework/RELEASE_NOTES.md` migrates to `.wavefoundry/CHANGELOG.md` with each section rewritten as cohesive narrative prose. Migration is part of this change, not deferred.
- **Two waves of confidence-tag expansion.** `131ar` documents `RECEIVER_RESOLVED` + `EXTRACTED`. `1319s` adds `CONSTRUCTION_RESOLVED`. If both ship together, `131ar`'s guidance should be written extensibly to include the new tag.
- **Build numbers are absent from `CHANGELOG.md` entirely** (per [[changelog-no-build-numbers]] memory). Not as sub-sections, not as footers, not inline. They live in git history, `VERSION` file, and dist zip filename.

## Open Threads

- Wave admission order between `131ar` and `131at` — flagged as a sequencing constraint above. Decide when starting implementation.
- Whether `1319s` ships with `131ar` in the same release (so `131ar`'s confidence-level guidance includes `CONSTRUCTION_RESOLVED` as a shipped level) or in a follow-up release.
- Whether all three coverage close-outs (`1319m`, `1319o`, `1319q`) ship together or get released independently as they land.

## Recent Decisions

- 2026-06-01: Wave 13129 closed at 1.2.1+319y; 21 changes delivered. This wave (131bt) admits the six follow-on items as Round 3.
- 2026-06-01: `131at` renames the file to `CHANGELOG.md` (not `RELEASE_NOTES.md`) for filename-convention discoverability.
- 2026-06-01: `131at` deliberately departs from Keep-a-Changelog format — cohesive narrative prose per version, not delta categories.
- 2026-06-01: Build numbers do not appear in `CHANGELOG.md` at all (no subsections, no footers, no inline references). Build-number traceability stays in git history, `VERSION` file, and dist zip filenames.
- 2026-06-01: `131ar` ships pure docs sync — option 1 from YAGNI value review. The Solaris field report asked for confidence levels to be documented; client-side filtering is one line per consumer. Earlier consideration of a `min_confidence` server-side parameter rejected as speculative API design — only one meaningful filter mode (drop `EXTRACTED`) means even the simpler `exclude_extracted: bool` would be premature without reported friction.
- 2026-06-01: Cross-language scope broadening during prepare value review — operator direction: "apply these concepts to all languages we support as broadly as needed."
  - `1319m`: Go-only → eight directory-grouping languages (Go + Python + Java + Kotlin + C# + Scala + PHP + Swift). Rust/Ruby/JS/TS excluded with documented rationale.
  - `1319o`: Python-only → Python + JavaScript + TypeScript (single-dominant-class with dominance gate). Per-language basename-match strategies (snake-to-PascalCase + literal for Python; literal + snake-to-Pascal + kebab-to-Pascal for JS/TS).
  - `1319q`: JS+TS+Python → JS + TS + Python + PHP + Ruby. Phase 1 ships grammar-supported annotations (TS/Python/PHP); Phase 2 ships comment-extracted annotations (JS JSDoc + Ruby Sorbet `sig` blocks).
  - `1319s`: Added Rust `struct_expression` as primary Rust construction shape (`::new()` was convention-only and missed the dominant idiom); added Go composite-literal `&Foo{}`/`Foo{}`, `new(Foo)` builtin, and `NewFoo()` factory-function convention. Prior "Go has no class constructors" framing was incorrect — Go has construction patterns; they're structural, not class-method-based.

## Active Signals

wave-id: `131bt field-feedback-round-3`

- Created 2026-06-01: six planned changes admitted — `1319m-enh go-file-grouping-package-to-directory`, `1319o-enh class-module-merge-python-dominant-class`, `1319q-enh receiver-type-js-ts-python-optional-annotations`, `1319s-bug construction-call-edges-to-class-node`, `131ar-doc mcp-tool-descriptions-sync-with-shipped-capabilities`, `131at-enh changelog-cumulative-project-level`.

## Promotion Evidence

- Stable artifact: `docs/waves/131bt field-feedback-round-3/wave.md`
- No lessons promoted yet; promote at wave closure to `docs/references/project-context-memory.md` if new patterns emerge — candidates include the construction-edge discriminator order (`1319s`), the annotation-presence gate model for typed-dynamic languages (`1319q`), and the project-level `CHANGELOG.md` cumulative-prose pattern (`131at`).

## Retirement And Supersession

- None yet. `131at` supersedes the prior `RELEASE_NOTES.md` location and structure model, but that supersession is internal to the change rather than a journal-level retirement.

## Governance

- No secrets, credentials, or PII in journals.
- Seed edits require the `seed_edit_allowed` gate; framework script edits require `framework_edit_allowed`. Both `131ar` and `131at` touch seeds; `1319s`, `1319m`, `1319o`, `1319q` touch framework scripts.
- Per [[changelog-no-build-numbers]] memory and `131at` Decision Log, build-number references are prohibited inside `CHANGELOG.md` sections — `build_pack.py` diagnostic enforces this.
