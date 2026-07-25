# Decision: memory-supply targets exclude verification harness entries

Owner: Engineering
Status: superseded
Last verified: 2026-07-23

Memory ID: `1tdmn-mem decision-memory-supply-targets-exclude-verification-harness-`
Superseded by: `1tj3j-mem memory-supply-targets-exclude-harness-entries-on-both-drafti`
Kind: `decision`
Confidence: 0.9
Created: 2026-07-23
Updated: 2026-07-25
Supersedes: `1t21l-mem decision-memory-supply-targets-exclude-the-verification-comm`

## Summary

When drafting memory candidates from repaired findings, exclude the canonical test-runner entry and any runner entry named by docs/workflow-config.json test_runner from every evidence-derived target source, including artifact_or_test_id; if no repaired-surface target survives, draft nothing.

## Evidence

- `1tgkx-bug memory-propose-harness-token-target-misattribution`
- `MemoryProposeTests.test_artifact_harness_tokens_never_become_targets`
- `MemoryProposeTests.test_configured_runner_is_filtered_but_product_signal_survives`
- `1tbt5`

## Targets

- `.wavefoundry/framework/scripts/memory_supply.py`
