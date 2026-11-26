# Preserve unreadable paths before every index removal consumer

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24d31-mem preserve-unreadable-paths-before-every-index-removal-consume`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 1539381
Action delta: When changing index removals, trace removed_broad through publication and pass unreadable directories into graph reconciliation. Check that earlier indexed data survives a temporarily unreadable subtree.
Validation rationale: Checked the walk-shadow filter, SQLite writer transaction, layer-hash deletion and graph merge in the current indexer.
Supersedes: `1x78p-mem indexer-py-the-reap-is-not-the-first-deleter-so-walk-output-`

## Summary

The SQLite index writer consumes removal sets after the walk. The registry, layer hashes, scanner bookkeeping and graph merge also consume walk results. Filtering only the final reap leaves other paths able to discard prior data for a directory the walker could not read.

## Evidence

- `1x54z`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/graph_indexer.py`

## Targets

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/graph_indexer.py`
