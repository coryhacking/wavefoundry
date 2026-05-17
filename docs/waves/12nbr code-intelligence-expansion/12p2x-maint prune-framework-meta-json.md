# Prune framework index metadata alongside pack-removed files

Change ID: `12p2x-maint prune-framework-meta-json`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-16
Wave: 12nbr code-intelligence-expansion

## Rationale

The framework pack is shipped with a prebuilt LanceDB index. When `prune_framework.py` removes pack-delivered files that disappeared between manifests, the corresponding entries in `.wavefoundry/framework/index/meta.json` can remain behind. That leaves the framework layer reporting stale removed paths even though the files were pruned from disk.

This change makes prune repair the shipped framework index metadata at the same time it removes files, so the installed pack’s framework index snapshot stays aligned with the files actually present after upgrade.

## Requirements

1. When `prune_framework.py` deletes pack-removed files, it must also remove the corresponding entries from framework index metadata.
2. The metadata repair must handle both `file_meta` and legacy `file_hashes` shapes.
3. The repair must be conservative: only paths that were actually pruned from disk should be removed from metadata.
4. The prune tool must remain safe for non-index framework files and user-created local files.

## Scope

**Problem statement:** `meta.json` can still list framework paths that were removed by prune, causing the framework layer to stay stale after upgrade.

**In scope:**

- `prune_framework.py`
- `test_prune_framework.py`

**Out of scope:**

- Rebuilding the framework index during ordinary upgrades
- Changing the Lance table layout or packaging zip structure
- Project index behavior

## Acceptance Criteria

- AC-1: After pruning removed pack files, the framework `meta.json` no longer contains those pruned paths in `file_meta`.
- AC-2: Legacy `file_hashes` metadata, when present, is pruned the same way.
- AC-3: Paths that remain in the new pack stay present in metadata.
- AC-4: Existing prune behavior for non-index files and directories is unchanged.

## Required Review Lanes

- `qa-reviewer` — required (upgrade-time prune behavior affects dashboard health)
- `code-reviewer` — required (touches framework upgrade pruning logic)

## Tasks

- Extend `prune_framework.py` to load framework `meta.json` when present and remove pruned paths from its index metadata maps.
- Add tests covering `file_meta` pruning, `file_hashes` pruning, and no-op behavior for surviving paths.
- Run the prune and server tool tests that validate the framework layer’s health/readiness behavior.

## Affected Architecture Docs

N/A. This is a narrow upgrade/prune repair.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Fixes the stale-path framework health symptom |
| AC-2 | required | Preserves compatibility with older index metadata |
| AC-3 | required | Avoids accidental data loss from the prune repair |
| AC-4 | important | Ensures the upgrade path still behaves as expected |
