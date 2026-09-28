# Read-Only Archive Record Root

Change ID: `1z827-feat read-only-archive-record-root`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-28
Wave: 1z8ts read-only-archive-root

## Rationale

The RFC "Vocabulary profiles and an optional parent tier" (section 6) asks for a read-only archive of closed records frozen under older names: a fork's rename history, or Wavefoundry's own future renames. Record names now come from `vocabulary_profile` (change `1z826`). A repository that switches vocabulary either renames every historical record or loses them from lookup, id-collision scanning and memory backfill. An archive root, read with its own profile and never written, keeps that history available without rewriting it.

## Requirements

1. **Archive root constant.** `record_paths` gains `ARCHIVE_ROOT: str | None = None`, fork-edited like the other roots and read from no configuration. When set, it is validated with the same `_check_root` rules as `WAVES_ROOT` (relative, inside the repository, no symlink or case alias, no file or dangling-link ancestor) and must differ from `WAVES_ROOT` and `PLANS_ROOT` and nest in neither, in either direction, by spelling or inode. A violation raises `RecordLayoutInvalid` naming `record_paths.ARCHIVE_ROOT`. `RecordRoots` gains `archive` and `archive_rel`, both `None` when unset. `layout_constants()` returns the same four-tuple as today when the archive is unset and appends the archive root only when it is set, so default cache keys stay byte-equal. The archive is walked with the live `NESTED` and `MAX_DEPTH`. `tests/record_layout_support` gains an `archive_root` key.
2. **Archive profile.** `vocabulary_profile` gains `ARCHIVE_PROFILE: dict[str, str] | None = None`. When set, it must hold exactly the twelve fields (the names of the module constants); `PREVIOUS_STATUS_LABEL` is derived from it as for the live profile. `validation_errors(fields=None)` validates the live constants by default and a given mapping otherwise, with the same rules, and the archive mapping is validated at import, failing closed with the field named. `archive_profile()` returns the effective archive profile (the live one when unset) as a plain object exposing the same field names, `PREVIOUS_STATUS_LABEL` and the `_RE` fragments; the module keeps importing only `re`.
3. **Archive discovery.** `record_paths.walk_wave_candidates` and `_has_wave_md` take an optional record filename, and `discover_archive_dirs(root)` returns the archive's wave folders (those holding the archive profile's record file), or an empty list when `ARCHIVE_ROOT` is unset or absent.
4. **Read paths consult the archive after the live roots.**
   - `wf_get_change`: at its two clean miss points (single-change lookup after `_resolve_change_doc_matches` finds nothing; wave lookup after `_resolve_wave_md_matches` finds nothing) it searches the archive: change documents by id stem, and archived waves by folder name or the archive profile's id key, with members parsed through profile-parameterized versions of the wave-id and member-id extraction. Archive hits carry `"archived": true`. The shared resolvers themselves do not change.
   - The dashboard document view (`dashboard_server._handle_doc`) adds the archive root to its allowed roots and, when no live document matches, serves the archived one with an `X-Wavefoundry-Archived: 1` response header.
   - `lifecycle_id._existing_prefixes` adds the archive's folder-name and document-stem prefixes, so a new id never collides with an archived one. This also raises `scan_max_prefix_value` (upgrade id provisioning) to cover archived prefixes, which is intended and tested.
5. **Nothing writes under the archive root.**
   - A writer-only check, `_refuse_if_archived(root, token, kind)`, runs on the `wave_not_found` or `change_not_found` branch of each lifecycle writer that takes an existing wave or change id: `wf_add_change`, `wf_remove_change`, `wf_mark_ac`, `wf_mark_task`, `wf_review_event`, `wf_prepare_wave`, `wf_pause_wave`, `wf_review_wave`, `wf_implement_wave`, `wf_close_wave` and `wf_reopen_wave`. When the id resolves only in the archive, the writer returns the named `archived_record_read_only` diagnostic instead of the not-found one and changes nothing. Read tools and undecorated helpers are untouched.
   - The docs gardener skips the archive in its own markdown enumeration, its changed-file input and its explicit-path input.
   - `reconcile_scan.excluded_dirs_for` excludes the archive root, as it does the waves root.
6. **Lint.** Docs-lint excludes the archive root from `iter_markdown_docs` and from the changed-file path (`is_under_markdown_scan_root`), so metadata, link and record rules do not run on archived files; the secrets scan still covers them. Links from live documents into the archive still resolve. Docs-lint checks only that each archive folder's record can be read under the archive profile, reporting a failure through an advisory sensor, `archive_record_unreadable`.
7. **Documentation.** `docs/architecture/current-state.md` and `docs/architecture/layering-rules.md` describe the archive root and profile; `docs/specs/mcp-tool-surface.md` documents the `archived` flag and `archived_record_read_only`; CHANGELOG `[Unreleased]`.

## Scope

**Problem statement:** after a vocabulary change, older records become invisible to lookup and id-collision scanning.

**In scope:**

- the archive root and profile, their validation and discovery;
- the three read paths in Requirement 4;
- the writer refusal, and the gardener, reconcile-scan and lint exemptions;
- tests and docs.

