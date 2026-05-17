# Framework pack index should follow the pack file filter

Change ID: `12p2y-bug framework-pack-index-follows-pack-filter`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-17
Wave: 12nbr code-intelligence-expansion

## Rationale

The framework package already excludes development-only files such as `scripts/tests/`, `scripts/benchmarks/`, and `scripts/run_tests.py` from the zip. The framework index build still walks the full framework tree before packaging, so `meta.json` can retain entries for files that are not shipped. That leaves the packaged framework layer reporting ghost paths even though the zip contents are clean.

This change makes the framework index build use the same exclusion-filtered file set that the packer uses, so the shipped LanceDB metadata only tracks files that are actually present in the packaged framework tree.

## Requirements

1. Packaging must build the framework index from the same filtered file list used to produce the zip.
2. The filtered framework index build must exclude development-only framework paths that are not shipped.
3. The new behavior must preserve incremental updates and LanceDB compaction.
4. Packaging tests must prove the framework index build no longer admits excluded pack-only files into `meta.json`.

## Scope

**Problem statement:** `build_pack.py` currently excludes development-only files from the zip, but the framework index is still generated from the unfiltered framework walk, leaving ghost entries in `meta.json`.

**In scope:**

- `build_pack.py`
- `indexer.py`
- `test_build_pack.py`
- `test_dashboard_server.py` if needed for end-to-end health coverage

**Out of scope:**

- Rebuilding the framework index from scratch on every package
- Changing the shipped Lance table layout
- Project index behavior

## Acceptance Criteria

- AC-1: The packaged framework index no longer contains metadata entries for files excluded from the pack zip.
- AC-2: Packaging still uses the incremental framework index update path.
- AC-3: LanceDB compaction still runs and remains a hard requirement.
- AC-4: Tests cover the filtered pack file list being used for the framework index build.

## Required Review Lanes

- `qa-reviewer` — required (packaging/index health affects shipped dashboards)
- `code-reviewer` — required (touches framework packaging and indexer behavior)

## Tasks

- Extend the framework index build path so it can consume an explicit filtered file list.
- Update `build_pack.py` to feed the pack file list into the framework index update before zipping.
- Add regression coverage that excluded framework pack files do not appear in `meta.json`.
- Verify packaging still compacts Lance tables before producing the zip.

## Affected Architecture Docs

N/A. This is a narrow packaging/index consistency fix.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Fixes the ghost-entry framework health symptom |
| AC-2 | required | Preserves the current incremental packaging flow |
| AC-3 | required | Ensures the packaged index is compacted before release |
| AC-4 | important | Prevents regression back to the unfiltered tree walk |
