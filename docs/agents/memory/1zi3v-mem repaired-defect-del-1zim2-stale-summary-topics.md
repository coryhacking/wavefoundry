# Repaired defect DEL-1ZIM2-STALE-SUMMARY-TOPICS

Owner: Engineering
Status: rejected
Last verified: 2026-10-01

Memory ID: `1zi3v-mem repaired-defect-del-1zim2-stale-summary-topics`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 113318
Source event: `finding:1zim2:DEL-1ZIM2-STALE-SUMMARY-TOPICS`
Validation: reject
Validated by: agent
Action delta: No durable action: the template count is now pinned by test_template_row_2_15_names_the_seed_summary_topic_count.
Validation rationale: A one-off stale count, now guarded by a test that derives the count from the seed; a memory adds nothing.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Real defect fixed in wave 1zim2: Stale enumeration fixed and pinned.

## Evidence

- `DEL-1ZIM2-STALE-SUMMARY-TOPICS`
- `ev-del-1zim2-stale-summary-topics-3`
- `1zim2`

## Targets

- `tests/test_install_log_lib.py`