**Out of scope:**

- memory backfill of archived waves: its claim flow re-resolves waves in the live root (`memory_supply.resolve_wave_dir`), `memory_supply` parses with the live profile at import, and backfill rows are keyed by folder name, so it needs its own change (planned as a follow-up);
- migration tooling that moves records into the archive;
- listing archived waves in `wf_list_waves`, `wf_current_wave` or the dashboard snapshot (lookup by id only);
- a separate archive layout (`NESTED`, `MAX_DEPTH`) or more than one archive root;
- retrieval indexing changes: archived documents are indexed as documents today, as any file under `docs/` is.

## Acceptance Criteria

- [x] AC-1: with `ARCHIVE_ROOT` unset, behavior is unchanged: the existing suites pass without edits to their assertions (the one exception is the recorded-decision sensor pin in `test_docs_lint`, which must name every advisory sensor and so gains `archive_record_unreadable`), and `layout_constants()` and every cache key are byte-equal for the shipped constants.
- [x] AC-2: with an archive root holding a wave and change written under a second profile, `wf_get_change` finds the archived change by id and the archived wave by id with its members, each marked archived; the dashboard document view serves the archived change with the archived header; a newly minted id skips an archived prefix and `scan_max_prefix_value` covers it. Each has a control with the archive unset that finds nothing.
- [x] AC-3: each of the eleven writers in Requirement 5 given an archived wave id, and `wf_add_change` given an archived change id, returns `archived_record_read_only` and changes no file; a live record with the same id wins over the archive; and a full live lifecycle run (create, admit, prepare, review evidence, close, gardening with explicit archive paths, and lint) leaves the archive tree byte-identical.
- [x] AC-4: an archive root equal to, inside, or containing a live root, or one that is absolute, escapes the repository or is a symlink alias, refuses with `record_layout_invalid` naming `record_paths.ARCHIVE_ROOT`.
- [x] AC-5: an `ARCHIVE_PROFILE` with a missing, extra or invalid field refuses to import with the field named; docs-lint passes an archive document that would fail live checks (full and changed-file runs), still reports a planted secret in it, and reports an unreadable archive record through `archive_record_unreadable` without failing.
- [x] AC-6: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] `ARCHIVE_ROOT`, `RecordRoots.archive`, validation, `layout_constants`, the record-filename parameter, `discover_archive_dirs`, test support key.
- [x] `ARCHIVE_PROFILE`, `validation_errors(fields=None)` and `archive_profile()`.
- [x] Read paths: `wf_get_change` (both miss points), dashboard document view, `lifecycle_id._existing_prefixes`.
- [x] `_refuse_if_archived` on the eleven writers; gardener, reconcile-scan and lint exemptions; the advisory sensor.
- [x] Tests for AC-1 to AC-5.
- [x] Docs and CHANGELOG; plan the memory-backfill follow-up.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Archive root | implementer | readiness | Profile first, then roots, readers, refusal |
| Review | combined reviewer | Archive root | Code, QA, architecture, docs-contract |

## Serialization Points

