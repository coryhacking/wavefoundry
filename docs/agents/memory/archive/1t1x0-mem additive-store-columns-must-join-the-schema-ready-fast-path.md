# Additive store columns must join the schema_ready fast-path check

Owner: Engineering
Status: archived
Last verified: 2026-07-20

Memory ID: `1t1x0-mem additive-store-columns-must-join-the-schema-ready-fast-path`
Kind: `environment_gotcha`
Confidence: 0.95
Created: 2026-07-20
Updated: 2026-11-25
Checked at: 2026-11-25T16:09:19Z
Check note: Item 7 review: target gone or duplicate. The action is carried at the target: the inline comment at context_efficiency.py:1316-1319 says every additive column MUST appear in the schema_ready column check (cites 1t3ek/1t3el), and tests/test_context_efficiency.py::AdditiveColumnMigrationTests (docstring :1683-1686, test_current_store_without_attribution_column_migrates_and_records) carries the stri.
Check flags: none
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, gone or carried by The action is carried at the target: the inline comment at context_efficiency.py:1316-1319 says every additive column MUST appear in the schema_ready column check (cites 1t3ek/1t3el), and tests/test_context_efficiency.py::AdditiveColumnMigratio.
Archive path: `docs/agents/memory/archive/1t1x0-mem additive-store-columns-must-join-the-schema-ready-fast-path.md`

## Summary

When adding a column to the context-efficiency store, the ALTER migration in _open_write_store_once only runs when schema_ready is False — and schema_ready is True for every already-current production store unless the new column is added to its explicit column check. A column missing from that check never migrates onto existing stores; the first INSERT naming it fails and correctly poisons the store. Hermetic tests cannot catch this class because fresh stores gain the column via CREATE TABLE — verify additive migrations with a live-store or stripped-current-store probe (the AdditiveColumnMigrationTests pattern).

## Evidence

- `1t3el-enh multi-agent-open-wave-attribution`
- `1t3ek`
- `schema-ready-fast-path-skips-additive-migration`
- `.wavefoundry/framework/scripts/context_efficiency.py`
- `AdditiveColumnMigrationTests.test_current_store_without_attribution_column_migrates_and_records`

## Targets

- `.wavefoundry/framework/scripts/context_efficiency.py`
