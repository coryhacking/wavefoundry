# The Journal Migration Follows Links Out Of The Repository

Change ID: `1zuq5-bug journal-migration-follows-links`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-05
Wave: 1zv87 downstream-security-hardening

## Rationale

Downstream report (Waveforge, private, reproduced here at `fdd8de15`): `upgrade_extensions._migrate_journals` runs from the post-extract step whenever the repository's own `VERSION` predates 1.15.0 and `docs/agents/journals/` exists, so the repository decides whether it runs. None of its file operations refuses a link: the journals folder and each journal are followed for reads, the wave folder is followed, the destination is guarded only by `not destination.exists()` (False for a dangling link) before `write_text` follows it, and `path.unlink()` removes the source after the copy. A repository can therefore make an upgrade create a file it chooses outside the repository (any path that does not exist yet, with journal text it controls), and a linked journals folder lets the upgrade delete journal-shaped files outside it. Present since 1.15.0.

## Requirements

1. Before any read, write or removal, the source must be a regular file (`S_ISREG` via `lstat`, so a FIFO or device named `*.md` is never opened), and `_migrate_journals` resolves the journals folder, each journal and each wave folder through `path_containment.contained_path(root, ..., refuse_symlink_components=True)`; any `None` (a link component, an escape, an error) leaves that journal in place and lists it, and a refused journals folder ends the migration with nothing touched.
2. A journal with more than one hard link (`st_nlink > 1`) is left in place: removing it would not remove the content, and copying it would duplicate a file shared with another path.
3. The destination is created only through `os.open` with `O_CREAT | O_EXCL | O_WRONLY` and `O_NOFOLLOW` where available (`O_BINARY` on Windows), on the absolute path inside the contained wave folder; an existing name, including a dangling link, is never followed or replaced (the journal is left in place). The open uses the absolute path `contained_path` returns (`dir_fd` is unsupported on Windows). Content is read as bytes and the move writes the original bytes, so newlines are preserved; the pristine-scaffold comparison uses newline-normalized text, so a CRLF scaffold from a Windows checkout is still recognized and deleted.
4. The source is removed only after the destination write completes and a fresh `lstat` shows the source is still a regular, singly linked file inside the contained journals folder; otherwise it is left in place.
5. A pristine scaffold is deleted only under the same source checks (contained, not a link, singly linked).
6. No new behavior for well-formed repositories: the existing `JournalMigrationTests` stay green (this repository no longer has `docs/agents/journals/`).
7. CHANGELOG gets a bullet under `## [1.29.0]` `### Security` stating the impact and affected versions (1.15.0 to 1.28.0) without exploit steps.

## Scope

**Problem statement:** an upgrade-time migration follows repository-controlled links when it reads, writes and deletes files.

**In scope:**

- `.wavefoundry/framework/scripts/upgrade_extensions.py` `_migrate_journals`; tests; CHANGELOG.

**Out of scope:**

- Profile-aware discovery and the public entry point (`1zuq6`, which builds on this).
- Publishing a security advisory (operator decision).

## Acceptance Criteria

- [x] AC-1: A dangling-link destination is never followed: the link target outside the repository is not created, the source journal stays, and the journal is listed as left.
- [x] AC-2: A linked journals folder, a linked journal, a hard-linked journal and a linked wave folder are each refused: nothing outside the repository is read, created or removed, and no source is removed.
- [x] AC-3: A destination that already exists as a regular file is left alone and the source stays.
- [x] AC-4: A well-formed repository migrates as before: a pristine scaffold is deleted (also when its newlines are CRLF), a content journal moves byte-exact (CRLF content keeps CRLF), a role journal stays, and a FIFO named `*.md` is left without being opened.
- [x] AC-5: Removing the containment checks, or using `write_text` instead of the exclusive open, fails the AC-1/AC-2 tests (scratch copy).
- [x] AC-6: CHANGELOG Security bullet; docs validate.

## Tasks

- [x] Route every journal path through `contained_path(..., refuse_symlink_components=True)` and the hard-link check
- [x] Write the destination with an exclusive, no-follow open; read and write bytes
- [x] Re-check the source with `lstat` before removing it
- [x] Add link, hard-link, existing-destination and regression tests
- [x] Show the mutants fail in a scratch copy
- [x] CHANGELOG Security bullet

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| migration-safety | implementer | — | upgrade_extensions only |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`

## Affected Architecture Docs

N/A: a single function's file handling; the containment helper already exists (`path_containment`).

## Platform Behavior

POSIX: `O_NOFOLLOW` refuses a final-component link; directory links are refused by the lstat walk. Windows: no `O_NOFOLLOW`; `contained_path`'s lstat walk refuses symlinks, while a directory junction (not reported as a link) is caught only by the post-resolve containment check when it escapes; `O_CREAT|O_EXCL` refuses an existing name (including a link); files are opened `O_BINARY`; `st_nlink` is populated. On POSIX `O_EXCL` already refuses a final symlink, and `O_NOFOLLOW` is kept as defense in depth. macOS, Linux and WSL2 follow POSIX.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the reproduced write |
| AC-2 | required | every reported link path |
| AC-3 | required | no overwrite |
| AC-4 | required | no regression |
| AC-5 | required | pins catch a revert |
| AC-6 | required | release notes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-05 | Implemented in `upgrade_extensions.py`: every journal path through `contained_path(..., refuse_symlink_components=True)`; regular-file and single-link checks via `lstat`; source read with `O_NOFOLLOW|O_NONBLOCK` plus `fstat`; destination `os.open(O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW|O_BINARY)` on the absolute path, partial file removed on failure; original bytes written; CRLF-normalized scaffold comparison; source removed only after a fresh containment and `lstat` same-file check (POSIX compares `st_dev`/`st_ino`). Tests `JournalMigrationLinkSafetyTests` (9) | 21 journal tests OK in a scratch copy; mutants (containment removed, `write_text`) fail |
| 2026-10-05 | Readiness review folded in: regular-file check, absolute-path open, newline-normalized scaffold comparison, junction note, test file is `test_upgrade_wavefoundry.JournalMigrationTests` | readiness F4, F5, F7 |
| 2026-10-05 | Planned from the Waveforge private report S1; reproduced by the verification reviewer in a scratch folder | dangling-link destination created a file outside the fake repository; source unlinked |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-05 | Leave unsafe journals in place and list them, rather than failing the upgrade | the migration is advisory housekeeping; refusing one journal must never block an upgrade | abort the upgrade on any link (blocks upgrades over a harmless link) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `contained_path` is not race-free | the destination open is exclusive and no-follow, and the source is re-checked with `lstat` right before removal |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
