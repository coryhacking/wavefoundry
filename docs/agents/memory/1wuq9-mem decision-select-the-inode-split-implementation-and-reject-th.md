# Decision: Select the inode-split implementation and reject the store-…

Owner: Engineering
Status: active
Last verified: 2026-09-01

Memory ID: `1wuq9-mem decision-select-the-inode-split-implementation-and-reject-th`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-01
Updated: 2026-09-01
Source exploration cost: 125943
Source event: `decision-log:1wtpl-bug retrieval-eval-store-identity-binding:4d84acff095fca47`
Validation: promote
Validated by: agent
Action delta: Before minting any new identity field in index_state_store.py, remember that the module is a PRODUCTION_RETRIEVAL_MODULES member: touching it perturbs production_identity and turns a same-generation comparison into a production change, so evaluator identity must be derived from existing fields.
Validation rationale: Evidence followed: the 1wtpl Decision Log row (readiness CODE-RDY-6) and the delivered CROSS_GENERATION_INDEX_IDENTITY_KEYS / SAME_GENERATION_INDEX_IDENTITY_KEYS split in retrieval_eval.py, which binds the store file device and inode only for same-generation receipts. Current target verified: index_state_store.py is unchanged by this wave and remains in PRODUCTION_RETRIEVAL_MODULES. The rationale is durable design guidance for any future evaluator or store change and is not stated in a canonical doc.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
## Summary

Decision (wave 1wur7): Select the inode-split implementation and reject the store-instance-identifier alternative (readiness CODE-RDY-6).. Rationale: No such identifier exists; minting one edits `index_state_store.py`, a `PRODUCTION_RETRIEVAL_MODULES` member, which would perturb `production_identity` and contradict this wave's own "no product path" scope. A `meta`-row identifier would also travel with a file copy, admitting a copied store that the inode correctly refuses..

## Evidence

- `1wtpl-bug retrieval-eval-store-identity-binding`
- `1wur7`

## Targets

- `index_state_store.py`
