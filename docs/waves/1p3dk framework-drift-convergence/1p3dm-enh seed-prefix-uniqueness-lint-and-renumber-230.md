# Seed Prefix Uniqueness Lint And Renumber 230

Change ID: `1p3dm-enh seed-prefix-uniqueness-lint-and-renumber-230`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p3dk framework-drift-convergence`

## Rationale

The `.wavefoundry/framework/seeds/` directory currently ships **two seeds with the prefix `230`**: `230-author-spec.prompt.md` (modified in 1.5.0) and `230-council-review.prompt.md` (new in 1.5.0). Any tooling that keys on the numeric prefix as a unique identifier — or any human who treats the prefix as a unique key when reading seed-160 / seed-100 references to `seed-230` — will collide on the meaning.

Solaris field feedback (2026-06-04) flagged this as a structural defect: the prefix declares itself a unique key but the framework permits two values for it. Same pattern as the other drift items in this wave: declared state and actual state disagree because the framework permits the ambiguity.

Fix is two-part:

1. **Renumber `230-council-review.prompt.md` → `237-council-review.prompt.md`.** Free slot `237` is unoccupied and sits adjacent to `236-archetype-council.prompt.md`, keeping council seeds grouped. `230-author-spec` keeps its current number because all existing `seed-230` *prefix* references in seed-160, seed-150, and consumer code refer to author-spec; renaming it would require touching more surfaces.
2. **Add a `docs-lint` check** that fails when two seeds share a numeric prefix. The check enumerates `.wavefoundry/framework/seeds/*.md`, parses the leading `NNN-` prefix, and errors on any duplicate. This converts the prefix from "convention" to "enforced unique key" — the same conversion this wave does for canonical names elsewhere.

## Requirements

1. `.wavefoundry/framework/seeds/230-council-review.prompt.md` is renamed to `.wavefoundry/framework/seeds/237-council-review.prompt.md` via `git mv` (preserves history).
2. The single existing reference to the old filename in `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md` (line 86) is updated to the new filename. No other references to `230-council-review.prompt.md` exist in the pack (verified via grep).
3. `docs-lint` gains a new check `check_seed_prefix_uniqueness` in `wave_lint_lib/` that enumerates seeds, parses leading `NNN-` prefixes, and errors on duplicates. Error message names both colliding filenames.
4. The new check runs in every `docs-lint` invocation (no special flag required).
5. The framework graph index is rebuilt after the `git mv` so graph edges from `230-council-review.prompt.md` are repointed to `237-council-review.prompt.md`. This is an advisory finding from the prepare-council readiness review and must be performed before the change is verified complete.
6. CHANGELOG entry under `## [1.5.0]` notes the rename and the new lint check.

## Scope

**Problem statement:** Two seeds share the prefix `230`. The framework treats the prefix as a convention but does not enforce uniqueness, so the collision ships in the 1.5.0 pack and any tooling keying on the prefix will resolve ambiguously.

**In scope:**

- File rename: `.wavefoundry/framework/seeds/230-council-review.prompt.md` → `.wavefoundry/framework/seeds/237-council-review.prompt.md`
- Reference update in `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- New `check_seed_prefix_uniqueness` rule in `wave_lint_lib/`
- Framework graph reindex after the move
- Tests: positive (clean state passes), negative (planted collision fails with both filenames in the error)
- CHANGELOG bullet

**Out of scope:**

- Renumbering other seeds whose prefixes are NOT colliding
- Restructuring the seed-prefix scheme (e.g., to longer numeric ranges)
- Migrating `seed-NNN` text references in non-seed files (no other places need updating per the verification grep)
- Project-side seed prefix enforcement (this lint is framework-scoped)

## Acceptance Criteria

- [x] AC-1: `.wavefoundry/framework/seeds/237-council-review.prompt.md` exists with the content of the former `230-council-review.prompt.md`; the old path does not exist in HEAD.
- [x] AC-2: `git log --follow .wavefoundry/framework/seeds/237-council-review.prompt.md` shows the file's pre-rename history (`git mv` preserves it).
- [x] AC-3: `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md` line 86 references `237-council-review.prompt.md` (the new path). No reference to `230-council-review.prompt.md` exists anywhere in the pack (`grep -rn "230-council-review" .wavefoundry/framework/` returns zero results).
- [x] AC-4: `wave_lint_lib/` has a new module function `check_seed_prefix_uniqueness(seeds_dir) -> list[str]` returning error messages (empty list when no collisions).
- [x] AC-5: When two seeds share a prefix, `check_seed_prefix_uniqueness` returns exactly one error per colliding pair, naming both filenames. Error message format: `seed prefix collision: \`NNN-\` shared by \`NNN-name1.md\` and \`NNN-name2.md\``.
- [x] AC-6: `docs-lint` invocation runs `check_seed_prefix_uniqueness` automatically; planted-collision test confirms the lint fails with the expected message.
- [x] AC-7: Framework graph index is rebuilt after the move; `wave_index_build(content="graph")` (or `setup_index --rebuild-graph`) produces zero references to `230-council-review.prompt.md` and the expected references to `237-council-review.prompt.md`.
- [x] AC-8: Tests in `test_docs_lint.py`: `test_seed_prefix_uniqueness_clean_state_passes`, `test_seed_prefix_uniqueness_collision_fails_with_both_names`.
- [x] AC-9: CHANGELOG bullet under `## [1.5.0]` describes the rename and the new lint check.
- [x] AC-10: Full framework test suite passes.
- [x] AC-11: docs-lint clean.

## Tasks

- [x] Open `seed_edit_allowed` gate (rename touches `.wavefoundry/framework/seeds/`)
- [x] `git mv .wavefoundry/framework/seeds/230-council-review.prompt.md .wavefoundry/framework/seeds/237-council-review.prompt.md`
- [x] Update reference in `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md` line 86
- [x] Verify zero remaining references via `grep -rn "230-council-review" .wavefoundry/framework/`
- [x] Add `check_seed_prefix_uniqueness(seeds_dir)` to `wave_lint_lib/`
- [x] Wire the new check into `docs-lint` invocation pipeline
- [x] Add positive and negative tests in `test_docs_lint.py`
- [x] Rebuild framework graph index (`wave_index_build(content="graph")` or equivalent)
- [x] Update CHANGELOG bullet
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close `seed_edit_allowed` gate

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| rename | implementer | — | `git mv` + reference update in seed-100 |
| lint-check | implementer | — | New `check_seed_prefix_uniqueness` + wiring |
| reindex | implementer | rename | Framework graph rebuild after move |
| tests | qa-reviewer | lint-check | Positive + negative coverage |

## Serialization Points

- The rename and the lint check can land in parallel: rename touches `.wavefoundry/framework/seeds/` only; lint check touches `wave_lint_lib/` only. Reindex must follow rename. Tests follow lint check.

## Affected Architecture Docs

`N/A` — file rename within an existing seed directory; new lint check in existing module; no boundary or data-flow change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core rename — the headline change. |
| AC-2 | required | History preservation is the reason for `git mv` over plain `mv`. |
| AC-3 | required | Stale references would shadow the rename. |
| AC-4 | required | The lint helper is the structural fix that prevents recurrence. |
| AC-5 | required | Error message clarity drives operator UX when the lint catches a future regression. |
| AC-6 | required | Without auto-invocation, the lint helper is dead code. |
| AC-7 | required | Advisory finding from readiness review: graph index must be rebuilt so edges to the renamed file refresh. |
| AC-8 | required | Coverage for both pass and fail paths of the new check. |
| AC-9 | required | Operator-visible change deserves CHANGELOG entry. |
| AC-10 | required | Suite must pass. |
| AC-11 | required | docs-lint must pass. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-04 | Change scaffolded and admitted to wave `1p3dk` | This doc; `wave_current` output |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-04 | Renumber `230-council-review` (not `230-author-spec`) | All existing `seed-230` prefix references in seed-160 and consumer code refer to `author-spec`; renumbering the other file would touch fewer surfaces. | Renumber `230-author-spec` — rejected; cascade of reference updates is larger. |
| 2026-06-04 | Target slot `237` for the council-review rename | Adjacent to `236-archetype-council`; keeps council seeds grouped; free in the seed directory. | `238`, `239`, `241+` — all unoccupied but less semantically adjacent. |
| 2026-06-04 | Add lint check rather than only renaming | The rename alone removes the current collision but doesn't prevent a future one. Lint conversion makes the prefix a real key. | Rename only — rejected; doesn't address the structural defect that allowed the collision. |
| 2026-06-04 | Framework graph reindex is an explicit task, not implicit | Readiness review (red-team) advisory finding: graph edges from `230-council-review.prompt.md` would otherwise point at the renamed file's old path until the next manual rebuild. | Defer reindex — rejected; leaves the index in a knowingly-stale state. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| External consumers (forks) that reference `230-council-review.prompt.md` by name in their own seeds or scripts would break | Risk is theoretical; the file is internal to the framework pack and downstream consumers don't reference it by number. Documented in CHANGELOG so any consumer auditing the diff sees the rename. |
| The new lint check could fire on legitimate temporary collisions during in-flight renames | Lint failures during in-flight renames are correct — the in-flight state IS a collision. Mitigation is procedural: renames happen atomically in a single change, not across changes. |
| Reindex after rename could miss the old filename in stale cache | `wave_index_build(content="graph")` reads from disk, not cache. The `_existing_prefixes` and graph-extractor scans look at the current filesystem state. Verified path. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
