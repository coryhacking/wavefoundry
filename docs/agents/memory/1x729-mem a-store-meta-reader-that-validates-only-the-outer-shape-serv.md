# A store meta reader that validates only the outer shape serves malformed entries

Owner: Engineering
Status: active
Last verified: 2026-09-05

Memory ID: `1x729-mem a-store-meta-reader-that-validates-only-the-outer-shape-serv`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-09-05
Updated: 2026-09-05

## Summary

Wave 1x6ti (1x551): reap_state_for_index in index_state_store.py served hand-edited or future-schema per-table entries verbatim when it checked only that the deferred and preserved maps were dicts, and a second pass that coerced with int() still accepted bools, truncated floats and defaulted a missing key under a surviving mutant. The shipped reader accepts a count only when it is an int, not a bool and non-negative (_is_count), drops any other entry, and reads a record with no well-formed entry as none, so the two tools that share it (index_build_status, index_health) never show a malformed block. Reuse the posture for any new meta record: validate per entry, no coercion, no default; the display-only generation and timestamp fields are still coerced (QA-RV2-2, accepted).

## Evidence

- `1x6ti`
- `QA-DEL-3`
- `QA-RV1-3`
- `QA-RV2-2`
- `test_server_tools_retrieval.ReapStateSurfaceTests.test_malformed_per_table_entries_are_dropped_by_the_reader`

## Targets

- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
