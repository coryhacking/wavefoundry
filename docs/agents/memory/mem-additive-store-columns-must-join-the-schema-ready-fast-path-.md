# Additive store columns must join the schema_ready fast-path check

Owner: Engineering
Status: active
Last verified: 2026-07-20

Memory ID: `mem-additive-store-columns-must-join-the-schema-ready-fast-path-`
Kind: `environment_gotcha`
Confidence: 0.95
Created: 2026-07-20
Updated: 2026-07-20

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