- `.wavefoundry/framework/scripts/record_paths.py`, `.wavefoundry/framework/scripts/vocabulary_profile.py`, `.wavefoundry/framework/scripts/lifecycle_id.py`, `.wavefoundry/framework/scripts/dashboard_server.py`, `.wavefoundry/framework/scripts/docs_gardener.py`, `.wavefoundry/framework/scripts/reconcile_scan.py`, `.wavefoundry/framework/scripts/wave_lint_lib/`, `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/tests/`
- `docs/architecture/current-state.md`, `docs/architecture/layering-rules.md`, `docs/specs/mcp-tool-surface.md`
- `CHANGELOG.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/layering-rules.md`: a third record root with read-only semantics and a second vocabulary profile.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | No change for users who do not opt in |
| AC-2 | required | The feature's purpose |
| AC-3 | required | Read-only is the safety property |
| AC-4 | required | Fail closed on overlapping roots |
| AC-5 | required | Fail closed on a bad profile; lint must not reject history |
| AC-6 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Cross-platform review (operator-requested before close): no blocking defect; path spelling, case-insensitive filesystems, drive letters and junctions are handled. Taken: X1, the two symlink-creating tests are skipped on Windows (creating symlinks needs a privilege there) and the six non-symlink layout cases moved to their own unguarded test; X2, archived `path` strings use `relative_to(root).as_posix()` | cross-platform review; `test_archive_root` 21 OK |
| 2026-09-28 | The full suite's containment census (`test_path_containment`) flagged `_archive_file_ok` for an ad-hoc `is_relative_to`; it now calls the single owner `path_containment.contained_resolved_path` with the same resolved inputs, so behavior is identical. Reviewer reverified D1 and D2 with its own mutation and approved the AC-3 wording | `test_path_containment` 23, `test_archive_root` 20 OK |
| 2026-09-28 | Delivery review: code, architecture and docs-contract ready, security approved; QA and red-team requested changes. D1: the gardener test was vacuous (the archived fixture had no `Last verified` line to rewrite), fixed with a stale line, an exit-code check and an archive-unset control that is stamped. D2: the full-lifecycle clause of AC-3 had no test, now `ArchiveUntouchedByLiveLifecycleTests` (create, admit, prepare, readiness and delivery evidence, close, then gardening with `--all-docs` and an explicit archived path, and lint, archive digest unchanged). D3 docs wording; D4 AC-3 names `wf_add_change` for change ids (the other writers target live wave folders, so a change id cannot reach the archive through them); D5 the archive walk in `_existing_prefixes` uses the archive record filename | `test_archive_root` (20 tests); scratch mutation disabling `docs_gardener._outside_archive` fails both the gardener test and the lifecycle test |
| 2026-09-28 | Implemented. `vocabulary_profile`: `ARCHIVE_PROFILE`, `FIELD_NAMES`, `validation_errors(fields=None)` (exact keys, derived previous-status label), `archive_profile()` returning a plain `_Profile`; validated at import. `record_paths`: `ARCHIVE_ROOT`, `RecordRoots.archive`/`archive_rel`, `_root_overlap` for the archive against both live roots, `layout_constants()` appending only when set, `walk_wave_candidates(base=, record_filename=)`, `discover_archive_dirs`. `lifecycle_id._existing_prefixes` adds archived names. `server_impl`: `_archived_change_matches`, `_archived_wave_matches` and `_archived_wave_response` (containment-checked, symlinks skipped (N1), members only from the archived folder (N2)) at `wf_get_change`'s two miss points; `_refuse_if_archived` in front of the not-found diagnostic of the eleven writers. Dashboard allowed roots, archive fallback and header. Gardener `_outside_archive` on all three inputs; lint `archive_root`, `is_under_archive_root`, `iter_markdown_docs` and `is_under_markdown_scan_root` exclusions; `archive_record_unreadable` sensor (recorded decision); `reconcile_scan.excluded_dirs_for`. Follow-up `1z8tt-enh archive-memory-backfill` planned. Gapfill: the edits were applied by scripted exact-string replacement for bulk mechanical routing (eleven writer sites, three module constants); reads used `code_read`/`code_keyword` | `test_archive_root` (19 tests); scratch mutations (lint exclusion removed; one writer's refusal removed) each failed a named test; `test_docs_lint` 1115, `test_dashboard_server` 215, record-layout, lifecycle-id, gardener, reconcile-scan and vocabulary suites OK |
| 2026-09-28 | Readiness review requested changes; adopted. F1 to F3: the refusal is a writer-only check on eleven named writers, not a raise in the shared resolvers. F4: memory backfill moved to a follow-up change. F5: `layout_constants()` appends the archive only when set. F6: parsers and the walk take a profile or record filename. F7: `validation_errors(fields=None)`, exact keys, derived previous-status label, `re`-only imports. F8: dashboard allowed roots and an archived header. F9: gardener and changed-file lint exclusions, secrets scan kept. F10: dropped. F11: provisioning effect stated, reconcile-scan exclusion. F12: writers listed. F13: test support key | readiness review |
| 2026-09-28 | Replanned against the delivered `1z826`: the archive profile is a validated mapping read through `archive_profile()`; the refusal reuses the `AmbiguousWaveId` pattern in `_fail_closed_on_record_layout`, which wraps all 17 lifecycle tools; `lifecycle_id._existing_prefixes` needs only names, so it reads the archive without a profile | `code_read` of `lifecycle_id._existing_prefixes`, `server_impl._resolve_wave_md_matches`, `_fail_closed_on_record_layout`, `wf_get_change_response` |
| 2026-09-27 | Planned from RFC section 6; depends on `1z826` | RFC |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | The archive profile is one optional mapping in `vocabulary_profile`, defaulting to the live profile | Keeps one owner for record names; a fork that archives without renaming sets nothing | A second profile module; per-reader overrides |
| 2026-09-28 | A writer-only check on each named writer's not-found branch | Raising from the shared resolvers would also hit read tools that must find the archive and undecorated telemetry helpers that expect `None` (readiness F1, F2) | Raise in the resolvers and convert in the decorator |
| 2026-09-28 | Memory backfill of the archive is a separate follow-up change | Its claim flow, parsing and row keys all assume the live root (readiness F4); bundling it would double this change | Scope it fully here |
| 2026-09-28 | Lookup by id only; no archive in listings | Listings drive lifecycle actions; archived records are history, found when asked for | Show archived waves in `wf_list_waves` |
| 2026-09-27 | A separate change after `1z826` | The archive needs a second profile, which only exists once the profile module does | Bundle into `1z826` |

## Risks

| Risk | Mitigation |
| --- | --- |
| A writer path is missed and writes into the archive | AC-3 drives every decorated tool with an archived id and diffs the archive tree across a full live lifecycle, gardening and lint |
| A live and an archived record share an id | Live-first order; AC-3 checks the live record wins |
| Existing caches keep a stale layout | `layout_constants()` includes the archive root, and AC-1 pins the unchanged keys for the default |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
