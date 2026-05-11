# Prompt File Extension Rename

Change ID: `12cvs-enh prompt-file-extension-rename`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-04
Wave: `12cv4 prompt-indexing-quality`

## Rationale

The `.prompt.md` extension convention already existed in the framework seeds (e.g. `170-plan-feature.prompt.md`) as a semantic signal: `.prompt.md` = "invoke this", `.md` = "read this for context." Project prompt files under `docs/prompts/` were all using plain `.md`, breaking that convention and making the file type ambiguous. Wave 12cv4 introduces `.prompt.md` extension detection as a chunk-kind trigger — renaming the project prompt files makes the detection consistent with the seed convention and requires no special-case path logic for a common case.

## Requirements

1. All runnable prompt files under `docs/prompts/` (including `docs/prompts/agents/`) are renamed from `<name>.md` to `<name>.prompt.md`.
2. `index.md` and `agents/README.md` are not renamed (they are reference/index documents, not runnable prompts).
3. All references to the old filenames across the entire repository (AGENTS.md, seeds, architecture docs, contributing docs, wave records, journals, personas, manifests, scripts) are updated to use the new names.
4. All framework tests continue to pass after the rename.

## Scope

**Problem statement:** Project prompt files used plain `.md` while framework seed prompts used `.prompt.md`. The inconsistency made the distinction between runnable prompts and reference docs unclear, and required path-based detection logic where extension-based detection would be cleaner.

**In scope:**
- `git mv` rename of 25 prompt files under `docs/prompts/`
- Reference updates across all files in the repository that reference the old paths

**Out of scope:**
- Framework seeds — already use `.prompt.md` convention, no rename needed
- `index.md`, `agents/README.md` — reference documents, not prompts

## Acceptance Criteria

- AC-1: All 25 prompt files renamed; `index.md` and `README.md` untouched
- AC-2: No broken references to old `.md` filenames remain in the working tree (excluding stale worktrees under `.claude/`)
- AC-3: All 812 framework tests pass
- AC-4: `prompt-surface-manifest.json` updated to reference new filenames

## Tasks

- [x] `git mv` all 25 prompt files to `.prompt.md`
- [x] Update all references: AGENTS.md, seeds, architecture, contributing, wave records, journals, personas, manifest, scripts
- [x] Verify no old-style references remain
- [x] Verify all tests pass

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| rename | Engineering | — | git mv all 25 files |
| references | Engineering | rename | bulk sed across all reference sites |
| verify | Engineering | references | grep + test suite |

## Serialization Points

- All renames must complete before reference updates begin.

## Affected Architecture Docs

N/A — pure rename, no behavior change; chunker detection updated in sibling change `12cv3-enh prompt-indexing-quality`.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Core deliverable |
| AC-2 | required | Broken references cause agent routing failures |
| AC-3 | required | Non-regression |
| AC-4 | required | Manifest drives surface generation |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-04 | All files renamed and references updated; 812 tests pass | git mv × 25, grep confirms no stale refs |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-04 | Rename now while distribution is limited | Low migration cost; establishes clean convention before broad adoption | Defer until next major release (rejected: no benefit to waiting) |
| 2026-05-04 | Keep index.md and README.md as plain .md | These are reference/index documents, not runnable prompts | Rename all .md (rejected: index.md is a catalog, not a prompt) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Stale references in external consumers | Distribution is limited; rename announced in wave record |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
