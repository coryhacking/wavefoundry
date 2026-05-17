# Remove legacy JSON fixture references from dashboard tests

Change ID: `12p2t-maint remove-legacy-json-fixtures`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-16
Wave: 12nbr code-intelligence-expansion

## Rationale

The dashboard and index code now use LanceDB tables exclusively. A few tests still create `docs.json` fixtures or mention the deleted flat-file layout, which is confusing and no longer reflects the shipped format. This cleanup removes the remaining legacy JSON fixture references from tests so the suite matches the current pack layout.

## Requirements

1. Remove legacy `docs.json` fixture writes from dashboard/index tests.
2. Keep the tests focused on LanceDB-backed index fixtures and snapshot behavior.
3. Preserve coverage for the same behaviors that the legacy fixtures were exercising.

## Scope

**Problem statement:** Some tests still mention or create deleted JSON index files even though the repository no longer ships them.

**In scope:**

- `test_server_tools.py` legacy JSON fixture cleanup
- Any dashboard tests that still create `docs.json` as part of index setup

**Out of scope:**

- Runtime support for legacy JSON index files
- Documentation history under `docs/waves/`
- Broad dashboard rendering changes

## Acceptance Criteria

- AC-1: No dashboard/index tests create `docs.json` or `code.json` fixtures for normal LanceDB-backed setup.
- AC-2: Existing dashboard snapshot and health tests still pass using LanceDB tables only.
- AC-3: The cleanup does not change runtime behavior or restored stats handling.

## Tasks

- Locate remaining test-only `docs.json` / `code.json` fixture writes.
- Replace them with LanceDB-backed setup or remove them where they are no longer needed.
- Run the dashboard and server tool test subsets that exercise the affected paths.

## Required Review Lanes

- `qa-reviewer` — required (test cleanup that affects dashboard/index contract coverage)
- `code-reviewer` — required (touches test fixtures for index behavior)

## Affected Architecture Docs

N/A. Test fixture cleanup only.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Removes the stale fixture format from normal test setup |
| AC-2 | required | Ensures the suite still validates current behavior |
| AC-3 | important | Prevents accidental runtime changes during cleanup |
