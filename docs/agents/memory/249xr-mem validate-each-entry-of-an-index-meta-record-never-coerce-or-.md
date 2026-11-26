# Validate each entry of an index meta record; never coerce or default

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249xr-mem validate-each-entry-of-an-index-meta-record-never-coerce-or-`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1x729-mem a-store-meta-reader-that-validates-only-the-outer-shape-serv`

## Summary

When you write a reader for a JSON meta record in the index state store that tools surface (as reap_state_for_index in index_state_store.py serves index_build_status and index_health), validate each entry. Do not coerce and do not default a missing key. Drop a malformed entry, and read a record with no well-formed entry as none. In wave 1x6ti (1x551), checking only that the outer maps were dicts served hand-edited and future-schema entries verbatim (QA-DEL-3). A second pass that coerced with int() still accepted bools and truncated floats, and it defaulted a missing key under a surviving mutant (QA-RV1-3). The shipped _is_count accepts only a non-negative int that is not a bool. Display-only generation and timestamp fields are still coerced, an accepted exception (QA-RV2-2).

## Evidence

- `1x6ti`
- `QA-DEL-3`
- `QA-RV1-3`
- `QA-RV2-2`
- `test_server_tools_retrieval.ReapStateSurfaceTests.test_malformed_per_table_entries_are_dropped_by_the_reader`

## Targets

- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
