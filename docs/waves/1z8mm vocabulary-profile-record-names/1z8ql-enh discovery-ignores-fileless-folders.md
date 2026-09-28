# Discovery Diagnostic Ignores Folders Without Files

Change ID: `1z8ql-enh discovery-ignores-fileless-folders`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-27
Wave: 1z8mm vocabulary-profile-record-names

## Rationale

The advisory `record_file_not_found` diagnostic (change `1z826`) fires when the waves root has candidate folders but none holds the profile's record file. In a nested layout, grouping folders are candidates, so a root holding only empty grouping folders (before the first wave is created in one) reports a mismatch that is not there. The same happens in a flat layout for an empty folder. The diagnostic exists to catch records written under another filename; a folder that holds no files cannot hold such a record.

## Requirements

1. `record_paths.record_discovery_mismatch` counts only candidate folders that directly contain at least one regular file whose name does not start with `.`. A candidate that holds no such file (empty, only subfolders, or only dot-files such as `.gitkeep` and `.DS_Store`) is ignored.
2. When no candidate holds a file, the diagnostic is silent. Otherwise the existing rule applies: it reports when none of the counted candidates holds the record file, and the count in its message is the counted folders.
3. The check stays read-only and never raises: an `OSError` while listing a folder counts that folder as having no files.
4. The documented limits in `docs/specs/mcp-tool-surface.md` and the function docstring say that folders without files (dot-files aside) are ignored, and narrow the grouping-folder limit to grouping or helper folders that hold files but no record (for example a `README.md`).

## Scope

**Problem statement:** the diagnostic reports a mismatch for roots whose only folders hold no files.

**In scope:**

- `record_discovery_mismatch`, its tests and the limits text.

**Out of scope:**

- the mixed-state limit (some folders renamed), which stays;
- discovery itself (`walk_wave_candidates`, `discover_wave_dirs`).

## Acceptance Criteria

- [x] AC-1: a root whose only folders are empty, hold only subfolders, or hold only `.gitkeep`, produces no diagnostic, in the flat and the nested layout.
- [x] AC-2: a folder holding a record under another filename still produces the diagnostic, including beside fileless folders and as a nested leaf under a fileless grouping folder, and the reported count covers only folders with files.
- [x] AC-3: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] Count only candidates with a file; keep the check read-only and non-raising.
- [x] Tests for AC-1 and AC-2 (flat and nested).
- [x] Update the limits in the docstring and `docs/specs/mcp-tool-surface.md`; CHANGELOG `[Unreleased]` wording for the warning.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Refinement | implementer | readiness | One function |
| Review | combined reviewer | Refinement | Code, QA, docs-contract |

## Serialization Points

- `.wavefoundry/framework/scripts/record_paths.py`, `.wavefoundry/framework/scripts/tests/test_vocabulary_profile.py`
- `docs/specs/mcp-tool-surface.md`
- `CHANGELOG.md` (shared by the changes in this wave)

## Affected Architecture Docs

`N/A`: narrows an advisory diagnostic's trigger.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The change itself |
| AC-2 | required | The diagnostic must still catch a real mismatch |
| AC-3 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Implemented: `record_paths._holds_a_file` (non-dot regular file, unlistable counts as none) filters candidates after the any-record check, which must come first because `_has_wave_md` follows a symlinked record that `_holds_a_file` skips. Delivery review: all lanes approved; D1 (the unlistable-folder test was vacuous on Python 3.13, where `Path.iterdir` also uses `os.scandir`) repaired by failing only the leaf's listing, with a control; D3 limit (a symlink-only renamed record stays silent) added to the docstring | `test_vocabulary_profile.DiscoveryDiagnosticTests` (29 tests); scratch mutation returning True on a listing error now fails `test_unlistable_folder_counts_as_fileless`; reviewer mutations (filter removed; order swapped with dot-file rule dropped) failed four and three new tests |
| 2026-09-27 | Readiness review adopted: dot-files do not count (Q1, a committed empty grouping folder holds `.gitkeep`); the grouping-folder limit is narrowed, not dropped (Q2); a nested renamed-leaf case joins AC-2 (Q3); an unlistable folder counts as fileless (Q4). All four lanes approved | readiness review |
| 2026-09-27 | Planned at the operator's request ("ignore folders that contain only subfolders"); empty folders are included because they cannot hold a renamed record either | operator direction |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | Ignore any candidate without a direct file, not only those with subfolders | The diagnostic is about records under another filename; a folder with no files cannot hold one, whether it is empty or a grouping folder | Ignore only folders whose entries are all subfolders |

## Risks

| Risk | Mitigation |
| --- | --- |
| A renamed record set nested one level deeper is missed | Discovery's candidate walk already reaches nested wave folders, which hold files and are counted |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
