# A Profile-Aware Journal Migration With A Public Entry Point

Change ID: `1zuq6-enh profile-aware-journal-migration`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-05
Wave: 1zv87 downstream-security-hardening

## Rationale

Downstream request (Waveforge R5): `_migrate_journals` reads only `^wave-id:` and looks waves up flat under the waves root, so a repository whose vocabulary profile uses another id key (`set-id`), nests waves below the root, or has archived waves gets no relocation; on Waveforge it relocated none of 26 content journals. It is also private, so a distribution or operator cannot run it (or preview it) after an upgrade.

## Requirements

1. Journal identity matches the active vocabulary profile's id key (`ID_KEY`, read at call time from the module imported from the extracted tree) or the legacy `wave-id` key (journals predate profiles); the pristine-template comparison keeps its `wave-id` literal (it deletes only on an exact match).
2. The wave folder for a journal comes from `record_paths` discovery (`discover_wave_dirs` over the waves and archive roots, `wave_id_of`), built once per run into a map keyed by the lower-cased id token (`wave_id.split(" ", 1)[0].lower()`, matching `wave_id_of`) over the waves and archive roots together; a token that maps to more than one folder is left in place and listed; a journal whose single match is an archived wave is left in place and listed (the archive root is read-only, wave 1z8ts), so only folders under the waves root, flat or nested, are relocation targets; and any discovery exception (`RecordRootUnreadable`, `RecordLayoutInvalid`, other errors) skips relocation and lists the journals.
3. Every path still goes through the `1zuq5` containment and exclusive-write rules; discovered folders are re-checked with `contained_path(..., refuse_symlink_components=True)`.
4. A public function `migrate_journals(root, *, apply=False)` returns a report (`deleted`, `moved`, `left`, each with repository-relative paths) and changes nothing when `apply` is False; `_migrate_journals(root)` becomes `migrate_journals(root, apply=True)` plus its existing printed summary, so the post-extract call is unchanged.
5. Seed `210-migrate-journals.prompt.md` names the public function for a preview before the operator-invoked migration (seed gate opened and closed around the edit).
6. CHANGELOG gets a bullet under `## [1.29.0]` `### Added`.

## Scope

**Problem statement:** the only mechanical journal migration ignores non-default record profiles and cannot be previewed or called directly.

**In scope:**

- `.wavefoundry/framework/scripts/upgrade_extensions.py`; tests; seed 210; CHANGELOG.

**Out of scope:**

- Changing which paths docs-lint or the reconcile scan ignore.

## Acceptance Criteria

- [x] AC-1: A repository with `ID_KEY = "set-id"` (via a test vocabulary profile), a nested wave and an archived wave, each with a content journal named for its id: the nested wave's journal lands byte-exact in its record folder, the archived wave's journal is left in place and listed with the archive reason, the archive folder is byte-identical, and a byte-exact default-profile scaffold is still deleted.
- [x] AC-2: An id discovered in two folders leaves its journal in place and lists it.
- [x] AC-3: `migrate_journals(root, apply=False)` reports what would happen and leaves the tree byte-identical; `apply=True` performs it; the report paths are repository-relative.
- [x] AC-4: The `1zuq5` link tests still pass against discovered folders (a linked nested wave folder is refused).
- [x] AC-5: Seed 210 names the preview; CHANGELOG Added bullet; docs validate.
- [x] AC-6: Reverting identity to the `wave-id` literal, or discovery to the flat lookup, fails the AC-1 test (scratch copy).

## Tasks

- [x] Use the profile id key and record discovery
- [x] Add `migrate_journals(root, *, apply=False)` and keep `_migrate_journals` as the applying wrapper
- [x] Tests for a non-default profile, nested and archived waves, ambiguity and dry run
- [x] Seed 210 note
- [x] Show the mutants fail in a scratch copy
- [x] CHANGELOG Added bullet

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| profile-migration | implementer | 1zuq5 | same function; after the safety change |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/seeds/210-migrate-journals.prompt.md`

## Affected Architecture Docs

N/A: one migration function and a seed note.

## Platform Behavior

Platform-neutral beyond `1zuq5`'s file rules.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the requested behavior |
| AC-2 | required | no guessing |
| AC-3 | required | public entry point |
| AC-4 | required | safety preserved |
| AC-5 | required | docs |
| AC-6 | required | pins catch a revert |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-05 | Implemented: `migrate_journals(root, *, apply=False)` returning `{deleted, moved, left, warnings}` (repository-relative); `_migrate_journals` applies it and prints the summary; identity by profile `ID_KEY` or legacy `wave-id`; one id-token map over waves and archive; archived matches left with the read-only reason; discovery errors skip relocation. Two existing tests now create the record file (discovery needs it). Tests `JournalMigrationProfileTests` (4) | mutants (`wave-id` literal, flat lookup, archive written) fail |
| 2026-10-05 | Implementation note: archived waves are discovered (for identity and ambiguity) but never written, because the archive root is read-only (wave 1z8ts); the implementer first relocated into the archive and this was corrected | coordinator review of the implementer report |
| 2026-10-05 | Readiness review folded in: legacy `wave-id` key also matched, id-token map over waves and archive, discovery errors skip relocation | readiness F6 |
| 2026-10-05 | Planned from the Waveforge request R5 | `_migrate_journals` reads `^wave-id:` and `record_roots.waves / wave_id` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-05 | Keep the private name as the post-extract caller | the post-extract step and its tests stay unchanged; the public function is the new surface | rename in place (breaks the existing call and any older runner) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The vocabulary profile module may be unavailable | the post-extract step runs the extracted (new) tree; on an import failure relocation is skipped and journals are listed, as today |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
