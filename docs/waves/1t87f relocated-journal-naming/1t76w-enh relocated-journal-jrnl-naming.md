# Relocated Wave Journals Carry the -jrnl Type Suffix

Change ID: `1t76w-enh relocated-journal-jrnl-naming`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-22
Wave: `1t87f relocated-journal-naming`

## Rationale

Operator directive after the 1t9wa close: wave journals relocated into their wave directories should carry a lifecycle type suffix, `<prefix>-jrnl <slug>.md`, consistent with every other typed artifact in a wave folder (`-ref`, `-feat`, `-mem`, and the rest). The 1t9wa migration relocated them under their bare scaffold name (`<wave-id-with-dashes>.md`, e.g. `1t3gt-mcp-tool-hygiene.md`), which reads as an untyped sibling of the change docs. The `-jrnl` token was considered during the 1t9w8 naming discussion and deemed moot for LIVE journals under retirement; it is not moot for the relocated historical artifacts, which live on permanently inside wave folders.

## Requirements

1. **Upgrade migration mints the typed name.** `_migrate_journals` relocates a wave journal to `docs/waves/<wave-id>/<prefix>-jrnl <slug>.md`, where `<prefix>` and `<slug>` come from splitting the wave id on its first space (the slug part is already dash-form in wave directory names). Source detection (filename equals the wave id with dashes) is unchanged; the destination-exists guard applies to the new name. No repository has run the old relocation besides this one (the hook is unreleased), so no old-name compatibility pass is needed in the hook.
2. **This repository's 16 relocated journals rename** to the `-jrnl` form in place (docs-only edit; content untouched; historical wave archives otherwise unmodified per the cleanup policy).
3. **The Migrate journals prompt teaches the naming:** seed 210's wave-journal step names the `<prefix>-jrnl <slug>.md` destination form so operator-invoked migrations in field repos converge on the same convention.
4. **Lint stays clean by construction:** wave-directory lint checks are content-driven for non-wave.md files (verified against `check_wave_docs`), so no grammar or constants change is required; the docs gate must pass after the rename.

## Scope

**Problem statement:** relocated historical wave journals are the only typed-artifact class in wave folders without a lifecycle type token in their filename.

**In scope:**

- `_migrate_journals` destination naming in `upgrade_extensions.py`
- `JournalMigrationTests` relocation expectations
- Local rename of the 16 relocated journals
- Seed 210 destination-naming note

**Out of scope:**

- Renaming any other historical artifact; touching journal content
- Reintroducing live journals or a `jrnl` change kind in creation tools (`VALID_CHANGE_KINDS` unchanged)
- Old-relocation-name compatibility in the hook (nothing released ran the old form)

## Acceptance Criteria

- [x] AC-1: against a fixture repo, `_migrate_journals` relocates a content-bearing wave journal to `<prefix>-jrnl <slug>.md` inside its wave directory; the destination-exists guard and left+reported classes behave as before; re-run is a no-op.
- [x] AC-2: this repository's 16 relocated journals carry the `-jrnl` form; zero bare-name relocated journals remain; docs gate passes.
- [x] AC-3: seed 210 names the destination form; full framework test suite passes.

## Tasks

- [x] Update `_migrate_journals` destination naming + `JournalMigrationTests`.
- [x] Rename the 16 local relocated journals; docs gate.
- [x] Seed 210 naming note; full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| hook-naming | implementer | — | upgrade_extensions.py + tests |
| local-rename | implementer | hook-naming | Mirrors the hook's exact naming |

## Serialization Points

- Local rename mirrors the hook's naming function output; do the hook first.

## Affected Architecture Docs

N/A — filename convention for relocated historical artifacts; no boundary, flow, or verification impact.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The convention ships to field repos through the hook. |
| AC-2 | required | The operator-directed local outcome. |
| AC-3 | required | Prompt-path convergence + standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-22 | Drafted from the operator directive following the 1t9wa close; verified `check_wave_docs` is content-driven for non-wave.md files so no lint grammar change is needed. | Session; `wave_validators.py` `check_wave_docs` read |
| 2026-07-22 | Implemented: `_migrate_journals` destination = `<prefix>-jrnl <slug>.md` (partition on first space; report line now names the destination); relocation tests updated with a bare-name-absence pin (8/8 OK); seed 210 step 2 names the form; 16 local journals renamed via the identical split rule; pre- and post-rename censuses found zero live bare-name references; docs gate clean. Note: `wf_create_wave` for this wave itself ran on a stale pre-retirement server session and scaffolded a journal — removed, heading fixed, `wf_reload_mcp` applied (impl now matches disk). | Rename output (16); `JournalMigrationTests` 8 OK; `wf_validate_docs` ok |
| 2026-07-22 | Full suite green post-implementation: 6,138 tests across 59 files OK in a single run. AC-1 through AC-3 met. | Suite output |
| 2026-07-22 | Gapfill: implement-stage MCP retrieval telemetry is zero because the exploration for this change ran at plan stage (code_keyword censuses for ITEM_ID/CHANGE_KINDS grammar and code_read of `check_wave_docs`, recorded pre-activation); the implementation itself was bulk-mechanical edits to already-located sites (one hook block, two test expectations, one seed line, a scripted 16-file rename), which is the justified harness-fallback case. The 62 changed non-docs files in the advisory are the accumulated uncommitted stack from waves 1t9tk/1t9w8/1t9wa, not this wave's diff. | Plan-stage retrieval in session; wave diff = upgrade_extensions.py + test_upgrade_wavefoundry.py + seed 210 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-22 | Destination form `<prefix>-jrnl <slug>.md` (space form). | Operator directive; consistent with the `<prefix>-<type> <slug>` grammar of change docs and memory records ("we use space for everything else"). | Dash-only form (inconsistent with sibling artifacts); leaving bare names (the state being corrected). |
| 2026-07-22 | No old-name compatibility pass in the hook. | The relocation hook has never shipped; only this repository ran it, and this change renames those 16 in the same wave. | Permanent compat scanning for a name that never reached the field. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A live doc references a relocated journal by its bare name. | Repository-wide reference census before and after the rename; docs gate link integrity. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
