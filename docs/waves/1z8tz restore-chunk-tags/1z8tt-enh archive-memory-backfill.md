# Memory Backfill From the Read-Only Archive

Change ID: `1z8tt-enh archive-memory-backfill`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-28
Wave: 1z8tz restore-chunk-tags

## Rationale

Wave `1z8ts` added a read-only archive root (`record_paths.ARCHIVE_ROOT`, read with `vocabulary_profile.ARCHIVE_PROFILE`) that lookup by id and id-collision scanning consult. The original plan (`1z827`) also asked memory backfill to read archived records as evidence, but its readiness review found that backfill assumes the live root throughout, so that part was split out here. Without it, a fork that archives its history loses those records as a source for memory.

## Requirements

1. **Inventory includes archived closed waves.** `memory_backfill.inventory_closed_waves` adds the closed waves under `record_paths.discover_archive_dirs(root)`, read with `vocabulary_profile.archive_profile()`. The archive-aware pieces:
   - `_wave_status` and `source_fingerprint` use the row's profile record filename;
   - `_contained_source_file` takes the base root the row came from (live waves root or archive root) instead of always using `_canonical_waves_dir`.

   An archive-only repository (no live waves root) still inventories its archived waves.
2. **Shadowing is decided by wave id, live first.** Rows stay keyed by folder name, with no schema change. Precedence follows `wf_get_change` and the dashboard: an archived wave is inventoried only when no live wave has the same id token (`record_paths.wave_id_of`, exact equality; prefix matching is for resolving user queries and would hide a distinct archived wave). A shadowed archived wave is skipped with an advisory `archived_wave_shadowed` diagnostic naming both paths, and the run summary reports the shadowed count.
3. **The claim flow resolves archived waves only when asked.**
   - `memory_supply.resolve_wave_dir` gains `include_archive: bool = False`. It is passed as True only by the backfill claim flow in `memory_handlers` and by `memory_propose`. It resolves live first, then the archive, and handles an archive-only repository.
   - Those callers resolve once and pass the resolved `(wave_dir, profile)` down to `draft_candidates`, including the crash-recovery call in `memory_handlers`, instead of `draft_candidates` resolving again through the live-only `_wave_dir_for_id`. The profile is the archive profile when `wave_dir` is under `roots.archive`.
   - Other callers, including the close gate's `_memory_validation_diagnostics`, stay live-only, keeping the documented rule that shared resolvers do not look at the archive by default.
   - `memory_supply`'s member and record parsing takes the wave's profile: `_ADMITTED_CHANGE_RE` becomes a per-profile builder, and `_admitted_change_ids`, `_admitted_change_docs` and `source_exploration_cost` use the profile's `RECORD_FILENAME`. `lifecycle_gate_support._extract_change_ids_from_wave_text(text, profile)` is reused where it fits.
4. **Nothing is written under the archive root.** Drafts from an archived wave carry the archived wave and change ids in `evidence` and `source_event`, and match what the same wave yields when live.
5. **Documentation matches.** `docs/architecture/layering-rules.md` names memory backfill's opt-in archive read (the `include_archive` flag) and updates the "three places" list and the "does not read the archive" sentence.

## Scope

**Problem statement:** archived closed records are not a memory-backfill source.

**In scope:**

- Backfill inventory, containment, fingerprint and status for archived waves; id-based shadowing; the opt-in claim-flow resolver; profile-aware parsing in `memory_supply`; `layering-rules.md`.

**Out of scope:**

- The archive root and its readers (delivered in `1z8ts`).
- A persisted-state schema change: `memory_backfill_waves` (keyed by run and folder name) and `memory_backfill_sources` (keyed by run and `source_event`) have no root column and need none.

## Acceptance Criteria

- [x] AC-1: with the archive unset, backfill behaviour and rows are unchanged.
- [x] AC-2: with an archive under a second profile, an archived closed wave is inventoried, claimed, drafted from and completed. Drafts carry the archived wave and change ids and match the drafts the same wave yields when live, and the archive tree stays byte-identical.
- [x] AC-3: a live and an archived wave with the same id token, even with different slugs, yield only the live wave; the archived one is skipped with `archived_wave_shadowed`, and the run summary counts it.
- [x] AC-4: an archive-only repository (no live waves root) inventories and claims its archived closed waves.
- [x] AC-5: without `include_archive`, `resolve_wave_dir` still does not return archived waves (the close gate is unchanged).
- [x] AC-6: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] Inventory, per-row profile for status and fingerprint, base-root containment, archive-only repository.
- [x] Id-token shadowing with the diagnostic and summary count.
- [x] `resolve_wave_dir(include_archive=...)` for the claim flow and `memory_propose`; pass the resolved `(wave_dir, profile)` into `draft_candidates`; per-profile parsing in `memory_supply`; a unit test that `memory_propose` on an archive-only id returns drafts.
- [x] Tests; `layering-rules.md`; CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Backfill | implementer | readiness | Key decided: folder name, id-token shadowing, live first |
| Review | combined reviewer | Backfill | Code, QA, docs contract |

