# Retrieval-eval store identity uses the inode, not a minted store-instance id

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24akh-mem retrieval-eval-store-identity-uses-the-inode-not-a-minted-st`
Kind: `decision`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 125943
Supersedes: `1wuq9-mem decision-select-the-inode-split-implementation-and-reject-th`
Checked at: 2026-11-26T06:32:43Z
Check note: The evaluator binds to the underlying store identity. Replacing the store and reopening the same path are different cases. Reviewed .wavefoundry/framework/scripts/retrieval_eval.py:1606.
Check flags: none

## Summary

When you change how retrieval_eval binds a run to its index state store, keep the device-and-inode binding and do not add a store-instance identifier (decision in wave 1wur7, change 1wtpl). No such identifier exists. Minting one means editing .wavefoundry/framework/scripts/index_state_store.py, a PRODUCTION_RETRIEVAL_MODULES member, which perturbs production_identity. An identifier stored in a meta row would also travel with a file copy and admit a copied store that the inode check correctly refuses.

## Evidence

- `1wtpl-bug retrieval-eval-store-identity-binding`
- `1wur7`

## Targets

- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/retrieval_eval.py`