## Serialization Points

- `.wavefoundry/framework/scripts/memory_backfill.py`, `.wavefoundry/framework/scripts/memory_supply.py`, `.wavefoundry/framework/scripts/lifecycle_gate_support.py`, `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/tests/`
- `docs/architecture/layering-rules.md`
- `CHANGELOG.md`

## Affected Architecture Docs

`docs/architecture/layering-rules.md`: the archive paragraph (the opt-in resolver flag, the list of archive readers, and the backfill sentence).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | No change for users who do not opt in |
| AC-2 | required | The feature's purpose |
| AC-3 | required | A shadowed archive copy must not merge into or replace the live history |
| AC-4 | important | The fork migration can leave only an archive |
| AC-5 | required | Keeps the close gate and other resolvers live-only |
| AC-6 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Implemented (implementer agent). `memory_backfill`: `_canonical_waves_dir(root, archive=True)` (folded in to satisfy the containment census), base-root containment, per-profile `_wave_status` and `source_fingerprint`, `_inventory` with id-token shadowing (`shadowed_archive_waves`, `archived_wave_shadowed` diagnostics, `archived_waves_shadowed` summary count), archive-only repositories. `memory_supply`: per-profile `_admitted_change_re`, `source_exploration_cost(root=...)`, `resolve_wave_dir(include_archive=...)` (live first; shadowed archived waves skipped), `wave_profile`, and `draft_candidates(wave_dir=, profile=)`. `memory_handlers`: `memory_propose` and the backfill claim flow, including crash recovery, pass the resolved directory and profile. Deviations: `lifecycle_gate_support._extract_change_ids_from_wave_text` not reused (different grammar would change live parsing); close-time auto-population reaches the archive through `memory_propose`, but a live wave being closed resolves live first, and `_memory_validation_diagnostics` stays live-only. New `tests/test_archive_memory_backfill.py` (9 tests); mutants (prefix shadowing, live profile for archive, live-only re-resolution, `include_archive` default True) each fail. Gapfill: none for retrieval | `test_archive_memory_backfill` 9 OK; focused suites |
| 2026-09-28 | Readiness confirmation round: B2 resolved. Adopted R1 (`draft_candidates` re-resolved live-only; the claim flow now passes the resolved wave directory and profile down) and R2 (shadow on exact id-token equality) | readiness confirmation |
| 2026-09-28 | Readiness review. B2 (blocking) adopted: drafts carry ids, not paths, so Requirement 4 and AC-2 now require archived ids and drafts that match the live equivalent. N8: archive-only repository handled (AC-4). N9: `_wave_status`, `source_fingerprint` and containment take the row's profile and base root. N10: `memory_supply`'s import-time `_ADMITTED_CHANGE_RE` and `RECORD_FILENAME` uses become per-profile. N11: shadowing by id token, not folder name. N12: opt-in `include_archive` keeps shared resolvers live-only (AC-5). N13: shadowed count in the run summary. N14: Serialization Points completed. Persisted state confirmed: no root column, no schema change | readiness review |
| 2026-09-28 | Split from `1z827` by its readiness review (finding F4): the claim flow re-resolves waves in the live root, `memory_supply` parses with the live profile at import, and backfill rows are keyed by folder name | `1z827` readiness review |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | Keep the folder-name key; shadow by id token with live precedence and a diagnostic | New ids cannot collide with archived ones (`lifecycle_id._existing_prefixes` includes the archive), so a clash means copied, restored or imported history, which should be reported, not modelled. Id-token matching mirrors `wf_get_change` and avoids two rows emitting the same `source_event` | Carry the root in the key or schema; prefer the archived copy |
| 2026-09-28 | Opt-in `include_archive` on `resolve_wave_dir` | Keeps the documented rule that shared resolvers do not look at the archive, and leaves the close gate live-only | A backfill-local archive resolver (duplicates resolution) |
| 2026-09-28 | Admitted to wave `1z8tz` with `1z8ty` at the operator's request | Batching; the two changes share no code | Separate wave |

## Risks

| Risk | Mitigation |
| --- | --- |
| An operator copies history into the archive instead of moving it | `archived_wave_shadowed` names both paths and the summary counts it; the live copy is used |
| Enabling an archive changes an in-flight run's inventory digest | Runs are idempotent; drafts are keyed by `source_event`, so re-pending does not duplicate |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
